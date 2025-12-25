"""
Integration tests to validate password reset actually works (Bug #1 verification).

These tests verify that:
1. Password reset function returns success
2. Password is ACTUALLY changed in IRIS
3. Connection works with NEW password
4. Connection fails with OLD password
"""

import pytest
from iris_devtester.containers import IRISContainer
from iris_devtester.utils.password_reset import reset_password


class TestPasswordResetActuallyWorks:
    """Verify password reset actually changes the password in IRIS."""

    def test_password_reset_enables_new_password(self):
        """
        Verify password reset actually changes password in IRIS.

        This test validates Bug #1 fix:
        1. Create container with default password
        2. Reset password to new value
        3. Verify connection works with NEW password
        4. Verify connection FAILS with OLD password

        Regression test for: Bug #1 - Password reset returns success
        but doesn't actually set the password.
        """
        # Create container with default credentials
        with IRISContainer.community(
            username="SuperUser",
            password="SYS",
            namespace="USER"
        ) as iris:
            # Get initial connection (this triggers proactive password reset)
            conn1 = iris.get_connection()
            cursor1 = conn1.cursor()
            cursor1.execute("SELECT 1")
            assert cursor1.fetchone()[0] == 1

            # Now manually reset password to a DIFFERENT value
            new_password = "NEWSYS123"
            container_name = iris.get_container_name()
            config = iris.get_config()

            success, message = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password=new_password,
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
            )

            # Verify reset returned success
            assert success, f"Password reset failed: {message}"
            print(f"✓ Password reset reported success: {message}")

            # CRITICAL: Verify connection works with NEW password
            # Update config to use new password
            iris._config.password = new_password

            # Get new connection with new password
            iris._connection = None  # Force new connection
            conn2 = iris.get_connection()
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT 2")
            result = cursor2.fetchone()

            assert result is not None, "Connection with NEW password failed!"
            assert result[0] == 2
            print(f"✓ Connection works with NEW password")

    def test_password_reset_disables_old_password(self):
        """
        Verify old password no longer works after password reset.

        This is the critical test for Bug #1 - we need to verify
        the password is ACTUALLY changed, not just that the function
        returns success.
        """
        import intersystems_iris.dbapi._DBAPI as dbapi

        # Create container
        with IRISContainer.community(
            username="SuperUser",
            password="SYS",
            namespace="USER"
        ) as iris:
            # Get connection to ensure container is ready
            conn1 = iris.get_connection()
            cursor1 = conn1.cursor()
            cursor1.execute("SELECT 1")
            assert cursor1.fetchone()[0] == 1

            # Reset password to new value
            new_password = "NEWSYS456"
            container_name = iris.get_container_name()
            config = iris.get_config()

            success, message = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password=new_password,
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
            )

            assert success, f"Password reset failed: {message}"

            # CRITICAL: Try to connect with OLD password (should FAIL)
            old_password = "SYS"

            with pytest.raises(Exception) as exc_info:
                # Attempt connection with OLD password
                dbapi.connect(
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                    username="SuperUser",
                    password=old_password,
                )

            # Verify we got authentication error (not connection refused)
            error_msg = str(exc_info.value).lower()
            assert "access denied" in error_msg or "authentication" in error_msg, \
                f"Expected authentication error, got: {error_msg}"

            print(f"✓ Old password correctly rejected: {error_msg}")

            # Verify NEW password works
            conn2 = dbapi.connect(
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
                username="SuperUser",
                password=new_password,
            )

            cursor2 = conn2.cursor()
            cursor2.execute("SELECT 3")
            assert cursor2.fetchone()[0] == 3
            print(f"✓ New password works correctly")

    def test_bug2_config_none_doesnt_crash(self):
        """
        Verify Bug #2 fix: reset_password() doesn't crash when _config is None.

        Before fix: AttributeError: 'NoneType' object has no attribute 'password'
        After fix: reset_password() initializes _config if needed
        """
        with IRISContainer.community() as iris:
            # Ensure container is running
            iris.get_connection()

            # Force _config to None to simulate the bug
            iris._config = None

            # This should NOT crash (Bug #2 fix)
            success = iris.reset_password(
                username="SuperUser",
                new_password="TEST123"
            )

            # Verify reset worked
            assert success, "Password reset failed"

            # Verify _config was initialized
            assert iris._config is not None, "_config should be initialized"
            assert iris._config.password == "TEST123"

            print("✓ Bug #2 fix verified: reset_password() handles None _config")
