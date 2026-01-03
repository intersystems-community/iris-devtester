"""Adapter layer between CLI and testcontainers-iris.

This module provides a thin wrapper around testcontainers-iris for CLI use,
adapting the test-focused API for command-line container lifecycle management.
"""

from dataclasses import dataclass
from typing import Optional

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container
from testcontainers.iris import IRISContainer

from iris_devtester.config.container_config import ContainerConfig


@dataclass
class VolumeMountSpec:
    """
    Volume mount specification parsed from Docker volume syntax (Feature 011 - T013).

    Attributes:
        host_path: Path on host system
        container_path: Path inside container
        mode: Mount mode ("rw" for read-write, "ro" for read-only)

    Example:
        >>> spec = VolumeMountSpec.parse("./data:/external:ro")
        >>> spec.host_path
        './data'
        >>> spec.container_path
        '/external'
        >>> spec.mode
        'ro'
    """

    host_path: str
    container_path: str
    mode: str = "rw"

    @classmethod
    def parse(cls, volume_string: str) -> "VolumeMountSpec":
        """
        Parse Docker volume mount string into VolumeMountSpec.

        Args:
            volume_string: Volume mount in format "host:container" or "host:container:mode"

        Returns:
            Parsed VolumeMountSpec

        Raises:
            ValueError: If volume string has invalid format or invalid mode

        Example:
            >>> spec = VolumeMountSpec.parse("./workspace:/external")
            >>> spec.mode
            'rw'

            >>> spec = VolumeMountSpec.parse("/tmp/data:/data:ro")
            >>> spec.mode
            'ro'
        """
        parts = volume_string.split(":")
        if len(parts) < 2:
            raise ValueError(
                f"Volume has invalid format: {volume_string}\n"
                f"  Expected format: host:container or host:container:mode\n"
                f"  Examples: './data:/external' or './data:/external:ro'"
            )

        host_path = parts[0]
        container_path = parts[1]
        mode = parts[2] if len(parts) > 2 else "rw"

        # Validate mode
        if mode not in ("rw", "ro"):
            raise ValueError(
                f"Volume has invalid mode: {mode}\n"
                f"  Valid modes: 'rw' (read-write) or 'ro' (read-only)\n"
                f"  Found in: {volume_string}"
            )

        return cls(host_path=host_path, container_path=container_path, mode=mode)


@dataclass
class ContainerPersistenceCheck:
    """
    Results of container persistence verification (Feature 011 - T014).

    Attributes:
        container_name: Name of the container checked
        exists: Whether container exists in Docker
        status: Container status (running, created, exited, etc.) or None if not found
        volume_mounts_verified: Whether volume mounts are present as expected
        verification_time: How long verification took (seconds)
        error_details: Optional error details if verification failed

    Example:
        >>> check = verify_container_persistence("my-container", config)
        >>> if check.success:
        ...     print("Container persisted successfully!")
        ... else:
        ...     print(check.get_error_message(config))
    """

    container_name: str
    exists: bool
    status: Optional[str]
    volume_mounts_verified: bool
    verification_time: float
    error_details: Optional[str] = None

    @property
    def success(self) -> bool:
        """
        Check if container persistence verification succeeded.

        Returns:
            True if container exists, is running/created, volumes verified, and no errors
        """
        return (
            self.exists
            and self.status in ["running", "created"]
            and self.volume_mounts_verified
            and self.error_details is None
        )

    def get_error_message(self, config: ContainerConfig) -> str:
        """
        Generate constitutional error message for failed persistence check.

        Args:
            config: Container configuration for context

        Returns:
            Constitutional format error message (What/Why/How/Docs)
        """
        return (
            f"Container persistence verification failed for '{self.container_name}'\n"
            "\n"
            "What went wrong:\n"
            f"  Container: {self.container_name}\n"
            f"  Exists: {self.exists}\n"
            f"  Status: {self.status or 'not found'}\n"
            f"  Volume mounts verified: {self.volume_mounts_verified}\n"
            f"  Error details: {self.error_details or 'none'}\n"
            "\n"
            "Why this happened:\n"
            "  The container was created but immediately removed or failed to start.\n"
            "  This often indicates:\n"
            "  - Testcontainers ryuk cleanup service removed the container\n"
            "  - Container startup failure due to configuration issues\n"
            "  - Volume mount failures preventing container start\n"
            "\n"
            "How to fix it:\n"
            "  1. Ensure Docker is running: docker info\n"
            "  2. Check for port conflicts: docker ps | grep <ports>\n"
            "  3. Verify volume paths exist before container creation\n"
            "  4. Review Docker logs: docker logs <container_name> (if still exists)\n"
            "  5. For CLI commands, ensure use_testcontainers=False to prevent ryuk cleanup\n"
            "\n"
            "Documentation: https://docs.docker.com/engine/reference/commandline/logs/\n"
        )


