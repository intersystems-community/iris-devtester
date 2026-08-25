"""
Unit tests for iris_devtester.utils.password module.

Tests cover:
- PasswordResult dataclass validation
- VerificationConfig defaults
- Password change detection
- Password verification with retry/backoff
- Password reset via Docker
- Password unexpiration
- Error handling and recovery
"""

import subprocess
import sys
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from iris_devtester.utils.password import (
    PasswordResult,
    VerificationConfig,
    detect_password_change_required,
    reset_password,
    reset_password_if_needed,
    unexpire_all_passwords,
    unexpire_passwords_for_containers,
    verify_password,
)


class TestPasswordResult:
    """Test PasswordResult dataclass validation and behavior."""

    def test_success_without_error_type(self):
        """success=True with error_type=None should be valid."""
        result = PasswordResult(success=True, message="OK")
        assert result.success is True
        assert result.message == "OK"
        assert result.error_type is None

    def test_success_with_error_type_raises_error(self):
        """success=True with error_type != None should raise ValueError."""
        with pytest.raises(ValueError, match="error_type must be None when success=True"):
            PasswordResult(success=True, message="OK", error_type="timeout")

    def test_failure_without_error_type_sets_unknown(self):
        """success=False with error_type=None should auto-set to 'unknown'."""
        result = PasswordResult(success=False, message="Failed")
        assert result.success is False
        assert result.error_type == "unknown"

    def test_failure_with_error_type(self):
        """success=False with explicit error_type should be preserved."""
        result = PasswordResult(
            success=False, message="Failed", error_type="access_denied"
        )
        assert result.success is False
        assert result.error_type == "access_denied"

    def test_negative_attempts_raises_error(self):
        """attempts < 0 should raise ValueError."""
        with pytest.raises(ValueError, match="attempts must be >= 0"):
            PasswordResult(success=True, message="OK", attempts=-1)

    def test_negative_elapsed_seconds_raises_error(self):
        """elapsed_seconds < 0 should raise ValueError."""
        with pytest.raises(ValueError, match="elapsed_seconds must be >= 0"):
            PasswordResult(success=True, message="OK", elapsed_seconds=-1.0)

    def test_zero_attempts_valid(self):
        """attempts=0 should be valid."""
        result = PasswordResult(success=True, message="OK", attempts=0)
        assert result.attempts == 0

    def test_zero_elapsed_seconds_valid(self):
        """elapsed_seconds=0 should be valid."""
        result = PasswordResult(success=True, message="OK", elapsed_seconds=0.0)
        assert result.elapsed_seconds == 0.0

    def test_tuple_unpacking_forward_compat(self):
        """__iter__ should support backward-compat tuple unpacking."""
        result = PasswordResult(success=True, message="Success message")
        success, message = result
        assert success is True
        assert message == "Success message"

    def test_all_fields_set(self):
        """All fields should be settable and retrievable."""
        result = PasswordResult(
            success=True,
            message="Test message",
            attempts=3,
            elapsed_seconds=2.5,
            error_type=None,
            container_name="test_iris",
            username="test_user",
        )
        assert result.success is True
        assert result.message == "Test message"
        assert result.attempts == 3
        assert result.elapsed_seconds == 2.5
        assert result.error_type is None
        assert result.container_name == "test_iris"
        assert result.username == "test_user"


class TestVerificationConfig:
    """Test VerificationConfig dataclass."""

    def test_default_values(self):
        """Default values should be reasonable for macOS Docker."""
        config = VerificationConfig()
        assert config.max_retries == 5
        assert config.initial_backoff_ms == 1000
        assert config.timeout_ms == 10000
        assert config.exponential_backoff is True

    def test_custom_values(self):
        """Custom values should be honored."""
        config = VerificationConfig(
            max_retries=10,
            initial_backoff_ms=500,
            timeout_ms=20000,
            exponential_backoff=False,
        )
        assert config.max_retries == 10
        assert config.initial_backoff_ms == 500
        assert config.timeout_ms == 20000
        assert config.exponential_backoff is False


