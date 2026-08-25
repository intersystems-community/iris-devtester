"""
Comprehensive unit tests for wait_strategies.py and dev_instance.py modules.

Focuses on uncovered lines and edge cases without requiring Docker or IRIS.
"""

import hashlib
import os
import socket
import subprocess
import time
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# ============================================================================
# TESTS FOR wait_strategies.py
# ============================================================================


class TestIRISReadyWaitStrategyInit:
    """Test IRISReadyWaitStrategy initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy()
        assert strategy.port == 1972
        assert strategy.timeout == 60
        assert strategy.poll_interval == 1.0

    def test_init_with_custom_values(self):
        """Test initialization with custom parameters."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy(port=2000, timeout=30, poll_interval=0.5)
        assert strategy.port == 2000
        assert strategy.timeout == 30
        assert strategy.poll_interval == 0.5


class TestIRISReadyWaitStrategyFastPath:
    """Test fast-path readiness check (is_ready_fast)."""

    @patch("socket.socket")
    def test_is_ready_fast_success(self, mock_socket):
        """Test fast readiness check succeeds when port is open."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Port open
        mock_socket.return_value.__enter__.return_value = mock_sock

        strategy = IRISReadyWaitStrategy()
        result = strategy.is_ready_fast("localhost", 1972)

        assert result is True
        mock_sock.settimeout.assert_called_once_with(0.05)
        mock_sock.connect_ex.assert_called_once_with(("localhost", 1972))

    @patch("socket.socket")
    def test_is_ready_fast_port_closed(self, mock_socket):
        """Test fast readiness check fails when port is closed."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1  # Port closed
        mock_socket.return_value.__enter__.return_value = mock_sock

        strategy = IRISReadyWaitStrategy()
        result = strategy.is_ready_fast("localhost", 1972)

        assert result is False

    @patch("socket.socket")
    def test_is_ready_fast_exception(self, mock_socket):
        """Test fast readiness check handles exceptions gracefully."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_socket.side_effect = Exception("Socket error")

        strategy = IRISReadyWaitStrategy()
        result = strategy.is_ready_fast("localhost", 1972)

        assert result is False


class TestIRISReadyWaitStrategyCheckPort:
    """Test port checking logic (_check_port_open)."""

    @patch("socket.socket")
    def test_check_port_open_success(self, mock_socket):
        """Test port open check succeeds."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock

        strategy = IRISReadyWaitStrategy()
        result = strategy._check_port_open("localhost", 1972, timeout=2.0)

        assert result is True
        mock_sock.settimeout.assert_called_once_with(2.0)

    @patch("socket.socket")
    def test_check_port_open_connection_refused(self, mock_socket):
        """Test port open check fails when connection is refused."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket.return_value.__enter__.return_value = mock_sock

        strategy = IRISReadyWaitStrategy()
        result = strategy._check_port_open("localhost", 1972)

        assert result is False

    @patch("socket.socket")
    def test_check_port_open_exception(self, mock_socket):
        """Test port open check handles exceptions."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_socket.side_effect = OSError("Network unreachable")

        strategy = IRISReadyWaitStrategy()
        result = strategy._check_port_open("localhost", 1972)

        assert result is False


