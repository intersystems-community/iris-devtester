# API Contract: PortRegistry

**Module**: `iris_devtester.ports.registry`
**Status**: Contract (TDD - implementation pending)

## Class: PortRegistry

```python
class PortRegistry:
    """
    Manages port assignments for multiple IRIS projects with atomic file-based persistence.

    Thread-safe via file locking. Race-condition safe for concurrent container starts.
    """

    def __init__(
        self,
        registry_path: Optional[Path] = None,  # Default: ~/.iris-devtester/port-registry.json
        port_range: tuple[int, int] = (1972, 1981),  # Default IRIS port range
    ):
        """Initialize port registry with optional custom path and port range."""

    def assign_port(
        self,
        project_path: str,
        preferred_port: Optional[int] = None
    ) -> PortAssignment:
        """
        Assign port to project (idempotent - returns existing if already assigned).

        Args:
            project_path: Absolute path to project directory
            preferred_port: Optional manual port override

        Returns:
            PortAssignment with assigned port

        Raises:
            PortExhaustedError: All ports in range are in use
            PortConflictError: preferred_port already assigned to different project
            PortAssignmentTimeoutError: File lock timeout (>5 seconds)
        """

    def release_port(self, project_path: str) -> None:
        """
        Release port assignment for project.

        Args:
            project_path: Absolute path to project directory

        Raises:
            KeyError: No assignment exists for project_path
        """

    def cleanup_stale(self) -> List[PortAssignment]:
        """
        Remove stale assignments (containers no longer exist).

        Returns:
            List of released assignments

        Requires:
            Docker daemon accessible
        """

    def get_assignment(self, project_path: str) -> Optional[PortAssignment]:
        """Query assignment by project path."""

    def list_all(self) -> List[PortAssignment]:
        """List all active and stale assignments."""

    def clear_all(self) -> None:
        """Remove all assignments (testing/debugging only)."""
```

## Contract Tests

Location: `tests/contract/test_port_registry_contract.py`

```python
def test_assign_port_returns_port_in_range():
    registry = PortRegistry()
    assignment = registry.assign_port("/tmp/project-a")
    assert 1972 <= assignment.port <= 1981

def test_assign_port_idempotent():
    registry = PortRegistry()
    assignment1 = registry.assign_port("/tmp/project-a")
    assignment2 = registry.assign_port("/tmp/project-a")
    assert assignment1.port == assignment2.port

def test_assign_port_with_preferred_port():
    registry = PortRegistry()
    assignment = registry.assign_port("/tmp/project-a", preferred_port=1975)
    assert assignment.port == 1975
    assert assignment.assignment_type == "manual"

def test_assign_port_raises_conflict_for_used_preferred_port():
    registry = PortRegistry()
    registry.assign_port("/tmp/project-a", preferred_port=1975)

    with pytest.raises(PortConflictError):
        registry.assign_port("/tmp/project-b", preferred_port=1975)

def test_assign_port_raises_exhausted_when_all_ports_used():
    registry = PortRegistry(port_range=(1972, 1973))  # Only 2 ports
    registry.assign_port("/tmp/project-a")
    registry.assign_port("/tmp/project-b")

    with pytest.raises(PortExhaustedError):
        registry.assign_port("/tmp/project-c")

def test_release_port_removes_assignment():
    registry = PortRegistry()
    registry.assign_port("/tmp/project-a")
    registry.release_port("/tmp/project-a")

    assert registry.get_assignment("/tmp/project-a") is None

def test_concurrent_assign_from_two_projects_unique_ports():
    # Test race condition handling
    registry = PortRegistry()

    import threading
    results = {}

    def assign(project_path):
        results[project_path] = registry.assign_port(project_path)

    t1 = threading.Thread(target=assign, args=("/tmp/project-a",))
    t2 = threading.Thread(target=assign, args=("/tmp/project-b",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["/tmp/project-a"].port != results["/tmp/project-b"].port
```

## References

- [Data Model](../data-model.md) - PortAssignment, PortRegistry entities
- [Research](../research.md) - File locking patterns
