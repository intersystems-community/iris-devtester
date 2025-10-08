"""
Unit tests for password reset utility.

Tests automatic detection and remediation of IRIS password change requirements.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess


class TestPasswordResetDetection:
    """Test password change requirement detection."""

    def test_can_import(self):
        """Test that password reset utilities can be imported."""
        from iris_devtools.utils.password_reset import detect_password_change_required

        assert callable(detect_password_change_required)

    def test_detects_password_change_required_lowercase(self):
        """Test detection of lowercase 'password change required'."""
        from iris_devtools.utils.password_reset import detect_password_change_required

        error_msg = "Connection failed: password change required for user"
        assert detect_password_change_required(error_msg) is True

    def test_detects_password_change_required_mixed_case(self):
        """Test detection of mixed case 'Password change required'."""
        from iris_devtools.utils.password_reset import detect_password_change_required

        error_msg = "Error: Password change required"
        assert detect_password_change_required(error_msg) is True

    def test_detects_password_expired(self):
        """Test detection of 'password expired' message."""
        from iris_devtools.utils.password_reset import detect_password_change_required

        error_msg = "Authentication failed: password expired"
        assert detect_password_change_required(error_msg) is True

    def test_does_not_detect_normal_errors(self):
        """Test that normal errors are not detected as password change."""
        from iris_devtools.utils.password_reset import detect_password_change_required

        error_msg = "Connection refused: host unreachable"
        assert detect_password_change_required(error_msg) is False

    def test_does_not_detect_empty_string(self):
        """Test that empty string returns False."""
        from iris_devtools.utils.password_reset import detect_password_change_required

        assert detect_password_change_required("") is False


class TestPasswordReset:
    """Test password reset functionality."""

    def test_can_import_reset_function(self):
        """Test that reset_password function can be imported."""
        from iris_devtools.utils.password_reset import reset_password

        assert callable(reset_password)

    @patch("subprocess.run")
    def test_reset_password_success(self, mock_run):
        """Test successful password reset."""
        from iris_devtools.utils.password_reset import reset_password

        # Mock successful docker ps (container running)
        ps_result = Mock()
        ps_result.returncode = 0
        ps_result.stdout = "iris_container"

        # Mock successful password reset
        reset_result = Mock()
        reset_result.returncode = 0
        reset_result.stdout = "Password changed"

        mock_run.side_effect = [ps_result, reset_result]

        success, message = reset_password(
            container_name="iris_container", username="_SYSTEM", new_password="SYS"
        )

        assert success is True
        assert "successful" in message.lower()

    @patch("subprocess.run")
    def test_reset_password_container_not_running(self, mock_run):
        """Test password reset when container not running."""
        from iris_devtools.utils.password_reset import reset_password

        # Mock docker ps showing no container
        ps_result = Mock()
        ps_result.returncode = 0
        ps_result.stdout = ""

        mock_run.return_value = ps_result

        success, message = reset_password(container_name="iris_container")

        assert success is False
        assert "not running" in message.lower()

    @patch("subprocess.run")
    def test_reset_password_docker_not_found(self, mock_run):
        """Test password reset when docker command not found."""
        from iris_devtools.utils.password_reset import reset_password

        mock_run.side_effect = FileNotFoundError("docker not found")

        success, message = reset_password()

        assert success is False
        assert "docker" in message.lower()

    @patch("subprocess.run")
    def test_reset_password_timeout(self, mock_run):
        """Test password reset timeout handling."""
        from iris_devtools.utils.password_reset import reset_password

        # Mock container check success
        ps_result = Mock()
        ps_result.returncode = 0
        ps_result.stdout = "iris_container"

        # Mock timeout on password reset
        mock_run.side_effect = [ps_result, subprocess.TimeoutExpired("cmd", 30)]

        success, message = reset_password(container_name="iris_container")

        assert success is False
        assert "timeout" in message.lower()


class TestPasswordResetIfNeeded:
    """Test automatic password reset remediation."""

    def test_can_import(self):
        """Test that reset_password_if_needed can be imported."""
        from iris_devtools.utils.password_reset import reset_password_if_needed

        assert callable(reset_password_if_needed)

    @patch("iris_devtools.utils.password_reset.reset_password")
    @patch("iris_devtools.utils.password_reset.detect_password_change_required")
    def test_resets_when_password_change_detected(
        self, mock_detect, mock_reset
    ):
        """Test that password is reset when change is detected."""
        from iris_devtools.utils.password_reset import reset_password_if_needed

        # Mock detection
        mock_detect.return_value = True

        # Mock successful reset
        mock_reset.return_value = (True, "Password reset successful")

        error = Exception("Password change required")
        result = reset_password_if_needed(error)

        assert result is True
        mock_detect.assert_called_once()
        mock_reset.assert_called_once()

    @patch("iris_devtools.utils.password_reset.detect_password_change_required")
    def test_does_not_reset_when_no_password_change_detected(self, mock_detect):
        """Test that password is not reset for normal errors."""
        from iris_devtools.utils.password_reset import reset_password_if_needed

        mock_detect.return_value = False

        error = Exception("Connection refused")
        result = reset_password_if_needed(error)

        assert result is False

    @patch("iris_devtools.utils.password_reset.reset_password")
    @patch("iris_devtools.utils.password_reset.detect_password_change_required")
    def test_retries_on_failure(self, mock_detect, mock_reset):
        """Test retry logic on password reset failure."""
        from iris_devtools.utils.password_reset import reset_password_if_needed

        mock_detect.return_value = True

        # First attempt fails, second succeeds
        mock_reset.side_effect = [
            (False, "Password reset failed"),
            (True, "Password reset successful"),
        ]

        error = Exception("Password change required")
        result = reset_password_if_needed(error, max_retries=2)

        assert result is True
        assert mock_reset.call_count == 2

    @patch("iris_devtools.utils.password_reset.reset_password")
    @patch("iris_devtools.utils.password_reset.detect_password_change_required")
    def test_gives_up_after_max_retries(self, mock_detect, mock_reset):
        """Test that retries are limited."""
        from iris_devtools.utils.password_reset import reset_password_if_needed

        mock_detect.return_value = True
        mock_reset.return_value = (False, "Password reset failed")

        error = Exception("Password change required")
        result = reset_password_if_needed(error, max_retries=2)

        assert result is False
        assert mock_reset.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
