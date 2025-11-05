"""
Auto-discovery utilities for IRIS database instances.

Automatically detects running IRIS instances via:
1. Docker container inspection
2. Native IRIS command-line tools
3. Multi-port scanning

Extracted from production rag-templates project.
"""

import logging
import re
import subprocess
import sys
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def discover_iris_port(test_ports: list[int] = None) -> Optional[int]:
    """
    Auto-discover IRIS SuperServer port from running instances.

    Tests multiple common IRIS ports in priority order until one succeeds.

    Args:
        test_ports: List of ports to test (default: [31972, 1972, 11972, 21972])

    Returns:
        Port number if IRIS found, None otherwise

    Example:
        >>> port = discover_iris_port()
        >>> if port:
        ...     print(f"Found IRIS on port {port}")

    Port Conventions:
        - 31972: Testcontainers (ephemeral, random high ports)
        - 1972:  Standard IRIS installation
        - 11972: rag-templates default (avoids conflicts)
        - 21972: Licensed/Enterprise IRIS
    """
    if test_ports is None:
        # Priority order: testcontainers, standard, rag-templates, licensed
        test_ports = [31972, 1972, 11972, 21972]

    logger.debug(f"Testing IRIS ports in order: {test_ports}")

    for port in test_ports:
        if _test_iris_port(port):
            logger.info(f"✅ Discovered IRIS on port {port}")
            return port

    logger.warning(f"No IRIS found on any of these ports: {test_ports}")
    return None


def _test_iris_port(port: int, timeout: int = 5) -> bool:
    """
    Test if IRIS is accessible on given port.

    Uses subprocess to avoid import issues and connection caching.

    Args:
        port: Port number to test
        timeout: Timeout in seconds

    Returns:
        True if IRIS responds on this port
    """
    try:
        # Test with subprocess to avoid import/connection issues
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import intersystems_iris.dbapi._DBAPI as dbapi
try:
    conn = dbapi.connect("localhost:{port}/USER", "_SYSTEM", "SYS")
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result and result[0] == 1:
        print("SUCCESS")
    else:
        print("FAILED")
except Exception:
    print("FAILED")
