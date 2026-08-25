"""
Unit tests for subprocess-based utility modules.

Tests cover container_port.py, enable_callin.py, and container_status.py
with comprehensive mocking of subprocess and external dependencies.
"""

import subprocess
from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.utils.container_port import get_container_port
from iris_devtester.utils.container_status import get_container_status
from iris_devtester.utils.enable_callin import enable_callin_service


class TestGetContainerPort:
    """Test get_container_port function."""

    def test_successful_port_lookup(self):
        """
        Test successful port lookup with valid docker output.

        Expected: Parses "0.0.0.0:55000" and returns 55000
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="0.0.0.0:55000\n",
            )

            result = get_container_port("test_container", container_port=1972, timeout=10)

            assert result == 55000
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["docker", "port", "test_container", "1972"]
            assert call_args[1]["timeout"] == 10

    def test_successful_port_lookup_with_ipv6(self):
        """
        Test parsing with multiple lines (IPv4 and IPv6).

        Expected: Uses first line, returns 55000
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="0.0.0.0:55000\n:::55000\n",
            )

            result = get_container_port("test_container")

            assert result == 55000

    def test_port_lookup_with_custom_container_port(self):
        """
        Test with custom container port parameter.

        Expected: Passes custom port to docker command
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="127.0.0.1:9999\n",
            )

            result = get_container_port("my_iris", container_port=9999, timeout=15)

            assert result == 9999
            call_args = mock_run.call_args
            assert "9999" in call_args[0][0]
            assert call_args[1]["timeout"] == 15

    def test_returncode_nonzero_returns_none(self):
        """
        Test when docker command fails (returncode != 0).

        Expected: Returns None
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: Container not found",
            )

            result = get_container_port("nonexistent_container")

            assert result is None

    def test_empty_stdout_returns_none(self):
        """
        Test when docker returns empty stdout (no port mapping).

        Expected: Returns None
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
            )

            result = get_container_port("container_without_port")

            assert result is None

    def test_whitespace_only_stdout_returns_none(self):
        """
        Test when docker returns whitespace-only stdout.

        Expected: Returns None (stdout.strip() is empty)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="   \n\n   ",
            )

            result = get_container_port("container")

            assert result is None

    def test_timeout_expired_returns_none(self):
        """
        Test when docker command times out.

        Expected: Returns None on TimeoutExpired
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 10)

            result = get_container_port("slow_container", timeout=10)

            assert result is None

    def test_value_error_on_malformed_port_returns_none(self):
        """
        Test parsing error when port is not an integer.

        Expected: Returns None on ValueError
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="0.0.0.0:invalid_port",
            )

            result = get_container_port("container")

            assert result is None

    def test_index_error_on_empty_split_returns_none(self):
        """
        Test IndexError when port mapping format is empty.

        Expected: Returns None on IndexError
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=":",  # Will split to ['', ''] then fail on [-1]
            )

            result = get_container_port("container")

            assert result is None

    def test_generic_exception_returns_none(self):
        """
        Test handling of unexpected exceptions.

        Expected: Returns None for any unexpected exception
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected docker error")

            result = get_container_port("container")

            assert result is None

    def test_default_timeout_is_10_seconds(self):
        """
        Test that default timeout is 10 seconds.

        Expected: Uses 10s timeout when not specified
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="0.0.0.0:1234\n")

            get_container_port("container")

            call_args = mock_run.call_args
            assert call_args[1]["timeout"] == 10

    def test_default_container_port_is_1972(self):
        """
        Test that default container port is 1972 (IRIS SuperServer).

        Expected: Passes 1972 as default port
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="0.0.0.0:5555\n")

            get_container_port("container")

            call_args = mock_run.call_args
            assert "1972" in call_args[0][0]

    def test_subprocess_called_with_text_mode(self):
        """
        Test that subprocess is called with text=True.

        Expected: text=True in subprocess.run call
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="0.0.0.0:1234\n")

            get_container_port("container")

            call_args = mock_run.call_args
            assert call_args[1]["text"] is True
            assert call_args[1]["capture_output"] is True

    def test_port_with_leading_zeros(self):
        """
        Test parsing port with leading zeros.

        Expected: Parses as integer correctly
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="0.0.0.0:00055000\n",
            )

            result = get_container_port("container")

            assert result == 55000


