"""
Unit tests for health check utilities module.

Tests verify multi-layer container health checking, port availability,
Docker health status checks, and IRIS Monitor.State() integration.
"""

import socket
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from iris_devtester.config.container_state import ContainerState, HealthStatus
from iris_devtester.utils.health_checks import (
    IrisHealthState,
    IrisMonitorResult,
    check_docker_health,
    check_iris_monitor_state,
    check_port_available,
    enable_callin_service,
    get_container_logs,
    is_container_healthy,
    wait_for_healthy,
    wait_for_iris_healthy,
    wait_for_port,
)


class TestIrisHealthState:
    """Test IrisHealthState enum and is_healthy property."""

    def test_iris_health_state_ok_value(self):
        """Test OK state has value 0."""
        assert IrisHealthState.OK.value == 0

    def test_iris_health_state_warning_value(self):
        """Test WARNING state has value 1."""
        assert IrisHealthState.WARNING.value == 1

    def test_iris_health_state_error_value(self):
        """Test ERROR state has value 2."""
        assert IrisHealthState.ERROR.value == 2

    def test_iris_health_state_fatal_value(self):
        """Test FATAL state has value 3."""
        assert IrisHealthState.FATAL.value == 3

    def test_ok_is_healthy(self):
        """Test OK state is considered healthy."""
        assert IrisHealthState.OK.is_healthy is True

    def test_warning_is_healthy(self):
        """Test WARNING state is considered healthy."""
        assert IrisHealthState.WARNING.is_healthy is True

    def test_error_is_not_healthy(self):
        """Test ERROR state is not considered healthy."""
        assert IrisHealthState.ERROR.is_healthy is False

    def test_fatal_is_not_healthy(self):
        """Test FATAL state is not considered healthy."""
        assert IrisHealthState.FATAL.is_healthy is False

    def test_all_states_accessible(self):
        """Test all states are accessible and distinct."""
        states = [IrisHealthState.OK, IrisHealthState.WARNING, IrisHealthState.ERROR, IrisHealthState.FATAL]
        values = [s.value for s in states]
        assert values == [0, 1, 2, 3]
        assert len(set(values)) == 4  # All unique


class TestIrisMonitorResult:
    """Test IrisMonitorResult dataclass."""

    def test_construct_with_all_fields(self):
        """Test creating IrisMonitorResult with all fields."""
        result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="Container is healthy",
            raw_output="0\n",
        )

        assert result.state == IrisHealthState.OK
        assert result.is_healthy is True
        assert result.message == "Container is healthy"
        assert result.raw_output == "0\n"

    def test_construct_without_raw_output(self):
        """Test creating IrisMonitorResult with default raw_output."""
        result = IrisMonitorResult(
            state=IrisHealthState.WARNING,
            is_healthy=True,
            message="Minor issues",
        )

        assert result.state == IrisHealthState.WARNING
        assert result.is_healthy is True
        assert result.message == "Minor issues"
        assert result.raw_output == ""

    def test_different_states(self):
        """Test IrisMonitorResult with different states."""
        states = [
            (IrisHealthState.OK, True),
            (IrisHealthState.WARNING, True),
            (IrisHealthState.ERROR, False),
            (IrisHealthState.FATAL, False),
        ]

        for state, is_healthy in states:
            result = IrisMonitorResult(
                state=state,
                is_healthy=is_healthy,
                message=f"State: {state.name}",
            )
            assert result.state == state
            assert result.is_healthy == is_healthy


class TestCheckPortAvailable:
    """Test check_port_available function."""

    @patch("socket.create_connection")
    def test_port_available_returns_true(self, mock_socket):
        """Test port available returns True."""
        mock_sock_obj = MagicMock()
        mock_socket.return_value = mock_sock_obj

        result = check_port_available(1972)

        assert result is True
        mock_socket.assert_called_once_with(("localhost", 1972), timeout=2)
        mock_sock_obj.close.assert_called_once()

    @patch("socket.create_connection")
    def test_port_available_with_custom_host(self, mock_socket):
        """Test port available with custom host."""
        mock_sock_obj = MagicMock()
        mock_socket.return_value = mock_sock_obj

        result = check_port_available(1972, host="127.0.0.1")

        assert result is True
        mock_socket.assert_called_once_with(("127.0.0.1", 1972), timeout=2)

    @patch("socket.create_connection")
    def test_port_timeout_returns_false(self, mock_socket):
        """Test socket timeout returns False."""
        mock_socket.side_effect = socket.timeout("Connection timed out")

        result = check_port_available(1972)

        assert result is False

    @patch("socket.create_connection")
    def test_port_connection_refused_returns_false(self, mock_socket):
        """Test connection refused returns False."""
        mock_socket.side_effect = ConnectionRefusedError("Connection refused")

        result = check_port_available(1972)

        assert result is False

    @patch("socket.create_connection")
    def test_port_socket_error_returns_false(self, mock_socket):
        """Test generic socket error returns False."""
        mock_socket.side_effect = socket.error("Socket error")

        result = check_port_available(1972)

        assert result is False

    @patch("socket.create_connection")
    def test_port_other_exception_returns_false(self, mock_socket):
        """Test other exceptions return False."""
        mock_socket.side_effect = OSError("OS error")

        result = check_port_available(1972)

        assert result is False