class TestIRISReadyWaitStrategyCheckIRISRunning:
    """Test IRIS process detection (check_iris_running)."""

    @patch("subprocess.run")
    def test_check_iris_running_success(self, mock_run):
        """Test IRIS process check succeeds when IRIS is running."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "IRIS\nRunning"
        mock_run.return_value = mock_result

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_running("test-container")

        assert result is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["docker", "exec", "-u", "irisowner", "test-container", "iris", "list"]
        assert kwargs["timeout"] == 5

    @patch("subprocess.run")
    def test_check_iris_running_not_running(self, mock_run):
        """Test IRIS process check fails when IRIS is not running."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_running("test-container")

        assert result is False

    @patch("subprocess.run")
    def test_check_iris_running_no_iris_in_output(self, mock_run):
        """Test IRIS process check fails when 'IRIS' is not in output."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "No running instances"
        mock_run.return_value = mock_result

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_running("test-container")

        assert result is False

    @patch("subprocess.run")
    def test_check_iris_running_subprocess_timeout(self, mock_run):
        """Test IRIS process check handles subprocess timeout."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_run.side_effect = subprocess.TimeoutExpired("iris", 5)

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_running("test-container")

        assert result is False

    @patch("subprocess.run")
    def test_check_iris_running_generic_exception(self, mock_run):
        """Test IRIS process check handles general exceptions."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_run.side_effect = Exception("Docker not available")

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_running("test-container")

        assert result is False


class TestIRISReadyWaitStrategyCheckInitialized:
    """Test IRIS initialization check (check_iris_initialized)."""

    @patch("subprocess.run")
    def test_check_iris_initialized_success(self, mock_run):
        """Test IRIS initialization check succeeds."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1"
        mock_run.return_value = mock_result

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_initialized("test-container")

        assert result is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert "docker" in args[0]
        assert "test-container" in args[0]

    @patch("subprocess.run")
    def test_check_iris_initialized_nonzero_return(self, mock_run):
        """Test IRIS initialization check fails with non-zero return code."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_initialized("test-container")

        assert result is False

    @patch("subprocess.run")
    def test_check_iris_initialized_no_output(self, mock_run):
        """Test IRIS initialization check fails when '1' not in output."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "error message"
        mock_run.return_value = mock_result

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_initialized("test-container")

        assert result is False

    @patch("subprocess.run")
    def test_check_iris_initialized_exception(self, mock_run):
        """Test IRIS initialization check handles exceptions."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)

        strategy = IRISReadyWaitStrategy()
        result = strategy.check_iris_initialized("test-container")

        assert result is False


class TestIRISReadyWaitStrategyWaitUntilReady:
    """Test main wait_until_ready method."""

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    def test_wait_until_ready_fast_path(self, mock_fast):
        """Test wait_until_ready returns immediately on fast path."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = True

        strategy = IRISReadyWaitStrategy()
        result = strategy.wait_until_ready("localhost", 1972)

        assert result is True
        mock_fast.assert_called_once_with("localhost", 1972)

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy._check_port_open")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    def test_wait_until_ready_port_only(self, mock_fast, mock_port):
        """Test wait_until_ready succeeds with port check only (no container_name)."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = False
        mock_port.return_value = True

        strategy = IRISReadyWaitStrategy(timeout=2, poll_interval=0.1)
        result = strategy.wait_until_ready("localhost", 1972, container_name=None)

        assert result is True

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.check_iris_initialized")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy._check_port_open")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    def test_wait_until_ready_with_container_initialized(self, mock_fast, mock_port, mock_init):
        """Test wait_until_ready succeeds when container is initialized."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = False
        mock_port.return_value = True
        mock_init.return_value = True

        strategy = IRISReadyWaitStrategy(timeout=2, poll_interval=0.1)
        result = strategy.wait_until_ready("localhost", 1972, container_name="test-container")

        assert result is True
        mock_init.assert_called_once_with("test-container")

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.check_iris_initialized")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy._check_port_open")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    @patch("time.sleep")
    def test_wait_until_ready_container_not_initialized_then_yes(
        self, mock_sleep, mock_fast, mock_port, mock_init
    ):
        """Test wait_until_ready retries until container is initialized."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = False
        mock_port.return_value = True
        mock_init.side_effect = [False, False, True]  # Not ready twice, then ready

        strategy = IRISReadyWaitStrategy(timeout=10, poll_interval=0.1)
        result = strategy.wait_until_ready("localhost", 1972, container_name="test-container")

        assert result is True
        assert mock_init.call_count == 3

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy._check_port_open")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    @patch("time.sleep")
    def test_wait_until_ready_timeout(self, mock_sleep, mock_fast, mock_port):
        """Test wait_until_ready raises TimeoutError when timeout exceeded."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = False
        mock_port.return_value = False

        strategy = IRISReadyWaitStrategy(timeout=1, poll_interval=0.5)

        with pytest.raises(TimeoutError) as exc_info:
            strategy.wait_until_ready("localhost", 1972)

        assert "IRIS not ready after" in str(exc_info.value)
        assert "localhost:1972" in str(exc_info.value)

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy._check_port_open")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    @patch("time.sleep")
    def test_wait_until_ready_exception_captured_in_error(self, mock_sleep, mock_fast, mock_port):
        """Test wait_until_ready includes last error in TimeoutError message."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = False
        mock_port.side_effect = RuntimeError("Connection failed")

        strategy = IRISReadyWaitStrategy(timeout=1, poll_interval=0.5)

        with pytest.raises(TimeoutError) as exc_info:
            strategy.wait_until_ready("localhost", 1972)

        error_msg = str(exc_info.value)
        assert "Last error: Connection failed" in error_msg or "Connection failed" in error_msg

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy._check_port_open")
    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.is_ready_fast")
    def test_wait_until_ready_uses_override_params(self, mock_fast, mock_port):
        """Test wait_until_ready uses provided port/timeout parameters."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        mock_fast.return_value = False
        mock_port.return_value = True

        strategy = IRISReadyWaitStrategy(port=1972, timeout=60, poll_interval=1.0)
        result = strategy.wait_until_ready("localhost", port=2000, timeout=30)

        assert result is True
        # Should be called with overridden port
        mock_fast.assert_called_once_with("localhost", 2000)