def verify_container_persistence(
    container_name: str,
    config: ContainerConfig,
    wait_seconds: float = 2.0
) -> ContainerPersistenceCheck:
    """
    Verify that container persists after creation (Feature 011 - T014).

    This function waits a few seconds after creation, then checks that:
    1. Container still exists in Docker
    2. Container status is 'running' or 'created'
    3. Volume mounts are present (if configured)

    Args:
        container_name: Name of container to verify
        config: Container configuration
        wait_seconds: How long to wait before verification (default: 2.0)

    Returns:
        ContainerPersistenceCheck with verification results

    Example:
        >>> config = ContainerConfig.default()
        >>> container = create_container(config)
        >>> check = verify_container_persistence(config.container_name, config)
        >>> if not check.success:
        ...     raise ValueError(check.get_error_message(config))
    """
    import time

    time.sleep(wait_seconds)
    client = docker.from_env()

    try:
        container = client.containers.get(container_name)
        mounts = container.attrs["Mounts"]

        # Verify volume mounts if configured
        expected_volumes = len(config.volumes)
        actual_volumes = len(mounts)
        volumes_ok = expected_volumes == 0 or actual_volumes >= expected_volumes

        return ContainerPersistenceCheck(
            container_name=container_name,
            exists=True,
            status=container.status,
            volume_mounts_verified=volumes_ok,
            verification_time=wait_seconds,
            error_details=None if volumes_ok else f"Expected {expected_volumes} volumes, found {actual_volumes}"
        )

    except NotFound:
        return ContainerPersistenceCheck(
            container_name=container_name,
            exists=False,
            status=None,
            volume_mounts_verified=False,
            verification_time=wait_seconds,
            error_details="Container not found after creation (possibly removed by ryuk or failed to start)"
        )

    except Exception as e:
        return ContainerPersistenceCheck(
            container_name=container_name,
            exists=False,
            status=None,
            volume_mounts_verified=False,
            verification_time=wait_seconds,
            error_details=f"Verification error: {str(e)}"
        )

    finally:
        client.close()


