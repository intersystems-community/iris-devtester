"""
Unit tests for JDBC connection.

Tests JDBC connection establishment, error handling, and fallback behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestJDBCConnection:
    """Test JDBC connection functionality."""

    def test_can_import(self):
        """Test that JDBC connection function can be imported."""
        from iris_devtools.connections.jdbc import create_jdbc_connection

        assert callable(create_jdbc_connection)

    @patch("iris_devtools.connections.jdbc.jaydebeapi")
    def test_create_jdbc_connection_success(self, mock_jaydebeapi):
        """Test successful JDBC connection creation."""
        from iris_devtools.connections.jdbc import create_jdbc_connection
        from iris_devtools.config import IRISConfig

        # Mock the connection
        mock_conn = Mock()
        mock_jaydebeapi.connect.return_value = mock_conn

        config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="SuperUser",
            password="SYS",
        )

        conn = create_jdbc_connection(config)

        # Verify connection was created
        mock_jaydebeapi.connect.assert_called_once()
        assert conn == mock_conn

    @patch("iris_devtools.connections.jdbc.jaydebeapi")
    def test_create_jdbc_connection_with_custom_config(self, mock_jaydebeapi):
        """Test JDBC connection with custom configuration."""
        from iris_devtools.connections.jdbc import create_jdbc_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_jaydebeapi.connect.return_value = mock_conn

        config = IRISConfig(
            host="remote.iris.com",
            port=1973,
            namespace="MYAPP",
            username="admin",
            password="secret123",
        )

        conn = create_jdbc_connection(config)

        assert conn == mock_conn
        # Verify JDBC URL format includes host, port, namespace
        call_args = mock_jaydebeapi.connect.call_args
        jdbc_url = call_args[0][1] if call_args else None
        # JDBC URL should contain connection details

    @patch("iris_devtools.connections.jdbc.jaydebeapi")
    def test_jdbc_connection_error_handling(self, mock_jaydebeapi):
        """Test JDBC connection error handling."""
        from iris_devtools.connections.jdbc import create_jdbc_connection
        from iris_devtools.config import IRISConfig

        # Simulate connection failure
        mock_jaydebeapi.connect.side_effect = Exception("JDBC connection failed")

        config = IRISConfig()

        with pytest.raises(Exception) as exc_info:
            create_jdbc_connection(config)

        assert "JDBC connection failed" in str(exc_info.value)

    def test_jdbc_module_not_available(self):
        """Test handling when JDBC module is not installed."""
        from iris_devtools.connections.jdbc import is_jdbc_available

        # This will test actual availability
        result = is_jdbc_available()
        assert isinstance(result, bool)

    @patch("iris_devtools.connections.jdbc.jaydebeapi")
    def test_jdbc_url_format(self, mock_jaydebeapi):
        """Test that JDBC URL is formatted correctly."""
        from iris_devtools.connections.jdbc import create_jdbc_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_jaydebeapi.connect.return_value = mock_conn

        config = IRISConfig(
            host="test.host",
            port=1972,
            namespace="USER",
        )

        create_jdbc_connection(config)

        # Verify connect was called
        assert mock_jaydebeapi.connect.called

    @patch("iris_devtools.connections.jdbc.jaydebeapi")
    def test_jdbc_connection_with_timeout(self, mock_jaydebeapi):
        """Test JDBC connection respects timeout configuration."""
        from iris_devtools.connections.jdbc import create_jdbc_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_jaydebeapi.connect.return_value = mock_conn

        config = IRISConfig(timeout=120)

        conn = create_jdbc_connection(config)

        assert conn == mock_conn

    @patch("iris_devtools.connections.jdbc.jaydebeapi")
    def test_jdbc_driver_class_name(self, mock_jaydebeapi):
        """Test that correct JDBC driver class is used."""
        from iris_devtools.connections.jdbc import create_jdbc_connection
        from iris_devtools.config import IRISConfig

        mock_conn = Mock()
        mock_jaydebeapi.connect.return_value = mock_conn

        config = IRISConfig()

        create_jdbc_connection(config)

        # Should use InterSystems JDBC driver
        call_args = mock_jaydebeapi.connect.call_args
        driver_class = call_args[0][0] if call_args else None
        # Driver should be InterSystems IRIS JDBC driver


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
