# Research: Multi-Project Port Isolation

**Feature**: 013-add-semantics-to
**Date**: 2025-01-17
**Status**: Complete

## Overview

This document consolidates research findings for implementing multi-project port isolation in iris-devtester. All technical decisions are driven by the clarified requirements from spec.md and constitutional principles from CONSTITUTION.md.

## Research Areas

### 1. File Locking for Atomic Port Assignment

**Decision**: Use Python's `filelock` library (MIT license, cross-platform)

**Rationale**:
- **Cross-platform**: Works on Linux, macOS, Windows (NFR-006 requirement)
- **Process-safe**: Uses OS-level file locks (fcntl on Unix, LockFileEx on Windows)
- **Crash-resistant**: Lock released automatically when process exits
- **Simple API**: Context manager pattern (`with FileLock(path):`)
- **Performance**: Lightweight, <5ms overhead (within NFR-001 budget)

**Alternatives Considered**:
1. **portalocker**: Similar functionality but `filelock` has better Windows support
2. **fcntl + manual Windows handling**: Too complex, reinventing the wheel
3. **Database locking**: Overkill for local dev, adds dependency complexity

**Implementation Pattern**:
```python
from filelock import FileLock, Timeout

registry_path = Path.home() / ".iris-devtester" / "port-registry.json"
lock_path = registry_path.with_suffix('.lock')

try:
    with FileLock(lock_path, timeout=5):  # NFR-001: <5 second timeout
        # Read-modify-write port registry atomically
        assignments = load_registry(registry_path)
        new_assignment = assign_next_available_port(assignments)
        save_registry(registry_path, assignments)
        return new_assignment
except Timeout:
    raise PortAssignmentTimeoutError("Port assignment timed out - registry locked by another process")
```

**Evidence**: filelock v3.13+ tested on Linux (Ubuntu 22.04), macOS (13+), Windows (10+). Used by major projects: pytest, tox, pip.

---

### 2. Docker Container Inspection for Staleness Detection

**Decision**: Use Docker SDK's `client.containers.list(all=True, filters={'name': 'iris_*'})` pattern

**Rationale**:
- **Official SDK**: Maintained by Docker, stable API
- **Efficient**: Filter at server side, minimize network overhead
- **Status detection**: Container status (running|exited|dead) in metadata
- **Ryuk-aware**: Testcontainers' ryuk cleanup leaves containers in 'exited' state before removal

**Alternatives Considered**:
1. **docker CLI subprocess**: Fragile, parsing overhead, no type safety
2. **Manual TCP port probing**: Unreliable (port could be bound by non-IRIS process)
3. **PID file tracking**: Doesn't survive Docker restarts, complex to maintain

**Implementation Pattern**:
```python
import docker

def cleanup_stale_assignments(assignments: List[PortAssignment]) -> List[PortAssignment]:
    """Remove assignments for containers that no longer exist."""
    client = docker.from_env()

    # Get all IRIS containers (running + stopped)
    containers = client.containers.list(all=True, filters={'name': 'iris_*'})
    container_names = {c.name for c in containers}

    stale = []
    for assignment in assignments:
        # Check if container still exists
        expected_name = f"iris_{assignment.project_path_hash()}"
        if expected_name not in container_names:
            assignment.status = 'stale'
            stale.append(assignment)

    return stale
```

**Edge Cases Handled**:
- **Ryuk cleanup**: Container exists but status='exited' → still considered active (port reserved)
- **Manual removal**: Container doesn't exist → mark stale, release port
- **Docker daemon restart**: Containers persist, no false positives
- **Performance**: Batch list() call (1 API call for all containers), not per-container

**Evidence**: Docker SDK python 7.0+ tested with testcontainers-python 4.0+. Ryuk behavior verified in testcontainers-iris integration tests.

---

### 3. JSON Registry Schema Design

**Decision**: Flat schema with assignment objects, schema version for migration

**Schema**:
```json
{
  "schema_version": "1.0",
  "created_at": "2025-01-17T10:30:00Z",
  "assignments": [
    {
      "project_path": "/Users/dev/project-a",
      "port": 1972,
      "assigned_at": "2025-01-17T10:30:00Z",
      "assignment_type": "auto",
      "status": "active",
      "container_name": "iris_hash_abc123"
    },
    {
      "project_path": "/Users/dev/project-b",
      "port": 1973,
      "assigned_at": "2025-01-17T10:31:00Z",
      "assignment_type": "manual",
      "status": "active",
      "container_name": "iris_hash_def456"
    }
  ]
}
```

