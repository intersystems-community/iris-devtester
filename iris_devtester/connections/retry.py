"""
Connection retry logic with exponential backoff.

Extracted from rag-templates production code with enhancements.
"""

import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry (should take no arguments)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay between retries
        max_delay: Maximum delay between retries

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries fail

    Example:
        >>> def connect():
        ...     return create_connection()
        >>> conn = retry_with_backoff(connect, max_retries=3)
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e

            # Don't retry on last attempt
            if attempt == max_retries - 1:
                logger.warning(
                    f"All {max_retries} retry attempts failed. Giving up."
                )
                break

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )

            time.sleep(delay)

            # Exponential backoff with max cap
            delay = min(delay * backoff_factor, max_delay)

    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry failed with no exception (unexpected)")


def create_connection_with_retry(
    connection_func: Callable[[], Any],
    max_retries: int = 3,
) -> Any:
    """
    Create database connection with automatic retry.

    Convenience wrapper around retry_with_backoff specifically for connections.

    Args:
        connection_func: Function that creates a connection
        max_retries: Maximum retry attempts

    Returns:
        Database connection

    Example:
        >>> from iris_devtester.connections.dbapi import create_dbapi_connection
        >>> config = IRISConfig(host="localhost", port=1972)
        >>> conn = create_connection_with_retry(
        ...     lambda: create_dbapi_connection(config),
        ...     max_retries=3
        ... )
    """
    logger.info(f"Attempting connection (max {max_retries} retries)...")

    return retry_with_backoff(
        connection_func,
        max_retries=max_retries,
        initial_delay=0.5,  # 0.5s, 1s, 2s pattern from rag-templates
        backoff_factor=2.0,
    )
