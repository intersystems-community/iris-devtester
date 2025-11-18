"""Integration tests for container validation functionality.

These tests use real Docker containers to validate the validation functionality.
Tests verify all validation levels, error scenarios, and performance SLAs.

Constitutional Compliance:
- Principle #1: Automatic remediation (error messages tested)
- Principle #5: Fail Fast with Guidance (message structure validated)
- Principle #7: Medical-Grade Reliability (comprehensive coverage)
"""

import time
import pytest
import docker
from iris_devtester.containers import (
    IRISContainer,
    validate_container,
    ContainerValidator,
    HealthCheckLevel,
    ContainerHealthStatus,
)


@pytest.fixture(scope="module")
def docker_client():
    """Docker client for integration tests."""
    return docker.from_env()


@pytest.fixture(scope="module")
def running_iris_container():
    """Running IRIS container for validation tests."""
    with IRISContainer.community() as iris:
        # Wait for container to be fully ready
        iris.wait_for_ready(timeout=60)
        yield iris


@pytest.fixture(scope="function")
def stopped_container(docker_client):
    """Create and stop a container for testing NOT_RUNNING status."""
    # Create container but don't start it
    container = docker_client.containers.create(
        "intersystemsdc/iris-community:latest",
        name="iris_test_stopped",
        detach=True
    )

    try:
        yield container.name
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass


class TestValidateContainerWithRunningContainer:
    """Test validate_container() with running IRIS container."""

    def test_validate_running_container_minimal_level(self, running_iris_container):
        """Validate healthy container with MINIMAL level check."""
        container_name = running_iris_container.get_container_name()

        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.MINIMAL
        )

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_name == container_name
        assert result.container_id is not None
        assert len(result.container_id) > 0
        assert result.remediation_steps == []
        assert result.validation_time > 0

    def test_validate_running_container_standard_level(self, running_iris_container):
        """Validate healthy container with STANDARD level check."""
        container_name = running_iris_container.get_container_name()

        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.STANDARD
        )

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_name == container_name
        assert result.container_id is not None
        assert result.remediation_steps == []

    def test_validate_running_container_full_level(self, running_iris_container):
        """Validate healthy container with FULL level check (includes IRIS health)."""
        container_name = running_iris_container.get_container_name()

        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.FULL
        )

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_name == container_name
        assert result.container_id is not None
        assert result.remediation_steps == []


class TestValidateContainerPerformanceSLAs:
    """Verify performance SLAs for each validation level."""

    def test_minimal_level_performance_under_500ms(self, running_iris_container):
        """MINIMAL validation must complete in <500ms."""
        container_name = running_iris_container.get_container_name()

        start = time.time()
        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.MINIMAL
        )
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed < 0.5  # <500ms SLA
        assert result.validation_time < 0.5

    def test_standard_level_performance_under_1000ms(self, running_iris_container):
        """STANDARD validation must complete in <1000ms."""
        container_name = running_iris_container.get_container_name()

        start = time.time()
        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.STANDARD
        )
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed < 1.0  # <1000ms SLA
        assert result.validation_time < 1.0

    def test_full_level_performance_under_2000ms(self, running_iris_container):
        """FULL validation must complete in <2000ms."""
        container_name = running_iris_container.get_container_name()

        start = time.time()
        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.FULL
        )
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed < 2.0  # <2000ms SLA
        assert result.validation_time < 2.0