class TestWaitForIRISReadyFunction:
    """Test convenience wait_for_iris_ready function."""

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    def test_wait_for_iris_ready_success(self, mock_wait):
        """Test wait_for_iris_ready returns True on success."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        mock_wait.return_value = True

        result = wait_for_iris_ready("localhost", 1972, timeout=60)

        assert result is True

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    def test_wait_for_iris_ready_timeout(self, mock_wait):
        """Test wait_for_iris_ready returns False on timeout."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        mock_wait.side_effect = TimeoutError("Timeout")

        result = wait_for_iris_ready("localhost", 1972, timeout=1)

        assert result is False

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    def test_wait_for_iris_ready_generic_exception(self, mock_wait):
        """Test wait_for_iris_ready returns False on generic exception."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        mock_wait.side_effect = RuntimeError("Docker not found")

        result = wait_for_iris_ready("localhost", 1972, timeout=1)

        assert result is False

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    def test_wait_for_iris_ready_uses_defaults(self, mock_wait):
        """Test wait_for_iris_ready uses default parameters."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        mock_wait.return_value = True

        result = wait_for_iris_ready()

        assert result is True
        # Should be called with defaults
        mock_wait.assert_called_once()
        args, kwargs = mock_wait.call_args
        assert args[0] == "localhost"
        assert args[1] == 1972


