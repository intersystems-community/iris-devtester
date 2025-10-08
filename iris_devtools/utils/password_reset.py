"""
Password reset utility for InterSystems IRIS.

Automatically detects and remediates password change requirements.
Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
"""

import logging
import os
import subprocess
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def detect_password_change_required(error_message: str) -> bool:
    """
    Detect if error is due to password change requirement.

    Args:
        error_message: Error message from connection attempt

    Returns:
        True if password change is required

    Example:
        >>> error = "Connection failed: Password change required"
        >>> detect_password_change_required(error)
        True
        >>> error = "Connection refused"
        >>> detect_password_change_required(error)
        False
    """
    password_change_indicators = [
        "password change required",
        "password expired",
        "password_change_required",
        "user must change password",
    ]

    error_lower = error_message.lower()
    return any(indicator in error_lower for indicator in password_change_indicators)


def reset_password(
    container_name: str = "iris_db",
    username: str = "_SYSTEM",
    new_password: str = "SYS",
    timeout: int = 30,
) -> Tuple[bool, str]:
    """
    Reset IRIS password using Docker exec.

    Implements Constitutional Principle #1: Automatic remediation instead of
    telling the user to manually reset the password.

    Args:
        container_name: Name of IRIS Docker container (default: "iris_db")
        username: Username to reset (default: "_SYSTEM")
        new_password: New password (default: "SYS")
        timeout: Timeout in seconds for docker commands (default: 30)

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        >>> success, msg = reset_password("my_iris_container")
        >>> if success:
        ...     print("Password reset successful")

    Raises:
        None - always returns (bool, str) tuple for graceful handling
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

        # Step 2: Reset password using IRIS session
        logger.info(f"Resetting IRIS password for user '{username}'...")

        # Use ObjectScript to change password
        reset_cmd = [
            "docker",
            "exec",
            "-i",
            container_name,
            "iris",
            "session",
            "IRIS",
            "-U",
            "%SYS",
            f"##class(Security.Users).ChangePassword('{username}','{new_password}')",
        ]

        result = subprocess.run(
            reset_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=new_password + "\n",  # Provide current password if needed
        )

        if result.returncode == 0:
            # Update environment variables so subsequent connections use new password
            os.environ["IRIS_USERNAME"] = username
            os.environ["IRIS_PASSWORD"] = new_password

            # Wait for password change to propagate
            time.sleep(2)

            logger.info(f"✓ Password reset successful for user '{username}'")
            return True, f"Password reset successful for user '{username}'"

        # Step 3: Try alternative method using SQL
        logger.debug("Primary method failed, trying SQL approach...")

        alt_cmd = [
            "docker",
            "exec",
            "-i",
            container_name,
            "sh",
            "-c",
            f"echo \"ALTER USER {username} IDENTIFY BY '{new_password}'\" | iris sql IRIS -U %SYS",
        ]

        result = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=timeout)

        if (
            "error" not in result.stdout.lower()
            and "error" not in result.stderr.lower()
        ):
            os.environ["IRIS_USERNAME"] = username
            os.environ["IRIS_PASSWORD"] = new_password
            time.sleep(2)

            logger.info(f"✓ Password reset successful (via SQL) for user '{username}'")
            return True, f"Password reset successful (via SQL) for user '{username}'"

        # Both methods failed
        return (
            False,
            f"Password reset failed\n"
            "\n"
            "How to fix it manually:\n"
            f"  1. docker exec -it {container_name} bash\n"
            f"  2. iris session IRIS -U %SYS\n"
            f"  3. Do ##class(Security.Users).ChangePassword('{username}','{new_password}')\n"
            "\n"
            f"Primary error: {result.stderr}\n",
        )

    except subprocess.TimeoutExpired:
        return (
            False,
            f"Password reset timed out after {timeout} seconds\n"
            "\n"
            "What went wrong:\n"
            "  Docker command did not complete in time.\n"
            "\n"
            "How to fix it:\n"
            "  1. Check container health:\n"
            f"     docker logs {container_name}\n"
            "\n"
            "  2. Try with longer timeout:\n"
            f"     reset_password(container_name='{container_name}', timeout=60)\n",
        )

    except FileNotFoundError:
        return (
            False,
            "Docker command not found\n"
            "\n"
            "What went wrong:\n"
            "  Docker is not installed or not in PATH.\n"
            "\n"
            "How to fix it:\n"
            "  1. Install Docker:\n"
            "     https://docs.docker.com/get-docker/\n"
            "\n"
            "  2. Verify installation:\n"
            "     docker --version\n",
        )

    except Exception as e:
        return (
            False,
            f"Password reset failed: {str(e)}\n"
            "\n"
            "How to fix it manually:\n"
            f"  1. docker exec -it {container_name} bash\n"
            f"  2. iris session IRIS -U %SYS\n"
            f"  3. Do ##class(Security.Users).ChangePassword('{username}','{new_password}')\n",
        )


def reset_password_if_needed(
    error: Exception,
    container_name: str = "iris_db",
    max_retries: int = 1,
) -> bool:
    """
    Automatically detect and remediate password change requirement.

    This is the main entry point for automatic password reset. It:
    1. Detects if the error is a password change requirement
    2. Attempts to reset the password automatically
    3. Retries if needed
    4. Updates environment variables

    Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"

    Args:
        error: Exception from connection attempt
        container_name: Name of IRIS Docker container (default: "iris_db")
        max_retries: Maximum number of reset attempts (default: 1)

    Returns:
        True if password was reset successfully, False otherwise

    Example:
        >>> try:
        ...     conn = get_connection(config)
        ... except Exception as e:
        ...     if reset_password_if_needed(e):
        ...         conn = get_connection(config)  # Retry connection
    """
    error_msg = str(error)

    # Check if this is a password change error
    if not detect_password_change_required(error_msg):
        logger.debug("Error is not password-related, skipping reset")
        return False

    logger.warning("⚠️  IRIS password change required. Attempting automatic remediation...")

    # Attempt password reset with retries
    for attempt in range(max_retries):
        if attempt > 0:
            logger.info(f"Retry {attempt + 1}/{max_retries} for password reset...")
            time.sleep(3)

        success, message = reset_password(container_name=container_name)

        if success:
            logger.info(f"✓ {message}")
            logger.info("Connection should now work. Please retry your operation.")
            return True
        else:
            logger.error(f"✗ {message}")

            if attempt == max_retries - 1:
                # Last attempt failed
                logger.error("\nAutomatic password reset failed after all retries.")
                logger.error("Manual intervention may be required.")

    return False
