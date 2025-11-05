"""
DBAPI connection module for InterSystems IRIS.

Provides DBAPI (intersystems-irispython) connections - the fastest option (3x faster than JDBC).
This is the preferred connection method per Constitutional Principle #2.
"""

import logging
from typing import Any, Optional

from iris_devtester.config.models import IRISConfig

logger = logging.getLogger(__name__)


def is_dbapi_available() -> bool:
    """
    Check if DBAPI (intersystems-irispython) is available.

    Args:
        (no arguments)

    Returns:
        True if DBAPI module can be imported and has connect attribute

    Example:
        >>> if is_dbapi_available():
        ...     print("DBAPI driver available (3x faster than JDBC)")
        ... else:
        ...     print("Install with: pip install intersystems-irispython")
    """
    try:
        import iris.dbapi

        return hasattr(iris.dbapi, "connect")
    except ImportError:
        return False


def create_dbapi_connection(config: IRISConfig) -> Any:
    """
    Create DBAPI connection using intersystems-irispython package.

    This is the fastest connection method (3x faster than JDBC) and should
    be preferred when available (Constitutional Principle #2).

    Args:
        config: IRIS configuration with connection parameters

    Returns:
        DBAPI connection object

    Raises:
        ImportError: If intersystems-irispython not installed
        ConnectionError: If connection fails (with remediation guidance)

    Example:
        >>> from iris_devtester.config import IRISConfig
        >>> config = IRISConfig(host="localhost", port=1972)
        >>> conn = create_dbapi_connection(config)
    """
    try:
        import iris.dbapi
    except ImportError as e:
        raise ImportError(
            "DBAPI connection failed: intersystems-irispython not installed\n"
            "\n"
            "What went wrong:\n"
            "  The intersystems-irispython package is not available in your environment.\n"
            "  This package provides the fastest IRIS connection method (3x faster than JDBC).\n"
            "\n"
            "How to fix it:\n"
            "  1. Install the package:\n"
            "     pip install intersystems-irispython\n"
            "\n"
            "  2. Or install iris-devtools with DBAPI support:\n"
            "     pip install 'iris-devtools[dbapi]'\n"
            "\n"
            f"Original error: {e}\n"
        ) from e

    # Verify iris.dbapi has connect
    if not hasattr(iris.dbapi, "connect"):
        dbapi_file = getattr(iris.dbapi, "__file__", "unknown")
        raise ImportError(
            f"DBAPI connection failed: iris.dbapi module has no 'connect' attribute\n"
            "\n"
            "What went wrong:\n"
            f"  The iris.dbapi module was imported from: {dbapi_file}\n"
            "  But it doesn't have the expected 'connect' method.\n"
            "  This usually means an incompatible version is installed.\n"
            "\n"
            "How to fix it:\n"
            "  1. Reinstall the package:\n"
            "     pip uninstall intersystems-irispython\n"
            "     pip install intersystems-irispython\n"
            "\n"
            "  2. Verify the installation:\n"
            "     python -c 'import iris.dbapi; print(iris.dbapi.__version__)'\n"
        )

    try:
        # Create connection using iris.dbapi
        connection = iris.dbapi.connect(
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
            username=config.username,
            password=config.password,
        )

        logger.debug(
            f"DBAPI connection established to {config.host}:{config.port}/{config.namespace}"
        )
        return connection

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
                "     reset_password_if_needed()\n"
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
