"""
Consolidated IRIS password management utilities.

This module provides all password-related functions for IRIS containers:
- Password reset via Docker exec
- Password verification via connection
- Password unexpiration for test/benchmark containers

The preferred approach is to use IRIS_PASSWORD environment variable at container
startup, which configures the password without any post-startup intervention.

Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
Constitutional Principle #5: Fail Fast with Guidance
Constitutional Principle #7: Medical-Grade Reliability
"""

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

ErrorType = Literal[
    "timeout",
    "access_denied",
    "connection_refused",
    "verification_failed",
    "network_error",
    "stuck_state",
    "unknown",
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PasswordResult:
    """
    Result of a password operation (reset, verify, unexpire).

    Supports backward compatibility via tuple unpacking:
        success, message = result  # Works like Tuple[bool, str]

    Fields:
        success: Whether the operation succeeded
        message: Human-readable success/failure message
        attempts: Number of attempts made
        elapsed_seconds: Total time elapsed
        error_type: Error classification if failed
        container_name: Name of IRIS container
        username: Username affected
    """

    success: bool
    message: str
    attempts: int = 0
    elapsed_seconds: float = 0.0
    error_type: Optional[ErrorType] = None
    container_name: str = ""
    username: str = ""

    def __post_init__(self):
        """Validate dataclass fields."""
        if self.attempts < 0:
            raise ValueError(f"attempts must be >= 0, got {self.attempts}")
        if self.elapsed_seconds < 0.0:
            raise ValueError(f"elapsed_seconds must be >= 0.0, got {self.elapsed_seconds}")
        if self.success and self.error_type is not None:
            raise ValueError("error_type must be None when success=True")
        if not self.success and self.error_type is None:
            self.error_type = "unknown"

    def __iter__(self):
        """Support backward compatibility via tuple unpacking."""
        return iter((self.success, self.message))


@dataclass
class VerificationConfig:
    """
    Configuration for password verification.

    Optimized defaults for macOS Docker Desktop (15-20s total delay needed).

    Fields:
        max_retries: Maximum number of connection verification attempts
        initial_backoff_ms: Initial wait time in milliseconds before first retry
        timeout_ms: Hard timeout in milliseconds for verification process
        exponential_backoff: Use exponential backoff (recommended)
    """

    max_retries: int = 5
    initial_backoff_ms: int = 1000
    timeout_ms: int = 10000
    exponential_backoff: bool = True


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# These aliases maintain backward compatibility with old imports
PasswordResetResult = PasswordResult
VerificationResult = PasswordResult


# =============================================================================
# Password Detection
# =============================================================================


def detect_password_change_required(error_message: str) -> bool:
    """
    Detect if an error message indicates a password change is required.

    Args:
        error_message: Error message from connection attempt

    Returns:
        True if password change is required
    """
    msg = error_message.lower()
    indicators = [
        "password change required",
        "change password",
        "required to change password",
        "password expired",
        "<853>",  # SQLCODE for password change required
    ]
    return any(indicator in msg for indicator in indicators)


# =============================================================================
# Password Verification
# =============================================================================


def verify_password(
    hostname: str,
    port: int,
    namespace: str,
    username: str,
    password: str,
    config: Optional[VerificationConfig] = None,
) -> PasswordResult:
    """
    Verify password works by attempting a real connection.

    Implements robust retry with backoff to handle macOS networking delay.

    Args:
        hostname: IRIS host
        port: IRIS port
        namespace: IRIS namespace
        username: Username to test
        password: Password to test
        config: Verification configuration

    Returns:
        PasswordResult indicating success/failure
    """
    if config is None:
        config = VerificationConfig()

    start_time = time.time()
    last_error = ""
    last_error_type: ErrorType = "unknown"

    for attempt in range(1, config.max_retries + 1):
        try:
            # Try DBAPI connection
            try:
                import iris

                conn = iris.connect(
                    hostname=hostname,
                    port=port,
                    namespace=namespace,
                    username=username,
                    password=password,
                    timeout=5,
                )
                conn.close()
                return PasswordResult(
                    success=True,
                    message="Password verified successfully",
                    attempts=attempt,
                    elapsed_seconds=time.time() - start_time,
                    username=username,
                )
            except ImportError:
                # Fallback to connection manager if iris package not found
                from iris_devtester.config import IRISConfig
                from iris_devtester.connections.dbapi import create_dbapi_connection

                cfg = IRISConfig(
                    host=hostname,
                    port=port,
                    namespace=namespace,
                    username=username,
                    password=password,
                )
                conn = create_dbapi_connection(cfg)
                conn.close()
                return PasswordResult(
                    success=True,
                    message="Password verified successfully",
                    attempts=attempt,
                    elapsed_seconds=time.time() - start_time,
                    username=username,
                )

        except Exception as e:
            last_error = str(e)
            error_msg = last_error.lower()

            if "access denied" in error_msg:
                last_error_type = "access_denied"
            elif "connection refused" in error_msg:
                last_error_type = "connection_refused"
            elif "timeout" in error_msg:
                last_error_type = "timeout"
            else:
                last_error_type = "unknown"

            # Check hard timeout
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > config.timeout_ms:
                return PasswordResult(
                    success=False,
                    message=f"Timeout after {elapsed_ms:.0f}ms: {last_error}",
                    attempts=attempt,
                    elapsed_seconds=time.time() - start_time,
                    error_type="timeout",
                    username=username,
                )

            # Wait for backoff
            if attempt < config.max_retries:
                backoff_ms = config.initial_backoff_ms
                if config.exponential_backoff:
                    backoff_ms = config.initial_backoff_ms * (2 ** (attempt - 1))

                logger.debug(
                    f"Verification attempt {attempt} failed ({last_error_type}). "
                    f"Retrying in {backoff_ms}ms..."
                )
                time.sleep(backoff_ms / 1000.0)

    return PasswordResult(
        success=False,
        message=f"Verification failed after {config.max_retries} attempts: {last_error}",
        attempts=config.max_retries,
        elapsed_seconds=time.time() - start_time,
        error_type=last_error_type,
        username=username,
    )


# Backward compatibility alias
verify_password_via_connection = verify_password


# =============================================================================
# Password Reset
# =============================================================================


def reset_password(
    container_name: str = "iris_db",
    username: str = "_SYSTEM",
    new_password: str = "SYS",
    timeout: int = 30,
    hostname: Optional[str] = None,
    port: int = 1972,
    namespace: str = "USER",
    verify: bool = True,
    verification_config: Optional[VerificationConfig] = None,
) -> PasswordResult:
    """
    Reset IRIS user password via Docker exec and optionally verify.

    Implements medical-grade reliability by:
    1. Resetting password via docker exec (ObjectScript)
    2. Clearing password expiration flags
    3. Optionally verifying the new password works via connection

    Args:
        container_name: Docker container name or ID
        username: IRIS username to reset
        new_password: New password to set
        timeout: Total timeout in seconds
        hostname: Hostname for verification (defaults to localhost)
        port: Port for verification
        namespace: Namespace for verification
        verify: Whether to verify password works after reset
        verification_config: Configuration for verification attempts

    Returns:
        PasswordResult indicating success/failure and details
    """
    start_time = time.time()

    # ObjectScript to reset password and clear flags
    objectscript_commands = f"""
Set user = "{username}"
Set password = "{new_password}"
Set sc = ##class(Security.Users).Get(user, .p)
If 'sc Write "FAILED:User not found" Halt
Set p("PasswordExternal") = password
Set p("ChangePassword") = 0
Set p("PasswordNeverExpires") = 1
Set sc = ##class(Security.Users).Modify(user, .p)
If 'sc Write "FAILED:"_$System.Status.GetErrorText(sc) Halt
Write "SUCCESS"
Halt
"""

    try:
        # Check if container is running first
        check_cmd = [
            "docker",
            "ps",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Names}}",
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
        if container_name not in result.stdout:
            return PasswordResult(
                success=False,
                message=(
                    f"Container '{container_name}' not running\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Start the container: docker-compose up -d\n"
                    f"  2. Or start manually: docker start {container_name}\n"
                    "  3. Verify it's running: docker ps | grep iris"
                ),
                error_type="unknown",
                container_name=container_name,
                username=username,
            )

        # Run the reset script
        cmd = [
            "docker",
            "exec",
            "-i",
            container_name,
            "iris",
            "session",
            "IRIS",
            "-U",
            "%SYS",
        ]

        reset_result = subprocess.run(
            cmd,
            input=objectscript_commands.encode("utf-8"),
            capture_output=True,
            timeout=15,
        )

        stdout = reset_result.stdout.decode("utf-8", errors="replace")
        if "SUCCESS" not in stdout:
            return PasswordResult(
                success=False,
                message=f"IRIS reset command failed: {stdout}\n{reset_result.stderr.decode()}",
                error_type="verification_failed",
                container_name=container_name,
                username=username,
            )

        # Optionally verify password works
        if verify:
            verify_host = hostname or "localhost"
            verify_result = verify_password(
                hostname=verify_host,
                port=port,
                namespace=namespace,
                username=username,
                password=new_password,
                config=verification_config,
            )

            if verify_result.success:
                return PasswordResult(
                    success=True,
                    message=f"Password for '{username}' reset and verified successfully",
                    attempts=verify_result.attempts,
                    elapsed_seconds=time.time() - start_time,
                    container_name=container_name,
                    username=username,
                )
            else:
                return PasswordResult(
                    success=False,
                    message=(
                        f"Password reset succeeded but verification failed: "
                        f"{verify_result.message}"
                    ),
                    error_type=verify_result.error_type or "verification_failed",
                    attempts=verify_result.attempts,
                    elapsed_seconds=time.time() - start_time,
                    container_name=container_name,
                    username=username,
                )
        else:
            return PasswordResult(
                success=True,
                message=f"Password for '{username}' reset successfully (not verified)",
                elapsed_seconds=time.time() - start_time,
                container_name=container_name,
                username=username,
            )

    except subprocess.TimeoutExpired:
        return PasswordResult(
            success=False,
            message=f"Password reset timed out after {timeout}s",
            error_type="timeout",
            container_name=container_name,
            username=username,
        )
    except FileNotFoundError:
        return PasswordResult(
            success=False,
            message="Docker command not found in PATH",
            error_type="unknown",
            container_name=container_name,
            username=username,
        )
    except Exception as e:
        return PasswordResult(
            success=False,
            message=f"Unexpected error during password reset: {str(e)}",
            error_type="unknown",
            container_name=container_name,
            username=username,
        )


