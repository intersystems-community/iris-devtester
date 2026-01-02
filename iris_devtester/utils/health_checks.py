"""Multi-layer health check utilities for IRIS containers."""

import re
import socket
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional

from docker.models.containers import Container

from iris_devtester.config.container_state import ContainerState, HealthStatus


class IrisHealthState(IntEnum):
    """IRIS $SYSTEM.Monitor.State() return values.

    Source: docs/learnings/iris-container-readiness.md

    These values match the official IRIS API return values:
    - 0: OK - System is healthy and ready for connections
    - 1: Warning - Minor issues detected, may still work
    - 2: Error - Significant problems, likely connection failures
    - 3: Fatal - Critical failure, do not use container
    """

    OK = 0
    WARNING = 1
    ERROR = 2
    FATAL = 3

    @property
    def is_healthy(self) -> bool:
        """Check if this state is considered healthy.

        OK and Warning are both considered healthy (can accept connections).
        Error and Fatal indicate the container should not be used.
        """
        return self.value <= 1


@dataclass
class IrisMonitorResult:
    """Result from checking IRIS $SYSTEM.Monitor.State().

    Attributes:
        state: The IrisHealthState enum value
        is_healthy: True if state is OK or Warning
        message: Human-readable description of the state
        raw_output: Raw output from the IRIS command (for debugging)
    """

    state: IrisHealthState
    is_healthy: bool
    message: str
    raw_output: str = ""


# Map state values to human-readable messages
_IRIS_STATE_MESSAGES = {
    IrisHealthState.OK: "OK - Container healthy",
    IrisHealthState.WARNING: "Warning - Container has minor issues",
    IrisHealthState.ERROR: "Error - Container has problems",
    IrisHealthState.FATAL: "Fatal - Container unusable",
}


