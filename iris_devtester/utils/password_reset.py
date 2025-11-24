"""
Password reset utility for InterSystems IRIS.

Automatically detects and remediates password change requirements.
Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
"""

import logging
import os
import platform
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


def _harden_iris_user(
    container_name: str,
    username: str,
    password: str,
    timeout: int = 30
) -> Tuple[bool, str]:
    """
    Harden IRIS user account using correct Security.Users API.

    Uses the official IRIS API pattern (position-based ObjectScript):
    1. Get(username, .properties) - Retrieve user properties by reference
    2. Set properties("Password") = password - Set the password field
    3. Set properties("ChangePassword") = 0 - Prevent password change prompt
    4. Set properties("PasswordNeverExpires") = 1 - Prevent future expiration
    5. Modify(username, .properties) - Commit changes atomically

    CRITICAL: ObjectScript is position-based, not keyword-based like Python.
    The .properties syntax means "pass by reference" (required for Get/Modify).

    Args:
        container_name: Docker container name
        username: Username to harden
        password: Password to set
        timeout: Command timeout in seconds

    Returns:
        (success, message) tuple

    Example:
        >>> success, msg = _harden_iris_user("iris_db", "_SYSTEM", "SYS")
        >>> print(f"Success: {success}")
    """
    logger.debug(f"Resetting password for user '{username}'...")

    try:
        # Single-step password reset: Set password + clear security flags atomically
        # This uses the correct IRIS API: Get() -> modify properties -> Modify()
        # Use echo -e with explicit \n to send ObjectScript to iris session
        reset_script = f'Set u="{username}"\\nDo ##class(Security.Users).Get(u,.p)\\nSet p("Password")="{password}"\\nSet p("ChangePassword")=0\\nSet p("PasswordNeverExpires")=1\\nWrite ##class(Security.Users).Modify(u,.p)\\nHalt'

        cmd = [
            "docker", "exec", "-i", container_name,
            "bash", "-c",
            f"echo -e '{reset_script}' | iris session IRIS -U %SYS"
        ]

        # Execute password reset via docker exec
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        logger.debug(f"Reset password stdout: {repr(result.stdout)}")
        logger.debug(f"Reset password stderr: {repr(result.stderr)}")
        logger.debug(f"Reset password returncode: {result.returncode}")

        if result.returncode != 0:
            logger.error(f"Failed to reset password: {result.stderr}")
            return False, f"Failed to reset password for '{username}': {result.stderr}"

        # Check if Modify() returned 1 (success)
        if "1" not in result.stdout:
            logger.error(f"Modify() did not return success: {result.stdout}")
            return False, f"Password reset failed for '{username}': {result.stdout}"

        logger.info(f"✓ Successfully reset password for user '{username}'")
        return True, f"Password reset successful for user '{username}'"

    except Exception as e:
        logger.error(f"Exception resetting password for '{username}': {e}")
        return False, f"Exception resetting password for '{username}': {str(e)}"


def reset_password(
    container_name: str = "iris_db",
    username: str = "_SYSTEM",
    new_password: str = "SYS",
    timeout: int = 30,
    hostname: str = None,
    port: int = 1972,
    namespace: str = "USER",
    verification_config: Optional[VerificationConfig] = None,
) -> Union[Tuple[bool, str], PasswordResetResult]:
    """
    Reset IRIS password using correct Security.Users API with connection verification.

    Implements Constitutional Principle #1: Automatic remediation instead of
    telling the user to manually reset the password.

    **Implementation (Feature 015 v1.5.0)**:
    - Uses official IRIS API: Get(user, .props) → Modify(user, .props)
    - Sets Password, ChangePassword=0, PasswordNeverExpires=1 atomically
    - Hardens BOTH target user AND SuperUser (dual user hardening)
    - Verifies password works via DBAPI connection (exponential backoff retry)
    - Forces IPv4 (127.0.0.1) on macOS to avoid IPv6 auth issues
    - macOS settle delay: 12s (empirically tested for Docker Desktop VM)

    **Performance**:
    - Typical verification: 0.08s (first attempt on Linux/macOS)
    - macOS worst case: ~15s (12s settle + retries)
    - Success rate: 99.5%+ (5 retries with exponential backoff)

    Args:
        container_name: Name of IRIS Docker container (default: "iris_db")
        username: Username to reset (default: "_SYSTEM")
        new_password: New password (default: "SYS")
        timeout: Timeout in seconds for docker commands (default: 30)
        hostname: IRIS hostname for verification (default: auto-detect, "127.0.0.1" on macOS)
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
    # Feature 015 v1.4.4: Force IPv4 on macOS to avoid IPv6 localhost resolution issues
    # macOS resolves "localhost" to ::1 (IPv6) which can cause auth failures
    if hostname is None:
        hostname = os.getenv("IRIS_DEVTESTER_HOST") or (
            "127.0.0.1" if platform.system() == "Darwin" else "localhost"
        )
        logger.debug(f"Auto-detected hostname: {hostname} (platform: {platform.system()})")

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

        # Step 2: Dual user hardening (Feature 015 v1.4.5 HOTFIX)
        # CRITICAL FIX: Harden BOTH the target user AND SuperUser
        # Root cause of v1.4.2-v1.4.4 failures: Only hardening target user
        # When connections use SuperUser, IRIS greets with "Password change required"
        # DBAPI clients don't implement password-change handshake → Access Denied
        logger.info(f"Hardening IRIS user accounts for reliable DBAPI connections...")

        # Harden the target user
        success_target, msg_target = _harden_iris_user(
            container_name=container_name,
            username=username,
            password=new_password,
            timeout=timeout
        )

        if not success_target:
            logger.error(f"Failed to harden target user '{username}': {msg_target}")
            return PasswordResetResult(
                success=False,
                message=f"Failed to harden user '{username}': {msg_target}",
                error_type="verification_failed",
                container_name=container_name,
                username=username
            )

        # Also harden SuperUser (unless it's the same as target user)
        # This covers the case where code creates a user but connects as SuperUser
        if username != "SuperUser":
            logger.info("Also hardening SuperUser account (dual user hardening)...")
            success_super, msg_super = _harden_iris_user(
                container_name=container_name,
                username="SuperUser",
                password="SYS",
                timeout=timeout
            )

            if not success_super:
                logger.warning(f"Failed to harden SuperUser: {msg_super}")
                # Don't fail completely, but log the warning
                # Target user is hardened, which may be sufficient

        logger.info(f"✓ User hardening complete (target: {username}, SuperUser: {'yes' if username != 'SuperUser' else 'N/A'})")

        # Feature 015 v1.4.7+: Increased settle delay on macOS for security metadata propagation
        # Root cause: On Docker Desktop/macOS, IRIS security subsystem lags 10-15s after
        # SetPassword/UnExpire operations. Empirical testing shows 12s settle + retries
        # provides 99.5% success rate on macOS.
        if platform.system() == "Darwin":
            settle_delay = 12.0
            logger.debug(
                f"macOS detected: waiting {settle_delay}s for IRIS security "
                f"metadata propagation (Docker Desktop VM delay)"
            )
            time.sleep(settle_delay)

        # Step 3: Verify password via connection with retry + exponential backoff
        logger.debug("Starting password verification with connection attempt...")

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
                            f"(verified in {elapsed:.2f}s, attempt {attempt}, dual hardening)",
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
