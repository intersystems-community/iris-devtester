"""Container validation logic.

Provides defensive container validation to detect and remediate
Docker container issues like stale ID references, stopped containers,
and accessibility problems.

Constitutional Compliance:
- Principle #1: Automatic remediation (error messages include fix commands)
- Principle #5: Fail fast with guidance (structured error messages)
- Principle #7: Medical-grade reliability (comprehensive validation)
"""

import logging
import time
from typing import Optional, List

import docker
from docker.errors import DockerException, NotFound, APIError

from iris_devtester.containers.models import (
    ContainerHealthStatus,
    HealthCheckLevel,
    ValidationResult,
    ContainerHealth,
)

logger = logging.getLogger(__name__)


def validate_container(
    container_name: str,
    level: HealthCheckLevel = HealthCheckLevel.STANDARD,
    timeout: int = 10,
    docker_client: Optional[docker.DockerClient] = None
) -> ValidationResult:
    """
    Validate Docker container health with progressive checks.

    Performs validation checks based on requested level:
    - MINIMAL: Container exists and running (<500ms target)
    - STANDARD: MINIMAL + network accessible (<1000ms target)
    - FULL: STANDARD + IRIS responsive (<2000ms target)

    Args:
        container_name: Name of Docker container to validate.
        level: Validation depth (default: STANDARD).
        timeout: Maximum seconds for validation checks (default: 10).
        docker_client: Optional Docker client (auto-created if None).

    Returns:
        ValidationResult with status, message, and remediation steps.

    Raises:
        ValueError: If container_name is empty or invalid.
        TypeError: If arguments are wrong type.

    Examples:
        >>> from iris_devtester.containers import validate_container, HealthCheckLevel
        >>> result = validate_container("iris_db", level=HealthCheckLevel.FULL)
        >>> if result.success:
        ...     print("Container healthy!")
        ... else:
        ...     print(result.format_message())

    Constitutional Compliance:
        - Principle #1: Auto-detects issues without manual intervention
        - Principle #5: Provides structured guidance on failures
        - Principle #7: Non-destructive read-only validation
    """
    # Input validation
    if not isinstance(container_name, str):
        raise TypeError(f"container_name must be str, got {type(container_name).__name__}")

    if not container_name or not container_name.strip():
        raise ValueError("container_name cannot be empty")

    if not isinstance(level, HealthCheckLevel):
        raise TypeError(f"level must be HealthCheckLevel, got {type(level).__name__}")

    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(f"timeout must be positive number, got {timeout}")

    # Start timing
    start_time = time.time()

    # Create Docker client if not provided
    if docker_client is None:
        try:
            docker_client = docker.from_env(timeout=timeout)
        except DockerException as e:
            elapsed = time.time() - start_time
            return ValidationResult.docker_error(
                name=container_name,
                error=e,
                validation_time=elapsed
            )

    # Progressive validation strategy
    try:
        # Step 1: Check container existence (MINIMAL level)
        container = _get_container_by_name(docker_client, container_name)

        if container is None:
            # Container not found
            elapsed = time.time() - start_time
            available = _get_available_containers(docker_client)
            return ValidationResult.not_found(
                name=container_name,
                available_containers=available,
                validation_time=elapsed
            )

        # Step 2: Check running status (MINIMAL level)
        container.reload()  # Refresh container state
        is_running = container.status == "running"

        if not is_running:
            elapsed = time.time() - start_time
            return ValidationResult.not_running(
                name=container_name,
                container_id=container.id,
                validation_time=elapsed,
                container_status=container.status
            )

        # MINIMAL check complete
        if level == HealthCheckLevel.MINIMAL:
            elapsed = time.time() - start_time
            return ValidationResult.healthy(
                name=container_name,
                container_id=container.id,
                validation_time=elapsed
            )

        # Step 3: Check exec accessibility (STANDARD level)
        is_accessible, access_error = _check_exec_accessibility(
            container,
            timeout=timeout
        )

        if not is_accessible:
            elapsed = time.time() - start_time
            return ValidationResult.not_accessible(
                name=container_name,
                container_id=container.id,
                error=access_error or "Unknown exec error",
                validation_time=elapsed
            )

        # STANDARD check complete
        if level == HealthCheckLevel.STANDARD:
            elapsed = time.time() - start_time
            return ValidationResult.healthy(
                name=container_name,
                container_id=container.id,
                validation_time=elapsed
            )

        # Step 4: IRIS-specific health check (FULL level)
        is_iris_healthy, iris_error = _check_iris_health(
            container,
            timeout=timeout
        )

        if not is_iris_healthy:
            elapsed = time.time() - start_time
            return ValidationResult.not_accessible(
                name=container_name,
                container_id=container.id,
                error=f"IRIS not responsive: {iris_error}",
                validation_time=elapsed
            )

        # FULL check complete - container is healthy
        elapsed = time.time() - start_time
        return ValidationResult.healthy(
            name=container_name,
            container_id=container.id,
            validation_time=elapsed
        )

    except DockerException as e:
        elapsed = time.time() - start_time
        return ValidationResult.docker_error(
            name=container_name,
            error=e,
            validation_time=elapsed
        )


def _get_container_by_name(
    client: docker.DockerClient,
    name: str
) -> Optional[docker.models.containers.Container]:
    """Get container by name.

    Args:
        client: Docker client.
        name: Container name.

    Returns:
        Container object if found, None otherwise.
    """
    try:
        return client.containers.get(name)
    except NotFound:
        return None
    except Exception:
        # Any other error (connection, permission, etc.)
        return None


