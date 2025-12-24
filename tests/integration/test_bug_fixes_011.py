"""Integration tests for Feature 011 bug fixes (ryuk cleanup, volume mounting, container persistence).

These tests use real Docker containers to verify:
1. Containers persist after CLI process exits (no ryuk cleanup)
2. Volume mounts are applied and accessible
3. Read-only volume mounts enforce permissions
4. Persistence verification works correctly

NOTE: These tests must run sequentially as they share Docker resources.
"""

import time
import tempfile
from pathlib import Path

import pytest
import docker
from docker.errors import DockerException

from iris_devtester.config.container_config import ContainerConfig
from iris_devtester.utils.iris_container_adapter import (
    IRISContainerManager,
    verify_container_persistence,
)


@pytest.fixture(scope="function")
def docker_client():
    """Get Docker client for inspection."""
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture(scope="function")
def cleanup_container():
    """Cleanup fixture to remove test containers after each test."""
    containers_to_cleanup = []

    def _register(container_name: str):
        containers_to_cleanup.append(container_name)

    yield _register

    # Cleanup
    client = docker.from_env()
    for container_name in containers_to_cleanup:
        try:
            container = client.containers.get(container_name)
            container.stop(timeout=5)
            container.remove(force=True)
            print(f"Cleaned up container: {container_name}")
        except Exception as e:
            print(f"Cleanup warning for {container_name}: {e}")
    client.close()


class TestRyukLifecycle:
    """Test that CLI containers persist without ryuk cleanup (Feature 011 - T004, T005)."""

    def test_cli_container_persists_after_process_exit(
        self, docker_client, cleanup_container
    ):
        """Test that container created via CLI persists for 60+ seconds (T004)."""
        # Arrange
        container_name = "test-persistence-cli-001"
        cleanup_container(container_name)

        config = ContainerConfig(
            edition="community",
            container_name=container_name,
            superserver_port=31001,
            webserver_port=58001,
            namespace="USER",
            password="SYS",
        )

        # Act - Create container with use_testcontainers=False (CLI mode)
        container = IRISContainerManager.create_from_config(
            config, use_testcontainers=False
        )

        # Wait 60 seconds (simulate CLI process exit)
        print(f"Waiting 60 seconds to verify container persists...")
        time.sleep(60)

        # Assert - Container should still exist
        fetched_container = docker_client.containers.get(container_name)
        assert fetched_container is not None
        assert fetched_container.status in ["running", "created"]
        print(f"✓ Container persisted after 60 seconds: {fetched_container.status}")

    def test_cli_container_has_no_testcontainers_labels(
        self, docker_client, cleanup_container
    ):
        """Test that CLI containers don't have testcontainers labels (T005)."""
        # Arrange
        container_name = "test-no-tc-labels-001"
        cleanup_container(container_name)

        config = ContainerConfig(
            edition="community",
            container_name=container_name,
            superserver_port=31002,
            webserver_port=58002,
            namespace="USER",
            password="SYS",
        )

        # Act - Create container with use_testcontainers=False
        container = IRISContainerManager.create_from_config(
            config, use_testcontainers=False
        )

        # Assert - No testcontainers labels
        fetched_container = docker_client.containers.get(container_name)
        labels = fetched_container.attrs["Config"]["Labels"] or {}

        # Check for any testcontainers-related labels
        tc_labels = [key for key in labels.keys() if "testcontainers" in key.lower()]
        assert len(tc_labels) == 0, f"Found testcontainers labels: {tc_labels}"
        print(f"✓ No testcontainers labels found")


