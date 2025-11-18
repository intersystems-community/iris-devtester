# Data Model: Defensive Container Validation

**Feature**: 014-address-this-enhancement
**Date**: 2025-01-17
**Status**: Complete

## Overview

This feature introduces two primary data models for representing container health state and validation results. Both use Python dataclasses for type safety and clear structure.

---

## Entity 1: ContainerHealthStatus (Enum)

**Purpose**: Enumerate possible container health states

**Type**: String Enum

**Values**:
```python
class ContainerHealthStatus(str, Enum):
    """Container health status values."""

    HEALTHY = "healthy"                  # Container running and accessible
    RUNNING_NOT_ACCESSIBLE = "running_not_accessible"  # Running but exec fails
    NOT_RUNNING = "not_running"          # Exists but not running
    NOT_FOUND = "not_found"              # Container does not exist
    STALE_REFERENCE = "stale_reference"  # Container recreated with new ID
    DOCKER_ERROR = "docker_error"        # Docker daemon communication failed
```

**Usage**:
```python
if validation.status == ContainerHealthStatus.NOT_FOUND:
    print(f"Container not found: {validation.message}")
```

**Rationale**:
- String enum for JSON serialization
- Explicit states from functional requirements (FR-007)
- Covers all edge cases from spec

---

## Entity 2: ValidationResult (Dataclass)

**Purpose**: Encapsulate container validation check results

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `success` | `bool` | Yes | Overall validation success (True = healthy) |
| `status` | `ContainerHealthStatus` | Yes | Specific health status |
| `container_name` | `str` | Yes | Name of validated container |
| `container_id` | `Optional[str]` | No | Current container ID (if exists) |
| `message` | `str` | Yes | Human-readable status message |
| `remediation_steps` | `List[str]` | Yes | Actionable fix commands (empty if success) |
| `available_containers` | `List[str]` | No | Alternative containers (only if not found) |
| `validation_time` | `float` | Yes | Time taken for validation (seconds) |

**Structure**:
```python
@dataclass
class ValidationResult:
    """Result of container validation check."""

    success: bool
    status: ContainerHealthStatus
    container_name: str
    message: str
    remediation_steps: List[str]
    container_id: Optional[str] = None
    available_containers: List[str] = field(default_factory=list)
    validation_time: float = 0.0

    def format_message(self) -> str:
        """
        Format validation result as multi-line message.

        Returns structured error message following Constitutional Principle #5.
        """
        ...

    @classmethod
    def healthy(cls, name: str, container_id: str, validation_time: float) -> "ValidationResult":
        """Factory method for healthy container."""
        ...

    @classmethod
    def not_found(
        cls,
        name: str,
        available_containers: List[str],
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for container not found."""
        ...

    @classmethod
    def not_running(
        cls,
        name: str,
        container_id: str,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for stopped container."""
        ...

    @classmethod
    def not_accessible(
        cls,
        name: str,
        container_id: str,
        error: str,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for inaccessible container."""
        ...

    @classmethod
    def stale_reference(
        cls,
        name: str,
        cached_id: str,
        current_id: str,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for stale container reference."""
        ...

    @classmethod
    def docker_error(
        cls,
        name: str,
        error: Exception,
        validation_time: float
    ) -> "ValidationResult":
        """Factory method for Docker daemon errors."""
        ...
```

**Example Usage**:
```python
# Validation succeeded
result = ValidationResult.healthy(
    name="iris_db",
    container_id="abc123...",
    validation_time=0.15
)
assert result.success is True
assert result.status == ContainerHealthStatus.HEALTHY

# Validation failed - container not found
result = ValidationResult.not_found(
    name="iris_db",
    available_containers=["iris_test", "iris_prod"],
    validation_time=0.12
)
assert result.success is False
assert result.status == ContainerHealthStatus.NOT_FOUND
assert len(result.remediation_steps) > 0
print(result.format_message())
```

**Factory Methods Rationale**:
- Enforce correct field combinations for each status
- Self-documenting creation pattern
- Consistent message/remediation formatting
- Follows builder pattern for complex objects

---

## Entity 3: ContainerHealth (Dataclass)

**Purpose**: Extended health information for detailed inspection

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `container_name` | `str` | Yes | Container name |
| `container_id` | `Optional[str]` | No | Current container ID |
| `status` | `ContainerHealthStatus` | Yes | Health status |
| `running` | `bool` | Yes | Container running flag |
| `accessible` | `bool` | Yes | Exec accessibility test result |
| `started_at` | `Optional[str]` | No | Container start timestamp (ISO format) |
| `port_bindings` | `Dict[str, str]` | No | Port mappings (container:host) |
| `image` | `Optional[str]` | No | Container image name |
| `docker_sdk_version` | `str` | Yes | Docker SDK version used |

**Structure**:
```python
@dataclass
class ContainerHealth:
    """
    Detailed container health information.

    Used for comprehensive health checks and diagnostics.
    """

    container_name: str
    status: ContainerHealthStatus
    running: bool
    accessible: bool
    docker_sdk_version: str
    container_id: Optional[str] = None
    started_at: Optional[str] = None
    port_bindings: Dict[str, str] = field(default_factory=dict)
    image: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        ...

    def is_healthy(self) -> bool:
        """Check if container is fully healthy."""
        return self.status == ContainerHealthStatus.HEALTHY
```