def reset_password_if_needed(
    error: Exception,
    container_name: Optional[str] = None,
    username: str = "_SYSTEM",
    new_password: str = "SYS",
    max_retries: int = 1,
) -> bool:
    """
    Reset password automatically if change is required.

    Args:
        error: Exception from connection attempt
        container_name: Optional container name (auto-discovers if None)
        username: Username to reset
        new_password: New password to set
        max_retries: Maximum reset attempts

    Returns:
        True if password was successfully reset
    """
    error_msg = str(error)

    if not detect_password_change_required(error_msg):
        logger.debug("Error is not password-related, skipping reset")
        return False

    # Auto-discover container name if not provided
    actual_container = container_name
    if not actual_container:
        try:
            import docker

            client = docker.from_env()
            containers = client.containers.list(filters={"status": "running"})
            for c in containers:
                if "iris" in c.name.lower():
                    actual_container = c.name
                    logger.info(f"Discovered IRIS container: {actual_container}")
                    break
        except Exception:
            pass

        if not actual_container:
            actual_container = "iris_db"  # Final default fallback

    logger.warning(
        f"IRIS password change required for '{actual_container}'. "
        "Attempting automatic remediation..."
    )

    for attempt in range(max_retries):
        if attempt > 0:
            logger.info(f"Retry {attempt + 1}/{max_retries} for password reset...")
            time.sleep(3)

        result = reset_password(
            container_name=actual_container,
            username=username,
            new_password=new_password,
        )

        if result.success:
            logger.info(f"Password reset successful: {result.message}")
            return True
        else:
            logger.error(f"Password reset failed: {result.message}")

    return False