class TestFHIRReadyWaitStrategy:
    """Test FHIR-specific wait strategy."""

    def test_fhir_init_defaults(self):
        """Test FHIRReadyWaitStrategy initialization with defaults."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy

        strategy = FHIRReadyWaitStrategy()
        assert strategy.superserver_port == 1972
        assert strategy.web_port == 52773
        assert strategy.fhir_app_key == "/csp/healthshare/demo/fhir/r4"
        assert strategy.timeout == 90
        assert strategy.poll_interval == 2.0

    def test_fhir_init_custom(self):
        """Test FHIRReadyWaitStrategy initialization with custom values."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy

        strategy = FHIRReadyWaitStrategy(
            superserver_port=1973,
            web_port=52774,
            fhir_app_key="/custom/fhir",
            timeout=120,
            poll_interval=1.0,
        )
        assert strategy.superserver_port == 1973
        assert strategy.web_port == 52774
        assert strategy.fhir_app_key == "/custom/fhir"
        assert strategy.timeout == 120
        assert strategy.poll_interval == 1.0

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_fhir_wait_until_ready_success(self, mock_sleep, mock_urlopen, mock_iris_wait):
        """Test FHIRReadyWaitStrategy.wait_until_ready succeeds."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy

        mock_iris_wait.return_value = True
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        strategy = FHIRReadyWaitStrategy(timeout=10, poll_interval=0.1)
        result = strategy.wait_until_ready("localhost", mapped_web_port=52773)

        assert result is True

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    def test_fhir_wait_until_ready_iris_fails(self, mock_iris_wait):
        """Test FHIRReadyWaitStrategy propagates IRIS wait failure."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy

        mock_iris_wait.side_effect = TimeoutError("IRIS timeout")

        strategy = FHIRReadyWaitStrategy(timeout=10)

        with pytest.raises(TimeoutError):
            strategy.wait_until_ready("localhost")

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_fhir_wait_until_ready_url_error(self, mock_sleep, mock_urlopen, mock_iris_wait):
        """Test FHIRReadyWaitStrategy retries on URL errors."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy
        import urllib.error

        mock_iris_wait.return_value = True
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        strategy = FHIRReadyWaitStrategy(timeout=1, poll_interval=0.1)

        with pytest.raises(TimeoutError) as exc_info:
            strategy.wait_until_ready("localhost")

        assert "FHIR endpoint not ready" in str(exc_info.value)

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_fhir_wait_until_ready_eventually_succeeds(self, mock_sleep, mock_urlopen, mock_iris_wait):
        """Test FHIRReadyWaitStrategy retries until FHIR endpoint is ready."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy
        import urllib.error

        mock_iris_wait.return_value = True
        mock_response = MagicMock()
        mock_response.status = 200
        # Fail twice, then succeed
        mock_urlopen.side_effect = [
            urllib.error.URLError("Connection refused"),
            urllib.error.URLError("Connection refused"),
            MagicMock(__enter__=MagicMock(return_value=mock_response)),
        ]

        strategy = FHIRReadyWaitStrategy(timeout=10, poll_interval=0.1)
        result = strategy.wait_until_ready("localhost")

        assert result is True

    @patch("iris_devtester.containers.wait_strategies.IRISReadyWaitStrategy.wait_until_ready")
    @patch("urllib.request.urlopen")
    def test_fhir_uses_mapped_port(self, mock_urlopen, mock_iris_wait):
        """Test FHIRReadyWaitStrategy uses mapped port when provided."""
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy

        mock_iris_wait.return_value = True
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        strategy = FHIRReadyWaitStrategy(timeout=1, web_port=52773)
        strategy.wait_until_ready("localhost", mapped_web_port=9999)

        # Should use mapped port in URL
        call_args = mock_urlopen.call_args
        url = call_args[0][0]
        assert "9999" in url


# ============================================================================
# TESTS FOR dev_instance.py
# ============================================================================


class TestDockerVolumeManagerInit:
    """Test DockerVolumeManager initialization."""

    @patch("docker.from_env")
    def test_init_with_default_client(self, mock_docker):
        """Test DockerVolumeManager uses docker.from_env() by default."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager

        mock_client = MagicMock()
        mock_docker.return_value = mock_client

        manager = DockerVolumeManager()

        assert manager.client == mock_client
        mock_docker.assert_called_once()

    def test_init_with_provided_client(self):
        """Test DockerVolumeManager accepts provided client."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager

        mock_client = MagicMock()
        manager = DockerVolumeManager(client=mock_client)

        assert manager.client == mock_client