class TestCheckDockerHealth:
    """Test check_docker_health function."""

    def test_healthy_status(self):
        """Test healthy Docker status."""
        container = MagicMock()
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "healthy",
                }
            }
        }

        result = check_docker_health(container)

        assert result == HealthStatus.HEALTHY
        container.reload.assert_called_once()

    def test_unhealthy_status(self):
        """Test unhealthy Docker status."""
        container = MagicMock()
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "unhealthy",
                }
            }
        }

        result = check_docker_health(container)

        assert result == HealthStatus.UNHEALTHY

    def test_starting_status(self):
        """Test starting Docker status."""
        container = MagicMock()
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "starting",
                }
            }
        }

        result = check_docker_health(container)

        assert result == HealthStatus.STARTING

    def test_none_status(self):
        """Test none/undefined Docker status."""
        container = MagicMock()
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "none",
                }
            }
        }

        result = check_docker_health(container)

        assert result == HealthStatus.NONE

    def test_no_health_info_returns_none(self):
        """Test no health info returns NONE status."""
        container = MagicMock()
        container.attrs = {"State": {}}

        result = check_docker_health(container)

        assert result == HealthStatus.NONE

    def test_case_insensitive_status(self):
        """Test status matching is case-insensitive."""
        container = MagicMock()
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "HEALTHY",
                }
            }
        }

        result = check_docker_health(container)

        assert result == HealthStatus.HEALTHY

    def test_unknown_status_returns_none(self):
        """Test unknown status returns NONE."""
        container = MagicMock()
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "unknown_status",
                }
            }
        }

        result = check_docker_health(container)

        assert result == HealthStatus.NONE

    def test_empty_attributes_returns_none(self):
        """Test empty attributes returns NONE."""
        container = MagicMock()
        container.attrs = {}

        result = check_docker_health(container)

        assert result == HealthStatus.NONE


class TestIsContainerHealthy:
    """Test is_container_healthy function."""

    def test_running_and_healthy(self):
        """Test container running and healthy returns True."""
        container = MagicMock()
        container.status = "running"
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "healthy",
                }
            }
        }

        result = is_container_healthy(container)

        assert result is True

    def test_not_running_returns_false(self):
        """Test container not running returns False."""
        container = MagicMock()
        container.status = "exited"

        result = is_container_healthy(container)

        assert result is False

    def test_running_but_unhealthy_returns_false(self):
        """Test running but unhealthy returns False."""
        container = MagicMock()
        container.status = "running"
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "unhealthy",
                }
            }
        }

        result = is_container_healthy(container)

        assert result is False

    def test_running_without_health_check_returns_true(self):
        """Test running without health check returns True."""
        container = MagicMock()
        container.status = "running"
        container.attrs = {"State": {}}

        result = is_container_healthy(container)

        assert result is True

    def test_dead_status_returns_false(self):
        """Test dead status returns False."""
        container = MagicMock()
        container.status = "dead"

        result = is_container_healthy(container)

        assert result is False

    def test_paused_status_returns_false(self):
        """Test paused status returns False."""
        container = MagicMock()
        container.status = "paused"

        result = is_container_healthy(container)

        assert result is False


