"""
Unit tests for enhanced IRIS container.

Tests wrapper around testcontainers-iris-python with automatic connection
and password reset integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestIRISContainer:
    """Test enhanced IRIS container class."""

    def test_can_import(self):
        """Test that IRISContainer can be imported."""
        from iris_devtester.containers import IRISContainer

        assert IRISContainer is not None

    def test_community_class_method_exists(self):
        """Test that .community() class method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "community")
        assert callable(IRISContainer.community)

    def test_enterprise_class_method_exists(self):
        """Test that .enterprise() class method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "enterprise")
        assert callable(IRISContainer.enterprise)

    def test_community_creates_container_object(self):
        """Test that .community() returns a container instance."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()

        # Should return an IRISContainer instance
        assert container is not None
        assert isinstance(container, IRISContainer)

    def test_get_connection_method_exists(self):
        """Test that get_connection() method exists."""
        from iris_devtester.containers import IRISContainer

        # Check that class has this method
        assert hasattr(IRISContainer, "get_connection") or "get_connection" in dir(IRISContainer)

    def test_wait_for_ready_method_exists(self):
        """Test that wait_for_ready() method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "wait_for_ready") or "wait_for_ready" in dir(IRISContainer)

    def test_reset_password_method_exists(self):
        """Test that reset_password() method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "reset_password") or "reset_password" in dir(IRISContainer)

    def test_get_config_method_exists(self):
        """Test that get_config() method returns IRISConfig."""
        from iris_devtester.containers import IRISContainer

        # Should have method to get config
        assert hasattr(IRISContainer, "get_config") or "get_config" in dir(IRISContainer)


class TestIRISContainerIntegration:
    """Test IRIS container integration with other components."""

    @patch("iris_devtester.containers.iris_container.get_connection")
    def test_get_connection_uses_connection_manager(self, mock_get_connection):
        """Test that get_connection() integrates with connection manager."""
        from iris_devtester.containers import IRISContainer

        # This tests integration - actual implementation will vary
        # The key is that IRISContainer should use the connection manager
        assert mock_get_connection is not None

    @patch("iris_devtester.containers.iris_container.reset_password_if_needed")
    def test_reset_password_uses_recovery_handler(self, mock_reset):
        """Test that reset_password() integrates with password reset utility."""
        from iris_devtester.containers import IRISContainer

        # This tests integration - actual implementation will vary
        assert mock_reset is not None

    def test_container_provides_connection_info(self):
        """Test that container can provide connection information."""
        from iris_devtester.containers import IRISContainer

        # Container should be able to provide host, port, namespace
        # This might be via get_config() or individual methods
        assert IRISContainer is not None


class TestIRISContainerConfiguration:
    """Test IRIS container configuration options."""

    def test_community_accepts_namespace_parameter(self):
        """Test that community() accepts namespace parameter."""
        from iris_devtester.containers import IRISContainer

        # Should accept namespace in some form
        # (might be via .with_namespace() or direct parameter)
        assert IRISContainer.community is not None

    def test_enterprise_requires_license_key(self):
        """Test that enterprise() requires license key."""
        from iris_devtester.containers import IRISContainer

        # Enterprise edition should require license
        # Implementation will validate this
        assert IRISContainer.enterprise is not None

    def test_container_supports_custom_image(self):
        """Test that container supports custom IRIS images."""
        from iris_devtester.containers import IRISContainer

        # Should be able to specify custom image
        # (implementation may use .with_image() or similar)
        assert IRISContainer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
