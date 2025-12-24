"""
Contract tests for password reset verification (Feature 015).

These tests verify that reset_password() properly verifies password changes
via actual connection attempts, not just ObjectScript return codes.

Contract: reset_password() MUST verify password works before returning success.

Expected to FAIL before implementation (TDD red phase).
"""

import logging
import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.utils.password_reset import reset_password


class TestResetVerificationContract:
    """Contract tests for password reset verification (FR-002)."""

    def test_reset_password_verifies_before_success(self, iris_container):
        """
        Contract: reset_password() must verify password works before returning success.

        Validates FR-002: System MUST verify password reset completed successfully
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        # Reset password
        success, message = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="TESTPWD123",
            hostname=config.host,
            port=config.port,
            namespace=config.namespace
        )

        # Contract assertion: If function returns success, connection MUST work
        if success:
            # Attempt connection with new password (try DBAPI first, fall back to iris.connect())
            connection_works = False
            error_message = ""

            try:
                # Try DBAPI first (Constitutional Principle #2)
                import iris.dbapi as dbapi

                conn = dbapi.connect(
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                    username="SuperUser",
                    password="TESTPWD123"
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()[0]
                conn.close()
                connection_works = True

            except ImportError:
                # DBAPI not available, fall back to iris.connect()
                try:
                    import iris
                    conn = iris.connect(
                        hostname=config.host,
                        port=config.port,
                        namespace=config.namespace,
                        username="SuperUser",
                        password="TESTPWD123"
                    )
                    conn.close()
                    connection_works = True
                except Exception as e:
                    error_message = f"iris.connect() failed: {str(e)}"

            except Exception as e:
                error_message = f"DBAPI connection failed: {str(e)}"

            if not connection_works:
                # Contract violated: Function returned success but password doesn't work
                pytest.fail(
                    f"Contract violation: reset_password() returned success but "
                    f"connection failed with: {error_message}\n"
                    f"This violates FR-002: System MUST verify password reset completed successfully"
                )

    def test_reset_password_no_false_positives(self, iris_container, monkeypatch):
        """
        Contract: reset_password() must NOT return success just because ObjectScript succeeded.

        Validates: ObjectScript execution success ≠ password ready for connections
        This is the root cause of the macOS bug.
        """
        container_name = iris_container.get_container_name()

        # Track if verification was attempted
        verification_attempted = {"value": False}

        original_subprocess_run = subprocess.run

        def mock_subprocess_run(*args, **kwargs):
            """Mock docker exec to succeed but don't actually change password."""
            # Let first check command through (container running check)
            if "ps" in str(args):
                return original_subprocess_run(*args, **kwargs)

            # Mock password reset command to succeed
            result = MagicMock()
            result.returncode = 0
            result.stdout = "1\n"  # Modify() returns 1 = success
            result.stderr = ""
            return result

        # Mock DBAPI connection to fail (password not actually changed)
        def mock_dbapi_connect(*args, **kwargs):
            verification_attempted["value"] = True
            raise Exception("Access Denied")

        monkeypatch.setattr("subprocess.run", mock_subprocess_run)

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password
        success, message = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="FAKEPWD"
        )

        # Contract assertion: Function must have attempted verification
        assert verification_attempted["value"], (
            "Contract violation: reset_password() did not attempt password verification"
        )

        # Contract assertion: Function must detect verification failure
        assert not success, (
            "Contract violation: reset_password() returned success "
            "even though password verification failed"
        )
        assert "verification" in message.lower() or "failed" in message.lower(), (
            "Error message should indicate verification failure"
        )

    def test_reset_password_verification_uses_dbapi(self, iris_container, mocker):
        """
        Contract: Verification MUST use actual DBAPI connection, not just command success.

        Validates FR-002: Verification via connection attempt (not just ObjectScript return code)
        """
        container_name = iris_container.get_container_name()

        try:
            import iris.dbapi as dbapi

            # Spy on DBAPI connection attempts
            original_connect = dbapi.connect
            connect_calls = []

            def spy_connect(*args, **kwargs):
                connect_calls.append((args, kwargs))
                return original_connect(*args, **kwargs)

            mocker.patch("iris.dbapi.connect", side_effect=spy_connect)

        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password
        success, message = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="NEWPWD"
        )

        # Contract assertion: DBAPI connection must have been attempted for verification
        assert len(connect_calls) > 0, (
            "Contract violation: reset_password() did not attempt DBAPI connection "
            "for verification (FR-002)"
        )

        # Verify connection was attempted with correct credentials
        # Find the verification call (not the initial container check)
        verification_calls = [
            call for call in connect_calls
            if call[1].get("password") == "NEWPWD"
        ]

        assert len(verification_calls) > 0, (
            "Verification must use the new password"
        )

    def test_reset_password_verification_timeout(self, iris_container, monkeypatch):
        """
        Contract: Verification MUST timeout within 10s (NFR-004).

        Validates NFR-004: Password reset verification MUST complete within 10 seconds
        """
        container_name = iris_container.get_container_name()

        # Mock connection attempts to always fail (simulate extreme latency)
        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            time.sleep(2)  # Simulate slow connection
            raise Exception("Access Denied")  # Simulate password not ready

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Measure time
        start_time = time.time()

        success, message = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="TIMEOUTTEST"
        )

        elapsed = time.time() - start_time

        # Contract assertion: Must timeout within 10s (14s on macOS due to 4s settle delay)
        import platform
        max_time = 14.5 if platform.system() == "Darwin" else 10.5  # Include macOS settle delay (4s) + verification (10s) + grace (0.5s)
        assert elapsed <= max_time, (
            f"Contract violation: Verification took {elapsed:.2f}s, "
            f"exceeds {max_time}s timeout (NFR-004, platform: {platform.system()})"
        )

        # Should return failure after timeout
        assert not success, "Should return failure after timeout"
        assert "timeout" in message.lower() or "verification failed" in message.lower() or "failed" in message.lower(), (
            f"Error message should indicate timeout or verification failure, got: {message}"
        )

    def test_reset_password_verification_attempts_logged(self, iris_container, caplog):
        """
        Contract: Verification attempts MUST be logged for debugging.

        Validates: Diagnostic logging for medical-grade reliability (Constitutional Principle #7)
        """
        container_name = iris_container.get_container_name()

        with caplog.at_level(logging.DEBUG):
            success, message = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="LOGTEST"
            )

        # Contract assertion: Verification attempts must be logged
        log_records = [r.message for r in caplog.records]

        # Should log verification attempts or success
        verification_logs = [
            log for log in log_records
            if "verification" in log.lower() or
               "attempt" in log.lower() or
               "password" in log.lower()
        ]

        assert len(verification_logs) > 0, (
            "Contract violation: Verification attempts not logged (required for debugging)"
        )
