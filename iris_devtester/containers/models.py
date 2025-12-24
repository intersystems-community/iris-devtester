"""Data models for container validation.

This module defines data structures for representing container health state
and validation results. All models follow Constitutional Principle #7
(Medical-Grade Reliability) with type safety and clear invariants.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ContainerHealthStatus(str, Enum):
    """Container health status values.

    Represents all possible container health states from validation checks.
    String enum for JSON serialization compatibility.
    """

    HEALTHY = "healthy"
    """Container is running and accessible."""

    RUNNING_NOT_ACCESSIBLE = "running_not_accessible"
    """Container is running but exec commands fail."""

    NOT_RUNNING = "not_running"
    """Container exists but is not running."""

    NOT_FOUND = "not_found"
    """Container does not exist."""

    STALE_REFERENCE = "stale_reference"
    """Container was recreated with new ID."""

    DOCKER_ERROR = "docker_error"
    """Docker daemon communication failed."""


class HealthCheckLevel(str, Enum):
    """Validation check depth levels.

    Defines progressive validation strategy:
    - MINIMAL: Fastest check (just running status)
    - STANDARD: Balanced check (running + accessibility)
    - FULL: Comprehensive check (includes IRIS-specific validation)
    """

    MINIMAL = "minimal"
    """Just check if container is running (<500ms)."""

    STANDARD = "standard"
    """Running + exec accessibility check (<1000ms)."""

    FULL = "full"
    """Standard + IRIS-specific health check (<2000ms)."""


@dataclass
class ValidationResult:
    """Result of container validation check.

    Encapsulates validation outcome with structured error messages
    following Constitutional Principle #5 (Fail Fast with Guidance).

    Invariants:
        - success=True ⟹ status=HEALTHY
        - success=False ⟹ status != HEALTHY
        - success=False ⟹ len(remediation_steps) > 0
        - status=NOT_FOUND ⟹ container_id is None
        - status=NOT_FOUND ⟹ available_containers may be populated

    Examples:
        >>> result = ValidationResult.healthy("iris_db", "abc123", 0.15)
        >>> assert result.success is True
        >>> assert result.status == ContainerHealthStatus.HEALTHY

        >>> result = ValidationResult.not_found("iris_db", ["iris_test"], 0.12)
        >>> assert result.success is False
        >>> assert len(result.remediation_steps) > 0
    """

    success: bool
    """Overall validation success (True = healthy)."""

    status: ContainerHealthStatus
    """Specific health status."""

    container_name: str
    """Name of validated container."""

    message: str
    """Human-readable status message."""

    remediation_steps: List[str]
    """Actionable fix commands (empty if success)."""

    container_id: Optional[str] = None
    """Current container ID (if exists)."""

    available_containers: List[str] = field(default_factory=list)
    """Alternative containers (only if not found)."""

    validation_time: float = 0.0
    """Time taken for validation (seconds)."""

    def format_message(self) -> str:
        """Format validation result as multi-line message.

        Returns structured error message following Constitutional Principle #5:
        - "What went wrong" explanation
        - "How to fix it" remediation steps
        - Optional context (available containers, etc.)

        Returns:
            Formatted multi-line message ready for display.

        Examples:
            >>> result = ValidationResult.not_found("iris_db", ["iris_test"], 0.1)
            >>> print(result.format_message())
            Container validation failed for 'iris_db'
            <BLANKLINE>
            What went wrong:
              Container 'iris_db' does not exist.
            <BLANKLINE>
            How to fix it:
              1. List all containers:
                 docker ps -a
            ...
        """
        if self.success:
            return f"Container '{self.container_name}' is healthy"

        lines = [f"Container validation failed for '{self.container_name}'", ""]

        # What went wrong
        lines.append("What went wrong:")
        lines.append(f"  {self.message}")
        lines.append("")

        # How to fix it
        if self.remediation_steps:
            lines.append("How to fix it:")
            for i, step in enumerate(self.remediation_steps, 1):
                if "\n" in step:
                    # Multi-line step
                    lines.append(f"  {i}. {step.split(chr(10))[0]}")
                    for sub_line in step.split("\n")[1:]:
                        lines.append(f"     {sub_line}")
                else:
                    lines.append(f"  {step}")
            lines.append("")

        # Available containers (if applicable)
        if self.available_containers:
            lines.append("Available containers:")
            for container in self.available_containers:
                lines.append(f"  - {container}")

        return "\n".join(lines).rstrip()

    @classmethod
    def healthy(
        cls,
        name: str,
        container_id: str,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for healthy container.

        Args:
            name: Container name.
            container_id: Current container ID.
            validation_time: Validation duration in seconds.

        Returns:
            ValidationResult indicating success.
        """
        return cls(
            success=True,
            status=ContainerHealthStatus.HEALTHY,
            container_name=name,
            container_id=container_id,
            message=f"Container '{name}' is running and accessible",
            remediation_steps=[],
            validation_time=validation_time
        )

    @classmethod
    def not_found(
        cls,
        name: str,
        available_containers: List[str],
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for container not found.

        Args:
            name: Container name.
            available_containers: List of available container names.
            validation_time: Validation duration in seconds.

        Returns:
            ValidationResult indicating container not found.
        """
        return cls(
            success=False,
            status=ContainerHealthStatus.NOT_FOUND,
            container_name=name,
            container_id=None,
            message=f"Container '{name}' does not exist.",
            remediation_steps=[
                "1. List all containers:\n   docker ps -a",
                f"2. Start container if it exists:\n   docker start {name}",
                f"3. Or create new container:\n   docker run -d --name {name} intersystemsdc/iris-community:latest"
            ],
            available_containers=available_containers,
            validation_time=validation_time
        )

    @classmethod
    def not_running(
        cls,
        name: str,
        container_id: str,
        validation_time: float,
        container_status: str = "exited"
    ) -> "ValidationResult":
        """Factory method for stopped container.

        Args:
            name: Container name.
            container_id: Container ID.
            validation_time: Validation duration in seconds.
            container_status: Container status from Docker (default: "exited").

        Returns:
            ValidationResult indicating container not running.
        """
        return cls(
            success=False,
            status=ContainerHealthStatus.NOT_RUNNING,
            container_name=name,
            container_id=container_id,
            message=f"Container exists but is not running (status: {container_status}).",
            remediation_steps=[
                f"docker start {name}"
            ],
            validation_time=validation_time
        )

    @classmethod
    def not_accessible(
        cls,
        name: str,
        container_id: str,
        error: str,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for inaccessible container.

        Args:
            name: Container name.
            container_id: Container ID.
            error: Error message from accessibility check.
            validation_time: Validation duration in seconds.

        Returns:
            ValidationResult indicating container not accessible.
        """
        return cls(
            success=False,
            status=ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE,
            container_name=name,
            container_id=container_id,
            message=f"Container is running but not accessible (exec failed).\n  Error: {error}",
            remediation_steps=[
                f"1. Restart container:\n   docker restart {name}",
                f"2. Check container logs:\n   docker logs {name} | tail -20",
                f"3. Enable CallIn service (for IRIS):\n   iris-devtester container enable-callin {name}"
            ],
            validation_time=validation_time
        )

    @classmethod
    def stale_reference(
        cls,
        name: str,
        cached_id: str,
        current_id: str,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for stale container reference.

        Args:
            name: Container name.
            cached_id: Stale container ID (old reference).
            current_id: Current container ID (active).
            validation_time: Validation duration in seconds.

        Returns:
            ValidationResult indicating stale reference detected.
        """
        return cls(
            success=False,
            status=ContainerHealthStatus.STALE_REFERENCE,
            container_name=name,
            container_id=current_id,
            message=(
                f"Container was recreated with new ID.\n"
                f"  Cached ID: {cached_id[:12]}... (stale)\n"
                f"  Current ID: {current_id[:12]}... (active)"
            ),
            remediation_steps=[
                "1. Clear cached references and restart:\n"
                "   # Exit Python session and restart\n"
                "   # Or recreate IRISContainer context manager",
                f"2. Verify container is running:\n   docker ps | grep {name}"
            ],
            validation_time=validation_time
        )

    @classmethod
    def docker_error(
        cls,
        name: str,
        error: Exception,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for Docker daemon errors.

        Args:
            name: Container name.
            error: Exception from Docker SDK.
            validation_time: Validation duration in seconds.

        Returns:
            ValidationResult indicating Docker communication error.
        """
        return cls(
            success=False,
            status=ContainerHealthStatus.DOCKER_ERROR,
            container_name=name,
            container_id=None,
            message=f"Cannot connect to Docker daemon.\n  Error: {str(error)}",
            remediation_steps=[
                "1. Check if Docker is running:\n   docker --version",
                "2. Start Docker Desktop (macOS/Windows)\n"
                "   # Or start Docker daemon (Linux):\n"
                "   sudo systemctl start docker",
                "3. Verify Docker is accessible:\n   docker ps"
            ],
            validation_time=validation_time
        )


@dataclass
class ContainerHealth:
    """Detailed container health information.

    Used for comprehensive health checks and diagnostics.
    Provides full metadata for logging, reporting, and debugging.

    Invariants:
        - status=HEALTHY ⟹ running=True AND accessible=True
        - status=RUNNING_NOT_ACCESSIBLE ⟹ running=True AND accessible=False
        - status=NOT_RUNNING ⟹ running=False
        - status=NOT_FOUND ⟹ running=False AND container_id is None

    Examples:
        >>> health = ContainerHealth(
        ...     container_name="iris_db",
        ...     container_id="abc123",
        ...     status=ContainerHealthStatus.HEALTHY,
        ...     running=True,
        ...     accessible=True,
        ...     docker_sdk_version="6.1.0"
        ... )
        >>> assert health.is_healthy()
    """

    container_name: str
    """Container name."""

    status: ContainerHealthStatus
    """Health status."""

    running: bool
    """Container running flag."""

    accessible: bool
    """Exec accessibility test result."""

    docker_sdk_version: str
    """Docker SDK version used for validation."""

    container_id: Optional[str] = None
    """Current container ID."""

    started_at: Optional[str] = None
    """Container start timestamp (ISO format)."""

    port_bindings: Dict[str, str] = field(default_factory=dict)
    """Port mappings (container:host)."""

    image: Optional[str] = None
    """Container image name."""

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "container_name": self.container_name,
            "container_id": self.container_id,
            "status": self.status.value,
            "running": self.running,
            "accessible": self.accessible,
            "started_at": self.started_at,
            "port_bindings": self.port_bindings,
            "image": self.image,
            "docker_sdk_version": self.docker_sdk_version
        }

    def is_healthy(self) -> bool:
        """Check if container is fully healthy.

        Returns:
            True if status is HEALTHY, False otherwise.
        """
        return self.status == ContainerHealthStatus.HEALTHY
