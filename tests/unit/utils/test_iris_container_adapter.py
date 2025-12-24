"""Unit tests for iris_container_adapter module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import docker
from docker.errors import NotFound, DockerException

from iris_devtester.utils.iris_container_adapter import (
    IRISContainerManager,
    translate_docker_error,
)
from iris_devtester.config.container_config import ContainerConfig


class TestIRISContainerManagerCreateFromConfig:
    """Test IRISContainerManager.create_from_config() method."""

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_community(self, mock_iris_container_class):
        """Test creating IRISContainer from Community edition config."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="iris-devtest",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            image_tag="latest",
        )

        # Act
        result = IRISContainerManager.create_from_config(config)

        # Assert
        mock_iris_container_class.assert_called_once_with(
            image="intersystemsdc/iris-community:latest",
            port=1972,
            username="_SYSTEM",
            password="SYS",
            namespace="USER",
            license_key=None,  # Community edition has no license key
        )
        mock_container.with_name.assert_called_once_with("iris-devtest")
        assert mock_container.with_bind_ports.call_count == 2
        mock_container.with_bind_ports.assert_any_call(1972, 1972)
        mock_container.with_bind_ports.assert_any_call(52773, 52773)
        assert result == mock_container

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_enterprise(self, mock_iris_container_class):
        """Test creating IRISContainer from Enterprise edition config with license."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="enterprise",
            container_name="iris-enterprise",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            license_key="test-license-key",
            image_tag="2024.1",
        )

        # Act
        result = IRISContainerManager.create_from_config(config)

        # Assert
        mock_iris_container_class.assert_called_once_with(
            image="intersystems/iris:2024.1",
            port=1972,
            username="_SYSTEM",
            password="SYS",
            namespace="USER",
            license_key="test-license-key",
        )
        mock_container.with_name.assert_called_once_with("iris-enterprise")
        # No volume mapping for license key path (not in ContainerConfig)
        mock_container.with_volume_mapping.assert_not_called()
        assert result == mock_container

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_port_mapping(self, mock_iris_container_class):
        """Test that port mappings are correctly configured."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=31972,  # Non-standard port
            webserver_port=8080,  # Non-standard port
            namespace="USER",
            password="SYS",
            image_tag="latest",
        )

        # Act
        IRISContainerManager.create_from_config(config)

        # Assert
        assert mock_container.with_bind_ports.call_count == 2
        mock_container.with_bind_ports.assert_any_call(31972, 31972)
        mock_container.with_bind_ports.assert_any_call(8080, 8080)

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_image_tag_variations(
        self, mock_iris_container_class
    ):
        """Test different image tag variations."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        # Test with specific version
        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            image_tag="2024.1.0",
        )

        # Act
        IRISContainerManager.create_from_config(config)

        # Assert
        assert mock_iris_container_class.call_args[1]["image"] == "intersystemsdc/iris-community:2024.1.0"

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_with_single_volume(self, mock_iris_container_class):
        """Test creating container with single volume mount (Bug Fix #3)."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            volumes=["./data:/external"]
        )

        # Act
        IRISContainerManager.create_from_config(config)

        # Assert - Volume mounting should be called once
        mock_container.with_volume_mapping.assert_called_once_with("./data", "/external", "rw")

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_with_multiple_volumes(self, mock_iris_container_class):
        """Test creating container with multiple volume mounts (Bug Fix #3)."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            volumes=["./data:/external", "./config:/opt/config:ro", "./logs:/var/log:rw"]
        )

        # Act
        IRISContainerManager.create_from_config(config)

        # Assert - Volume mounting should be called three times
        assert mock_container.with_volume_mapping.call_count == 3
        calls = mock_container.with_volume_mapping.call_args_list
        assert calls[0][0] == ("./data", "/external", "rw")
        assert calls[1][0] == ("./config", "/opt/config", "ro")
        assert calls[2][0] == ("./logs", "/var/log", "rw")

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_with_read_only_volume(self, mock_iris_container_class):
        """Test creating container with read-only volume mount (Bug Fix #3)."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            volumes=["./config:/opt/config:ro"]
        )

        # Act
        IRISContainerManager.create_from_config(config)

        # Assert - Mode should be 'ro'
        mock_container.with_volume_mapping.assert_called_once_with("./config", "/opt/config", "ro")

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_with_empty_volumes(self, mock_iris_container_class):
        """Test creating container with empty volumes list (Bug Fix #3)."""
        # Arrange
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            volumes=[]
        )

        # Act
        IRISContainerManager.create_from_config(config)

        # Assert - Volume mounting should not be called
        mock_container.with_volume_mapping.assert_not_called()


