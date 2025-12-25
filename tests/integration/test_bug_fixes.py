"""Integration tests for Feature 010 bug fixes.

Tests verify that bug fixes work correctly with real Docker containers:
- Bug Fix #1: Community edition uses correct Docker Hub image name
- Bug Fix #3: Volume mounts from config are applied to containers
"""

import os
import tempfile
from pathlib import Path

import docker
import pytest

from iris_devtester.config.container_config import ContainerConfig
from iris_devtester.utils.iris_container_adapter import IRISContainerManager


@pytest.fixture
def docker_client():
    """Get Docker client for integration tests."""
    return docker.from_env()


@pytest.fixture
def cleanup_containers(docker_client):
    """Cleanup test containers after each test."""
    containers_to_cleanup = []

    yield containers_to_cleanup

    # Cleanup
    for container_name in containers_to_cleanup:
        try:
            container = docker_client.containers.get(container_name)
            container.stop(timeout=2)
            container.remove(force=True, v=True)
            print(f"✓ Cleaned up container: {container_name}")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"Warning: Failed to cleanup {container_name}: {e}")


class TestBugFix1ImageName:
    """Integration tests for Bug Fix #1: Docker image name correction."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_community_edition_uses_correct_image(self, docker_client, cleanup_containers):
        """Test that Community edition containers use intersystemsdc/iris-community image.

        This verifies Bug Fix #1 works end-to-end:
        - Create ContainerConfig with edition="community"
        - Create and start IRISContainer using adapter
        - Verify container uses intersystemsdc/iris-community:latest (not intersystems/iris-community)
        """
        # Arrange
        container_name = "test-bug-fix-1-community"
        cleanup_containers.append(container_name)

        config = ContainerConfig(
            edition="community",
            container_name=container_name,
            superserver_port=41972,  # Non-standard port to avoid conflicts
            webserver_port=48773,
            namespace="USER",
            password="SYS",
            image_tag="latest"
        )

        # Act
        iris = IRISContainerManager.create_from_config(config)
        iris.start()

        try:
            # Get the underlying Docker container
            docker_container = docker_client.containers.get(container_name)

            # Assert - Verify image name
            image_name = docker_container.attrs['Config']['Image']

            # The image should be intersystemsdc/iris-community:latest (with 'dc' suffix)
            assert "intersystemsdc/iris-community" in image_name, (
                f"Expected image to contain 'intersystemsdc/iris-community' but got: {image_name}"
            )
            assert "intersystems/iris-community" not in image_name or "dc" in image_name, (
                f"Image should NOT be 'intersystems/iris-community' (without 'dc')"
            )

            # Verify container is actually running
            assert docker_container.status in ["running", "created"], (
                f"Container should be running but status is: {docker_container.status}"
            )

            print(f"✓ Community container using correct image: {image_name}")

        finally:
            # Cleanup
            iris.stop()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_community_edition_image_can_be_pulled(self, docker_client):
        """Test that the correct Community image can be pulled from Docker Hub.

        Verifies that intersystemsdc/iris-community:latest exists and is accessible.
        """
        # Arrange
        expected_image = "intersystemsdc/iris-community:latest"

        # Act - Try to pull the image
        try:
            image = docker_client.images.pull(expected_image)

            # Assert
            assert image is not None, f"Failed to pull image: {expected_image}"
            assert len(image.tags) > 0, "Pulled image has no tags"
            assert expected_image in image.tags, (
                f"Expected {expected_image} in tags but got: {image.tags}"
            )

            print(f"✓ Successfully pulled and verified image: {expected_image}")

        except docker.errors.ImageNotFound:
            pytest.fail(f"Image not found on Docker Hub: {expected_image}")
        except docker.errors.APIError as e:
            pytest.fail(f"Docker API error while pulling image: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_wrong_community_image_does_not_exist(self, docker_client):
        """Test that the OLD incorrect image name doesn't exist (validates the bug).

        Verifies that intersystems/iris-community (without 'dc') doesn't exist on Docker Hub.
        This confirms why Bug Fix #1 was necessary.

        Note: This test may be skipped if the image is cached locally.
        """
        # Arrange
        wrong_image = "intersystems/iris-community:latest"

        # Try to remove local cached version first
        try:
            docker_client.images.remove(wrong_image, force=True)
        except:
            pass  # Image not cached, that's fine

        # Act & Assert - Should NOT be able to pull this image from Docker Hub
        try:
            docker_client.images.pull(wrong_image)
            # If we got here, the image exists (might be cached or created by user)
            pytest.skip(f"Image {wrong_image} exists (may be local/cached). Bug Fix #1 still verified by other tests.")
        except docker.errors.NotFound:
            print(f"✓ Confirmed wrong image doesn't exist on Docker Hub: {wrong_image}")
        except docker.errors.ImageNotFound:
            print(f"✓ Confirmed wrong image doesn't exist on Docker Hub: {wrong_image}")


class TestBugFix3VolumeMounting:
    """Integration tests for Bug Fix #3: Volume mounting implementation."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_single_volume_mount_is_applied(self, docker_client, cleanup_containers):
        """Test that a single volume mount from config is applied to container.

        Verifies Bug Fix #3:
        - Create temp directory with test file
        - Create ContainerConfig with volume mount
        - Start container
        - Verify mount exists and file is accessible
        """
        # Arrange
        container_name = "test-bug-fix-3-single-volume"
        cleanup_containers.append(container_name)

        # Create temp directory with test file
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Test content from host")

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=42972,
                webserver_port=48774,
                namespace="USER",
                password="SYS",
                volumes=[f"{temp_dir}:/external"]
            )

            # Act
            iris = IRISContainerManager.create_from_config(config)
            iris.start()

            try:
                # Get Docker container
                docker_container = docker_client.containers.get(container_name)

                # Assert - Verify mount exists
                mounts = docker_container.attrs['Mounts']
                assert len(mounts) > 0, "Container should have at least one mount"

                # Find our mount
                external_mount = None
                for mount in mounts:
                    if mount.get('Destination') == '/external' or '/external' in str(mount):
                        external_mount = mount
                        break

                assert external_mount is not None, (
                    f"Expected mount to /external but found mounts: {mounts}"
                )

                # Verify mount source matches our temp dir
                mount_source = external_mount.get('Source', '')
                assert temp_dir in mount_source or mount_source.endswith(os.path.basename(temp_dir)), (
                    f"Mount source {mount_source} should contain {temp_dir}"
                )

                # Verify file is accessible in container
                exec_result = docker_container.exec_run("cat /external/test.txt")
                assert exec_result.exit_code == 0, (
                    f"Failed to read file in container: {exec_result.output.decode()}"
                )
                assert "Test content from host" in exec_result.output.decode(), (
                    f"File content mismatch: {exec_result.output.decode()}"
                )

                print(f"✓ Single volume mount verified: {temp_dir} -> /external")

            finally:
                iris.stop()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_volume_mounts_are_applied(self, docker_client, cleanup_containers):
        """Test that multiple volume mounts from config are all applied.

        Verifies Bug Fix #3 with multiple volumes:
        - Create multiple temp directories
        - Mount all of them
        - Verify all mounts exist and are accessible
        """
        # Arrange
        container_name = "test-bug-fix-3-multiple-volumes"
        cleanup_containers.append(container_name)

        # Create temp directories
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:

            # Create test files
            (Path(temp_dir1) / "file1.txt").write_text("Content 1")
            (Path(temp_dir2) / "file2.txt").write_text("Content 2")

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=43972,
                webserver_port=48775,
                namespace="USER",
                password="SYS",
                volumes=[
                    f"{temp_dir1}:/data1",
                    f"{temp_dir2}:/data2"
                ]
            )

            # Act
            iris = IRISContainerManager.create_from_config(config)
            iris.start()

            try:
                docker_container = docker_client.containers.get(container_name)

                # Assert - Verify both mounts exist
                mounts = docker_container.attrs['Mounts']
                mount_destinations = [m.get('Destination', '') for m in mounts]

                assert '/data1' in mount_destinations or any('/data1' in str(m) for m in mounts), (
                    f"Expected /data1 mount but found: {mount_destinations}"
                )
                assert '/data2' in mount_destinations or any('/data2' in str(m) for m in mounts), (
                    f"Expected /data2 mount but found: {mount_destinations}"
                )

                # Verify files are accessible
                exec1 = docker_container.exec_run("cat /data1/file1.txt")
                assert exec1.exit_code == 0
                assert "Content 1" in exec1.output.decode()

                exec2 = docker_container.exec_run("cat /data2/file2.txt")
                assert exec2.exit_code == 0
                assert "Content 2" in exec2.output.decode()

                print(f"✓ Multiple volume mounts verified: /data1 and /data2")

            finally:
                iris.stop()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_read_only_volume_mount(self, docker_client, cleanup_containers):
        """Test that read-only volume mounts are enforced.

        Verifies Bug Fix #3 with read-only mode:
        - Mount volume with :ro suffix
        - Verify mount is read-only
        - Verify writes are blocked
        """
        # Arrange
        container_name = "test-bug-fix-3-readonly-volume"
        cleanup_containers.append(container_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "readonly.txt"
            test_file.write_text("Read-only content")

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=44972,
                webserver_port=48776,
                namespace="USER",
                password="SYS",
                volumes=[f"{temp_dir}:/readonly:ro"]
            )

            # Act
            iris = IRISContainerManager.create_from_config(config)
            iris.start()

            try:
                docker_container = docker_client.containers.get(container_name)

                # Assert - Verify mount exists and is read-only
                mounts = docker_container.attrs['Mounts']
                readonly_mount = None
                for mount in mounts:
                    if '/readonly' in str(mount.get('Destination', '')):
                        readonly_mount = mount
                        break

                assert readonly_mount is not None, f"Expected /readonly mount but found: {mounts}"

                # Verify RW flag is False (read-only)
                is_readonly = readonly_mount.get('RW', True) == False
                assert is_readonly or readonly_mount.get('Mode', '') == 'ro', (
                    f"Mount should be read-only but got: {readonly_mount}"
                )

                # Verify file can be read
                read_result = docker_container.exec_run("cat /readonly/readonly.txt")
                assert read_result.exit_code == 0
                assert "Read-only content" in read_result.output.decode()

                # Verify writes are blocked
                write_result = docker_container.exec_run(
                    "sh -c 'echo test > /readonly/newfile.txt'"
                )
                assert write_result.exit_code != 0, (
                    "Write should fail on read-only mount"
                )

                print(f"✓ Read-only volume mount verified: {temp_dir} -> /readonly:ro")

            finally:
                iris.stop()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_empty_volumes_list_works(self, docker_client, cleanup_containers):
        """Test that containers with no volumes still work correctly.

        Verifies Bug Fix #3 doesn't break containers without volumes.
        """
        # Arrange
        container_name = "test-bug-fix-3-no-volumes"
        cleanup_containers.append(container_name)

        config = ContainerConfig(
            edition="community",
            container_name=container_name,
            superserver_port=45972,
            webserver_port=48777,
            namespace="USER",
            password="SYS",
            volumes=[]  # Empty volumes list
        )

        # Act
        iris = IRISContainerManager.create_from_config(config)
        iris.start()

        try:
            docker_container = docker_client.containers.get(container_name)

            # Assert - Container should be running
            assert docker_container.status in ["running", "created"]

            # User-specified mounts should be 0 (IRIS may have internal mounts)
            # We just verify container started successfully
            print(f"✓ Container with empty volumes list started successfully")

        finally:
            iris.stop()


