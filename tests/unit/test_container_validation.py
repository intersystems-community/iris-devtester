"""Unit tests for container validation module.

Tests cover:
- validate_container() function with various scenarios
- _get_container_by_name() helper
- _get_available_containers() helper
- _check_exec_accessibility() helper
- _check_iris_health() helper
- ContainerValidator class with caching
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.containers.models import (
    ContainerHealthStatus,
    HealthCheckLevel,
    ValidationResult,
)
from iris_devtester.containers.validation import (
    ContainerValidator,
    _check_exec_accessibility,
    _check_iris_health,
    _get_available_containers,
    _get_container_by_name,
    validate_container,
)


class TestGetContainerByName:
    """Test _get_container_by_name helper function."""

    def test_container_found(self):
        """Test finding an existing container by name."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.name = "iris_test"
        mock_client.containers.get.return_value = mock_container

        result = _get_container_by_name(mock_client, "iris_test")

        assert result is mock_container
        mock_client.containers.get.assert_called_once_with("iris_test")

    def test_container_not_found(self):
        """Test that None is returned when container doesn't exist."""
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")

        result = _get_container_by_name(mock_client, "iris_nonexistent")

        assert result is None

    def test_container_unexpected_error(self):
        """Test that None is returned on unexpected errors."""
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("Connection error")

        result = _get_container_by_name(mock_client, "iris_test")

        assert result is None


class TestGetAvailableContainers:
    """Test _get_available_containers helper function."""

    def test_no_containers(self):
        """Test with no containers running."""
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []

        result = _get_available_containers(mock_client)

        assert result == []

    def test_multiple_containers(self):
        """Test listing multiple containers with status."""
        mock_client = MagicMock()

        mock_container1 = MagicMock()
        mock_container1.name = "iris_test"
        mock_container1.status = "running"

        mock_container2 = MagicMock()
        mock_container2.name = "iris_prod"
        mock_container2.status = "exited"

        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        result = _get_available_containers(mock_client)

        assert len(result) == 2
        assert "iris_test (running)" in result
        assert "iris_prod (exited)" in result

    def test_containers_with_none_name(self):
        """Test that containers with None name are skipped."""
        mock_client = MagicMock()

        mock_container1 = MagicMock()
        mock_container1.name = None
        mock_container1.status = "running"

        mock_container2 = MagicMock()
        mock_container2.name = "iris_test"
        mock_container2.status = "running"

        mock_client.containers.list.return_value = [mock_container1, mock_container2]

        result = _get_available_containers(mock_client)

        assert len(result) == 1
        assert "iris_test (running)" in result

    def test_exception_returns_empty_list(self):
        """Test that exceptions return an empty list."""
        mock_client = MagicMock()
        mock_client.containers.list.side_effect = Exception("Connection failed")

        result = _get_available_containers(mock_client)

        assert result == []


class TestCheckExecAccessibility:
    """Test _check_exec_accessibility helper function."""

    def test_exec_successful(self):
        """Test successful exec command."""
        mock_container = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.exit_code = 0
        mock_container.exec_run.return_value = mock_exec_result

        accessible, error = _check_exec_accessibility(mock_container)

        assert accessible is True
        assert error is None
        mock_container.exec_run.assert_called_once_with("echo healthy", demux=False)

    def test_exec_failed_with_exit_code(self):
        """Test failed exec with non-zero exit code."""
        mock_container = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.exit_code = 1
        mock_container.exec_run.return_value = mock_exec_result

        accessible, error = _check_exec_accessibility(mock_container)

        assert accessible is False
        assert "exit code 1" in error

    def test_exec_exception(self):
        """Test exec raising an exception."""
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = Exception("Connection refused")

        accessible, error = _check_exec_accessibility(mock_container)

        assert accessible is False
        assert error is not None
        assert "Connection refused" in error


class TestCheckIrisHealth:
    """Test _check_iris_health helper function."""

    def test_iris_query_successful(self):
        """Test successful IRIS health check."""
        mock_container = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.exit_code = 0
        mock_container.exec_run.return_value = mock_exec_result

        healthy, error = _check_iris_health(mock_container)

        assert healthy is True
        assert error is None

    def test_iris_query_failed(self):
        """Test failed IRIS health check."""
        mock_container = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.exit_code = 1
        mock_container.exec_run.return_value = mock_exec_result

        healthy, error = _check_iris_health(mock_container)

        assert healthy is False
        assert "exit code 1" in error

    def test_iris_query_exception(self):
        """Test IRIS health check with exception."""
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = Exception("IRIS not responsive")

        healthy, error = _check_iris_health(mock_container)

        assert healthy is False
        assert "IRIS not responsive" in error


