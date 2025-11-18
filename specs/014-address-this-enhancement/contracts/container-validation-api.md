# API Contract: Container Validation

**Feature**: 014-address-this-enhancement
**Date**: 2025-01-17
**Status**: Complete

## Overview

This document defines the public API contract for container validation functionality. All public methods must maintain backward compatibility and follow Constitutional Principle #5 (Fail Fast with Guidance).

---

## Module: iris_devtester.containers.validation

### Function: validate_container()

**Purpose**: Validate Docker container health and accessibility

**Signature**:
```python
def validate_container(
    container_name: str,
    level: HealthCheckLevel = HealthCheckLevel.STANDARD,
    timeout: int = 10,
    docker_client: Optional[docker.DockerClient] = None
) -> ValidationResult:
    """
    Validate Docker container health with progressive checks.

    Performs validation checks based on requested level:
    - MINIMAL: Container exists and running
    - STANDARD: MINIMAL + network accessible
    - FULL: STANDARD + IRIS responsive

    Args:
        container_name: Name of Docker container to validate
        level: Validation depth (default: STANDARD)
        timeout: Maximum seconds for validation checks (default: 10)
        docker_client: Optional Docker client (auto-created if None)

    Returns:
        ValidationResult with status, message, and remediation steps

    Raises:
        ValueError: If container_name is empty or invalid
        TypeError: If arguments are wrong type

    Example:
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
```

**Input Validation**:
```python
# Valid inputs
validate_container("iris_db")  # ✅
validate_container("iris-test", level=HealthCheckLevel.MINIMAL)  # ✅
validate_container("my_container", timeout=30)  # ✅

# Invalid inputs (raise ValueError)
validate_container("")  # ❌ Empty name
validate_container(None)  # ❌ None name (raises TypeError)
validate_container("iris_db", level="invalid")  # ❌ Invalid level (raises TypeError)
validate_container("iris_db", timeout=-1)  # ❌ Negative timeout
```

**Return Values**:

| Scenario | `success` | `status` | `remediation_steps` | `available_containers` |
|----------|-----------|----------|---------------------|------------------------|
| Container healthy | `True` | `HEALTHY` | `[]` | `[]` |
| Container not found | `False` | `NOT_FOUND` | `[...]` | `["iris_test", ...]` |
| Container stopped | `False` | `NOT_RUNNING` | `[...]` | `[]` |
| Container not accessible | `False` | `RUNNING_NOT_ACCESSIBLE` | `[...]` | `[]` |
| Stale reference | `False` | `STALE_REFERENCE` | `[...]` | `[]` |
| Docker daemon error | `False` | `DOCKER_ERROR` | `[...]` | `[]` |

**Performance Contract**:
- `HealthCheckLevel.MINIMAL`: <500ms
- `HealthCheckLevel.STANDARD`: <1000ms
- `HealthCheckLevel.FULL`: <2000ms
- Timeout respected: Never exceeds `timeout` parameter

**Error Handling**:
```python
# ValueError for invalid input
try:
    validate_container("")
except ValueError as e:
    assert "container_name cannot be empty" in str(e)

# Graceful degradation for Docker errors
result = validate_container("iris_db")  # Docker daemon down
assert result.success is False
assert result.status == ContainerHealthStatus.DOCKER_ERROR
assert "docker ps" in " ".join(result.remediation_steps)
```

---

### Enum: HealthCheckLevel

**Purpose**: Define validation check depth

**Values**:
```python
class HealthCheckLevel(str, Enum):
    """Validation check depth levels."""

    MINIMAL = "minimal"      # Just check if container running
    STANDARD = "standard"    # Running + exec accessibility
    FULL = "full"           # STANDARD + IRIS-specific checks
```

**Usage**:
```python
# Fast check (just running status)
result = validate_container("iris_db", level=HealthCheckLevel.MINIMAL)

# Standard check (default - running + accessible)
result = validate_container("iris_db")  # Uses STANDARD

# Full check (including IRIS responsiveness)
result = validate_container("iris_db", level=HealthCheckLevel.FULL)
```

**Performance Characteristics**:
- `MINIMAL`: 1 Docker API call
- `STANDARD`: 2 Docker API calls
- `FULL`: 3 Docker API calls + IRIS exec command