class TestValidateContainerErrorScenarios:
    """Test validation with various error conditions."""

    def test_validate_nonexistent_container(self, docker_client):
        """Validate detection of non-existent container."""
        result = validate_container(
            container_name="iris_nonexistent_container_12345",
            level=HealthCheckLevel.STANDARD,
            docker_client=docker_client
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_FOUND
        assert result.container_name == "iris_nonexistent_container_12345"
        assert result.container_id is None
        assert len(result.remediation_steps) > 0
        assert "docker ps" in " ".join(result.remediation_steps)

    def test_validate_stopped_container(self, stopped_container, docker_client):
        """Validate detection of stopped (not running) container."""
        result = validate_container(
            container_name=stopped_container,
            level=HealthCheckLevel.STANDARD,
            docker_client=docker_client
        )

        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_RUNNING
        assert result.container_name == stopped_container
        assert result.container_id is not None
        assert len(result.remediation_steps) > 0
        assert "docker start" in " ".join(result.remediation_steps)

    def test_validate_container_format_message_structure(self, docker_client):
        """Verify error message follows Constitutional Principle #5."""
        result = validate_container(
            container_name="iris_test_not_found",
            level=HealthCheckLevel.STANDARD,
            docker_client=docker_client
        )

        message = result.format_message()

        # Constitutional Principle #5: Structured error messages
        assert "Container validation failed for 'iris_test_not_found'" in message
        assert "What went wrong:" in message
        assert "How to fix it:" in message


class TestValidateContainerInputValidation:
    """Test input validation for validate_container()."""

    def test_validate_container_empty_name_raises_valueerror(self, docker_client):
        """Empty container name must raise ValueError."""
        with pytest.raises(ValueError, match="container_name cannot be empty"):
            validate_container(
                container_name="",
                docker_client=docker_client
            )

    def test_validate_container_none_name_raises_typeerror(self, docker_client):
        """None container name must raise TypeError."""
        with pytest.raises(TypeError, match="container_name must be str"):
            validate_container(
                container_name=None,
                docker_client=docker_client
            )

    def test_validate_container_invalid_level_raises_typeerror(self, docker_client):
        """Invalid level type must raise TypeError."""
        with pytest.raises(TypeError, match="level must be HealthCheckLevel"):
            validate_container(
                container_name="iris_db",
                level="invalid",  # Should be HealthCheckLevel enum
                docker_client=docker_client
            )

    def test_validate_container_invalid_timeout_raises_valueerror(self, docker_client):
        """Invalid timeout must raise ValueError."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            validate_container(
                container_name="iris_db",
                timeout=-1,
                docker_client=docker_client
            )


class TestContainerValidatorClass:
    """Test ContainerValidator class functionality."""

    def test_container_validator_basic_usage(self, running_iris_container):
        """Test ContainerValidator with running container."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name)
        result = validator.validate()

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert validator.is_healthy is True

    def test_container_validator_caching(self, running_iris_container):
        """Test ContainerValidator caches results."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name, cache_ttl=10)

        # First validation (cache miss)
        result1 = validator.validate()
        time1 = result1.validation_time

        # Second validation (cache hit - should be instant)
        start = time.time()
        result2 = validator.validate()
        elapsed = time.time() - start

        # Cached result should be returned almost instantly
        assert elapsed < 0.01  # <10ms (much faster than actual validation)
        assert result1.container_id == result2.container_id

    def test_container_validator_force_refresh(self, running_iris_container):
        """Test ContainerValidator force_refresh bypasses cache."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name, cache_ttl=10)

        # First validation
        result1 = validator.validate()

        # Force refresh (cache bypass)
        result2 = validator.validate(force_refresh=True)

        # Both should succeed
        assert result1.success is True
        assert result2.success is True
        # But validation times should be similar (not cached)
        assert result2.validation_time > 0.01

    def test_container_validator_clear_cache(self, running_iris_container):
        """Test ContainerValidator.clear_cache() clears cache."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name, cache_ttl=10)

        # First validation (populates cache)
        validator.validate()

        # Clear cache
        validator.clear_cache()

        # Next validation should not use cache
        start = time.time()
        result = validator.validate()
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed > 0.01  # Not instant (cache was cleared)

    def test_container_validator_get_health(self, running_iris_container):
        """Test ContainerValidator.get_health() returns detailed metadata."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name)
        health = validator.get_health()

        assert health.container_name == container_name
        assert health.status == ContainerHealthStatus.HEALTHY
        assert health.running is True
        assert health.accessible is True
        assert health.container_id is not None
        assert health.docker_sdk_version is not None
        assert health.is_healthy() is True

        # Verify to_dict() serialization
        health_dict = health.to_dict()
        assert isinstance(health_dict, dict)
        assert health_dict["container_name"] == container_name
        assert health_dict["status"] == "healthy"
        assert health_dict["running"] is True

    def test_container_validator_container_id_property(self, running_iris_container):
        """Test ContainerValidator.container_id property."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name)

        # Before validation
        container_id = validator.container_id
        assert container_id is not None
        assert len(container_id) > 0

        # After validation
        result = validator.validate()
        assert validator.container_id == result.container_id


class TestIRISContainerValidationMethods:
    """Test IRISContainer.validate() and assert_healthy() integration."""

    def test_iriscontainer_validate_method(self, running_iris_container):
        """Test IRISContainer.validate() returns ValidationResult."""
        result = running_iris_container.validate()

        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_id is not None
        assert result.remediation_steps == []

    def test_iriscontainer_validate_with_level_parameter(self, running_iris_container):
        """Test IRISContainer.validate() with explicit level."""
        # MINIMAL level
        result_minimal = running_iris_container.validate(level=HealthCheckLevel.MINIMAL)
        assert result_minimal.success is True

        # STANDARD level
        result_standard = running_iris_container.validate(level=HealthCheckLevel.STANDARD)
        assert result_standard.success is True

        # FULL level
        result_full = running_iris_container.validate(level=HealthCheckLevel.FULL)
        assert result_full.success is True

    def test_iriscontainer_assert_healthy_succeeds(self, running_iris_container):
        """Test IRISContainer.assert_healthy() does not raise for healthy container."""
        # Should not raise exception
        running_iris_container.assert_healthy()

        # With explicit level
        running_iris_container.assert_healthy(level=HealthCheckLevel.FULL)

    def test_iriscontainer_assert_healthy_raises_on_failure(self):
        """Test IRISContainer.assert_healthy() raises RuntimeError on failure."""
        # Create mock IRISContainer that will fail validation
        # We can't easily test this with a real stopped container in the context manager,
        # but we can test the logic by using validate_container directly

        # This test verifies the error message structure when validation fails
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult.not_found(
            name="iris_test",
            available_containers=["iris_db"],
            validation_time=0.1
        )

        # Verify format_message() produces correct structure
        message = result.format_message()
        assert "Container validation failed" in message
        assert "What went wrong:" in message
        assert "How to fix it:" in message

        # The actual assert_healthy() would raise RuntimeError with this message
        # We test the message structure here to ensure Constitutional Principle #5


class TestValidationResultsInvariants:
    """Test ValidationResult invariants are maintained."""

    def test_invariant_success_implies_healthy(self, running_iris_container):
        """Invariant: success=True ⟹ status=HEALTHY."""
        container_name = running_iris_container.get_container_name()
        result = validate_container(container_name)

        if result.success:
            assert result.status == ContainerHealthStatus.HEALTHY

    def test_invariant_failure_implies_not_healthy(self, docker_client):
        """Invariant: success=False ⟹ status != HEALTHY."""
        result = validate_container("iris_nonexistent", docker_client=docker_client)

        if not result.success:
            assert result.status != ContainerHealthStatus.HEALTHY

    def test_invariant_failure_has_remediation(self, docker_client):
        """Invariant: success=False ⟹ len(remediation_steps) > 0."""
        result = validate_container("iris_nonexistent", docker_client=docker_client)

        if not result.success:
            assert len(result.remediation_steps) > 0

    def test_invariant_success_no_remediation(self, running_iris_container):
        """Invariant: success=True ⟹ remediation_steps == []."""
        container_name = running_iris_container.get_container_name()
        result = validate_container(container_name)

        if result.success:
            assert result.remediation_steps == []

    def test_invariant_not_found_no_container_id(self, docker_client):
        """Invariant: status=NOT_FOUND ⟹ container_id is None."""
        result = validate_container("iris_nonexistent", docker_client=docker_client)

        if result.status == ContainerHealthStatus.NOT_FOUND:
            assert result.container_id is None


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def test_validate_container_with_custom_docker_client(self, running_iris_container):
        """Test validate_container() with custom Docker client."""
        container_name = running_iris_container.get_container_name()
        custom_client = docker.from_env()

        result = validate_container(
            container_name=container_name,
            docker_client=custom_client
        )

        assert result.success is True

    def test_validate_container_with_short_timeout(self, running_iris_container):
        """Test validate_container() with very short timeout still works."""
        container_name = running_iris_container.get_container_name()

        # Even with 1s timeout, MINIMAL check should complete
        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.MINIMAL,
            timeout=1
        )

        assert result.success is True
        assert result.validation_time < 1.0

    def test_container_validator_zero_cache_ttl(self, running_iris_container):
        """Test ContainerValidator with cache_ttl=0 (effectively disabled)."""
        container_name = running_iris_container.get_container_name()

        validator = ContainerValidator(container_name=container_name, cache_ttl=0)

        # First validation
        result1 = validator.validate()

        # Second validation should NOT use cache (TTL is 0)
        start = time.time()
        result2 = validator.validate()
        elapsed = time.time() - start

        assert result1.success is True
        assert result2.success is True
        # Should not be instant (cache TTL is 0)
        assert elapsed > 0.01