class TestValidateContainerInputValidation:
    """Test validate_container input validation."""

    def test_empty_container_name(self):
        """Test that empty container name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_container("")

    def test_whitespace_container_name(self):
        """Test that whitespace-only container name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_container("   ")

    def test_non_string_container_name(self):
        """Test that non-string container name raises TypeError."""
        with pytest.raises(TypeError, match="must be str"):
            validate_container(123)

    def test_invalid_level_type(self):
        """Test that invalid level type raises TypeError."""
        with pytest.raises(TypeError, match="must be HealthCheckLevel"):
            validate_container("iris_test", level="full")

    def test_invalid_timeout(self):
        """Test that invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            validate_container("iris_test", timeout=-1)

    def test_zero_timeout(self):
        """Test that zero timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            validate_container("iris_test", timeout=0)


class TestValidateContainerWithMockedDocker:
    """Test validate_container with mocked Docker client."""

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_docker_connection_error(self, mock_from_env):
        """Test handling Docker connection errors."""
        from docker.errors import DockerException

        mock_from_env.side_effect = DockerException("Cannot connect to Docker daemon")

        result = validate_container("iris_test")

        assert result.success is False
        assert result.status == ContainerHealthStatus.DOCKER_ERROR
        assert result.container_id is None

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_container_not_found(self, mock_from_env):
        """Test validation when container is not found."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        # Simulate container not found
        with patch(
            "iris_devtester.containers.validation._get_container_by_name", return_value=None
        ):
            with patch(
                "iris_devtester.containers.validation._get_available_containers",
                return_value=["iris_other (running)", "iris_test2 (exited)"],
            ):
                result = validate_container("iris_nonexistent")

        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_FOUND
        assert result.container_id is None
        assert len(result.available_containers) == 2

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_container_not_running(self, mock_from_env):
        """Test validation when container exists but is not running."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123def456"
        mock_container.status = "exited"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            result = validate_container("iris_test")

        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_RUNNING
        assert result.container_id == "abc123def456"

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_minimal_level_success(self, mock_from_env):
        """Test MINIMAL validation level (just running status)."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            result = validate_container("iris_test", level=HealthCheckLevel.MINIMAL)

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_id == "abc123"

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_standard_level_accessibility_failure(self, mock_from_env):
        """Test STANDARD validation level with accessibility failure."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            with patch(
                "iris_devtester.containers.validation._check_exec_accessibility",
                return_value=(False, "Connection refused"),
            ):
                result = validate_container("iris_test", level=HealthCheckLevel.STANDARD)

        assert result.success is False
        assert result.status == ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE
        assert "Connection refused" in result.message

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_standard_level_success(self, mock_from_env):
        """Test STANDARD validation level success."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            with patch(
                "iris_devtester.containers.validation._check_exec_accessibility",
                return_value=(True, None),
            ):
                result = validate_container("iris_test", level=HealthCheckLevel.STANDARD)

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_full_level_iris_health_failure(self, mock_from_env):
        """Test FULL validation level with IRIS health check failure."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            with patch(
                "iris_devtester.containers.validation._check_exec_accessibility",
                return_value=(True, None),
            ):
                with patch(
                    "iris_devtester.containers.validation._check_iris_health",
                    return_value=(False, "IRIS not responding to queries"),
                ):
                    result = validate_container("iris_test", level=HealthCheckLevel.FULL)

        assert result.success is False
        assert result.status == ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE
        assert "IRIS not responsive" in result.message

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_full_level_success(self, mock_from_env):
        """Test FULL validation level complete success."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            with patch(
                "iris_devtester.containers.validation._check_exec_accessibility",
                return_value=(True, None),
            ):
                with patch(
                    "iris_devtester.containers.validation._check_iris_health",
                    return_value=(True, None),
                ):
                    result = validate_container("iris_test", level=HealthCheckLevel.FULL)

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_validation_time_recorded(self, mock_from_env):
        """Test that validation time is recorded."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            result = validate_container("iris_test", level=HealthCheckLevel.MINIMAL)

        assert result.validation_time >= 0
        assert isinstance(result.validation_time, float)