# =============================================================================
# Password Unexpiration
# =============================================================================


def unexpire_all_passwords(container_name: str = "iris_db", timeout: int = 30) -> Tuple[bool, str]:
    """
    Unexpire all passwords in IRIS container.

    This is commonly needed for:
    - Benchmark containers that need to run without interaction
    - Test containers that get reused
    - CI/CD pipelines
    - Multi-container setups (pgwire, embedded, etc.)

    Args:
        container_name: Name of IRIS Docker container
        timeout: Timeout in seconds for docker commands (default: 30)

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        >>> unexpire_all_passwords("iris-4way")
        >>> unexpire_all_passwords("iris-4way-embedded")
    """
    try:
        objectscript_commands = """
Set rs=##class(%ResultSet).%New("Security.Users:List")
Do rs.Execute()
While rs.Next() {
    Set user=rs.Get("Name")
    Set sc=##class(Security.Users).Get(user,.p)
    If $$$ISOK(sc) {
        Set p("PasswordNeverExpires")=1
        Set p("ChangePassword")=0
        Do ##class(Security.Users).Modify(user,.p)
    }
}
Do ##class(Security.Users).UnExpireUserPasswords("*")
Write "UNEXPIRED"
Halt
"""

        cmd = [
            "docker",
            "exec",
            container_name,
            "sh",
            "-c",
            f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
        ]

        logger.info(f"Unexpiring passwords in container: {container_name}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        if result.returncode == 0 and "UNEXPIRED" in result.stdout:
            logger.info(f"Passwords unexpired in {container_name}")
            return True, f"Passwords unexpired successfully in {container_name}"
        else:
            return (
                False,
                f"Failed to unexpire passwords in {container_name}\n"
                f"stderr: {result.stderr}\n"
                f"stdout: {result.stdout}",
            )

    except subprocess.TimeoutExpired:
        return (
            False,
            f"Timeout unexpiring passwords in {container_name} after {timeout}s\n"
            "\n"
            "How to fix it:\n"
            f"  1. Check container is running:\n"
            f"     docker ps | grep {container_name}\n"
            "\n"
            f"  2. Check container logs:\n"
            f"     docker logs {container_name}\n"
            "\n"
            f"  3. Try with longer timeout:\n"
            f"     unexpire_all_passwords('{container_name}', timeout=60)\n",
        )

    except FileNotFoundError:
        return (
            False,
            "Docker command not found\n"
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
            f"Failed to unexpire passwords in {container_name}: {str(e)}\n"
            "\n"
            "Manual fix:\n"
            f"  docker exec {container_name} bash -c 'echo \"do ##class(Security.Users)"
            f'.UnExpireUserPasswords(\\"*\\")" | iris session IRIS -U %SYS\'\n',
        )


def unexpire_passwords_for_containers(
    container_names: List[str], timeout: int = 30, fail_fast: bool = False
) -> Dict[str, Tuple[bool, str]]:
    """
    Unexpire passwords for multiple IRIS containers.

    Perfect for multi-container benchmark setups like pgwire 4-way benchmarks.

    Args:
        container_names: List of container names to process
        timeout: Timeout per container in seconds (default: 30)
        fail_fast: Stop on first failure (default: False, process all)

    Returns:
        Dictionary mapping container_name -> (success, message)

    Example:
        >>> results = unexpire_passwords_for_containers([
        ...     "iris-4way",
        ...     "iris-4way-embedded",
        ... ])
    """
    results = {}

    for container_name in container_names:
        success, message = unexpire_all_passwords(container_name, timeout)
        results[container_name] = (success, message)

        if not success and fail_fast:
            logger.error(f"Stopping due to failure on {container_name}")
            break

    successes = sum(1 for s, _ in results.values() if s)
    failures = len(results) - successes

    if failures == 0:
        logger.info(f"All {successes} containers: passwords unexpired")
    else:
        logger.warning(f"Password unexpiration: {successes} succeeded, {failures} failed")

    return results
