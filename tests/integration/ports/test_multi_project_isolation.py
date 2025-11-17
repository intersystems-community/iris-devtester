"""
Integration test: Multi-project port isolation (T028).

Tests that multiple projects can run simultaneously with isolated ports.
Based on quickstart.md scenario.
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


def test_multi_project_isolation(temp_registry):
    """
    Test that multiple projects get isolated ports and can run concurrently.

    Scenario:
    1. Start container for project A
    2. Start container for project B
    3. Verify both have different ports
    4. Verify both can be accessed concurrently
    5. Verify registry tracks both assignments
    6. Stop both containers
    7. Verify ports released
    """
    # Create containers for two projects
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )

    container_b = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-b"
    )

    # Start both containers
    container_a.start()
    container_b.start()

    try:
        # Verify unique ports assigned
        port_a = container_a.get_assigned_port()
        port_b = container_b.get_assigned_port()

        assert port_a != port_b, "Projects must have unique ports"
        assert 1972 <= port_a <= 1981, f"Port {port_a} out of range"
        assert 1972 <= port_b <= 1981, f"Port {port_b} out of range"

        # Verify registry tracking
        assignments = temp_registry.list_all()
        assert len(assignments) == 2, "Registry should track 2 assignments"

        paths = {a.project_path for a in assignments}
        assert "/tmp/test-project-a" in paths
        assert "/tmp/test-project-b" in paths

        ports = {a.port for a in assignments}
        assert port_a in ports
        assert port_b in ports

        # Verify both containers are accessible (basic connectivity check)
        # Note: Full connection test would require IRIS to be fully started
        assert container_a.get_container_host_ip() is not None
        assert container_b.get_container_host_ip() is not None

    finally:
        # Cleanup
        container_a.stop()
        container_b.stop()

    # Verify ports released
    assignments_after = temp_registry.list_all()
    assert len(assignments_after) == 0, "All ports should be released after stop"


def test_multi_project_idempotency(temp_registry):
    """
    Test that restarting same project gets same port.

    Scenario:
    1. Start project A, get port X
    2. Stop project A
    3. Start project A again
    4. Verify port X assigned again (idempotent)
    """
    # First start
    container_1 = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )
    container_1.start()
    port_1 = container_1.get_assigned_port()
    container_1.stop()

    # Second start (same project)
    container_2 = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )
    container_2.start()

    try:
        port_2 = container_2.get_assigned_port()
        assert port_1 == port_2, "Same project should get same port (idempotent)"
    finally:
        container_2.stop()