**Example Usage**:
```python
health = ContainerHealth(
    container_name="iris_db",
    container_id="abc123...",
    status=ContainerHealthStatus.HEALTHY,
    running=True,
    accessible=True,
    started_at="2025-01-17T10:30:00Z",
    port_bindings={"1972/tcp": "1972"},
    image="intersystemsdc/iris-community:latest",
    docker_sdk_version="6.1.0"
)

# Serialize for logging/reporting
health_json = health.to_dict()
```

**Use Cases**:
- Detailed health check reports
- Diagnostic logging
- Container metadata inspection
- Debugging container issues

---

## Entity Relationships

```
ValidationResult
├── status: ContainerHealthStatus (enum)
├── container_name: str
├── container_id: Optional[str]
└── remediation_steps: List[str]

ContainerHealth
├── status: ContainerHealthStatus (enum)
├── container_name: str
├── container_id: Optional[str]
└── [detailed metadata...]
```

**Relationship**:
- `ValidationResult` - Lightweight, focused on validation outcome
- `ContainerHealth` - Comprehensive, includes all diagnostic metadata
- Both share `ContainerHealthStatus` enum for consistency

---

## Validation Rules

### ValidationResult Invariants

1. **Success consistency**:
   - `success=True` ⟹ `status=HEALTHY`
   - `success=False` ⟹ `status != HEALTHY`

2. **Remediation steps**:
   - `success=False` ⟹ `len(remediation_steps) > 0`
   - `success=True` ⟹ `remediation_steps == []`

3. **Available containers**:
   - `status=NOT_FOUND` ⟹ `len(available_containers) >= 0`
   - `status != NOT_FOUND` ⟹ `available_containers == []`

4. **Container ID**:
   - `status=NOT_FOUND` ⟹ `container_id is None`
   - `status != NOT_FOUND` ⟹ `container_id is not None`

### ContainerHealth Invariants

1. **Health status consistency**:
   - `status=HEALTHY` ⟹ `running=True AND accessible=True`
   - `status=RUNNING_NOT_ACCESSIBLE` ⟹ `running=True AND accessible=False`
   - `status=NOT_RUNNING` ⟹ `running=False`
   - `status=NOT_FOUND` ⟹ `running=False AND container_id is None`

---

## State Transitions

```
[Initial State]
      ↓
Container Lookup by Name
      ↓
   ┌──────────┐
   │ Exists?  │
   └──────────┘
      ↓     ↓
     No    Yes → Check Running State
      ↓           ↓     ↓
  NOT_FOUND      No    Yes → Check Accessibility
                  ↓           ↓         ↓
             NOT_RUNNING     No        Yes
                              ↓         ↓
                    RUNNING_NOT_ACCESSIBLE  HEALTHY
```

**Special Cases**:

1. **Stale Reference Detection**:
   ```
   Lookup by Cached ID
         ↓
   "container not running" error
         ↓
   Lookup by Name (succeeds)
         ↓
   Compare IDs → Different
         ↓
   STALE_REFERENCE
   ```

2. **Docker Daemon Error**:
   ```
   Any Docker SDK call
         ↓
   docker.errors.APIError
         ↓
   DOCKER_ERROR
   ```

---

## Performance Characteristics

### ValidationResult
- **Memory**: ~200 bytes (typical)
- **Creation**: O(1)
- **Serialization**: O(n) where n = message length

### ContainerHealth
- **Memory**: ~500 bytes (typical)
- **Creation**: O(1)
- **Serialization**: O(1)

### Validation Check
- **Time**: 100ms - 2000ms (depending on check level)
- **Docker API calls**: 1-3 (progressive)

---

## Example Scenarios

### Scenario 1: Container Healthy
```python
result = validate_container("iris_db", HealthCheckLevel.FULL)

assert result.success is True
assert result.status == ContainerHealthStatus.HEALTHY
assert result.container_id is not None
assert result.remediation_steps == []
```

### Scenario 2: Container Not Found
```python
result = validate_container("nonexistent", HealthCheckLevel.MINIMAL)

assert result.success is False
assert result.status == ContainerHealthStatus.NOT_FOUND
assert result.container_id is None
assert "iris_test" in result.available_containers
assert "docker ps -a" in result.remediation_steps[0]
```

### Scenario 3: Stale Reference Detected
```python
# Container was recreated
result = validate_container("iris_db", HealthCheckLevel.MINIMAL)

assert result.success is False
assert result.status == ContainerHealthStatus.STALE_REFERENCE
assert "Container was recreated" in result.message
assert "docker restart" in " ".join(result.remediation_steps)
```

---

## Constitutional Compliance

### Principle #5: Fail Fast with Guidance
✅ **Compliant**: `ValidationResult.format_message()` provides:
- "What went wrong" (message field)
- "How to fix it" (remediation_steps field)
- Actionable commands (copy-paste ready)

### Principle #7: Medical-Grade Reliability
✅ **Compliant**:
- Type-safe dataclasses (mypy validated)
- Immutable after creation (frozen=True option)
- Clear invariants (documented above)
- Factory methods enforce correctness

---

## Future Considerations

### Potential Extensions

1. **Metrics Collection**:
   - Add `check_count: int` to track validation frequency
   - Add `last_healthy_at: datetime` for uptime tracking

2. **History Tracking**:
   - Add `previous_status: ContainerHealthStatus` for state changes
   - Add `status_changed_at: datetime` for transition tracking

3. **Custom Remediation**:
   - Add `custom_remediation: Callable` for project-specific fixes
   - Add `auto_remediate: bool` flag for automatic recovery

**Note**: These are NOT in scope for initial implementation (Feature 014).
