# Data Model: Multi-Project Port Isolation

**Feature**: 013-add-semantics-to
**Date**: 2025-01-17

## Overview

This document defines the data entities for multi-project port isolation. Entities are extracted from the feature specification (spec.md lines 159-172) and refined based on research findings.

## Entities

### PortAssignment

Represents a port-to-project mapping with lifecycle metadata.

**Fields**:
- `project_path` (str): Absolute path to project directory (e.g., `/Users/dev/project-a`)
- `port` (int): Assigned IRIS superserver port (1972-1981 for auto, or user-specified)
- `assigned_at` (datetime): ISO 8601 timestamp of assignment creation
- `assignment_type` (Literal["auto", "manual"]): How port was assigned
- `status` (Literal["active", "released", "stale"]): Current assignment status
- `container_name` (Optional[str]): Docker container name for staleness tracking

**Validation Rules**:
- `project_path` MUST be absolute path (starts with `/` on Unix, drive letter on Windows)
- `port` MUST be in range 1-65535 (auto-assignment uses 1972-1981)
- `assigned_at` MUST be valid ISO 8601 timestamp
- `assignment_type` MUST be "auto" or "manual"
- `status` MUST be "active", "released", or "stale"

**State Transitions**:
```
active → released  (when container stops normally via IRISContainer.stop())
active → stale     (when container crashes or removed manually)
released → (removed from registry)
stale → (removed by cleanup_stale())
```

**Python Representation**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

@dataclass
class PortAssignment:
    project_path: str
    port: int
    assigned_at: datetime
    assignment_type: Literal["auto", "manual"]
    status: Literal["active", "released", "stale"]
    container_name: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "project_path": self.project_path,
            "port": self.port,
            "assigned_at": self.assigned_at.isoformat(),
            "assignment_type": self.assignment_type,
            "status": self.status,
            "container_name": self.container_name
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortAssignment":
        """Deserialize from JSON dict."""
        return cls(
            project_path=data["project_path"],
            port=data["port"],
            assigned_at=datetime.fromisoformat(data["assigned_at"]),
            assignment_type=data["assignment_type"],
            status=data["status"],
            container_name=data.get("container_name")
        )
```

---

### PortRegistry

Manages the collection of port assignments with atomic file-based persistence.

**Fields**:
- `registry_file_path` (Path): Location of JSON registry file (default: `~/.iris-devtester/port-registry.json`)
- `assignments` (List[PortAssignment]): Current active/stale port assignments

**Operations**:
- `assign_port(project_path, preferred_port=None) → PortAssignment`: Assign port to project
- `release_port(project_path) → None`: Release port assignment
- `cleanup_stale() → List[PortAssignment]`: Remove stale assignments, return released ports
- `get_assignment(project_path) → Optional[PortAssignment]`: Query assignment by project
- `list_all() → List[PortAssignment]`: List all assignments
- `clear_all() → None`: Remove all assignments (testing/debugging only)

**Concurrency Control**:
- File locking via `filelock` library
- Atomic read-modify-write operations
- 5-second timeout (NFR-001 budget)

**Persistence Format** (JSON):
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
      "container_name": "iris_abc123"
    }
  ]
}
```

**Error Handling**:
- `PortExhaustedError`: All 10 ports (1972-1981) in use
- `PortConflictError`: Requested port already assigned
- `PortAssignmentTimeoutError`: File lock timeout exceeded

---

### Project (Conceptual Entity)

Not stored directly, derived from runtime context.

**Identifier**: Absolute directory path (e.g., `/Users/dev/project-a`)

**Derivation**:
1. Explicit parameter: `project_path="/path/to/project"`
2. Auto-detection: `Path.cwd().resolve()` (current working directory)
3. Environment variable: `IRIS_PROJECT_PATH` (optional override)

**Normalization**:
- Convert to absolute path: `Path(project_path).resolve()`
- Normalize separators: Use `os.path.normpath()` for cross-platform consistency
- Case sensitivity: Preserve OS-specific behavior (case-insensitive on Windows/macOS, sensitive on Linux)

---

## Relationships

```
Project (1) ─── has ───> (0..1) PortAssignment
PortAssignment (1) ─── references ───> (0..1) Docker Container
PortRegistry (1) ─── contains ───> (0..10) PortAssignment
```

**Cardinality Rules**:
- Each Project has at most ONE active PortAssignment
- Each PortAssignment references at most ONE Docker Container
- PortRegistry contains at most 10 active auto-assigned PortAssignments (range 1972-1981)

---

## Invariants

1. **Uniqueness**: No two active assignments can have the same port
2. **Bounds**: Auto-assigned ports MUST be in range 1972-1981
3. **Staleness**: Assignments for non-existent containers MUST be marked stale
4. **Atomicity**: Registry modifications MUST be atomic (file locking)
5. **Idempotency**: `assign_port()` for same project returns existing assignment if active

---

## Schema Migration Strategy

**Version 1.0** (current):
- Fields: project_path, port, assigned_at, assignment_type, status, container_name

**Future Extensions** (v2.0, out of scope for Feature 013):
- Add `user_id` field for multi-user support
- Add `machine_id` field for distributed registry
- Add `last_accessed` timestamp for LRU eviction

**Migration Function**:
```python
def migrate_schema(data: dict, from_version: str, to_version: str) -> dict:
    if from_version == "1.0" and to_version == "1.0":
        return data  # No migration needed

    # Future: Handle version transitions
    # if from_version == "1.0" and to_version == "2.0":
    #     data["assignments"] = [
    #         {**a, "user_id": os.getuid(), "machine_id": get_machine_id()}
    #         for a in data["assignments"]
    #     ]

    return data
```

---

## References

- [Feature Specification](./spec.md) - Lines 159-172 (Key Entities)
- [Research Document](./research.md) - JSON schema design, filelock patterns
- [IRIS DevTools Constitution](../../../CONSTITUTION.md) - Principle #7 (Medical-Grade Reliability)
