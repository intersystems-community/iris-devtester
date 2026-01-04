"""
Contract tests for Container Management API.

These tests validate the public API interface defined in:
specs/001-implement-iris-devtester/contracts/container-api.md

These tests MUST FAIL until implementation is complete.
"""


import pytest

pytestmark = pytest.mark.contract


class TestIRISContainer:
    """Contract tests for IRISContainer class."""

    def test_class_exists(self):
        """Test that IRISContainer class can be imported."""
        from iris_devtester.containers import IRISContainer

        assert IRISContainer is not None

    def test_has_community_classmethod(self):
        """Test that IRISContainer has community() class method."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, 'community')
        assert callable(IRISContainer.community)

    def test_community_returns_instance(self):
        """Test that community() returns IRISContainer instance."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()
        assert isinstance(container, IRISContainer)

    def test_has_enterprise_classmethod(self):
        """Test that IRISContainer has enterprise() class method."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, 'enterprise')
        assert callable(IRISContainer.enterprise)

    def test_enterprise_requires_license_key(self):
        """Test that enterprise() requires license_key parameter."""
        from iris_devtester.containers import IRISContainer

        # Should raise ValueError without license_key
        with pytest.raises((ValueError, TypeError)):
            IRISContainer.enterprise()

    def test_enterprise_returns_instance(self):
        """Test that enterprise() returns IRISContainer instance."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.enterprise(license_key="test-license")
        assert isinstance(container, IRISContainer)

    def test_has_get_connection_method(self):
        """Test that IRISContainer has get_connection() method."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()
        assert hasattr(container, 'get_connection')
        assert callable(container.get_connection)

    def test_has_wait_for_ready_method(self):
        """Test that IRISContainer has wait_for_ready() method."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()
        assert hasattr(container, 'wait_for_ready')
        assert callable(container.wait_for_ready)

    def test_has_reset_password_method(self):
        """Test that IRISContainer has reset_password() method."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()
        assert hasattr(container, 'reset_password')
        assert callable(container.reset_password)

    def test_context_manager_support(self):
        """Test that IRISContainer supports context manager protocol."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()
        assert hasattr(container, '__enter__')
        assert hasattr(container, '__exit__')


class TestIRISReadyWaitStrategy:
    """Contract tests for IRISReadyWaitStrategy class."""

    def test_class_exists(self):
        """Test that IRISReadyWaitStrategy class can be imported."""
        from iris_devtester.containers import IRISReadyWaitStrategy

        assert IRISReadyWaitStrategy is not None

    def test_can_instantiate(self):
        """Test that IRISReadyWaitStrategy can be instantiated."""
        from iris_devtester.containers import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy()
        assert strategy is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
