"""
Integration test: Manual port override (T032).

Tests that users can manually specify preferred ports.
"""

import tempfile
from pathlib import Path

import pytest

from iris_devtester.containers.iris_container import IRISContainer
from iris_devtester.ports import PortRegistry, PortConflictError


@pytest.fixture
def temp_registry():
    """Temporary registry for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test-registry.json"
        yield PortRegistry(registry_path=registry_path)


def test_manual_port_preference(temp_registry):
    """
    Test that preferred_port parameter allows manual port selection.

    Scenario:
    1. Start container A with preferred_port=1975
    2. Verify port 1975 assigned
    3. Start container B without preference
    4. Verify container B gets different port (not 1975)
    """
    # Container A with manual port preference
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a",
        preferred_port=1975
    )
    container_a.start()

    try:
        port_a = container_a.get_assigned_port()
        assert port_a == 1975, "Should get preferred port 1975"

        # Container B without preference (auto-assign)
        container_b = IRISContainer(
            port_registry=temp_registry,
            project_path="/tmp/test-project-b"
        )
        container_b.start()

        try:
            port_b = container_b.get_assigned_port()
            assert port_b != 1975, "Container B should get different port"
            assert 1972 <= port_b <= 1981, f"Port {port_b} should be in range"

        finally:
            container_b.stop()

    finally:
        container_a.stop()


def test_manual_port_conflict_detection(temp_registry):
    """
    Test that PortConflictError is raised when preferred port already in use.

    Scenario:
    1. Start container A on port 1975
    2. Try to start container B with preferred_port=1975
    3. Verify PortConflictError raised
    4. Verify error message includes conflict details
    """
    # Container A gets port 1975
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a",
        preferred_port=1975
    )
    container_a.start()

    try:
        # Container B tries to get same port - should fail
        container_b = IRISContainer(
            port_registry=temp_registry,
            project_path="/tmp/test-project-b",
            preferred_port=1975
        )

        with pytest.raises(PortConflictError) as exc_info:
            container_b.start()

        # Verify error message quality
        error_msg = str(exc_info.value)
        assert "1975" in error_msg, "Error should mention conflicting port"
        assert "test-project-a" in error_msg, "Error should mention conflicting project"
        assert "already" in error_msg.lower() or "conflict" in error_msg.lower(), \
            "Error should indicate conflict"

    finally:
        container_a.stop()


def test_manual_port_idempotency(temp_registry):
    """
    Test that same project with same preferred port gets that port consistently.

    Scenario:
    1. Start container A with preferred_port=1975
    2. Stop container A
    3. Restart container A with preferred_port=1975
    4. Verify port 1975 assigned again (idempotent)
    """
    # First start
    container_1 = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a",
        preferred_port=1975
    )
    container_1.start()
    port_1 = container_1.get_assigned_port()
    assert port_1 == 1975, "First start should get preferred port"
    container_1.stop()

    # Second start (same project, same preference)
    container_2 = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a",
        preferred_port=1975
    )
    container_2.start()

    try:
        port_2 = container_2.get_assigned_port()
        assert port_2 == 1975, "Second start should get same preferred port"

    finally:
        container_2.stop()


def test_manual_port_outside_range_allows_manual_override(temp_registry):
    """
    Test that preferred port outside registry range is allowed (manual override).

    Scenario:
    1. Assign port 9999 (outside default range 1972-1981)
    2. Verify assignment succeeds (manual override allowed)
    3. Verify port 9999 assigned

    Note: PortRegistry allows manual port override outside the auto-assignment range.
    This is intentional - users can manually specify ANY port, but auto-assignment
    only uses the configured range.
    """
    # Manual port override is allowed outside range
    assignment = temp_registry.assign_port(
        project_path="/tmp/test-project-manual",
        preferred_port=9999
    )

    # Verify assignment succeeded with manual port
    assert assignment.port == 9999, "Manual port override should work outside range"
    assert assignment.assignment_type == "manual", "Should be marked as manual assignment"


def test_manual_port_persists_until_released(temp_registry):
    """
    Test that manual port assignment persists until explicitly released.

    Scenario:
    1. Start container A with preferred_port=1975
    2. Stop container A (releases port)
    3. Start container A again without preference (auto-assign)
    4. Verify container A gets first available port (not necessarily 1975)

    Note: Port release happens in stop(), so the second start gets a new assignment.
    This is correct behavior - ports are released immediately on stop() to allow reuse.
    """
    # First start with manual preference
    container_1 = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-manual-persist",
        preferred_port=1975
    )
    container_1.start()
    port_1 = container_1.get_assigned_port()
    assert port_1 == 1975, "First start should get manual port"
    container_1.stop()  # RELEASES port 1975

    # Verify port was released
    assignments = temp_registry.list_all()
    assert len(assignments) == 0, "Port should be released after stop"

    # Second start without preference - gets new auto-assignment
    container_2 = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-manual-persist"
        # No preferred_port specified
    )
    container_2.start()

    try:
        port_2 = container_2.get_assigned_port()
        # Port was released, so new assignment from available pool
        assert 1972 <= port_2 <= 1981, "Should get port in auto-assignment range"
        # Port may or may not be 1975 (depends on Docker bound ports)

    finally:
        container_2.stop()
