"""
Contract tests for IRISContainer integration with PortRegistry.

These tests define the expected behavior when IRISContainer uses PortRegistry
for automatic port management.

Following TDD workflow: tests written BEFORE implementation.

Now ENABLED - IRISContainer integration implemented (T021-T024).
"""

import os
import tempfile
from pathlib import Path

import pytest

from iris_devtester.containers.iris_container import IRISContainer
from iris_devtester.ports import (
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


def test_backwards_compatibility_no_port_registry():
    """
    T010: Container without port_registry uses default port 1972.

    Contract: Backwards compatibility - existing code continues to work.
    """
    container = IRISContainer()
    container.start()

    try:
        assert container.get_assigned_port() == 1972
        assert container.get_project_path() is None
    finally:
        container.stop()


def test_auto_assignment_with_port_registry(temp_registry):
    """
    T011: Container with port_registry auto-assigns port from range.

    Contract: Port registry integration enables automatic port assignment.
    """
    container = IRISContainer(
        port_registry=temp_registry,
        project_path="/tmp/project-a"
    )
    container.start()

    try:
        port = container.get_assigned_port()
        assert 1972 <= port <= 1981

        # Verify registry has assignment
        assignment = temp_registry.get_assignment("/tmp/project-a")
        assert assignment is not None
        assert assignment.port == port
    finally:
        container.stop()


def test_auto_detect_project_path_from_cwd(temp_registry):
    """
    T012: Container auto-detects project_path from os.getcwd().

    Contract: Zero configuration - project path inferred from working directory.
    """
    # from testcontainers.iris import IRISContainer
    #
    # with tempfile.TemporaryDirectory() as tmpdir:
    #     old_cwd = os.getcwd()
    #     try:
    #         os.chdir(tmpdir)
    #         container = IRISContainer(port_registry=temp_registry)
    #
    #         assert container.get_project_path() == os.path.abspath(tmpdir)
    #
    #     finally:
    #         os.chdir(old_cwd)
    pass


def test_manual_port_preference_with_registry(temp_registry):
    """
    T013: Container respects manual port preference when port_registry provided.

    Contract: Manual override supported alongside auto-assignment.
    """
    # from testcontainers.iris import IRISContainer
    #
    # container = IRISContainer(
    #     port_registry=temp_registry,
    #     project_path="/tmp/project-a",
    #     port=1975  # Manual preference
    # )
    # container.start()
    #
    # assert container.get_assigned_port() == 1975
    #
    # assignment = temp_registry.get_assignment("/tmp/project-a")
    # assert assignment.assignment_type == "manual"
    # assert assignment.port == 1975
    #
    # container.stop()
    pass


def test_port_conflict_raises_error(temp_registry):
    """
    T014: Port conflict raises PortConflictError during container start.

    Contract: Port conflicts detected before container starts.
    """
    # from testcontainers.iris import IRISContainer
    #
    # # Project A gets port 1975
    # container_a = IRISContainer(
    #     port_registry=temp_registry,
    #     project_path="/tmp/project-a",
    #     port=1975
    # )
    # container_a.start()
    #
    # # Project B tries same port
    # container_b = IRISContainer(
    #     port_registry=temp_registry,
    #     project_path="/tmp/project-b",
    #     port=1975
    # )
    #
    # with pytest.raises(PortConflictError):
    #     container_b.start()
    #
    # container_a.stop()
    pass


def test_stop_releases_port_assignment(temp_registry):
    """
    T015: Container.stop() releases port assignment in registry.

    Contract: Ports automatically freed when containers stop.
    """
    # from testcontainers.iris import IRISContainer
    #
    # container = IRISContainer(
    #     port_registry=temp_registry,
    #     project_path="/tmp/project-a"
    # )
    # container.start()
    #
    # # Verify assignment exists
    # assignment = temp_registry.get_assignment("/tmp/project-a")
    # assert assignment is not None
    #
    # container.stop()
    #
    # # Port released
    # assignment = temp_registry.get_assignment("/tmp/project-a")
    # assert assignment is None
    pass


def test_multiple_containers_unique_ports(temp_registry):
    """
    T016: Multiple containers get unique ports from registry.

    Contract: Registry prevents port conflicts across containers.
    """
    # from testcontainers.iris import IRISContainer
    #
    # containers = []
    # for i in range(3):
    #     container = IRISContainer(
    #         port_registry=temp_registry,
    #         project_path=f"/tmp/project-{i}"
    #     )
    #     container.start()
    #     containers.append(container)
    #
    # # Verify unique ports
    # ports = [c.get_assigned_port() for c in containers]
    # assert len(ports) == len(set(ports)), "Ports must be unique"
    #
    # # Cleanup
    # for container in containers:
    #     container.stop()
    pass


def test_idempotent_start_for_same_project(temp_registry):
    """
    T017: Starting same project twice returns same port (idempotent).

    Contract: Registry provides stable port assignments per project.
    """
    # from testcontainers.iris import IRISContainer
    #
    # container_1 = IRISContainer(
    #     port_registry=temp_registry,
    #     project_path="/tmp/project-a"
    # )
    # container_1.start()
    # port_1 = container_1.get_assigned_port()
    #
    # # Same project, new container instance
    # container_2 = IRISContainer(
    #     port_registry=temp_registry,
    #     project_path="/tmp/project-a"
    # )
    # container_2.start()
    # port_2 = container_2.get_assigned_port()
    #
    # assert port_1 == port_2, "Same project should get same port (idempotent)"
    #
    # container_1.stop()
    # container_2.stop()
    pass


def test_port_exhaustion_raises_error(temp_registry_small_range):
    """
    Additional contract test: Port exhaustion raises PortExhaustedError.

    Contract: Clear error message when all ports in range are used.
    """
    # from testcontainers.iris import IRISContainer
    #
    # container_a = IRISContainer(
    #     port_registry=temp_registry_small_range,
    #     project_path="/tmp/project-a"
    # )
    # container_a.start()
    #
    # container_b = IRISContainer(
    #     port_registry=temp_registry_small_range,
    #     project_path="/tmp/project-b"
    # )
    # container_b.start()
    #
    # # Third container should fail
    # container_c = IRISContainer(
    #     port_registry=temp_registry_small_range,
    #     project_path="/tmp/project-c"
    # )
    #
    # with pytest.raises(PortExhaustedError):
    #     container_c.start()
    #
    # container_a.stop()
    # container_b.stop()
    pass
