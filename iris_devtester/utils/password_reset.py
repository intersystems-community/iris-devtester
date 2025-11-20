"""
Password reset utility for InterSystems IRIS.

Automatically detects and remediates password change requirements.
Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
"""

import logging
import os
import subprocess
import time
from typing import Optional, Tuple, Union

from iris_devtester.utils.password_verification import (
    PasswordResetResult,
    VerificationConfig,
    verify_password_via_connection,
)

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
    hostname: str = "localhost",
    port: int = 1972,
    namespace: str = "USER",
    verification_config: Optional[VerificationConfig] = None,
) -> Union[Tuple[bool, str], PasswordResetResult]:
    """
    Reset IRIS password using Docker exec with connection verification.

    Implements Constitutional Principle #1: Automatic remediation instead of
    telling the user to manually reset the password.

    **Feature 015 Enhancement**: Now verifies password via connection attempt
    with retry logic to handle macOS Docker Desktop timing delays (4-6s).

    Args:
        container_name: Name of IRIS Docker container (default: "iris_db")
        username: Username to reset (default: "_SYSTEM")
        new_password: New password (default: "SYS")
        timeout: Timeout in seconds for docker commands (default: 30)
        hostname: IRIS hostname for verification (default: "localhost")
        port: IRIS port for verification (default: 1972)
        namespace: IRIS namespace for verification (default: "USER")
        verification_config: Optional verification config (auto-creates if None)

    Returns:
        PasswordResetResult that can be unpacked as (bool, str) for backward compatibility.
        - result.success: True if password reset AND verified
        - result.message: Human-readable message with timing details
        - result.verification_attempts: Number of connection attempts made
        - result.elapsed_seconds: Total time from reset to verification

    Example:
        >>> # Backward compatible (unpacks to tuple)
        >>> success, msg = reset_password("my_iris_container")
        >>> if success:
        ...     print("Password reset successful")
        >>>
        >>> # New usage (with metadata)
        >>> result = reset_password("my_iris_container")
        >>> print(f"Success: {result.success}, Attempts: {result.verification_attempts}")

    Raises:
        None - always returns PasswordResetResult for graceful handling
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
            return PasswordResetResult(
                success=False,
                message=f"Container '{container_name}' not running\n"
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
                error_type="connection_refused",
                container_name=container_name,
                username=username
            )

        # Step 2: Reset password using IRIS session
        logger.info(f"Resetting IRIS password for user '{username}'...")

        # Use ObjectScript to change password AND set PasswordNeverExpires
        # CRITICAL FIX (Feature 007 + Bug #1): Use single-line ObjectScript with echo
        # This is the ONLY method that actually works reliably.
        # Pattern:
        # 1. Get() retrieves current properties
        # 2. Set Password property directly
        # 3. Set PasswordNeverExpires=1
        # 4. Modify() saves changes and returns status (1 = success)

        # Single-line ObjectScript (verified working in production)
        objectscript = (
            f'do ##class(Security.Users).Get(\\"{username}\\",.p) '
            f'set p(\\"Password\\")=\\"{new_password}\\" '
            f'set p(\\"PasswordNeverExpires\\")=1 '
            f'write ##class(Security.Users).Modify(\\"{username}\\",.p) '
            f'halt'
        )

        # Use echo pipe to iris session (verified working method)
        reset_cmd = [
            "docker",
            "exec",
            container_name,
            "bash",
            "-c",
            f'echo "{objectscript}" | iris session IRIS -U %SYS',
        ]

        logger.debug(f"Executing ObjectScript password reset for user '{username}'...")

        result = subprocess.run(
            reset_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        logger.debug(f"Password reset stdout: {result.stdout}")
        logger.debug(f"Password reset stderr: {result.stderr}")
        logger.debug(f"Password reset returncode: {result.returncode}")

        # Check for success: returncode 0 and "1" in output (Modify returns 1 on success)
        if result.returncode == 0 and "1" in result.stdout:
            logger.info(f"ObjectScript password reset succeeded for user '{username}'")
            logger.debug("Starting password verification with connection attempt...")

            # Feature 015: Verify password via connection with retry + exponential backoff
            # This handles macOS Docker Desktop's 4-6s networking delay
            if verification_config is None:
                verification_config = VerificationConfig()

            start_time = time.time()
            last_error_type = "unknown"
            last_error_message = ""

            # Retry loop with exponential backoff
            for attempt in range(1, verification_config.max_retries + 1):
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= (verification_config.timeout_ms / 1000.0):
                    logger.warning(f"Verification timeout after {elapsed:.2f}s")
                    return PasswordResetResult(
                        success=False,
                        message=f"Password verification timed out after {elapsed:.2f}s (NFR-004)",
                        verification_attempts=attempt - 1,
                        elapsed_seconds=elapsed,
                        error_type="timeout",
                        container_name=container_name,
                        username=username
                    )

                # Attempt verification
                verification_result = verify_password_via_connection(
                    hostname=hostname,
                    port=port,
                    namespace=namespace,
                    username=username,
                    password=new_password,
                    attempt_number=attempt,
                    config=verification_config
                )

                if verification_result.success:
                    # Success! Return immediately (early exit)
                    elapsed = time.time() - start_time
                    logger.info(
                        f"✓ Password verified in {elapsed:.2f}s "
                        f"(attempt {attempt}/{verification_config.max_retries})"
                    )
                    return PasswordResetResult(
                        success=True,
                        message=f"Password reset successful for user '{username}' "
                                f"(verified in {elapsed:.2f}s, attempt {attempt})",
                        verification_attempts=attempt,
                        elapsed_seconds=elapsed,
                        container_name=container_name,
                        username=username
                    )

                # Verification failed
                last_error_type = verification_result.error_type
                last_error_message = verification_result.error_message

                # Check if error is retryable
                if not verification_result.is_retryable:
                    # Non-retryable error: fail fast
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Non-retryable error on attempt {attempt}: {last_error_type}"
                    )
                    return PasswordResetResult(
                        success=False,
                        message=f"Password verification failed (non-retryable): {last_error_message}",
                        verification_attempts=attempt,
                        elapsed_seconds=elapsed,
                        error_type=last_error_type,
                        container_name=container_name,
                        username=username
                    )

                # Retryable error: wait and retry (if not last attempt)
                if attempt < verification_config.max_retries:
                    backoff_ms = verification_config.calculate_backoff_ms(attempt - 1)
                    backoff_s = backoff_ms / 1000.0
                    logger.debug(
                        f"Attempt {attempt} failed with {last_error_type}, "
                        f"retrying in {backoff_s}s..."
                    )
                    time.sleep(backoff_s)

            # All retries exhausted
            elapsed = time.time() - start_time
            logger.error(
                f"Password verification failed after {verification_config.max_retries} attempts "
                f"({elapsed:.2f}s)"
            )
            return PasswordResetResult(
                success=False,
                message=f"Password verification failed after {verification_config.max_retries} attempts "
                        f"({elapsed:.2f}s): {last_error_message}",
                verification_attempts=verification_config.max_retries,
                elapsed_seconds=elapsed,
                error_type=last_error_type,
                container_name=container_name,
                username=username
            )
        else:
            logger.warning(f"Primary method failed: returncode={result.returncode}, stdout={result.stdout[:100]}")
            # Fall through to try alternative method

        # Step 3: Try alternative method using ChangePassword (without Modify)
        logger.debug("Primary method failed, trying ChangePassword approach...")

        alt_cmd = [
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
            alt_cmd, capture_output=True, text=True, timeout=timeout, input=new_password + "\n"
        )

        if result.returncode == 0:
            # Also set PasswordNeverExpires=1 using correct IRIS Security API
            # CRITICAL FIX (Feature 007): Same fix as primary method
            set_never_expires_cmd = [
                "docker",
                "exec",
                "-i",
                container_name,
                "bash",
                "-c",
                f'''echo "set sc = ##class(Security.Users).Get(\\"{username}\\",.props) set props(\\"PasswordNeverExpires\\")=1 write ##class(Security.Users).Modify(\\"{username}\\",.props)" | iris session IRIS -U %SYS''',
            ]
            subprocess.run(set_never_expires_cmd, capture_output=True, text=True, timeout=timeout)

            logger.info(f"ObjectScript password reset succeeded (via ChangePassword) for user '{username}'")
            logger.debug("Starting password verification with connection attempt...")

            # Feature 015: Verify password via connection instead of time.sleep(2)
            if verification_config is None:
                verification_config = VerificationConfig()

            start_time = time.time()
            verification_result = verify_password_via_connection(
                hostname=hostname,
                port=port,
                namespace=namespace,
                username=username,
                password=new_password,
                attempt_number=1,
                config=verification_config
            )

            elapsed = time.time() - start_time

            if verification_result.success:
                logger.info(
                    f"✓ Password verified in {elapsed:.2f}s "
                    f"(attempt {verification_result.attempt_number}, via ChangePassword)"
                )
                return PasswordResetResult(
                    success=True,
                    message=f"Password reset successful (via ChangePassword) for user '{username}' "
                            f"(verified in {elapsed:.2f}s, attempt {verification_result.attempt_number})",
                    verification_attempts=verification_result.attempt_number,
                    elapsed_seconds=elapsed,
                    container_name=container_name,
                    username=username
                )
            else:
                logger.warning(
                    f"Password reset succeeded but verification failed: "
                    f"{verification_result.error_type}"
                )
                return PasswordResetResult(
                    success=False,
                    message=f"Password reset succeeded but verification failed after {elapsed:.2f}s: "
                            f"{verification_result.error_message}",
                    verification_attempts=verification_result.attempt_number,
                    elapsed_seconds=elapsed,
                    error_type=verification_result.error_type,
                    container_name=container_name,
                    username=username
                )

        # Both methods failed
        return PasswordResetResult(
            success=False,
            message=f"Password reset failed\n"
                    "\n"
                    "How to fix it manually:\n"
                    f"  1. docker exec -it {container_name} bash\n"
                    f"  2. iris session IRIS -U %SYS\n"
                    f"  3. Set props(\"ChangePassword\")=0 Set props(\"ExternalPassword\")=\"{new_password}\" Write ##class(Security.Users).Modify(\"{username}\",.props)\n"
                    "\n"
                    f"Primary error: {result.stderr}\n",
            error_type="verification_failed",
            container_name=container_name,
            username=username
        )

    except subprocess.TimeoutExpired:
        return PasswordResetResult(
            success=False,
            message=f"Password reset timed out after {timeout} seconds\n"
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
            error_type="timeout",
            container_name=container_name,
            username=username
        )

    except FileNotFoundError:
        return PasswordResetResult(
            success=False,
            message="Docker command not found\n"
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
            error_type="unknown",
            container_name=container_name,
            username=username
        )

    except Exception as e:
        return PasswordResetResult(
            success=False,
            message=f"Password reset failed: {str(e)}\n"
                    "\n"
                    "How to fix it manually:\n"
                    f"  1. docker exec -it {container_name} bash\n"
                    f"  2. iris session IRIS -U %SYS\n"
                    f"  3. Set props(\"ChangePassword\")=0 Set props(\"ExternalPassword\")=\"{new_password}\" Write ##class(Security.Users).Modify(\"{username}\",.props)\n",
            error_type="unknown",
            container_name=container_name,
            username=username
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
