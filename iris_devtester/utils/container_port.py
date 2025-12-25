"""
Container port detection utility for InterSystems IRIS.

Detects mapped host port for IRIS SuperServer (1972) in Docker containers.
Implements Constitutional Principle #4: "Zero Configuration Viable"
"""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def get_container_port(
    container_name: str,
    container_port: int = 1972,
    timeout: int = 10,
) -> Optional[int]:
    """
    Get the host port mapped to a container's internal port.

    Uses `docker port` to detect the actual mapped port for containers
    that use random port assignment (e.g., testcontainers).

    Args:
        container_name: Docker container name
        container_port: Container internal port (default: 1972 for IRIS SuperServer)
        timeout: Command timeout in seconds

    Returns:
        Host port number if mapping exists, None otherwise

    Example:
        >>> port = get_container_port("my_iris_container")
        >>> if port:
        ...     print(f"IRIS accessible on port {port}")
        ... else:
        ...     print("Port mapping not found")

    Constitutional Compliance:
        - Principle #4: Zero Configuration Viable
          Auto-discovers port without configuration
    """
    try:
        cmd = [
            "docker",
            "port",
            container_name,
            str(container_port),
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse output like "0.0.0.0:55000" or "0.0.0.0:55000\n:::55000"
            port_mapping = result.stdout.strip().split("\n")[0]
            # Extract port number (after the colon)
            host_port = int(port_mapping.split(":")[-1])
            logger.debug(
                f"Container '{container_name}' port {container_port} "
                f"mapped to host port {host_port}"
            )
            return host_port
        else:
            # No port mapping found - container might use fixed ports or not expose this port
            logger.debug(
                f"No port mapping found for {container_name}:{container_port}"
            )
            return None

    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout getting port for container '{container_name}'")
        return None
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse port mapping: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error getting container port: {e}")
        return None


__all__ = ["get_container_port"]