---

### Class: ContainerValidator

**Purpose**: Stateful container validation with caching

**Signature**:
```python
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
            container_name: Container to validate
            docker_client: Optional Docker client
            cache_ttl: Cache TTL in seconds (default: 5)
        """

    def validate(
        self,
        level: HealthCheckLevel = HealthCheckLevel.STANDARD,
        force_refresh: bool = False
    ) -> ValidationResult:
        """
        Validate container health.

        Args:
            level: Validation depth
            force_refresh: Bypass cache and re-validate

        Returns:
            ValidationResult (may be cached)
        """

    def get_health(self, force_refresh: bool = False) -> ContainerHealth:
        """
        Get detailed container health information.

        Args:
            force_refresh: Bypass cache

        Returns:
            ContainerHealth with full metadata
        """

    def clear_cache(self):
        """Clear validation cache."""

    @property
    def container_id(self) -> Optional[str]:
        """Current container ID (None if not found)."""

    @property
    def is_healthy(self) -> bool:
        """Quick health check (uses cache)."""
```

**Usage Example**:
```python
# Create validator for container
validator = ContainerValidator("iris_db")

# First validation (hits Docker)
result = validator.validate(level=HealthCheckLevel.FULL)
assert result.validation_time > 0

# Second validation (cached)
result2 = validator.validate()
assert result2.validation_time < result.validation_time  # Faster

# Force refresh
result3 = validator.validate(force_refresh=True)

# Get detailed health info
health = validator.get_health()
print(f"Container ID: {health.container_id}")
print(f"Started at: {health.started_at}")
```

**Cache Behavior**:
- Cache TTL: 5 seconds (configurable)
- Cache key: `(container_name, level)`
- Cache invalidation: Automatic after TTL, manual via `clear_cache()`
- Stale detection: If container recreated, cache auto-invalidates

---

## Integration with IRISContainer

### Method: IRISContainer.validate()

**Purpose**: Validate IRISContainer health

**Signature**:
```python
class IRISContainer(BaseIRISContainer):
    """Enhanced IRIS container with validation."""

    def validate(
        self,
        level: HealthCheckLevel = HealthCheckLevel.STANDARD
    ) -> ValidationResult:
        """
        Validate this container's health.

        Args:
            level: Validation depth

        Returns:
            ValidationResult for this container

        Example:
            >>> with IRISContainer.community() as iris:
            ...     result = iris.validate()
            ...     if not result.success:
            ...         print(result.format_message())
        """

    def assert_healthy(
        self,
        level: HealthCheckLevel = HealthCheckLevel.STANDARD
    ):
        """
        Assert container is healthy, raise if not.

        Args:
            level: Validation depth

        Raises:
            ContainerValidationError: If validation fails

        Example:
            >>> with IRISContainer.community() as iris:
            ...     iris.assert_healthy()  # Raises if not healthy
            ...     conn = iris.get_connection()
        """
```

**Usage Example**:
```python
# Validate before operations
with IRISContainer.community() as iris:
    # Quick validation
    result = iris.validate(level=HealthCheckLevel.MINIMAL)
    if not result.success:
        print(result.format_message())
        raise RuntimeError("Container not healthy")

    # Or assert (raises exception)
    iris.assert_healthy()

    # Safe to use now
    conn = iris.get_connection()
```

---

## Error Messages Contract

### Structure