class TestIRISContainerManagerGetExisting:
    """Test IRISContainerManager.get_existing() method."""

    @patch("iris_devtester.utils.iris_container_adapter.docker")
    def test_get_existing_found(self, mock_docker):
        """Test finding an existing container."""
        # Arrange
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.containers.get.return_value = mock_container

        # Act
        result = IRISContainerManager.get_existing("iris-devtest")

        # Assert
        mock_docker.from_env.assert_called_once()
        mock_client.containers.get.assert_called_once_with("iris-devtest")
        assert result == mock_container

    @patch("iris_devtester.utils.iris_container_adapter.docker")
    def test_get_existing_not_found(self, mock_docker):
        """Test that None is returned when container doesn't exist."""
        # Arrange
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.containers.get.side_effect = NotFound("Container not found")

        # Act
        result = IRISContainerManager.get_existing("nonexistent-container")

        # Assert
        assert result is None

    @patch("iris_devtester.utils.iris_container_adapter.docker")
    @patch("iris_devtester.utils.iris_container_adapter.translate_docker_error")
    def test_get_existing_docker_error(self, mock_translate, mock_docker):
        """Test that Docker errors are translated to constitutional format."""
        # Arrange
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        docker_error = DockerException("Connection refused")
        mock_client.containers.get.side_effect = docker_error

        translated_error = ConnectionError("Translated error")
        mock_translate.return_value = translated_error

        # Act & Assert
        with pytest.raises(ConnectionError, match="Translated error"):
            IRISContainerManager.get_existing("iris-devtest")

        mock_translate.assert_called_once_with(docker_error, None)


class TestIRISContainerManagerGetDockerClient:
    """Test IRISContainerManager.get_docker_client() method."""

    @patch("iris_devtester.utils.iris_container_adapter.docker")
    def test_get_docker_client_success(self, mock_docker):
        """Test successful Docker client connection."""
        # Arrange
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        # Act
        result = IRISContainerManager.get_docker_client()

        # Assert
        mock_docker.from_env.assert_called_once()
        mock_client.ping.assert_called_once()
        assert result == mock_client

    @patch("iris_devtester.utils.iris_container_adapter.docker")
    def test_get_docker_client_connection_error(self, mock_docker):
        """Test Docker client connection failure."""
        # Arrange
        mock_docker.from_env.side_effect = DockerException("Connection refused")

        # Act & Assert
        with pytest.raises(ConnectionError) as exc_info:
            IRISContainerManager.get_docker_client()

        # Verify constitutional error format
        error_message = str(exc_info.value)
        assert "Failed to connect to Docker daemon" in error_message
        assert "What went wrong:" in error_message
        assert "Why it matters:" in error_message
        assert "How to fix it:" in error_message
        assert "Documentation:" in error_message

    @patch("iris_devtester.utils.iris_container_adapter.docker")
    def test_get_docker_client_ping_fails(self, mock_docker):
        """Test Docker client ping failure."""
        # Arrange
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.side_effect = DockerException("Ping failed")

        # Act & Assert
        with pytest.raises(ConnectionError) as exc_info:
            IRISContainerManager.get_docker_client()

        assert "Failed to connect to Docker daemon" in str(exc_info.value)


