"""
Integration test: Port persistence (T029).

Tests that port assignments persist across container restarts.
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


def test_port_persists_across_restarts(temp_registry):
    """
    Test that same project gets same port across multiple start/stop cycles.

    Scenario:
    1. Start container for project, get port X
    2. Stop container
    3. Restart container
    4. Verify port X assigned again
    5. Repeat 2-4 multiple times
    """
    project_path = "/tmp/test-project-persistence"
    ports_observed = []

    # Run 3 start/stop cycles
    for cycle in range(3):
        container = IRISContainer(
            port_registry=temp_registry,
            project_path=project_path
        )

        container.start()
        port = container.get_assigned_port()
        ports_observed.append(port)
        container.stop()

    # All cycles should get same port
    assert len(set(ports_observed)) == 1, \
        f"Expected same port across all cycles, got: {ports_observed}"

    # Verify registry is clean after all stops
    assignments = temp_registry.list_all()
    assert len(assignments) == 0, "Registry should be empty after all stops"


def test_port_released_after_stop(temp_registry):
    """
    Test that port is released immediately after container stop.

    Scenario:
    1. Start container A on port X
    2. Stop container A
    3. Start container B (different project)
    4. Verify container B can get port X (it's been released)
    """
    # Start and stop project A
    container_a = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-a"
    )
    container_a.start()
    port_a = container_a.get_assigned_port()
    container_a.stop()

    # Verify port released in registry
    assignments = temp_registry.list_all()
    assert len(assignments) == 0, "Port should be released after stop"

    # Start project B - should be able to reuse port_a
    container_b = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/test-project-b"
    )
    container_b.start()

    try:
        port_b = container_b.get_assigned_port()
        # Port B should get the first available port (which is port_a since it was released)
        assert port_b == port_a, "Released port should be reusable"
    finally:
        container_b.stop()
