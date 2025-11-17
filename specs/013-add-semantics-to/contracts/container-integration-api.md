# API Contract: IRISContainer Integration

**Module**: `testcontainers.iris` (extends testcontainers-iris package)
**Status**: Contract (TDD - implementation pending)

## Class: IRISContainer (Modified)

```python
class IRISContainer:
    """
    IRIS database container with automatic port management and multi-project isolation.

    Extends testcontainers-iris with optional PortRegistry integration for automatic
    port assignment based on project directory. Fully backwards compatible.
    """

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        port: int = 1972,  # EXISTING: backwards compatible default
        username: str = "_SYSTEM",
        password: str = "SYS",
        namespace: str = "USER",
        # ... existing parameters ...
        port_registry: Optional[PortRegistry] = None,  # NEW: opt-in port management
        project_path: Optional[str] = None,  # NEW: auto-detect from cwd if None
    ):
        """
        Initialize IRIS container with optional port registry integration.

        Args:
            image: IRIS Docker image (community or enterprise)
            port: Port number (default 1972). Ignored if port_registry provided.
            username: IRIS username
            password: IRIS password
            namespace: IRIS namespace
            port_registry: Optional PortRegistry for multi-project isolation.
                          If None, uses default port 1972 (backwards compatible).
            project_path: Absolute path to project directory. Auto-detects from
                         os.getcwd() if None and port_registry is provided.

        Behavior:
            - If port_registry is None: Use hardcoded port (backwards compatible)
            - If port_registry provided: Auto-assign port from registry
            - If port != 1972 and port_registry provided: Use port as preferred_port
        """

    def get_assigned_port(self) -> int:
        """
        Get the assigned IRIS superserver port.

        Returns:
            Port number (1972-1981 for auto-assigned, or user-specified)
        """

    def get_project_path(self) -> Optional[str]:
        """
        Get the project path for this container.

        Returns:
            Absolute path to project directory, or None if not using port registry
        """

    def start(self) -> "IRISContainer":
        """
        Start IRIS container and register port assignment.

        Raises:
            PortExhaustedError: All ports in range are in use
            PortConflictError: Requested port already assigned to different project
            PortAssignmentTimeoutError: Port assignment timed out
        """

    def stop(self) -> None:
        """
        Stop container and release port assignment.

        Behavior:
            - Stop Docker container
            - If using port_registry: release_port(project_path)
        """
```

## Integration Patterns

### Pattern 1: Backwards Compatible (No Port Registry)

```python
# OLD CODE - continues to work without changes
container = IRISContainer()
container.start()

assert container.get_assigned_port() == 1972  # Default port
```

### Pattern 2: Auto-Assignment with Port Registry

```python
# NEW CODE - automatic port assignment
from iris_devtester.ports import PortRegistry

registry = PortRegistry()
container = IRISContainer(
    port_registry=registry,
    project_path="/Users/dev/project-a"
)
container.start()

# Port automatically assigned from range 1972-1981
assigned_port = container.get_assigned_port()
assert 1972 <= assigned_port <= 1981
```

### Pattern 3: Auto-Detection of Project Path

```python
# Project path auto-detected from os.getcwd()
import os
os.chdir("/Users/dev/project-a")

registry = PortRegistry()
container = IRISContainer(port_registry=registry)  # project_path auto-detected
container.start()

assert container.get_project_path() == "/Users/dev/project-a"
```

### Pattern 4: Manual Port Preference

```python
# Request specific port (manual override)
registry = PortRegistry()
container = IRISContainer(
    port_registry=registry,
    project_path="/Users/dev/project-a",
    port=1975  # Preferred port
)
container.start()

assert container.get_assigned_port() == 1975
```

## Contract Tests

Location: `tests/contract/test_container_integration_contract.py`