class IRISContainerManager:
    """Manager for IRIS containers using testcontainers-iris."""

    @staticmethod
    def create_from_config(
        config: ContainerConfig,
        use_testcontainers: bool = True
    ) -> Container:
        """
        Create IRIS container from config with dual-mode support (Feature 011 - T012).

        Args:
            config: Container configuration
            use_testcontainers: If True, use testcontainers-iris (pytest fixtures).
                              If False, use Docker SDK directly (CLI commands).

        Returns:
            Docker Container object (started)

        Raises:
            ValueError: If configuration is invalid
            ConnectionError: If Docker daemon not accessible

        Example (testcontainers mode - pytest):
            >>> config = ContainerConfig.default()
            >>> container = IRISContainerManager.create_from_config(config, use_testcontainers=True)

        Example (Docker SDK mode - CLI):
            >>> config = ContainerConfig.default()
            >>> container = IRISContainerManager.create_from_config(config, use_testcontainers=False)
        """
        if use_testcontainers:
            return IRISContainerManager._create_with_testcontainers(config)
        else:
            return IRISContainerManager._create_with_docker_sdk(config)

    @staticmethod
    def _create_with_testcontainers(config: ContainerConfig) -> IRISContainer:
        """Create container using testcontainers-iris (automatic cleanup)."""
        # Create base container
        container = IRISContainer(
            image=config.get_image_name(),
            port=config.superserver_port,
            username="_SYSTEM",  # IRIS default user
            password=config.password,
            namespace=config.namespace,
            license_key=config.license_key if config.edition == "enterprise" else None
        )

        # Configure container name
        container.with_name(config.container_name)

        # Configure port mappings
        container.with_bind_ports(config.superserver_port, config.superserver_port)
        container.with_bind_ports(config.webserver_port, config.webserver_port)

        # Configure volume mounts
        for volume in config.volumes:
            spec = VolumeMountSpec.parse(volume)
            container.with_volume_mapping(spec.host_path, spec.container_path, spec.mode)

        return container

    @staticmethod
    def _create_with_docker_sdk(config: ContainerConfig) -> Container:
        """
        Create container using Docker SDK directly (manual cleanup, no ryuk).

        This mode is used for CLI commands where containers need to persist
        until explicitly removed by the user.
        """
        client = docker.from_env()

        # Parse volumes for Docker SDK
        volumes = {}
        for volume_str in config.volumes:
            spec = VolumeMountSpec.parse(volume_str)
            volumes[spec.host_path] = {
                'bind': spec.container_path,
                'mode': spec.mode
            }

        # IRIS environment variables (Feature 011 - T012)
        # Note: Don't set ISC_DATA_DIRECTORY - let IRIS use its default
        environment = {}

        # Add license key for Enterprise edition
        if config.edition == 'enterprise' and config.license_key:
            environment['ISC_LICENSE_KEY'] = config.license_key

        # Create container without testcontainers labels (prevents ryuk cleanup)
        container = client.containers.create(
            image=config.get_image_name(),
            name=config.container_name,
            volumes=volumes or None,
            ports={
                f'{config.superserver_port}/tcp': config.superserver_port,
                f'{config.webserver_port}/tcp': config.webserver_port
            },
            environment=environment,
            detach=True
        )

        # Start the container
        container.start()

        return container

    @staticmethod
    def get_existing(container_name: str) -> Optional[Container]:
        """Get existing container by name.

        Args:
            container_name: Name of container to find

        Returns:
            Docker Container object or None if not found

        Raises:
            ConnectionError: If Docker daemon is not accessible

        Example:
            >>> container = IRISContainerManager.get_existing("iris-devtest")
            >>> if container:
            ...     print(container.status)
        """
        try:
            client = docker.from_env()
            return client.containers.get(container_name)
        except NotFound:
            return None
        except DockerException as e:
            error = translate_docker_error(e, None)
            raise error from e

    @staticmethod
    def get_docker_client() -> docker.DockerClient:
        """Get Docker SDK client with connection verification.

        Returns:
            Docker client instance

        Raises:
            ConnectionError: If Docker daemon is not accessible

        Example:
            >>> client = IRISContainerManager.get_docker_client()
            >>> client.ping()
            True
        """
        try:
            client = docker.from_env()
            client.ping()
            return client
        except DockerException as e:
            raise ConnectionError(
                "Failed to connect to Docker daemon\n"
                "\n"
                "What went wrong:\n"
                "  Docker is not running or not accessible by current user.\n"
                "\n"
                "Why it matters:\n"
                "  Container lifecycle commands require Docker to create and manage IRIS containers.\n"
                "\n"
                "How to fix it:\n"
                "  1. Start Docker Desktop (macOS/Windows):\n"
                "     → Open Docker Desktop application\n"
                "  2. Start Docker daemon (Linux):\n"
                "     → sudo systemctl start docker\n"
                "  3. Verify Docker is running:\n"
                "     → docker --version\n"
                "     → docker ps\n"
                "\n"
                "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/\n"
            ) from e


