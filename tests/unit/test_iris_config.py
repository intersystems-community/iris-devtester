"""
Unit tests for IRISConfig model.

Tests MUST FAIL until iris_devtester/config/models.py is implemented.
"""

import pytest


class TestIRISConfig:
    """Test IRISConfig dataclass."""

    def test_can_import(self):
        """Test that IRISConfig can be imported."""
        from iris_devtester.config import IRISConfig

        assert IRISConfig is not None

    def test_default_values(self):
        """Test that IRISConfig has correct default values."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig()
        assert config.host == "localhost"
        assert config.port == 1972
        assert config.namespace == "USER"
        assert config.username == "SuperUser"
        assert config.password == "SYS"
        assert config.driver == "auto"
        assert config.timeout == 30

    def test_explicit_values(self):
        """Test that IRISConfig accepts explicit values."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig(
            host="iris.example.com",
            port=1973,
            namespace="MYAPP",
            username="admin",
            password="secret",
            driver="dbapi",
            timeout=60
        )
        assert config.host == "iris.example.com"
        assert config.port == 1973
        assert config.namespace == "MYAPP"
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.driver == "dbapi"
        assert config.timeout == 60

    def test_port_validation_range(self):
        """Test that port must be in valid range 1-65535."""
        from iris_devtester.config import IRISConfig

        # Valid ports
        config = IRISConfig(port=1)
        assert config.port == 1

        config = IRISConfig(port=65535)
        assert config.port == 65535

        # Invalid ports
        with pytest.raises(ValueError):
            IRISConfig(port=0)

        with pytest.raises(ValueError):
            IRISConfig(port=65536)

    def test_namespace_validation(self):
        """Test that namespace cannot be empty."""
        from iris_devtester.config import IRISConfig

        with pytest.raises(ValueError):
            IRISConfig(namespace="")

    def test_timeout_validation(self):
        """Test that timeout must be positive."""
        from iris_devtester.config import IRISConfig

        with pytest.raises(ValueError):
            IRISConfig(timeout=0)

        with pytest.raises(ValueError):
            IRISConfig(timeout=-1)

    def test_driver_validation(self):
        """Test that driver must be one of allowed values."""
        from iris_devtester.config import IRISConfig

        # Valid drivers
        config = IRISConfig(driver="dbapi")
        assert config.driver == "dbapi"

        config = IRISConfig(driver="jdbc")
        assert config.driver == "jdbc"

        config = IRISConfig(driver="auto")
        assert config.driver == "auto"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