class TestTranslateDockerError:
    """Test translate_docker_error() function."""

    def test_translate_port_conflict(self):
        """Test translation of port conflict error."""
        # Arrange
        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            image_tag="latest",
        )
        error = DockerException("port is already allocated")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ValueError)
        error_msg = str(result)
        assert "Port 1972 is already in use" in error_msg
        assert "What went wrong:" in error_msg
        assert "SuperServer port" in error_msg
        assert "How to fix it:" in error_msg
        assert "docker ps" in error_msg
        assert "Documentation:" in error_msg

    def test_translate_address_already_in_use(self):
        """Test translation of address already in use error."""
        # Arrange
        config = ContainerConfig.default()
        error = DockerException("address already in use")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ValueError)
        assert "is already in use" in str(result)

    def test_translate_image_not_found(self):
        """Test translation of image not found error."""
        # Arrange
        config = ContainerConfig(
            edition="community",
            container_name="iris-test",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            image_tag="nonexistent",
        )
        error = DockerException("image not found")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ValueError)
        error_msg = str(result)
        assert "intersystemsdc/iris-community:nonexistent" in error_msg
        assert "not found" in error_msg
        assert "docker pull" in error_msg

    def test_translate_manifest_unknown(self):
        """Test translation of manifest unknown error (image not found variant)."""
        # Arrange
        config = ContainerConfig.default()
        error = DockerException("manifest unknown")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ValueError)
        assert "not found" in str(result)

    def test_translate_docker_not_running(self):
        """Test translation of Docker daemon not running error."""
        # Arrange
        config = ContainerConfig.default()
        error = DockerException("cannot connect to docker daemon")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ConnectionError)
        error_msg = str(result)
        assert "Failed to connect to Docker daemon" in error_msg
        assert "Docker is not running" in error_msg
        assert "Start Docker Desktop" in error_msg or "systemctl start docker" in error_msg

    def test_translate_connection_refused(self):
        """Test translation of connection refused error."""
        # Arrange
        config = ContainerConfig.default()
        error = DockerException("connection refused")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ConnectionError)
        assert "Failed to connect to Docker daemon" in str(result)

    def test_translate_container_name_conflict(self):
        """Test translation of container name already in use error."""
        # Arrange
        config = ContainerConfig(
            edition="community",
            container_name="iris-devtest",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
            image_tag="latest",
        )
        error = DockerException("name already in use by container")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert isinstance(result, ValueError)
        error_msg = str(result)
        assert "iris-devtest" in error_msg
        assert "already in use" in error_msg
        assert "docker rm" in error_msg

    def test_translate_generic_error(self):
        """Test that unknown errors are passed through unchanged."""
        # Arrange
        config = ContainerConfig.default()
        error = DockerException("Unknown docker error")

        # Act
        result = translate_docker_error(error, config)

        # Assert
        assert result == error  # Pass through unchanged

    def test_translate_with_none_config(self):
        """Test error translation when config is None."""
        # Arrange
        error = DockerException("port is already allocated")

        # Act
        result = translate_docker_error(error, None)

        # Assert
        assert isinstance(result, ValueError)
        error_msg = str(result)
        assert "Port unknown is already in use" in error_msg
        assert "What went wrong:" in error_msg


class TestConstitutionalErrorFormat:
    """Test that all constitutional errors follow the 4-part format."""

    def test_all_errors_have_four_parts(self):
        """Verify all error messages have What/Why/How/Docs sections."""
        config = ContainerConfig.default()

        error_scenarios = [
            ("port is already allocated", ValueError),
            ("image not found", ValueError),
            ("cannot connect", ConnectionError),
            ("name already in use", ValueError),
        ]

        for error_str, expected_type in error_scenarios:
            error = DockerException(error_str)
            result = translate_docker_error(error, config)

            if result != error:  # If translated (not passed through)
                assert isinstance(result, expected_type)
                error_msg = str(result)
                assert "What went wrong:" in error_msg, f"Missing 'What' in {error_str}"
                assert "Why it matters:" in error_msg, f"Missing 'Why' in {error_str}"
                assert "How to fix it:" in error_msg, f"Missing 'How' in {error_str}"
                assert (
                    "Documentation:" in error_msg
                ), f"Missing 'Docs' in {error_str}"


