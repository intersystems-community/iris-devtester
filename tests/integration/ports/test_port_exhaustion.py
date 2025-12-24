"""
Integration test: Port exhaustion handling (T030).

Tests that PortRegistry handles port exhaustion gracefully.
"""

import tempfile
from pathlib import Path

import pytest

from iris_devtester.containers.iris_container import IRISContainer
from iris_devtester.ports import PortRegistry, PortExhaustedError


@pytest.fixture
def temp_registry_small_range():
    """Temporary registry with small port range for testing exhaustion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test-registry.json"
        # Use small range (1972-1974) to make exhaustion testable
        yield PortRegistry(registry_path=registry_path, port_range=(1972, 1974))


def test_port_exhaustion_error(temp_registry_small_range):
    """
    Test that PortExhaustedError is raised when all ports are in use.

    Scenario:
    1. Fill all available ports in range (may be 2-3 depending on Docker conflicts)
    2. Try to start one more container
    3. Verify PortExhaustedError is raised
    4. Verify error message includes remediation steps
    5. Stop one container
    6. Verify new container can now start (port released)

    Note: Docker conflict detection may reduce available ports if external containers
    are using ports in the range (e.g., iris_db on 1972).
    """
    containers = []

    try:
        # Determine how many ports are actually available
        # Try to start containers until we hit PortExhaustedError
        max_attempts = 5  # Safety limit
        for i in range(max_attempts):
            try:
                container = IRISContainer(
                    port_registry=temp_registry_small_range,
                    project_path=f"/tmp/test-project-exhaust-{chr(65 + i)}"
                )
                container.start()
                containers.append(container)
            except PortExhaustedError:
                # Expected - all ports exhausted
                break

        # Verify at least 2 containers started (range is 1972-1974)
        assert len(containers) >= 2, "Should be able to start at least 2 containers"

        # Verify all available ports are assigned
        assignments = temp_registry_small_range.list_all()
        assert len(assignments) == len(containers), "Assignments should match containers"

        # Try to start one more container - should fail
        container_extra = IRISContainer(
            port_registry=temp_registry_small_range,
            project_path="/tmp/test-project-exhaust-EXTRA"
        )

        with pytest.raises(PortExhaustedError) as exc_info:
            container_extra.start()

        # Verify error message quality
        error_msg = str(exc_info.value)
        assert "1972-1974" in error_msg, "Error should mention port range"
        assert "exhausted" in error_msg.lower() or "in use" in error_msg.lower(), \
            "Error should mention exhaustion"
        assert "stop" in error_msg.lower() or "release" in error_msg.lower() or "clear" in error_msg.lower(), \
            "Error should suggest remediation"

        # Stop one container to free a port
        containers[0].stop()
        freed_port = containers[0].get_assigned_port()
        containers.pop(0)

        # Now extra container should be able to start
        container_extra.start()
        port_extra = container_extra.get_assigned_port()
        assert 1972 <= port_extra <= 1974, f"Port {port_extra} should be in range"

        containers.append(container_extra)

    finally:
        # Cleanup all containers
        for container in containers:
            try:
                container.stop()
            except Exception:
                pass


def test_port_exhaustion_with_stale_assignments(temp_registry_small_range):
    """
    Test that cleanup_stale() frees ports for reuse.

    Scenario:
    1. Manually create stale assignments in registry with container_name set
    2. Try to assign port - should fail (ports exhausted)
    3. Run cleanup_stale()
    4. Try to assign port - should succeed (stale ports freed)

    Note: Docker conflict detection may reduce available ports, so we fill
    only the available ports dynamically.
    """
    import hashlib
    from iris_devtester.ports.assignment import PortAssignment
    from datetime import datetime

    # Determine available port count by trying assignments
    available_ports = []
    for i in range(10):  # Safety limit
        try:
            assignment = temp_registry_small_range.assign_port(
                project_path=f"/tmp/test-project-stale-{i}",
            )

            # CRITICAL: Set container_name so cleanup_stale() can detect staleness
            # (containers don't actually exist, so cleanup will mark as stale)
            project_hash = hashlib.md5(f"/tmp/test-project-stale-{i}".encode()).hexdigest()[:8]
            assignment.container_name = f"iris_{project_hash}_{assignment.port}"

            # Update assignment in registry
            data = temp_registry_small_range._read_registry()
            for j, a in enumerate(data["assignments"]):
                if a["project_path"] == assignment.project_path:
                    data["assignments"][j] = assignment.to_dict()
            temp_registry_small_range._write_registry(data)

            available_ports.append(assignment.port)
        except PortExhaustedError:
            # All available ports filled
            break

    # Verify we filled at least 2 ports (range is 1972-1974, docker may use 1972)
    assert len(available_ports) >= 2, "Should have at least 2 available ports"

    # Verify all available ports assigned
    assignments = temp_registry_small_range.list_all()
    assert len(assignments) == len(available_ports), "Assignments should match available ports"

    # Try to assign another port - should fail
    with pytest.raises(PortExhaustedError):
        temp_registry_small_range.assign_port("/tmp/test-project-new")

    # Run cleanup_stale() - should release all stale assignments
    # (containers don't actually exist since we manually created assignments)
    released = temp_registry_small_range.cleanup_stale()
    assert len(released) == len(available_ports), f"Should release all {len(available_ports)} stale assignments"

    # Now assignment should succeed
    assignment = temp_registry_small_range.assign_port("/tmp/test-project-new")
    assert 1972 <= assignment.port <= 1974, "Should get port in range"
    assert assignment.port in available_ports, "Should reuse one of the freed ports"
