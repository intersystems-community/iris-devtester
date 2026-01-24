"""
Enhanced IRIS container wrapper.

Extends testcontainers-iris-python with automatic connection management,
password reset, and better wait strategies.
"""

import hashlib
import logging
import os
import platform as platform_module
import subprocess
import time
from typing import TYPE_CHECKING, Any, Optional, Union

from iris_devtester.config.models import IRISConfig
from iris_devtester.connections.manager import get_connection
from iris_devtester.containers.monitoring import (
    MonitoringPolicy,
    configure_monitoring,
    disable_monitoring,
)
from iris_devtester.containers.performance import get_resource_metrics
from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy
from iris_devtester.utils.password_reset import reset_password_if_needed

if TYPE_CHECKING:
    from iris_devtester.config.container_config import ContainerConfig
    from iris_devtester.containers.models import HealthCheckLevel, ValidationResult
    from iris_devtester.ports.registry import PortRegistry

logger = logging.getLogger(__name__)

try:
    from testcontainers.iris import IRISContainer as BaseIRISContainer

    HAS_TESTCONTAINERS_IRIS = True
except ImportError:
    logger.warning("testcontainers-iris-python not installed.")
    HAS_TESTCONTAINERS_IRIS = False

    class BaseIRISContainer:
        def __init__(self, image: str = "", **kwargs):
            self.image = image
            self.port = 1972

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def start(self):
            logger.info("Mock IRIS container started (test mode)")
            return self

        def stop(self, *args, **kwargs):
            pass

        def get_wrapped_container(self):
            return None

        def with_env(self, key: str, value: str):
            return self

        def with_volume_mapping(self, host: str, container: str, mode: str = "rw"):
            return self

        def with_bind_ports(self, container: int, host: int):
            return self

        def with_name(self, name: str):
            return self

        def get_container_host_ip(self):
            return "localhost"

        def get_exposed_port(self, port: int):
            return port


