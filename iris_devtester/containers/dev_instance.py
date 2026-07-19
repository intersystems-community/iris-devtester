"""
Management of the persistent IRIS Dev Instance.

Provides the 'Warm Start' capability by maintaining a global Docker container
and volume, while ensuring project isolation via hashed namespaces.
"""

import hashlib
import logging
import os
import subprocess
from typing import Optional

import docker
from docker.errors import NotFound
from docker.models.containers import Container
from docker.models.volumes import Volume

from iris_devtester.config.container_config import ContainerConfig
from iris_devtester.utils.iris_container_adapter import IRISContainerManager

logger = logging.getLogger(__name__)

# Constants
DEV_INSTANCE_NAME = "idt-dev-instance"
DEV_VOLUME_NAME = "idt-dev-data"
DEV_DURABLE_PATH = "/iris/data"


class DockerVolumeManager:
    """Manages Docker volumes for persistent storage."""

    def __init__(self, client: Optional[docker.DockerClient] = None):
        self.client = client or docker.from_env()

    def get_or_create(self, name: str) -> Volume:
        """Get existing volume or create a new one."""
        try:
            return self.client.volumes.get(name)
        except NotFound:
            logger.info(f"Creating persistent volume: {name}")
            volume = self.client.volumes.create(name=name)
            
            # Ensure volume is writable by irisowner (UID 51773)
            # We do this by running a small container that chowns the mount point
            logger.info(f"Setting permissions for volume: {name}")
            self.client.containers.run(
                "busybox",
                f"chown -R 51773:51773 {DEV_DURABLE_PATH}",
                volumes={name: {"bind": DEV_DURABLE_PATH, "mode": "rw"}},
                remove=True,
            )
            return volume

    def remove(self, name: str) -> bool:
        """Remove a volume."""
        try:
            volume = self.client.volumes.get(name)
            volume.remove(force=True)
            return True
        except NotFound:
            return False


class DevInstanceManager:
    """Manages the lifecycle of the global IRIS dev engine."""

    def __init__(self, client: Optional[docker.DockerClient] = None):
        self.client = client or docker.from_env()
        self.volume_manager = DockerVolumeManager(self.client)

    def get_instance(self) -> Optional[Container]:
        """Get the dev instance container if it exists."""
        try:
            return self.client.containers.get(DEV_INSTANCE_NAME)
        except NotFound:
            return None

    def is_running(self) -> bool:
        """Check if the dev instance is currently running."""
        instance = self.get_instance()
        return instance is not None and instance.status == "running"

    def ensure_ready(self, image: Optional[str] = None, force: bool = False) -> Container:
        """Ensure the dev instance is created, started, and ready."""
        instance = self.get_instance()

        if instance and force:
            logger.info(f"Forcing restart of {DEV_INSTANCE_NAME}...")
            instance.remove(force=True)
            instance = None

        if not instance:
            # Create new instance
            config = ContainerConfig.default()
            config.container_name = DEV_INSTANCE_NAME
            if image:
                config.image = image

            # Find available ports (Auto-assign strategy)
            config.superserver_port = self._find_available_port(1972)
            config.webserver_port = self._find_available_port(52773)

            # Use Durable %SYS for persistence
            self.volume_manager.get_or_create(DEV_VOLUME_NAME)
            config.durable_sys = True
            config.isc_data_directory = DEV_DURABLE_PATH
            config.volumes.append(f"{DEV_VOLUME_NAME}:{DEV_DURABLE_PATH}")
            
            # Use Docker SDK mode for persistence
            instance = IRISContainerManager.create_from_config(
                config, 
                use_testcontainers=False
            )
            
        if instance.status != "running":
            instance.start()

        return instance

    def _find_available_port(self, start_port: int) -> int:
        """Find the next available port starting from start_port."""
        import socket
        port = start_port
        while port < start_port + 100:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port))
                    return port
                except OSError:
                    port += 1
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port+100}")

    def stop(self):
        """Stop the dev instance."""
        instance = self.get_instance()
        if instance:
            instance.stop()

    def remove(self, remove_volumes: bool = False):
        """Remove the dev instance."""
        instance = self.get_instance()
        if instance:
            instance.remove(force=True)
        
        if remove_volumes:
            self.volume_manager.remove(DEV_VOLUME_NAME)


def get_project_id(path: Optional[str] = None) -> str:
    """Generate a stable Project ID from a directory path."""
    target_path = os.path.abspath(path or os.getcwd())
    h = hashlib.sha256(target_path.encode()).hexdigest()
    return h[:11].upper()


def get_project_namespace(path: Optional[str] = None) -> str:
    """Generate a valid IRIS namespace name for a project."""
    return f"P{get_project_id(path)}"
