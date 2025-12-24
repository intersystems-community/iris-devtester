# Data Model: Fix IRIS Container Infrastructure Issues

**Feature**: 011-fix-iris-container
**Date**: 2025-01-13
**Status**: Complete

## Overview

This feature introduces no new data structures but clarifies existing entities related to container lifecycle management. The data model focuses on configuration and runtime state tracking for IRIS containers.

## Entities

### 1. ContainerConfig (Existing - Enhanced)

**Purpose**: Configuration for IRIS container creation

**Location**: `iris_devtester/config/container_config.py`

**Existing Fields**:
```python
class ContainerConfig:
    edition: str = "community"  # "community" or "enterprise"
    container_name: str = "iris-container"
    superserver_port: int = 1972
    webserver_port: int = 52773
    namespace: str = "USER"
    password: str = "SYS"
    image_tag: str = "latest"
    volumes: List[str] = []  # Docker volume syntax: "host:container:mode"
    license_key: Optional[str] = None
```

**Enhancements Required**:
- Add volume path validation (FR-016)
- Add `use_testcontainers` parameter for lifecycle control

**New Methods**:
```python
def validate_volume_paths(self) -> List[str]:
    """
    Validate that all volume host paths exist.

    Returns:
        List of error messages for invalid paths (empty list if all valid)

    Constitutional Principle #5: Fail Fast with Guidance
    """
    errors = []
    for volume in self.volumes:
        parts = volume.split(":")
        host_path = parts[0]
        if not os.path.exists(host_path):
            errors.append(
                f"Volume host path does not exist: {host_path}\n"
                f"  Required by volume mount: {volume}\n"
                f"  Create the directory or fix the path in configuration"
            )
    return errors
```

**Validation Rules**:
- Host path in `volumes` must exist before container creation
- Volume syntax: `host:container` or `host:container:mode` (mode = "rw" or "ro")
- Invalid volumes should raise clear error at configuration time (not creation time)

### 2. VolumeMountSpec (New - Internal Helper)

**Purpose**: Structured representation of volume mount configuration

**Location**: `iris_devtester/utils/iris_container_adapter.py` (internal class)

**Fields**:
```python
@dataclass
class VolumeMountSpec:
    """
    Parsed volume mount specification.

    Used internally to parse Docker volume syntax into structured format.
    """
    host_path: str          # Absolute path on host
    container_path: str     # Path inside container
    mode: str = "rw"        # "rw" (read-write) or "ro" (read-only)

    @classmethod
    def parse(cls, volume_string: str) -> 'VolumeMountSpec':
        """
        Parse Docker volume syntax: host:container or host:container:mode

        Examples:
            "./data:/external" → VolumeMountSpec("./data", "/external", "rw")
            "./config:/app/config:ro" → VolumeMountSpec("./config", "/app/config", "ro")

        Raises:
            ValueError: If volume string format is invalid
        """
        parts = volume_string.split(":")
        if len(parts) < 2:
            raise ValueError(
                f"Invalid volume syntax: {volume_string}\n"
                f"Expected format: host:container or host:container:mode"
            )

        host_path = parts[0]
        container_path = parts[1]
        mode = parts[2] if len(parts) > 2 else "rw"

        if mode not in ["rw", "ro"]:
            raise ValueError(
                f"Invalid volume mode: {mode}\n"
                f"Must be 'rw' (read-write) or 'ro' (read-only)"
            )

        return cls(host_path=host_path, container_path=container_path, mode=mode)
```

**Usage**:
```python
# Parse volumes from config
for volume_str in config.volumes:
    spec = VolumeMountSpec.parse(volume_str)
    # Use spec.host_path, spec.container_path, spec.mode
```

### 3. ContainerPersistenceCheck (New)

**Purpose**: Results of post-creation container verification

**Location**: `iris_devtester/utils/iris_container_adapter.py`

