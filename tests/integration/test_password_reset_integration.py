"""
Integration tests for reset_password() function.

These tests verify that reset_password() ACTUALLY sets the password,
not just returns success. This is the critical bug fix for Feature 007.

CRITICAL: These tests MUST FAIL initially (TDD red phase) to prove they
detect the bug. After the fix (T006-T007), they should PASS (TDD green).

Tests verify:
- T001: Password is ACTUALLY set (connection succeeds with new password)
- T002: DBAPI connection succeeds with new password
- T003: PasswordNeverExpires=1 is set correctly
- T004: Function is idempotent (safe to call multiple times)
"""

import pytest
from iris_devtester.utils.password_reset import reset_password


class TestResetPasswordIntegration:
    """Integration tests for reset_password() function."""

    def test_reset_password_actually_sets_password(self, iris_db):
        """
        T001: Verify password is ACTUALLY set (not just function returning success).

        This is the CRITICAL test that exposes the bug:
        - Current bug: reset_password() returns (True, "success") but password NOT set
        - Fixed: reset_password() returns (True, "success") AND password IS set

        Expected (TDD red): ❌ FAIL - password not actually set
        Expected (TDD green): ✅ PASS - password actually set
        """
        # Arrange - get container info
        container_name = iris_db._container.get_wrapped_container().name
        new_password = "TESTPWD123"

        # Get actual exposed port from testcontainers
        host = iris_db._container.get_container_host_ip()
        port = int(iris_db._container.get_exposed_port(1972))

        # Act - reset password (must provide correct host/port for verification)
        success, msg = reset_password(
            container_name=container_name,
            username="_SYSTEM",
            new_password=new_password,
            hostname=host,
            port=port
        )

        # Assert - function reports success
        assert success, f"reset_password() returned failure: {msg}"
        assert "success" in msg.lower(), f"Success message not found: {msg}"

        # CRITICAL: Verify password ACTUALLY changed by attempting connection
        # This is what the current bug fails - password NOT actually set
        from iris_devtester.utils.dbapi_compat import get_connection

        # Try to connect with NEW password (host/port already retrieved above)
        conn = get_connection(
            hostname=host,
            port=port,
            namespace="USER",
            username="_SYSTEM",
            password=new_password
        )

        # Verify connection works by executing query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS test")
        result = cursor.fetchone()
        assert result[0] == 1, "Query failed - password not actually set"

        conn.close()

    def test_reset_password_connection_succeeds(self, iris_db):
        """
        T002: Verify DBAPI connection succeeds with new password.

        This test focuses specifically on the connection succeeding,
        which is what users reported failing ("Access Denied" error).

        Expected (TDD red): ❌ FAIL - connection fails with "Access Denied"
        Expected (TDD green): ✅ PASS - connection succeeds
        """
        # Arrange
        container_name = iris_db._container.get_wrapped_container().name
        new_password = "NEWPASS"

        # Get actual exposed port from testcontainers
        host = iris_db._container.get_container_host_ip()
        port = int(iris_db._container.get_exposed_port(1972))

        # Act - reset password (must provide correct host/port for verification)
        success, msg = reset_password(
            container_name=container_name,
            username="_SYSTEM",
            new_password=new_password,
            hostname=host,
            port=port
        )

        # Assert - function reports success
        assert success, f"reset_password() failed: {msg}"

        # CRITICAL: Verify connection with new password succeeds
        from iris_devtester.utils.dbapi_compat import get_connection

        # This should succeed if password was actually set
        conn = get_connection(
            hostname=host,
            port=port,
            namespace="USER",
            username="_SYSTEM",
            password=new_password
        )

        # Execute simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

        conn.close()

    def test_reset_password_sets_password_never_expires(self, iris_db):
        """
        T003: Verify PasswordNeverExpires=1 is set correctly.

        Current bug uses ChangePassword=0 (wrong flag).
        Fixed version should use PasswordNeverExpires=1.

        Expected (TDD red): ❌ FAIL - PasswordNeverExpires not set
        Expected (TDD green): ✅ PASS - PasswordNeverExpires=1
        """
        # Arrange
        container_name = iris_db._container.get_wrapped_container().name
        new_password = "PWD123"

        # Get actual exposed port from testcontainers
        host = iris_db._container.get_container_host_ip()
        port = int(iris_db._container.get_exposed_port(1972))

        # Act - reset password (must provide correct host/port for verification)
        success, msg = reset_password(
            container_name=container_name,
            username="_SYSTEM",
            new_password=new_password,
            hostname=host,
            port=port
        )

        # Assert - function reports success
        assert success, f"reset_password() failed: {msg}"

        # CRITICAL: Query Security.Users to verify PasswordNeverExpires=1
        # Use docker exec to run ObjectScript query
        import subprocess

        query_cmd = [
            "docker", "exec", "-i", container_name, "bash", "-c",
            'echo "set sc = ##class(Security.Users).Get(\\"_SYSTEM\\",.prop) write prop(\\"PasswordNeverExpires\\")" | iris session IRIS -U %SYS'
        ]

        result = subprocess.run(
            query_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Verify PasswordNeverExpires=1 in output
        assert "1" in result.stdout, (
            f"PasswordNeverExpires not set to 1. "
            f"Current bug uses ChangePassword=0 instead of PasswordNeverExpires=1. "
            f"Output: {result.stdout}"
        )

    def test_reset_password_idempotent(self, iris_db):
        """
        T004: Verify function is idempotent (safe to call multiple times).

        Should be able to call reset_password() multiple times with same password
        without errors or side effects.

        Expected (TDD red): ❌ MAY FAIL depending on bug behavior
        Expected (TDD green): ✅ PASS - all calls succeed
        """
        # Arrange
        container_name = iris_db._container.get_wrapped_container().name
        new_password = "SAMEPWD"

        # Get actual exposed port from testcontainers
        host = iris_db._container.get_container_host_ip()
        port = int(iris_db._container.get_exposed_port(1972))

        # Act - call reset_password() 3 times with same password
        for i in range(3):
            success, msg = reset_password(
                container_name=container_name,
                username="_SYSTEM",
                new_password=new_password,
                hostname=host,
                port=port
            )

            # Assert each call succeeds
            assert success, f"Call {i+1} failed: {msg}"

        # CRITICAL: Verify password still works after 3 calls
        from iris_devtester.utils.dbapi_compat import get_connection

        host = iris_db._container.get_container_host_ip()
        port = int(iris_db._container.get_exposed_port(1972))

        conn = get_connection(
            hostname=host,
            port=port,
            namespace="USER",
            username="_SYSTEM",
            password=new_password
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1, "Password broken after multiple reset calls"

        conn.close()