class TestDetectPasswordChangeRequired:
    """Test password change detection logic."""

    def test_password_change_required(self):
        """'password change required' should return True (case insensitive)."""
        assert detect_password_change_required("Password Change Required") is True
        assert detect_password_change_required("PASSWORD CHANGE REQUIRED") is True
        assert detect_password_change_required("password change required") is True

    def test_change_password_indicator(self):
        """'change password' should return True."""
        assert detect_password_change_required("Please change password") is True
        assert detect_password_change_required("CHANGE PASSWORD") is True

    def test_required_to_change_password_indicator(self):
        """'required to change password' should return True."""
        assert detect_password_change_required("You are required to change password") is True

    def test_password_expired_indicator(self):
        """'password expired' should return True."""
        assert detect_password_change_required("Your password expired") is True
        assert detect_password_change_required("PASSWORD EXPIRED") is True

    def test_sqlcode_853_indicator(self):
        """'<853>' (SQLCODE for password change required) should return True."""
        assert detect_password_change_required("<853>") is True
        assert detect_password_change_required("Error: <853>") is True

    def test_access_denied_not_detected(self):
        """'access denied' should return False."""
        assert detect_password_change_required("access denied") is False

    def test_connection_refused_not_detected(self):
        """'connection refused' should return False."""
        assert detect_password_change_required("connection refused") is False

    def test_empty_message(self):
        """Empty message should return False."""
        assert detect_password_change_required("") is False

    def test_unrelated_message(self):
        """Unrelated error message should return False."""
        assert detect_password_change_required("Network timeout") is False