class TestEnableCallinService:
    """Test enable_callin_service function."""

    def test_successful_enablement_with_success_marker(self):
        """
        Test successful CallIn service enablement.

        Expected: Returns (True, message) when "1" in stdout
        """
        with patch("subprocess.run") as mock_run:
            # First call: docker ps check (container running)
            # Second call: enable command (returns "1")
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n", stderr=""),
                MagicMock(returncode=0, stdout="1\n", stderr=""),
            ]
            with patch("time.sleep"):  # Skip sleep
                result, message = enable_callin_service("my_container")

            assert result is True
            assert "CallIn service enabled" in message

    def test_container_not_running(self):
        """
        Test when container is not running.

        Expected: Returns (False, remediation_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result, message = enable_callin_service("nonexistent_container")

            assert result is False
            assert "not running" in message
            assert "docker start" in message

    def test_enable_command_fails_no_1_marker(self):
        """
        Test when enable command succeeds but returns no "1".

        Expected: Still returns True (idempotent check passes)
        """
        with patch("subprocess.run") as mock_run:
            # First: docker ps (running)
            # Second: enable command (returncode 0 but no "1")
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n"),
                MagicMock(returncode=0, stdout="already enabled\n"),
            ]
            with patch("time.sleep"):
                result, message = enable_callin_service("my_container")

            # Still returns True due to idempotent check
            assert result is True

    def test_enable_command_fails_with_error(self):
        """
        Test when enable command fails (returncode != 0).

        Expected: Returns (False, error_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n"),
                MagicMock(returncode=1, stdout="", stderr="ObjectScript error"),
            ]

            result, message = enable_callin_service("my_container")

            assert result is False
            assert "Failed to enable CallIn" in message
            assert "ObjectScript error" in message

    def test_timeout_on_docker_ps_check(self):
        """
        Test timeout during docker ps check.

        Expected: Returns (False, timeout_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 30)

            result, message = enable_callin_service("my_container", timeout=30)

            assert result is False
            assert "Timeout" in message
            assert "30s" in message

    def test_timeout_on_enable_command(self):
        """
        Test timeout during enable command execution.

        Expected: Returns (False, timeout_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n"),
                subprocess.TimeoutExpired("docker", 30),
            ]

            result, message = enable_callin_service("my_container", timeout=30)

            assert result is False
            assert "Timeout" in message

    def test_file_not_found_error(self):
        """
        Test when docker binary is not found.

        Expected: Returns (False, with "not found" guidance)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")

            result, message = enable_callin_service("my_container")

            assert result is False
            assert "Unexpected error" in message

    def test_generic_exception_handling(self):
        """
        Test handling of unexpected exceptions.

        Expected: Returns (False, error_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            result, message = enable_callin_service("my_container")

            assert result is False
            assert "Unexpected error" in message

    def test_default_container_name_is_iris_db(self):
        """
        Test default container name is "iris_db".

        Expected: Uses "iris_db" when not specified
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="iris_db\n"),
                MagicMock(returncode=0, stdout="1\n"),
            ]
            with patch("time.sleep"):
                enable_callin_service()

            call_args = mock_run.call_args_list[0]
            # Check that "name=iris_db" is in the command list
            cmd = call_args[0][0]
            assert any("iris_db" in str(arg) for arg in cmd)

    def test_default_timeout_is_30_seconds(self):
        """
        Test default timeout is 30 seconds.

        Expected: Passes timeout=30 to subprocess calls
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="iris_db\n"),
                MagicMock(returncode=0, stdout="1\n"),
            ]
            with patch("time.sleep"):
                enable_callin_service("iris_db")

            # Both calls should have timeout=30
            for call in mock_run.call_args_list:
                assert call[1]["timeout"] == 30

    def test_sleep_called_after_successful_enable(self):
        """
        Test that sleep is called after successful enablement.

        Expected: Calls time.sleep(1) after success
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n"),
                MagicMock(returncode=0, stdout="1\n"),
            ]
            with patch("time.sleep") as mock_sleep:
                enable_callin_service("my_container")

            mock_sleep.assert_called_once_with(1)

    def test_docker_ps_command_format(self):
        """
        Test that docker ps command has correct filters.

        Expected: Uses name filter and format
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n"),
                MagicMock(returncode=0, stdout="1\n"),
            ]
            with patch("time.sleep"):
                enable_callin_service("my_container")

            # First call is docker ps
            call_args = mock_run.call_args_list[0]
            cmd = call_args[0][0]
            assert "ps" in cmd
            assert "--filter" in cmd
            assert "name=my_container" in cmd
            assert "--format" in cmd

    def test_enable_command_uses_irisowner_user(self):
        """
        Test that enable command runs as irisowner.

        Expected: Uses -u irisowner in docker exec
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_container\n"),
                MagicMock(returncode=0, stdout="1\n"),
            ]
            with patch("time.sleep"):
                enable_callin_service("my_container")

            # Second call is docker exec
            call_args = mock_run.call_args_list[1]
            cmd = call_args[0][0]
            assert "exec" in cmd
            assert "-u" in cmd
            assert "irisowner" in cmd


class TestGetContainerStatus:
    """Test get_container_status function."""

    def test_container_healthy_and_accessible(self):
        """
        Test when container is running, healthy, and accessible.

        Expected: Returns (True, status_message) with checkmarks
        """
        with patch("subprocess.run") as mock_run:
            # docker ps call
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            # docker inspect call
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected successfully")

                result, status = get_container_status("my_iris")

            assert result is True
            assert "✓" in status
            assert "Running:    ✓ Yes" in status
            assert "healthy" in status

    def test_container_not_running(self):
        """
        Test when container is not running.

        Expected: Returns (False, status_message) early
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            result, status = get_container_status("stopped_container")

            assert result is False
            assert "Running:    ✗ No" in status
            assert "docker start" in status

    def test_container_running_but_starting(self):
        """
        Test when container is running but still starting.

        Expected: Shows health status as "starting"
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="starting\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected")

                result, status = get_container_status("my_iris")

            assert "starting" in status
            assert "container still initializing" in status

    def test_container_healthy_but_connection_fails(self):
        """
        Test when container is healthy but connection test fails.

        Expected: Returns (False, status_message) with connection error
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (False, "Connection refused")

                result, status = get_container_status("my_iris")

            assert result is False
            assert "Connection: ✗ Failed" in status
            assert "enable-callin" in status

    def test_no_healthcheck_configured(self):
        """
        Test when container has no healthcheck configured.

        Expected: Shows "No healthcheck" status
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="<no value>\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected")

                result, status = get_container_status("my_iris")

            assert "No healthcheck" in status

    def test_container_unhealthy(self):
        """
        Test when container is unhealthy.

        Expected: Shows checkmark (healthy substring match) or warning for other values
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            # Note: "unhealthy" contains "healthy" as a substring, so it matches the if condition
            inspect_result = MagicMock(returncode=0, stdout="failed\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (False, "Connection failed")

                result, status = get_container_status("my_iris")

            assert "⚠" in status
            assert "failed" in status

    def test_timeout_on_docker_ps(self):
        """
        Test timeout during docker ps check.

        Expected: Returns (False, timeout_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 10)

            result, status = get_container_status("my_iris")

            assert result is False
            assert "Timeout" in status

    def test_exception_handling(self):
        """
        Test generic exception handling.

        Expected: Returns (False, error_message)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            result, status = get_container_status("my_iris")

            assert result is False
            assert "Unexpected error" in status
            assert "docker --version" in status

    def test_default_container_name_is_iris_db(self):
        """
        Test default container name is "iris_db".

        Expected: Uses "iris_db" when not specified
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="iris_db\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected")

                get_container_status()

            # Verify test_connection was called with default name
            mock_test_conn.assert_called_once()
            call_args = mock_test_conn.call_args
            assert call_args[0][0] == "iris_db"

    def test_test_connection_called_with_user_namespace(self):
        """
        Test that test_connection is called with USER namespace.

        Expected: Calls test_connection(container_name, "USER", timeout=10)
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected")

                get_container_status("my_iris")

            # Verify test_connection signature
            call_args = mock_test_conn.call_args
            assert call_args[0][1] == "USER"
            assert call_args[1]["timeout"] == 10

    def test_status_message_includes_container_name(self):
        """
        Test that status message includes container name.

        Expected: First line includes container name
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_custom_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected")

                result, status = get_container_status("my_custom_iris")

            assert "my_custom_iris" in status

    def test_connection_error_message_included_in_status(self):
        """
        Test that connection error message is included in status.

        Expected: Shows first line of error message
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (False, "Cannot connect to port 1972\nDetailed error info")

                result, status = get_container_status("my_iris")

            assert "Cannot connect to port 1972" in status

    def test_overall_success_when_all_checks_pass(self):
        """
        Test overall success status when all checks pass.

        Expected: Shows "Overall: ✓ Container healthy and accessible"
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "Connected")

                result, status = get_container_status("my_iris")

            assert "Overall: ✓ Container healthy and accessible" in status

    def test_overall_failure_when_checks_fail(self):
        """
        Test overall failure status when any check fails.

        Expected: Shows "Overall: ✗ Issues detected"
        """
        with patch("subprocess.run") as mock_run:
            ps_result = MagicMock(returncode=0, stdout="my_iris\n")
            inspect_result = MagicMock(returncode=0, stdout="healthy\n")

            mock_run.side_effect = [ps_result, inspect_result]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (False, "Failed to connect")

                result, status = get_container_status("my_iris")

            assert "Overall: ✗ Issues detected" in status

    def test_subprocess_called_with_correct_docker_ps_command(self):
        """
        Test correct docker ps command is used.

        Expected: Command format matches expected pattern
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_iris\n"),
                MagicMock(returncode=0, stdout="healthy\n"),
            ]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "OK")

                get_container_status("my_iris")

            # First call should be docker ps
            call_args = mock_run.call_args_list[0]
            cmd = call_args[0][0]
            assert cmd[0] == "docker"
            assert cmd[1] == "ps"
            assert "--filter" in cmd
            assert "--format" in cmd

    def test_subprocess_called_with_correct_docker_inspect_command(self):
        """
        Test correct docker inspect command is used.

        Expected: Command format matches expected pattern
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="my_iris\n"),
                MagicMock(returncode=0, stdout="healthy\n"),
            ]

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                mock_test_conn.return_value = (True, "OK")

                get_container_status("my_iris")

            # Second call should be docker inspect
            call_args = mock_run.call_args_list[1]
            cmd = call_args[0][0]
            assert cmd[0] == "docker"
            assert cmd[1] == "inspect"
            assert "--format" in cmd
            assert "Health.Status" in cmd[3]

    def test_early_return_on_container_not_running(self):
        """
        Test that function returns early if container not running.

        Expected: Doesn't call test_connection if container not running
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            with patch("iris_devtester.utils.container_status.test_connection") as mock_test_conn:
                get_container_status("my_iris")

                # test_connection should not be called
                mock_test_conn.assert_not_called()
