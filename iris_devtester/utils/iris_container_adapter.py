"""Adapter layer between CLI and testcontainers-iris.

This module provides a thin wrapper around testcontainers-iris for CLI use,
adapting the test-focused API for command-line container lifecycle management.
"""

from typing import Optional

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container
from testcontainers.iris import IRISContainer

from iris_devtester.config.container_config import ContainerConfig


class IRISContainerManager:
    """Manager for IRIS containers using testcontainers-iris."""

    @staticmethod
    def create_from_config(config: ContainerConfig) -> IRISContainer:
        """Create IRISContainer from ContainerConfig.

        Args:
            config: Container configuration

        Returns:
            Configured IRISContainer (not started)

        Example:
            >>> config = ContainerConfig.default()
            >>> iris = IRISContainerManager.create_from_config(config)
            >>> iris.start()
        """
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

        # Bug Fix #3: Configure volume mounts from config
        for volume in config.volumes:
            parts = volume.split(":")
            host_path = parts[0]
            container_path = parts[1]
            mode = parts[2] if len(parts) > 2 else "rw"
            container.with_volume_mapping(host_path, container_path, mode)

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

    # Generic Docker error - pass through with original exception
    return error


__all__ = ["IRISContainerManager", "translate_docker_error"]
