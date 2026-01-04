"""
Contract tests for Connection Management API.

These tests validate the public API interface defined in:
specs/001-implement-iris-devtester/contracts/connection-api.md

These tests MUST FAIL until implementation is complete.
"""


import pytest

pytestmark = pytest.mark.contract


class TestGetIRISConnection:
    """Contract tests for get_iris_connection() function."""

    def test_function_exists(self):
        """Test that get_iris_connection function can be imported."""
        from iris_devtester.connections import get_iris_connection

        assert callable(get_iris_connection)

    def test_signature_zero_config(self):
        """Test that get_iris_connection works with zero config."""
        from iris_devtester.connections import get_iris_connection

        # This should work (will fail until implemented)
        conn = get_iris_connection()
        assert conn is not None

    def test_signature_explicit_config(self):
        """Test that get_iris_connection accepts IRISConfig."""
        from iris_devtester.connections import get_iris_connection
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972)
        conn = get_iris_connection(config)
        assert conn is not None

    def test_signature_keyword_args(self):
        """Test that get_iris_connection accepts keyword arguments."""
        from iris_devtester.connections import get_iris_connection

        conn = get_iris_connection(
            auto_remediate=True,
            retry_attempts=3,
            retry_delay=1.0
        )
        assert conn is not None


class TestResetPasswordIfNeeded:
    """Contract tests for reset_password_if_needed() function."""

    def test_function_exists(self):
        """Test that reset_password_if_needed function can be imported."""
        from iris_devtester.connections import reset_password_if_needed

        assert callable(reset_password_if_needed)

    def test_signature(self):
        """Test that reset_password_if_needed accepts required parameters."""
        from iris_devtester.connections import reset_password_if_needed
        from iris_devtester.config import IRISConfig

        config = IRISConfig()
        result = reset_password_if_needed(config)
        assert hasattr(result, 'success')

    def test_returns_password_reset_result(self):
        """Test that function returns PasswordResetResult."""
        from iris_devtester.connections import reset_password_if_needed
        from iris_devtester.config import IRISConfig
        from iris_devtester.testing.models import PasswordResetResult

        config = IRISConfig()
        result = reset_password_if_needed(config)
        assert isinstance(result, PasswordResetResult)


class TestTestConnection:
    """Contract tests for test_connection() function."""

    def test_function_exists(self):
        """Test that test_connection function can be imported."""
        from iris_devtester.connections import test_connection

        assert callable(test_connection)

    def test_signature(self):
        """Test that test_connection accepts config parameter."""
        from iris_devtester.connections import test_connection
        from iris_devtester.config import IRISConfig

        config = IRISConfig()
        result = test_connection(config)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_tuple(self):
        """Test that test_connection returns (bool, Optional[str])."""
        from iris_devtester.connections import test_connection
        from iris_devtester.config import IRISConfig

        config = IRISConfig()
        success, error_msg = test_connection(config)
        assert isinstance(success, bool)
        assert error_msg is None or isinstance(error_msg, str)


class TestIRISConnectionManager:
    """Contract tests for IRISConnectionManager class."""

    def test_class_exists(self):
        """Test that IRISConnectionManager class can be imported."""
        from iris_devtester.connections import IRISConnectionManager

        assert IRISConnectionManager is not None

    def test_init_zero_config(self):
        """Test that IRISConnectionManager can be instantiated with zero config."""
        from iris_devtester.connections import IRISConnectionManager

        manager = IRISConnectionManager()
        assert manager is not None

    def test_init_with_config(self):
        """Test that IRISConnectionManager accepts IRISConfig."""
        from iris_devtester.connections import IRISConnectionManager
        from iris_devtester.config import IRISConfig

        config = IRISConfig()
        manager = IRISConnectionManager(config)
        assert manager is not None

    def test_has_get_connection_method(self):
        """Test that IRISConnectionManager has get_connection method."""
        from iris_devtester.connections import IRISConnectionManager

        manager = IRISConnectionManager()
        assert hasattr(manager, 'get_connection')
        assert callable(manager.get_connection)

    def test_has_close_all_method(self):
        """Test that IRISConnectionManager has close_all method."""
        from iris_devtester.connections import IRISConnectionManager

        manager = IRISConnectionManager()
        assert hasattr(manager, 'close_all')
        assert callable(manager.close_all)

    def test_context_manager_support(self):
        """Test that IRISConnectionManager supports context manager protocol."""
        from iris_devtester.connections import IRISConnectionManager

        manager = IRISConnectionManager()
        assert hasattr(manager, '__enter__')
        assert hasattr(manager, '__exit__')

    def test_has_config_attribute(self):
        """Test that IRISConnectionManager has config attribute."""
        from iris_devtester.connections import IRISConnectionManager

        manager = IRISConnectionManager()
        assert hasattr(manager, 'config')

    def test_has_driver_type_attribute(self):
        """Test that IRISConnectionManager has driver_type attribute."""
        from iris_devtester.connections import IRISConnectionManager

        manager = IRISConnectionManager()
        assert hasattr(manager, 'driver_type')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