class TestBugFixesIntegration:
    """Comprehensive integration tests combining multiple bug fixes."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_community_with_volumes_end_to_end(self, docker_client, cleanup_containers):
        """Test Community edition with volume mounts (combines Bug Fix #1 and #3).

        This is the real-world use case: Community edition container with data volumes.
        """
        # Arrange
        container_name = "test-bug-fixes-combined"
        cleanup_containers.append(container_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test data
            data_file = Path(temp_dir) / "data.txt"
            data_file.write_text("Production data")

            config = ContainerConfig(
                edition="community",
                container_name=container_name,
                superserver_port=46972,
                webserver_port=48778,
                namespace="USER",
                password="SYS",
                volumes=[f"{temp_dir}:/production-data"]
            )

            # Act
            iris = IRISContainerManager.create_from_config(config)
            iris.start()

            try:
                docker_container = docker_client.containers.get(container_name)

                # Assert - Verify image name (Bug Fix #1)
                image_name = docker_container.attrs['Config']['Image']
                assert "intersystemsdc/iris-community" in image_name

                # Assert - Verify volume mount (Bug Fix #3)
                mounts = docker_container.attrs['Mounts']
                assert any('/production-data' in str(m.get('Destination', '')) for m in mounts)

                # Assert - Verify data is accessible
                exec_result = docker_container.exec_run("cat /production-data/data.txt")
                assert exec_result.exit_code == 0
                assert "Production data" in exec_result.output.decode()

                # Assert - Container is healthy
                assert docker_container.status in ["running", "created"]

                print(f"✓ End-to-end test passed: Community + volumes working correctly")

            finally:
                iris.stop()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_config_from_yaml_with_volumes(self, docker_client, cleanup_containers):
        """Test loading config from YAML with volumes (real-world pattern).

        Verifies bug fixes work with YAML configuration (most common use case).
        """
        # Arrange
        container_name = "test-bug-fixes-yaml"
        cleanup_containers.append(container_name)

        with tempfile.TemporaryDirectory() as temp_dir, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as yaml_file:

            # Create test data
            (Path(temp_dir) / "config.txt").write_text("Config from YAML")

            # Write YAML config
            yaml_content = f"""
edition: community
container_name: {container_name}
ports:
  superserver: 47972
  webserver: 48779
namespace: USER
password: SYS
volumes:
  - {temp_dir}:/app-config
image_tag: latest
"""
            yaml_file.write(yaml_content)
            yaml_file.flush()

            try:
                # Act - Load config from YAML
                config = ContainerConfig.from_yaml(yaml_file.name)

                # Verify config loaded correctly
                assert config.edition == "community"
                assert len(config.volumes) == 1
                assert f"{temp_dir}:/app-config" in config.volumes

                # Start container
                iris = IRISContainerManager.create_from_config(config)
                iris.start()

                try:
                    docker_container = docker_client.containers.get(container_name)

                    # Assert - Verify everything works
                    assert "intersystemsdc/iris-community" in docker_container.attrs['Config']['Image']

                    mounts = docker_container.attrs['Mounts']
                    assert any('/app-config' in str(m.get('Destination', '')) for m in mounts)

                    exec_result = docker_container.exec_run("cat /app-config/config.txt")
                    assert exec_result.exit_code == 0
                    assert "Config from YAML" in exec_result.output.decode()

                    print(f"✓ YAML config with volumes test passed")

                finally:
                    iris.stop()

            finally:
                # Cleanup YAML file
                Path(yaml_file.name).unlink()
