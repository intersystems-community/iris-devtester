"""Multi-layer health check utilities for IRIS containers."""

import socket
import time
from typing import Callable, Optional

from docker.models.containers import Container

from iris_devtester.config.container_state import ContainerState, HealthStatus


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
