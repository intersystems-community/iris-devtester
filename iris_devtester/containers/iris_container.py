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
from typing import Any, Optional, TYPE_CHECKING, Union

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

if TYPE_CHECKING:
    from iris_devtester.ports.registry import PortRegistry
    from iris_devtester.containers.models import HealthCheckLevel, ValidationResult
    from iris_devtester.config.container_config import ContainerConfig

logger = logging.getLogger(__name__)

try:
    from testcontainers.iris import IRISContainer as BaseIRISContainer
    HAS_TESTCONTAINERS_IRIS = True
except ImportError:
    logger.warning("testcontainers-iris-python not installed.")
    HAS_TESTCONTAINERS_IRIS = False

    class BaseIRISContainer:
        def __init__(self, image: str = None, **kwargs):
            self.image = image
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def start(self): return self
        def stop(self, **kwargs): pass
        def get_wrapped_container(self): return None
        def with_env(self, key: str, value: str): return self
        def with_volume_mapping(self, host: str, container: str, mode: str = "rw"): return self
        def with_bind_ports(self, container: int, host: int): return self
        def with_name(self, name: str): return self
        def get_container_host_ip(self): return "localhost"
        def get_exposed_port(self, port: int): return port


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

    def start(self):
        """Start IRIS container with port registry integration."""
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

        result = super().start()
        self.wait_for_ready()

        if self._config:
            self._config.host = self.get_container_host_ip()
            if self._port_registry:
                self._config.port = self._port_assignment.port
            else:
                self._config.port = int(self.get_exposed_port(self.port))

        return result

    def stop(self, force=True, delete_volume=True):
        """Stop IRIS container and release resources."""
        try:
            super().stop()
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

        container = cls(
            username=username,
            password=password,
            namespace=namespace,
            **kwargs
        )

        container._config = IRISConfig(
            host="localhost",
            port=1972,
            namespace=namespace,
            username=username,
            password=password,
            container_name=container.get_container_name()
        )
        return container

    @classmethod
    def from_existing(cls, auto_discover: bool = True) -> Optional[IRISConfig]:
        """Detect existing IRIS instance."""
        if not auto_discover: return None
        from iris_devtester.config.auto_discovery import auto_discover_iris
        config_dict = auto_discover_iris()
        if config_dict is None: return None
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
            image=image,
            username=username,
            password=password,
            namespace=namespace,
            **kwargs
        )
        container.with_env("ISC_LICENSE_KEY", license_key)
        container._config = IRISConfig(
            host="localhost",
            port=1972,
            namespace=namespace,
            username=username,
            password=password,
            container_name=container.get_container_name()
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
        exposed_port = int(result.stdout.strip().split(":")[-1]) if result.returncode == 0 and result.stdout.strip() else 1972

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
            container_name=container_name
        )
        instance._container_name = container_name
        return instance

    def get_connection(self, enable_callin: bool = True) -> Any:
        """Get database connection."""
        if self._connection is not None: return self._connection
        
        container_name = self.get_container_name()
        
        if enable_callin and not self._callin_enabled:
            self.enable_callin_service()

        from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords
        unexpire_all_passwords(container_name)

        from iris_devtester.utils.password_reset import reset_password
        config = self.get_config()
        
        reset_password(
            container_name=container_name,
            username=config.username,
            new_password=config.password,
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
        )

        self._connection = get_connection(config)
        return self._connection

    def get_config(self) -> IRISConfig:
        """Get connection configuration."""
        if self._config is None: self._config = IRISConfig()
        try:
            if HAS_TESTCONTAINERS_IRIS and hasattr(self, "get_container_host_ip"):
                self._config = IRISConfig(
                    host=self.get_container_host_ip(),
                    port=int(self.get_exposed_port(1972)),
                    namespace=self._config.namespace,
                    username=self._config.username,
                    password=self._config.password,
                    container_name=self.get_container_name()
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
                config.host, 
                config.port, 
                timeout, 
                container_name=self.get_container_name()
            )
            if not ready: return False
            
            from iris_devtester.utils.password_reset import reset_password
            reset_password(
                container_name=self.get_container_name(), 
                username=config.username, 
                new_password=config.password, 
                hostname=None, 
                port=config.port, 
                namespace=config.namespace
            )
            return True
        except TimeoutError: return False

    def reset_password(self, username: str = "_SYSTEM", new_password: str = "SYS") -> bool:
        """Reset user password."""
        from iris_devtester.utils.password_reset import reset_password
        config = self.get_config()
        success, message = reset_password(
            container_name=self.get_container_name(), 
            username=username, 
            new_password=new_password, 
            hostname=config.host, 
            port=config.port, 
            namespace=config.namespace
        )
        if success: config.password = new_password
        return success

    def get_container_name(self) -> str:
        """Get current container name."""
        if hasattr(self, "_is_attached") and self._is_attached: return self._container_name
        if HAS_TESTCONTAINERS_IRIS:
            try: return self.get_wrapped_container().name
            except Exception: pass
        return "iris_container"

    def enable_callin_service(self) -> bool:
        """Enable CallIn service."""
        if self._callin_enabled: return True
        try:
            container_name = self.get_container_name()
            script = 'Do ##class(Security.Services).Get("%Service_CallIn",.p) Set p("Enabled")=1,p("AutheEnabled")=48 Do ##class(Security.Services).Modify("%Service_CallIn",.p) Write "OK" Halt'
            cmd = ["docker", "exec", "-u", "root", container_name, "sh", "-c", f'iris session IRIS -U %SYS << "EOF"\n{script}\nEOF']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "OK" in result.stdout:
                self._callin_enabled = True
                return True
            return False
        except Exception: return False

    def check_callin_enabled(self) -> bool:
        """Check if CallIn is enabled."""
        try:
            script = 'Do ##class(Security.Services).Get("%Service_CallIn",.s) Write s.Enabled'
            cmd = ["docker", "exec", self.get_container_name(), "iris", "session", "IRIS", "-U", "%SYS", script]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            is_enabled = result.returncode == 0 and "1" in result.stdout
            if is_enabled: self._callin_enabled = True
            return is_enabled
        except Exception: return False

    def execute_objectscript(self, code: str, namespace: Optional[str] = None) -> str:
        """Execute ObjectScript code."""
        ns = namespace or self.get_config().namespace
        if "Halt" not in code: code += "\nHalt"
        cmd = ["docker", "exec", self.get_container_name(), "sh", "-c", f'iris session IRIS -U {ns} << "EOF"\n{code}\nEOF']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0: raise RuntimeError(f"OS failed: {result.stderr}")
        return result.stdout

    def validate(self, level: Any = None) -> Any:
        """Validate container health."""
        from iris_devtester.containers.models import HealthCheckLevel
        from iris_devtester.containers.validation import validate_container
        return validate_container(container_name=self.get_container_name(), level=level or HealthCheckLevel.STANDARD, docker_client=None)

    def assert_healthy(self, level: Any = None):
        """Raise if not healthy."""
        res = self.validate(level=level)
        if not res.success: raise RuntimeError(res.format_message())

    @classmethod
    def from_config(cls, config: Any) -> "IRISContainer":
        """Create from ContainerConfig."""
        image = config.get_image_name()
        if getattr(config, "edition", "community") == "community":
            container = cls.community(namespace=getattr(config, "namespace", "USER"), username=getattr(config, "username", "SuperUser"), password=getattr(config, "password", "SYS"), image=image)
        else:
            container = cls.enterprise(license_key=getattr(config, "license_key", None), namespace=getattr(config, "namespace", "USER"), username=getattr(config, "username", "SuperUser"), password=getattr(config, "password", "SYS"), image=image)
        if getattr(config, "cpf_merge", None): container.with_cpf_merge(config.cpf_merge)
        return container
