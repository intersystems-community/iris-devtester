import logging
import subprocess
import time
from typing import Any, Optional

from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection
from iris_devtester.containers.models import HealthCheckLevel, ValidationResult

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

    Lifecycle: Containers created via Python (community(), enterprise(), light()) are
    managed by testcontainers Ryuk, which removes them when the Python process exits.
    This is correct for pytest fixtures but means containers do NOT persist after your
    script ends. For persistent containers, use ``idt container up`` (CLI, no Ryuk) and
    reconnect with ``IRISContainer.attach(name)``.
    """

    # Custom kwargs that should NOT be passed to parent/Docker SDK
    _CUSTOM_KWARGS = {"port_registry", "preferred_port", "project_path"}

    def __init__(
        self,
        image: str = "intersystemsdc/iris-community:latest",
        username: str = "_SYSTEM",
        password: str = "SYS",
        namespace: str = "USER",
        **kwargs,
    ):
        if not HAS_TESTCONTAINERS:
            logger.warning("testcontainers not installed. Functionality will be limited.")

        # Extract custom kwargs before passing to parent
        self._port_registry = kwargs.pop("port_registry", None)
        self._preferred_port = kwargs.pop("preferred_port", None)
        self._project_path = kwargs.pop("project_path", None)
        self._port_assignment = None  # Will be set in start() if port_registry is used

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
        self._mapped_port: Optional[int] = None  # Host-side mapped port (1972 only, cached)
        self._port_cache: dict[int, int] = {}  # Host-side mapped port cache for all internal ports

        # Pre-configuration fields (Feature 001)
        self._preconfigure_password: Optional[str] = None
        self._preconfigure_username: Optional[str] = None

    def get_password(self) -> str:
        """Return the currently configured password."""
        return self._password

    def get_username(self) -> str:
        """Return the currently configured username."""
        return self._username

    @classmethod
    def dev(cls, **kwargs) -> "IRISContainer":
        """
        Attach to or start the global persistent Dev Instance.
        
        This provides 'Warm Start' capability with instant connectivity.
        Isolation is handled automatically via project-specific namespaces.
        
        Args:
            **kwargs: Additional configuration (username, password).
            
        Returns:
            An IRISContainer instance attached to the dev engine.
        """
        from iris_devtester.containers.dev_instance import DevInstanceManager, get_project_namespace
        
        manager = DevInstanceManager()
        instance = manager.ensure_ready()
        
        # Determine namespace for current project
        project_ns = get_project_namespace()
        kwargs.setdefault("namespace", project_ns)
        
        container_name = str(instance.name) if instance.name else "iris_db"
        return cls.attach(container_name, **kwargs)

    @classmethod
    def community(
        cls, image: Optional[str] = None, version: str = "latest", **kwargs
    ) -> "IRISContainer":
        """
        Create a Community Edition container.

        Auto-detects architecture (ARM64 vs x86) and pulls the appropriate image.
        Container is cleaned up by Ryuk on process exit. For persistent containers,
        use ``idt container up`` and ``IRISContainer.attach(name)``.

        Args:
            image: Docker image to use. If None, auto-detects based on architecture.
            version: Image version tag. Options: 'latest', '2025.1', '2025.2', etc.
        """
        if image is None:
            import platform as platform_module

            if platform_module.machine() == "arm64":
                # ARM64 (Apple Silicon) - use official InterSystems registry
                tag = version if version != "latest" else "2025.1"
                image = f"containers.intersystems.com/intersystems/iris-community:{tag}"
            else:
                # x86_64 - use Docker Hub community image
                image = f"intersystemsdc/iris-community:{version}"
        return cls(image=image, **kwargs)

    @classmethod
    def enterprise(
        cls, license_key: Optional[str] = None, image: Optional[str] = None, **kwargs
    ) -> "IRISContainer":
        """
        Create an Enterprise Edition container.

        Container is cleaned up by Ryuk on process exit. For persistent containers,
        use ``idt container up`` and ``IRISContainer.attach(name)``.

        Args:
            license_key: Path to iris.key file. If None, checks IRIS_LICENSE_KEY env var.
            image: Docker image to use. Defaults to containers.intersystems.com/intersystems/iris:latest

        Raises:
            ValueError: If no license key is provided or found in environment.
        """
        import os

        if license_key is None:
            license_key = os.environ.get("IRIS_LICENSE_KEY")

        if license_key is None:
            raise ValueError(
                "Enterprise edition requires a license key.\n"
                "\n"
                "Provide license_key parameter or set IRIS_LICENSE_KEY environment variable:\n"
                "  IRISContainer.enterprise(license_key='/path/to/iris.key')\n"
                "  # or\n"
                "  export IRIS_LICENSE_KEY=/path/to/iris.key"
            )

        if not os.path.exists(license_key):
            raise ValueError(
                f"License key file not found: {license_key}\n"
                "\n"
                "Verify the license key path exists and is readable."
            )

        if image is None:
            image = "containers.intersystems.com/intersystems/iris:latest"

        container = cls(image=image, **kwargs)
        # Mount license key into container
        container._license_key_path = license_key
        return container

    @classmethod
    def light(
        cls, image: Optional[str] = None, version: str = "latest", **kwargs
    ) -> "IRISContainer":
        """
        Create a Light Edition container optimized for CI/CD.

        Light edition is ~85% smaller than full Community edition (~580MB vs ~3.5GB).
        It removes Interoperability, Management Portal, DeepSee, and web components.
        DBAPI, JDBC, and ODBC connectivity are fully supported.
        Container is cleaned up by Ryuk on process exit.

        Args:
            image: Docker image to use. Defaults to caretdev/iris-community-light.
            version: Image version tag. Options: 'latest', 'latest-em' (LTS), '2025.1', etc.

        Best for:
            - CI/CD pipelines
            - Microservices
            - Automated testing
            - SQL-only workloads

        Not supported:
            - Interoperability/Ensemble
            - Management Portal
            - DeepSee/BI
            - CSP/REST web framework
        """
        if image is None:
            # Use latest-em for LTS stability, or allow version override
            tag = version if version != "latest" else "latest-em"
            image = f"caretdev/iris-community-light:{tag}"
        return cls(image=image, **kwargs)

    @classmethod
    def attach(cls, container_name: str, **kwargs) -> "IRISContainer":
        """
        Attach to an existing IRIS container by name.

        Use this to reconnect to persistent containers started by ``idt container up``
        or docker-compose. Unlike containers created via community()/enterprise()/light(),
        CLI-managed containers are NOT cleaned up by Ryuk and persist across process exits.

        Args:
            container_name: Name of the existing Docker container.
            **kwargs: Additional configuration (username, password, namespace).

        Returns:
            An IRISContainer instance attached to the existing container.
        """
        if not container_name:
            raise ValueError("container_name must be a non-empty string")

        instance = cls(image="", name=container_name, **kwargs)
        instance._is_attached = True
        instance._container_name = container_name

        try:
            import docker

            client = docker.from_env()
            container = client.containers.get(container_name)
            instance._container = container

            # If it's a mock container, we need to set these manually
            if not HAS_TESTCONTAINERS:
                instance.host = "localhost"
                # Try to find port from container ports
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                if "1972/tcp" in ports and ports["1972/tcp"]:
                    instance._mapped_port = int(ports["1972/tcp"][0]["HostPort"])
            else:
                # testcontainers will handle discovery via get_config()
                instance.get_config()

        except Exception as e:
            # For attached containers, we MUST find the container to be useful
            raise ValueError(
                f"Container '{container_name}' not found or not running\n"
                "\n"
                "What went wrong:\n"
                f"  {str(e)}\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify the container name is correct: docker ps\n"
                "  2. Ensure the container is started: docker start <name>\n"
                "  3. Check if your user has permission to access the Docker socket"
            )

        return instance

    def with_name(self, name: str) -> "IRISContainer":
        """Set the container name."""
        self._container_name = name
        # Use parent's _name attribute directly - do NOT use with_kwargs(name=...)
        # as that causes duplicate 'name' kwarg in Docker's run() call
        # (parent passes both name=self._name and **self._kwargs to run())
        self._name = name
        return self

    def with_cpf_merge(self, cpf_content_or_path: str) -> "IRISContainer":
        """Configure CPF merge for IRIS startup customization.

        CPF merge allows customizing IRIS configuration at startup time
        using a merge file that is applied during container initialization.
        This enables features like:
        - Enabling CallIn service automatically
        - Setting memory configuration
        - Pre-configuring users and security settings

        Args:
            cpf_content_or_path: Either a CPF merge content string or a
                path to a CPF merge file. If the string contains newlines
                or CPF section markers like "[Actions]", it's treated as
                content. Otherwise, it's treated as a file path.

        Returns:
            Self for method chaining.

        Examples:
            >>> # From preset content
            >>> iris = IRISContainer.community().with_cpf_merge(CPFPreset.ENABLE_CALLIN)

            >>> # From file path
            >>> iris = IRISContainer.community().with_cpf_merge("/path/to/merge.cpf")
        """
        import os
        import tempfile

        # Determine if it's content or a file path
        is_content = "\n" in cpf_content_or_path or "[" in cpf_content_or_path

        if is_content:
            # Write content to a temporary file
            # Note: The temp file needs to persist until container is started
            if not hasattr(self, "_cpf_temp_files"):
                self._cpf_temp_files = []

            fd, temp_path = tempfile.mkstemp(suffix=".cpf", prefix="iris_merge_")
            os.write(fd, cpf_content_or_path.encode("utf-8"))
            os.close(fd)
            self._cpf_temp_files.append(temp_path)
            host_path = temp_path
        else:
            # Treat as file path
            host_path = os.path.abspath(cpf_content_or_path)
            if not os.path.exists(host_path):
                raise FileNotFoundError(f"CPF merge file not found: {host_path}")

        # Container path for the merge file
        container_path = "/tmp/merge.cpf"

        # Mount the CPF file into the container
        if hasattr(self, "with_volume_mapping"):
            self.with_volume_mapping(host_path, container_path, "ro")

        # Set the environment variable to tell IRIS to use the merge file
        if hasattr(self, "with_env"):
            self.with_env("ISC_CPF_MERGE_FILE", container_path)

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

        cmd = ["docker", "exec", "-u", "irisowner", "-i", container_name, "iris", "session", "IRIS", "-U", ns]

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
        """Get connection configuration.

        Note: Credentials are always read fresh from _username/_password
        to support credential updates after container start.
        """
        # Always create fresh config to pick up any credential changes
        # (e.g., conftest may update _username/_password after start())
        config = IRISConfig(
            username=self._username,
            password=self._password,
            namespace=self._namespace,
            container_name=self.get_container_name(),
        )
        self._config = config
        try:
            discovered_host = self.get_container_host_ip()
            if discovered_host in ("0.0.0.0", "::"):
                discovered_host = "localhost"
            self.host = discovered_host
            self._mapped_port = self.get_mapped_port(1972)
            config.host = self.host
            config.port = self._mapped_port
        except ConnectionError:
            pass
        return config

    def get_mapped_port(self, internal_port: int = 1972) -> int:
        """Get the host-side port that maps to the given internal container port.

        In Docker-in-Docker (DinD) environments, the outer host's port bindings are
        not visible to the inner Docker daemon. testcontainers raises ConnectionError
        from DockerClient.port() in that case. We catch it and return the internal
        port directly — which is reachable via the container's bridge/gateway IP.

        Args:
            internal_port: Port inside the container (1972 = IRIS SuperServer, 52773 = web)

        Returns:
            Host-side mapped port, or internal_port if mapping is unavailable (DinD).
        """
        if internal_port == 1972 and self._mapped_port is not None:
            return self._mapped_port
        if internal_port in self._port_cache:
            return self._port_cache[internal_port]
        try:
            host_port = int(self.get_exposed_port(internal_port))
            self._port_cache[internal_port] = host_port
            return host_port
        except ConnectionError:
            self._port_cache[internal_port] = internal_port
            return internal_port

    def get_connection(self, enable_callin: bool = True) -> Any:
        """Get database connection."""
        if self._connection is not None:
            return self._connection

        if enable_callin:
            self.enable_callin_service()

        from iris_devtester.utils.password import unexpire_all_passwords

        unexpire_all_passwords(self.get_container_name())

        config = self.get_config()
        self._connection = get_connection(config)
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

    def reset_password(
        self, username: str = "_SYSTEM", new_password: str = "SYS", timeout: int = 30
    ) -> bool:
        """
        Reset password for a user in this container.

        Args:
            username: Username to reset
            new_password: New password to set
            timeout: Timeout in seconds

        Returns:
            True if successful
        """
        from iris_devtester.utils.password import reset_password as reset_func

        config = self.get_config()
        result = reset_func(
            container_name=self.get_container_name(),
            username=username,
            new_password=new_password,
            timeout=timeout,
            hostname=config.host,
            port=config.port,
        )
        if result.success:
            self._password = new_password
            return True
        return False

    def start(self) -> "IRISContainer":
        """Start container with pre-config support and port registry integration."""
        if self._preconfigure_password:
            self.with_env("IRIS_PASSWORD", self._preconfigure_password)
        if self._preconfigure_username:
            self.with_env("IRIS_USERNAME", self._preconfigure_username)

        # Port registry integration: assign port before starting
        if self._port_registry is not None and self._project_path is not None:
            self._port_assignment = self._port_registry.assign_port(
                project_path=self._project_path,
                preferred_port=self._preferred_port,
            )
            # Configure container to use the assigned port
            # Note: testcontainers uses with_bind_ports() for port mapping
            if hasattr(self, "with_bind_ports"):
                self.with_bind_ports(1972, self._port_assignment.port)

        super().start()
        # Ensure host/port are updated after start
        self.get_config()
        self._password_preconfigured = True
        return self

    def get_assigned_port(self) -> Optional[int]:
        """
        Get the port assigned by the port registry.

        Returns:
            The assigned port number, or None if no port registry was used.
        """
        if hasattr(self, "_port_assignment") and self._port_assignment is not None:
            return self._port_assignment.port
        return None

    def get_project_path(self) -> Optional[str]:
        """
        Get the project path associated with this container.

        Returns:
            The project path, or None if no port registry was used.
        """
        return self._project_path

    def wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for IRIS to be ready."""
        # Simple wait for prototype
        time.sleep(15)
        return True

    def validate(self, level: HealthCheckLevel = HealthCheckLevel.STANDARD) -> ValidationResult:
        """Validate this container's health status.

        Args:
            level: Validation depth level (MINIMAL, STANDARD, or FULL).

        Returns:
            ValidationResult with success status, details, and remediation steps.

        Examples:
            >>> with IRISContainer.community() as iris:
            ...     result = iris.validate()
            ...     assert result.success is True
        """
        # Import here to avoid circular import
        from iris_devtester.containers.validation import validate_container

        container_name = self.get_container_name()
        return validate_container(container_name=container_name, level=level)

    def assert_healthy(self, level: HealthCheckLevel = HealthCheckLevel.STANDARD) -> None:
        """Assert that this container is healthy, raising RuntimeError if not.

        Args:
            level: Validation depth level (MINIMAL, STANDARD, or FULL).

        Raises:
            RuntimeError: If container validation fails, with structured error
                message including "What went wrong" and "How to fix it" sections.

        Examples:
            >>> with IRISContainer.community() as iris:
            ...     iris.assert_healthy()  # No exception = healthy
        """
        result = self.validate(level=level)
        if not result.success:
            raise RuntimeError(result.format_message())
