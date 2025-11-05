"""
IRIS DevTools - Battle-tested InterSystems IRIS infrastructure utilities.

This package provides automatic, reliable infrastructure for IRIS development:
- Testcontainers integration with auto-remediation
- Connection management (DBAPI-first, JDBC fallback)
- Automatic password reset
- Testing utilities (pytest fixtures, schema management)
- Zero-configuration defaults

Quick Start:
    >>> from iris_devtools.containers import IRISContainer
    >>> with IRISContainer.community() as iris:
    ...     conn = iris.get_connection()
    ...     cursor = conn.cursor()
    ...     cursor.execute("SELECT 1")
    ...     print(cursor.fetchone())
"""

__version__ = "1.0.0"
__author__ = "InterSystems Community"
__license__ = "MIT"

# Convenience imports for common usage
from iris_devtools.connections import get_connection
from iris_devtools.containers import IRISContainer
from iris_devtools.config import IRISConfig

__all__ = [
    "__version__",
    "get_connection",
    "IRISContainer",
    "IRISConfig",
]
