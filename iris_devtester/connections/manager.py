"""
Connection manager with DBAPI-first, JDBC-fallback strategy.

Implements Constitutional Principle #2: "DBAPI First, JDBC Fallback"
- Always tries DBAPI first (3x faster)
- Falls back to JDBC if DBAPI unavailable or fails
- Provides helpful error messages with remediation steps
"""

import logging
from datetime import datetime
from typing import Any, Literal, Tuple

from iris_devtester.config.models import IRISConfig
from iris_devtester.connections.models import ConnectionInfo
from iris_devtester.connections import dbapi, jdbc
from iris_devtester.utils.dbapi_compat import get_package_info

logger = logging.getLogger(__name__)


def get_connection(config: IRISConfig) -> Any:
    """
    Get IRIS database connection using automatic driver selection.

    Implements Constitutional Principle #2 (DBAPI First, JDBC Fallback):
    1. If driver="auto" (default): Try DBAPI first, fall back to JDBC
    2. If driver="dbapi": Use DBAPI only
    3. If driver="jdbc": Use JDBC only

    Args:
        config: IRIS configuration with connection parameters

    Returns:
        Database connection object

    Raises:
        ConnectionError: If connection fails (with remediation guidance)

    Example:
        >>> from iris_devtester.config import IRISConfig, discover_config
        >>> # Zero-config (auto-discovers from environment)
        >>> config = discover_config()
        >>> conn = get_connection(config)
        >>>
        >>> # Explicit config
        >>> config = IRISConfig(host="localhost", port=1972, driver="auto")
        >>> conn = get_connection(config)
    """
    # Explicit driver selection
    if config.driver == "dbapi":
        return _get_dbapi_only(config)
    elif config.driver == "jdbc":
        return _get_jdbc_only(config)

    # Auto mode: Try DBAPI first, fall back to JDBC
    return _get_auto_connection(config)


def get_connection_with_info(config: IRISConfig) -> Tuple[Any, ConnectionInfo]:
    """
    Get connection and metadata about which driver was used.

    Same as get_connection() but also returns ConnectionInfo with driver type,
    connection time, and other metadata.

    Args:
        config: IRIS configuration with connection parameters

    Returns:
        Tuple of (connection, connection_info)

    Example:
        >>> from iris_devtester.config import IRISConfig
        >>> config = IRISConfig()
        >>> conn, info = get_connection_with_info(config)
        >>> print(f"Connected using {info.driver_type} at {info.connection_time}")
    """
    start_time = datetime.now()

    # Get connection using normal flow
    conn = get_connection(config)

    # Determine which driver was actually used
    # (This is a bit of a hack - we should track this during connection)
    driver_type: Literal["dbapi", "jdbc"] = "dbapi"  # Default assumption

    # Try to detect JDBC vs DBAPI based on connection object type
    conn_type_name = type(conn).__name__.lower()
    if "jdbc" in conn_type_name or "jaydebeapi" in str(type(conn).__module__):
        driver_type = "jdbc"

    # Create connection info
    info = ConnectionInfo(
        driver_type=driver_type,
        host=config.host,
        port=config.port,
        namespace=config.namespace,
        username=config.username,
        connection_time=start_time,
        is_pooled=False,
        container_id=None,
    )

    return conn, info


