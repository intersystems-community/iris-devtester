"""DBAPI Package Compatibility Layer.

This module provides automatic detection and compatibility between:
- Modern package: intersystems-irispython (v5.1.2+)
- Legacy package: intersystems-iris (v3.0.0+)

The module automatically detects which package is installed and provides
a unified interface for DBAPI connections, ensuring zero-config compatibility
and backward compatibility for existing users.

CRITICAL: This module uses the OFFICIAL iris.connect() API (Constitutional Principle #8).
It does NOT use private _DBAPI attributes which do not exist in either package version.
See CONSTITUTION.md Principle 8 for empirical evidence.

Constitutional Compliance:
- Principle #2: DBAPI First (maintains performance)
- Principle #4: Zero Configuration Viable (automatic detection)
- Principle #5: Fail Fast with Guidance (constitutional errors)
- Principle #7: Medical-Grade Reliability (version validation)
- Principle #8: Official IRIS Python API (NO private _DBAPI attribute!)

Performance: Package detection overhead <10ms (NFR-001)

Logging Levels:
- INFO: Package detected successfully
- DEBUG: Fallback attempts (modern → legacy)
- ERROR: No package available
"""
import logging
import time
import importlib.metadata
from dataclasses import dataclass
from typing import Callable, Any
from packaging import version

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


def validate_package_version(package_name: str, installed_version: str, min_version: str) -> None:
    """Validate that installed package meets minimum version requirement.

    Args:
        package_name: Name of the package (e.g., "intersystems-irispython")
        installed_version: Version string of installed package
        min_version: Minimum required version string

    Raises:
        ImportError: If installed version is too old (constitutional format)
    """
    if version.parse(installed_version) < version.parse(min_version):
        raise ImportError(
            f"Package {package_name} version {installed_version} is incompatible\n"
            "\n"
            "What went wrong:\n"
            f"  Detected package version does not meet minimum requirements.\n"
            f"  Minimum required: {min_version}\n"
            "\n"
            "Why this happened:\n"
            f"  iris-devtester requires specific DBAPI features introduced in v{min_version}.\n"
            "  Older versions may have incompatible APIs or missing functionality.\n"
            "\n"
            "How to fix it:\n"
            f"  Upgrade the package:\n"
            f"  → pip install --upgrade {package_name}>={min_version}\n"
            "\n"
            "Documentation:\n"
            "  https://iris-devtester.readthedocs.io/dbapi-packages/\n"
        )


class DBAPIPackageNotFoundError(ImportError):
    """Raised when no compatible IRIS Python package is found."""

    def __init__(self):
        super().__init__(
            "No IRIS Python package detected\n"
            "\n"
            "What went wrong:\n"
            "  Neither intersystems-irispython nor intersystems-iris is installed.\n"
            "  iris-devtester requires one of these packages for DBAPI connections.\n"
            "\n"
            "Why this happened:\n"
            "  iris-devtester uses DBAPI for fast SQL operations (3x faster than JDBC).\n"
            "  The modern package (intersystems-irispython) or legacy package\n"
            "  (intersystems-iris) must be installed.\n"
            "\n"
            "How to fix it:\n"
            "  Install the modern IRIS Python package:\n"
            "  → pip install intersystems-irispython>=5.1.2\n"
            "\n"
            "  Or install the legacy package (backward compatibility):\n"
            "  → pip install intersystems-iris>=3.0.0\n"
            "\n"
            "Documentation:\n"
            "  https://iris-devtester.readthedocs.io/dbapi-packages/\n"
        )