**Fields**:
```python
@dataclass
class ContainerPersistenceCheck:
    """
    Results of container persistence verification.

    Constitutional Principle #5: Fail Fast with Guidance
    Constitutional Principle #7: Medical-Grade Reliability
    """
    container_name: str
    exists: bool                        # Container found in Docker
    status: Optional[str]               # 'running', 'created', 'exited', etc.
    volume_mounts_verified: bool        # All volumes accessible
    verification_time: float            # Seconds since creation
    error_details: Optional[str] = None # Error message if verification failed

    @property
    def success(self) -> bool:
        """Container is running and all checks passed."""
        return (
            self.exists
            and self.status in ['running', 'created']
            and self.volume_mounts_verified
            and self.error_details is None
        )

    def get_error_message(self, config: ContainerConfig) -> str:
        """
        Generate constitutional error message (What/Why/How/Docs format).

        Constitutional Principle #5: Fail Fast with Guidance
        """
        if self.success:
            return ""

        if not self.exists:
            return (
                f"Container '{self.container_name}' was created but immediately disappeared\n"
                "\n"
                "What went wrong:\n"
                "  The container was created successfully but was removed by cleanup service.\n"
                "  This is typically caused by testcontainers ryuk service.\n"
                "\n"
                "How to fix it:\n"
                "  1. For CLI commands: This is a bug in iris-devtester (should use Docker SDK)\n"
                "  2. For pytest fixtures: This is expected behavior (automatic cleanup)\n"
                "  3. Check Docker labels: docker inspect {self.container_name}\n"
                "\n"
                "Documentation: docs/learnings/testcontainers-ryuk-lifecycle.md\n"
            )

        if not self.volume_mounts_verified:
            return (
                f"Container '{self.container_name}' created but volume mounts failed\n"
                "\n"
                "What went wrong:\n"
                "  Volume mount verification failed - configured volumes not accessible.\n"
                f"  Configured volumes: {config.volumes}\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify host paths exist: ls -la <host_path>\n"
                "  2. Check Docker volume syntax: host:container or host:container:mode\n"
                "  3. Inspect container mounts: docker inspect {self.container_name}\n"
                "\n"
                "Documentation: https://docs.docker.com/storage/volumes/\n"
            )

        return self.error_details or "Unknown verification failure"
```

**Usage**:
```python
# After container creation
check = verify_container_persistence(config.container_name, config)
if not check.success:
    raise ValueError(check.get_error_message(config))
```

### 4. IRISContainerManager (Existing - Enhanced)

**Purpose**: Factory for creating IRIS containers with lifecycle control

**Location**: `iris_devtester/utils/iris_container_adapter.py`

**Enhancement**: Add `use_testcontainers` parameter

**Before**:
```python
@staticmethod
def create_from_config(config: ContainerConfig) -> IRISContainer:
    """Create IRIS container from configuration."""
    # Always uses testcontainers-iris (automatic cleanup)
```

**After**:
```python
@staticmethod
def create_from_config(
    config: ContainerConfig,
    use_testcontainers: bool = False
) -> Union[IRISContainer, DockerContainer]:
    """
    Create IRIS container from configuration.

    Args:
        config: Container configuration
        use_testcontainers: If True, use testcontainers-iris (automatic cleanup)
                            If False, use Docker SDK directly (manual cleanup)

    Returns:
        IRISContainer if use_testcontainers=True
        DockerContainer if use_testcontainers=False

    Constitutional Principle #3: Isolation by Default
    - Test fixtures: use_testcontainers=True (automatic cleanup)
    - CLI commands: use_testcontainers=False (manual cleanup)
    """
    if use_testcontainers:
        return _create_with_testcontainers(config)
    else:
        return _create_with_docker_sdk(config)
```

**Lifecycle Modes**:

| Mode | Use Case | Cleanup | ryuk | Persistence |
|------|----------|---------|------|-------------|
| `use_testcontainers=True` | pytest fixtures | Automatic | Yes | Until fixture scope ends |
| `use_testcontainers=False` | CLI commands | Manual | No | Until explicit removal |

**CLI Usage**:
```python
# In cli/container.py
container = IRISContainerManager.create_from_config(
    config,
    use_testcontainers=False  # CLI mode: manual cleanup
)
```

**Pytest Usage**:
```python
# In tests/conftest.py
@pytest.fixture
def iris_container():
    container = IRISContainerManager.create_from_config(
        config,
        use_testcontainers=True  # Test mode: automatic cleanup
    )
    yield container
    # Automatic cleanup by testcontainers
```

## State Transitions

### Container Lifecycle States