""",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if "SUCCESS" in result.stdout:
            logger.debug(f"Port {port} responded successfully")
            return True
        else:
            logger.debug(f"Port {port} test failed: {result.stdout.strip()}")
            return False

    except subprocess.TimeoutExpired:
        logger.debug(f"Port {port} test timed out after {timeout}s")
        return False
    except FileNotFoundError:
        logger.error(f"Python not found at {sys.executable}")
        return False
    except Exception as e:
        logger.debug(f"Port {port} test failed with exception: {e}")
        return False


def discover_docker_iris() -> Optional[Dict[str, Any]]:
    """
    Auto-detect IRIS running in Docker containers.

    Inspects running Docker containers for IRIS instances and extracts
    connection information from port mappings.

    Returns:
        Dict with connection config if found, None otherwise

    Example:
        >>> config = discover_docker_iris()
        >>> if config:
        ...     print(f"Found IRIS at {config['host']}:{config['port']}")
    """
    try:
        # Get running containers with port mappings
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("Docker ps failed, Docker may not be available")
            return None

        # Look for IRIS containers
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            # Check if this is an IRIS container
            if "iris" not in line.lower():
                continue

            # Parse port mapping: "0.0.0.0:11972->1972/tcp"
            match = re.search(r"0\.0\.0\.0:(\d+)->1972/tcp", line)
            if match:
                port = int(match.group(1))
                container_name = line.split("\t")[0]

                logger.info(
                    f"✅ Discovered Docker IRIS container '{container_name}' on port {port}"
                )

                return {
                    "host": "localhost",
                    "port": port,
                    "username": "_SYSTEM",
                    "password": "SYS",
                    "namespace": "USER",
                    "container_name": container_name,
                }

        logger.debug("No IRIS containers found in Docker")
        return None

    except FileNotFoundError:
        logger.debug("Docker command not found, Docker not installed")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Docker ps timed out after 5s")
        return None
    except Exception as e:
        logger.warning(f"Docker discovery failed: {e}")
        return None


def discover_native_iris() -> Optional[Dict[str, Any]]:
    """
    Auto-detect native IRIS installation (non-Docker).

    Uses 'iris list' command to find running IRIS instances.

    Returns:
        Dict with connection config if found, None otherwise

    Example:
        >>> config = discover_native_iris()
        >>> if config:
        ...     print(f"Found native IRIS on port {config['port']}")
    """
    try:
        # Run 'iris list' to see running instances
        result = subprocess.run(
            ["iris", "list"], capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            logger.debug(f"'iris list' failed with exit code {result.returncode}")
            return None

        # Parse output for running instances
        # Format: "status: running, since ..."
        # Then: "SuperServers: <port>"
        lines = result.stdout.split("\n")

        for i, line in enumerate(lines):
            if "status:" in line and "running" in line:
                # Found running instance, look for SuperServers port
                for j in range(i + 1, min(i + 5, len(lines))):
                    if "SuperServers:" in lines[j]:
                        # Extract port number
                        match = re.search(r"SuperServers:\s+(\d+)", lines[j])
                        if match:
                            port = int(match.group(1))

                            logger.info(
                                f"✅ Discovered native IRIS on SuperServer port {port}"
                            )

                            return {
                                "host": "localhost",
                                "port": port,
                                "username": "_SYSTEM",
                                "password": "SYS",
                                "namespace": "USER",
                            }

        logger.debug("No running IRIS instances found via 'iris list'")
        return None

    except FileNotFoundError:
        logger.debug("'iris' command not found, native IRIS not installed")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("'iris list' timed out after 5s")
        return None
    except Exception as e:
        logger.warning(f"Native IRIS discovery failed: {e}")
        return None


def auto_discover_iris() -> Optional[Dict[str, Any]]:
    """
    Automatically discover IRIS instance using all available methods.

    Tries in priority order:
    1. Docker containers (most common for development)
    2. Native IRIS installation (production deployments)
    3. Multi-port scanning (fallback)

    Returns:
        Dict with connection config if found, None otherwise

    Example:
        >>> config = auto_discover_iris()
        >>> if config:
        ...     conn = dbapi.connect(
        ...         f"{config['host']}:{config['port']}/{config['namespace']}",
        ...         config['username'],
        ...         config['password']
        ...     )

    See Also:
        - docs/learnings/rag-templates-production-patterns.md (Pattern 1, 2)
        - CONSTITUTION.md Principle #4 (Zero Configuration Viable)
    """
    logger.info("Auto-discovering IRIS instance...")

    # Priority 1: Docker containers
    config = discover_docker_iris()
    if config:
        logger.info(
            f"✓ Auto-discovery successful (Docker): {config['host']}:{config['port']}"
        )
        return config

    # Priority 2: Native IRIS
    config = discover_native_iris()
    if config:
        logger.info(
            f"✓ Auto-discovery successful (Native): {config['host']}:{config['port']}"
        )
        return config

    # Priority 3: Multi-port scanning
    port = discover_iris_port()
    if port:
        config = {
            "host": "localhost",
            "port": port,
            "username": "_SYSTEM",
            "password": "SYS",
            "namespace": "USER",
        }
        logger.info(
            f"✓ Auto-discovery successful (Port scan): {config['host']}:{config['port']}"
        )
        return config

    logger.warning(
        "✗ Auto-discovery failed. No IRIS instance found.\n"
        "\n"
        "Tried:\n"
        "  1. Docker containers (docker ps)\n"
        "  2. Native IRIS (iris list)\n"
        "  3. Port scanning (31972, 1972, 11972, 21972)\n"
        "\n"
        "Solutions:\n"
        "  - Start IRIS: docker-compose up -d\n"
        "  - Use IRISContainer.community() for automatic management\n"
        "  - Provide explicit connection config\n"
    )
    return None


if __name__ == "__main__":
    """Quick test of auto-discovery."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s: %(message)s"
    )

    print("=" * 60)
    print("IRIS Auto-Discovery Test")
    print("=" * 60)

    config = auto_discover_iris()

    if config:
        print(f"\n✅ SUCCESS - Found IRIS instance:")
        print(f"   Host: {config['host']}")
        print(f"   Port: {config['port']}")
        print(f"   Namespace: {config['namespace']}")
        if "container_name" in config:
            print(f"   Container: {config['container_name']}")
        print()
    else:
        print("\n❌ FAILED - No IRIS instance found")
        print("   See log messages above for details\n")
        exit(1)

    print("=" * 60)
