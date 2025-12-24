"""
Unit tests for validation result models.

Tests MUST FAIL until iris_devtester/testing/models.py is implemented.
"""

import pytest
from datetime import datetime


class TestPasswordResetResult:
    """Test PasswordResetResult dataclass."""

    def test_can_import(self):
        """Test that PasswordResetResult can be imported."""
        from iris_devtester.testing.models import PasswordResetResult

        assert PasswordResetResult is not None

    def test_success_result(self):
        """Test that PasswordResetResult can represent success."""
        from iris_devtester.testing.models import PasswordResetResult

        result = PasswordResetResult(
            success=True,
            new_password="newsecret",
            environment_updated=True
        )
        assert result.success == True
        assert result.new_password == "newsecret"
        assert result.environment_updated == True

    def test_failure_result(self):
        """Test that PasswordResetResult can represent failure."""
        from iris_devtester.testing.models import PasswordResetResult

        result = PasswordResetResult(
            success=False,
            error="Container not accessible",
            remediation_steps=["Step 1", "Step 2"]
        )
        assert result.success == False
        assert result.error == "Container not accessible"
        assert len(result.remediation_steps) == 2

    def test_get_message(self):
        """Test that PasswordResetResult has get_message method."""
        from iris_devtester.testing.models import PasswordResetResult

        result = PasswordResetResult(success=True, new_password="test")
        message = result.get_message()
        assert isinstance(message, str)


class TestCleanupAction:
    """Test CleanupAction dataclass."""

    def test_can_import(self):
        """Test that CleanupAction can be imported."""
        from iris_devtester.testing.models import CleanupAction

        assert CleanupAction is not None

    def test_required_fields(self):
        """Test that CleanupAction requires action_type and target."""
        from iris_devtester.testing.models import CleanupAction

        action = CleanupAction(
            action_type="drop_table",
            target="test_users"
        )
        assert action.action_type == "drop_table"
        assert action.target == "test_users"
        assert action.priority == 0

    def test_with_priority(self):
        """Test that CleanupAction supports priority."""
        from iris_devtester.testing.models import CleanupAction

        action = CleanupAction(
            action_type="stop_container",
            target="abc123",
            priority=10
        )
        assert action.priority == 10


class TestTestState:
    """Test TestState dataclass."""

    def test_can_import(self):
        """Test that TestState can be imported."""
        from iris_devtester.testing.models import TestState

        assert TestState is not None

    def test_required_fields(self):
        """Test that TestState requires test_id, isolation_level, namespace."""
        from iris_devtester.testing.models import TestState

        state = TestState(
            test_id="test_001",
            isolation_level="container",
            namespace="TEST_001"
        )
        assert state.test_id == "test_001"
        assert state.isolation_level == "container"
        assert state.namespace == "TEST_001"

    def test_default_fields(self):
        """Test that TestState has default values."""
        from iris_devtester.testing.models import TestState

        state = TestState(
            test_id="test_001",
            isolation_level="namespace",
            namespace="TEST_001"
        )
        assert state.container_id is None
        assert state.connection_info is None
        assert state.cleanup_registered == []
        assert state.schema_validated == False
        assert isinstance(state.created_at, datetime)

    def test_register_cleanup(self):
        """Test that TestState has register_cleanup method."""
        from iris_devtester.testing.models import TestState, CleanupAction

        state = TestState(
            test_id="test_001",
            isolation_level="namespace",
            namespace="TEST_001"
        )

        action1 = CleanupAction(action_type="drop_table", target="t1", priority=1)
        action2 = CleanupAction(action_type="drop_table", target="t2", priority=10)

        state.register_cleanup(action1)
        state.register_cleanup(action2)

        assert len(state.cleanup_registered) == 2
        # Should be sorted by priority (higher first)
        assert state.cleanup_registered[0].priority == 10
        assert state.cleanup_registered[1].priority == 1


class TestContainerConfig:
    """Test ContainerConfig dataclass."""

    def test_can_import(self):
        """Test that ContainerConfig can be imported."""
        from iris_devtester.testing.models import ContainerConfig

        assert ContainerConfig is not None

    def test_default_values(self):
        """Test that ContainerConfig has default values."""
        from iris_devtester.testing.models import ContainerConfig

        config = ContainerConfig()
        assert config.edition == "community"
        assert config.image == "intersystemsdc/iris-community"
        assert config.tag == "latest"
        assert config.wait_timeout == 60
        assert config.health_check_interval == 5

    def test_enterprise_requires_license(self):
        """Test that enterprise edition requires license_key."""
        from iris_devtester.testing.models import ContainerConfig

        with pytest.raises(ValueError):
            ContainerConfig(edition="enterprise")

    def test_enterprise_with_license(self):
        """Test that enterprise edition works with license_key."""
        from iris_devtester.testing.models import ContainerConfig

        config = ContainerConfig(
            edition="enterprise",
            license_key="test-license"
        )
        assert config.edition == "enterprise"
        assert config.license_key == "test-license"

    def test_timeout_validation(self):
        """Test that timeouts must be positive."""
        from iris_devtester.testing.models import ContainerConfig

        with pytest.raises(ValueError):
            ContainerConfig(wait_timeout=0)

        with pytest.raises(ValueError):
            ContainerConfig(health_check_interval=-1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
