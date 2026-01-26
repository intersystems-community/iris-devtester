"""
Integration tests for REAL WORLD PROBLEMS that iris-devtester solves.

NO MOCKING: These tests demonstrate actual issues solved by iris-devtester
by running against real IRIS containers.
"""

import os
from unittest.mock import patch

import pytest


class TestPgwireConfigProblem:
    """
    REAL PROBLEM: iris-pgwire config discovery issues.
    Tests that IRIS_HOST environment variable is properly read.
    """

    def test_discovers_iris_hostname_from_environment(self, monkeypatch):
        """Test that IRIS_HOST environment variable is properly read."""
        from iris_devtester.config import discover_config

        monkeypatch.setenv("IRIS_HOST", "iris-benchmark")
        monkeypatch.setenv("IRIS_PORT", "1972")

        config = discover_config()
        assert config.host == "iris-benchmark"
        assert config.port == 1972


class TestVectorGraphCallInProblem:
    """
    REAL PROBLEM: iris-vector-graph getting ACCESS_DENIED with licensed IRIS.
    Licensed IRIS container had CallIn service DISABLED by default.
    """

    def test_callin_service_enablement_real_iris(self, iris_container):
        """
        Test that CallIn enablement works on a real container.
        NO MOCKING: Verifies actual service state change.
        """
        # 1. Disable it first to ensure we are testing enablement
        container_name = iris_container.get_container_name()

        # Use standard Security.Services:Modify API to disable
        iris_container.execute_objectscript(
            'Do ##class(Security.Services).Get("%Service_CallIn",.p) '
            'Set p("Enabled")=0 '
            'Do ##class(Security.Services).Modify("%Service_CallIn",.p)'
        )

        # Verify it is disabled
        assert iris_container.check_callin_enabled() is False

        # 2. Enable it using our API
        from iris_devtester.utils.enable_callin import enable_callin_service

        success, msg = enable_callin_service(container_name)
        assert success is True

        # 3. Verify it is now enabled in the real IRIS instance
        assert iris_container.check_callin_enabled() is True


class TestPgwireBenchmarkPasswordExpiration:
    """
    REAL PROBLEM: iris-pgwire benchmarks require manual password unexpiration.
    """

    def test_unexpire_all_passwords_real_iris(self, iris_container):
        """
        Test unexpiring passwords on a real container.
        NO MOCKING: Verifies actual unexpiration.
        """
        from iris_devtester.utils import unexpire_all_passwords

        container_name = iris_container.get_container_name()

        # Execute unexpiration on real container
        success, message = unexpire_all_passwords(container_name)

        assert success is True
        assert container_name in message
        # Output should contain the expected success indicator
        assert "unexpired" in message.lower() or "UNEXPIRED" in message


class TestDBAPIFirstJDBCFallbackInAction:
    """
    REAL PROBLEM: Connections hang when DBAPI doesn't work.
    """

    def test_uses_dbapi_when_available(self, iris_container):
        """Test DBAPI is tried first with REAL connection."""
        from iris_devtester.connections import get_connection
        from iris_devtester.connections.dbapi import is_dbapi_available

        config = iris_container.get_config()
        conn = get_connection(config)

        assert conn is not None
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
        conn.close()
        assert is_dbapi_available() is True

    def test_falls_back_to_jdbc_when_dbapi_fails(self, iris_container):
        """Test automatic fallback to JDBC when driver is forced."""
        from iris_devtester.connections import get_connection
        from iris_devtester.connections.jdbc import is_jdbc_available

        config = iris_container.get_config()
        config.driver = "jdbc"

        if is_jdbc_available():
            conn = get_connection(config)
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
            conn.close()
        else:
            pytest.skip("JDBC not available in this environment")
