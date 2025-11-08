"""
Container status reporting utility for InterSystems IRIS.

Aggregates comprehensive status information from multiple checks.
Implements Constitutional Principle #4: "Zero Configuration Viable"
"""

import logging
import subprocess
from typing import Tuple

from .test_connection import test_connection

logger = logging.getLogger(__name__)


def get_container_status(
    container_name: str = "iris_db",
) -> Tuple[bool, str]:
    """
    Get comprehensive status of IRIS container.

    Aggregates status from multiple checks:
    - Container running status (docker ps)
    - Container health check (docker inspect)
    - Connection test to USER namespace

    Args:
        container_name: Name of IRIS Docker container (default: "iris_db")

    Returns:
        Tuple of (success: bool, message: str)
        - success: True if container running and accessible
        - message: Multi-line formatted status report

    Example:
        >>> success, status = get_container_status("my_iris")
        >>> print(status)
        Container Status: my_iris
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        Running:    ✓ Yes
        Health:     ✓ healthy
        Connection: ✓ USER namespace accessible

    Constitutional Compliance:
        - Principle #4: Zero Configuration Viable
          Auto-discovers all status without configuration
        - Principle #5: Fail Fast with Guidance
          Clear status with remediation if issues found
        - Principle #7: Medical-Grade Reliability
          Non-destructive read-only checks
    """
    try:
        status_lines = []
        overall_success = True

        # Header
        status_lines.append(f"Container Status: {container_name}")
        status_lines.append("━" * 40)

        # Step 1: Check if container is running
        logger.debug(f"Checking running status for '{container_name}'...")

        check_cmd = [
            "docker",
            "ps",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Names}}",
        ]

        result = subprocess.run(
            check_cmd, capture_output=True, text=True, timeout=10
        )

        if container_name in result.stdout:
            status_lines.append("Running:    ✓ Yes")
        else:
            status_lines.append("Running:    ✗ No")
            overall_success = False
            status_lines.append("")
            status_lines.append("How to fix:")
            status_lines.append(f"  docker start {container_name}")
            status_lines.append("  # or")
            status_lines.append("  docker-compose up -d")

            return (False, "\n".join(status_lines))

        # Step 2: Check container health
        logger.debug(f"Checking health status for '{container_name}'...")

        health_cmd = [
            "docker",
            "inspect",
            "--format",
            "{{.State.Health.Status}}",
            container_name,
        ]

        result = subprocess.run(
            health_cmd, capture_output=True, text=True, timeout=10
        )

        health_status = result.stdout.strip()
        if health_status and health_status != "<no value>":
            if "healthy" in health_status:
                status_lines.append(f"Health:     ✓ {health_status}")
            else:
                status_lines.append(f"Health:     ⚠ {health_status}")
                if health_status == "starting":
                    status_lines.append("            (container still initializing)")
        else:
            # No health check configured
            status_lines.append("Health:     - No healthcheck")

        # Step 3: Test connection to USER namespace
        logger.debug(f"Testing connection to '{container_name}'...")

        conn_success, conn_msg = test_connection(container_name, "USER", timeout=10)

        if conn_success:
            status_lines.append("Connection: ✓ USER namespace accessible")
        else:
            status_lines.append("Connection: ✗ Failed")
            overall_success = False
            status_lines.append("")
            status_lines.append("Connection Error:")
            # Include first line of error for context
            first_error_line = conn_msg.split("\n")[0] if conn_msg else "Unknown error"
            status_lines.append(f"  {first_error_line}")
            status_lines.append("")
            status_lines.append("How to fix:")
            status_lines.append("  # Enable CallIn service:")
            status_lines.append(f"  iris-devtester container enable-callin {container_name}")
            status_lines.append("")
            status_lines.append("  # Check logs:")
            status_lines.append(f"  docker logs {container_name} | tail -20")

        # Step 4: Summary
        status_lines.append("")
        if overall_success:
            status_lines.append("Overall: ✓ Container healthy and accessible")
        else:
            status_lines.append("Overall: ✗ Issues detected (see above)")

        return (overall_success, "\n".join(status_lines))

    except subprocess.TimeoutExpired:
        return (
            False,
            f"Timeout checking status of '{container_name}'\n"
            "\n"
            "What went wrong:\n"
            "  Docker commands took too long to complete.\n"
            "\n"
            "How to fix it:\n"
            "  1. Check if Docker is responding:\n"
            "     docker ps\n"
            "\n"
            "  2. Restart Docker Desktop if needed\n",
        )

    except Exception as e:
        logger.error(f"Unexpected error checking container status: {e}")
        return (
            False,
            f"Unexpected error checking container status: {str(e)}\n"
            "\n"
            "What went wrong:\n"
            "  An unexpected error occurred.\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify Docker is running:\n"
            "     docker --version\n"
            "\n"
            "  2. Check if container exists:\n"
            f"     docker ps -a | grep {container_name}\n"
            "\n"
            "  3. File an issue at:\n"
            "     https://github.com/intersystems-community/iris-devtester/issues\n",
        )


__all__ = ["get_container_status"]
