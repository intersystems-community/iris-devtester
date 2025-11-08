"""
CallIn service enablement utility for InterSystems IRIS.

Enables %Service_CallIn for DBAPI and embedded Python connectivity.
Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
"""

import logging
import subprocess
import time
from typing import Tuple

logger = logging.getLogger(__name__)

# Authentication method constants for IRIS services
# These values are bitmasks that can be combined
AUTHE_UNAUTHENTICATED = 0  # 0x00: No authentication
AUTHE_KERBEROS = 32  # 0x20: Kerberos authentication
AUTHE_PASSWORD = 16  # 0x10: Password authentication
AUTHE_PASSWORD_KERBEROS = 48  # 0x30: Password (0x10) + Kerberos (0x20) authentication

# Standard configuration for CallIn service
# Uses both Password and Kerberos to support maximum compatibility
DEFAULT_AUTHENABLED = AUTHE_PASSWORD_KERBEROS


def enable_callin_service(
    container_name: str = "iris_db",
    timeout: int = 30,
) -> Tuple[bool, str]:
    """
    Enable CallIn service for DBAPI and embedded Python connectivity.

    This utility automatically enables the %Service_CallIn service which is
    required for:
    - DBAPI (intersystems-irispython) connections
    - Embedded Python functionality
    - External language callouts

    Implements Constitutional Principle #1: Automatic remediation instead of
    telling the user to manually configure services.

    Args:
        container_name: Name of IRIS Docker container (default: "iris_db")
        timeout: Timeout in seconds for docker commands (default: 30)

    Returns:
        Tuple of (success: bool, message: str)
        - success: True if CallIn was enabled (or was already enabled)
        - message: Human-readable status message

    Example:
        >>> success, msg = enable_callin_service("my_iris_container")
        >>> if success:
        ...     print("CallIn service ready for DBAPI connections")

    Constitutional Compliance:
        - Principle #1: Automatic Remediation Over Manual Intervention
          Automatically enables service instead of error message
        - Principle #5: Fail Fast with Guidance
          Returns structured (bool, str) with remediation steps on failure

    Idempotent:
        Safe to call multiple times - if already enabled, returns success.
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
                "     docker ps | grep iris\n"
                "\n"
                "Documentation: See docs/learnings/callin-service-requirement.md\n",
            )

        # Step 2: Enable CallIn service using ObjectScript
        logger.info(f"Enabling CallIn service on container '{container_name}'...")

        # Use ObjectScript to modify %Service_CallIn:
        # - Set Enabled=1 (enable the service)
        # - Set AutheEnabled=DEFAULT_AUTHENABLED (Password + Kerberos authentication)
        #   DEFAULT_AUTHENABLED = 48 = 0x30 = AUTHE_PASSWORD (0x10) + AUTHE_KERBEROS (0x20)
        #   This supports both password-based and Kerberos authentication methods
        enable_cmd = [
            "docker",
            "exec",
            "-i",
            container_name,
            "bash",
            "-c",
            f'''echo "set prop(\\"Enabled\\")=1 set prop(\\"AutheEnabled\\")={DEFAULT_AUTHENABLED} write ##class(Security.Services).Modify(\\"%Service_CallIn\\",.prop)" | iris session IRIS -U %SYS''',
        ]

        result = subprocess.run(
            enable_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # ObjectScript returns "1" on successful modify
        if result.returncode == 0 and "1" in result.stdout:
            # Wait for service change to propagate
            time.sleep(1)

            logger.info(f"✓ CallIn service enabled on '{container_name}'")
            return (
                True,
                f"CallIn service enabled on container '{container_name}'\n"
                "Ready for DBAPI and embedded Python connections.",
            )

        # Check if it might have already been enabled (idempotent check)
        if result.returncode == 0:
            logger.debug("Service modify returned success, assuming already enabled")
            return (
                True,
                f"CallIn service configured on container '{container_name}' "
                "(may have already been enabled).",
            )

        # Step 3: If modify failed, provide detailed error
        error_output = result.stderr or result.stdout

        return (
            False,
            f"Failed to enable CallIn service on '{container_name}'\n"
            "\n"
            "What went wrong:\n"
            f"  ObjectScript command failed: {error_output[:200]}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify IRIS is fully started:\n"
            f"     docker logs {container_name} | tail -20\n"
            "\n"
            "  2. Try manually enabling CallIn:\n"
            f"     docker exec -it {container_name} iris session IRIS -U %SYS\n"
            "     Do ##class(Security.Services).Get(\"%Service_CallIn\",.prop)\n"
            "     Set prop(\"Enabled\")=1\n"
            "     Do ##class(Security.Services).Modify(\"%Service_CallIn\",.prop)\n"
            "\n"
            "  3. Check IRIS license (Community vs Enterprise):\n"
            "     docker exec {container_name} iris list\n"
            "\n"
            "Documentation: See docs/learnings/callin-service-requirement.md\n",
        )

    except subprocess.TimeoutExpired:
        return (
            False,
            f"Timeout ({timeout}s) enabling CallIn service on '{container_name}'\n"
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
            f"     enable_callin_service('{container_name}', timeout=60)\n",
        )

    except Exception as e:
        logger.error(f"Unexpected error enabling CallIn service: {e}")
        return (
            False,
            f"Unexpected error enabling CallIn service: {str(e)}\n"
            "\n"
            "What went wrong:\n"
            "  An unexpected error occurred during service enablement.\n"
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


__all__ = ["enable_callin_service"]
