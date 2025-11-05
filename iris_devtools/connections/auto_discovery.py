"""
Auto-discovery of IRIS connection parameters from Docker and native instances.

Extracted from rag-templates production code with enhancements.
"""

import logging
import re
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def auto_detect_iris_port() -> Optional[int]:
    """
    Auto-detect IRIS port from running Docker containers or native instances.

    Priority:
    1. Docker containers (docker ps)
    2. Native IRIS instances (iris list)

    Args:
        (no arguments)

    Returns:
        Detected port number or None if not found

    Example:
        >>> port = auto_detect_iris_port()
        >>> if port:
        ...     print(f"Found IRIS on port {port}")
    """
    # Try Docker first
    port = _detect_port_from_docker()
    if port:
        logger.info(f"Auto-detected IRIS port {port} from Docker")
        return port

    # Fall back to native instances
    port = _detect_port_from_native()
    if port:
        logger.info(f"Auto-detected IRIS port {port} from native instance")
        return port

    logger.debug("Could not auto-detect IRIS port")
    return None


def auto_detect_iris_host_and_port() -> Tuple[Optional[str], Optional[int]]:
    """
    Auto-detect both IRIS host and port from running instances.

    Args:
        (no arguments)

    Returns:
        Tuple of (host, port) or (None, None) if not found

    Example:
        >>> host, port = auto_detect_iris_host_and_port()
        >>> if host and port:
        ...     print(f"Found IRIS at {host}:{port}")
    """
    # For Docker, host is always localhost
    port = _detect_port_from_docker()
    if port:
        return "localhost", port

    # For native, host is also localhost (local instance)
    port = _detect_port_from_native()
    if port:
        return "localhost", port

    return None, None


def _detect_port_from_docker() -> Optional[int]:
    """
    Detect IRIS port from Docker containers.

    Looks for containers with port mappings like:
    - 0.0.0.0:1972->1972/tcp
    - :::1972->1972/tcp

    Returns:
        Port number or None
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("Docker not available or not running")
            return None

        # Look for containers with IRIS port mapping (1972)
        # Note: We look for ANY container mapping port 1972, not just those named "iris"
        # This is more flexible and handles custom container names
        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            # Skip lines that don't have tab separator
            if "\t" not in line:
                continue

            name, ports = line.split("\t", 1)

            # Look for port mapping like "0.0.0.0:1972->1972/tcp" or "0.0.0.0:51773->1972/tcp"
            # Match patterns: 0.0.0.0:PORT->1972/tcp or :::PORT->1972/tcp
            match = re.search(r"(?:0\.0\.0\.0|:::):?(\d+)->1972/tcp", ports)
            if match:
                port = int(match.group(1))
                logger.debug(f"Found IRIS port {port} in Docker container {name}")
                return port

            # Also check if container name contains 'iris' (lower priority)
            # This handles containers that might use port 1972 internally
            if "iris" in name.lower() and "1972" in ports:
                # Try to extract any mapped port
                match = re.search(r"(?:0\.0\.0\.0|:::):?(\d+)->(\d+)/tcp", ports)
                if match:
                    external_port = int(match.group(1))
                    logger.debug(f"Found IRIS container '{name}' with port {external_port}")
                    return external_port

    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
        logger.debug(f"Error detecting port from Docker: {e}")

    return None


def _detect_port_from_native() -> Optional[int]:
    """
    Detect IRIS port from native instances using 'iris list'.

    Parses output like:
    Configuration 'IRIS'
        SuperServers: 1972

    Returns:
        Port number or None
    """
    try:
        result = subprocess.run(
            ["iris", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("IRIS not installed or 'iris list' failed")
            return None

        # Look for SuperServers line
        for line in result.stdout.splitlines():
            if "SuperServer" in line:
                # Parse "SuperServers: 1972" or similar
                match = re.search(r"SuperServer\w*:\s*(\d+)", line)
                if match:
                    port = int(match.group(1))
                    logger.debug(f"Found IRIS port {port} from native instance")
                    return port

    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
        logger.debug(f"Error detecting port from native IRIS: {e}")

    return None
