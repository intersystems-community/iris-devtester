import logging
import subprocess
import time
from typing import Any, Optional

from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection
from iris_devtester.containers.connection_info import IRISConnectionInfo
from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus, HealthCheckLevel, ValidationResult
from iris_devtester.utils.password import reset_password, unexpire_all_passwords

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
        self.port = 1972
        self._mapped_port: Optional[int] = None
        self._port_cache: dict[int, int] = {}
        self._password_handled: bool = False

        # Pre-configuration fields (Feature 001)
        self._preconfigure_password: Optional[str] = None
        self._preconfigure_username: Optional[str] = None

    def get_password(self) -> str:
        """Return the currently configured password."""
        return self._password

    def get_username(self) -> str:
        """Return the currently configured username."""
        return self._username

    def stop_gracefully(self, timeout: int = 30) -> bool:
        """Stop IRIS cleanly before stopping the container.

        Calls 'iris stop IRIS quietly' inside the container so IRIS flushes
        its write buffer (WIJ) before Docker sends SIGKILL. Without this,
        docker stop may terminate IRIS mid-write, leaving uncommitted data
        in the WIJ. IRIS will recover on next start, but this can take
        30-300 seconds and any in-flight writes not yet committed are lost.

        Returns True if graceful stop succeeded, False if it timed out or
        the container was not running (caller should proceed with docker stop).
        """
        try:
            container = self.get_wrapped_container()
            if container is None:
                return False
            exit_code, _ = container.exec_run(
                "iris stop IRIS quietly",
                user="irisowner",
            )
            return exit_code == 0
        except Exception:
            return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_gracefully()
        super().__exit__(exc_type, exc_val, exc_tb)

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
            tag = version if version != "latest" else "latest-em"
            image = f"caretdev/iris-community-light:{tag}"
        return cls(image=image, **kwargs)

    @classmethod
    def health(
        cls, image: Optional[str] = None, version: str = "latest", **kwargs
    ) -> "IRISContainer":
        """
        Create an irishealth-community container with FHIR R4 pre-installed.

        Foundation.Install + InstallInstance are baked at build time — no ZPM,
        no network calls, no runtime setup. FHIR R4 endpoint available at
        /csp/healthshare/demo/fhir/r4/metadata within ~90 seconds of start.

        Web portal on 52773. SuperServer on 1972. Community edition.
        Container is cleaned up by Ryuk on process exit.

        Args:
            image: Docker image. Defaults to irishealth-community:latest.
            version: Image tag. Options: 'latest', '2024.1', '2025.1', etc.
        """
        if image is None:
            image = f"intersystemsdc/irishealth-community:{version}"
        container = cls(image=image, **kwargs)
        container._edition = "health"
        return container

    @classmethod
    def ai_hub(
        cls,
        build: str = "159",
        image: Optional[str] = None,
        durable_path: Optional[str] = None,
        **kwargs,
    ) -> "IRISContainer":
        """
        Create an irishealth AI Hub container with %AI.Agent, %AI.MCP.Service, VECTOR.

        Requires access to docker.iscinternal.com (ISC internal registry).
        No license key needed — this is not the standard enterprise image.
        SuperServer on 1972 only. No web server (WebServer=0 in iris.cpf).

        CRITICAL — /durable volume:
            Named Docker volumes mount with root ownership. irisowner (uid 51773)
            cannot write → container fails silently. This factory defaults to
            tmpfs:/durable. For persistence, provide durable_path (host bind-mount
            must be pre-chowned to uid 51773 before starting).

        CRITICAL — double-start bug:
            The -a entrypoint hook in /iris-main runs after IRIS is already started.
            Any startup script that calls 'iris start IRIS quietly' will cause IRIS
            to fail with "database already running". Startup scripts under -a must
            assume IRIS is already live.

        Args:
            build: AI Hub build number (default: "159" = 2026.2.0AI.159).
            image: Override full image reference. If None, uses irishealth:2026.2.0AI.{build}.0
            durable_path: Host path for persistent /durable bind-mount. Must be
                pre-chowned to uid 51773:51773. If None, uses tmpfs (non-persistent).
        """
        import os

        if image is None:
            image = f"docker.iscinternal.com/docker-intersystems/intersystems/irishealth:2026.2.0AI.{build}.0"

        container = cls(image=image, **kwargs)
        container._edition = "ai_hub"
        container._durable_path = durable_path
        container._use_tmpfs_durable = durable_path is None
        return container

    @classmethod
    def attach(
        cls,
        container_name: str,
        port: Optional[int] = None,
        unexpire_passwords: bool = True,
        **kwargs,
    ) -> "IRISContainer":
        """
        Attach to an existing IRIS container by name.

        Use this to reconnect to persistent containers started by ``idt container up``
        or docker-compose. Unlike containers created via community()/enterprise()/light(),
        CLI-managed containers are NOT cleaned up by Ryuk and persist across process exits.

        Args:
            container_name: Name of the existing Docker container.
            port: Host-side SuperServer port to use instead of the Docker-inspected
                binding. Required when Docker Desktop NAT rewrites the source IP and
                IRIS rejects the connection (macOS Docker Desktop with irishealth
                enterprise). When supplied, the docker port lookup is skipped entirely.
                Also honoured via ``IVG_PORT`` or ``IRIS_PORT`` environment variables
                when ``port`` is not provided explicitly.
            unexpire_passwords: When True (default), call unexpire_all_passwords() after
                attaching. Enterprise images often ship with expired passwords; this
                prevents silent login failures. Set to False when the container is known
                to have valid credentials and you want to skip the overhead.
            **kwargs: Additional configuration (username, password, namespace).

        Returns:
            An IRISContainer instance attached to the existing container.
        """
        import os

        if not container_name:
            raise ValueError("container_name must be a non-empty string")

        # Resolve explicit port override: parameter > IVG_PORT > IRIS_PORT
        if port is None:
            for env_var in ("IVG_PORT", "IRIS_PORT"):
                env_val = os.environ.get(env_var)
                if env_val:
                    try:
                        port = int(env_val)
                    except ValueError:
                        pass
                    else:
                        break

        instance = cls(image="", name=container_name, **kwargs)
        instance._is_attached = True
        instance._container_name = container_name

        # Pin the mapped port immediately so get_mapped_port(1972) never falls
        # through to the docker port lookup, regardless of which code path below runs.
        if port is not None:
            instance._mapped_port = port

        try:
            import docker

            client = docker.from_env()
            container = client.containers.get(container_name)
            instance._container = container

            if not HAS_TESTCONTAINERS:
                instance.host = "localhost"
                # Only read docker port binding when no explicit port was given
                if port is None:
                    ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                    if "1972/tcp" in ports and ports["1972/tcp"]:
                        instance._mapped_port = int(ports["1972/tcp"][0]["HostPort"])
            else:
                # testcontainers will handle host/port discovery via get_config(),
                # but _mapped_port is already pinned above if port was supplied.
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

        if unexpire_passwords:
            # Enterprise images often ship with expired passwords; wildcard unexpire
            # prevents silent login failures. Failure is non-fatal — the container
            # is already attached and the caller may supply valid credentials.
            try:
                unexpire_all_passwords(container_name)
            except Exception:
                pass

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

    def connection_info(self, web_port: Optional[int] = None) -> "IRISConnectionInfo":
        """Build the iris-devtester -> iris-agentic-dev handoff contract.

        Returns an :class:`IRISConnectionInfo` describing how to reach this
        container: host, host-mapped SuperServer port, credentials, image, and a
        WebGateway URL if one is auto-detected. A session calls this once and
        writes ``connection_info().to_toml_snippet()`` into
        ``.iris-agentic-dev.toml``, which iad hot-reloads.

        WebGateway detection scans containers sharing a Docker network with this
        IRIS container for a ``*webgateway*`` image and uses its host-mapped port
        80. When detection finds nothing, ``web_port`` (typically read from
        ``.iris-dev.toml``) is used as a fallback; if that is also None, the
        result is ``docker_only=True``.

        Args:
            web_port: Explicit WebGateway host port to fall back to when
                auto-detection finds none (e.g. from ``.iris-dev.toml``).

        Returns:
            An :class:`IRISConnectionInfo` for this container.
        """
        from iris_devtester.containers.connection_info import (
            IRISConnectionInfo,
            detect_webgateway,
        )

        host = self.host
        superserver_port = self.get_mapped_port(1972)
        container_name = self.get_container_name()

        wrapped = None
        try:
            wrapped = self.get_wrapped_container()
        except Exception:
            pass

        iris_image = str(self.image)
        iris_networks: set = set()
        client = None
        if wrapped is not None:
            try:
                tags = wrapped.image.tags
                if tags:
                    iris_image = tags[0]
            except Exception:
                pass
            try:
                networks = wrapped.attrs["NetworkSettings"]["Networks"]
                iris_networks = set(networks.keys())
            except Exception:
                pass
            client = getattr(wrapped, "client", None)

        webgateway_url: Optional[str] = None
        webgateway_container: Optional[str] = None
        if client is not None and iris_networks:
            webgateway_url, webgateway_container = detect_webgateway(
                client, iris_networks=iris_networks, host=host
            )

        # Fallback: explicit web_port (e.g. .iris-dev.toml override) when
        # auto-detection found no WebGateway container.
        if webgateway_url is None and web_port is not None:
            webgateway_url = f"http://{host}:{web_port}"

        return IRISConnectionInfo(
            host=host,
            superserver_port=superserver_port,
            container=container_name,
            iris_image=iris_image,
            namespace=self._namespace,
            username=self._username,
            password=self._password,
            webgateway_url=webgateway_url,
            webgateway_container=webgateway_container,
        )

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

        config = self.get_config()
        try:
            self._connection = get_connection(config)
            return self._connection
        except Exception as e:
            from iris_devtester.utils.password import detect_password_change_required, unexpire_all_passwords
            if detect_password_change_required(str(e)) and not self._password_handled:
                container_name = self.get_container_name()
                unexpire_all_passwords(container_name)
                self._password_handled = True
                self._connection = get_connection(config)
                return self._connection
            raise

    def health_check(self) -> "ContainerHealth":
        """Probe schema visibility and return enriched ContainerHealth.

        Calls get_connection() to obtain (or reuse) a DBAPI connection, then
        runs probe_connection() to inspect visible schemas. Use this before
        running queries to confirm the container is seeded, not just running.
        """
        from iris_devtester.diagnostics import probe_connection

        conn = self.get_connection()
        probe = probe_connection(conn)
        return ContainerHealth(
            container_name=self.get_container_name(),
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="",
            schemas=probe.schemas,
        )

    def fhir_health_check(self, timeout: int = 10) -> "FHIRContainerHealth":
        from iris_devtester.containers.models import FHIRContainerHealth
        import urllib.request
        import urllib.error
        import json

        host = self.get_container_host_ip()
        web_port = self.get_mapped_port(52773)
        app_key = getattr(self, "_fhir_app_key", "/csp/healthshare/demo/fhir/r4")
        endpoint = f"http://{host}:{web_port}{app_key}"
        metadata_url = f"{endpoint}/metadata"

        try:
            with urllib.request.urlopen(metadata_url, timeout=timeout) as resp:
                data = json.loads(resp.read())
                fhir_version = data.get("fhirVersion")
                resource_types = {e.get("type") for e in data.get("rest", [{}])[0].get("resource", [])}
                return FHIRContainerHealth(
                    container_name=self.get_container_name(),
                    accessible=True,
                    endpoint=endpoint,
                    fhir_version=fhir_version,
                    resource_types_count=len(resource_types),
                )
        except Exception as e:
            return FHIRContainerHealth(
                container_name=self.get_container_name(),
                accessible=False,
                endpoint=endpoint,
                error=str(e),
            )

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
        from iris_devtester.config.presets import CPFPreset

        if not hasattr(self, "_cpf_temp_files") or not self._cpf_temp_files:
            # Always use SECURE_DEFAULTS for the CPF merge — it handles CallIn
            # and clears expiry flags for SuperUser/_SYSTEM via proper CPF fields.
            # When a custom password is requested we reset it post-start via
            # PasswordExternal (plaintext accepted) rather than injecting it into
            # PasswordHash= here, which requires a pre-computed PBKDF2 hash,salt
            # string — passing plaintext into PasswordHash= sets a corrupt hash
            # and makes every subsequent login fail silently.
            self.with_cpf_merge(CPFPreset.SECURE_DEFAULTS)

        self._password_handled = True

        if self._preconfigure_password:
            self.with_env("IRIS_PASSWORD", self._preconfigure_password)
        if self._preconfigure_username:
            self.with_env("IRIS_USERNAME", self._preconfigure_username)

        if self._port_registry is not None and self._project_path is not None:
            self._port_assignment = self._port_registry.assign_port(
                project_path=self._project_path,
                preferred_port=self._preferred_port,
            )
            if hasattr(self, "with_bind_ports"):
                self.with_bind_ports(1972, self._port_assignment.port)

        super().start()
        self.get_config()

        # Post-start: apply custom password via PasswordExternal (accepts plaintext).
        # Must happen after super().start() so the container is ready.
        if self._preconfigure_password:
            config = self.get_config()
            username = self._preconfigure_username or "SuperUser"
            reset_password(
                container_name=self.get_container_name(),
                username=username,
                new_password=self._preconfigure_password,
                hostname=config.host,
                port=config.port,
                verify=False,
            )

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
