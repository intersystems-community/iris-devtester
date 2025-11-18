"""
Integration test: Stale assignment cleanup (T031).

Tests that cleanup_stale() properly detects and removes stale assignments.
"""

import tempfile
from pathlib import Path

import pytest

from iris_devtester.containers.iris_container import IRISContainer
from iris_devtester.ports import PortRegistry


@pytest.fixture
def temp_registry():
    """Temporary registry for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test-registry.json"
        yield PortRegistry(registry_path=registry_path)


def test_cleanup_stale_removes_dead_containers(temp_registry):
    """
    Test that cleanup_stale() removes assignments for containers that no longer exist.

    Scenario:
    1. Start container A normally
    2. Manually create assignment for non-existent container B
    3. Run cleanup_stale()
    4. Verify container B's assignment removed (stale)
    5. Verify container A's assignment kept (still running)
    """
    # Start real container A
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )
    container_a.start()

    try:
        # Manually create stale assignment (container doesn't exist)
        assignment_b = temp_registry.assign_port("/tmp/test-project-b")
        # Update container name to simulate what IRISContainer would do
        import hashlib
        project_hash = hashlib.md5("/tmp/test-project-b".encode()).hexdigest()[:8]
        assignment_b.container_name = f"iris_{project_hash}_{assignment_b.port}"

        # Manually save the stale assignment
        data = temp_registry._read_registry()
        for i, a in enumerate(data["assignments"]):
            if a["project_path"] == "/tmp/test-project-b":
                data["assignments"][i] = assignment_b.to_dict()
        temp_registry._write_registry(data)

        # Verify 2 assignments exist
        assignments_before = temp_registry.list_all()
        assert len(assignments_before) == 2, "Should have 2 assignments before cleanup"

        # Run cleanup_stale()
        released = temp_registry.cleanup_stale()

        # Verify only stale assignment (B) was released
        assert len(released) == 1, "Should release 1 stale assignment"
        assert released[0].project_path == "/tmp/test-project-b"
        assert released[0].status == "stale"

        # Verify only active assignment (A) remains
        assignments_after = temp_registry.list_all()
        assert len(assignments_after) == 1, "Should have 1 assignment after cleanup"
        assert assignments_after[0].project_path == "/tmp/test-project-a"

    finally:
        container_a.stop()


def test_cleanup_stale_preserves_active_containers(temp_registry):
    """
    Test that cleanup_stale() doesn't remove assignments for running containers.

    Scenario:
    1. Start containers A and B
    2. Run cleanup_stale()
    3. Verify both assignments preserved (both containers still running)
    """
    # Start two real containers
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )
    container_b = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-b"
    )

    container_a.start()
    container_b.start()

    try:
        # Verify 2 assignments exist
        assignments_before = temp_registry.list_all()
        assert len(assignments_before) == 2, "Should have 2 assignments before cleanup"

        # Run cleanup_stale()
        released = temp_registry.cleanup_stale()

        # Verify no assignments released (both containers still running)
        assert len(released) == 0, "Should not release any active assignments"

        # Verify both assignments still exist
        assignments_after = temp_registry.list_all()
        assert len(assignments_after) == 2, "Should still have 2 assignments"

    finally:
        container_a.stop()
        container_b.stop()


def test_cleanup_stale_handles_stopped_containers(temp_registry):
    """
    Test that cleanup_stale() removes assignments for stopped containers.

    Scenario:
    1. Start container A
    2. Stop container A (but don't release port via normal flow)
    3. Manually re-add assignment to simulate incomplete cleanup
    4. Run cleanup_stale()
    5. Verify assignment removed (container stopped)
    """
    # Start and stop container normally first
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )
    container_a.start()
    container_name = container_a.get_container_name()
    port = container_a.get_assigned_port()
    container_a.stop()

    # Manually re-add assignment to simulate incomplete cleanup scenario
    # (e.g., container was force-killed, port release failed)
    from iris_devtester.ports.assignment import PortAssignment
    from datetime import datetime

    stale_assignment = PortAssignment(
        project_path="/tmp/test-project-a",
        port=port,
        assigned_at=datetime.now(),
        assignment_type="auto",
        status="active",
        container_name=container_name
    )

    data = temp_registry._read_registry()
    data["assignments"].append(stale_assignment.to_dict())
    temp_registry._write_registry(data)

    # Verify assignment exists
    assignments_before = temp_registry.list_all()
    assert len(assignments_before) == 1, "Should have 1 stale assignment"

    # Run cleanup_stale()
    released = temp_registry.cleanup_stale()

    # Verify stale assignment removed (container no longer exists)
    assert len(released) == 1, "Should release 1 stale assignment"
    assert released[0].project_path == "/tmp/test-project-a"

    # Verify registry is clean
    assignments_after = temp_registry.list_all()
    assert len(assignments_after) == 0, "Registry should be empty after cleanup"