class IRISContainer(BaseIRISContainer):
    """Enhanced IRIS container with automatic connection and password reset."""

    def __init__(
        self,
        image: str = "intersystemsdc/iris-community:latest",
        port_registry: Optional["PortRegistry"] = None,
        project_path: Optional[str] = None,
        preferred_port: Optional[int] = None,
        **kwargs,
    ):
        if not HAS_TESTCONTAINERS_IRIS:
            raise ImportError("testcontainers-iris-python not installed")

        # Extract known args for BaseIRISContainer if it's the mock one
        base_kwargs = {}
        if not HAS_TESTCONTAINERS_IRIS:
            base_kwargs = {
                k: v for k, v in kwargs.items() if k in ["username", "password", "namespace"]
            }

        super().__init__(image=image, **kwargs)
        self._connection = None
        self._config = None
        self._callin_enabled = False
        self._is_attached = False
        self._port_registry = port_registry
        self._port_assignment = None
        self._preferred_port = preferred_port
        self._cpf_manager = None
        self._cpf_merge_path = None
        self._project_path = project_path or os.getcwd()
        self._container_name = "iris_container"
        self._username = kwargs.get("username", "SuperUser")
        self._password = kwargs.get("password", "SYS")
        self._namespace = kwargs.get("namespace", "USER")

        # Password pre-configuration state (feature: 001-preconfigure-passwords)
        self._preconfigure_password: Optional[str] = None
        self._preconfigure_username: Optional[str] = None
        self._password_preconfigured: bool = False

    def _should_preconfigure(self) -> bool:
        """
        Determine if password pre-configuration should be used.

        Pre-configuration is enabled when:
        1. Programmatic API was called (with_preconfigured_password/with_credentials)
        2. IRIS_PASSWORD environment variable is set

        Returns:
            True if pre-configuration should be attempted, False otherwise.
        """
        if self._preconfigure_password is not None:
            return True
        return os.environ.get("IRIS_PASSWORD") is not None

    def _apply_password_preconfig(self) -> None:
        """
        Apply password pre-configuration by setting IRIS_PASSWORD/IRIS_USERNAME env vars.

        Priority: Programmatic API > Environment variables

        Sets environment variables on the container before start to enable
        IRIS to configure credentials during initial startup.
        """
        password = self._preconfigure_password or os.environ.get("IRIS_PASSWORD")
        username = self._preconfigure_username or os.environ.get("IRIS_USERNAME")

        if password:
            self.with_env("IRIS_PASSWORD", password)
            self._password = password
            logger.info("Pre-configuring IRIS password via environment variable")

        if username:
            self.with_env("IRIS_USERNAME", username)
            self._username = username
            logger.info(f"Pre-configuring IRIS username: {username}")

    def _verify_preconfig_success(self) -> bool:
        """
        Verify that pre-configured credentials work after container is ready.

        Attempts a connection using the pre-configured credentials with retries
        to allow the authentication subsystem to initialize.

        Returns:
            True if credentials work, False if fallback to password reset is needed.
        """
        for attempt in range(3):
            try:
                # Brief settle delay for auth subsystem (especially on macOS)
                if attempt > 0:
                    time.sleep(1.0)
                
                config = self.get_config()
                test_config = IRISConfig(
                    host=config.host,
                    port=config.port,
                    namespace=config.namespace,
                    username=self._username,
                    password=self._password,
                    container_name=self.get_container_name(),
                )
                conn = get_connection(test_config)
                if conn:
                    conn.close()
                    self._password_preconfigured = True
                    logger.info("Password pre-configuration verified successfully")
                    return True
            except Exception as e:
                logger.debug(f"Pre-configuration verification attempt {attempt + 1} failed: {e}")
        return False

    def get_assigned_port(self) -> int:
        """Get the port assigned to this container."""
        if os.environ.get("IRIS_TEST_MODE"):
            return self._port_assignment.port if self._port_assignment else 1972

        if self._port_assignment:
            return self._port_assignment.port
        return int(self.get_exposed_port(1972))

    def get_test_namespace(self) -> str:
        """Generate a unique test namespace."""
        import uuid

        ns = f"TEST_{str(uuid.uuid4())[:8].upper()}"
        self.execute_objectscript(f'Set status = ##class(Config.Namespaces).Create("{ns}",.p)')
        return ns

    def delete_namespace(self, namespace: str):
        """Delete a namespace."""
        self.execute_objectscript(f'Do ##class(Config.Namespaces).Delete("{namespace}")')

    def with_cpf_merge(self, path_or_content: str) -> "IRISContainer":
        """Configure a CPF merge file for the container."""
        from .cpf_manager import TempCPFManager

        if os.path.exists(path_or_content) and os.path.isfile(path_or_content):
            self._cpf_merge_path = os.path.abspath(path_or_content)
        else:
            if self._cpf_manager is None:
                self._cpf_manager = TempCPFManager()
            self._cpf_merge_path = self._cpf_manager.create_temp_cpf(path_or_content)

        container_path = "/usr/irissys/merge.cpf"
        self.with_env("ISC_CPF_MERGE_FILE", container_path)
        self.with_volume_mapping(self._cpf_merge_path, container_path, "ro")
        return self

    def with_preconfigured_password(self, password: str) -> "IRISContainer":
        """
        Configure password pre-configuration for faster container startup.

        Instead of resetting the password after container starts (5-10 second delay),
        this sets IRIS_PASSWORD environment variable so IRIS configures the password
        during initial startup.

        Args:
            password: Password to pre-configure for the default user.

        Returns:
            Self for method chaining.

        Example:
            >>> with IRISContainer.community().with_preconfigured_password("SYS") as iris:
            ...     conn = iris.get_connection()  # Immediate, no password reset delay
        """
        if not password:
            raise ValueError("Password cannot be empty")
        self._preconfigure_password = password
        return self

    def with_credentials(self, username: str, password: str) -> "IRISContainer":
        """
        Configure both username and password pre-configuration.

        Args:
            username: Username to pre-configure.
            password: Password to pre-configure.

        Returns:
            Self for method chaining.

        Example:
            >>> with IRISContainer.community().with_credentials("_SYSTEM", "SYS") as iris:
            ...     conn = iris.get_connection()
        """
        if not password:
            raise ValueError("Password cannot be empty")
        if not username:
            raise ValueError("Username cannot be empty")
        self._preconfigure_password = password
        self._preconfigure_username = username
        return self

    def start(self):
        """Start IRIS container with port registry integration and optional password pre-config."""
        if hasattr(self, "_is_attached") and self._is_attached:
            logger.info("Container is attached - skipping start()")
            return self

        if self._port_registry:
            self._port_assignment = self._port_registry.assign_port(
                project_path=self._project_path, preferred_port=self._preferred_port
            )
            assigned_port = self._port_assignment.port
            if self._config:
                self._config.port = assigned_port

            self.with_bind_ports(1972, assigned_port)
            self.port = assigned_port
            project_hash = hashlib.md5(self._project_path.encode()).hexdigest()[:8]
            container_name = f"iris_{project_hash}_{assigned_port}"
            self._port_assignment.container_name = container_name
            self.with_name(container_name)
            self._container_name = container_name

        use_preconfig = self._should_preconfigure()
        if use_preconfig:
            self._apply_password_preconfig()

        try:
            if HAS_TESTCONTAINERS_IRIS and not os.environ.get("IRIS_TEST_MODE"):
                result = super().start()
            else:
                logger.info("Mock IRIS container started (test mode)")
                result = self
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            raise

        if HAS_TESTCONTAINERS_IRIS and not os.environ.get("IRIS_TEST_MODE"):
            config = self.get_config()
            from iris_devtester.utils.password_reset import reset_password

            if use_preconfig and self._verify_preconfig_success():
                logger.info("Password pre-configuration successful, skipping password reset")
            else:
                if use_preconfig:
                    logger.info("Password pre-configuration failed, falling back to password reset")
                try:
                    reset_password(
                        container_name=self.get_container_name(),
                        username=config.username,
                        new_password=config.password,
                        hostname=None,
                        port=config.port,
                        namespace=config.namespace,
                        timeout=10,
                    )
                    # Mark password as ready after successful fallback
                    self._password_preconfigured = True
                except Exception as e:
                    logger.debug(f"Initial password reset failed (non-critical): {e}")

        return result

    def stop(self, *args, **kwargs):
        """Stop IRIS container and release resources."""
        try:
            super().stop(*args, **kwargs)
        finally:
            if self._port_registry and self._port_assignment:
                try:
                    self._port_registry.release_port(self._project_path)
                except Exception as e:
                    logger.warning(f"Failed to release port assignment: {e}")
            if self._cpf_manager:
                self._cpf_manager.cleanup()

    @classmethod
    def community(
        cls,
        namespace: str = "USER",
        username: str = "SuperUser",
        password: str = "SYS",
        **kwargs,
    ) -> "IRISContainer":
        """Create Community Edition IRIS container."""
        if "image" not in kwargs:
            if platform_module.machine() == "arm64":
                kwargs["image"] = "containers.intersystems.com/intersystems/iris-community:2025.1"
            else:
                kwargs["image"] = "intersystemsdc/iris-community:latest"

        container = cls(username=username, password=password, namespace=namespace, **kwargs)

        container._config = IRISConfig(
            host="localhost",
            port=1972,
            namespace=namespace,
            username=username,
            password=password,
            container_name=container.get_container_name(),
        )
        return container

    @classmethod
    def from_existing(cls, auto_discover: bool = True) -> Optional[IRISConfig]:
        """Detect existing IRIS instance."""
        if not auto_discover:
            return None
        from iris_devtester.config.auto_discovery import auto_discover_iris

        config_dict = auto_discover_iris()
        if config_dict is None:
            return None
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
        """Create Enterprise Edition IRIS container."""
        license_key = license_key or os.environ.get("IRIS_LICENSE_KEY")
        if license_key is None:
            raise ValueError("Enterprise Edition requires license key")

        if platform_module.machine() == "arm64":
            image = "containers.intersystems.com/intersystems/iris-arm64:2025.1"
        else:
            image = "intersystemsdc/iris:latest"

        container = cls(
            image=image, username=username, password=password, namespace=namespace, **kwargs
        )
        container.with_env("ISC_LICENSE_KEY", license_key)
        container._config = IRISConfig(
            host="localhost",
            port=1972,
            namespace=namespace,
            username=username,
            password=password,
            container_name=container.get_container_name(),
        )
        return container

    @classmethod
    def attach(cls, container_name: str) -> "IRISContainer":
        """Attach to existing IRIS container."""
        import subprocess

        check_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
        if container_name not in result.stdout:
            raise ValueError(f"Container '{container_name}' not found")

        port_cmd = ["docker", "port", container_name, "1972"]
        result = subprocess.run(port_cmd, capture_output=True, text=True, timeout=10)
        exposed_port = (
            int(result.stdout.strip().split(":")[-1])
            if result.returncode == 0 and result.stdout.strip()
            else 1972
        )

        instance = cls.__new__(cls)
        instance._connection = None
        instance._callin_enabled = False
        instance._is_attached = True
        instance._config = IRISConfig(
            host="localhost",
            port=exposed_port,
            namespace="USER",
            username="SuperUser",
            password="SYS",
            container_name=container_name,
        )
        instance._container_name = container_name
        return instance

    def get_connection(self, enable_callin: bool = True) -> Any:
        """Get database connection."""
        if self._connection is not None:
            return self._connection

        container_name = self.get_container_name()

        if enable_callin and not self._callin_enabled:
            self.enable_callin_service()

        from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords

        unexpire_all_passwords(container_name)

        from iris_devtester.utils.password_reset import reset_password

        config = self.get_config()

        # Only reset password if not already configured via pre-config or startup fallback
        if not self._password_preconfigured:
            reset_password(
                container_name=container_name,
                username=config.username,
                new_password=config.password,
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
            )
            self._password_preconfigured = True

        self._connection = get_connection(config)
        return self._connection

    def get_config(self) -> IRISConfig:
        """Get connection configuration."""
        if self._config is None:
            self._config = IRISConfig()
        try:
            if HAS_TESTCONTAINERS_IRIS and hasattr(self, "get_container_host_ip"):
                self._config = IRISConfig(
                    host=self.get_container_host_ip(),
                    port=int(self.get_exposed_port(1972)),
                    namespace=self._config.namespace,
                    username=self._config.username,
                    password=self._config.password,
                    container_name=self.get_container_name(),
                )
            elif self._is_attached:
                self._config.container_name = self.get_container_name()
        except Exception as e:
            logger.debug(f"Could not update config: {e}")
        return self._config

    def wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for IRIS to be fully ready."""
        config = self.get_config()
        strategy = IRISReadyWaitStrategy(port=config.port, timeout=timeout)
        try:
            ready = strategy.wait_until_ready(
                config.host, config.port, timeout, container_name=self.get_container_name()
            )
            if not ready:
                return False

            from iris_devtester.utils.password_reset import reset_password

            # Only reset password if not already configured
            if not self._password_preconfigured:
                # Convert result to bool to satisfy type checker
                result = reset_password(
                    container_name=self.get_container_name(),
                    username=config.username,
                    new_password=config.password,
                    hostname=None,
                    port=config.port,
                    namespace=config.namespace,
                )
                if hasattr(result, "success"):
                    success = bool(getattr(result, "success"))
                else:
                    success = bool(result[0])
                
                if success:
                    self._password_preconfigured = True
                return success
            
            return True
        except (TimeoutError, IndexError, TypeError):
            return False

    def reset_password(self, username: str = "_SYSTEM", new_password: str = "SYS") -> bool:
        """Reset user password."""
        from iris_devtester.utils.password_reset import reset_password

        config = self.get_config()
        result = reset_password(
            container_name=self.get_container_name(),
            username=username,
            new_password=new_password,
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
        )
        # Handle both Tuple[bool, str] and PasswordResetResult
        if hasattr(result, "success"):
            success = bool(getattr(result, "success"))
        elif isinstance(result, (list, tuple)):
            success = bool(result[0])
        else:
            success = False

        if success:
            config.password = new_password
        return success

    def get_container_name(self) -> str:
        """Get current container name."""
        if hasattr(self, "_is_attached") and self._is_attached:
            return self._container_name
        if HAS_TESTCONTAINERS_IRIS:
            try:
                wrapped = self.get_wrapped_container()
                if wrapped and hasattr(wrapped, "name"):
                    return str(wrapped.name)
            except Exception:
                pass
        return "iris_container"

    def get_project_path(self) -> Optional[str]:
        """Get project path if port registry is used."""
        if self._port_registry:
            return self._project_path
        return None

    def enable_callin_service(self) -> bool:
        """Enable CallIn service."""
        if self._callin_enabled:
            return True
        try:
            container_name = self.get_container_name()
            script = 'Do ##class(Security.Services).Get("%Service_CallIn",.p) Set p("Enabled")=1,p("AutheEnabled")=48 Do ##class(Security.Services).Modify("%Service_CallIn",.p) Write "OK" Halt'
            cmd = [
                "docker",
                "exec",
                "-u",
                "root",
                container_name,
                "sh",
                "-c",
                f'iris session IRIS -U %SYS << "EOF"\n{script}\nEOF',
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "OK" in result.stdout:
                self._callin_enabled = True
                return True
            return False
        except Exception:
            return False

    def check_callin_enabled(self) -> bool:
        """Check if CallIn is enabled."""
        try:
            script = 'Do ##class(Security.Services).Get("%Service_CallIn",.s) Write s.Enabled'
            cmd = [
                "docker",
                "exec",
                self.get_container_name(),
                "iris",
                "session",
                "IRIS",
                "-U",
                "%SYS",
                script,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            is_enabled = result.returncode == 0 and "1" in result.stdout
            if is_enabled:
                self._callin_enabled = True
            return is_enabled
        except Exception:
            return False

    def execute_objectscript(self, code: str, namespace: Optional[str] = None) -> str:
        """Execute ObjectScript code."""
        ns = namespace or self.get_config().namespace
        if "Halt" not in code:
            code += "\nHalt"
        cmd = [
            "docker",
            "exec",
            self.get_container_name(),
            "sh",
            "-c",
            f'iris session IRIS -U {ns} << "EOF"\n{code}\nEOF',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"OS failed: {result.stderr}")
        return result.stdout

    def validate(self, level: Any = None) -> Any:
        """Validate container health."""
        from iris_devtester.containers.models import HealthCheckLevel
        from iris_devtester.containers.validation import validate_container

        return validate_container(
            container_name=self.get_container_name(),
            level=level or HealthCheckLevel.STANDARD,
            docker_client=None,
        )

    def assert_healthy(self, level: Any = None):
        """Raise if not healthy."""
        res = self.validate(level=level)
        if not res.success:
            raise RuntimeError(res.format_message())

    @classmethod
    def from_config(cls, config: Any) -> "IRISContainer":
        """Create from ContainerConfig."""
        image = config.get_image_name()
        if getattr(config, "edition", "community") == "community":
            container = cls.community(
                namespace=getattr(config, "namespace", "USER"),
                username=getattr(config, "username", "SuperUser"),
                password=getattr(config, "password", "SYS"),
                image=image,
            )
        else:
            container = cls.enterprise(
                license_key=getattr(config, "license_key", None),
                namespace=getattr(config, "namespace", "USER"),
                username=getattr(config, "username", "SuperUser"),
                password=getattr(config, "password", "SYS"),
                image=image,
            )
        if getattr(config, "cpf_merge", None):
            container.with_cpf_merge(config.cpf_merge)
        return container
