"""
Connection management for InterSystems IRIS databases.

This is a modern DBAPI-only toolkit. For simple usage:

    >>> from iris_devtester.connections import get_connection
    >>> conn = get_connection()  # Auto-discovers everything

For advanced usage, see the legacy manager module.
"""

# Modern DBAPI-only API (recommended)
from iris_devtester.connections.connection import get_connection, IRISConnection

# Legacy API with JDBC fallback (for compatibility)
from iris_devtester.connections.models import ConnectionInfo
from iris_devtester.connections.manager import (
    get_connection as get_connection_legacy,
    get_connection_with_info,
)
from iris_devtester.connections import dbapi, jdbc

# Utilities
from iris_devtester.connections.auto_discovery import (
    auto_detect_iris_port,
    auto_detect_iris_host_and_port,
)
from iris_devtester.connections.retry import (
    retry_with_backoff,
    create_connection_with_retry,
)

__all__ = [
    # Modern API (recommended)
    "get_connection",
    "IRISConnection",
    # Legacy API
    "ConnectionInfo",
    "get_connection_legacy",
    "get_connection_with_info",
    "dbapi",
    "jdbc",
    # Utilities
    "auto_detect_iris_port",
    "auto_detect_iris_host_and_port",
    "retry_with_backoff",
    "create_connection_with_retry",
]
