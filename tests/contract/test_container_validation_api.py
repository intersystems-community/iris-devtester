"""Contract tests for container validation API.

These tests define the API contract for container validation functionality.
Tests are written BEFORE implementation (TDD Red phase).

Constitutional Compliance:
- Principle #5: Fail Fast with Guidance (error message validation)
- Principle #7: Medical-Grade Reliability (comprehensive test coverage)
"""

import pytest
from iris_devtester.containers.models import (
    ContainerHealthStatus,
    HealthCheckLevel,
    ValidationResult,
    ContainerHealth,
)


class TestContainerHealthStatus:
    """Contract tests for ContainerHealthStatus enum."""

    def test_enum_values_are_strings(self):
        """All enum values must be strings for JSON serialization."""
        assert ContainerHealthStatus.HEALTHY == "healthy"
        assert ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE == "running_not_accessible"
        assert ContainerHealthStatus.NOT_RUNNING == "not_running"
        assert ContainerHealthStatus.NOT_FOUND == "not_found"
        assert ContainerHealthStatus.STALE_REFERENCE == "stale_reference"
        assert ContainerHealthStatus.DOCKER_ERROR == "docker_error"

    def test_all_statuses_defined(self):
        """All expected statuses must be defined."""
        expected_statuses = {
            "healthy",
            "running_not_accessible",
            "not_running",
            "not_found",
            "stale_reference",
            "docker_error",
        }
        actual_statuses = {status.value for status in ContainerHealthStatus}
        assert actual_statuses == expected_statuses


class TestHealthCheckLevel:
    """Contract tests for HealthCheckLevel enum."""

    def test_enum_values_are_strings(self):
        """All enum values must be strings."""
        assert HealthCheckLevel.MINIMAL == "minimal"
        assert HealthCheckLevel.STANDARD == "standard"
        assert HealthCheckLevel.FULL == "full"

    def test_all_levels_defined(self):
        """All expected levels must be defined."""
        expected_levels = {"minimal", "standard", "full"}
        actual_levels = {level.value for level in HealthCheckLevel}
        assert actual_levels == expected_levels