class TestContainerValidatorClass:
    """Test ContainerValidator class with caching."""

    def test_instantiation_with_name(self):
        """Test creating a ContainerValidator instance."""
        validator = ContainerValidator("iris_test")
        assert validator is not None

    def test_invalid_name_raises_error(self):
        """Test that invalid container name raises ValueError."""
        with pytest.raises(ValueError, match="must be non-empty string"):
            ContainerValidator("")

    def test_whitespace_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="must be non-empty string"):
            ContainerValidator("   ")

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_validate_calls_validate_container(self, mock_from_env):
        """Test that validate() calls validate_container."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        validator = ContainerValidator("iris_test", docker_client=mock_client)

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            result = validator.validate(level=HealthCheckLevel.MINIMAL)

        assert result.success is True
        assert isinstance(result, ValidationResult)

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_cache_ttl_honored(self, mock_from_env):
        """Test that cache TTL is honored."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        validator = ContainerValidator("iris_test", docker_client=mock_client, cache_ttl=10)

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            # First call
            result1 = validator.validate(level=HealthCheckLevel.MINIMAL)
            # Second call should use cache
            result2 = validator.validate(level=HealthCheckLevel.MINIMAL)

        assert result1 is result2  # Same object from cache

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_force_refresh_bypasses_cache(self, mock_from_env):
        """Test that force_refresh=True bypasses cache."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        validator = ContainerValidator("iris_test", docker_client=mock_client, cache_ttl=10)

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            result1 = validator.validate(level=HealthCheckLevel.MINIMAL)
            result2 = validator.validate(level=HealthCheckLevel.MINIMAL, force_refresh=True)

        # Different objects because cache was bypassed
        assert result1 is not result2

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_clear_cache(self, mock_from_env):
        """Test that clear_cache() resets cached state."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        validator = ContainerValidator("iris_test", docker_client=mock_client)

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            validator.validate(level=HealthCheckLevel.MINIMAL)
            assert validator._cached_result is not None

            validator.clear_cache()
            assert validator._cached_result is None

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_container_id_property_from_cache(self, mock_from_env):
        """Test that container_id property returns cached ID."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123def456"
        mock_container.status = "running"

        validator = ContainerValidator("iris_test", docker_client=mock_client)

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            validator.validate(level=HealthCheckLevel.MINIMAL)
            assert validator.container_id == "abc123def456"

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_is_healthy_property(self, mock_from_env):
        """Test is_healthy property."""
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"

        validator = ContainerValidator("iris_test", docker_client=mock_client)

        with patch(
            "iris_devtester.containers.validation._get_container_by_name",
            return_value=mock_container,
        ):
            # Patch validate_container to return success
            with patch(
                "iris_devtester.containers.validation.validate_container",
                return_value=ValidationResult.healthy("iris_test", "abc123", 0.1),
            ):
                assert validator.is_healthy is True

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_get_health_returns_container_health(self, mock_from_env):
        """Test that get_health() returns ContainerHealth object."""
        from iris_devtester.containers.models import ContainerHealth

        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.status = "running"
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {}},
            "State": {"StartedAt": "2025-01-01T00:00:00Z"},
        }
        mock_container.image.tags = ["intersystemsdc/iris-community:latest"]
        # Ensure reload() doesn't fail
        mock_container.reload = MagicMock()

        mock_client.containers.get.return_value = mock_container

        with patch(
            "iris_devtester.containers.validation._check_exec_accessibility",
            return_value=(True, None),
        ):
            validator = ContainerValidator("iris_test", docker_client=mock_client)
            health = validator.get_health()

        assert isinstance(health, ContainerHealth)
        assert health.container_name == "iris_test"
        assert health.running is True

    @patch("iris_devtester.containers.validation.docker.from_env")
    def test_get_health_container_not_found(self, mock_from_env):
        """Test that get_health() raises error for non-existent container."""
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = NotFound("Not found")

        validator = ContainerValidator("iris_nonexistent", docker_client=mock_client)

        with pytest.raises(ValueError, match="not found"):
            validator.get_health()
