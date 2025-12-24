"""
Contract tests for PortRegistry API.

These tests define the expected behavior of the PortRegistry class.
Following TDD workflow: tests written BEFORE implementation.

Expected Status: FAIL (PortRegistry raises NotImplementedError)
"""

import tempfile
import threading
from pathlib import Path

import pytest

from iris_devtester.ports import (
    PortAssignment,
    PortAssignmentTimeoutError,
    PortConflictError,
    PortExhaustedError,
    PortRegistry,
)


@pytest.fixture
def temp_registry():
    """Temporary registry for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test-registry.json"
        yield PortRegistry(registry_path=registry_path)


@pytest.fixture
def temp_registry_small_range():
    """Temporary registry with limited port range."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test-registry.json"
        yield PortRegistry(registry_path=registry_path, port_range=(1972, 1973))


def test_assign_port_returns_port_in_range(temp_registry):
    """
    T004: assign_port() returns port in range 1972-1981.

    Contract: Auto-assigned ports must be within configured range.
    """
    assignment = temp_registry.assign_port("/tmp/project-a")

    assert isinstance(assignment, PortAssignment)
    assert 1972 <= assignment.port <= 1981
    assert assignment.project_path == "/tmp/project-a"
    assert assignment.assignment_type == "auto"
    assert assignment.status == "active"


def test_assign_port_idempotent(temp_registry):
    """
    T005: assign_port() is idempotent - same project gets same port.

    Contract: Multiple calls with same project_path return same assignment.
    """
    assignment1 = temp_registry.assign_port("/tmp/project-a")
    assignment2 = temp_registry.assign_port("/tmp/project-a")

    assert assignment1.port == assignment2.port
    assert assignment1.project_path == assignment2.project_path
    assert assignment1.assigned_at == assignment2.assigned_at  # Same timestamp


def test_assign_port_with_preferred_port(temp_registry):
    """
    T006a: assign_port() respects preferred_port parameter.

    Contract: Manual port specification overrides auto-assignment.
    """
    assignment = temp_registry.assign_port("/tmp/project-a", preferred_port=1975)

    assert assignment.port == 1975
    assert assignment.assignment_type == "manual"
    assert assignment.status == "active"


def test_assign_port_raises_conflict_for_used_preferred_port(temp_registry):
    """
    T006b: assign_port() raises PortConflictError for already-used preferred_port.

    Contract: Port conflict detection prevents double-assignment.
    """
    # Project A gets port 1975
    temp_registry.assign_port("/tmp/project-a", preferred_port=1975)

    # Project B tries same port - should fail
    with pytest.raises(PortConflictError) as exc_info:
        temp_registry.assign_port("/tmp/project-b", preferred_port=1975)

    error = exc_info.value
    assert "1975" in str(error)
    assert "/tmp/project-a" in str(error)


def test_assign_port_raises_exhausted_when_all_ports_used(temp_registry_small_range):
    """
    T007: assign_port() raises PortExhaustedError when all ports in range are used.

    Contract: Port exhaustion is detected and reported with guidance.
    """
    # Fill both ports (1972, 1973)
    temp_registry_small_range.assign_port("/tmp/project-a")
    temp_registry_small_range.assign_port("/tmp/project-b")

    # Third project should fail
    with pytest.raises(PortExhaustedError) as exc_info:
        temp_registry_small_range.assign_port("/tmp/project-c")

    error = exc_info.value
    assert "1972-1973" in str(error)
    assert "How to fix" in str(error)  # Guidance present


def test_release_port_removes_assignment(temp_registry):
    """
    T008: release_port() removes assignment from registry.

    Contract: Released ports become available for reassignment.
    """
    # Assign port
    assignment = temp_registry.assign_port("/tmp/project-a")
    port = assignment.port

    # Verify assigned
    assert temp_registry.get_assignment("/tmp/project-a") is not None

    # Release
    temp_registry.release_port("/tmp/project-a")

    # Verify released
    assert temp_registry.get_assignment("/tmp/project-a") is None


def test_concurrent_assign_from_two_projects_unique_ports(temp_registry):
    """
    T009: Concurrent assign_port() from 2 projects returns different ports.

    Contract: File locking prevents race conditions during concurrent assignment.
    """
    results = {}

    def assign(project_path):
        results[project_path] = temp_registry.assign_port(project_path)

    # Start two threads assigning ports simultaneously
    t1 = threading.Thread(target=assign, args=("/tmp/project-a",))
    t2 = threading.Thread(target=assign, args=("/tmp/project-b",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify unique ports assigned
    port_a = results["/tmp/project-a"].port
    port_b = results["/tmp/project-b"].port

    assert port_a != port_b, "Concurrent assignments must get unique ports"


def test_cleanup_stale_detects_manually_removed_container(temp_registry):
    """
    T009.5a: cleanup_stale() detects manually removed containers.

    Contract: Stale assignments (container removed via docker rm) are detected and cleaned.

    Note: This test requires Docker daemon. Skipped if unavailable.
    """
    pytest.skip(
        "Requires Docker integration - will be implemented in integration test phase (T031)"
    )


def test_cleanup_stale_preserves_ryuk_exited_containers(temp_registry):
    """
    T009.5b: cleanup_stale() preserves testcontainers ryuk 'exited' containers.

    Contract: Containers stopped via IRISContainer.stop() (status='exited') are NOT
    marked stale, as testcontainers ryuk will clean them up.

    Note: This test requires Docker integration. Skipped if unavailable.
    """
    pytest.skip(
        "Requires Docker integration - will be implemented in integration test phase (T031)"
    )


def test_cleanup_stale_docker_daemon_restart(temp_registry):
    """
    T009.5c: cleanup_stale() handles Docker daemon restart gracefully.

    Contract: If Docker daemon restarts, containers may persist. cleanup_stale()
    should not mark them as stale unless truly missing.

    Note: This test requires Docker daemon control. Skipped if unavailable.
    """
    pytest.skip(
        "Requires Docker daemon control - will be implemented in integration test phase (T031)"
    )


def test_get_assignment_returns_none_if_not_exists(temp_registry):
    """
    Contract: get_assignment() returns None if no assignment exists for project.
    """
    assignment = temp_registry.get_assignment("/tmp/nonexistent-project")
    assert assignment is None


def test_list_all_returns_all_assignments(temp_registry):
    """
    Contract: list_all() returns all active and stale assignments.
    """
    # Assign to 3 projects
    temp_registry.assign_port("/tmp/project-a")
    temp_registry.assign_port("/tmp/project-b")
    temp_registry.assign_port("/tmp/project-c")

    all_assignments = temp_registry.list_all()

    assert len(all_assignments) == 3
    project_paths = {a.project_path for a in all_assignments}
    assert project_paths == {"/tmp/project-a", "/tmp/project-b", "/tmp/project-c"}


def test_clear_all_removes_all_assignments(temp_registry):
    """
    Contract: clear_all() removes all assignments from registry.
    """
    # Assign to 2 projects
    temp_registry.assign_port("/tmp/project-a")
    temp_registry.assign_port("/tmp/project-b")

    # Verify assignments exist
    assert len(temp_registry.list_all()) == 2

    # Clear all
    temp_registry.clear_all()

    # Verify empty
    assert len(temp_registry.list_all()) == 0
