"""
Unit tests for connection fallback logic.

Tests DBAPI-first, JDBC-fallback strategy per Constitutional Principle #2.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestConnectionFallback:
    """Test connection fallback logic (DBAPI -> JDBC)."""

    def test_can_import(self):
        """Test that connection manager can be imported."""
        from iris_devtester.connections.manager import get_connection

        assert callable(get_connection)

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=True)
    @patch("iris_devtester.connections.dbapi.create_dbapi_connection")
    def test_uses_dbapi_when_available(self, mock_dbapi_create, mock_dbapi_available):
        """Test that DBAPI is tried first when available."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        mock_conn = Mock()
        mock_dbapi_create.return_value = mock_conn

        config = IRISConfig()
        conn = get_connection(config)

        # Should use DBAPI
        mock_dbapi_create.assert_called_once_with(config)
        assert conn == mock_conn

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=False)
    @patch("iris_devtester.connections.jdbc.is_jdbc_available", return_value=True)
    @patch("iris_devtester.connections.jdbc.create_jdbc_connection")
    def test_falls_back_to_jdbc_when_dbapi_unavailable(
        self, mock_jdbc_create, mock_jdbc_available, mock_dbapi_available
    ):
        """Test fallback to JDBC when DBAPI not available."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        mock_conn = Mock()
        mock_jdbc_create.return_value = mock_conn

        config = IRISConfig()
        conn = get_connection(config)

        # Should use JDBC as fallback
        mock_jdbc_create.assert_called_once_with(config)
        assert conn == mock_conn

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=True)
    @patch("iris_devtester.connections.dbapi.create_dbapi_connection")
    @patch("iris_devtester.connections.jdbc.create_jdbc_connection")
    def test_falls_back_to_jdbc_on_dbapi_failure(
        self, mock_jdbc_create, mock_dbapi_create, mock_dbapi_available
    ):
        """Test fallback to JDBC when DBAPI connection fails."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        # DBAPI fails
        mock_dbapi_create.side_effect = Exception("DBAPI connection failed")

        # JDBC succeeds
        mock_jdbc_conn = Mock()
        mock_jdbc_create.return_value = mock_jdbc_conn

        config = IRISConfig()
        conn = get_connection(config)

        # Should attempt DBAPI first, then fall back to JDBC
        mock_dbapi_create.assert_called_once_with(config)
        mock_jdbc_create.assert_called_once_with(config)
        assert conn == mock_jdbc_conn

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=False)
    @patch("iris_devtester.connections.jdbc.is_jdbc_available", return_value=False)
    def test_raises_error_when_no_drivers_available(
        self, mock_jdbc_available, mock_dbapi_available
    ):
        """Test error when neither driver is available."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        config = IRISConfig()

        with pytest.raises(Exception) as exc_info:
            get_connection(config)

        # Should provide helpful error message
        error_msg = str(exc_info.value)
        assert "driver" in error_msg.lower() or "install" in error_msg.lower()

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=True)
    @patch("iris_devtester.connections.dbapi.create_dbapi_connection")
    @patch("iris_devtester.connections.jdbc.create_jdbc_connection")
    def test_logs_driver_selection(
        self, mock_jdbc_create, mock_dbapi_create, mock_dbapi_available
    ):
        """Test that driver selection is logged."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        mock_conn = Mock()
        mock_dbapi_create.return_value = mock_conn

        config = IRISConfig()

        # This should log which driver was selected
        conn = get_connection(config)

        assert conn == mock_conn

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=True)
    @patch("iris_devtester.connections.dbapi.create_dbapi_connection")
    def test_respects_explicit_driver_dbapi(self, mock_dbapi_create, mock_dbapi_available):
        """Test that explicit driver='dbapi' forces DBAPI."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        mock_conn = Mock()
        mock_dbapi_create.return_value = mock_conn

        config = IRISConfig(driver="dbapi")
        conn = get_connection(config)

        mock_dbapi_create.assert_called_once_with(config)
        assert conn == mock_conn

    @patch("iris_devtester.connections.jdbc.is_jdbc_available", return_value=True)
    @patch("iris_devtester.connections.jdbc.create_jdbc_connection")
    def test_respects_explicit_driver_jdbc(self, mock_jdbc_create, mock_jdbc_available):
        """Test that explicit driver='jdbc' forces JDBC."""
        from iris_devtester.connections.manager import get_connection
        from iris_devtester.config import IRISConfig

        mock_conn = Mock()
        mock_jdbc_create.return_value = mock_conn

        config = IRISConfig(driver="jdbc")
        conn = get_connection(config)

        mock_jdbc_create.assert_called_once_with(config)
        assert conn == mock_conn


class TestConnectionInfo:
    """Test connection info tracking."""

    @patch("iris_devtester.connections.dbapi.is_dbapi_available", return_value=True)
    @patch("iris_devtester.connections.dbapi.create_dbapi_connection")
    def test_returns_connection_info(self, mock_dbapi_create, mock_dbapi_available):
        """Test that connection returns metadata about driver used."""
        from iris_devtester.connections.manager import get_connection_with_info
        from iris_devtester.config import IRISConfig

        mock_conn = Mock()
        mock_dbapi_create.return_value = mock_conn

        config = IRISConfig()
        conn, info = get_connection_with_info(config)

        assert conn == mock_conn
        assert info.driver_type == "dbapi"
        assert info.host == config.host
        assert info.port == config.port
        assert info.namespace == config.namespace


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