class TestWaitForPort:
    """Test wait_for_port function."""

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_port_available")
    def test_port_immediately_available(self, mock_check, mock_sleep):
        """Test port available on first check."""
        mock_check.return_value = True

        # Should not raise
        wait_for_port(1972, timeout=30)

        mock_check.assert_called_once_with(1972, "localhost")
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_port_available")
    def test_port_available_after_retries(self, mock_check, mock_sleep):
        """Test port becomes available after retries."""
        mock_check.side_effect = [False, False, True]

        wait_for_port(1972, timeout=30)

        assert mock_check.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_port_available")
    def test_port_timeout_raises_error(self, mock_check, mock_sleep):
        """Test timeout raises TimeoutError."""
        mock_check.return_value = False

        with pytest.raises(TimeoutError, match="Port 1972 on localhost did not become accessible within 5 seconds"):
            wait_for_port(1972, timeout=5)

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_port_available")
    def test_custom_host(self, mock_check, mock_sleep):
        """Test custom host."""
        mock_check.return_value = True

        wait_for_port(1972, host="127.0.0.1", timeout=30)

        mock_check.assert_called_once_with(1972, "127.0.0.1")

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_port_available")
    def test_respects_timeout(self, mock_check, mock_sleep):
        """Test that timeout is respected."""
        mock_check.return_value = False

        with pytest.raises(TimeoutError):
            wait_for_port(1972, timeout=3)

        # Should have called check_port_available multiple times
        assert mock_check.call_count >= 1


class TestGetContainerLogs:
    """Test get_container_logs function."""

    def test_get_logs_bytes_decoded(self):
        """Test logs are properly decoded from bytes."""
        container = MagicMock()
        container.logs.return_value = b"Container log line 1\nContainer log line 2\n"

        result = get_container_logs(container)

        assert result == "Container log line 1\nContainer log line 2\n"
        container.logs.assert_called_once_with(tail=100)

    def test_get_logs_custom_tail(self):
        """Test custom tail parameter."""
        container = MagicMock()
        container.logs.return_value = b"Last line\n"

        result = get_container_logs(container, tail=50)

        assert result == "Last line\n"
        container.logs.assert_called_once_with(tail=50)

    def test_get_logs_with_unicode(self):
        """Test logs with unicode characters."""
        container = MagicMock()
        container.logs.return_value = "Unicode: éàü".encode("utf-8")

        result = get_container_logs(container)

        assert "é" in result

    def test_get_logs_with_invalid_utf8(self):
        """Test logs with invalid UTF-8 are handled gracefully."""
        container = MagicMock()
        container.logs.return_value = b"Valid \xff Invalid"

        # Should not raise, invalid chars are ignored
        result = get_container_logs(container)

        assert "Valid" in result