class TestVerifyPassword:
    """Test password verification with retry/backoff."""

    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_success_on_first_attempt(self, mock_time):
        """Successful connection on first attempt should return success."""
        mock_time.return_value = 100.0  # First call returns start time

        with patch("iris.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            result = verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="pass",
            )

            assert result.success is True
            assert "verified" in result.message.lower()
            assert result.attempts == 1
            mock_connect.assert_called_once()
            mock_conn.close.assert_called_once()

    @patch("iris_devtester.utils.password.time.sleep")
    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_retry_with_backoff(self, mock_time, mock_sleep):
        """Failed connections should retry with exponential backoff."""
        # Simulate time progression: 0, 1, 2, 3, 4, 5 seconds
        mock_time.side_effect = [0, 1, 2, 3, 4, 5]

        with patch("iris.connect") as mock_connect:
            # Fail first 2 times, succeed on 3rd
            mock_connect.side_effect = [
                Exception("Connection refused"),
                Exception("Connection refused"),
                MagicMock(),  # Success
            ]

            result = verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="pass",
                config=VerificationConfig(max_retries=5),
            )

            assert result.success is True
            assert result.attempts == 3
            assert mock_connect.call_count == 3
            # Should have slept twice (between attempts 1-2 and 2-3)
            assert mock_sleep.call_count == 2

    @patch("iris_devtester.utils.password.time.sleep")
    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_all_retries_exhausted(self, mock_time, mock_sleep):
        """Exhausting all retries should return failure."""
        # Time always returns 0 (no timeout)
        mock_time.return_value = 0

        with patch("iris.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")

            result = verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="pass",
                config=VerificationConfig(max_retries=3),
            )

            assert result.success is False
            assert result.attempts == 3
            assert result.error_type == "connection_refused"
            assert "Connection refused" in result.message
            # Should have slept 2 times (between attempts)
            assert mock_sleep.call_count == 2

    def test_verify_password_timeout_exceeded(self):
        """Exceeding timeout_ms should return timeout error."""
        # Use a mock that tracks time progression
        time_values = [0, 1, 11, 11]  # start, first fail check, timeout check, final elapsed
        time_iter = iter(time_values)

        def mock_time_func():
            return next(time_iter)

        with patch("iris_devtester.utils.password.time.time", side_effect=mock_time_func):
            with patch("iris.connect") as mock_connect:
                mock_connect.side_effect = Exception("Connection refused")

                result = verify_password(
                    hostname="localhost",
                    port=1972,
                    namespace="USER",
                    username="test",
                    password="pass",
                    config=VerificationConfig(timeout_ms=10000),
                )

                assert result.success is False
                assert result.error_type == "timeout"
                assert "Timeout" in result.message

    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_access_denied_error_type(self, mock_time):
        """'access denied' error should map to access_denied error_type."""
        mock_time.return_value = 0

        with patch("iris.connect") as mock_connect:
            mock_connect.side_effect = Exception("access denied")

            result = verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="wrong",
                config=VerificationConfig(max_retries=1),
            )

            assert result.success is False
            assert result.error_type == "access_denied"

    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_timeout_error_type(self, mock_time):
        """'timeout' error should map to timeout error_type."""
        mock_time.return_value = 0

        with patch("iris.connect") as mock_connect:
            mock_connect.side_effect = Exception("timeout")

            result = verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="pass",
                config=VerificationConfig(max_retries=1),
            )

            assert result.success is False
            assert result.error_type == "timeout"

    @patch("iris_devtester.utils.password.time.sleep")
    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_fallback_to_dbapi_on_import_error(self, mock_time, mock_sleep):
        """If iris import fails, should fallback to create_dbapi_connection."""
        mock_time.return_value = 0

        # Mock the iris module to not be available
        with patch.dict("sys.modules", {"iris": None}):
            with patch("iris_devtester.connections.dbapi.create_dbapi_connection") as mock_dbapi:
                mock_conn = MagicMock()
                mock_dbapi.return_value = mock_conn

                result = verify_password(
                    hostname="localhost",
                    port=1972,
                    namespace="USER",
                    username="test",
                    password="pass",
                )

                assert result.success is True
                mock_dbapi.assert_called_once()
                mock_conn.close.assert_called_once()

    @patch("iris_devtester.utils.password.time.sleep")
    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_exponential_backoff_calculation(self, mock_time, mock_sleep):
        """Exponential backoff should double each retry: 1s, 2s, 4s..."""
        mock_time.return_value = 0

        with patch("iris.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")

            verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="pass",
                config=VerificationConfig(
                    max_retries=4,
                    initial_backoff_ms=1000,
                    exponential_backoff=True,
                ),
            )

            # Expected calls: 1000ms, 2000ms, 4000ms (between 4 attempts)
            call_args = [call[0][0] for call in mock_sleep.call_args_list]
            assert call_args == [1.0, 2.0, 4.0]

    @patch("iris_devtester.utils.password.time.sleep")
    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_linear_backoff(self, mock_time, mock_sleep):
        """Linear backoff (exponential=False) should use constant initial_backoff_ms."""
        mock_time.return_value = 0

        with patch("iris.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")

            verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="test",
                password="pass",
                config=VerificationConfig(
                    max_retries=4,
                    initial_backoff_ms=500,
                    exponential_backoff=False,
                ),
            )

            # Expected calls: all 500ms
            call_args = [call[0][0] for call in mock_sleep.call_args_list]
            assert call_args == [0.5, 0.5, 0.5]

    @patch("iris_devtester.utils.password.time.time")
    def test_verify_password_username_preserved_in_result(self, mock_time):
        """Result should include the username that was tested."""
        mock_time.return_value = 0

        with patch("iris.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            result = verify_password(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="custom_user",
                password="pass",
            )

            assert result.username == "custom_user"