class TestVolumeMountSpecParse:
    """Test VolumeMountSpec.parse() method (Feature 011 - T002)."""

    def test_parse_volume_host_container(self):
        """Test parsing volume string with host and container paths."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        # Act
        spec = VolumeMountSpec.parse("./data:/external")

        # Assert
        assert spec.host_path == "./data"
        assert spec.container_path == "/external"
        assert spec.mode == "rw"  # Default mode

    def test_parse_volume_host_container_mode(self):
        """Test parsing volume string with explicit read-only mode."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        # Act
        spec = VolumeMountSpec.parse("./data:/external:ro")

        # Assert
        assert spec.host_path == "./data"
        assert spec.container_path == "/external"
        assert spec.mode == "ro"

    def test_parse_volume_invalid_format(self):
        """Test that missing container path raises ValueError."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            VolumeMountSpec.parse("./data")

        error_msg = str(exc_info.value)
        assert "invalid format" in error_msg.lower()
        assert "host:container" in error_msg

    def test_parse_volume_invalid_mode(self):
        """Test that invalid mode (not rw/ro) raises ValueError."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            VolumeMountSpec.parse("./data:/external:invalid")

        error_msg = str(exc_info.value)
        assert "invalid mode" in error_msg.lower()
        assert "rw" in error_msg
        assert "ro" in error_msg

    def test_parse_volume_default_mode(self):
        """Test that mode defaults to 'rw' when not specified."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        # Act - Parse without mode suffix
        spec1 = VolumeMountSpec.parse("./data1:/external1")
        spec2 = VolumeMountSpec.parse("/absolute/path:/container/path")

        # Assert - Both should default to read-write
        assert spec1.mode == "rw"
        assert spec2.mode == "rw"


class TestContainerPersistenceCheck:
    """Test ContainerPersistenceCheck class (Feature 011 - T003)."""

    def test_persistence_check_success(self):
        """Test that success property returns True when all checks pass."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        # Arrange - All checks passing
        check = ContainerPersistenceCheck(
            container_name="test-container",
            exists=True,
            status="running",
            volume_mounts_verified=True,
            verification_time=2.0,
            error_details=None
        )

        # Assert
        assert check.success is True

    def test_persistence_check_container_not_found(self):
        """Test that success is False when container doesn't exist."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        # Arrange - Container missing
        check = ContainerPersistenceCheck(
            container_name="missing-container",
            exists=False,
            status=None,
            volume_mounts_verified=False,
            verification_time=2.0,
            error_details="Container not found after creation"
        )

        # Assert
        assert check.success is False
        assert check.exists is False

    def test_persistence_check_wrong_status(self):
        """Test that success is False when container has exited."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        # Arrange - Container exists but exited
        check = ContainerPersistenceCheck(
            container_name="exited-container",
            exists=True,
            status="exited",
            volume_mounts_verified=True,
            verification_time=2.0,
            error_details=None
        )

        # Assert
        assert check.success is False
        assert check.status == "exited"

    def test_persistence_check_volumes_not_verified(self):
        """Test that success is False when volume mounts failed verification."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        # Arrange - Container running but volumes not mounted
        check = ContainerPersistenceCheck(
            container_name="test-container",
            exists=True,
            status="running",
            volume_mounts_verified=False,
            verification_time=2.0,
            error_details=None
        )

        # Assert
        assert check.success is False
        assert check.volume_mounts_verified is False

    def test_get_error_message_constitutional_format(self):
        """Test that error message follows constitutional format (What/Why/How/Docs)."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        # Arrange - Failed persistence check
        check = ContainerPersistenceCheck(
            container_name="failed-container",
            exists=False,
            status=None,
            volume_mounts_verified=False,
            verification_time=2.0,
            error_details="Container removed by ryuk cleanup service"
        )

        config = ContainerConfig(
            edition="community",
            container_name="failed-container",
            superserver_port=1972,
            webserver_port=52773,
            namespace="USER",
            password="SYS",
        )

        # Act
        error_msg = check.get_error_message(config)

        # Assert - Constitutional format
        assert "What went wrong:" in error_msg
        assert "Why it matters:" in error_msg or "Why this happened:" in error_msg
        assert "How to fix it:" in error_msg
        assert "Documentation:" in error_msg

        # Assert - Specific details
        assert "failed-container" in error_msg
        assert check.error_details in error_msg