def wait_for_healthy(
    container: Container,
    timeout: int = 60,
    progress_callback: Optional[Callable[[str], None]] = None
) -> ContainerState:
    """
    Wait for container to be fully healthy using multi-layer validation.

    This implements a progressive validation strategy:
    1. Layer 1: Container running (fast fail if crashes)
    2. Layer 2: Docker health check passing (if defined)
    3. Layer 3: IRIS SuperServer port accessible (service ready)
    4. Layer 4: IRIS $SYSTEM.Monitor.State() = OK (IRIS-level health)

    Layer 4 is the official IRIS health check that ensures the container is
    truly ready for connections, not just that the port is open.
    Source: docs/learnings/iris-container-readiness.md

    Args:
        container: Container to wait for
        timeout: Maximum time to wait (seconds)
        progress_callback: Optional callback for progress messages

    Returns:
        ContainerState when container is healthy

    Raises:
        TimeoutError: If container not healthy within timeout
        RuntimeError: If container crashes or fails

    Example:
        >>> from iris_devtester.utils.iris_container_adapter import IRISContainerManager
        >>> container = IRISContainerManager.get_existing("iris_db")
        >>> if container:
        ...     state = wait_for_healthy(container, timeout=60)
        ...     print(f"Container healthy: {state.status}")
    """

    start_time = time.time()

    def elapsed() -> float:
        return time.time() - start_time

    def notify(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    # Layer 1: Wait for container to be running
    notify("⏳ Waiting for container to start...")
    while elapsed() < timeout:
        container.reload()
        if container.status == "running":
            notify("✓ Container is running")
            break

        if container.status in ["exited", "dead"]:
            logs = container.logs().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"Container failed to start (status: {container.status})\n"
                f"\n"
                f"Container logs:\n{logs[-1000:]}"  # Last 1000 chars
            )

        time.sleep(1)

    if elapsed() >= timeout:
        raise TimeoutError(
            f"Container did not start within {timeout} seconds\n"
            f"Final status: {container.status}"
        )

    # Layer 2: Wait for Docker health check (if defined)
    container.reload()
    has_healthcheck = bool(container.attrs.get("State", {}).get("Health"))

    if has_healthcheck:
        notify("⏳ Waiting for Docker health check...")
        while elapsed() < timeout:
            container.reload()
            health = container.attrs.get("State", {}).get("Health", {})
            health_status = health.get("Status", "none")

            if health_status == "healthy":
                notify("✓ Docker health check passed")
                break

            if health_status == "unhealthy":
                # Get health check logs
                health_log = health.get("Log", [])
                last_log = health_log[-1] if health_log else {}
                output = last_log.get("Output", "No output")

                raise RuntimeError(
                    f"Container health check failed\n"
                    f"\n"
                    f"Health check output:\n{output}"
                )

            time.sleep(2)

        if elapsed() >= timeout:
            raise TimeoutError(
                f"Container health check did not pass within {timeout} seconds"
            )
    else:
        notify("⚠ No Docker health check defined, skipping Layer 2")

    # Layer 3: Wait for IRIS SuperServer port to be accessible
    notify("⏳ Waiting for IRIS SuperServer port...")

    # Get port mapping
    container.reload()
    port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})
    superserver_host_port = None

    for container_port_str, host_bindings in port_bindings.items():
        if "1972" in container_port_str and host_bindings:
            superserver_host_port = int(host_bindings[0]["HostPort"])
            break

    if not superserver_host_port:
        notify("⚠ Could not determine SuperServer port, skipping Layer 3")
    else:
        while elapsed() < timeout:
            try:
                sock = socket.create_connection(
                    ("localhost", superserver_host_port),
                    timeout=2
                )
                sock.close()
                notify(f"✓ IRIS SuperServer port {superserver_host_port} is accessible")
                break
            except (socket.timeout, socket.error, ConnectionRefusedError):
                time.sleep(2)

        if elapsed() >= timeout:
            raise TimeoutError(
                f"IRIS SuperServer port not accessible within {timeout} seconds"
            )

    # Layer 4: Wait for IRIS Monitor.State() to be OK
    # This is the official IRIS health check - more reliable than just port check
    # Source: docs/learnings/iris-container-readiness.md
    notify("⏳ Waiting for IRIS health check (Monitor.State)...")

    while elapsed() < timeout:
        result = check_iris_monitor_state(container)

        if result.is_healthy:
            notify(f"✓ IRIS health check passed: {result.message}")
            break

        # Not healthy yet, wait and retry
        time.sleep(2)

    if elapsed() >= timeout:
        raise TimeoutError(
            f"IRIS Monitor.State check did not pass within {timeout} seconds\n"
            f"Last state: {result.message if 'result' in dir() else 'unknown'}"
        )

    # All layers passed - get final state
    final_state = ContainerState.from_container(container)
    notify(f"✓ Container '{container.name}' is healthy")

    return final_state


def check_port_available(port: int, host: str = "localhost") -> bool:
    """
    Check if a port is accessible.

    Args:
        port: Port number to check
        host: Host to check (default: localhost)

    Returns:
        True if port is accessible, False otherwise

    Example:
        >>> if check_port_available(1972):
        ...     print("Port 1972 is accessible")
    """
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return True
    except (socket.timeout, socket.error, ConnectionRefusedError):
        return False


def check_docker_health(container: Container) -> HealthStatus:
    """
    Check Docker health check status.

    Args:
        container: Container to check

    Returns:
        HealthStatus enum value

    Example:
        >>> container = get_container("iris_db")
        >>> health = check_docker_health(container)
        >>> if health == HealthStatus.HEALTHY:
        ...     print("Container is healthy")
    """
    container.reload()
    health_info = container.attrs.get("State", {}).get("Health", {})

    if not health_info:
        return HealthStatus.NONE

    health_status_str = health_info.get("Status", "none").lower()

    mapping = {
        "starting": HealthStatus.STARTING,
        "healthy": HealthStatus.HEALTHY,
        "unhealthy": HealthStatus.UNHEALTHY,
        "none": HealthStatus.NONE,
    }

    return mapping.get(health_status_str, HealthStatus.NONE)