class TestResetPassword:
    """Test password reset via Docker exec."""

    @patch("subprocess.run")
    def test_reset_password_success_without_verify(self, mock_run):
        """Successful reset without verify should return success."""
        # Mock docker ps to show container running
        ps_result = Mock(stdout="iris_db", returncode=0)
        # Mock docker exec reset to show SUCCESS
        exec_result = Mock(
            stdout=b"SUCCESS", stderr=b"", returncode=0
        )
        mock_run.side_effect = [ps_result, exec_result]

        with patch("iris_devtester.utils.password.time.time", return_value=100):
            result = reset_password(
                container_name="iris_db",
                username="_SYSTEM",
                new_password="SYS",
                verify=False,
            )

        assert result.success is True
        assert "reset successfully" in result.message.lower()
        assert result.container_name == "iris_db"
        assert result.username == "_SYSTEM"
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_reset_password_container_not_running(self, mock_run):
        """Container not found should return failure."""
        # Mock docker ps to show container NOT running
        ps_result = Mock(stdout="", returncode=0)
        mock_run.return_value = ps_result

        result = reset_password(
            container_name="iris_db",
            username="_SYSTEM",
            new_password="SYS",
        )

        assert result.success is False
        assert "not running" in result.message.lower()
        assert result.error_type == "unknown"

    @patch("subprocess.run")
    def test_reset_password_docker_exec_no_success_marker(self, mock_run):
        """docker exec without SUCCESS marker should return failure."""
        # Mock docker ps to show container running
        ps_result = Mock(stdout="iris_db", returncode=0)
        # Mock docker exec to NOT return SUCCESS
        exec_result = Mock(
            stdout=b"FAILED:User not found", stderr=b"", returncode=0
        )
        mock_run.side_effect = [ps_result, exec_result]

        result = reset_password(
            container_name="iris_db",
            username="_SYSTEM",
            new_password="SYS",
            verify=False,
        )

        assert result.success is False
        assert result.error_type == "verification_failed"
        assert "FAILED" in result.message

    @patch("subprocess.run")
    def test_reset_password_timeout_expired(self, mock_run):
        """TimeoutExpired should return timeout error."""
        mock_run.side_effect = subprocess.TimeoutExpired("docker", timeout=30)

        result = reset_password(
            container_name="iris_db",
            username="_SYSTEM",
            new_password="SYS",
            timeout=30,
        )

        assert result.success is False
        assert result.error_type == "timeout"
        assert "timed out" in result.message.lower()

    @patch("subprocess.run")
    def test_reset_password_file_not_found(self, mock_run):
        """FileNotFoundError (Docker not in PATH) should return failure."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        result = reset_password(
            container_name="iris_db",
            username="_SYSTEM",
            new_password="SYS",
        )

        assert result.success is False
        assert "docker" in result.message.lower()

    @patch("subprocess.run")
    def test_reset_password_unexpected_exception(self, mock_run):
        """Unexpected exceptions should return unknown error."""
        mock_run.side_effect = RuntimeError("Unexpected error")

        result = reset_password(
            container_name="iris_db",
            username="_SYSTEM",
            new_password="SYS",
        )

        assert result.success is False
        assert result.error_type == "unknown"
        assert "Unexpected error" in result.message

    @patch("iris_devtester.utils.password.verify_password")
    @patch("subprocess.run")
    def test_reset_password_with_verify_success(self, mock_run, mock_verify):
        """Reset with verify=True and successful verification should succeed."""
        # Mock docker ps and exec
        ps_result = Mock(stdout="iris_db", returncode=0)
        exec_result = Mock(stdout=b"SUCCESS", stderr=b"", returncode=0)
        mock_run.side_effect = [ps_result, exec_result]

        # Mock verify_password to succeed
        mock_verify.return_value = PasswordResult(
            success=True,
            message="Password verified",
            attempts=1,
        )

        with patch("iris_devtester.utils.password.time.time", return_value=100):
            result = reset_password(
                container_name="iris_db",
                username="_SYSTEM",
                new_password="SYS",
                verify=True,
                hostname="localhost",
                port=1972,
            )

        assert result.success is True
        assert "verified successfully" in result.message.lower()
        mock_verify.assert_called_once()

    @patch("iris_devtester.utils.password.verify_password")
    @patch("subprocess.run")
    def test_reset_password_with_verify_fails(self, mock_run, mock_verify):
        """Reset succeeds but verify fails should return verification_failed."""
        # Mock docker ps and exec
        ps_result = Mock(stdout="iris_db", returncode=0)
        exec_result = Mock(stdout=b"SUCCESS", stderr=b"", returncode=0)
        mock_run.side_effect = [ps_result, exec_result]

        # Mock verify_password to fail
        mock_verify.return_value = PasswordResult(
            success=False,
            message="Connection refused",
            error_type="connection_refused",
            attempts=3,
        )

        with patch("iris_devtester.utils.password.time.time", return_value=100):
            result = reset_password(
                container_name="iris_db",
                username="_SYSTEM",
                new_password="SYS",
                verify=True,
            )

        assert result.success is False
        assert result.error_type == "connection_refused"
        assert "verification failed" in result.message.lower()

    @patch("subprocess.run")
    def test_reset_password_custom_container_name(self, mock_run):
        """Should use provided container_name."""
        ps_result = Mock(stdout="custom_iris", returncode=0)
        exec_result = Mock(stdout=b"SUCCESS", stderr=b"", returncode=0)
        mock_run.side_effect = [ps_result, exec_result]

        with patch("iris_devtester.utils.password.time.time", return_value=100):
            result = reset_password(
                container_name="custom_iris",
                verify=False,
            )

        assert result.container_name == "custom_iris"

    @patch("subprocess.run")
    def test_reset_password_custom_username(self, mock_run):
        """Should use provided username."""
        ps_result = Mock(stdout="iris_db", returncode=0)
        exec_result = Mock(stdout=b"SUCCESS", stderr=b"", returncode=0)
        mock_run.side_effect = [ps_result, exec_result]

        with patch("iris_devtester.utils.password.time.time", return_value=100):
            result = reset_password(
                container_name="iris_db",
                username="custom_user",
                verify=False,
            )

        assert result.username == "custom_user"

    @patch("subprocess.run")
    def test_reset_password_verifies_with_custom_hostname(self, mock_run):
        """Verify should use custom hostname if provided."""
        ps_result = Mock(stdout="iris_db", returncode=0)
        exec_result = Mock(stdout=b"SUCCESS", stderr=b"", returncode=0)
        mock_run.side_effect = [ps_result, exec_result]

        with patch("iris_devtester.utils.password.verify_password") as mock_verify:
            mock_verify.return_value = PasswordResult(
                success=True, message="OK", attempts=1
            )
            with patch("iris_devtester.utils.password.time.time", return_value=100):
                reset_password(
                    container_name="iris_db",
                    hostname="custom.host",
                    port=9999,
                    verify=True,
                )

            # Check verify_password was called with custom hostname/port
            call_kwargs = mock_verify.call_args[1]
            assert call_kwargs["hostname"] == "custom.host"
            assert call_kwargs["port"] == 9999


class TestUnexpireAllPasswords:
    """Test password unexpiration for a single container."""

    @patch("subprocess.run")
    def test_unexpire_all_passwords_success(self, mock_run):
        """Successful unexpiration should return (True, message)."""
        # Execute unexpire command (docker ps check and exec are combined in the actual code)
        exec_result = Mock(returncode=0, stdout="UNEXPIRED", stderr="", text=True)
        mock_run.return_value = exec_result

        success, message = unexpire_all_passwords("iris_db")

        assert success is True
        assert "iris_db" in message

    @patch("subprocess.run")
    def test_unexpire_all_passwords_command_fails(self, mock_run):
        """Non-zero returncode should return (False, message)."""
        exec_result = Mock(returncode=1, stdout="ERROR", stderr="Failed", text=True)
        mock_run.return_value = exec_result

        success, message = unexpire_all_passwords("iris_db")

        assert success is False
        assert "Failed" in message

    @patch("subprocess.run")
    def test_unexpire_all_passwords_no_unexpired_marker(self, mock_run):
        """Missing UNEXPIRED marker should return failure."""
        exec_result = Mock(returncode=0, stdout="No marker", stderr="", text=True)
        mock_run.return_value = exec_result

        success, message = unexpire_all_passwords("iris_db")

        assert success is False

    @patch("subprocess.run")
    def test_unexpire_all_passwords_timeout_expired(self, mock_run):
        """TimeoutExpired should return (False, message)."""
        mock_run.side_effect = subprocess.TimeoutExpired("docker", timeout=30)

        success, message = unexpire_all_passwords("iris_db", timeout=30)

        assert success is False
        assert "Timeout" in message

    @patch("subprocess.run")
    def test_unexpire_all_passwords_file_not_found(self, mock_run):
        """FileNotFoundError should return (False, message)."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        success, message = unexpire_all_passwords("iris_db")

        assert success is False
        assert "Docker" in message

    @patch("subprocess.run")
    def test_unexpire_all_passwords_unexpected_exception(self, mock_run):
        """Unexpected exceptions should return (False, message)."""
        mock_run.side_effect = RuntimeError("Unexpected error")

        success, message = unexpire_all_passwords("iris_db")

        assert success is False

    @patch("subprocess.run")
    def test_unexpire_all_passwords_custom_timeout(self, mock_run):
        """Custom timeout should be passed to subprocess.run."""
        exec_result = Mock(returncode=0, stdout="UNEXPIRED", stderr="", text=True)
        mock_run.return_value = exec_result

        unexpire_all_passwords("iris_db", timeout=60)

        # Check that timeout=60 was used
        for call in mock_run.call_args_list:
            assert call[1]["timeout"] == 60