class TestEnableCallinService:
    """Test enable_callin_service function."""

    def test_enable_callin_success(self):
        """Test successful CallIn service enabling."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"")

        # Should not raise
        enable_callin_service(container)

        container.exec_run.assert_called_once()
        call_args = container.exec_run.call_args
        assert "iris session IRIS" in call_args[1]["cmd"][2]
        assert "%Service_CallIn" in call_args[1]["cmd"][2]
        assert call_args[1]["user"] == "irisowner"

    def test_enable_callin_failure_exit_code(self):
        """Test CallIn service enabling fails with non-zero exit code."""
        container = MagicMock()
        container.exec_run.return_value = (1, b"Error: Permission denied")

        with pytest.raises(RuntimeError, match="Failed to enable CallIn service"):
            enable_callin_service(container)

    def test_enable_callin_exception_raised(self):
        """Test CallIn service enabling handles exceptions."""
        container = MagicMock()
        container.exec_run.side_effect = Exception("Docker error")

        with pytest.raises(RuntimeError, match="Failed to enable CallIn service"):
            enable_callin_service(container)


class TestCheckIrisMonitorState:
    """Test check_iris_monitor_state function."""

    def test_monitor_state_ok(self):
        """Test Monitor.State() returns 0 (OK)."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"0\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.OK
        assert result.is_healthy is True
        assert "OK" in result.message

    def test_monitor_state_warning(self):
        """Test Monitor.State() returns 1 (WARNING)."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"1\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.WARNING
        assert result.is_healthy is True

    def test_monitor_state_error(self):
        """Test Monitor.State() returns 2 (ERROR)."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"2\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.ERROR
        assert result.is_healthy is False

    def test_monitor_state_fatal(self):
        """Test Monitor.State() returns 3 (FATAL)."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"3\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.FATAL
        assert result.is_healthy is False

    def test_monitor_state_unconfigured_minus_one(self):
        """Test Monitor.State() returns -1 (monitoring not configured)."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"-1\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.OK
        assert result.is_healthy is True
        assert "monitoring not configured" in result.message

    def test_monitor_state_with_output_prefix(self):
        """Test Monitor.State() output with IRIS prompt prefix (multiline)."""
        container = MagicMock()
        # The regex looks for the number on its own line (or with just \n around it)
        # "IRIS> 0" won't match, but "IRIS>\n0" or similar would
        container.exec_run.return_value = (0, b"Some IRIS output\n0\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.OK
        assert result.is_healthy is True

    def test_monitor_state_exit_code_nonzero(self):
        """Test Monitor.State() with non-zero exit code."""
        container = MagicMock()
        container.exec_run.return_value = (1, b"Error message")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.FATAL
        assert result.is_healthy is False
        assert "exit code: 1" in result.message

    def test_monitor_state_unparseable_output(self):
        """Test Monitor.State() with unparseable output."""
        container = MagicMock()
        container.exec_run.return_value = (0, b"Some garbage output\n")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.FATAL
        assert result.is_healthy is False
        assert "Could not parse" in result.message

    def test_monitor_state_exception_handling(self):
        """Test Monitor.State() exception handling."""
        container = MagicMock()
        container.exec_run.side_effect = Exception("Docker error")

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.FATAL
        assert result.is_healthy is False
        assert "Health check failed" in result.message


class TestWaitForIrisHealthy:
    """Test wait_for_iris_healthy function."""

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_immediately_healthy(self, mock_check, mock_sleep):
        """Test container immediately healthy."""
        mock_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        mock_check.return_value = mock_result

        result = wait_for_iris_healthy(MagicMock(), timeout=30)

        assert result is True
        mock_check.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_becomes_healthy_after_retries(self, mock_check, mock_sleep):
        """Test container becomes healthy after retries."""
        warning_result = IrisMonitorResult(
            state=IrisHealthState.WARNING,
            is_healthy=True,
            message="Warning - Container has minor issues",
        )
        ok_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        # Since WARNING is still healthy (is_healthy=True), the function returns on first check!
        # Change WARNING to ERROR to trigger retries
        error_result = IrisMonitorResult(
            state=IrisHealthState.ERROR,
            is_healthy=False,
            message="Error - Container has problems",
        )
        mock_check.side_effect = [error_result, error_result, ok_result]

        result = wait_for_iris_healthy(MagicMock(), timeout=30)

        assert result is True
        assert mock_check.call_count == 3

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_timeout_returns_false(self, mock_check, mock_sleep):
        """Test timeout returns False."""
        error_result = IrisMonitorResult(
            state=IrisHealthState.ERROR,
            is_healthy=False,
            message="Error - Container has problems",
        )
        mock_check.return_value = error_result

        result = wait_for_iris_healthy(MagicMock(), timeout=5)

        assert result is False

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_progress_callback_called(self, mock_check, mock_sleep):
        """Test progress callback is called."""
        mock_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        mock_check.return_value = mock_result
        mock_callback = MagicMock()

        result = wait_for_iris_healthy(MagicMock(), timeout=30, progress_callback=mock_callback)

        assert result is True
        mock_callback.assert_called()


class TestWaitForHealthy:
    """Test wait_for_healthy function (multi-layer health check)."""

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.ContainerState.from_container")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    @patch("socket.create_connection")
    def test_all_layers_pass(self, mock_socket, mock_monitor, mock_container_state, mock_sleep):
        """Test all layers pass successfully."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {"Health": {"Status": "healthy"}},
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}},
        }

        mock_socket_obj = MagicMock()
        mock_socket.return_value = mock_socket_obj

        monitor_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        mock_monitor.return_value = monitor_result

        expected_state = MagicMock(spec=ContainerState)
        mock_container_state.return_value = expected_state

        result = wait_for_healthy(container, timeout=60)

        assert result == expected_state

    @patch("time.sleep")
    def test_container_not_running_raises_error(self, mock_sleep):
        """Test container not running raises RuntimeError."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "exited"
        container.logs.return_value = b"Container startup failed"

        with pytest.raises(RuntimeError, match="Container failed to start"):
            wait_for_healthy(container, timeout=10)

    @patch("time.sleep")
    def test_timeout_waiting_for_running(self, mock_sleep):
        """Test timeout waiting for container to run."""
        container = MagicMock()
        container.status = "creating"
        # Simulate timeout by making status never reach "running"

        with pytest.raises(TimeoutError, match="Container did not start within 5 seconds"):
            wait_for_healthy(container, timeout=5)

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_docker_health_check_failed(self, mock_monitor, mock_sleep):
        """Test Docker health check failure."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "unhealthy",
                    "Log": [{"Output": "Health check failed"}],
                }
            },
        }

        with pytest.raises(RuntimeError, match="Container health check failed"):
            wait_for_healthy(container, timeout=30)

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    @patch("socket.create_connection")
    def test_port_not_accessible_timeout(self, mock_socket, mock_monitor, mock_sleep):
        """Test IRIS port not accessible timeout."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {"Health": {"Status": "healthy"}},
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}},
        }

        mock_socket.side_effect = ConnectionRefusedError("Connection refused")

        with pytest.raises(TimeoutError, match="IRIS SuperServer port not accessible"):
            wait_for_healthy(container, timeout=5)

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.ContainerState.from_container")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    @patch("socket.create_connection")
    def test_iris_monitor_state_timeout(self, mock_socket, mock_monitor, mock_container_state, mock_sleep):
        """Test IRIS Monitor.State timeout."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {"Health": {"Status": "healthy"}},
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}},
        }

        mock_socket_obj = MagicMock()
        mock_socket.return_value = mock_socket_obj

        error_result = IrisMonitorResult(
            state=IrisHealthState.ERROR,
            is_healthy=False,
            message="Error - Container has problems",
        )
        mock_monitor.return_value = error_result

        with pytest.raises(TimeoutError, match="IRIS Monitor.State check did not pass"):
            wait_for_healthy(container, timeout=5)

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.ContainerState.from_container")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    @patch("socket.create_connection")
    def test_progress_callback_invoked(self, mock_socket, mock_monitor, mock_container_state, mock_sleep):
        """Test progress callback is invoked throughout."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {"Health": {"Status": "healthy"}},
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}},
        }

        mock_socket_obj = MagicMock()
        mock_socket.return_value = mock_socket_obj

        monitor_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        mock_monitor.return_value = monitor_result

        expected_state = MagicMock(spec=ContainerState)
        mock_container_state.return_value = expected_state

        callback = MagicMock()

        result = wait_for_healthy(container, timeout=60, progress_callback=callback)

        assert result == expected_state
        # Callback should have been called for multiple layers
        assert callback.call_count >= 4

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.ContainerState.from_container")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    @patch("socket.create_connection")
    def test_no_docker_health_check_skips_layer2(self, mock_socket, mock_monitor, mock_container_state, mock_sleep):
        """Test skips Layer 2 when no Docker health check defined."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {},  # No Health info
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}},
        }

        mock_socket_obj = MagicMock()
        mock_socket.return_value = mock_socket_obj

        monitor_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        mock_monitor.return_value = monitor_result

        expected_state = MagicMock(spec=ContainerState)
        mock_container_state.return_value = expected_state

        result = wait_for_healthy(container, timeout=60)

        assert result == expected_state

    @patch("time.sleep")
    @patch("iris_devtester.utils.health_checks.ContainerState.from_container")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_no_port_mapping_skips_layer3(self, mock_monitor, mock_container_state, mock_sleep):
        """Test skips Layer 3 when no port mapping found."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {"Health": {"Status": "healthy"}},
            "NetworkSettings": {"Ports": {}},  # No port mapping
        }

        monitor_result = IrisMonitorResult(
            state=IrisHealthState.OK,
            is_healthy=True,
            message="OK - Container healthy",
        )
        mock_monitor.return_value = monitor_result

        expected_state = MagicMock(spec=ContainerState)
        mock_container_state.return_value = expected_state

        result = wait_for_healthy(container, timeout=60)

        assert result == expected_state

    @patch("time.sleep")
    def test_docker_health_check_starting_then_timeout(self, mock_sleep):
        """Test Docker health check stays in starting state and times out."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        # Health check stays in "starting" state
        container.attrs = {
            "State": {
                "Health": {
                    "Status": "starting",
                }
            },
        }

        with pytest.raises(TimeoutError, match="Container health check did not pass within 5 seconds"):
            wait_for_healthy(container, timeout=5)

    @patch("time.sleep")
    @patch("socket.create_connection")
    @patch("iris_devtester.utils.health_checks.check_iris_monitor_state")
    def test_iris_monitor_stays_unhealthy_timeout(self, mock_monitor, mock_socket, mock_sleep):
        """Test IRIS Monitor.State stays unhealthy until timeout."""
        container = MagicMock()
        container.name = "test_iris"
        container.status = "running"
        container.attrs = {
            "State": {"Health": {"Status": "healthy"}},
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}},
        }

        mock_socket_obj = MagicMock()
        mock_socket.return_value = mock_socket_obj

        # Monitor always returns unhealthy
        error_result = IrisMonitorResult(
            state=IrisHealthState.ERROR,
            is_healthy=False,
            message="Error - Container has problems",
        )
        mock_monitor.return_value = error_result

        with pytest.raises(TimeoutError, match="IRIS Monitor.State check did not pass within 5 seconds"):
            wait_for_healthy(container, timeout=5)