class TestValidationResultDataclass:
    """Contract tests for ValidationResult dataclass."""

    def test_healthy_factory_method(self):
        """Factory method for healthy container must work correctly."""
        result = ValidationResult.healthy(
            name="iris_db",
            container_id="abc123def456",
            validation_time=0.15
        )

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_name == "iris_db"
        assert result.container_id == "abc123def456"
        assert result.message == "Container 'iris_db' is running and accessible"
        assert result.remediation_steps == []
        assert result.available_containers == []
        assert result.validation_time == 0.15

    def test_not_found_factory_method(self):
        """Factory method for container not found must work correctly."""
        result = ValidationResult.not_found(
            name="iris_db",
            available_containers=["iris_test", "iris_prod"],
            validation_time=0.12
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_FOUND
        assert result.container_name == "iris_db"
        assert result.container_id is None
        assert "does not exist" in result.message
        assert len(result.remediation_steps) >= 1
        assert "docker ps -a" in " ".join(result.remediation_steps)
        assert result.available_containers == ["iris_test", "iris_prod"]
        assert result.validation_time == 0.12

    def test_not_running_factory_method(self):
        """Factory method for stopped container must work correctly."""
        result = ValidationResult.not_running(
            name="iris_db",
            container_id="abc123",
            validation_time=0.10
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_RUNNING
        assert result.container_name == "iris_db"
        assert result.container_id == "abc123"
        assert "not running" in result.message
        assert len(result.remediation_steps) >= 1
        assert "docker start" in " ".join(result.remediation_steps)
        assert result.validation_time == 0.10

    def test_not_accessible_factory_method(self):
        """Factory method for inaccessible container must work correctly."""
        result = ValidationResult.not_accessible(
            name="iris_db",
            container_id="abc123",
            error="Cannot connect to container daemon",
            validation_time=0.25
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE
        assert result.container_name == "iris_db"
        assert result.container_id == "abc123"
        assert "not accessible" in result.message
        assert "Cannot connect" in result.message
        assert len(result.remediation_steps) >= 1
        assert "docker restart" in " ".join(result.remediation_steps)
        assert result.validation_time == 0.25

    def test_stale_reference_factory_method(self):
        """Factory method for stale reference must work correctly."""
        result = ValidationResult.stale_reference(
            name="iris_db",
            cached_id="abc123old",
            current_id="def456new",
            validation_time=0.18
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.STALE_REFERENCE
        assert result.container_name == "iris_db"
        assert result.container_id == "def456new"
        assert "recreated" in result.message.lower()
        assert "abc123old" in result.message
        assert "def456new" in result.message
        assert len(result.remediation_steps) >= 1
        assert result.validation_time == 0.18

    def test_docker_error_factory_method(self):
        """Factory method for Docker daemon error must work correctly."""
        test_error = ConnectionError("Error while fetching server API version")
        result = ValidationResult.docker_error(
            name="iris_db",
            error=test_error,
            validation_time=0.05
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.DOCKER_ERROR
        assert result.container_name == "iris_db"
        assert result.container_id is None
        assert "Docker daemon" in result.message
        assert "Error while fetching" in result.message
        assert len(result.remediation_steps) >= 1
        assert "docker --version" in " ".join(result.remediation_steps)
        assert result.validation_time == 0.05

    def test_format_message_for_healthy_container(self):
        """format_message() must return simple message for healthy container."""
        result = ValidationResult.healthy("iris_db", "abc123", 0.15)
        message = result.format_message()

        assert "iris_db" in message
        assert "healthy" in message.lower()
        # Healthy message should be simple (no multi-line structure)
        assert "What went wrong" not in message

    def test_format_message_for_not_found(self):
        """format_message() must follow constitutional structure for errors."""
        result = ValidationResult.not_found(
            "iris_db",
            ["iris_test"],
            0.12
        )
        message = result.format_message()

        # Constitutional Principle #5: Structured error messages
        assert "Container validation failed for 'iris_db'" in message
        assert "What went wrong:" in message
        assert "How to fix it:" in message
        assert "Available containers:" in message
        assert "iris_test" in message

    def test_format_message_for_not_running(self):
        """format_message() must include remediation for stopped container."""
        result = ValidationResult.not_running("iris_db", "abc123", 0.10)
        message = result.format_message()

        assert "What went wrong:" in message
        assert "How to fix it:" in message
        assert "docker start" in message

    def test_invariant_success_implies_healthy(self):
        """Invariant: success=True ⟹ status=HEALTHY."""
        result = ValidationResult.healthy("iris_db", "abc123", 0.15)
        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY

    def test_invariant_failure_implies_not_healthy(self):
        """Invariant: success=False ⟹ status != HEALTHY."""
        result = ValidationResult.not_found("iris_db", [], 0.12)
        assert result.success is False
        assert result.status != ContainerHealthStatus.HEALTHY

    def test_invariant_failure_has_remediation(self):
        """Invariant: success=False ⟹ len(remediation_steps) > 0."""
        result = ValidationResult.not_running("iris_db", "abc123", 0.10)
        assert result.success is False
        assert len(result.remediation_steps) > 0

    def test_invariant_success_no_remediation(self):
        """Invariant: success=True ⟹ remediation_steps == []."""
        result = ValidationResult.healthy("iris_db", "abc123", 0.15)
        assert result.success is True
        assert result.remediation_steps == []

    def test_invariant_not_found_no_container_id(self):
        """Invariant: status=NOT_FOUND ⟹ container_id is None."""
        result = ValidationResult.not_found("iris_db", [], 0.12)
        assert result.status == ContainerHealthStatus.NOT_FOUND
        assert result.container_id is None


class TestContainerHealthDataclass:
    """Contract tests for ContainerHealth dataclass."""

    def test_constructor_with_required_fields(self):
        """ContainerHealth must accept all required fields."""
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0"
        )

        assert health.container_name == "iris_db"
        assert health.status == ContainerHealthStatus.HEALTHY
        assert health.running is True
        assert health.accessible is True
        assert health.docker_sdk_version == "6.1.0"

    def test_constructor_with_optional_fields(self):
        """ContainerHealth must accept optional fields."""
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            container_id="abc123",
            started_at="2025-01-17T10:30:00Z",
            port_bindings={"1972/tcp": "1972"},
            image="intersystemsdc/iris-community:latest"
        )

        assert health.container_id == "abc123"
        assert health.started_at == "2025-01-17T10:30:00Z"
        assert health.port_bindings == {"1972/tcp": "1972"}
        assert health.image == "intersystemsdc/iris-community:latest"

    def test_to_dict_serialization(self):
        """to_dict() must serialize all fields correctly."""
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            container_id="abc123"
        )

        result = health.to_dict()

        assert isinstance(result, dict)
        assert result["container_name"] == "iris_db"
        assert result["status"] == "healthy"
        assert result["running"] is True
        assert result["accessible"] is True
        assert result["docker_sdk_version"] == "6.1.0"
        assert result["container_id"] == "abc123"

    def test_is_healthy_returns_true_for_healthy_status(self):
        """is_healthy() must return True for HEALTHY status."""
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0"
        )

        assert health.is_healthy() is True

    def test_is_healthy_returns_false_for_non_healthy_status(self):
        """is_healthy() must return False for non-HEALTHY statuses."""
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.NOT_RUNNING,
            running=False,
            accessible=False,
            docker_sdk_version="6.1.0"
        )

        assert health.is_healthy() is False

    def test_invariant_healthy_implies_running_and_accessible(self):
        """Invariant: status=HEALTHY ⟹ running=True AND accessible=True."""
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0"
        )

        assert health.status == ContainerHealthStatus.HEALTHY
        assert health.running is True
        assert health.accessible is True