def detect_dbapi_package() -> DBAPIPackageInfo:
    """Detect available IRIS DBAPI package.

    Tries modern package (intersystems-irispython) first, falls back to
    legacy package (intersystems-iris) if modern unavailable.

    Returns:
        DBAPIPackageInfo with detected package details

    Raises:
        DBAPIPackageNotFoundError: When neither package is available
        ImportError: When package version is too old

    Performance: <10ms detection time (NFR-001)
    """
    start_time = time.perf_counter()

    # Try modern package first (priority per Principle #2)
    # CRITICAL: Use official iris.connect() API, NOT private _DBAPI attribute!
    # See CONSTITUTION.md Principle 8 for empirical evidence that _DBAPI does not exist.
    try:
        import iris
        import os
        import sys

        # Check if connect method is available
        if not hasattr(iris, "connect"):
            # Workaround for pytest module caching issue (from iris-vector-rag v0.5.13)
            # During pytest collection, iris may be imported when PYTEST_CURRENT_TEST is set,
            # causing partial initialization. Manually load _elsdk_.py or _init_elsdk.py
            # to inject DBAPI attributes into iris module.
            logger.debug("iris.connect() not found, attempting to load ELSDK manually")

            # Get iris module directory
            if hasattr(iris, '__file__') and iris.__file__:
                iris_dir = os.path.dirname(iris.__file__)

                # Try both _elsdk_.py (v5.3.0+) and _init_elsdk.py (v5.1.2)
                for elsdk_file in ['_elsdk_.py', '_init_elsdk.py']:
                    elsdk_path = os.path.join(iris_dir, elsdk_file)
                    if os.path.exists(elsdk_path):
                        logger.info(f"Found {elsdk_file}, loading to inject DBAPI interface")
                        try:
                            with open(elsdk_path, 'r') as f:
                                elsdk_code = compile(f.read(), elsdk_path, 'exec')
                            exec(elsdk_code, iris.__dict__)

                            if hasattr(iris, "connect"):
                                logger.info(f"Successfully injected DBAPI via {elsdk_file}")
                                break
                        except Exception as exec_error:
                            logger.warning(f"Failed to exec {elsdk_file}: {exec_error}")

                if not hasattr(iris, "connect"):
                    raise ImportError(
                        f"iris module found but connect() not available even after trying to load ELSDK. "
                        f"iris dir: {iris_dir}, available: {[x for x in dir(iris) if not x.startswith('_')]}"
                    )

        # Validate version
        pkg_version = importlib.metadata.version("intersystems-irispython")
        validate_package_version("intersystems-irispython", pkg_version, "5.1.2")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Detected IRIS DBAPI package: intersystems-irispython v{pkg_version}")

        return DBAPIPackageInfo(
            package_name="intersystems-irispython",
            import_path="iris",
            version=pkg_version,
            connect_function=iris.connect,
            detection_time_ms=elapsed_ms
        )
    except ImportError as e:
        logger.debug(f"Modern package not available, trying legacy: {e}")

    # Fall back to legacy package
    try:
        import iris.irissdk

        # Validate version
        pkg_version = importlib.metadata.version("intersystems-iris")
        validate_package_version("intersystems-iris", pkg_version, "3.0.0")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Detected IRIS DBAPI package: intersystems-iris v{pkg_version} (legacy)")

        return DBAPIPackageInfo(
            package_name="intersystems-iris",
            import_path="iris.irissdk",
            version=pkg_version,
            connect_function=iris.irissdk.connect,
            detection_time_ms=elapsed_ms
        )
    except ImportError:
        logger.error("No IRIS DBAPI package detected")

    # Neither package available
    raise DBAPIPackageNotFoundError()


class DBAPIConnectionAdapter:
    """Adapter for IRIS DBAPI connections.

    Provides package-agnostic interface for creating DBAPI connections.
    Implements singleton pattern for zero overhead.
    """

    def __init__(self):
        """Initialize adapter with detected package info."""
        self._package_info = detect_dbapi_package()

    def connect(self, hostname: str, port: int, namespace: str,
                username: str, password: str, **kwargs) -> Any:
        """Create DBAPI connection using detected package.

        Args:
            hostname: IRIS hostname
            port: IRIS port
            namespace: IRIS namespace
            username: IRIS username
            password: IRIS password
            **kwargs: Additional connection parameters

        Returns:
            DBAPI connection object

        Performance: Zero overhead - direct function call
        """
        return self._package_info.connect_function(
            hostname=hostname,
            port=port,
            namespace=namespace,
            username=username,
            password=password,
            **kwargs
        )

    def get_package_info(self) -> DBAPIPackageInfo:
        """Return detected package information.

        Returns:
            DBAPIPackageInfo with package metadata
        """
        return self._package_info


# Global singleton adapter (cached for performance)
_adapter: DBAPIConnectionAdapter | None = None


def _get_adapter() -> DBAPIConnectionAdapter:
    """Get or create singleton adapter instance.

    Returns:
        DBAPIConnectionAdapter singleton
    """
    global _adapter
    if _adapter is None:
        _adapter = DBAPIConnectionAdapter()
    return _adapter


def get_connection(*args, **kwargs) -> Any:
    """Get DBAPI connection using detected package.

    Convenience function that delegates to the singleton adapter.

    Args:
        *args: Connection arguments (hostname, port, namespace, username, password)
        **kwargs: Additional connection parameters

    Returns:
        DBAPI connection object

    Example:
        >>> conn = get_connection(hostname="localhost", port=1972,
        ...                       namespace="USER", username="_SYSTEM", password="SYS")
    """
    return _get_adapter().connect(*args, **kwargs)


def get_package_info() -> DBAPIPackageInfo:
    """Return detected package information.

    Returns:
        DBAPIPackageInfo with package metadata

    Example:
        >>> info = get_package_info()
        >>> print(f"Using {info.package_name} v{info.version}")
    """
    return _get_adapter().get_package_info()


__all__ = [
    "detect_dbapi_package",
    "validate_package_version",
    "DBAPIPackageInfo",
    "DBAPIPackageNotFoundError",
    "DBAPIConnectionAdapter",
    "get_connection",
    "get_package_info",
]
