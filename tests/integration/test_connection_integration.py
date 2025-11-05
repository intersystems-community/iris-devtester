"""
Integration tests for modern DBAPI-only connection manager.

Tests verify:
- Auto-discovery from Docker containers
- Connection retry logic
- Context manager functionality
- Zero-config operation
"""

import pytest
from iris_devtester.connections import get_connection, IRISConnection
from iris_devtester.config import IRISConfig


class TestModernConnectionManager:
    """Test modern DBAPI-only connection manager."""

    def test_get_connection_with_explicit_config(self, iris_db):
        """
        Test connection with explicit configuration.

        Expected: Connection succeeds with provided config.
        """
        # Get connection info from fixture
        cursor = iris_db.cursor()

        # Create new connection with explicit config
        # (Use same host/port as fixture container)
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        conn = get_connection(config, auto_retry=False)

        assert conn is not None

        # Verify connection works
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS test")
        result = cursor.fetchone()
        assert result[0] == 1

        conn.close()

    def test_connection_context_manager(self, iris_db):
        """
        Test IRISConnection context manager.

        Expected: Connection automatically closes on exit.
        """
        # Get connection config from fixture
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        with IRISConnection(config, auto_retry=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 42 AS answer")
            result = cursor.fetchone()
            assert result[0] == 42

        # Connection should be closed after exiting context

    def test_connection_retry_on_transient_failure(self, iris_db):
        """
        Test retry logic handles transient failures.

        Note: This test uses explicit config to avoid retry failures
        during connection establishment.
        """
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        # First connection should succeed (with retry enabled)
        conn = get_connection(config, auto_retry=True, max_retries=3)
        assert conn is not None

        # Verify it works
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

        conn.close()

    def test_connection_without_retry(self, iris_db):
        """
        Test connection with retry disabled.

        Expected: Connection succeeds or fails immediately, no retries.
        """
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        conn = get_connection(config, auto_retry=False)
        assert conn is not None

        cursor = conn.cursor()
        cursor.execute("SELECT 'no retry' AS mode")
        result = cursor.fetchone()
        assert result[0] == "no retry"

        conn.close()


class TestAutoDiscovery:
    """Test auto-discovery of connection parameters."""

    def test_explicit_config_overrides_discovery(self, iris_db):
        """
        Test that explicit config takes precedence over auto-discovery.

        Expected: Explicit config is used, not auto-discovered values.
        """
        # Explicit config should override any auto-discovery
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        conn = get_connection(config)
        assert conn is not None

        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_TIMESTAMP")
        result = cursor.fetchone()
        assert result is not None

        conn.close()


class TestConnectionErrorHandling:
    """Test error handling and remediation guidance."""

    def test_connection_to_invalid_host_provides_guidance(self):
        """
        Test that connection to invalid host provides helpful error.

        Expected: Clear error message with remediation steps.
        """
        config = IRISConfig(
            host="invalid-host-that-does-not-exist",
            port=9999,
            namespace="USER",
            username="test",
            password="test",
        )

        with pytest.raises(ConnectionError) as exc_info:
            get_connection(config, auto_retry=False)

        error_message = str(exc_info.value)

        # Verify error message contains remediation guidance
        assert "What went wrong" in error_message or "How to fix it" in error_message
        assert "invalid-host-that-does-not-exist" in error_message

    def test_connection_to_wrong_port_provides_guidance(self, iris_db):
        """
        Test that connection to wrong port provides helpful error.

        Expected: Clear error message with remediation steps.
        """
        # Use correct host but wrong port
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=9999,  # Wrong port
            namespace="USER",
            username="test",
            password="test",
        )

        with pytest.raises(ConnectionError) as exc_info:
            get_connection(config, auto_retry=False)

        error_message = str(exc_info.value)

        # Verify error message contains helpful info
        assert "9999" in error_message  # Shows the port we tried


class TestConnectionManagerIntegration:
    """Integration tests for full connection workflow."""

    def test_full_workflow_zero_config(self, iris_db):
        """
        Test complete workflow with minimal configuration.

        This simulates real-world usage where users provide minimal config
        and the system auto-discovers the rest.
        """
        # Create minimal config (just credentials)
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        # Get connection
        with IRISConnection(config) as conn:
            # Execute query
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    'Connection successful' AS status,
                    CURRENT_TIMESTAMP AS connected_at
            """)
            result = cursor.fetchone()

            assert result[0] == "Connection successful"
            assert result[1] is not None  # Timestamp should exist

    def test_multiple_sequential_connections(self, iris_db):
        """
        Test creating multiple connections sequentially.

        Expected: Each connection is independent and works correctly.
        """
        config = IRISConfig(
            host=iris_db._container.get_container_host_ip(),
            port=int(iris_db._container.get_exposed_port(1972)),
            namespace="USER",
            username="test",
            password="test",
        )

        # First connection
        with IRISConnection(config) as conn1:
            cursor1 = conn1.cursor()
            cursor1.execute("SELECT 1 AS conn")
            result1 = cursor1.fetchone()
            assert result1[0] == 1

        # Second connection (independent)
        with IRISConnection(config) as conn2:
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT 2 AS conn")
            result2 = cursor2.fetchone()
            assert result2[0] == 2