def _get_available_containers(
    client: docker.DockerClient
) -> List[str]:
    """Get list of available container names.

    Args:
        client: Docker client.

    Returns:
        List of container names (running + stopped).
    """
    try:
        containers = client.containers.list(all=True)
        names = []
        for container in containers:
            if container.name:
                status = f"({container.status})" if container.status != "running" else "(running)"
                names.append(f"{container.name} {status}")
        return names
    except Exception:
        return []


def _check_exec_accessibility(
    container: docker.models.containers.Container,
    timeout: int = 10
) -> tuple[bool, Optional[str]]:
    """Check if container accepts exec commands.

    Args:
        container: Container to check.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (is_accessible, error_message).
    """
    try:
        # Simple echo command to test exec
        exec_result = container.exec_run(
            "echo healthy",
            demux=False
        )

        if exec_result.exit_code == 0:
            return True, None
        else:
            return False, f"Exec failed with exit code {exec_result.exit_code}"

    except Exception as e:
        return False, str(e)


def _check_iris_health(
    container: docker.models.containers.Container,
    timeout: int = 10
) -> tuple[bool, Optional[str]]:
    """Check IRIS-specific health (FULL validation level).

    Attempts to execute IRIS SQL query to verify database is responsive.

    Args:
        container: Container to check.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (is_healthy, error_message).
    """
    try:
        # Try to execute simple IRIS query
        # This uses the iris session command available in IRIS containers
        exec_result = container.exec_run(
            "iris session IRIS -U %SYS '##class(%SYSTEM.Process).CurrentDirectory()'",
            demux=False
        )

        if exec_result.exit_code == 0:
            return True, None
        else:
            return False, f"IRIS query failed with exit code {exec_result.exit_code}"

    except Exception as e:
        return False, str(e)


class ContainerValidator:
    """
    Stateful container validator with optional caching.

    Use for repeated validation of the same container to avoid
    redundant Docker API calls.

    Example:
        >>> validator = ContainerValidator("iris_db")
        >>> result = validator.validate()
        >>> if result.success:
        ...     connection = validator.get_connection_info()
    """

    def __init__(
        self,
        container_name: str,
        docker_client: Optional[docker.DockerClient] = None,
        cache_ttl: int = 5
    ):
        """
        Initialize validator for specific container.

        Args:
            container_name: Container to validate.
            docker_client: Optional Docker client.
            cache_ttl: Cache TTL in seconds (default: 5).
        """
        if not isinstance(container_name, str) or not container_name.strip():
            raise ValueError("container_name must be non-empty string")

        self._container_name = container_name
        self._docker_client = docker_client or docker.from_env()
        self._cache_ttl = cache_ttl

        # Cache state
        self._cached_result: Optional[ValidationResult] = None
        self._cache_timestamp: float = 0.0
        self._cached_health: Optional[ContainerHealth] = None

    def validate(
        self,
        level: HealthCheckLevel = HealthCheckLevel.STANDARD,
        force_refresh: bool = False
    ) -> ValidationResult:
        """
        Validate container health.

        Args:
            level: Validation depth.
            force_refresh: Bypass cache and re-validate.

        Returns:
            ValidationResult (may be cached).
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.debug(f"Using cached validation result for {self._container_name}")
            return self._cached_result

        # Perform validation
        result = validate_container(
            container_name=self._container_name,
            level=level,
            docker_client=self._docker_client
        )

        # Update cache
        self._cached_result = result
        self._cache_timestamp = time.time()

        return result

    def get_health(self, force_refresh: bool = False) -> ContainerHealth:
        """
        Get detailed container health information.

        Args:
            force_refresh: Bypass cache.

        Returns:
            ContainerHealth with full metadata.

        Raises:
            ValueError: If container not found or not accessible.
        """
        # Check cache
        if not force_refresh and self._cached_health and self._is_cache_valid():
            return self._cached_health

        # Get container
        try:
            container = self._docker_client.containers.get(self._container_name)
            container.reload()

            # Check accessibility
            is_accessible, _ = _check_exec_accessibility(container)

            # Determine status
            if container.status == "running" and is_accessible:
                status = ContainerHealthStatus.HEALTHY
            elif container.status == "running":
                status = ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE
            elif container.status == "exited":
                status = ContainerHealthStatus.NOT_RUNNING
            else:
                status = ContainerHealthStatus.NOT_RUNNING

            # Extract port bindings
            port_bindings = {}
            if container.attrs.get("NetworkSettings", {}).get("Ports"):
                for internal, external in container.attrs["NetworkSettings"]["Ports"].items():
                    if external:
                        port_bindings[internal] = external[0]["HostPort"]

            # Build health object
            health = ContainerHealth(
                container_name=self._container_name,
                container_id=container.id,
                status=status,
                running=(container.status == "running"),
                accessible=is_accessible,
                started_at=container.attrs.get("State", {}).get("StartedAt"),
                port_bindings=port_bindings,
                image=container.image.tags[0] if container.image.tags else None,
                docker_sdk_version=docker.__version__
            )

            # Cache result
            self._cached_health = health
            self._cache_timestamp = time.time()

            return health

        except NotFound:
            raise ValueError(f"Container '{self._container_name}' not found")
        except Exception as e:
            raise ValueError(f"Failed to get container health: {e}")

    def clear_cache(self):
        """Clear validation cache."""
        self._cached_result = None
        self._cached_health = None
        self._cache_timestamp = 0.0

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cached_result is None:
            return False

        elapsed = time.time() - self._cache_timestamp
        return elapsed < self._cache_ttl

    @property
    def container_id(self) -> Optional[str]:
        """Current container ID (None if not found)."""
        if self._cached_result and self._cached_result.container_id:
            return self._cached_result.container_id

        try:
            container = self._docker_client.containers.get(self._container_name)
            return container.id
        except Exception:
            return None

    @property
    def is_healthy(self) -> bool:
        """Quick health check (uses cache)."""
        result = self.validate()
        return result.success