All error messages MUST follow this structure (Constitutional Principle #5):

```
Container validation failed for '{container_name}'

What went wrong:
  {specific_diagnosis}

How to fix it:
  {remediation_step_1}
  {remediation_step_2}
  ...

{optional_context}
```

### Examples

**Container Not Found**:
```
Container validation failed for 'iris_db'

What went wrong:
  Container 'iris_db' does not exist.

How to fix it:
  1. List all containers:
     docker ps -a

  2. Start container if it exists:
     docker start iris_db

  3. Or create new container:
     docker run -d --name iris_db intersystemsdc/iris-community:latest

Available containers:
  - iris_test (running)
  - iris_prod (stopped)
```

**Container Not Running**:
```
Container validation failed for 'iris_db'

What went wrong:
  Container exists but is not running (status: exited).

How to fix it:
  docker start iris_db
```

**Container Not Accessible**:
```
Container validation failed for 'iris_db'

What went wrong:
  Container is running but not accessible (exec failed).
  Error: Cannot connect to container daemon

How to fix it:
  1. Restart container:
     docker restart iris_db

  2. Check container logs:
     docker logs iris_db | tail -20

  3. Enable CallIn service (for IRIS):
     iris-devtester container enable-callin iris_db
```

**Stale Reference**:
```
Container validation failed for 'iris_db'

What went wrong:
  Container was recreated with new ID.
  Cached ID: abc123... (stale)
  Current ID: def456... (active)

How to fix it:
  1. Clear cached references and restart:
     # Exit Python session and restart
     # Or recreate IRISContainer context manager

  2. Verify container is running:
     docker ps | grep iris_db
```

---

## Backward Compatibility

### Existing Code

All existing code MUST continue to work:

```python
# Existing pattern - still works
with IRISContainer.community() as iris:
    conn = iris.get_connection()  # ✅ Still works

# Existing container_status.py - enhanced
from iris_devtester.utils import get_container_status
success, message = get_container_status("iris_db")  # ✅ Still works
```

### Migration Path

New validation is **opt-in**:

```python
# Old way (still works)
with IRISContainer.community() as iris:
    conn = iris.get_connection()

# New way (explicit validation)
with IRISContainer.community() as iris:
    result = iris.validate()
    if result.success:
        conn = iris.get_connection()
```

**No Breaking Changes**: Existing code runs unchanged.

---

## Testing Contract

### Unit Tests

**File**: `tests/unit/test_validation_models.py`

Required tests:
- `test_validation_result_healthy()`
- `test_validation_result_not_found()`
- `test_validation_result_factory_methods()`
- `test_container_health_invariants()`
- `test_health_status_enum_values()`

### Contract Tests

**File**: `tests/contract/test_container_validation_api.py`

Required tests:
- `test_validate_container_signature()`
- `test_validate_container_minimal_level()`
- `test_validate_container_standard_level()`
- `test_validate_container_full_level()`
- `test_validate_container_invalid_input()`
- `test_validate_container_timeout()`
- `test_container_validator_caching()`
- `test_iriscontainer_validate_method()`

### Integration Tests

**File**: `tests/integration/test_container_validation.py`

Required tests:
- `test_validate_running_container()`
- `test_validate_stopped_container()`
- `test_validate_nonexistent_container()`
- `test_validate_with_docker_down()`

---

## Performance SLA

| Operation | Max Time | Typical Time |
|-----------|----------|--------------|
| `validate_container(MINIMAL)` | 500ms | 100ms |
| `validate_container(STANDARD)` | 1000ms | 300ms |
| `validate_container(FULL)` | 2000ms | 800ms |
| `ContainerValidator.validate()` (cached) | 10ms | 1ms |
| `ValidationResult.format_message()` | 50ms | 5ms |

**SLA Violations**: Log warning if exceeded, but don't fail operation.

---

## Security Considerations

### Docker Socket Access

- **Requirement**: Read-only access to Docker socket
- **Permissions**: Standard Docker user (non-root)
- **Operations**: Only inspection (no container modification)

### Error Message Sanitization

- **No secrets**: Never include passwords or credentials
- **Path sanitization**: Redact user home directories
- **Container ID truncation**: Show first 12 characters only

---

## Versioning

**API Version**: 1.0.0

**Compatibility Promise**:
- Signature changes: Major version bump (2.0.0)
- New optional parameters: Minor version bump (1.1.0)
- Bug fixes: Patch version bump (1.0.1)

**Deprecation Policy**:
- 1 version deprecation warning before removal
- Minimum 6 months before breaking change

---

## Constitutional Compliance Checklist

- [x] **Principle #1**: Automatic detection of stale references
- [x] **Principle #5**: Structured error messages with remediation
- [x] **Principle #7**: Non-destructive validation, comprehensive error handling
- [x] **Backward compatible**: Existing code works unchanged
- [x] **Performance**: All operations under 2s SLA
- [x] **Type safe**: Full type hints for mypy
- [x] **Documented**: Every public method has docstring