class TestDockerVolumeManagerGetOrCreate:
    """Test volume get_or_create logic."""

    def test_get_existing_volume(self):
        """Test get_or_create returns existing volume."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager

        mock_client = MagicMock()
        mock_volume = MagicMock()
        mock_client.volumes.get.return_value = mock_volume

        manager = DockerVolumeManager(client=mock_client)
        result = manager.get_or_create("test-volume")

        assert result == mock_volume
        mock_client.volumes.get.assert_called_once_with("test-volume")
        mock_client.containers.run.assert_not_called()

    def test_create_new_volume(self):
        """Test get_or_create creates new volume when not found."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_volume = MagicMock()
        mock_client.volumes.get.side_effect = NotFound("Not found")
        mock_client.volumes.create.return_value = mock_volume

        manager = DockerVolumeManager(client=mock_client)
        result = manager.get_or_create("test-volume")

        assert result == mock_volume
        mock_client.volumes.create.assert_called_once_with(name="test-volume")
        # Should run chown container
        mock_client.containers.run.assert_called_once()
        call_args = mock_client.containers.run.call_args
        assert "busybox" in call_args[0]

    def test_create_volume_sets_permissions(self):
        """Test get_or_create sets proper permissions on new volume."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_volume = MagicMock()
        mock_client.volumes.get.side_effect = NotFound("Not found")
        mock_client.volumes.create.return_value = mock_volume

        manager = DockerVolumeManager(client=mock_client)
        manager.get_or_create("idt-dev-data")

        # Verify chown command was run with correct UID
        call_args = mock_client.containers.run.call_args
        assert call_args[0][1] == "chown -R 51773:51773 /iris/data"
        assert call_args[1]["remove"] is True


class TestDockerVolumeManagerRemove:
    """Test volume removal logic."""

    def test_remove_existing_volume(self):
        """Test remove successfully removes existing volume."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager

        mock_client = MagicMock()
        mock_volume = MagicMock()
        mock_client.volumes.get.return_value = mock_volume

        manager = DockerVolumeManager(client=mock_client)
        result = manager.remove("test-volume")

        assert result is True
        mock_client.volumes.get.assert_called_once_with("test-volume")
        mock_volume.remove.assert_called_once_with(force=True)

    def test_remove_nonexistent_volume(self):
        """Test remove returns False for non-existent volume."""
        from iris_devtester.containers.dev_instance import DockerVolumeManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.volumes.get.side_effect = NotFound("Not found")

        manager = DockerVolumeManager(client=mock_client)
        result = manager.remove("nonexistent-volume")

        assert result is False


class TestDevInstanceManagerInit:
    """Test DevInstanceManager initialization."""

    @patch("docker.from_env")
    def test_init_with_default_client(self, mock_docker):
        """Test DevInstanceManager uses docker.from_env() by default."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_docker.return_value = mock_client

        manager = DevInstanceManager()

        assert manager.client == mock_client
        assert isinstance(manager.volume_manager, object)

    def test_init_with_provided_client(self):
        """Test DevInstanceManager accepts provided client."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        manager = DevInstanceManager(client=mock_client)

        assert manager.client == mock_client


class TestDevInstanceManagerGetInstance:
    """Test instance retrieval logic."""

    def test_get_existing_instance(self):
        """Test get_instance returns existing container."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.get_instance()

        assert result == mock_container
        mock_client.containers.get.assert_called_once_with("idt-dev-instance")

    def test_get_nonexistent_instance(self):
        """Test get_instance returns None for non-existent container."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")

        manager = DevInstanceManager(client=mock_client)
        result = manager.get_instance()

        assert result is None


