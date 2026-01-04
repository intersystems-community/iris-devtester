"""
Enhanced IRIS container wrapper.

Extends testcontainers-iris-python with automatic connection management,
password reset, and better wait strategies.
"""

import logging
from typing import Any, Optional

from iris_devtester.config.models import IRISConfig
from iris_devtester.connections.manager import get_connection
from iris_devtester.utils.password_reset import reset_password_if_needed
from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy
from iris_devtester.containers.monitoring import (
    MonitoringPolicy,
    configure_monitoring,
    disable_monitoring,
)
from iris_devtester.containers.performance import get_resource_metrics

logger = logging.getLogger(__name__)

# Try to import testcontainers-iris, provide fallback if not available
try:
    from testcontainers.iris import IRISContainer as BaseIRISContainer

    HAS_TESTCONTAINERS_IRIS = True
except ImportError:
    # Fallback: create minimal base class
    logger.warning(
        "testcontainers-iris-python not installed. "
        "Install with: pip install 'iris-devtester[containers]'"
    )
    HAS_TESTCONTAINERS_IRIS = False

    # Minimal base class for type checking
    class BaseIRISContainer:
        """Fallback base class when testcontainers-iris not available."""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def start(self):
            return self

        def stop(self):
            pass

        def get_wrapped_container(self):
            return None


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

    def __init__(
        self,
        image: str = "intersystemsdc/iris-community:latest",
        port_registry: Optional["PortRegistry"] = None,
        project_path: Optional[str] = None,
        preferred_port: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize IRIS container.

        Args:
            image: Docker image to use
            port_registry: Optional PortRegistry for multi-project port management
            project_path: Absolute path to project directory (auto-detects from cwd if None)
            preferred_port: Optional manual port override (requires port_registry)
            **kwargs: Additional arguments passed to base container

        Example:
            >>> # Without port registry (backwards compatible)
            >>> container = IRISContainer()

            >>> # With port registry (automatic port assignment)
            >>> from iris_devtester.ports import PortRegistry
            >>> registry = PortRegistry()
            >>> container = IRISContainer(port_registry=registry)

            >>> # With manual port preference
            >>> container = IRISContainer(port_registry=registry, preferred_port=1975)
        """
        if not HAS_TESTCONTAINERS_IRIS:
            raise ImportError(
                "testcontainers-iris-python not installed\n"
                "\n"
                "How to fix it:\n"
                "  1. Install testcontainers support:\n"
                "     pip install 'iris-devtester[containers]'\n"
                "\n"
                "  2. Or install all optional dependencies:\n"
                "     pip install 'iris-devtester[all]'\n"
            )

        super().__init__(image=image, **kwargs)
        self._connection = None
        self._config = None
        self._callin_enabled = False
        self._is_attached = False  # True if attached to external container

        # Port registry integration (Feature 013)
        self._port_registry = port_registry
        self._port_assignment = None
        self._preferred_port = preferred_port

        # Auto-detect project path from current working directory if not provided
        if port_registry is not None and project_path is None:
            import os

            project_path = os.getcwd()

        self._project_path = project_path

    def start(self):
        """
        Start IRIS container with port registry integration.

        If port_registry is configured, assigns a port before starting.
        Otherwise uses default port 1972 (backwards compatible).

        Returns:
            Self for method chaining

        Raises:
            PortExhaustedError: All ports in range are in use
            PortConflictError: Preferred port already assigned
        """
        # Port registry integration (T022)
        if self._port_registry:
            # Assign port from registry
            self._port_assignment = self._port_registry.assign_port(
                project_path=self._project_path, preferred_port=self._preferred_port
            )

            # Use assigned port for container
            assigned_port = self._port_assignment.port

            # Update configuration if exists
            if self._config:
                self._config.port = assigned_port

            # CRITICAL FIX: Configure fixed port binding
            # Without this, testcontainers uses RANDOM port mapping (defeating the purpose!)
            # This binds container:1972 → host:assigned_port (e.g., 1973, 1974, etc.)
            self.with_bind_ports(1972, assigned_port)

            # Update port attribute for compatibility
            self.port = assigned_port

            # Update container name to include project path hash for staleness detection
            import hashlib

            project_hash = hashlib.md5(self._project_path.encode()).hexdigest()[:8]
            container_name = f"iris_{project_hash}_{assigned_port}"

            # Update assignment with container name
            self._port_assignment.container_name = container_name

            # Set container name
            self.with_name(container_name)

            logger.info(
                f"Port registry: assigned port {assigned_port} to {self._project_path}"
            )

        # Call parent start()
        result = super().start()

        # Update config with actual host/port after start
        if self._config:
            self._config.host = self.get_container_host_ip()
            if self._port_registry:
                # With port registry, use the assigned port directly (fixed binding)
                self._config.port = self._port_assignment.port
            else:
                # Without port registry, get mapped port from container (random mapping)
                self._config.port = int(self.get_exposed_port(self.port))

        return result

    def stop(self, force=True, delete_volume=True):
        """
        Stop IRIS container and release port assignment.

        If port_registry is configured, releases the port assignment.

        Args:
            force: Force stop container
            delete_volume: Delete associated volumes

        Returns:
            None
        """
        try:
            # Call parent stop()
            super().stop(force=force, delete_volume=delete_volume)
        finally:
            # Port registry integration (T023)
            if self._port_registry and self._port_assignment:
                try:
                    self._port_registry.release_port(self._project_path)
                    logger.info(
                        f"Port registry: released port {self._port_assignment.port} "
                        f"for {self._project_path}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to release port assignment: {e}")

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
        # CRITICAL FIX (v1.4.5): Pass username/password/namespace to parent testcontainers-iris class
        # Without this, testcontainers-iris uses defaults ("test"/"test") which don't match our config!
        container = cls(
            image="intersystemsdc/iris-community:latest",
            username=username,
            password=password,
            namespace=namespace,
            **kwargs
        )

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
    def from_existing(cls, auto_discover: bool = True) -> Optional[IRISConfig]:
        """
        Detect existing IRIS instance (Docker or native) without creating container.

        Uses auto-discovery to find running IRIS instances via:
        1. Docker container inspection
        2. Native IRIS 'iris list' command
        3. Multi-port scanning (31972, 1972, 11972, 21972)

        Args:
            auto_discover: Enable automatic discovery (default: True)

        Returns:
            IRISConfig if found, None otherwise

        Example:
            >>> config = IRISContainer.from_existing()
            >>> if config:
            ...     print(f"Found IRIS at {config.host}:{config.port}")
            ... else:
            ...     # No existing IRIS, create new container
            ...     with IRISContainer.community() as iris:
            ...         pass

        See Also:
            - docs/learnings/rag-templates-production-patterns.md (Pattern 1, 2)
            - iris_devtester.config.auto_discovery
        """
        if not auto_discover:
            return None

        from iris_devtester.config.auto_discovery import auto_discover_iris

        config_dict = auto_discover_iris()

        if config_dict is None:
            return None

        # Convert dict to IRISConfig
        return IRISConfig(
            host=config_dict.get("host", "localhost"),
            port=config_dict.get("port", 1972),
            namespace=config_dict.get("namespace", "USER"),
            username=config_dict.get("username", "_SYSTEM"),
            password=config_dict.get("password", "SYS"),
        )

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

        # CRITICAL: For Enterprise edition, DON'T create test user
        # Enterprise containers have _SYSTEM by default, we don't need to create users
        # (Community edition needs this because testcontainers-iris creates "test" user)

        # Use ARM64 Enterprise image on ARM architecture
        import platform as platform_module
        if platform_module.machine() == "arm64":
            # Use the ARM64 image we have locally (2025.1)
            image = "containers.intersystems.com/intersystems/iris-arm64:2025.1"
        else:
            image = "intersystemsdc/iris:latest"

        # CRITICAL FIX: Pass username="_SYSTEM" to prevent testcontainers-iris from creating "test" user
        # testcontainers-iris._connect() tries to create self.username (defaults to "test")
        # Enterprise containers have _SYSTEM by default, so we tell testcontainers to use that
        container = cls(
            image=image,
            username=username,  # Pass username so testcontainers uses _SYSTEM, not "test"
            password=password,  # Pass password for consistency
            namespace=namespace,
            **kwargs
        )

        # Set license key as environment variable for Enterprise container
        # Use with_env() method instead of kwargs to avoid duplicate environment parameter
        container.with_env("ISC_LICENSE_KEY", license_key)

        # Store connection config
        container._config = IRISConfig(
            host="localhost",
            port=1972,
            namespace=namespace,
            username=username,
            password=password,
        )

        return container

    @classmethod
    def attach(cls, container_name: str) -> "IRISContainer":
        """
        Attach to existing IRIS container without lifecycle management.

        Use this when IRIS is running via docker-compose or was started externally.
        The returned IRISContainer instance can use all utility methods
        (get_connection, enable_callin, etc.) but lifecycle methods (start, stop,
        context manager) will raise errors.

        Args:
            container_name: Name of the existing Docker container

        Returns:
            IRISContainer instance configured for existing container

        Raises:
            ValueError: If container not found or not running

        Examples:
            >>> # Attach to docker-compose container
            >>> iris = IRISContainer.attach("iris_db")
            >>> conn = iris.get_connection()
            >>>
            >>> # Enable CallIn service on existing container
            >>> iris = IRISContainer.attach("my-iris")
            >>> iris.enable_callin_service()

        Constitutional Compliance:
            - Principle #6: Enterprise Ready, Community Friendly
              Enables docker-compose workflows with licensed IRIS
        """
        import subprocess

        # Verify container exists and is running
        try:
            check_cmd = [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ]

            result = subprocess.run(
                check_cmd, capture_output=True, text=True, timeout=10
            )

            if container_name not in result.stdout:
                raise ValueError(
                    f"Container '{container_name}' not found or not running\n"
                    "\n"
                    "What went wrong:\n"
                    "  The specified container is not running or doesn't exist.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Check running containers:\n"
                    "     docker ps\n"
                    "\n"
                    "  2. Check all containers (including stopped):\n"
                    "     docker ps -a\n"
                    "\n"
                    "  3. Start the container if stopped:\n"
                    f"     docker start {container_name}\n"
                    "\n"
                    "  4. Or start with docker-compose:\n"
                    "     docker-compose up -d\n"
                )

        except subprocess.TimeoutExpired:
            raise ValueError(
                "Timeout checking for container\n"
                "\n"
                "What went wrong:\n"
                "  Docker command took too long to respond.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check if Docker is running:\n"
                "     docker --version\n"
                "\n"
                "  2. Restart Docker Desktop if needed\n"
            )

        except FileNotFoundError:
            raise ValueError(
                "Docker command not found\n"
                "\n"
                "What went wrong:\n"
                "  Docker CLI is not installed or not in PATH.\n"
                "\n"
                "How to fix it:\n"
                "  1. Install Docker Desktop:\n"
                "     https://www.docker.com/products/docker-desktop\n"
                "\n"
                "  2. Verify installation:\n"
                "     docker --version\n"
            )

        # Get container port mapping for SuperServer (1972)
        try:
            port_cmd = [
                "docker",
                "port",
                container_name,
                "1972",
            ]

            result = subprocess.run(
                port_cmd, capture_output=True, text=True, timeout=10
            )

            # Parse output like "0.0.0.0:1972" or "0.0.0.0:55000"
            if result.returncode == 0 and result.stdout.strip():
                port_mapping = result.stdout.strip()
                # Extract port number (after the colon)
                exposed_port = int(port_mapping.split(":")[-1])
            else:
                # No port mapping found, assume container uses 1972 directly
                exposed_port = 1972
                logger.debug(
                    f"No port mapping found for {container_name}:1972, "
                    "assuming direct access on port 1972"
                )

        except Exception as e:
            logger.warning(f"Could not determine port mapping: {e}, using default 1972")
            exposed_port = 1972

        # Create instance without calling BaseIRISContainer.__init__
        # (we don't want testcontainers to try to manage this container)
        instance = cls.__new__(cls)

        # Initialize instance variables directly
        instance._connection = None
        instance._callin_enabled = False
        instance._is_attached = True  # Mark as attached

        # Store config with discovered port
        instance._config = IRISConfig(
            host="localhost",
            port=exposed_port,
            namespace="USER",
            username="SuperUser",
            password="SYS",
        )

        # Store container name for utility methods
        instance._container_name = container_name

        logger.info(
            f"Attached to existing container '{container_name}' "
            f"(localhost:{exposed_port})"
        )

        return instance

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

        # CRITICAL: Unexpire passwords to prevent "password change required" errors
        # (Constitutional Principle #1: Automatic Remediation)
        from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords
        container_name = self.get_container_name()
        success, msg = unexpire_all_passwords(container_name)
        if success:
            logger.info(f"✓ Passwords unexpired: {msg}")
        else:
            logger.warning(f"⚠️  Could not unexpire passwords: {msg}")

        # CRITICAL: PROACTIVELY reset password BEFORE first connection attempt
        # (Feature 007 fix - Constitutional Principle #1: Automatic Remediation)
        # This prevents "Access Denied" and "Password change required" errors
        from iris_devtester.utils.password_reset import reset_password
        config = self.get_config()

        logger.info("Proactively resetting password to ensure clean connection...")
        reset_success, reset_msg = reset_password(
            container_name=container_name,
            username=config.username,
            new_password=config.password,
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
        )
        if reset_success:
            logger.info(f"✓ Password proactively reset: {reset_msg}")
        else:
            logger.warning(f"⚠️  Password reset failed (will attempt connection anyway): {reset_msg}")

        # Use connection manager (DBAPI-first, JDBC-fallback)
        self._connection = get_connection(config)
        return self._connection

    def get_config(self) -> IRISConfig:
        """
        Get IRISConfig for this container.

        Returns configuration with actual container host/port.

        Returns:
            IRISConfig instance

        Example:
            >>> with IRISContainer.community() as iris:
            ...     config = iris.get_config()
            ...     print(f"IRIS running at {config.host}:{config.port}")
            ...     print(f"Namespace: {config.namespace}")
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
        Wait for IRIS to be fully ready and apply dual user hardening.

        Uses IRISReadyWaitStrategy for thorough readiness checks, then applies
        the v1.4.5 dual user hardening fix to ensure both the target user AND
        SuperUser are properly configured for DBAPI connections.

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
            # Step 1: Wait for IRIS to be ready
            ready = strategy.wait_until_ready(
                config.host,
                config.port,
                timeout,
                container_name=self.get_container_name()
            )

            if not ready:
                return False

            # Step 2: Apply dual user hardening (v1.4.5 fix)
            # This ensures both the target user AND SuperUser are properly configured
            logger.info("Applying dual user hardening to ensure reliable DBAPI connections...")

            from iris_devtester.utils.password_reset import reset_password

            # CRITICAL: Don't pass hostname - let reset_password() auto-detect
            # This enables IPv4 forcing on macOS (127.0.0.1 vs localhost)
            # Passing "localhost" explicitly bypasses the IPv4 forcing logic
            result = reset_password(
                container_name=self.get_container_name(),
                username=config.username,
                new_password=config.password,
                hostname=None,  # Auto-detect (forces IPv4 on macOS)
                port=config.port,
                namespace=config.namespace,
            )

            # reset_password returns PasswordResetResult that can unpack to (bool, str)
            success, message = result

            if not success:
                logger.warning(f"Password reset failed (will attempt connection anyway): {message}")
                # Don't fail completely - user might already be configured correctly
                # Connection attempts will reveal if there's a real problem
            else:
                logger.info(f"✓ {message}")

            return True

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
        from iris_devtester.utils.password_reset import reset_password

        # Get config for host/port (Bug #2 fix: initialize if needed)
        config = self.get_config()

        success, message = reset_password(
            container_name=self.get_container_name(),
            username=username,
            new_password=new_password,
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
        )

        if success:
            # Update stored config with new password
            config.password = new_password
            logger.info(f"✓ {message}")
        else:
            logger.error(f"✗ {message}")

        return success

    def get_container_name(self) -> str:
        """
        Get Docker container name.

        Returns:
            Container name

        Example:
            >>> with IRISContainer.community() as iris:
            ...     name = iris.get_container_name()
            ...     print(f"Container name: {name}")
        """
        # If attached to external container, return stored name
        if hasattr(self, "_is_attached") and self._is_attached:
            return self._container_name

        # Otherwise get from testcontainers
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

        Args:
            (no arguments)

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

            # ObjectScript commands to enable CallIn service
            # Works for BOTH Community and Enterprise editions
            # Uses heredoc for proper multi-line ObjectScript execution
            objectscript_commands = """Do ##class(Security.Services).Get("%Service_CallIn",.prop)
Set prop("Enabled")=1
Set prop("AutheEnabled")=48
Do ##class(Security.Services).Modify("%Service_CallIn",.prop)
Write "CALLIN_ENABLED"
Halt"""

            # Execute via iris session with heredoc
            # Note: Using sh -c with heredoc for reliable multi-line execution
            cmd = [
                "docker",
                "exec",
                container_name,
                "sh",
                "-c",
                f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
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

        Args:
            (no arguments)

        Returns:
            True if CallIn is enabled, False otherwise

        Example:
            >>> with IRISContainer.community() as container:
            ...     if container.check_callin_enabled():
            ...         print("DBAPI connections will work")
            ...     else:
            ...         print("Only JDBC connections available")
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

    def get_iris_connection(self):
        """
        Get iris.connect() connection for ObjectScript operations.

        Use this for operations that require ObjectScript execution:
        - Creating/deleting namespaces
        - Task Manager operations
        - Global variable operations
        - Full ObjectScript code execution

        For SQL operations (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE),
        use get_connection() instead - it's 3x faster via DBAPI.

        Args:
            (no arguments)

        Returns:
            iris connection object (embedded Python)

        Raises:
            ImportError: If intersystems-irispython not installed

        Example:
            >>> with IRISContainer.community() as container:
            ...     # Get iris.connect() for ObjectScript
            ...     iris_conn = container.get_iris_connection()
            ...     iris_obj = iris.createIRIS(iris_conn)
            ...
            ...     # Create namespace via ObjectScript
            ...     iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
            ...
            ...     # Get DBAPI connection for SQL (3x faster)
            ...     db_conn = container.get_connection()
            ...     cursor = db_conn.cursor()
            ...     cursor.execute("CREATE TABLE TestData (ID INT, Name VARCHAR(100))")

        Reference:
            See docs/SQL_VS_OBJECTSCRIPT.md for complete guide on when to use
            iris.connect() vs DBAPI.
        """
        try:
            import iris
        except ImportError:
            raise ImportError(
                "intersystems-irispython not installed\n"
                "\n"
                "What went wrong:\n"
                "  iris.connect() requires intersystems-irispython package\n"
                "\n"
                "How to fix it:\n"
                "  pip install intersystems-irispython\n"
                "\n"
                "Why you need this:\n"
                "  - ObjectScript operations require iris.connect()\n"
                "  - SQL operations can use DBAPI (3x faster)\n"
                "  - See docs/SQL_VS_OBJECTSCRIPT.md for details\n"
            )

        config = self.get_config()

        conn = iris.connect(
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
            username=config.username,
            password=config.password,
        )

        logger.debug(
            f"Created iris.connect() connection to {config.host}:{config.port}/{config.namespace}"
        )

        return conn

    def execute_objectscript(self, code: str, namespace: Optional[str] = None) -> str:
        """
        Execute ObjectScript code and return result.

        Uses docker exec with `iris session` - the only reliable way to execute
        arbitrary ObjectScript code from external Python.

        Args:
            code: ObjectScript code to execute
            namespace: Optional namespace (default: container's namespace)

        Returns:
            Result from ObjectScript execution (whatever was Written)

        Example:
            >>> with IRISContainer.community() as container:
            ...     # Simple expression
            ...     result = container.execute_objectscript('Write "Hello, IRIS!"')
            ...     print(result)  # "Hello, IRIS!"
            ...
            ...     # Complex ObjectScript
            ...     result = container.execute_objectscript('''
            ...         Set ^MyGlobal = "test value"
            ...         Write ^MyGlobal
            ...     ''')
            ...     print(result)  # "test value"
            ...
            ...     # Execute in different namespace
            ...     result = container.execute_objectscript(
            ...         'Write $NAMESPACE',
            ...         namespace="%SYS"
            ...     )
            ...     print(result)  # "%SYS"
        """
        import subprocess

        ns = namespace or self._config.namespace
        container_name = self.get_container_name()

        # Ensure code ends with Halt to terminate session cleanly
        if "Halt" not in code:
            code = code + "\nHalt"

        # Execute via iris session with heredoc
        cmd = [
            "docker",
            "exec",
            container_name,
            "sh",
            "-c",
            f'iris session IRIS -U {ns} << "EOF"\n{code}\nEOF',
        ]

        logger.debug(f"Executing ObjectScript in namespace {ns}: {code[:100]}...")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"ObjectScript execution failed (exit code {result.returncode})\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        return result.stdout

    def create_namespace(self, namespace: str) -> bool:
        """
        Create IRIS namespace using ObjectScript via docker exec.

        This uses docker exec to run ObjectScript commands directly, which is more
        reliable than trying to use iris.connect() with by-reference parameters.

        Args:
            namespace: Name of namespace to create

        Returns:
            True if successful, False otherwise

        Example:
            >>> with IRISContainer.community() as container:
            ...     # Create test namespace
            ...     success = container.create_namespace("TEST")
            ...     if success:
            ...         print("Namespace created!")
            ...
            ...     # Use DBAPI for SQL operations
            ...     conn = container.get_connection()
            ...     cursor = conn.cursor()
            ...     cursor.execute("SET NAMESPACE TEST")
            ...     cursor.execute("CREATE TABLE MyTable (ID INT, Name VARCHAR(100))")

        Reference:
            Uses docker exec with ObjectScript because Config.Namespaces.Create()
            requires passing properties by reference (.props), which doesn't work
            from Python embedded API.
        """
        try:
            import subprocess

            container_name = self.get_container_name()

            # ObjectScript commands to create namespace
            # Pattern from InterSystems docs:
            # Set props("Globals")="USER"
            # Set props("Routines")="USER"
            # Set status=##class(Config.Namespaces).Create("name", .props)
            objectscript_commands = f"""Do ##class(Config.Namespaces).Exists("{namespace}",.obj,.status)
If status=1 {{
    Write "EXISTS"
}} Else {{
    Set props("Globals")="USER"
    Set props("Routines")="USER"
    Set status=##class(Config.Namespaces).Create("{namespace}",.props)
    If $$$ISOK(status) {{
        Write "CREATED"
    }} Else {{
        Write "FAILED"
    }}
}}
Halt"""

            # Execute via iris session with heredoc
            cmd = [
                "docker",
                "exec",
                container_name,
                "sh",
                "-c",
                f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
            ]

            logger.debug(f"Creating namespace {namespace} in container: {container_name}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                if "CREATED" in result.stdout:
                    logger.info(f"✓ Created namespace: {namespace}")
                    return True
                elif "EXISTS" in result.stdout:
                    logger.debug(f"Namespace {namespace} already exists")
                    return True
                else:
                    logger.error(
                        f"Failed to create namespace {namespace}:\n"
                        f"stdout: {result.stdout}\n"
                        f"stderr: {result.stderr}"
                    )
                    return False
            else:
                logger.error(
                    f"Docker exec failed for namespace creation:\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(
                f"Timeout creating namespace {namespace} (IRIS may not be fully started)"
            )
            return False

        except FileNotFoundError:
            logger.error(
                "Docker command not found. Cannot create namespace via docker exec."
            )
            return False

        except Exception as e:
            logger.error(f"Error creating namespace {namespace}: {e}")
            return False

    def delete_namespace(self, namespace: str) -> bool:
        """
        Delete IRIS namespace using ObjectScript.

        This is a convenience method that handles the iris.connect() boilerplate.

        Args:
            namespace: Name of namespace to delete

        Returns:
            True if successful, False otherwise

        Example:
            >>> with IRISContainer.community() as container:
            ...     # Create and use namespace
            ...     container.create_namespace("TEST")
            ...     # ... do testing ...
            ...
            ...     # Cleanup
            ...     container.delete_namespace("TEST")

        Reference:
            This uses iris.connect() internally because namespace deletion
            requires ObjectScript. See docs/SQL_VS_OBJECTSCRIPT.md for details.
        """
        import iris

        config = self.get_config()

        conn = iris.connect(
            hostname=config.host,
            port=config.port,
            namespace="%SYS",  # Must use %SYS for namespace operations
            username=config.username,
            password=config.password,
        )

        try:
            iris_obj = iris.createIRIS(conn)
            result = iris_obj.classMethodValue("Config.Namespaces", "Delete", namespace)
            success = result == 1

            if success:
                logger.info(f"✓ Deleted namespace: {namespace}")
            else:
                logger.warning(f"Failed to delete namespace: {namespace} (may not exist)")

            return success

        except Exception as e:
            logger.error(f"Error deleting namespace {namespace}: {e}")
            return False

        finally:
            conn.close()

    def get_test_namespace(self, prefix: str = "TEST") -> str:
        """
        Create unique test namespace for isolated testing.

        Use this in pytest fixtures to ensure test isolation. Each call
        creates a new namespace with a unique name.

        Args:
            prefix: Namespace prefix (default: "TEST")

        Returns:
            Namespace name (e.g., "TEST_A1B2C3D4")

        Example:
            >>> # In pytest conftest.py
            >>> @pytest.fixture
            ... def test_namespace(iris_container):
            ...     # Create unique namespace
            ...     namespace = iris_container.get_test_namespace()
            ...
            ...     # Yield for testing
            ...     yield namespace
            ...
            ...     # Automatic cleanup
            ...     iris_container.delete_namespace(namespace)

            >>> # In test file
            >>> def test_my_feature(iris_container, test_namespace):
            ...     # Get DBAPI connection for SQL
            ...     conn = iris_container.get_connection()
            ...     cursor = conn.cursor()
            ...     cursor.execute(f"SET NAMESPACE {test_namespace}")
            ...     cursor.execute("CREATE TABLE TestData (ID INT, Name VARCHAR(100))")
            ...     cursor.execute("INSERT INTO TestData VALUES (1, 'Alice')")
            ...
            ...     # Test your code
            ...     cursor.execute("SELECT COUNT(*) FROM TestData")
            ...     assert cursor.fetchone()[0] == 1

        Reference:
            See docs/SQL_VS_OBJECTSCRIPT.md for the pattern of using
            iris.connect() for setup/cleanup and DBAPI for testing.
        """
        import uuid

        namespace = f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

        if self.create_namespace(namespace):
            logger.debug(f"Created test namespace: {namespace}")
            return namespace
        else:
            raise RuntimeError(
                f"Failed to create test namespace: {namespace}\n"
                "\n"
                "What went wrong:\n"
                "  Could not create unique namespace for testing.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check IRIS container is running\n"
                "  2. Check user has namespace creation privileges\n"
                "  3. Check namespace doesn't already exist\n"
            )

    def get_assigned_port(self) -> int:
        """
        Get the port assigned to this container.

        Returns port from port registry assignment if available, otherwise
        returns the default port (1972) or manually configured port.

        Returns:
            Port number (e.g., 1972, 1973, etc.)

        Example:
            >>> registry = PortRegistry()
            >>> with IRISContainer(port_registry=registry) as iris:
            ...     port = iris.get_assigned_port()
            ...     print(f"Container running on port {port}")
        """
        if self._port_assignment:
            return self._port_assignment.port
        elif self._config:
            return self._config.port
        else:
            return 1972  # Default port

    def get_project_path(self) -> Optional[str]:
        """
        Get the project path associated with this container.

        Returns None if port_registry was not used.

        Returns:
            Absolute path to project directory, or None

        Example:
            >>> registry = PortRegistry()
            >>> with IRISContainer(port_registry=registry) as iris:
            ...     path = iris.get_project_path()
            ...     print(f"Project: {path}")
        """
        return self._project_path

    def validate(
        self,
        level: "HealthCheckLevel" = None
    ) -> "ValidationResult":
        """
        Validate this container's health.

        Performs defensive validation to detect container issues like:
        - Container not running
        - Stale container ID references
        - Exec accessibility problems
        - IRIS not responsive

        Args:
            level: Validation depth (MINIMAL, STANDARD, or FULL).
                  Default: STANDARD

        Returns:
            ValidationResult for this container.

        Example:
            >>> with IRISContainer.community() as iris:
            ...     result = iris.validate()
            ...     if not result.success:
            ...         print(result.format_message())

        Constitutional Compliance:
            - Principle #1: Automatic detection of issues
            - Principle #5: Clear guidance on failures
        """
        from iris_devtester.containers.models import HealthCheckLevel
        from iris_devtester.containers.validation import validate_container

        if level is None:
            level = HealthCheckLevel.STANDARD

        # Get container name from underlying container
        container_name = self.get_container_name()

        return validate_container(
            container_name=container_name,
            level=level,
            docker_client=None  # Auto-create
        )

    def assert_healthy(
        self,
        level: "HealthCheckLevel" = None
    ):
        """
        Assert container is healthy, raise if not.

        Convenience method for validation that raises an exception
        if the container is not healthy.

        Args:
            level: Validation depth (default: STANDARD).

        Raises:
            RuntimeError: If validation fails. Error message includes
                         full remediation guidance.

        Example:
            >>> with IRISContainer.community() as iris:
            ...     iris.assert_healthy()  # Raises if not healthy
            ...     conn = iris.get_connection()  # Safe to proceed

        Constitutional Compliance:
            - Principle #5: Structured error messages with remediation
        """
        result = self.validate(level=level)

        if not result.success:
            raise RuntimeError(result.format_message())