class TestValidateContainerFunctionContract:
    """Contract tests for validate_container() function.

    Note: These tests will FAIL until implementation (TDD Red phase).
    This is expected and intentional.
    """

    def test_validate_container_function_exists(self):
        """validate_container() function must be importable."""
        from iris_devtester.containers.validation import validate_container
        assert callable(validate_container)

    def test_validate_container_signature(self):
        """validate_container() must have correct signature."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_minimal_level(self):
        """validate_container(level=MINIMAL) must perform fast check."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_standard_level(self):
        """validate_container(level=STANDARD) must check accessibility."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_full_level(self):
        """validate_container(level=FULL) must perform comprehensive check."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_invalid_input_empty_name(self):
        """validate_container() must raise ValueError for empty name."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_invalid_input_none_name(self):
        """validate_container() must raise TypeError for None name."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_timeout_parameter(self):
        """validate_container() must respect timeout parameter."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_performance_sla_minimal(self):
        """validate_container(MINIMAL) must complete in <500ms."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_performance_sla_standard(self):
        """validate_container(STANDARD) must complete in <1000ms."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_validate_container_performance_sla_full(self):
        """validate_container(FULL) must complete in <2000ms."""
        # This will fail until implementation
        pytest.skip("Implementation pending")


class TestContainerValidatorClassContract:
    """Contract tests for ContainerValidator class.

    Note: These tests will FAIL until implementation (TDD Red phase).
    """

    def test_container_validator_class_exists(self):
        """ContainerValidator class must be importable."""
        from iris_devtester.containers.validation import ContainerValidator
        assert ContainerValidator is not None

    def test_container_validator_caching(self):
        """ContainerValidator must cache validation results."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_container_validator_cache_ttl(self):
        """ContainerValidator must respect cache_ttl parameter."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_container_validator_force_refresh(self):
        """ContainerValidator.validate(force_refresh=True) must bypass cache."""
        # This will fail until implementation
        pytest.skip("Implementation pending")


class TestIRISContainerValidationContract:
    """Contract tests for IRISContainer validation methods.

    Note: These tests will FAIL until implementation (TDD Red phase).
    """

    def test_iriscontainer_validate_method_exists(self):
        """IRISContainer.validate() method must exist."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_iriscontainer_assert_healthy_method_exists(self):
        """IRISContainer.assert_healthy() method must exist."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_iriscontainer_validate_returns_validation_result(self):
        """IRISContainer.validate() must return ValidationResult."""
        # This will fail until implementation
        pytest.skip("Implementation pending")

    def test_iriscontainer_assert_healthy_raises_on_failure(self):
        """IRISContainer.assert_healthy() must raise exception on failure."""
        # This will fail until implementation
        pytest.skip("Implementation pending")
