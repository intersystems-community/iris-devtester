"""
Stringent Contract tests for password reset verification (Feature 015).

NO MOCKING: These tests verify that reset_password() properly verifies password changes
via actual connection attempts to a real IRIS instance.

Contract: reset_password() MUST verify password works before returning success.
"""

import logging
import time

import pytest

from iris_devtester.utils.dbapi_compat import get_connection
from iris_devtester.utils.password import reset_password


class TestResetVerificationContract:
    """Stringent contract tests for password reset verification (FR-002)."""

    def test_reset_password_verifies_real_connection(self, iris_container):
        """
        Contract: reset_password() must verify password works before returning success.
        NO MOCKING: Verifies against real running IRIS.
        """
        iris = iris_container
        container_name = iris.get_container_name()
        config = iris.get_config()

        # Step 1: Reset password to a known value
        new_pwd = "RealPassword123!"
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password=new_pwd,
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
        )

        # Assertion: Function returns success
        assert result.success, f"Password reset failed on real IRIS: {result.message}"

        # Step 2: Verify we can actually connect and execute SQL (Zero Mocking)
        conn = get_connection(
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
            username="SuperUser",
            password=new_pwd,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        val = cursor.fetchone()[0]
        assert val == 1
        conn.close()

    def test_reset_password_detects_real_failure(self, iris_container):
        """
        Contract: reset_password() must fail if it can't verify the connection.
        NO MOCKING: We use a deliberately wrong port to trigger a real failure.
        """
        iris = iris_container
        container_name = iris.get_container_name()
        config = iris.get_config()

        # Try to reset but point verification to wrong port
        # This will cause a REAL connection failure during verification
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="ShouldNotWork",
            hostname=config.host,
            port=9999,  # WRONG PORT
            namespace=config.namespace,
            timeout=5,
        )

        assert not result.success
        assert "failed" in result.message.lower() or "timeout" in result.message.lower()
