"""
JDBC connection module for InterSystems IRIS.

Provides JDBC (jaydebeapi) connections as a fallback option.
JDBC is slower (3x) than DBAPI but works everywhere (Constitutional Principle #2).
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from iris_devtester.config.models import IRISConfig

logger = logging.getLogger(__name__)

# JDBC driver class name
JDBC_DRIVER_CLASS = "com.intersystems.jdbc.IRISDriver"

# JDBC JAR filename
JDBC_JAR_NAME = "intersystems-jdbc-3.8.4.jar"


def is_jdbc_available() -> bool:
    """
    Check if JDBC (jaydebeapi) is available.

    Args:
        (no arguments)

    Returns:
        True if jaydebeapi module can be imported

    Example:
        >>> if is_jdbc_available():
        ...     print("JDBC driver available (fallback option)")
        ... else:
        ...     print("Install with: pip install jaydebeapi")
    """
    try:
        import jaydebeapi

        return True
    except ImportError:
        return False


def find_jdbc_driver() -> Optional[Path]:
    """
    Find JDBC driver JAR file.

    Searches multiple common locations for the InterSystems JDBC driver.

    Args:
        (no arguments)

    Returns:
        Path to JDBC JAR file, or None if not found

    Example:
        >>> jar_path = find_jdbc_driver()
        >>> if jar_path:
        ...     print(f"JDBC driver found at: {jar_path}")
        ... else:
        ...     print("JDBC driver not found - download from GitHub")
    """
    # Possible JDBC driver locations (in priority order)
    possible_paths = [
        # Package directory
        Path(__file__).parent.parent / JDBC_JAR_NAME,
        # Current working directory
        Path.cwd() / JDBC_JAR_NAME,
        # User home directory
        Path.home() / JDBC_JAR_NAME,
        # System locations
        Path("/opt/iris/jdbc") / JDBC_JAR_NAME,
        Path("/usr/local/lib") / JDBC_JAR_NAME,
    ]

    for path in possible_paths:
        if path.exists():
            logger.debug(f"Found JDBC driver at: {path}")
            return path

    return None


def create_jdbc_connection(config: IRISConfig) -> Any:
    """
    Create JDBC connection using jaydebeapi package.

    JDBC is slower than DBAPI (3x) but works everywhere. Use as fallback
    per Constitutional Principle #2 (DBAPI First, JDBC Fallback).

    Args:
        config: IRIS configuration with connection parameters

    Returns:
        JDBC connection object

    Raises:
        ImportError: If jaydebeapi not installed
        FileNotFoundError: If JDBC driver JAR not found
        ConnectionError: If connection fails (with remediation guidance)

    Example:
        >>> from iris_devtester.config import IRISConfig
        >>> config = IRISConfig(host="localhost", port=1972)
        >>> conn = create_jdbc_connection(config)
    """
    try:
        import jaydebeapi
    except ImportError as e:
        raise ImportError(
            "JDBC connection failed: jaydebeapi not installed\n"
            "\n"
            "What went wrong:\n"
            "  The jaydebeapi package is not available in your environment.\n"
            "  This package provides JDBC connectivity to IRIS.\n"
            "\n"
            "How to fix it:\n"
            "  1. Install the package:\n"
            "     pip install jaydebeapi\n"
            "\n"
            "  2. Or install iris-devtester with JDBC support:\n"
            "     pip install 'iris-devtester[jdbc]'\n"
            "\n"
            f"Original error: {e}\n"
        ) from e

    # Find JDBC driver JAR
    jdbc_jar_path = find_jdbc_driver()

    if jdbc_jar_path is None:
        # List where we looked for helpful error message
        search_locations = [
            str(Path(__file__).parent.parent / JDBC_JAR_NAME),
            str(Path.cwd() / JDBC_JAR_NAME),
            str(Path.home() / JDBC_JAR_NAME),
            "/opt/iris/jdbc/" + JDBC_JAR_NAME,
        ]

        raise FileNotFoundError(
            f"JDBC connection failed: Driver JAR not found\n"
            "\n"
            "What went wrong:\n"
            f"  The JDBC driver ({JDBC_JAR_NAME}) was not found.\n"
            "  Searched locations:\n"
            + "".join(f"    - {loc}\n" for loc in search_locations)
            + "\n"
            "How to fix it:\n"
            "  1. Download the JDBC driver:\n"
            "     wget https://github.com/intersystems-community/iris-driver-distribution/raw/main/JDBC/JDK18/intersystems-jdbc-3.8.4.jar\n"
            "\n"
            "  2. Place it in one of these locations:\n"
            f"     - {Path.cwd() / JDBC_JAR_NAME} (current directory)\n"
            f"     - {Path.home() / JDBC_JAR_NAME} (home directory)\n"
            "\n"
            "  3. Or use DBAPI instead (3x faster):\n"
            "     pip install 'iris-devtester[dbapi]'\n"
        )

    # Build JDBC URL
    jdbc_url = f"jdbc:IRIS://{config.host}:{config.port}/{config.namespace}"

    try:
        # Create JDBC connection
        connection = jaydebeapi.connect(
            JDBC_DRIVER_CLASS,
            jdbc_url,
            [config.username, config.password],
            str(jdbc_jar_path),
        )

        logger.debug(
            f"JDBC connection established to {jdbc_url} using driver at {jdbc_jar_path}"
        )
        return connection

    except Exception as e:
        error_msg = str(e).lower()

        # Check for password change requirement
        if "password change required" in error_msg or "password expired" in error_msg:
            raise ConnectionError(
                f"JDBC connection failed: Password change required\n"
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

        # Check for driver issues
        if "class not found" in error_msg or "driver" in error_msg:
            raise ConnectionError(
                f"JDBC connection failed: Driver issue\n"
                "\n"
                "What went wrong:\n"
                f"  JDBC driver at {jdbc_jar_path} could not be loaded.\n"
                "  The driver JAR may be corrupted or incompatible.\n"
                "\n"
                "How to fix it:\n"
                "  1. Re-download the JDBC driver:\n"
                "     rm {jdbc_jar_path}\n"
                "     wget https://github.com/intersystems-community/iris-driver-distribution/raw/main/JDBC/JDK18/intersystems-jdbc-3.8.4.jar\n"
                "\n"
                "  2. Verify Java is installed:\n"
                "     java -version\n"
                "\n"
                f"Original error: {e}\n"
            ) from e

        # Generic connection error
        raise ConnectionError(
            f"JDBC connection failed to {jdbc_url}\n"
            "\n"
            "What went wrong:\n"
            "  Unable to establish JDBC connection to IRIS database.\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify IRIS is running:\n"
            "     docker ps | grep iris\n"
            "\n"
            "  2. Check connection details:\n"
            f"     URL: {jdbc_url}\n"
            f"     Driver: {jdbc_jar_path}\n"
            "\n"
            "  3. Verify credentials are valid\n"
            "\n"
            "  4. Try DBAPI instead (3x faster):\n"
            "     pip install 'iris-devtester[dbapi]'\n"
            "\n"
            f"Original error: {e}\n"
        ) from e