def _get_auto_connection(config: IRISConfig) -> Any:
    """
    Get connection with automatic DBAPI->JDBC fallback.

    Constitutional Principle #2: DBAPI First, JDBC Fallback
    """
    dbapi_error = None

    # Try DBAPI first if available
    if dbapi.is_dbapi_available():
        try:
            logger.info("Attempting DBAPI connection (3x faster than JDBC)...")
            conn = dbapi.create_dbapi_connection(config)

            # Log which DBAPI package was used (FR-010)
            try:
                info = get_package_info()
                logger.info(
                    f"✓ Connected using DBAPI - {info.package_name} v{info.version} "
                    f"(detected in {info.detection_time_ms:.2f}ms)"
                )
            except Exception:
                # Fallback if package info unavailable
                logger.info("✓ Connected using DBAPI")

            return conn
        except Exception as e:
            dbapi_error = e
            logger.warning(f"DBAPI connection failed: {e}")
            logger.info("Falling back to JDBC connection...")

    # Fall back to JDBC
    if jdbc.is_jdbc_available():
        try:
            logger.info("Attempting JDBC connection...")
            conn = jdbc.create_jdbc_connection(config)
            logger.info("✓ Connected using JDBC (fallback)")
            return conn
        except Exception as jdbc_error:
            # Both failed - provide comprehensive error
            raise ConnectionError(
                f"Failed to establish database connection with both DBAPI and JDBC\n"
                "\n"
                "What went wrong:\n"
                "  Both connection methods failed to connect to IRIS.\n"
                "\n"
                f"DBAPI error: {dbapi_error}\n"
                f"JDBC error: {jdbc_error}\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify IRIS is running:\n"
                "     docker ps | grep iris\n"
                "\n"
                "  2. Check connection details:\n"
                f"     Host: {config.host}\n"
                f"     Port: {config.port}\n"
                f"     Namespace: {config.namespace}\n"
                "\n"
                "  3. Verify credentials are correct\n"
                "\n"
                "  4. Check network connectivity and firewall rules\n"
            ) from jdbc_error

    # Neither driver available
    raise ConnectionError(
        "No IRIS database drivers available\n"
        "\n"
        "What went wrong:\n"
        "  No compatible DBAPI package (intersystems-irispython or intersystems-iris)\n"
        "  and no JDBC driver (jaydebeapi) is installed.\n"
        "  At least one driver is required to connect to IRIS.\n"
        "\n"
        "How to fix it:\n"
        "  1. Install modern DBAPI driver (recommended - 3x faster):\n"
        "     pip install intersystems-irispython>=5.3.0\n"
        "\n"
        "  2. Or install legacy DBAPI driver:\n"
        "     pip install intersystems-iris>=3.0.0\n"
        "\n"
        "  3. Or install JDBC driver (fallback):\n"
        "     pip install jaydebeapi\n"
        "\n"
        "  4. Or install iris-devtester with all drivers:\n"
        "     pip install 'iris-devtester[all]'\n"
        "\n"
        "Documentation:\n"
        "  https://iris-devtester.readthedocs.io/dbapi-packages/\n"
    )


def _get_dbapi_only(config: IRISConfig) -> Any:
    """
    Get DBAPI connection only (no fallback).

    Raises ConnectionError if DBAPI is not available or connection fails.
    """
    if not dbapi.is_dbapi_available():
        raise ConnectionError(
            "DBAPI driver not available (driver='dbapi' specified)\n"
            "\n"
            "What went wrong:\n"
            "  You specified driver='dbapi' but no compatible DBAPI package is installed.\n"
            "\n"
            "How to fix it:\n"
            "  1. Install modern DBAPI driver (recommended):\n"
            "     pip install intersystems-irispython>=5.3.0\n"
            "\n"
            "  2. Or install legacy DBAPI driver:\n"
            "     pip install intersystems-iris>=3.0.0\n"
            "\n"
            "  3. Or use auto driver selection:\n"
            "     config = IRISConfig(driver='auto')  # Will try DBAPI then JDBC\n"
            "\n"
            "Documentation:\n"
            "  https://iris-devtester.readthedocs.io/dbapi-packages/\n"
        )

    logger.info("Using DBAPI connection (explicit driver='dbapi')")
    conn = dbapi.create_dbapi_connection(config)

    # Log which DBAPI package was used (FR-010)
    try:
        info = get_package_info()
        logger.info(
            f"Connected via {info.package_name} v{info.version} "
            f"(detected in {info.detection_time_ms:.2f}ms)"
        )
    except Exception:
        pass  # Already logged in create_dbapi_connection

    return conn


def _get_jdbc_only(config: IRISConfig) -> Any:
    """
    Get JDBC connection only (no fallback).

    Raises ConnectionError if JDBC is not available or connection fails.
    """
    if not jdbc.is_jdbc_available():
        raise ConnectionError(
            "JDBC driver not available (driver='jdbc' specified)\n"
            "\n"
            "What went wrong:\n"
            "  You specified driver='jdbc' but jaydebeapi is not installed.\n"
            "\n"
            "How to fix it:\n"
            "  1. Install JDBC driver:\n"
            "     pip install jaydebeapi\n"
            "\n"
            "  2. Download JDBC JAR:\n"
            "     wget https://github.com/intersystems-community/iris-driver-distribution/raw/main/JDBC/JDK18/intersystems-jdbc-3.8.4.jar\n"
            "\n"
            "  3. Or use DBAPI instead (3x faster):\n"
            "     config = IRISConfig(driver='dbapi')\n"
            "     pip install intersystems-irispython\n"
        )

    logger.info("Using JDBC connection (explicit driver='jdbc')")
    return jdbc.create_jdbc_connection(config)
