"""
Connection testing utility for InterSystems IRIS.

Tests database connectivity using non-destructive queries.
Implements Constitutional Principle #7: "Medical-Grade Reliability" (non-destructive)
"""

import logging
import subprocess
from typing import Tuple

logger = logging.getLogger(__name__)


def test_connection(
    container_name: str = "iris_db",
    namespace: str = "USER",
    timeout: int = 10,
) -> Tuple[bool, str]:
    """
    Test connection to IRIS container with a non-destructive query.

    This utility performs a simple SELECT query to validate connectivity
    without modifying any data. Uses docker exec with ObjectScript for
    maximum compatibility.

    Args:
        container_name: Name of IRIS Docker container (default: "iris_db")
        namespace: IRIS namespace to test (default: "USER")
        timeout: Timeout in seconds for docker commands (default: 10)

    Returns:
        Tuple of (success: bool, message: str)
        - success: True if connection successful
        - message: Human-readable status message

    Example:
        >>> success, msg = test_connection("my_iris_container", "USER")
        >>> if success:
        ...     print("IRIS is ready!")

    Constitutional Compliance:
        - Principle #5: Fail Fast with Guidance
          Returns structured (bool, str) with remediation steps on failure
        - Principle #7: Medical-Grade Reliability
          Non-destructive query (SELECT $HOROLOG) - reads only, no writes

    Non-Destructive:
        Only reads system variables - no database modifications.
    """
    try:
        # Step 1: Check if container is running
        logger.debug(f"Checking if container '{container_name}' is running...")

        check_cmd = [
            "docker",
            "ps",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Names}}",
        ]

        result = subprocess.run(
            check_cmd, capture_output=True, text=True, timeout=timeout
        )

        if container_name not in result.stdout:
            return (
                False,
                f"Container '{container_name}' not running\n"
                "\n"
                "What went wrong:\n"
                "  The IRIS container is not running or not accessible.\n"
                "\n"
                "How to fix it:\n"
                "  1. Start the container:\n"
                "     docker-compose up -d\n"
                "\n"
                "  2. Or start manually:\n"
                f"     docker start {container_name}\n"
                "\n"
                "  3. Verify it's running:\n"
                "     docker ps | grep iris\n",
            )

        # Step 2: Test connection with non-destructive query
        logger.debug(f"Testing connection to namespace '{namespace}' in '{container_name}'...")

        # Use simple ObjectScript query: SELECT $HOROLOG (current date/time)
        # This is guaranteed non-destructive - just reads system variable
        test_cmd = [
            "docker",
            "exec",
            "-i",
            container_name,
            "bash",
            "-c",
            f'''echo "write $HOROLOG" | iris session IRIS -U {namespace}''',
        ]

        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Successful connection returns horolog value (e.g., "66666,12345")
        if result.returncode == 0 and "," in result.stdout:
            logger.info(f"✓ Connection successful to '{namespace}' in '{container_name}'")
            return (
                True,
                f"Connection successful to namespace '{namespace}' in container '{container_name}'\n"
                "Database is accessible and responding to queries.",
            )

        # Check for common error patterns
        error_output = result.stderr or result.stdout

        if "namespace" in error_output.lower() or "does not exist" in error_output.lower():
            return (
                False,
                f"Namespace '{namespace}' does not exist in '{container_name}'\n"
                "\n"
                "What went wrong:\n"
                "  The specified namespace is not available.\n"
                "\n"
                "How to fix it:\n"
                "  1. List available namespaces:\n"
                f"     docker exec {container_name} iris session IRIS -U %SYS \"\"\"Do ^%GSIZE\"\"\"\n"
                "\n"
                "  2. Create the namespace if needed:\n"
                f"     docker exec {container_name} iris session IRIS -U %SYS\n"
                f"     Do ##class(Config.Namespaces).Create(\"{namespace}\")\n"
                "\n"
                "  3. Or use an existing namespace like 'USER' or '%SYS'\n",
            )

        # Generic connection failure
        return (
            False,
            f"Failed to connect to namespace '{namespace}' in '{container_name}'\n"
            "\n"
            "What went wrong:\n"
            f"  {error_output[:200]}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify IRIS is fully started:\n"
            f"     docker logs {container_name} | tail -20\n"
            "\n"
            "  2. Check if CallIn service is enabled (for DBAPI):\n"
            "     iris-devtester container enable-callin {container_name}\n"
            "\n"
            "  3. Test basic IRIS access:\n"
            f"     docker exec -it {container_name} iris session IRIS -U %SYS\n",
        )

    except subprocess.TimeoutExpired:
        return (
            False,
            f"Timeout ({timeout}s) testing connection to '{container_name}'\n"
            "\n"
            "What went wrong:\n"
            "  Docker command took too long to complete.\n"
            "\n"
            "How to fix it:\n"
            "  1. Check if IRIS is starting up:\n"
            f"     docker logs {container_name}\n"
            "\n"
            "  2. Wait for IRIS to fully start (~30 seconds)\n"
            "\n"
            "  3. Try again with longer timeout:\n"
            f"     test_connection('{container_name}', '{namespace}', timeout=30)\n",
        )

    except Exception as e:
        logger.error(f"Unexpected error testing connection: {e}")
        return (
            False,
            f"Unexpected error testing connection: {str(e)}\n"
            "\n"
            "What went wrong:\n"
            "  An unexpected error occurred during connection test.\n"
            "\n"
            "How to fix it:\n"
            "  1. Check Docker is running:\n"
            "     docker ps\n"
            "\n"
            "  2. Check container logs:\n"
            f"     docker logs {container_name}\n"
            "\n"
            "  3. File an issue at:\n"
            "     https://github.com/intersystems-community/iris-devtester/issues\n",
        )


__all__ = ["test_connection"]
