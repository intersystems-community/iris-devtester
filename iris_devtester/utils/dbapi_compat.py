"""DBAPI Package Compatibility Layer.

This module provides automatic detection and compatibility between:
- Modern package: intersystems-irispython (v5.3.0+)
- Legacy package: intersystems-iris (v3.0.0+)

The module automatically detects which package is installed and provides
a unified interface for DBAPI connections, ensuring zero-config compatibility
and backward compatibility for existing users.

Constitutional Compliance:
- Principle #2: DBAPI First (maintains performance)
- Principle #4: Zero Configuration Viable (automatic detection)
- Principle #5: Fail Fast with Guidance (constitutional errors)
- Principle #7: Medical-Grade Reliability (version validation)

Performance: Package detection overhead <10ms (NFR-001)

Logging Levels:
- INFO: Package detected successfully
- DEBUG: Fallback attempts (modern → legacy)
- ERROR: No package available
"""
import logging
from dataclasses import dataclass
from typing import Callable, Any

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class DBAPIPackageInfo:
    """Information about detected DBAPI package.

    Attributes:
        package_name: One of "intersystems-irispython" or "intersystems-iris"
        import_path: Module import path (e.g., "intersystems_iris.dbapi._DBAPI")
        version: Package version (e.g., "5.3.0")
        connect_function: Reference to the connect() function
        detection_time_ms: Time taken to detect package in milliseconds
    """

    package_name: str
    import_path: str
    version: str
    connect_function: Callable[..., Any]
    detection_time_ms: float


def detect_dbapi_package():
    """Detect available IRIS DBAPI package.

    Placeholder for package detection logic.
    Will be implemented in T013.
    """
    pass


class DBAPIConnectionAdapter:
    """Adapter for IRIS DBAPI connections.

    Provides package-agnostic interface for creating DBAPI connections.
    Placeholder - will be implemented in T015.
    """
    pass


def get_connection(*args, **kwargs):
    """Get DBAPI connection using detected package.

    Placeholder for convenience function.
    Will be implemented in T016.
    """
    pass


def get_package_info():
    """Return detected package information.

    Placeholder for package info retrieval.
    Will be implemented in T016.
    """
    pass


__all__ = [
    "detect_dbapi_package",
    "DBAPIConnectionAdapter",
    "get_connection",
    "get_package_info",
]
