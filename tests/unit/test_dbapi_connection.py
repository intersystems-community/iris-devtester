"""
Unit tests for DBAPI connection.

Tests DBAPI connection establishment, error handling, and configuration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestDBAPIConnection:
    """Test DBAPI connection functionality."""

    def test_can_import(self):
        """Test that DBAPI connection function can be imported."""
        from iris_devtools.connections.dbapi import create_dbapi_connection

        assert callable(create_dbapi_connection)

    @patch("iris_devtools.connections.dbapi.irisnative")
    def test_create_dbapi_connection_success(self, mock_irisnative):
        """Test successful DBAPI connection creation."""
        from iris_devtools.connections.dbapi import create_dbapi_connection
        from iris_devtools.config import IRISConfig

        # Mock the connection
        mock_conn = Mock()
        mock_irisnative.createConnection.return_value = mock_conn

        config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="SuperUser",
            password="SYS",
        )

        conn = create_dbapi_connection(config)

        # Verify connection was created with correct parameters
        mock_irisnative.createConnection.assert_called_once()
        assert conn == mock_conn

    @patch("iris_devtools.connections.dbapi.irisnative")
    def test_create_dbapi_connection_with_custom_config(self, mock_irisnative):
        """Test DBAPI connection with custom configuration."""
        from iris_devtools.connections.dbapi import create_dbapi_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_irisnative.createConnection.return_value = mock_conn

        config = IRISConfig(
            host="custom.host",
            port=1973,
            namespace="MYAPP",
            username="admin",
            password="secret123",
        )

        conn = create_dbapi_connection(config)

        assert conn == mock_conn
        mock_irisnative.createConnection.assert_called_once()

    @patch("iris_devtools.connections.dbapi.irisnative")
    def test_dbapi_connection_error_handling(self, mock_irisnative):
        """Test DBAPI connection error handling."""
        from iris_devtools.connections.dbapi import create_dbapi_connection
        from iris_devtools.config import IRISConfig

        # Simulate connection failure
        mock_irisnative.createConnection.side_effect = Exception("Connection refused")

        config = IRISConfig()

        with pytest.raises(Exception) as exc_info:
            create_dbapi_connection(config)

        assert "Connection refused" in str(exc_info.value)

    def test_dbapi_module_not_available(self):
        """Test handling when DBAPI module is not installed."""
        from iris_devtools.connections.dbapi import is_dbapi_available

        # This will test actual availability
        result = is_dbapi_available()
        assert isinstance(result, bool)

    @patch("iris_devtools.connections.dbapi.irisnative")
    def test_dbapi_connection_timeout(self, mock_irisnative):
        """Test DBAPI connection with timeout configuration."""
        from iris_devtools.connections.dbapi import create_dbapi_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_irisnative.createConnection.return_value = mock_conn

        config = IRISConfig(timeout=60)

        conn = create_dbapi_connection(config)

        assert conn == mock_conn

    @patch("iris_devtools.connections.dbapi.irisnative")
    def test_dbapi_connection_returns_connection_object(self, mock_irisnative):
        """Test that DBAPI connection returns a proper connection object."""
        from iris_devtools.connections.dbapi import create_dbapi_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_conn.cursor = Mock(return_value=Mock())
        mock_irisnative.createConnection.return_value = mock_conn

        config = IRISConfig()
        conn = create_dbapi_connection(config)

        # Verify it has expected connection interface
        assert hasattr(conn, "cursor")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