def translate_docker_error(error: Exception, config: Optional[ContainerConfig]) -> Exception:
    """Translate Docker errors to constitutional format.

    Args:
        error: Original Docker exception
        config: Container configuration (for context in error message)

    Returns:
        Translated exception with constitutional error message

    Example:
        >>> try:
        ...     container.start()
        ... except Exception as e:
        ...     raise translate_docker_error(e, config)
    """
    error_str = str(error).lower()

    # Volume mount failures (Feature 011 - T016)
    if "volume" in error_str or "mount" in error_str or "bind" in error_str:
        volumes_info = ""
        if config and config.volumes:
            volumes_info = f"\n  Configured volumes:\n"
            for vol in config.volumes:
                volumes_info += f"    - {vol}\n"

        return ValueError(
            f"Volume mount failed\n"
            "\n"
            "What went wrong:\n"
            f"  {str(error)}\n"
            f"{volumes_info}"
            "\n"
            "Why this happened:\n"
            "  Volume mounting can fail if:\n"
            "  - Host path doesn't exist\n"
            "  - Docker lacks permissions to access host path\n"
            "  - Invalid volume syntax used\n"
            "  - Volume already mounted by another container\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify host paths exist:\n"
            "     → ls -la <host_path>\n"
            "  2. Check Docker volume syntax:\n"
            "     → host:container (read-write) or host:container:ro (read-only)\n"
            "  3. Ensure Docker has permissions to access host path\n"
            "  4. Create missing directories:\n"
            "     → mkdir -p <host_path>\n"
            "\n"
            "Documentation: https://docs.docker.com/storage/volumes/\n"
        )

    # Port already in use
    if "port is already allocated" in error_str or "address already in use" in error_str:
        port = config.superserver_port if config else "unknown"
        return ValueError(
            f"Port {port} is already in use\n"
            "\n"
            "What went wrong:\n"
            "  Another container or service is using the SuperServer port.\n"
            "\n"
            "Why it matters:\n"
            "  IRIS requires exclusive access to the SuperServer port.\n"
            "\n"
            "How to fix it:\n"
            "  1. Stop the conflicting container:\n"
            "     → docker ps  # Find container using the port\n"
            "     → docker stop <container-name>\n"
            "  2. Change the port in iris-config.yml:\n"
            "     → superserver_port: 2000  # Use different port\n"
            "  3. Use environment variable:\n"
            "     → export IRIS_SUPERSERVER_PORT=2000\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/#port-conflicts\n"
        )

    # Image not found
    if "image not found" in error_str or "manifest unknown" in error_str or "no such image" in error_str:
        image = config.get_image_name() if config else "unknown"
        return ValueError(
            f"Docker image '{image}' not found\n"
            "\n"
            "What went wrong:\n"
            "  The IRIS Docker image is not available locally or in the registry.\n"
            "\n"
            "Why it matters:\n"
            "  Container creation requires a valid IRIS Docker image.\n"
            "\n"
            "How to fix it:\n"
            "  1. Pull the image manually:\n"
            "     → docker pull {image}\n"
            "  2. Check image_tag in config:\n"
            "     → Verify 'image_tag' field in iris-config.yml\n"
            "  3. Use default Community image:\n"
            "     → edition: community\n"
            "     → image_tag: latest\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/#image-not-found\n"
        )

    # Docker not running
    if "cannot connect" in error_str or "connection refused" in error_str or "daemon" in error_str:
        return ConnectionError(
            "Failed to connect to Docker daemon\n"
            "\n"
            "What went wrong:\n"
            "  Docker is not running or not accessible.\n"
            "\n"
            "Why it matters:\n"
            "  Container management requires Docker to be running.\n"
            "\n"
            "How to fix it:\n"
            "  1. Start Docker Desktop (macOS/Windows):\n"
            "     → Open Docker Desktop application\n"
            "  2. Start Docker daemon (Linux):\n"
            "     → sudo systemctl start docker\n"
            "  3. Verify Docker is running:\n"
            "     → docker --version\n"
            "     → docker ps\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/#docker-not-running\n"
        )

    # Container name already in use
    if "already in use" in error_str and "name" in error_str:
        name = config.container_name if config else "unknown"
        return ValueError(
            f"Container name '{name}' is already in use\n"
            "\n"
            "What went wrong:\n"
            "  Another container is already using this name.\n"
            "\n"
            "Why it matters:\n"
            "  Container names must be unique.\n"
            "\n"
            "How to fix it:\n"
            "  1. Remove the existing container:\n"
            "     → docker rm {name}\n"
            "  2. Use a different container name:\n"
            "     → Change 'container_name' in iris-config.yml\n"
            "  3. List existing containers:\n"
            "     → docker ps -a\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/#name-conflicts\n"
        )

    # Architecture mismatch
    if "unsupported cpu" in error_str or "exec format error" in error_str:
        image = config.get_image_name() if config else "unknown"
        return ValueError(
            f"Architecture mismatch for image '{image}'\n"
            "\n"
            "What went wrong:\n"
            "  The Docker image architecture does not match your host CPU.\n"
            "  (e.g., trying to run amd64 image on Apple Silicon arm64)\n"
            "\n"
            "Why it matters:\n"
            "  IRIS containers require native or emulated CPU support.\n"
            "\n"
            "How to fix it:\n"
            "  1. Ensure you are using the correct image for your architecture\n"
            "  2. For Apple Silicon, use Community images (multi-arch support)\n"
            "  3. Or enable Rosetta 2 emulation in Docker Desktop settings\n"
            "\n"
            "Documentation: https://docs.docker.com/desktop/settings/mac/#general\n"
        )

    if "unsupported cpu" in error_str or "exec format error" in error_str:
        image = config.get_image_name() if config else "unknown"
        return ValueError(
            f"Architecture mismatch for image '{image}'\n"
            "\n"
            "What went wrong:\n"
            "  The Docker image architecture does not match your host CPU.\n"
            "  (e.g., trying to run amd64 image on Apple Silicon arm64)\n"
            "\n"
            "Why it matters:\n"
            "  IRIS containers require native or emulated CPU support.\n"
            "\n"
            "How to fix it:\n"
            "  1. Ensure you are using the correct image for your architecture\n"
            "  2. For Apple Silicon, use Community images (multi-arch support)\n"
            "  3. Or enable Rosetta 2 emulation in Docker Desktop settings\n"
            "\n"
            "Documentation: https://docs.docker.com/desktop/settings/mac/#general\n"
        )

    # Generic Docker error - pass through with original exception
    return error


__all__ = ["IRISContainerManager", "translate_docker_error"]
