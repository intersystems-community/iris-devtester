"""Container runtime state model for IRIS lifecycle management."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ContainerStatus(str, Enum):
    """Container lifecycle status."""
    CREATING = "creating"
    STARTING = "starting"
    RUNNING = "running"
    HEALTHY = "healthy"
    STOPPED = "stopped"
    REMOVING = "removing"


class HealthStatus(str, Enum):
    """Docker health check status."""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    NONE = "none"


class ContainerState(BaseModel):
    """
    Container runtime state model.

    Represents the current state and health of a managed IRIS container.
    Queried dynamically from Docker engine via Docker SDK.

    Attributes:
        container_id: Docker container ID (64 character hex string)
        container_name: Container name (matches ContainerConfig)
        status: Current lifecycle state
        health_status: Docker health check status
        created_at: Container creation timestamp
        started_at: Last start timestamp (None if never started)
        finished_at: Last stop timestamp (None if never stopped)
        ports: Port mappings (container_port -> host_port)
        image: Full image reference used
        config_source: Source config file path (if any)

    Example:
        >>> from iris_devtester.config import get_container_state
        >>> state = get_container_state("iris_db")
        >>> print(f"Status: {state.status}")
        >>> print(f"Health: {state.health_status}")
        >>> print(f"Ports: {state.ports}")
    """

    container_id: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Docker container ID (full hash)"
    )
    container_name: str = Field(
        ...,
        description="Container name"
    )
    status: ContainerStatus = Field(
        ...,
        description="Current lifecycle state"
    )
    health_status: HealthStatus = Field(
        default=HealthStatus.NONE,
        description="Docker health check status"
    )
    created_at: datetime = Field(
        ...,
        description="Container creation timestamp"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="Last start timestamp"
    )
    finished_at: Optional[datetime] = Field(
        default=None,
        description="Last stop timestamp"
    )
    ports: Dict[int, int] = Field(
        default_factory=dict,
        description="Port mappings (container -> host)"
    )
    image: str = Field(
        ...,
        description="Full image reference"
    )
    config_source: Optional[Path] = Field(
        default=None,
        description="Source config file (if any)"
    )

    @field_validator("container_id")
    @classmethod
    def validate_container_id(cls, v: str) -> str:
        """Validate Docker container ID format (64 hex chars)."""
        if len(v) != 64:
            raise ValueError(f"Container ID must be 64 characters, got {len(v)}")

        # Check if hex
        try:
            int(v, 16)
        except ValueError:
            raise ValueError(f"Container ID must be hexadecimal, got: {v}")

        return v

    @classmethod
    def from_container(cls, container) -> "ContainerState":
        """
        Query container state from Docker.

        Args:
            container: Docker Container object to query

        Returns:
            ContainerState object with current state

        Example:
            >>> from iris_devtester.utils.iris_container_adapter import IRISContainerManager
            >>> container = IRISContainerManager.get_existing("iris_db")
            >>> if container:
            ...     state = ContainerState.from_container(container)
            ...     print(f"Status: {state.status}")
        """
        # Reload to get latest state
        container.reload()
        attrs = container.attrs

        # Map Docker status to ContainerStatus
        docker_status = container.status.lower()
        status_mapping = {
            "created": ContainerStatus.CREATING,
            "restarting": ContainerStatus.STARTING,
            "running": ContainerStatus.RUNNING,
            "paused": ContainerStatus.STOPPED,
            "exited": ContainerStatus.STOPPED,
            "dead": ContainerStatus.STOPPED,
        }
        status = status_mapping.get(docker_status, ContainerStatus.STOPPED)

        # Check health status
        health_info = attrs.get("State", {}).get("Health", {})
        health_status_str = health_info.get("Status", "none").lower()
        health_mapping = {
            "starting": HealthStatus.STARTING,
            "healthy": HealthStatus.HEALTHY,
            "unhealthy": HealthStatus.UNHEALTHY,
            "none": HealthStatus.NONE,
        }
        health_status = health_mapping.get(health_status_str, HealthStatus.NONE)

        # Upgrade status to healthy if health check passes
        if health_status == HealthStatus.HEALTHY and status == ContainerStatus.RUNNING:
            status = ContainerStatus.HEALTHY

        # Parse timestamps
        created_at = datetime.fromisoformat(attrs["Created"].rstrip("Z"))
        started_at_str = attrs["State"].get("StartedAt", "")
        finished_at_str = attrs["State"].get("FinishedAt", "")

        started_at = None
        if started_at_str and started_at_str != "0001-01-01T00:00:00Z":
            started_at = datetime.fromisoformat(started_at_str.rstrip("Z"))

        finished_at = None
        if finished_at_str and finished_at_str != "0001-01-01T00:00:00Z":
            finished_at = datetime.fromisoformat(finished_at_str.rstrip("Z"))

        # Extract port mappings
        ports = {}
        port_bindings = attrs.get("NetworkSettings", {}).get("Ports", {})
        for container_port_str, host_bindings in port_bindings.items():
            if host_bindings:
                # Parse "1972/tcp" -> 1972
                container_port = int(container_port_str.split("/")[0])
                host_port = int(host_bindings[0]["HostPort"])
                ports[container_port] = host_port

        # Get image
        image = attrs["Config"]["Image"]

        # Get config source from labels
        config_source = None
        labels = attrs.get("Config", {}).get("Labels", {})
        if "iris-devtester.config.source" in labels:
            source_str = labels["iris-devtester.config.source"]
            if source_str != "default":
                config_source = source_str

        return cls(
            container_id=container.id,
            container_name=container.name,
            status=status,
            health_status=health_status,
            created_at=created_at,
            started_at=started_at,
            finished_at=finished_at,
            ports=ports,
            image=image,
            config_source=config_source,
        )

    def is_running(self) -> bool:
        """
        Check if container is currently running.

        Returns:
            True if status is running or healthy
        """
        return self.status in [ContainerStatus.RUNNING, ContainerStatus.HEALTHY]

    def is_healthy(self) -> bool:
        """
        Check if container is healthy.

        Returns:
            True if status is healthy and health_status is healthy
        """
        return (
            self.status == ContainerStatus.HEALTHY
            and self.health_status == HealthStatus.HEALTHY
        )

    def get_uptime_seconds(self) -> Optional[float]:
        """
        Calculate container uptime in seconds.

        Returns:
            Uptime in seconds, or None if not running
        """
        if not self.is_running() or self.started_at is None:
            return None

        now = datetime.now(self.started_at.tzinfo)
        delta = now - self.started_at
        return delta.total_seconds()

    def format_uptime(self) -> str:
        """
        Format uptime as human-readable string.

        Returns:
            Formatted uptime (e.g., "2h 15m 30s") or "Not running"
        """
        uptime_seconds = self.get_uptime_seconds()
        if uptime_seconds is None:
            return "Not running"

        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def format_ports(self) -> str:
        """
        Format port mappings as human-readable string.

        Returns:
            Formatted port string (e.g., "1972->1972, 52773->52773")
        """
        if not self.ports:
            return "None"

        port_strs = [f"{container_port}->{host_port}"
                     for container_port, host_port in sorted(self.ports.items())]
        return ", ".join(port_strs)

    def to_text_output(self) -> str:
        """
        Format state as text output for CLI display.

        Returns:
            Multi-line formatted string

        Example:
            Container: iris_db
            Status:    healthy
            Health:    healthy
            Uptime:    2h 15m 30s
            Ports:     1972->1972, 52773->52773
            Image:     intersystems/iris-community:latest
        """
        lines = [
            f"Container: {self.container_name}",
            f"ID:        {self.container_id[:12]}",
            f"Status:    {self.status.value}",
            f"Health:    {self.health_status.value}",
            f"Uptime:    {self.format_uptime()}",
            f"Ports:     {self.format_ports()}",
            f"Image:     {self.image}",
        ]

        if self.config_source:
            lines.append(f"Config:    {self.config_source}")

        return "\n".join(lines)

    def to_json_output(self) -> dict:
        """
        Format state as JSON-serializable dict for CLI --format=json.

        Returns:
            Dictionary with all state information
        """
        return {
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": self.status.value,
            "health_status": self.health_status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "uptime_seconds": self.get_uptime_seconds(),
            "ports": self.ports,
            "image": self.image,
            "config_source": str(self.config_source) if self.config_source else None,
        }

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "container_id": "a1b2c3d4e5f6" + "0" * 52,  # 64 chars
                "container_name": "iris_db",
                "status": "healthy",
                "health_status": "healthy",
                "created_at": "2025-01-10T14:30:00Z",
                "started_at": "2025-01-10T14:30:15Z",
                "finished_at": None,
                "ports": {1972: 1972, 52773: 52773},
                "image": "intersystems/iris-community:latest",
                "config_source": None
            }
        }
