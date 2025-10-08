"""
Enhanced IRIS container wrapper.

Extends testcontainers-iris-python with automatic connection management,
password reset, and better wait strategies.
"""

import logging
from typing import Any, Optional

from iris_devtools.config.models import IRISConfig
from iris_devtools.connections.manager import get_connection
from iris_devtools.utils.password_reset import reset_password_if_needed
from iris_devtools.containers.wait_strategies import IRISReadyWaitStrategy
from iris_devtools.containers.monitoring import (
    MonitoringPolicy,
    configure_monitoring,
    disable_monitoring,
)
from iris_devtools.containers.performance import get_resource_metrics

logger = logging.getLogger(__name__)

# Try to import testcontainers-iris, provide fallback if not available
try:
    from testcontainers_iris import IRISContainer as BaseIRISContainer

    HAS_TESTCONTAINERS_IRIS = True
except ImportError:
    # Fallback: create minimal base class
    logger.warning(
        "testcontainers-iris-python not installed. "
        "Install with: pip install 'iris-devtools[containers]'"
    )
    HAS_TESTCONTAINERS_IRIS = False

    # Minimal base class for type checking
    class BaseIRISContainer:
        """Fallback base class when testcontainers-iris not available."""

        pass


class IRISContainer(BaseIRISContainer):
    """
    Enhanced IRIS container with automatic connection and password reset.

    Wraps testcontainers-iris-python with:
    - Convenience methods for Community/Enterprise editions
    - Automatic connection management via get_connection()
    - Automatic password reset integration
    - Better wait strategies for container readiness

    Example:
        >>> # Community Edition (most common)
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     # Use connection...

        >>> # Enterprise Edition (requires license)
        >>> with IRISContainer.enterprise(license_key="...") as iris:
        ...     conn = iris.get_connection()
    """

    def __init__(self, image: str = "intersystemsdc/iris-community:latest", **kwargs):
        """
        Initialize IRIS container.

        Args:
            image: Docker image to use
            **kwargs: Additional arguments passed to base container
        """
        if not HAS_TESTCONTAINERS_IRIS:
            raise ImportError(
                "testcontainers-iris-python not installed\n"
                "\n"
                "How to fix it:\n"
                "  1. Install testcontainers support:\n"
                "     pip install 'iris-devtools[containers]'\n"
                "\n"
                "  2. Or install all optional dependencies:\n"
                "     pip install 'iris-devtools[all]'\n"
            )

        super().__init__(image=image, **kwargs)
        self._connection = None
        self._config = None
        self._callin_enabled = False

    @classmethod
    def community(
        cls,
        namespace: str = "USER",
        username: str = "SuperUser",
        password: str = "SYS",
        **kwargs,
    ) -> "IRISContainer":
        """
        Create Community Edition IRIS container.

        This is the most common configuration for development and testing.

        Args:
            namespace: IRIS namespace (default: "USER")
            username: Username (default: "SuperUser")
            password: Password (default: "SYS")
            **kwargs: Additional container configuration

        Returns:
            Configured IRISContainer instance

        Example:
            >>> with IRISContainer.community() as iris:
            ...     conn = iris.get_connection()
            ...     # Test code here...
        """
        container = cls(image="intersystemsdc/iris-community:latest", **kwargs)

        # Store connection config
        container._config = IRISConfig(
            host="localhost",  # Will be updated on start
            port=1972,  # Will be updated on start
            namespace=namespace,
            username=username,
            password=password,
        )

        return container

    @classmethod
    def enterprise(
        cls,
        license_key: Optional[str] = None,
        namespace: str = "USER",
        username: str = "SuperUser",
        password: str = "SYS",
        **kwargs,
    ) -> "IRISContainer":
        """
        Create Enterprise Edition IRIS container.

        Requires a valid InterSystems license key.

        Args:
            license_key: InterSystems IRIS license key (optional)
            namespace: IRIS namespace (default: "USER")
            username: Username (default: "SuperUser")
            password: Password (default: "SYS")
            **kwargs: Additional container configuration

        Returns:
            Configured IRISContainer instance

        Raises:
            ValueError: If license_key not provided and not in environment

        Example:
            >>> with IRISContainer.enterprise(license_key="...") as iris:
            ...     conn = iris.get_connection()
        """
        if license_key is None:
            import os

            license_key = os.environ.get("IRIS_LICENSE_KEY")

        if license_key is None:
            raise ValueError(
                "Enterprise Edition requires license key\n"
                "\n"
                "How to fix it:\n"
                "  1. Provide license key:\n"
                "     IRISContainer.enterprise(license_key='your-key')\n"
                "\n"
                "  2. Or set environment variable:\n"
                "     export IRIS_LICENSE_KEY='your-key'\n"
                "\n"
                "  3. Or use Community Edition instead:\n"
                "     IRISContainer.community()\n"
            )

        container = cls(image="intersystemsdc/iris:latest", **kwargs)

        # Store connection config
        container._config = IRISConfig(
            host="localhost",
            port=1972,
            namespace=namespace,
            username=username,
            password=password,
        )

        # TODO: Configure license key injection
        # This would typically involve mounting license file or env var

        return container

    def get_connection(self, enable_callin: bool = True) -> Any:
        """
        Get database connection to this container.

        Automatically handles:
        - CallIn service enablement (for DBAPI/embedded Python)
        - Connection via DBAPI or JDBC
        - Password reset if needed
        - Connection configuration from container

        Args:
            enable_callin: Auto-enable CallIn service for DBAPI (default: True)

        Returns:
            Database connection object

        Example:
            >>> with IRISContainer.community() as iris:
            ...     conn = iris.get_connection()
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT 1")
        """
        if self._connection is not None:
            return self._connection

        # CRITICAL: Enable CallIn service for DBAPI connections
        # This is required for embedded Python and DBAPI to work
        # (Constitutional Principle #1: Automatic Remediation)
        if enable_callin and not self._callin_enabled:
            logger.info("Enabling CallIn service for DBAPI connections...")
            if self.enable_callin_service():
                logger.info("✓ CallIn service enabled")
            else:
                logger.warning(
                    "⚠️  Could not enable CallIn service. "
                    "DBAPI connections may fail. Will fall back to JDBC."
                )

        # Update config with actual container host/port
        config = self.get_config()

        try:
            # Use connection manager (DBAPI-first, JDBC-fallback)
            self._connection = get_connection(config)
            return self._connection

        except Exception as e:
            # Try automatic password reset
            logger.warning(f"Connection failed: {e}")

            if reset_password_if_needed(e, container_name=self.get_container_name()):
                logger.info("Password reset successful, retrying connection...")
                self._connection = get_connection(config)
                return self._connection

            raise

    def get_config(self) -> IRISConfig:
        """
        Get IRISConfig for this container.

        Returns configuration with actual container host/port.

        Returns:
            IRISConfig instance
        """
        if self._config is None:
            self._config = IRISConfig()

        # Update with actual container details if running
        try:
            if HAS_TESTCONTAINERS_IRIS and hasattr(self, "get_container_host_ip"):
                self._config = IRISConfig(
                    host=self.get_container_host_ip(),
                    port=int(self.get_exposed_port(1972)),
                    namespace=self._config.namespace,
                    username=self._config.username,
                    password=self._config.password,
                )
        except Exception as e:
            logger.debug(f"Could not update config from container: {e}")

        return self._config

    def wait_for_ready(self, timeout: int = 60) -> bool:
        """
        Wait for IRIS to be fully ready.

        Uses IRISReadyWaitStrategy for thorough readiness checks.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if ready, False if timeout

        Example:
            >>> container = IRISContainer.community()
            >>> container.start()
            >>> if container.wait_for_ready(timeout=30):
            ...     print("IRIS is ready!")
        """
        config = self.get_config()

        strategy = IRISReadyWaitStrategy(port=config.port, timeout=timeout)

        try:
            return strategy.wait_until_ready(config.host, config.port, timeout)
        except TimeoutError:
            logger.error("IRIS container did not become ready in time")
            return False

    def reset_password(
        self, username: str = "_SYSTEM", new_password: str = "SYS"
    ) -> bool:
        """
        Reset IRIS password in this container.

        Args:
            username: Username to reset (default: "_SYSTEM")
            new_password: New password (default: "SYS")

        Returns:
            True if successful, False otherwise

        Example:
            >>> with IRISContainer.community() as iris:
            ...     if iris.reset_password():
            ...         print("Password reset successful")
        """
        from iris_devtools.utils.password_reset import reset_password

        success, message = reset_password(
            container_name=self.get_container_name(),
            username=username,
            new_password=new_password,
        )

        if success:
            # Update stored config with new password
            self._config.password = new_password
            logger.info(f"✓ {message}")
        else:
            logger.error(f"✗ {message}")

        return success

    def get_container_name(self) -> str:
        """
        Get Docker container name.

        Returns:
            Container name
        """
        if HAS_TESTCONTAINERS_IRIS:
            try:
                return self.get_wrapped_container().name
            except Exception:
                pass

        return "iris_container"

    def enable_callin_service(self) -> bool:
        """
        Enable CallIn service for DBAPI and embedded Python.

        CRITICAL: CallIn service must be enabled for:
        - DBAPI connections (intersystems-irispython)
        - Embedded Python (iris module)
        - External applications calling IRIS methods

        Works transparently for BOTH Community and Enterprise editions.

        Returns:
            True if successful, False otherwise

        Example:
            >>> container = IRISContainer.community()
            >>> container.start()
            >>> container.enable_callin_service()  # Required for DBAPI
            >>> conn = container.get_connection()  # Now works!

        Note:
            This is automatically called by get_connection() so you rarely
            need to call it manually.
        """
        if self._callin_enabled:
            logger.debug("CallIn service already enabled")
            return True

        try:
            import subprocess

            container_name = self.get_container_name()

            # ObjectScript command to enable CallIn service
            # Works for BOTH Community and Enterprise editions
            objectscript_cmd = (
                "Do ##class(Security.Services).Get(\"%Service_CallIn\",.s) "
                "Set s.Enabled=1 "
                "Do ##class(Security.Services).Modify(s) "
                "Write \"CALLIN_ENABLED\""
            )

            # Execute via iris session
            cmd = [
                "docker",
                "exec",
                container_name,
                "iris",
                "session",
                "IRIS",
                "-U",
                "%SYS",
                objectscript_cmd,
            ]

            logger.debug(f"Enabling CallIn on container: {container_name}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and "CALLIN_ENABLED" in result.stdout:
                self._callin_enabled = True
                logger.info(
                    f"✓ CallIn service enabled on {container_name} "
                    "(Community/Enterprise transparent)"
                )
                return True
            else:
                logger.warning(
                    f"CallIn enablement returned unexpected output:\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(
                "Timeout enabling CallIn service (IRIS may not be fully started)"
            )
            return False

        except FileNotFoundError:
            logger.error(
                "Docker command not found. Cannot enable CallIn service.\n"
                "This means DBAPI connections will likely fail. "
                "Connection manager will fall back to JDBC."
            )
            return False

        except Exception as e:
            logger.error(f"Failed to enable CallIn service: {e}")
            return False

    def check_callin_enabled(self) -> bool:
        """
        Check if CallIn service is currently enabled.

        Returns:
            True if CallIn is enabled, False otherwise

        Example:
            >>> if container.check_callin_enabled():
            ...     print("DBAPI connections will work")
            ... else:
            ...     print("Only JDBC connections available")
        """
        try:
            import subprocess

            container_name = self.get_container_name()

            # ObjectScript to check CallIn status
            objectscript_cmd = (
                "Do ##class(Security.Services).Get(\"%Service_CallIn\",.s) "
                "Write s.Enabled"
            )

            cmd = [
                "docker",
                "exec",
                container_name,
                "iris",
                "session",
                "IRIS",
                "-U",
                "%SYS",
                objectscript_cmd,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )

            # Check if output contains "1" (enabled)
            is_enabled = result.returncode == 0 and "1" in result.stdout

            if is_enabled:
                self._callin_enabled = True

            return is_enabled

        except Exception as e:
            logger.debug(f"Could not check CallIn status: {e}")
            return False
