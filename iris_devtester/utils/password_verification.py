"""
Password verification utilities for InterSystems IRIS.

Provides connection-based verification of password changes with retry logic.
Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
"""

import logging
import time
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

logger = logging.getLogger(__name__)


ErrorType = Literal[
    "timeout",
    "access_denied",
    "connection_refused",
    "verification_failed",
    "network_error",
    "unknown"
]


@dataclass
class PasswordResetResult:
    """
    Complete result of password reset operation with verification.

    Supports backward compatibility via tuple unpacking:
        success, message = result  # Works like Tuple[bool, str]

    Fields:
        success: Whether password was reset AND verified successfully
        message: Human-readable success/failure message with timing details
        verification_attempts: Number of connection verification attempts made
        elapsed_seconds: Total time elapsed from reset to verification
        error_type: Error classification if failed
        container_name: Name of IRIS container where password was reset
        username: Username whose password was reset

    Example:
        >>> result = PasswordResetResult(
        ...     success=True,
        ...     message="Password verified in 3.2s (attempt 2)",
        ...     verification_attempts=2,
        ...     elapsed_seconds=3.2
        ... )
        >>> # Backward compatible unpacking
        >>> success, message = result
        >>> print(f"Success: {success}, Message: {message}")
    """

    success: bool
    message: str
    verification_attempts: int = 0
    elapsed_seconds: float = 0.0
    error_type: Optional[ErrorType] = None
    container_name: str = ""
    username: str = ""

    def __post_init__(self):
        """Validate dataclass fields."""
        if self.verification_attempts < 0:
            raise ValueError(f"verification_attempts must be >= 0, got {self.verification_attempts}")
        if self.elapsed_seconds < 0.0:
            raise ValueError(f"elapsed_seconds must be >= 0.0, got {self.elapsed_seconds}")
        if self.success and self.error_type is not None:
            raise ValueError("error_type must be None when success=True")
        if not self.success and self.error_type is None:
            # Auto-set error_type if not provided
            self.error_type = "unknown"

    def __iter__(self):
        """Support backward compatibility via tuple unpacking."""
        return iter((self.success, self.message))


@dataclass
class VerificationConfig:
    """
    Configuration for password reset verification.

    Optimized defaults for macOS Docker Desktop (15-20s total delay needed).

    Fields:
        max_retries: Maximum number of connection verification attempts
        initial_backoff_ms: Initial wait time in milliseconds before first retry
        timeout_ms: Hard timeout in milliseconds for verification process (NFR-004)
        exponential_backoff: Use exponential backoff (recommended)
        verify_via_dbapi: Use DBAPI connection for verification (faster)

    Example:
        >>> # Default config (macOS optimized)
        >>> config = VerificationConfig()
        >>>
        >>> # Custom config for extra slow systems
        >>> slow_config = VerificationConfig(
        ...     max_retries=7,
        ...     timeout_ms=45000
        ... )
    """

    max_retries: int = 5
    initial_backoff_ms: int = 2000  # 2s initial backoff for macOS Docker Desktop
    timeout_ms: int = 35000  # 35s allows all 5 retries with exponential backoff (2+4+8+16=30s)
    exponential_backoff: bool = True
    verify_via_dbapi: bool = True

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.initial_backoff_ms <= 0:
            raise ValueError(f"initial_backoff_ms must be > 0, got {self.initial_backoff_ms}")
        if self.timeout_ms <= 0:
            raise ValueError(f"timeout_ms must be > 0, got {self.timeout_ms}")

    def calculate_backoff_ms(self, attempt: int) -> int:
        """
        Calculate backoff time in milliseconds for given attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Backoff time in milliseconds

        Example:
            >>> config = VerificationConfig(initial_backoff_ms=2000)
            >>> config.calculate_backoff_ms(0)  # First retry
            2000
            >>> config.calculate_backoff_ms(1)  # Second retry
            4000
            >>> config.calculate_backoff_ms(2)  # Third retry
            8000
        """
        if not self.exponential_backoff:
            return self.initial_backoff_ms

        # Exponential backoff: 2s → 4s → 8s → 16s (optimized for macOS Docker Desktop)
        return self.initial_backoff_ms * (2 ** attempt)


@dataclass
class ConnectionVerificationResult:
    """
    Result of single connection verification attempt.

    Used internally during retry loop to track individual attempts.

    Fields:
        success: Whether this connection attempt succeeded
        error_type: Error classification
        attempt_number: Which attempt this was (1-indexed)
        elapsed_ms: Time elapsed for this attempt in milliseconds
        error_message: Detailed error message from exception (if failed)
        is_retryable: Whether this error should trigger a retry

    Example:
        >>> result = ConnectionVerificationResult(
        ...     success=False,
        ...     error_type="access_denied",
        ...     attempt_number=1,
        ...     elapsed_ms=150,
        ...     is_retryable=True
        ... )
        >>> if result.is_retryable:
        ...     print("Will retry this connection")
    """

    success: bool
    error_type: str
    attempt_number: int
    elapsed_ms: int
    error_message: str = ""
    is_retryable: bool = False

    def __post_init__(self):
        """Validate fields."""
        if self.attempt_number <= 0:
            raise ValueError(f"attempt_number must be > 0, got {self.attempt_number}")
        if self.elapsed_ms < 0:
            raise ValueError(f"elapsed_ms must be >= 0, got {self.elapsed_ms}")