class TestVolumeMountVerification:
    """Test volume mounting for CLI containers (Feature 011 - T006, T007, T008)."""

    def test_single_volume_mount_applied_and_accessible(
        self, docker_client, cleanup_container
    ):
        """Test single volume mount is applied and files are accessible (T006)."""
        # Arrange - Create temp directory with test file
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello from host volume")

            container_name = "test-single-volume-001"
            cleanup_container(container_name)

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=31003,
                webserver_port=58003,
                namespace="USER",
                password="SYS",
                volumes=[f"{temp_dir}:/external"],
            )

            # Act - Create container
            container = IRISContainerManager.create_from_config(
                config, use_testcontainers=False
            )

            # Assert - Verify mount in Docker inspection
            fetched_container = docker_client.containers.get(container_name)
            mounts = fetched_container.attrs["Mounts"]
            assert len(mounts) >= 1, "No mounts found"

            # Find our mount
            external_mount = next(
                (m for m in mounts if m["Destination"] == "/external"), None
            )
            assert external_mount is not None, "Mount /external not found"
            assert temp_dir in external_mount["Source"]
            print(f"✓ Mount found: {external_mount['Source']} → /external")

            # Verify file accessible via docker exec
            exec_result = fetched_container.exec_run("cat /external/test.txt")
            assert exec_result.exit_code == 0
            assert b"Hello from host volume" in exec_result.output
            print(f"✓ File accessible from container")

    def test_multiple_volumes_all_mounted(self, docker_client, cleanup_container):
        """Test that multiple volumes can be mounted simultaneously (T007)."""
        # Arrange - Create 3 temp directories
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2, \
             tempfile.TemporaryDirectory() as temp_dir3:

            # Create test files in each directory
            (Path(temp_dir1) / "file1.txt").write_text("Data 1")
            (Path(temp_dir2) / "file2.txt").write_text("Data 2")
            (Path(temp_dir3) / "file3.txt").write_text("Data 3")

            container_name = "test-multiple-volumes-001"
            cleanup_container(container_name)

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=31004,
                webserver_port=58004,
                namespace="USER",
                password="SYS",
                volumes=[
                    f"{temp_dir1}:/data1",
                    f"{temp_dir2}:/data2",
                    f"{temp_dir3}:/data3",
                ],
            )

            # Act - Create container
            container = IRISContainerManager.create_from_config(
                config, use_testcontainers=False
            )

            # Assert - All 3 mounts present
            fetched_container = docker_client.containers.get(container_name)
            mounts = fetched_container.attrs["Mounts"]
            destinations = [m["Destination"] for m in mounts]

            assert "/data1" in destinations
            assert "/data2" in destinations
            assert "/data3" in destinations
            print(f"✓ All 3 volume mounts found")

            # Verify all files accessible
            for i in range(1, 4):
                exec_result = fetched_container.exec_run(f"cat /data{i}/file{i}.txt")
                assert exec_result.exit_code == 0
                assert f"Data {i}".encode() in exec_result.output
            print(f"✓ All 3 files accessible")

    def test_read_only_volume_enforced(self, docker_client, cleanup_container):
        """Test that read-only volume mounts enforce permissions (T008)."""
        # Arrange - Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "readonly.txt").write_text("Read only data")

            container_name = "test-readonly-volume-001"
            cleanup_container(container_name)

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=31005,
                webserver_port=58005,
                namespace="USER",
                password="SYS",
                volumes=[f"{temp_dir}:/readonly:ro"],
            )

            # Act - Create container
            container = IRISContainerManager.create_from_config(
                config, use_testcontainers=False
            )

            # Assert - Mount has RW=false
            fetched_container = docker_client.containers.get(container_name)
            mounts = fetched_container.attrs["Mounts"]
            readonly_mount = next(
                (m for m in mounts if m["Destination"] == "/readonly"), None
            )
            assert readonly_mount is not None
            assert readonly_mount["RW"] is False, "Mount should be read-only"
            print(f"✓ Mount is read-only (RW=False)")

            # Try to write (should fail)
            exec_result = fetched_container.exec_run("touch /readonly/newfile.txt")
            assert exec_result.exit_code != 0, "Write should have failed"
            assert (
                b"Read-only file system" in exec_result.output
                or b"Permission denied" in exec_result.output
            )
            print(f"✓ Write operation correctly failed")


class TestContainerPersistence:
    """Test container persistence verification (Feature 011 - T009)."""

    def test_persistence_check_detects_success(self, docker_client, cleanup_container):
        """Test that persistence verification detects successful container creation (T009)."""
        # Arrange
        container_name = "test-persistence-check-001"
        cleanup_container(container_name)

        config = ContainerConfig(
            edition="community",
            container_name=container_name,
            superserver_port=31006,
            webserver_port=58006,
            namespace="USER",
            password="SYS",
        )

        # Act - Create container
        container = IRISContainerManager.create_from_config(
            config, use_testcontainers=False
        )

        # Call persistence verification
        check = verify_container_persistence(container_name, config)

        # Assert - All checks pass
        assert check.success is True
        assert check.exists is True
        assert check.status in ["running", "created"]
        assert check.volume_mounts_verified is True
        print(f"✓ Persistence check passed: {check}")