class TestUnexpirePasswordsForContainers:
    """Test password unexpiration for multiple containers."""

    @patch("iris_devtester.utils.password.unexpire_all_passwords")
    def test_unexpire_multiple_containers_all_succeed(self, mock_unexpire):
        """All containers succeed should return all success entries."""
        mock_unexpire.side_effect = [
            (True, "Success 1"),
            (True, "Success 2"),
            (True, "Success 3"),
        ]

        results = unexpire_passwords_for_containers(
            ["iris1", "iris2", "iris3"], timeout=30, fail_fast=False
        )

        assert len(results) == 3
        assert all(success for success, _ in results.values())
        assert mock_unexpire.call_count == 3

    @patch("iris_devtester.utils.password.unexpire_all_passwords")
    def test_unexpire_multiple_containers_some_fail(self, mock_unexpire):
        """Partial failures should include both successes and failures."""
        mock_unexpire.side_effect = [
            (True, "Success 1"),
            (False, "Failed 2"),
            (True, "Success 3"),
        ]

        results = unexpire_passwords_for_containers(
            ["iris1", "iris2", "iris3"], timeout=30, fail_fast=False
        )

        assert len(results) == 3
        assert results["iris1"][0] is True
        assert results["iris2"][0] is False
        assert results["iris3"][0] is True

    @patch("iris_devtester.utils.password.unexpire_all_passwords")
    def test_unexpire_multiple_containers_fail_fast_stops_on_failure(self, mock_unexpire):
        """fail_fast=True should stop after first failure."""
        mock_unexpire.side_effect = [
            (True, "Success 1"),
            (False, "Failed 2"),
            (True, "Success 3"),  # Should not be reached
        ]

        results = unexpire_passwords_for_containers(
            ["iris1", "iris2", "iris3"], timeout=30, fail_fast=True
        )

        # Should only process up to iris2
        assert len(results) == 2
        assert mock_unexpire.call_count == 2

    @patch("iris_devtester.utils.password.unexpire_all_passwords")
    def test_unexpire_multiple_containers_empty_list(self, mock_unexpire):
        """Empty container list should return empty results."""
        results = unexpire_passwords_for_containers([], timeout=30)

        assert len(results) == 0
        assert mock_unexpire.call_count == 0

    @patch("iris_devtester.utils.password.unexpire_all_passwords")
    def test_unexpire_multiple_containers_custom_timeout(self, mock_unexpire):
        """Custom timeout should be passed to each call."""
        mock_unexpire.side_effect = [(True, "OK"), (True, "OK")]

        unexpire_passwords_for_containers(["iris1", "iris2"], timeout=60)

        # Check timeout=60 was passed to each call (can be positional or keyword)
        for call in mock_unexpire.call_args_list:
            # Check if timeout was passed as positional or keyword argument
            if len(call[0]) >= 2:
                # Positional: (container_name, timeout)
                assert call[0][1] == 60
            else:
                # Keyword argument
                assert call[1].get("timeout") == 60

    @patch("iris_devtester.utils.password.unexpire_all_passwords")
    def test_unexpire_multiple_containers_single_container(self, mock_unexpire):
        """Single container should work like multiple."""
        mock_unexpire.return_value = (True, "Success")

        results = unexpire_passwords_for_containers(["iris1"])

        assert len(results) == 1
        assert results["iris1"][0] is True


