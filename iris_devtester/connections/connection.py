"""
Modern DBAPI-only connection manager for IRIS.

This is a simplified, modern connection manager that:
- Uses DBAPI only (no JDBC)
- Auto-discovers connection parameters
- Includes retry logic with exponential backoff
- Automatically handles password reset
- Provides clean, simple API

Constitutional Principle #2: DBAPI First (no JDBC fallback in this modern toolkit)
"""

import logging
from typing import Any, Optional

from iris_devtester.config import IRISConfig, discover_config
from iris_devtester.connections.dbapi import create_dbapi_connection, is_dbapi_available
from iris_devtester.connections.retry import create_connection_with_retry

logger = logging.getLogger(__name__)


def get_connection(
    config: Optional[IRISConfig] = None,
    auto_retry: bool = True,
    max_retries: int = 3,
) -> Any:
    """
    Get IRIS database connection (DBAPI only, modern toolkit).

    Simplified, modern connection manager:
    - DBAPI-only (3x faster than JDBC, no fallback needed)
    - Auto-discovers connection parameters from Docker/env
    - Retry logic with exponential backoff
    - Clear error messages with remediation steps

    Args:
        config: Optional IRIS configuration. If None, auto-discovers from:
                - Environment variables (IRIS_HOST, IRIS_PORT, etc.)
                - .env file
                - Docker container inspection
                - Native IRIS instances
        auto_retry: Enable automatic retry with exponential backoff
        max_retries: Maximum retry attempts (default: 3)

    Returns:
        DBAPI connection object

    Raises:
        ConnectionError: If connection fails (with remediation guidance)

    Examples:
        >>> # Zero-config (auto-discovers everything)
        >>> conn = get_connection()

        >>> # Explicit config
        >>> from iris_devtester.config import IRISConfig
        >>> config = IRISConfig(host="localhost", port=1972)
        >>> conn = get_connection(config)

        >>> # Disable retry
        >>> conn = get_connection(auto_retry=False)
    """
    # Discover configuration if not provided
    if config is None:
        config = discover_config()
        logger.info(f"Auto-discovered IRIS at {config.host}:{config.port}")

    # Verify DBAPI is available
    if not is_dbapi_available():
        raise ConnectionError(
            "DBAPI driver not available\n"
            "\n"
            "What went wrong:\n"
            "  This is a modern DBAPI-only toolkit. A compatible IRIS Python\n"
            "  package is required to connect to IRIS.\n"
            "\n"
            "How to fix it:\n"
            "  1. Install the modern DBAPI driver (recommended):\n"
            "     pip install intersystems-irispython>=5.3.0\n"
            "\n"
            "  2. Or install the legacy DBAPI driver:\n"
            "     pip install intersystems-iris>=3.0.0\n"
            "\n"
            "  3. Or install iris-devtester with DBAPI support:\n"
            "     pip install 'iris-devtester[dbapi]'\n"
            "\n"
            "  4. Or install with all optional dependencies:\n"
            "     pip install 'iris-devtester[all]'\n"
            "\n"
            "Documentation:\n"
            "  https://iris-devtester.readthedocs.io/dbapi-packages/\n"
        )

    # Create connection function
    def _connect():
        try:
            return create_dbapi_connection(config)
        except Exception as e:
            from iris_devtester.utils.password_reset import reset_password_if_needed
            if reset_password_if_needed(e, username=config.username):
                return create_dbapi_connection(config)
            raise e

    # Connect with or without retry

    if auto_retry:
        return create_connection_with_retry(_connect, max_retries=max_retries)
    else:
        return _connect()


class IRISConnection:
    """
    Context manager wrapper for IRIS connections.

    Provides clean resource management with automatic cleanup.

    Example:
        >>> with IRISConnection() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT COUNT(*) FROM SomeTable")
        ...     result = cursor.fetchone()
    """

    def __init__(
        self,
        config: Optional[IRISConfig] = None,
        auto_retry: bool = True,
        max_retries: int = 3,
    ):
        """
        Initialize connection context manager.

        Args:
            config: Optional IRIS configuration (auto-discovers if None)
            auto_retry: Enable automatic retry
            max_retries: Maximum retry attempts
        """
        self.config = config
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        self.connection = None

    def __enter__(self):
        """Create and return connection."""
        self.connection = get_connection(
            config=self.config,
            auto_retry=self.auto_retry,
            max_retries=self.max_retries,
        )
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection on exit."""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
        return False  # Don't suppress exceptions