class TestDevInstanceManagerIsRunning:
    """Test running status check."""

    def test_is_running_when_running(self):
        """Test is_running returns True when container is running."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.is_running()

        assert result is True

    def test_is_running_when_stopped(self):
        """Test is_running returns False when container is stopped."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.is_running()

        assert result is False

    def test_is_running_when_not_exists(self):
        """Test is_running returns False when container does not exist."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")

        manager = DevInstanceManager(client=mock_client)
        result = manager.is_running()

        assert result is False


class TestDevInstanceManagerFindAvailablePort:
    """Test port availability checking."""

    def test_find_available_port_first_is_free(self):
        """Test find_available_port returns first port when free."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        manager = DevInstanceManager(client=mock_client)

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            mock_sock.bind.return_value = None  # Success

            port = manager._find_available_port(1972)

            assert port == 1972

    def test_find_available_port_increments(self):
        """Test find_available_port increments when ports are in use."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        manager = DevInstanceManager(client=mock_client)

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            # First two ports fail, third succeeds
            mock_sock.bind.side_effect = [OSError("Port in use"), OSError("Port in use"), None]

            port = manager._find_available_port(1972)

            assert port == 1974

    def test_find_available_port_raises_when_all_busy(self):
        """Test find_available_port raises when all ports in range are busy."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        manager = DevInstanceManager(client=mock_client)

        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            mock_sock.bind.side_effect = OSError("Port in use")

            with pytest.raises(RuntimeError) as exc_info:
                manager._find_available_port(1972)

            assert "Could not find available port" in str(exc_info.value)


class TestDevInstanceManagerEnsureReady:
    """Test ensure_ready logic."""

    @patch("iris_devtester.containers.dev_instance.IRISContainerManager.create_from_config")
    def test_ensure_ready_creates_instance_when_not_exists(self, mock_create):
        """Test ensure_ready creates instance when it doesn't exist."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_create.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.ensure_ready()

        assert result == mock_container
        mock_create.assert_called_once()

    @patch("iris_devtester.containers.dev_instance.IRISContainerManager.create_from_config")
    def test_ensure_ready_starts_stopped_instance(self, mock_create):
        """Test ensure_ready starts stopped instance."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.ensure_ready()

        assert result == mock_container
        mock_container.start.assert_called_once()

    def test_ensure_ready_returns_running_instance(self):
        """Test ensure_ready returns already running instance."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.ensure_ready()

        assert result == mock_container
        mock_container.start.assert_not_called()

    @patch("iris_devtester.containers.dev_instance.IRISContainerManager.create_from_config")
    def test_ensure_ready_force_removes_instance(self, mock_create):
        """Test ensure_ready removes instance when force=True."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_old_container = MagicMock()
        mock_new_container = MagicMock()
        mock_new_container.status = "running"

        # First call returns old, then None for new instance
        mock_client.containers.get.side_effect = [mock_old_container, None, mock_new_container]
        mock_create.return_value = mock_new_container

        manager = DevInstanceManager(client=mock_client)
        result = manager.ensure_ready(force=True)

        assert result == mock_new_container
        mock_old_container.remove.assert_called_once_with(force=True)

    @patch("iris_devtester.containers.dev_instance.IRISContainerManager.create_from_config")
    def test_ensure_ready_uses_custom_image(self, mock_create):
        """Test ensure_ready uses custom image when provided."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_create.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        manager.ensure_ready(image="custom-iris:latest")

        # Verify config was created with custom image
        call_args = mock_create.call_args
        config = call_args[0][0]
        assert config.image == "custom-iris:latest"

    @patch("iris_devtester.containers.dev_instance.IRISContainerManager.create_from_config")
    def test_ensure_ready_sets_durable_sys(self, mock_create):
        """Test ensure_ready configures durable %SYS."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_create.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        manager.ensure_ready()

        # Verify durable_sys was set
        call_args = mock_create.call_args
        config = call_args[0][0]
        assert config.durable_sys is True
        assert config.isc_data_directory == "/iris/data"


class TestDevInstanceManagerStop:
    """Test instance stopping."""

    def test_stop_running_instance(self):
        """Test stop stops running instance."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        manager.stop()

        mock_container.stop.assert_called_once()

    def test_stop_when_not_exists(self):
        """Test stop handles non-existent instance gracefully."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")

        manager = DevInstanceManager(client=mock_client)
        manager.stop()  # Should not raise