# Retryable errors (timing issues - retry with backoff)
# These are transient errors that should resolve with time
RETRYABLE_ERRORS = {
    "access denied",
    "password change required",
    "authentication failed",
    # IRIS COMMUNICATION LINK errors (transient connection issues)
    "communication link error",
    "communication error",
    "invalid message received",
    "failed to connect to server",
    # Error codes from IRIS DBAPI (transient)
    "error code: -1",  # Generic connection error
    "error code: 60",  # Communication timed out
    "failed to receive message",
}

# Non-retryable errors (real failures - fail fast)
# These indicate infrastructure problems that won't resolve with retries
NON_RETRYABLE_ERRORS = {
    "connection refused",  # Service not running
    "network unreachable",  # Network infrastructure problem
    "unknown host",  # DNS failure
    "no route to host",  # Routing problem
}


def classify_error(error_message: str) -> Tuple[str, bool]:
    """
    Classify connection error as retryable or non-retryable.

    Default behavior: Unknown errors are RETRYABLE during password verification.
    Most connection errors during container startup are transient timing issues.

    Args:
        error_message: Error message from connection attempt

    Returns:
        Tuple of (error_type, is_retryable)

    Example:
        >>> classify_error("Access Denied")
        ('access_denied', True)
        >>> classify_error("Connection refused")
        ('connection_refused', False)
        >>> classify_error("Some unknown error")  # Defaults to retryable
        ('unknown', True)
    """
    error_lower = error_message.lower()

    # Check non-retryable errors FIRST (infrastructure failures)
    # These indicate problems that won't resolve with retries
    for non_retryable_error in NON_RETRYABLE_ERRORS:
        if non_retryable_error in error_lower:
            error_type = non_retryable_error.replace(" ", "_")
            return error_type, False

    # Check retryable errors
    for retryable_error in RETRYABLE_ERRORS:
        if retryable_error in error_lower:
            error_type = retryable_error.replace(" ", "_")
            return error_type, True

    # Unknown error - DEFAULT TO RETRYABLE (Constitutional Principle #1)
    # During password verification, most unknown errors are transient timing issues
    # that will resolve after IRIS finishes initializing
    return "unknown", True


def verify_password_via_connection(
    hostname: str,
    port: int,
    namespace: str,
    username: str,
    password: str,
    attempt_number: int,
    config: Optional[VerificationConfig] = None
) -> ConnectionVerificationResult:
    """
    Verify password change by attempting DBAPI connection.

    Args:
        hostname: IRIS hostname
        port: IRIS port (usually 1972)
        namespace: IRIS namespace
        username: Username to verify
        password: Password to verify
        attempt_number: Current attempt number (1-indexed)
        config: Verification configuration

    Returns:
        ConnectionVerificationResult with success status and timing

    Example:
        >>> result = verify_password_via_connection(
        ...     hostname="localhost",
        ...     port=1972,
        ...     namespace="USER",
        ...     username="SuperUser",
        ...     password="SYS",
        ...     attempt_number=1
        ... )
        >>> if result.success:
        ...     print("Password verified!")
    """
    if config is None:
        config = VerificationConfig()

    start_time_ms = int(time.time() * 1000)

    try:
        # Use dbapi_compat for proper DBAPI connection (handles iris.connect() workaround)
        # Constitutional Principle #2: DBAPI First
        # Constitutional Principle #8: Use official iris.connect() API
        from iris_devtester.utils.dbapi_compat import get_connection

        conn = get_connection(
            hostname=hostname,
            port=port,
            namespace=namespace,
            username=username,
            password=password
        )

        # Test connection with simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        elapsed_ms = int(time.time() * 1000) - start_time_ms

        logger.debug(
            f"Verification attempt {attempt_number} succeeded in {elapsed_ms}ms"
        )

        return ConnectionVerificationResult(
            success=True,
            error_type="",
            attempt_number=attempt_number,
            elapsed_ms=elapsed_ms,
            is_retryable=False
        )

    except Exception as e:
        elapsed_ms = int(time.time() * 1000) - start_time_ms
        error_message = str(e)
        error_type, is_retryable = classify_error(error_message)

        logger.debug(
            f"Verification attempt {attempt_number} failed in {elapsed_ms}ms: "
            f"{error_type} (retryable={is_retryable})"
        )

        return ConnectionVerificationResult(
            success=False,
            error_type=error_type,
            attempt_number=attempt_number,
            elapsed_ms=elapsed_ms,
            error_message=error_message,
            is_retryable=is_retryable
        )
