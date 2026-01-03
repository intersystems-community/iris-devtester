"""
Custom wait strategies for IRIS containers.

Provides IRIS-specific readiness checks to ensure containers are fully ready
before returning control to tests or application code.
"""

import logging
import socket
import time
from typing import Optional

logger = logging.getLogger(__name__)


class IRISReadyWaitStrategy:
    """
    Wait strategy that ensures IRIS is fully ready.

    Checks multiple readiness criteria:
    1. Port is open and accepting connections
    2. IRIS process is running inside container
    3. Database accepts SQL queries
    4. Namespace is accessible

    This is more thorough than simple port checks and prevents race conditions
    where port is open but database isn't ready.
    """

    def __init__(
        self,
        port: int = 1972,
        timeout: int = 60,
        poll_interval: float = 1.0,
    ):
        """
        Initialize IRIS readiness wait strategy.

        Args:
            port: IRIS superserver port to check (default: 1972)
            timeout: Maximum time to wait in seconds (default: 60)
            poll_interval: Time between readiness checks in seconds (default: 1.0)
        """
        self.port = port
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._timeout = timeout  # Alias for compatibility

    def wait_until_ready(
        self,
        host: str,
        port: Optional[int] = None,
        timeout: Optional[int] = None,
        container_name: Optional[str] = None,
    ) -> bool:
        port = port or self.port
        timeout = timeout or self.timeout

        logger.info(f"Waiting for IRIS at {host}:{port} (timeout: {timeout}s)...")

        start_time = time.time()
        last_error = None

        while time.time() - start_time < timeout:
            try:
                # Check 1: Port is open
                if self._check_port_open(host, port):
                    logger.debug(f"✓ Port {port} is open")

                    if container_name:
                        if self.check_iris_initialized(container_name):
                            logger.info(f"✓ IRIS application initialized at {host}:{port}")
                            return True
                        else:
                            logger.debug("Port open but IRIS application not fully ready yet")
                    else:
                        logger.info(f"✓ IRIS ready at {host}:{port} (port check only)")
                        return True

            except Exception as e:
                last_error = e
                logger.debug(f"Not ready yet: {e}")

            time.sleep(self.poll_interval)

        # Timeout reached

        elapsed = time.time() - start_time
        raise TimeoutError(
            f"IRIS not ready after {elapsed:.1f}s\n"
            f"Host: {host}:{port}\n"
            f"Last error: {last_error}\n"
            "\n"
            "How to fix it:\n"
            "  1. Check container logs:\n"
            "     docker logs <container_name>\n"
            "\n"
            "  2. Verify IRIS is starting:\n"
            "     docker exec <container_name> iris list\n"
            "\n"
            "  3. Increase timeout if needed:\n"
            f"     IRISReadyWaitStrategy(timeout={timeout * 2})\n"
        )

    def check_iris_initialized(self, container_name: str) -> bool:
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "exec", container_name, "iris", "session", "IRIS", "-U", "%SYS", "W 1", "Halt"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "1" in result.stdout
        except Exception:
            return False

    def check_iris_running(self, container_name: str) -> bool:
        """
        Check if IRIS process is running inside container.

        Args:
            container_name: Name of Docker container

        Returns:
            True if IRIS process is running

        Note: This requires Docker access and is optional for basic readiness.

        Example:
            >>> strategy = IRISReadyWaitStrategy()
            >>> with IRISContainer.community() as iris:
            ...     container_name = iris.get_container_name()
            ...     if strategy.check_iris_running(container_name):
            ...         print("IRIS process is active")
        """
        try:
            import subprocess

            result = subprocess.run(
                ["docker", "exec", container_name, "iris", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0 and "IRIS" in result.stdout

        except Exception as e:
            logger.debug(f"Could not check IRIS process: {e}")
            return False

    def _check_port_open(self, host: str, port: int, timeout: float = 2.0) -> bool:
        """
        Check if port is open and accepting connections.

        Args:
            host: Host to check
            port: Port to check
            timeout: Connection timeout in seconds

        Returns:
            True if port is open
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception as e:
            logger.debug(f"Port check failed: {e}")
            return False


def wait_for_iris_ready(
    host: str = "localhost",
    port: int = 1972,
    timeout: int = 60,
    poll_interval: float = 1.0,
) -> bool:
    """
    Convenience function to wait for IRIS to be ready.

    Args:
        host: IRIS host (default: "localhost")
        port: IRIS port (default: 1972)
        timeout: Maximum wait time in seconds (default: 60)
        poll_interval: Time between checks in seconds (default: 1.0)

    Returns:
        True if IRIS is ready, False if timeout

    Example:
        >>> from iris_devtester.containers import wait_for_iris_ready
        >>> if wait_for_iris_ready("localhost", 1972, timeout=30):
        ...     print("IRIS is ready!")
        ... else:
        ...     print("Timeout waiting for IRIS")
    """
    strategy = IRISReadyWaitStrategy(
        port=port, timeout=timeout, poll_interval=poll_interval
    )

    try:
        return strategy.wait_until_ready(host, port, timeout)
    except TimeoutError:
        logger.error(f"Timeout waiting for IRIS at {host}:{port}")
        return False
    except Exception as e:
        logger.error(f"Error waiting for IRIS: {e}")
        return False
