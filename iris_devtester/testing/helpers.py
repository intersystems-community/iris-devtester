"""
Testing helpers for password reset timing validation.

Provides utilities for measuring and validating password verification timing.
"""

import logging
import time
from contextlib import contextmanager
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@contextmanager
def measure_verification_time(operation_name: str = "operation"):
    """
    Context manager to measure and log operation timing.

    Args:
        operation_name: Name of operation being measured

    Yields:
        Dictionary with timing data (updated after context exit)

    Example:
        >>> with measure_verification_time("password_reset") as timing:
        ...     # Perform password reset
        ...     success, msg = reset_password()
        >>> print(f"Took {timing['elapsed_seconds']:.2f}s")
    """
    timing = {"start_time": time.time(), "elapsed_seconds": 0.0}

    logger.debug(f"Starting {operation_name}...")

    yield timing

    timing["elapsed_seconds"] = time.time() - timing["start_time"]
    logger.debug(
        f"Completed {operation_name} in {timing['elapsed_seconds']:.2f}s"
    )


def assert_within_timeout(
    elapsed_seconds: float,
    timeout_seconds: float,
    operation_name: str = "operation",
    grace_period_seconds: float = 0.5
):
    """
    Assert that operation completed within timeout.

    Args:
        elapsed_seconds: Actual time elapsed
        timeout_seconds: Expected timeout limit
        operation_name: Name of operation (for error message)
        grace_period_seconds: Grace period to allow for timing variance

    Raises:
        AssertionError: If operation exceeded timeout

    Example:
        >>> elapsed = 9.2
        >>> assert_within_timeout(elapsed, timeout_seconds=10.0, operation_name="verification")
        >>> # Passes: 9.2s < 10.0s
        >>>
        >>> elapsed = 11.5
        >>> assert_within_timeout(elapsed, timeout_seconds=10.0, operation_name="verification")
        AssertionError: verification took 11.5s, exceeds 10.0s timeout (NFR-004)
    """
    max_allowed = timeout_seconds + grace_period_seconds

    if elapsed_seconds > max_allowed:
        raise AssertionError(
            f"{operation_name} took {elapsed_seconds:.2f}s, "
            f"exceeds {timeout_seconds:.1f}s timeout "
            f"(allowed up to {max_allowed:.1f}s with grace period)"
        )

    logger.debug(
        f"{operation_name} completed in {elapsed_seconds:.2f}s "
        f"(within {timeout_seconds:.1f}s timeout)"
    )


def simulate_delayed_password_propagation(
    delay_seconds: float,
    callback: Optional[Callable] = None
):
    """
    Simulate password propagation delay for testing.

    Args:
        delay_seconds: Time to wait (simulates IRIS processing time)
        callback: Optional callback to execute after delay

    Example:
        >>> # Simulate 3s macOS delay
        >>> simulate_delayed_password_propagation(3.0)
        >>>
        >>> # With callback
        >>> def on_ready():
        ...     print("Password ready!")
        >>> simulate_delayed_password_propagation(2.0, callback=on_ready)
    """
    logger.debug(f"Simulating password propagation delay ({delay_seconds}s)...")
    time.sleep(delay_seconds)

    if callback:
        callback()

    logger.debug("Password propagation simulation complete")


def calculate_success_rate(successes: int, total: int) -> float:
    """
    Calculate success rate as percentage.

    Args:
        successes: Number of successful attempts
        total: Total number of attempts

    Returns:
        Success rate as percentage (0-100)

    Example:
        >>> calculate_success_rate(995, 1000)
        99.5
        >>> calculate_success_rate(0, 0)
        0.0
    """
    if total == 0:
        return 0.0
    return (successes / total) * 100.0


def assert_success_rate_meets_target(
    successes: int,
    total: int,
    target_rate: float,
    operation_name: str = "operation"
):
    """
    Assert that success rate meets or exceeds target.

    Args:
        successes: Number of successful attempts
        total: Total number of attempts
        target_rate: Target success rate percentage (e.g., 99.5)
        operation_name: Name of operation (for error message)

    Raises:
        AssertionError: If success rate below target

    Example:
        >>> assert_success_rate_meets_target(995, 1000, 99.5, "password_reset")
        >>> # Passes: 99.5% >= 99.5%
        >>>
        >>> assert_success_rate_meets_target(990, 1000, 99.5, "password_reset")
        AssertionError: password_reset success rate 99.0% < target 99.5% (NFR-001)
    """
    actual_rate = calculate_success_rate(successes, total)

    if actual_rate < target_rate:
        raise AssertionError(
            f"{operation_name} success rate {actual_rate:.1f}% < "
            f"target {target_rate:.1f}% (NFR-001)\n"
            f"  Successes: {successes}/{total}"
        )

    logger.info(
        f"{operation_name} success rate: {actual_rate:.1f}% "
        f"(meets target {target_rate:.1f}%)"
    )