```python
def test_backwards_compatibility_no_port_registry():
    """OLD: Container without port_registry uses default port."""
    container = IRISContainer()
    container.start()

    assert container.get_assigned_port() == 1972
    assert container.get_project_path() is None

    container.stop()

def test_auto_assignment_with_port_registry():
    """NEW: Container with port_registry auto-assigns port."""
    registry = PortRegistry()
    container = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a"
    )
    container.start()

    port = container.get_assigned_port()
    assert 1972 <= port <= 1981

    # Verify registry has assignment
    assignment = registry.get_assignment("/tmp/project-a")
    assert assignment is not None
    assert assignment.port == port

    container.stop()

def test_auto_detect_project_path_from_cwd():
    """Project path auto-detected from os.getcwd()."""
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            registry = PortRegistry()
            container = IRISContainer(port_registry=registry)

            assert container.get_project_path() == os.path.abspath(tmpdir)

        finally:
            os.chdir(old_cwd)

def test_manual_port_preference_with_registry():
    """Manual port override via port parameter."""
    registry = PortRegistry()
    container = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a",
        port=1975  # Preferred port
    )
    container.start()

    assert container.get_assigned_port() == 1975

    assignment = registry.get_assignment("/tmp/project-a")
    assert assignment.assignment_type == "manual"
    assert assignment.port == 1975

    container.stop()

def test_port_conflict_raises_error():
    """Port conflict raises PortConflictError."""
    registry = PortRegistry()

    # Project A gets port 1975
    container_a = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a",
        port=1975
    )
    container_a.start()

    # Project B tries to use same port
    container_b = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-b",
        port=1975
    )

    with pytest.raises(PortConflictError):
        container_b.start()

    container_a.stop()

def test_stop_releases_port_assignment():
    """Container.stop() releases port assignment."""
    registry = PortRegistry()
    container = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a"
    )
    container.start()

    assignment = registry.get_assignment("/tmp/project-a")
    assert assignment is not None

    container.stop()

    # Port released
    assignment = registry.get_assignment("/tmp/project-a")
    assert assignment is None

def test_multiple_containers_unique_ports():
    """Multiple containers get unique ports."""
    registry = PortRegistry()

    containers = []
    for i in range(3):
        container = IRISContainer(
            port_registry=registry,
            project_path=f"/tmp/project-{i}"
        )
        container.start()
        containers.append(container)

    # Verify unique ports
    ports = [c.get_assigned_port() for c in containers]
    assert len(ports) == len(set(ports)), "Ports must be unique"

    # Cleanup
    for container in containers:
        container.stop()

def test_port_exhaustion_raises_error():
    """Port exhaustion raises PortExhaustedError."""
    registry = PortRegistry(port_range=(1972, 1973))  # Only 2 ports

    container_a = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a"
    )
    container_a.start()

    container_b = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-b"
    )
    container_b.start()

    # Third container should fail
    container_c = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-c"
    )

    with pytest.raises(PortExhaustedError):
        container_c.start()

    container_a.stop()
    container_b.stop()

def test_idempotent_start_for_same_project():
    """Starting same project twice returns same port (idempotent)."""
    registry = PortRegistry()

    container_1 = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a"
    )
    container_1.start()
    port_1 = container_1.get_assigned_port()

    # Same project, new container instance
    container_2 = IRISContainer(
        port_registry=registry,
        project_path="/tmp/project-a"
    )
    container_2.start()
    port_2 = container_2.get_assigned_port()

    assert port_1 == port_2, "Same project should get same port (idempotent)"

    container_1.stop()
    container_2.stop()
```

## Error Handling

### PortExhaustedError

**When**: All 10 ports (1972-1981) are in use

**Error Message Format**:
```
PortExhaustedError: All IRIS ports (1972-1981) are in use

Current port assignments:
  /Users/dev/project-a → 1972 (auto, active)
  /Users/dev/project-b → 1973 (auto, active)
  ...

How to fix:
  1. Stop unused containers: iris-devtester ports list
  2. Clean up stale assignments: iris-devtester ports clear
  3. Use manual port override: IRISContainer(port=2000, port_registry=registry)

Documentation: https://iris-devtester.readthedocs.io/ports/exhaustion/
```

### PortConflictError

**When**: Requested port already assigned to different project

**Error Message Format**:
```
PortConflictError: Port 1975 already assigned to /Users/dev/project-a

Requested: /Users/dev/project-b → 1975
Existing: /Users/dev/project-a → 1975 (manual, active)

How to fix:
  1. Use auto-assignment (omit port parameter)
  2. Choose different port: IRISContainer(port=1976, ...)
  3. Stop conflicting container: iris-devtester ports list

Documentation: https://iris-devtester.readthedocs.io/ports/conflicts/
```

### PortAssignmentTimeoutError

**When**: File lock timeout (>5 seconds)

**Error Message Format**:
```
PortAssignmentTimeoutError: Port assignment timed out after 5 seconds

Registry locked by another process:
  Registry: ~/.iris-devtester/port-registry.json
  Lock file: ~/.iris-devtester/port-registry.lock

How to fix:
  1. Wait for other process to complete
  2. Check for stale lock file (kill orphaned processes)
  3. Remove lock file manually (last resort): rm ~/.iris-devtester/port-registry.lock

Documentation: https://iris-devtester.readthedocs.io/ports/timeouts/
```

## References

- [Data Model](../data-model.md) - PortAssignment, PortRegistry entities
- [Port Registry API](./port-registry-api.md) - PortRegistry class contract
- [Research](../research.md) - Backwards compatibility patterns
