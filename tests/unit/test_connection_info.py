"""
Unit tests for ConnectionInfo model.

Tests MUST FAIL until iris_devtester/connections/models.py is implemented.
"""

import pytest
from datetime import datetime


class TestConnectionInfo:
    """Test ConnectionInfo dataclass."""

    def test_can_import(self):
        """Test that ConnectionInfo can be imported."""
        from iris_devtester.connections.models import ConnectionInfo

        assert ConnectionInfo is not None

    def test_required_fields(self):
        """Test that ConnectionInfo requires certain fields."""
        from iris_devtester.connections.models import ConnectionInfo

        info = ConnectionInfo(
            driver_type="dbapi",
            host="localhost",
            port=1972,
            namespace="USER",
            username="SuperUser"
        )
        assert info.driver_type == "dbapi"
        assert info.host == "localhost"
        assert info.port == 1972
        assert info.namespace == "USER"
        assert info.username == "SuperUser"

    def test_default_fields(self):
        """Test that ConnectionInfo has default values for optional fields."""
        from iris_devtester.connections.models import ConnectionInfo

        info = ConnectionInfo(
            driver_type="dbapi",
            host="localhost",
            port=1972,
            namespace="USER",
            username="SuperUser"
        )
        assert isinstance(info.connection_time, datetime)
        assert info.is_pooled == False
        assert info.container_id is None

    def test_optional_fields(self):
        """Test that ConnectionInfo accepts optional fields."""
        from iris_devtester.connections.models import ConnectionInfo

        now = datetime.now()
        info = ConnectionInfo(
            driver_type="jdbc",
            host="iris.example.com",
            port=1973,
            namespace="MYAPP",
            username="admin",
            connection_time=now,
            is_pooled=True,
            container_id="abc123"
        )
        assert info.connection_time == now
        assert info.is_pooled == True
        assert info.container_id == "abc123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
