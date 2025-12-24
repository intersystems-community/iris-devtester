# Quickstart: Multi-Project Port Isolation

**Feature**: 013-add-semantics-to
**Status**: Test scenario (executable after implementation)

## Overview

This quickstart demonstrates multi-project port isolation with two concurrent IRIS containers. This scenario validates Acceptance Scenario #1 and #3 from spec.md.

## Scenario

**Given**: Two separate projects (Project A and Project B) on the same machine
**When**: Developer starts IRIS containers for both projects simultaneously
**Then**: Each project gets a unique port, both containers run without conflicts

## Prerequisites

- iris-devtester installed with Feature 013 implementation
- Docker running
- No existing IRIS containers using ports 1972-1973

## Executable Test

```python
#!/usr/bin/env python3
"""
Quickstart: Multi-Project Port Isolation

This script demonstrates automatic port assignment for multiple projects.
Run this after implementing Feature 013.
"""

import os
import tempfile
from pathlib import Path
from testcontainers.iris import IRISContainer
from iris_devtester.ports import PortRegistry

def main():
    print("=== Multi-Project Port Isolation Quickstart ===\n")

    # Create port registry (shared across projects)
    registry = PortRegistry()
    print(f"Port registry: {registry.registry_file_path}")
    print(f"Initial assignments: {len(registry.list_all())}\n")

    # Simulate two separate project directories
    with tempfile.TemporaryDirectory(prefix="project_a_") as project_a_path:
        with tempfile.TemporaryDirectory(prefix="project_b_") as project_b_path:

            print(f"Project A path: {project_a_path}")
            print(f"Project B path: {project_b_path}\n")

            # Start Project A container
            print("Starting Project A container...")
            container_a = IRISContainer(
                port_registry=registry,
                project_path=project_a_path
            )
            container_a.start()

            assignment_a = registry.get_assignment(project_a_path)
            print(f"✓ Project A assigned port: {assignment_a.port}")
            print(f"  Assignment type: {assignment_a.assignment_type}")
            print(f"  Status: {assignment_a.status}\n")

            # Start Project B container
            print("Starting Project B container...")
            container_b = IRISContainer(
                port_registry=registry,
                project_path=project_b_path
            )
            container_b.start()

            assignment_b = registry.get_assignment(project_b_path)
            print(f"✓ Project B assigned port: {assignment_b.port}")
            print(f"  Assignment type: {assignment_b.assignment_type}")
            print(f"  Status: {assignment_b.status}\n")

            # Verify isolation
            print("Verification:")
            assert assignment_a.port != assignment_b.port, "Ports must be unique!"
            print(f"✓ Ports are unique: {assignment_a.port} != {assignment_b.port}")

            assert assignment_a.port in range(1972, 1982), "Port A out of range"
            assert assignment_b.port in range(1972, 1982), "Port B out of range"
            print(f"✓ Ports in valid range (1972-1981)")

            # Test concurrent access
            print("\nTesting concurrent container access...")
            conn_a = container_a.get_connection()
            conn_b = container_b.get_connection()

            cursor_a = conn_a.cursor()
            cursor_a.execute("SELECT 'Project A' as project")
            result_a = cursor_a.fetchone()
            cursor_a.close()
            print(f"✓ Project A query successful: {result_a}")

            cursor_b = conn_b.cursor()
            cursor_b.execute("SELECT 'Project B' as project")
            result_b = cursor_b.fetchone()
            cursor_b.close()
            print(f"✓ Project B query successful: {result_b}")

            # Cleanup
            print("\nCleaning up...")
            container_a.stop()
            print(f"✓ Project A container stopped")

            container_b.stop()
            print(f"✓ Project B container stopped")

            # Verify port release
            registry.cleanup_stale()
            remaining = len([a for a in registry.list_all() if a.status == "active"])
            print(f"✓ Active assignments after cleanup: {remaining}")

    print("\n=== Quickstart Complete! ===")
    print("Multi-project port isolation working correctly.")

if __name__ == "__main__":
    main()
```

## Expected Output

```
=== Multi-Project Port Isolation Quickstart ===

Port registry: /Users/dev/.iris-devtester/port-registry.json
Initial assignments: 0

Project A path: /tmp/project_a_abc123
Project B path: /tmp/project_b_def456

Starting Project A container...
✓ Project A assigned port: 1972
  Assignment type: auto
  Status: active

Starting Project B container...
✓ Project B assigned port: 1973
  Assignment type: auto
  Status: active

Verification:
✓ Ports are unique: 1972 != 1973
✓ Ports in valid range (1972-1981)

Testing concurrent container access...
✓ Project A query successful: ('Project A',)
✓ Project B query successful: ('Project B',)

Cleaning up...
✓ Project A container stopped
✓ Project B container stopped
✓ Active assignments after cleanup: 0

=== Quickstart Complete! ===
Multi-project port isolation working correctly.
```

## Manual Testing

```bash
# Step 1: Check current port assignments
iris-devtester ports list

# Step 2: Start first project
cd /Users/dev/project-a
python -m pytest  # Uses port 1972

# Step 3: In another terminal, start second project
cd /Users/dev/project-b
python -m pytest  # Uses port 1973 (auto-assigned)

# Step 4: Verify both running
iris-devtester ports list
# Expected output:
# /Users/dev/project-a → 1972 (auto, active)
# /Users/dev/project-b → 1973 (auto, active)

# Step 5: Stop first project
cd /Users/dev/project-a
# Containers auto-cleanup when tests complete

# Step 6: Restart first project (persistence test)
cd /Users/dev/project-a
python -m pytest  # Should reuse port 1972

# Step 7: Clean up all assignments
iris-devtester ports clear
```

## Success Criteria

- ✓ Project A gets port 1972 (first available)
- ✓ Project B gets port 1973 (second available)
- ✓ Both containers run simultaneously without conflicts
- ✓ Both can execute SQL queries independently
- ✓ Port assignments persist across container restarts
- ✓ Cleanup releases ports for reuse

## References

- [Feature Specification](./spec.md) - Acceptance Scenarios
- [Data Model](./data-model.md) - PortRegistry, PortAssignment
- [Research](./research.md) - Implementation patterns
