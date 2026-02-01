import logging
import subprocess
import time
from typing import Any, Optional

from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection

logger = logging.getLogger(__name__)


# Single base class definition to satisfy LSP
class _IRISMockContainer:
    def __init__(self, image: str = "", **kwargs):
        self.image = image
        self._container = None

    def start(self):
        return self

    def stop(self, *args, **kwargs):
        pass

    def get_container_host_ip(self) -> str:
        return "localhost"

    def get_exposed_port(self, port: int) -> int:
        return port

    def with_env(self, key: str, value: str):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get_container_name(self) -> str:
        return "iris_db"


# Select the base class. We use Any type to bypass strict type check on the class itself.
IRISBase: Any = _IRISMockContainer

# Check for testcontainers
HAS_TESTCONTAINERS = False
try:
    from testcontainers.iris import IRISContainer as _ActualBase

    IRISBase = _ActualBase
    HAS_TESTCONTAINERS = True
except ImportError:
    pass


class IRISContainer(IRISBase):
    """
    Enhanced IRIS container with automatic connection and password management.
    """

    def __init__(
        self,
        image: str = "intersystemsdc/iris-community:latest",
        username: str = "SuperUser",
        password: str = "SYS",
        namespace: str = "USER",
        **kwargs,
    ):
        if not HAS_TESTCONTAINERS:
            logger.warning("testcontainers not installed. Functionality will be limited.")

        super().__init__(image=image, **kwargs)
        self._username = username
        self._password = password
        self._namespace = namespace
        self._connection = None
        self._callin_enabled = False
        self._password_preconfigured = False
        self._is_attached = False
        self._container_name: Optional[str] = kwargs.get("name")
        self._config: Optional[IRISConfig] = None

        # Standard attributes used by fixtures
        # IMPORTANT: self.port must remain the INTERNAL container port (1972)
        # for testcontainers' get_exposed_port() to work correctly.
        # Use self._mapped_port for the host-side mapped port.
        self.host = "localhost"
        self.port = 1972  # Internal container port - DO NOT CHANGE
        self._mapped_port: Optional[int] = None  # Host-side mapped port

        # Pre-configuration fields (Feature 001)
        self._preconfigure_password: Optional[str] = None
        self._preconfigure_username: Optional[str] = None

    @classmethod
    def community(cls, image: Optional[str] = None, **kwargs) -> "IRISContainer":
        """Create a Community Edition container."""
        if image is None:
            import platform as platform_module

            if platform_module.machine() == "arm64":
                image = "containers.intersystems.com/intersystems/iris-community:2025.1"
            else:
                image = "intersystemsdc/iris-community:latest"
        return cls(image=image, **kwargs)

    @classmethod
    def enterprise(cls, license_key: str, image: Optional[str] = None, **kwargs) -> "IRISContainer":
        """Create an Enterprise Edition container."""
        if image is None:
            image = "containers.intersystems.com/intersystems/iris:latest"
        container = cls(image=image, **kwargs)
        return container

    def with_name(self, name: str) -> "IRISContainer":
        """Set the container name."""
        self._container_name = name
        if hasattr(self, "with_kwargs"):
            self.with_kwargs(name=name)
        return self

    def get_container_name(self) -> str:
        """Get the actual container name."""
        # Priority 1: Explicit name set by with_name()
        if self._container_name:
            return self._container_name

        # Priority 2: Get from actual Docker container (after start)
        try:
            if hasattr(self, "_container") and self._container is not None:
                return str(self._container.name)
        except Exception:
            pass

        # Priority 3: Try parent class method (testcontainers might have one)
        try:
            parent_name = super().get_container_name()
            if parent_name and parent_name != "iris_db":
                return str(parent_name)
        except Exception:
            pass

        # Fallback - but this is problematic if container isn't started yet
        return "iris_db"

    def execute_objectscript(self, script: str, namespace: Optional[str] = None) -> str:
        """Execute ObjectScript in the container."""
        container_name = self.get_container_name()
        ns = namespace or self._namespace

        cmd = ["docker", "exec", "-i", container_name, "iris", "session", "IRIS", "-U", ns]

        result = subprocess.run(
            cmd, input=f"{script}\nHalt\n".encode("utf-8"), capture_output=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"OS failed: {result.stderr.decode()}")

        return result.stdout.decode("utf-8", errors="replace")

    def enable_callin_service(self) -> bool:
        """Enable the CallIn service (required for DBAPI)."""
        if self._callin_enabled:
            return True

        from iris_devtester.utils.enable_callin import enable_callin_service

        success, msg = enable_callin_service(self.get_container_name())
        if success:
            self._callin_enabled = True
            return True
        else:
            logger.error(f"Failed to enable CallIn: {msg}")
            return False

    def check_callin_enabled(self) -> bool:
        """Check if CallIn is enabled."""
        try:
            script = 'Do ##class(Security.Services).Get("%Service_CallIn",.p) Write "ENABLED:",p("Enabled")'
            output = self.execute_objectscript(script, namespace="%SYS")
            is_enabled = "ENABLED:1" in output
            if is_enabled:
                self._callin_enabled = True
            return is_enabled
        except Exception:
            return False

    def get_test_namespace(self, prefix: str = "TEST") -> str:
        """Generate a unique test namespace with its own database."""
        import uuid

        ns = f"{prefix}_{str(uuid.uuid4())[:8].upper()}"
        db_dir = f"/usr/irissys/mgr/db_{ns.lower()}"

        script = f"""
 Set ns="{ns}"
 Set dbDir="{db_dir}"
 If '##class(%File).DirectoryExists(dbDir) Do ##class(%File).CreateDirectoryChain(dbDir)
 Set db=##class(SYS.Database).%New() Set db.Directory=dbDir Do db.%Save()
 Do ##class(Config.Databases).Create(ns,dbDir)
 Set p("Globals")=ns,p("Routines")=ns Do ##class(Config.Namespaces).Create(ns,.p)
 Write "SUCCESS" Halt
 """
        self.execute_objectscript(script, namespace="%SYS")
        return ns

    def delete_namespace(self, namespace: str):
        """Delete a namespace and its associated database files cleanly."""
        script = f"""
 Set ns="{namespace}"
 Do ##class(Config.Namespaces).Delete(ns)
 If ##class(Config.Databases).Get(ns,.p) {{
     Set dir = p("Directory")
     Do ##class(SYS.Database).DismountDatabase(dir)
     Do ##class(Config.Databases).Delete(ns)
     Do ##class(%File).RemoveDirectoryTree(dir)
 }}
 Write "SUCCESS" Halt
 """
        self.execute_objectscript(script, namespace="%SYS")

    def get_config(self) -> IRISConfig:
        """Get connection configuration."""
        if self._config is None:
            self._config = IRISConfig(
                username=self._username,
                password=self._password,
                namespace=self._namespace,
                container_name=self.get_container_name(),
            )
        config = self._config
        try:
            # Get host and mapped port from testcontainers
            # IMPORTANT: self.port must remain 1972 (internal port) for get_exposed_port() to work
            self.host = self.get_container_host_ip()
            self._mapped_port = int(self.get_exposed_port(1972))  # Use internal port to get mapping
            config.host = self.host
            config.port = self._mapped_port  # Config uses the host-mapped port for connections
        except Exception:
            pass
        return config

    def get_mapped_port(self, internal_port: int = 1972) -> int:
        """Get the host-side mapped port for a given internal container port.

        This is a convenience wrapper around get_exposed_port() that ensures
        we always pass the internal port (not the host port).

        Args:
            internal_port: The port inside the container (default: 1972 for IRIS superserver)

        Returns:
            The host-side port that maps to the internal port
        """
        if self._mapped_port is not None and internal_port == 1972:
            return self._mapped_port
        return int(self.get_exposed_port(internal_port))

    def get_connection(self, enable_callin: bool = True) -> Any:
        """Get database connection."""
        if self._connection is not None:
            return self._connection

        if enable_callin:
            self.enable_callin_service()

        from iris_devtester.utils.password import unexpire_all_passwords

        unexpire_all_passwords(self.get_container_name())

        config = self.get_config()
        from iris_devtester.connections.connection import get_connection as get_modern_connection

        self._connection = get_modern_connection(config)
        return self._connection

    def with_preconfigured_password(self, password: str) -> "IRISContainer":
        """Set password for pre-configuration."""
        if not password:
            raise ValueError("Password cannot be empty")
        self._preconfigure_password = password
        self._password = password
        return self

    def with_credentials(self, username: str, password: str) -> "IRISContainer":
        """Set credentials for pre-configuration."""
        if not username:
            raise ValueError("Username cannot be empty")
        if not password:
            raise ValueError("Password cannot be empty")
        self._preconfigure_username = username
        self._preconfigure_password = password
        self._username = username
        self._password = password
        return self

    def start(self) -> "IRISContainer":
        """Start container with pre-config support."""
        if self._preconfigure_password:
            self.with_env("IRIS_PASSWORD", self._preconfigure_password)
        if self._preconfigure_username:
            self.with_env("IRIS_USERNAME", self._preconfigure_username)

        super().start()
        # Ensure host/port are updated after start
        self.get_config()
        self._password_preconfigured = True
        return self

    def wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for IRIS to be ready."""
        # Simple wait for prototype
        time.sleep(15)
        return True
