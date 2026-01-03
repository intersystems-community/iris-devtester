"""
DBAPI connection module for InterSystems IRIS.

Provides DBAPI connections with automatic package detection - the fastest option (3x faster than JDBC).
Supports both modern (intersystems-irispython) and legacy (intersystems-iris) packages.
This is the preferred connection method per Constitutional Principle #2.
"""

import logging
from typing import Any, Optional

from iris_devtester.config.models import IRISConfig
from iris_devtester.utils.dbapi_compat import get_connection, get_package_info, DBAPIPackageNotFoundError

logger = logging.getLogger(__name__)


def is_dbapi_available() -> bool:
    """
    Check if any DBAPI package (modern or legacy) is available.

    Automatically detects:
    - Modern: intersystems-irispython (v5.3.0+)
    - Legacy: intersystems-iris (v3.0.0+)

    Args:
        (no arguments)

    Returns:
        True if a compatible DBAPI package is available

    Example:
        >>> if is_dbapi_available():
        ...     print("DBAPI driver available (3x faster than JDBC)")
        ... else:
        ...     print("Install with: pip install intersystems-irispython")
    """
    try:
        # Use our compatibility layer to detect package
        info = get_package_info()
        return info is not None
    except (DBAPIPackageNotFoundError, ImportError):
        return False


def create_dbapi_connection(config: IRISConfig) -> Any:
    """
    Create DBAPI connection using automatic package detection.

    Automatically uses the best available package:
    - Modern: intersystems-irispython (v5.3.0+) - preferred
    - Legacy: intersystems-iris (v3.0.0+) - fallback

    This is the fastest connection method (3x faster than JDBC) and should
    be preferred when available (Constitutional Principle #2).

    Args:
        config: IRIS configuration with connection parameters

    Returns:
        DBAPI connection object

    Raises:
        DBAPIPackageNotFoundError: If no compatible package installed
        ConnectionError: If connection fails (with remediation guidance)

    Example:
        >>> from iris_devtester.config import IRISConfig
        >>> config = IRISConfig(host="localhost", port=1972)
        >>> conn = create_dbapi_connection(config)
    """
    try:
        # Use compatibility layer for automatic package detection
        connection = get_connection(
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
            username=config.username,
            password=config.password,
        )

        # Log which package was used
        info = get_package_info()
        logger.debug(
            f"DBAPI connection established using {info.package_name} v{info.version} "
            f"to {config.host}:{config.port}/{config.namespace}"
        )
        return connection

    except DBAPIPackageNotFoundError as e:
        # Re-raise with original constitutional error message
        raise e

    except Exception as e:
        error_msg = str(e).lower()

        # Check for password change requirement
        if "password change required" in error_msg or "password expired" in error_msg:
            raise ConnectionError(
                f"DBAPI connection failed: Password change required\n"
                "\n"
                "What went wrong:\n"
                f"  IRIS at {config.host}:{config.port} requires a password change.\n"
                "  This is common on first connection or after password expiration.\n"
                "\n"
                "How to fix it:\n"
                "  1. Use the password reset utility:\n"
                "     from iris_devtester.utils import reset_password_if_needed\n"
                f"     reset_password_if_needed(e, username='{config.username}')\n"
                "\n"
                "  2. Or manually reset via Management Portal:\n"
                "     http://{config.host}:52773/csp/sys/UtilHome.csp\n"
                "\n"
                f"Original error: {e}\n"
            ) from e

        # Generic connection error
        raise ConnectionError(
            f"DBAPI connection failed to {config.host}:{config.port}\n"
            "\n"
            "What went wrong:\n"
            "  Unable to establish DBAPI connection to IRIS database.\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify IRIS is running:\n"
            "     docker ps | grep iris\n"
            "\n"
            "  2. Check host/port are correct:\n"
            f"     Host: {config.host}\n"
            f"     Port: {config.port}\n"
            "\n"
            "  3. Verify credentials are valid\n"
            "\n"
            "  4. Check firewall/network connectivity\n"
            "\n"
            f"Original error: {e}\n"
        ) from e