```
[Configuration]
    ↓ validate_volume_paths()
[Validated Config]
    ↓ create_from_config()
[Container Creating]
    ↓ (if use_testcontainers=False)
[Docker SDK Creation]
    ↓ apply volumes, start container
[Container Started]
    ↓ verify_container_persistence()
[Persistence Check]
    ↓ (if check.success)
[Container Running] → (persists until explicit cleanup)
    ↓ (if !check.success)
[Error] → Constitutional error message

Alternative path (use_testcontainers=True):
[Container Creating]
    ↓ (if use_testcontainers=True)
[Testcontainers Creation]
    ↓ testcontainers-iris handles lifecycle
[Container Running] → (persists until fixture scope ends)
```

### Volume Mount Verification Flow

```
[Container Started]
    ↓ Get container.attrs['Mounts']
[Inspect Mounts]
    ↓ For each configured volume
[Check Mount Exists]
    ↓ docker exec cat <container_path>/test_file
[Verify Accessibility]
    ↓ All mounts verified?
[Verification Success] or [Verification Failure]
```

## Validation Rules

### Volume Path Validation (FR-016)

**Rule**: Host paths in `volumes` configuration must exist before container creation

**Validation Point**: During `ContainerConfig` construction or at CLI command start

**Error Message Format** (Constitutional Principle #5):
```
Volume host path does not exist: /path/to/host/dir

What went wrong:
  Volume mount requires host path '/path/to/host/dir' but it doesn't exist.
  Container creation will fail if we proceed.

How to fix it:
  1. Create directory: mkdir -p /path/to/host/dir
  2. Or fix path in configuration: iris-config.yml
  3. Or remove volume from configuration if not needed

Configuration: volumes: ["/path/to/host/dir:/container/path"]
```

### Volume Syntax Validation

**Rule**: Volume string must match pattern `host:container` or `host:container:mode`

**Valid Examples**:
- `./data:/external` → host=./data, container=/external, mode=rw
- `/tmp/workspace:/opt/workspace:ro` → read-only mount

**Invalid Examples**:
- `./data` → Missing container path
- `./data:` → Empty container path
- `./data:/external:invalid` → Invalid mode (must be rw or ro)

### Container Persistence Validation (FR-017)

**Rule**: After creation, container must exist and be running for at least 2 seconds

**Validation Steps**:
1. Create container
2. Wait 2 seconds (allow Docker to settle)
3. Query Docker: `docker inspect <container_name>`
4. Verify: `status in ['running', 'created']`
5. Verify: All volume mounts exist in `container.attrs['Mounts']`

**Failure Modes**:
- Container not found → Immediate cleanup (ryuk issue)
- Container status = 'exited' → Creation succeeded but startup failed
- Volumes missing → Mount configuration not applied

## Relationships

```
ContainerConfig
    ├─ validates → VolumeMountSpec (parsing)
    ├─ creates → IRISContainer (if use_testcontainers=True)
    ├─ creates → DockerContainer (if use_testcontainers=False)
    └─ verifies → ContainerPersistenceCheck

VolumeMountSpec
    └─ parsed from → ContainerConfig.volumes

ContainerPersistenceCheck
    ├─ validates → DockerContainer existence
    └─ generates → Constitutional error messages

IRISContainerManager
    ├─ creates → IRISContainer or DockerContainer
    └─ performs → ContainerPersistenceCheck
```

## Constitutional Compliance

**Principle #1: Automatic Remediation**
- ✅ Volume path validation catches issues before creation
- ✅ Persistence check detects cleanup issues immediately
- ✅ Error messages include remediation steps

**Principle #3: Isolation by Default**
- ✅ `use_testcontainers=True` maintains test isolation
- ✅ Volume mounts allow isolated workspaces

**Principle #5: Fail Fast with Guidance**
- ✅ ContainerPersistenceCheck provides What/Why/How/Docs errors
- ✅ Volume validation fails at configuration time (not runtime)

**Principle #7: Medical-Grade Reliability**
- ✅ Post-creation verification ensures containers actually persist
- ✅ Volume accessibility verification (not just configuration check)
- ✅ Structured error handling with actionable messages

## References

- Feature 010: Volume mounting implementation (iris_container_adapter.py:52-58)
- Constitutional Principle #3: Isolation by Default
- Constitutional Principle #5: Fail Fast with Guidance
- Constitutional Principle #7: Medical-Grade Reliability
- Docker SDK volumes documentation
- testcontainers-python lifecycle documentation