class TestResetPasswordIfNeeded:
    """Test automatic password reset on demand."""

    def test_reset_password_if_needed_non_password_error(self):
        """Non-password errors should return False."""
        error = Exception("Connection refused")
        result = reset_password_if_needed(error, container_name="iris_db")

        assert result is False

    def test_reset_password_if_needed_password_change_required(self):
        """Password change required error should trigger reset."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )

            result = reset_password_if_needed(
                error,
                container_name="iris_db",
                username="_SYSTEM",
                new_password="SYS",
            )

            assert result is True
            mock_reset.assert_called_once()

    def test_reset_password_if_needed_password_expired(self):
        """Password expired error should trigger reset."""
        # Use exact phrase that will be detected
        error = Exception("password expired")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )

            result = reset_password_if_needed(error, container_name="iris_db")

            assert result is True
            mock_reset.assert_called_once()

    def test_reset_password_if_needed_sqlcode_853(self):
        """SQLCODE 853 error should trigger reset."""
        error = Exception("Error: <853>")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )

            result = reset_password_if_needed(error, container_name="iris_db")

            assert result is True

    def test_reset_password_if_needed_auto_discover_container(self):
        """Should auto-discover container if not provided."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )
            with patch("docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_container = MagicMock()
                mock_container.name = "iris_auto"
                mock_client.containers.list.return_value = [mock_container]
                mock_docker.return_value = mock_client

                result = reset_password_if_needed(error, container_name=None)

                assert result is True
                # Should have called reset with discovered container
                call_kwargs = mock_reset.call_args[1]
                assert call_kwargs["container_name"] == "iris_auto"

    def test_reset_password_if_needed_auto_discover_fallback(self):
        """Should fallback to default container if auto-discovery fails."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )
            with patch("docker.from_env", side_effect=Exception("Docker error")):
                result = reset_password_if_needed(error, container_name=None)

                assert result is True
                # Should have used default fallback
                call_kwargs = mock_reset.call_args[1]
                assert call_kwargs["container_name"] == "iris_db"

    def test_reset_password_if_needed_max_retries_exceeded(self):
        """Should return False if reset fails after max retries."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=False, message="Reset failed", error_type="unknown"
            )
            with patch("iris_devtester.utils.password.time.sleep"):
                result = reset_password_if_needed(
                    error,
                    container_name="iris_db",
                    max_retries=2,
                )

                assert result is False
                # Should have attempted reset twice
                assert mock_reset.call_count == 2

    def test_reset_password_if_needed_custom_password(self):
        """Should use provided new_password."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )

            reset_password_if_needed(
                error,
                container_name="iris_db",
                new_password="CustomPassword123",
            )

            call_kwargs = mock_reset.call_args[1]
            assert call_kwargs["new_password"] == "CustomPassword123"

    def test_reset_password_if_needed_custom_username(self):
        """Should use provided username."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.return_value = PasswordResult(
                success=True, message="Reset successful"
            )

            reset_password_if_needed(
                error,
                container_name="iris_db",
                username="custom_user",
            )

            call_kwargs = mock_reset.call_args[1]
            assert call_kwargs["username"] == "custom_user"

    @patch("iris_devtester.utils.password.time.sleep")
    def test_reset_password_if_needed_retry_after_delay(self, mock_sleep):
        """Should retry after 3-second delay."""
        error = Exception("Password Change Required")

        with patch("iris_devtester.utils.password.reset_password") as mock_reset:
            mock_reset.side_effect = [
                PasswordResult(success=False, message="Failed", error_type="unknown"),
                PasswordResult(success=True, message="OK"),
            ]

            result = reset_password_if_needed(
                error,
                container_name="iris_db",
                max_retries=2,
            )

            assert result is True
            # Should have slept between retries
            mock_sleep.assert_called()
            assert mock_reset.call_count == 2