def is_container_healthy(container: Container) -> bool:
    """
    Quick check if container is fully healthy.

    Checks both running status and health check (if available).

    Args:
        container: Container to check

    Returns:
        True if container is running and healthy

    Example:
        >>> container = get_container("iris_db")
        >>> if is_container_healthy(container):
        ...     print("Ready to connect")
    """
    container.reload()

    # Must be running
    if container.status != "running":
        return False

    # Check health if defined
    health_info = container.attrs.get("State", {}).get("Health", {})
    if health_info:
        health_status = health_info.get("Status", "none")
        return health_status == "healthy"

    # No health check defined - just running is good enough
    return True


def wait_for_port(port: int, host: str = "localhost", timeout: int = 60) -> None:
    """
    Wait for a port to become accessible.

    Args:
        port: Port number to wait for
        host: Host to check (default: localhost)
        timeout: Maximum time to wait (seconds)

    Raises:
        TimeoutError: If port not accessible within timeout

    Example:
        >>> wait_for_port(1972, timeout=30)
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if check_port_available(port, host):
            return

        time.sleep(1)

    raise TimeoutError(
        f"Port {port} on {host} did not become accessible within {timeout} seconds"
    )


def get_container_logs(container: Container, tail: int = 100) -> str:
    """
    Get container logs as string.

    Args:
        container: Container to get logs from
        tail: Number of lines to retrieve from end

    Returns:
        Container logs as string

    Example:
        >>> container = get_container("iris_db")
        >>> logs = get_container_logs(container, tail=50)
        >>> print(logs)
    """
    logs_bytes = container.logs(tail=tail)
    return logs_bytes.decode("utf-8", errors="ignore")


def enable_callin_service(container: Container) -> None:
    """
    Enable CallIn service in IRIS container.

    This is required for DBAPI connections to work.
    Constitutional Principle #2: Automatic Remediation.

    Args:
        container: Running IRIS container

    Raises:
        RuntimeError: If CallIn service cannot be enabled

    Example:
        >>> container = get_container("iris_db")
        >>> enable_callin_service(container)
    """
    # Execute ObjectScript to enable CallIn
    objectscript_cmd = (
        'iris session iris -U%SYS '
        '"Do ##class(Security.Services).Get(\"%Service_CallIn\", .service) '
        'Set service.Enabled = 1 '
        'Do ##class(Security.Services).Modify(\"%Service_CallIn\", .service)"'
    )

    try:
        exit_code, output = container.exec_run(
            cmd=["sh", "-c", objectscript_cmd],
            user="irisowner"
        )

        if exit_code != 0:
            raise RuntimeError(
                f"Failed to enable CallIn service (exit code: {exit_code})\n"
                f"Output: {output.decode('utf-8', errors='ignore')}"
            )

    except Exception as e:
        raise RuntimeError(
            f"Failed to enable CallIn service: {e}\n"
            "\n"
            "What went wrong:\n"
            "  Could not execute ObjectScript command to enable CallIn.\n"
            "\n"
            "Why it matters:\n"
            "  CallIn service is required for DBAPI connections to work.\n"
            "\n"
            "How to fix it:\n"
            "  1. Manually enable in Management Portal:\n"
            "     → System Administration > Security > Services\n"
            "     → Enable %Service_CallIn\n"
            "  2. Or restart container (will auto-enable)\n"
            "\n"
            "Documentation:\n"
            "  https://iris-devtester.readthedocs.io/troubleshooting/callin-service/\n"
        ) from e


def check_iris_monitor_state(container: Container) -> IrisMonitorResult:
    """Check IRIS container health using $SYSTEM.Monitor.State().

    This is the official IRIS API for determining container readiness.
    A container with SuperServer port open is NOT necessarily ready -
    this function checks true IRIS-level health.

    Source: docs/learnings/iris-container-readiness.md

    Args:
        container: Running IRIS container

    Returns:
        IrisMonitorResult with state, is_healthy flag, and message

    Example:
        >>> from iris_devtester.containers import IRISContainer
        >>> with IRISContainer.community() as iris:
        ...     result = check_iris_monitor_state(iris._container)
        ...     if result.is_healthy:
        ...         print("Container ready for connections")
    """
    # ObjectScript command to get Monitor state
    # Use $SYSTEM.Monitor.State() which returns 0=OK, 1=Warning, 2=Error, 3=Fatal
    # Note: ##class(%SYSTEM.System).GetInstanceState() does NOT exist in Community Edition
    objectscript_cmd = '''iris session IRIS -U %SYS << 'EOF'
Write $SYSTEM.Monitor.State()
Halt
EOF'''

    try:
        exit_code, output = container.exec_run(
            cmd=["sh", "-c", objectscript_cmd],
            user="irisowner"
        )

        raw_output = output.decode("utf-8", errors="ignore")

        if exit_code != 0:
            return IrisMonitorResult(
                state=IrisHealthState.FATAL,
                is_healthy=False,
                message=f"Failed to execute health check (exit code: {exit_code})",
                raw_output=raw_output,
            )

        # Parse the state from output - should be 0, 1, 2, 3, or -1
        # -1 means "monitoring not configured" - treat as healthy since container is running
        # The output may contain prompts/banners, so look for the number on its own line
        # Check for -1 first (monitoring unconfigured), then 0-3
        match = re.search(r'(?:^|\n)(-1)\s*(?:\n|$)', raw_output) or re.search(r'(?:^|\n)([0-3])\s*(?:\n|$)', raw_output)
        if match:
            state_value = int(match.group(1))
            # Handle -1 (monitoring unconfigured) as OK since container is running
            if state_value == -1:
                return IrisMonitorResult(
                    state=IrisHealthState.OK,
                    is_healthy=True,
                    message="OK - Container healthy (monitoring not configured)",
                    raw_output=raw_output,
                )
            state = IrisHealthState(state_value)
            return IrisMonitorResult(
                state=state,
                is_healthy=state.is_healthy,
                message=_IRIS_STATE_MESSAGES.get(state, f"Unknown state: {state_value}"),
                raw_output=raw_output,
            )

        # Could not parse state - assume not ready
        return IrisMonitorResult(
            state=IrisHealthState.FATAL,
            is_healthy=False,
            message=f"Could not parse Monitor.State from output",
            raw_output=raw_output,
        )

    except Exception as e:
        return IrisMonitorResult(
            state=IrisHealthState.FATAL,
            is_healthy=False,
            message=f"Health check failed: {e}",
            raw_output="",
        )


def wait_for_iris_healthy(
    container: Container,
    timeout: int = 60,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """Wait for IRIS container to reach healthy state.

    Uses $SYSTEM.Monitor.State() to check true IRIS-level health.
    This is more reliable than just checking if the port is open.

    Source: docs/learnings/iris-container-readiness.md

    Args:
        container: Running IRIS container
        timeout: Maximum time to wait (seconds)
        progress_callback: Optional callback for progress messages

    Returns:
        True if container became healthy, False if timeout

    Example:
        >>> from iris_devtester.containers import IRISContainer
        >>> with IRISContainer.community() as iris:
        ...     if wait_for_iris_healthy(iris._container, timeout=30):
        ...         print("Container ready!")
    """
    start_time = time.time()

    def elapsed() -> float:
        return time.time() - start_time

    def notify(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    notify("⏳ Waiting for IRIS Monitor.State() = OK...")

    while elapsed() < timeout:
        result = check_iris_monitor_state(container)

        if result.is_healthy:
            notify(f"✓ IRIS health check passed: {result.message}")
            return True

        # Not healthy yet, wait and retry
        time.sleep(2)

    notify(f"⚠ IRIS health check timed out after {timeout}s")
    return False