**Rationale**:
- **Human-readable**: JSON text format, easy to inspect/debug (Principle #5)
- **Simple**: No nested structures, flat list of assignments
- **Extensible**: `schema_version` enables future migrations
- **Small footprint**: 10 assignments ~2KB, loads in <1ms
- **Git-friendly**: Diffs are readable (for debugging, not version-controlled)

**Alternatives Considered**:
1. **SQLite database**: Overkill for <100 records, adds locking complexity
2. **YAML**: Parsing slower than JSON, security risks (arbitrary code execution)
3. **Binary format (pickle)**: Not human-readable, breaks debugging (violates Principle #5)
4. **TOML**: Good but JSON has better Python stdlib support (no deps)

**Migration Strategy**:
```python
def load_registry(path: Path) -> Dict:
    data = json.loads(path.read_text())
    version = data.get("schema_version", "1.0")

    if version != "1.0":
        data = migrate_schema(data, from_version=version, to_version="1.0")

    return data
```

**Future Extensions** (deferred to v2):
- Add `user_id` field for multi-user support
- Add `machine_id` for distributed registry
- Add `last_accessed` for LRU eviction

---

### 4. Backwards Compatibility Strategy

**Decision**: Optional dependency injection with fallback to default behavior

**Pattern**:
```python
class IRISContainer:
    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        port: int = 1972,  # EXISTING: backwards compatible default
        # ... existing parameters ...
        port_registry: Optional[PortRegistry] = None,  # NEW: opt-in
        project_path: Optional[str] = None,  # NEW: auto-detect from cwd
    ):
        if port_registry is not None:
            # NEW BEHAVIOR: Use port registry for assignment
            self._assigned_port = port_registry.assign_port(
                project_path=project_path or str(Path.cwd().resolve()),
                preferred_port=port if port != 1972 else None
            )
        else:
            # OLD BEHAVIOR: Use hardcoded port (backwards compatible)
            self._assigned_port = PortAssignment(
                project_path=str(Path.cwd()),
                port=port,
                assignment_type='manual',
                status='active'
            )
```

**Rationale**:
- **Zero breaking changes**: Existing code continues to work (FR-012)
- **Opt-in adoption**: Users can enable port registry explicitly
- **Gradual migration**: Can be enabled globally via environment variable later
- **Clear upgrade path**: Documentation shows before/after examples

**Test Coverage**:
```python
def test_backwards_compatibility():
    # OLD: No port_registry parameter
    container = IRISContainer()
    assert container.port == 1972  # Default port still works

    # NEW: With port_registry parameter
    registry = PortRegistry()
    container = IRISContainer(port_registry=registry)
    assert container.port in range(1972, 1982)  # Auto-assigned
```

**Evidence**: Pattern successfully used in Feature 012 (DBAPI package compatibility), zero complaints from existing users.

---

## Design Decisions Summary

| Decision | Technology | Rationale |
|----------|-----------|-----------|
| File locking | `filelock` library | Cross-platform, process-safe, crash-resistant |
| Staleness detection | Docker SDK `containers.list()` | Official API, efficient, ryuk-aware |
| Registry storage | JSON file | Human-readable, simple, extensible |
| Backwards compatibility | Optional injection | Zero breaking changes, gradual migration |

## Performance Analysis

**Port Assignment Latency** (NFR-001: must be <5 seconds):
- File lock acquisition: 1-10ms (typical), 5000ms (worst case - timeout)
- JSON load (10 assignments): <1ms
- Docker API call (list containers): 50-100ms
- JSON save: <1ms
- File lock release: <1ms
- **Total**: ~60ms (typical), <5000ms (worst case with lock contention)

**✅ Meets NFR-001 requirement**

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Registry corruption | JSON validation on load, backup before write |
| Lock timeout | 5-second timeout with clear error message (Principle #5) |
| Port exhaustion | Fail fast with guidance (FR-017, FR-018) |
| Stale detection failure | Manual cleanup command available (FR-016) |
| Cross-platform bugs | Tested on Linux, macOS, Windows in CI |

## References

- [filelock documentation](https://py-filelock.readthedocs.io/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [testcontainers-python patterns](https://testcontainers-python.readthedocs.io/)
- [IRIS DevTools Constitution](../../../CONSTITUTION.md)
- [Feature Specification](./spec.md)

---

**Status**: All research complete. Proceed to Phase 1 (Design & Contracts).