class TestDevInstanceManagerRemove:
    """Test instance removal."""

    def test_remove_instance(self):
        """Test remove removes instance."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container

        manager = DevInstanceManager(client=mock_client)
        manager.remove()

        mock_container.remove.assert_called_once_with(force=True)

    def test_remove_with_volumes(self):
        """Test remove also removes volumes when specified."""
        from iris_devtester.containers.dev_instance import DevInstanceManager

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_volume = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_client.volumes.get.return_value = mock_volume

        manager = DevInstanceManager(client=mock_client)
        manager.remove(remove_volumes=True)

        mock_container.remove.assert_called_once_with(force=True)
        mock_volume.remove.assert_called_once_with(force=True)

    def test_remove_when_not_exists(self):
        """Test remove handles non-existent instance gracefully."""
        from iris_devtester.containers.dev_instance import DevInstanceManager
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Not found")

        manager = DevInstanceManager(client=mock_client)
        manager.remove()  # Should not raise


class TestGetProjectId:
    """Test project ID generation."""

    def test_get_project_id_default_path(self):
        """Test get_project_id uses current directory by default."""
        from iris_devtester.containers.dev_instance import get_project_id

        pid = get_project_id()

        assert isinstance(pid, str)
        assert len(pid) == 11
        assert pid.isupper()

    def test_get_project_id_custom_path(self):
        """Test get_project_id hashes custom path."""
        from iris_devtester.containers.dev_instance import get_project_id

        pid = get_project_id("/some/path/to/project")

        assert isinstance(pid, str)
        assert len(pid) == 11
        assert pid.isupper()

    def test_get_project_id_stable(self):
        """Test get_project_id produces stable hash for same path."""
        from iris_devtester.containers.dev_instance import get_project_id

        path = "/some/path/to/project"
        pid1 = get_project_id(path)
        pid2 = get_project_id(path)

        assert pid1 == pid2

    def test_get_project_id_unique(self):
        """Test get_project_id produces different hashes for different paths."""
        from iris_devtester.containers.dev_instance import get_project_id

        pid1 = get_project_id("/path1")
        pid2 = get_project_id("/path2")

        assert pid1 != pid2

    def test_get_project_id_uses_sha256(self):
        """Test get_project_id uses SHA256 hashing."""
        from iris_devtester.containers.dev_instance import get_project_id

        path = "/test/path"
        expected_hash = hashlib.sha256(path.encode()).hexdigest()
        expected_id = expected_hash[:11].upper()

        pid = get_project_id(path)

        assert pid == expected_id


class TestGetProjectNamespace:
    """Test project namespace generation."""

    def test_get_project_namespace_default_path(self):
        """Test get_project_namespace uses current directory by default."""
        from iris_devtester.containers.dev_instance import get_project_namespace

        ns = get_project_namespace()

        assert isinstance(ns, str)
        assert ns.startswith("P")
        assert len(ns) == 12
        assert ns.isupper()

    def test_get_project_namespace_custom_path(self):
        """Test get_project_namespace hashes custom path."""
        from iris_devtester.containers.dev_instance import get_project_namespace

        ns = get_project_namespace("/some/path")

        assert ns.startswith("P")
        assert len(ns) == 12
        assert ns.isupper()

    def test_get_project_namespace_stable(self):
        """Test get_project_namespace produces stable name for same path."""
        from iris_devtester.containers.dev_instance import get_project_namespace

        path = "/some/path"
        ns1 = get_project_namespace(path)
        ns2 = get_project_namespace(path)

        assert ns1 == ns2

    def test_get_project_namespace_unique(self):
        """Test get_project_namespace produces different names for different paths."""
        from iris_devtester.containers.dev_instance import get_project_namespace

        ns1 = get_project_namespace("/path1")
        ns2 = get_project_namespace("/path2")

        assert ns1 != ns2

    def test_get_project_namespace_format(self):
        """Test get_project_namespace format is P + 11-char hash."""
        from iris_devtester.containers.dev_instance import get_project_namespace, get_project_id

        path = "/test/path"
        pid = get_project_id(path)
        ns = get_project_namespace(path)

        assert ns == f"P{pid}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
