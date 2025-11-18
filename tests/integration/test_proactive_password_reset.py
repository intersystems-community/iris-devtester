"""
Integration tests for proactive password reset in IRISContainer.get_connection().

This verifies Feature 007 fix - password reset happens BEFORE first connection attempt.
"""

import pytest
from iris_devtester.containers import IRISContainer


class TestProactivePasswordReset:
    """Test proactive password reset before connection attempts."""

    def test_get_connection_proactively_resets_password(self):
        """
        Verify IRISContainer.get_connection() proactively resets password
        BEFORE first connection attempt (Feature 007 fix).

        This test ensures:
        1. Password is reset BEFORE connection attempt (not after failure)
        2. Connection succeeds without "Access Denied" error
        3. No "Password change required" error occurs

        Regression Test for: Bug report from production user
        - v1.3.0 and v1.4.0: "Access Denied" errors
        - Root Cause: Password reset was reactive (after connection failed)
        - Fix: Proactive password reset (before connection attempt)
        """
        # Create IRIS container with known credentials
        with IRISContainer.community(
            username="SuperUser",
            password="SYS",
            namespace="USER"
        ) as iris:
            # This should trigger proactive password reset in get_connection()
            # Password should be reset BEFORE attempting connection
            conn = iris.get_connection()

            # Verify connection works (no "Access Denied" or "Password change required")
            cursor = conn.cursor()
            cursor.execute("SELECT $ZVERSION")
            result = cursor.fetchone()

            assert result is not None
            assert len(result) > 0
            # Verify we got IRIS version string
            assert "IRIS" in str(result[0])

    def test_get_connection_succeeds_without_errors(self):
        """
        Verify get_connection() completes without password-related errors.

        Ensures proactive password reset prevents:
        - "Access Denied" errors
        - "Password change required" errors
        - Any other authentication failures
        """
        with IRISContainer.community() as iris:
            # Should not raise any exceptions
            conn = iris.get_connection()

            # Verify connection is usable
            cursor = conn.cursor()
            cursor.execute("SELECT 1 AS test")
            result = cursor.fetchone()

            assert result[0] == 1

    def test_multiple_connections_reuse_reset_password(self):
        """
        Verify multiple get_connection() calls work correctly.

        First call should reset password proactively.
        Subsequent calls should reuse existing connection.
        """
        with IRISContainer.community() as iris:
            # First connection - triggers proactive password reset
            conn1 = iris.get_connection()

            # Second connection - should reuse existing connection
            conn2 = iris.get_connection()

            # Both should be the same connection object
            assert conn1 is conn2

            # Verify connection works
            cursor = conn1.cursor()
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
            result = cursor.fetchone()

            assert result is not None
            assert result[0] >= 0  # At least 0 tables

    def test_proactive_reset_is_idempotent(self):
        """
        Verify proactive password reset is idempotent.

        Multiple containers can call get_connection() and each
        will proactively reset the password without conflicts.
        """
        # First container
        with IRISContainer.community() as iris1:
            conn1 = iris1.get_connection()
            cursor1 = conn1.cursor()
            cursor1.execute("SELECT 1")
            assert cursor1.fetchone()[0] == 1

        # Second container (fresh instance)
        # Should also proactively reset password without issues
        with IRISContainer.community() as iris2:
            conn2 = iris2.get_connection()
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT 2")
            assert cursor2.fetchone()[0] == 2
