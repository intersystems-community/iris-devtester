"""
Comprehensive unit tests for iris_devtester config and container models.

Tests three modules with high coverage:
- iris_devtester/config/auto_discovery.py (10% → 75%+)
- iris_devtester/config/discovery.py (72% → 85%+)
- iris_devtester/containers/models.py (70% → 85%+)

All tests are pure unit tests with mocked subprocess, docker, and file I/O.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# ============================================================================
# Tests for iris_devtester/config/auto_discovery.py
# ============================================================================


class TestDiscoverIrisPort:
    """Test discover_iris_port() function."""

    def test_default_ports(self):
        """Test that default ports are [31972, 1972, 11972, 21972]."""
        with patch("iris_devtester.config.auto_discovery._test_iris_port") as mock_test:
            mock_test.return_value = False
            from iris_devtester.config.auto_discovery import discover_iris_port

            discover_iris_port()
            # Should call _test_iris_port for each default port
            assert mock_test.call_count == 4
            call_args = [call[0][0] for call in mock_test.call_args_list]
            assert call_args == [31972, 1972, 11972, 21972]

    def test_finds_first_responding_port(self):
        """Test that function returns first port that responds."""
        with patch("iris_devtester.config.auto_discovery._test_iris_port") as mock_test:
            # Third port responds
            mock_test.side_effect = [False, False, True, False]
            from iris_devtester.config.auto_discovery import discover_iris_port

            result = discover_iris_port()
            assert result == 11972

    def test_returns_none_when_no_port_responds(self):
        """Test that function returns None when no port responds."""
        with patch("iris_devtester.config.auto_discovery._test_iris_port") as mock_test:
            mock_test.return_value = False
            from iris_devtester.config.auto_discovery import discover_iris_port

            result = discover_iris_port()
            assert result is None

    def test_respects_custom_test_ports(self):
        """Test that custom port list is used when provided."""
        with patch("iris_devtester.config.auto_discovery._test_iris_port") as mock_test:
            mock_test.return_value = False
            from iris_devtester.config.auto_discovery import discover_iris_port

            discover_iris_port(test_ports=[9999, 8888])
            call_args = [call[0][0] for call in mock_test.call_args_list]
            assert call_args == [9999, 8888]

    def test_stops_after_first_success(self):
        """Test that function stops testing after first success."""
        with patch("iris_devtester.config.auto_discovery._test_iris_port") as mock_test:
            mock_test.side_effect = [True, True, True, True]
            from iris_devtester.config.auto_discovery import discover_iris_port

            result = discover_iris_port()
            assert result == 31972
            # Should only call once (first port succeeds)
            assert mock_test.call_count == 1


class TestTestIrisPort:
    """Test _test_iris_port() function."""

    def test_success_case(self):
        """Test successful IRIS port detection."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="SUCCESS", returncode=0)
            from iris_devtester.config.auto_discovery import _test_iris_port

            result = _test_iris_port(1972)
            assert result is True

    def test_failed_case(self):
        """Test failed IRIS port detection."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="FAILED", returncode=1)
            from iris_devtester.config.auto_discovery import _test_iris_port

            result = _test_iris_port(1972)
            assert result is False

    def test_timeout_handling(self):
        """Test timeout exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
            from iris_devtester.config.auto_discovery import _test_iris_port

            result = _test_iris_port(1972, timeout=5)
            assert result is False

    def test_file_not_found_handling(self):
        """Test FileNotFoundError handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("python not found")
            from iris_devtester.config.auto_discovery import _test_iris_port

            result = _test_iris_port(1972)
            assert result is False

    def test_generic_exception_handling(self):
        """Test generic exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Some error")
            from iris_devtester.config.auto_discovery import _test_iris_port

            result = _test_iris_port(1972)
            assert result is False

    def test_custom_timeout(self):
        """Test that custom timeout is passed to subprocess.run."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="SUCCESS")
            from iris_devtester.config.auto_discovery import _test_iris_port

            _test_iris_port(1972, timeout=10)
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["timeout"] == 10


class TestDiscoverDockerIris:
    """Test discover_docker_iris() function."""

    def test_successful_discovery(self):
        """Test successful Docker IRIS discovery."""
        docker_output = "iris-dev\t0.0.0.0:11972->1972/tcp\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=docker_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is not None
            assert result["port"] == 11972
            assert result["container_name"] == "iris-dev"
            assert result["host"] == "localhost"

    def test_no_iris_containers(self):
        """Test when no IRIS containers are found."""
        docker_output = "mysql-db\t0.0.0.0:3306->3306/tcp\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=docker_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None

    def test_specific_container_name(self):
        """Test discovery with specific container name."""
        docker_output = "iris-test\t0.0.0.0:21972->1972/tcp\niris-dev\t0.0.0.0:11972->1972/tcp\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=docker_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris(container_name="iris-test")
            assert result is not None
            assert result["port"] == 21972
            assert result["container_name"] == "iris-test"

    def test_docker_not_available(self):
        """Test handling when docker is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None

    def test_docker_ps_fails(self):
        """Test handling when docker ps returns error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None

    def test_docker_ps_timeout(self):
        """Test handling when docker ps times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker ps", 5)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None

    def test_docker_generic_exception(self):
        """Test generic exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Docker error")
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None

    def test_empty_docker_output(self):
        """Test handling of empty docker ps output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None

    def test_returns_expected_config_keys(self):
        """Test that returned config has all expected keys."""
        docker_output = "iris-db\t0.0.0.0:11972->1972/tcp\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=docker_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert "host" in result
            assert "port" in result
            assert "username" in result
            assert "password" in result
            assert "namespace" in result
            assert "container_name" in result

    def test_specific_container_name_not_found(self):
        """Test when specific container name doesn't match any line."""
        docker_output = "iris-dev\t0.0.0.0:11972->1972/tcp\niris-test\t0.0.0.0:21972->1972/tcp\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=docker_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris(container_name="iris-missing")
            assert result is None

    def test_docker_port_regex_no_match(self):
        """Test when docker output doesn't match port regex."""
        docker_output = "iris-db\t0.0.0.0:11972->3306/tcp\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=docker_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_docker_iris

            result = discover_docker_iris()
            assert result is None


class TestDiscoverNativeIris:
    """Test discover_native_iris() function."""

    def test_successful_discovery(self):
        """Test successful native IRIS discovery."""
        iris_output = """Instance 'iris'
        status: running, since 2026-01-01 10:00:00
        SuperServers: 1972
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=iris_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is not None
            assert result["port"] == 1972

    def test_no_running_instances(self):
        """Test when no running instances found."""
        iris_output = """Instance 'iris'
        status: stopped
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=iris_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is None

    def test_iris_command_not_found(self):
        """Test handling when 'iris' command is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("iris not found")
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is None

    def test_iris_list_fails(self):
        """Test handling when 'iris list' returns error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is None

    def test_iris_list_timeout(self):
        """Test handling when 'iris list' times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("iris list", 5)
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is None

    def test_returns_expected_config_keys(self):
        """Test that returned config has all expected keys."""
        iris_output = """Instance 'iris'
        status: running, since 2026-01-01 10:00:00
        SuperServers: 1972
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=iris_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert "host" in result
            assert "port" in result
            assert "username" in result
            assert "password" in result
            assert "namespace" in result

    def test_generic_exception_handling(self):
        """Test handling of generic exceptions."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is None

    def test_superservers_parsing_boundary(self):
        """Test when SuperServers appears at end of output."""
        iris_output = """Instance 'iris'
        status: running
        Something else
        Something else
        SuperServers: 2972
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=iris_output, returncode=0)
            from iris_devtester.config.auto_discovery import discover_native_iris

            result = discover_native_iris()
            assert result is not None
            assert result["port"] == 2972


class TestAutoDiscoverIris:
    """Test auto_discover_iris() function."""

    def test_docker_first_priority(self):
        """Test that Docker discovery is tried first."""
        docker_config = {
            "host": "localhost",
            "port": 11972,
            "username": "_SYSTEM",
            "password": "SYS",
            "namespace": "USER",
            "container_name": "iris-dev",
        }
        with patch(
            "iris_devtester.config.auto_discovery.discover_docker_iris"
        ) as mock_docker, patch(
            "iris_devtester.config.auto_discovery.discover_native_iris"
        ) as mock_native:
            mock_docker.return_value = docker_config
            mock_native.return_value = None
            from iris_devtester.config.auto_discovery import auto_discover_iris

            result = auto_discover_iris()
            assert result == docker_config
            # Native should not be called if Docker succeeds
            mock_native.assert_not_called()

    def test_native_second_priority(self):
        """Test that native discovery is tried second."""
        native_config = {
            "host": "localhost",
            "port": 1972,
            "username": "_SYSTEM",
            "password": "SYS",
            "namespace": "USER",
        }
        with patch(
            "iris_devtester.config.auto_discovery.discover_docker_iris"
        ) as mock_docker, patch(
            "iris_devtester.config.auto_discovery.discover_native_iris"
        ) as mock_native:
            mock_docker.return_value = None
            mock_native.return_value = native_config
            from iris_devtester.config.auto_discovery import auto_discover_iris

            result = auto_discover_iris()
            assert result == native_config

    def test_port_scan_third_priority(self):
        """Test that port scanning is tried third."""
        with patch(
            "iris_devtester.config.auto_discovery.discover_docker_iris"
        ) as mock_docker, patch(
            "iris_devtester.config.auto_discovery.discover_native_iris"
        ) as mock_native, patch(
            "iris_devtester.config.auto_discovery.discover_iris_port"
        ) as mock_scan:
            mock_docker.return_value = None
            mock_native.return_value = None
            mock_scan.return_value = 11972
            from iris_devtester.config.auto_discovery import auto_discover_iris

            result = auto_discover_iris()
            assert result is not None
            assert result["port"] == 11972

    def test_all_methods_fail(self):
        """Test when all discovery methods fail."""
        with patch(
            "iris_devtester.config.auto_discovery.discover_docker_iris"
        ) as mock_docker, patch(
            "iris_devtester.config.auto_discovery.discover_native_iris"
        ) as mock_native, patch(
            "iris_devtester.config.auto_discovery.discover_iris_port"
        ) as mock_scan:
            mock_docker.return_value = None
            mock_native.return_value = None
            mock_scan.return_value = None
            from iris_devtester.config.auto_discovery import auto_discover_iris

            result = auto_discover_iris()
            assert result is None

    def test_container_name_passed_to_docker(self):
        """Test that container_name is passed to docker discovery."""
        with patch(
            "iris_devtester.config.auto_discovery.discover_docker_iris"
        ) as mock_docker:
            mock_docker.return_value = None
            with patch(
                "iris_devtester.config.auto_discovery.discover_native_iris"
            ) as mock_native:
                mock_native.return_value = None
                with patch(
                    "iris_devtester.config.auto_discovery.discover_iris_port"
                ) as mock_scan:
                    mock_scan.return_value = None
                    from iris_devtester.config.auto_discovery import auto_discover_iris

                    auto_discover_iris(container_name="iris-test")
                    mock_docker.assert_called_with(container_name="iris-test")


# ============================================================================
# Tests for iris_devtester/config/discovery.py
# ============================================================================


class TestDiscoverConfig:
    """Test discover_config() function."""

    def test_explicit_config_returned_immediately(self):
        """Test that explicit config is returned without trying other sources."""
        from iris_devtester.config.models import IRISConfig
        from iris_devtester.config.discovery import discover_config

        explicit = IRISConfig(host="explicit.host", port=9999)
        result = discover_config(explicit_config=explicit)
        assert result is explicit
        assert result.host == "explicit.host"
        assert result.port == 9999

    def test_defaults_applied(self):
        """Test that defaults are applied."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {}
            mock_os_env.return_value = {}
            mock_dev_instance = MagicMock()
            mock_dev_instance.return_value.get_instance.return_value = None
            mock_dev.return_value = mock_dev_instance
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                assert result.host == "localhost"
                assert result.port == 1972
                assert result.namespace == "USER"

    def test_env_vars_override_defaults(self):
        """Test that environment variables override defaults."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {}
            mock_os_env.return_value = {
                "host": "env.host",
                "port": 9999,
                "namespace": "ENVNS",
            }
            mock_dev_instance = MagicMock()
            mock_dev_instance.return_value.get_instance.return_value = None
            mock_dev.return_value = mock_dev_instance
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                assert result.host == "env.host"
                assert result.port == 9999
                assert result.namespace == "ENVNS"

    def test_dotenv_overrides_defaults(self):
        """Test that .env file overrides defaults."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {"host": "dotenv.host", "port": 8888}
            mock_os_env.return_value = {}
            mock_dev_instance = MagicMock()
            mock_dev_instance.return_value.get_instance.return_value = None
            mock_dev.return_value = mock_dev_instance
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                assert result.host == "dotenv.host"
                assert result.port == 8888

    def test_env_vars_override_dotenv(self):
        """Test that environment variables override .env."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {"host": "dotenv.host"}
            mock_os_env.return_value = {"host": "os_env.host"}
            mock_dev_instance = MagicMock()
            mock_dev_instance.return_value.get_instance.return_value = None
            mock_dev.return_value = mock_dev_instance
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                assert result.host == "os_env.host"

    def test_dev_instance_detected_and_running(self):
        """Test detection of persistent dev instance."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {}
            mock_os_env.return_value = {}
            # Create a properly configured mock
            dev_inst = Mock()
            dev_inst.status = "running"
            dev_inst.name = "iris-dev"
            dev_inst.attrs = {
                "NetworkSettings": {
                    "Ports": {"1972/tcp": [{"HostPort": "11972"}]}
                }
            }
            mock_dev_manager = Mock()
            mock_dev_manager.get_instance.return_value = dev_inst
            mock_dev.return_value = mock_dev_manager
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                assert result.port == 11972
                assert result.container_name == "iris-dev"

    def test_dev_instance_not_running(self):
        """Test that stopped dev instances are ignored."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {}
            mock_os_env.return_value = {}
            dev_inst = Mock()
            dev_inst.status = "exited"
            mock_dev_manager = Mock()
            mock_dev_manager.get_instance.return_value = dev_inst
            mock_dev.return_value = mock_dev_manager
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                # Should use defaults since dev instance is not running
                assert result.port == 1972

    def test_auto_detect_returns_host_and_port(self):
        """Test when auto_detect_iris_host_and_port returns values."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {}
            mock_os_env.return_value = {}
            mock_dev_manager = Mock()
            mock_dev_manager.get_instance.return_value = None
            mock_dev.return_value = mock_dev_manager
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = ("auto.host", 9999)
                from iris_devtester.config.discovery import discover_config

                result = discover_config()
                assert result.host == "auto.host"
                assert result.port == 9999

    def test_container_name_propagated_to_config(self):
        """Test that container_name is propagated when auto-detected."""
        with patch("iris_devtester.config.discovery._load_from_dotenv") as mock_env, patch(
            "iris_devtester.config.discovery._load_from_environment"
        ) as mock_os_env, patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_dev:
            mock_env.return_value = {}
            mock_os_env.return_value = {}
            mock_dev_manager = Mock()
            mock_dev_manager.get_instance.return_value = None
            mock_dev.return_value = mock_dev_manager
            with patch(
                "iris_devtester.connections.auto_discovery.auto_detect_iris_host_and_port"
            ) as mock_auto:
                mock_auto.return_value = (None, None)
                from iris_devtester.config.discovery import discover_config

                result = discover_config(container_name="iris-specific")
                assert result.container_name == "iris-specific"


class TestLoadFromEnvironment:
    """Test _load_from_environment() function."""

    def test_loads_iris_host(self):
        """Test loading IRIS_HOST from environment."""
        with patch.dict(os.environ, {"IRIS_HOST": "test.host"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["host"] == "test.host"

    def test_loads_iris_port(self):
        """Test loading IRIS_PORT from environment."""
        with patch.dict(os.environ, {"IRIS_PORT": "9999"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["port"] == 9999

    def test_loads_iris_namespace(self):
        """Test loading IRIS_NAMESPACE from environment."""
        with patch.dict(os.environ, {"IRIS_NAMESPACE": "CUSTOM"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["namespace"] == "CUSTOM"

    def test_loads_iris_username(self):
        """Test loading IRIS_USERNAME from environment."""
        with patch.dict(os.environ, {"IRIS_USERNAME": "admin"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["username"] == "admin"

    def test_loads_iris_password(self):
        """Test loading IRIS_PASSWORD from environment."""
        with patch.dict(os.environ, {"IRIS_PASSWORD": "secretpass"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["password"] == "secretpass"

    def test_loads_iris_driver(self):
        """Test loading IRIS_DRIVER from environment."""
        with patch.dict(os.environ, {"IRIS_DRIVER": "dbapi"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["driver"] == "dbapi"

    def test_loads_iris_timeout(self):
        """Test loading IRIS_TIMEOUT from environment."""
        with patch.dict(os.environ, {"IRIS_TIMEOUT": "60"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["timeout"] == 60

    def test_loads_iris_auto_create_true(self):
        """Test loading IRIS_AUTO_CREATE=true from environment."""
        with patch.dict(os.environ, {"IRIS_AUTO_CREATE": "true"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["auto_create"] is True

    def test_loads_iris_auto_create_false(self):
        """Test loading IRIS_AUTO_CREATE=false from environment."""
        with patch.dict(os.environ, {"IRIS_AUTO_CREATE": "false"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["auto_create"] is False

    def test_ignores_auto_create_invalid_values(self):
        """Test that invalid IRIS_AUTO_CREATE values are ignored."""
        with patch.dict(os.environ, {"IRIS_AUTO_CREATE": "maybe"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert "auto_create" not in result

    def test_ignores_unknown_env_vars(self):
        """Test that unknown IRIS_* vars are ignored."""
        with patch.dict(os.environ, {"IRIS_UNKNOWN": "value"}):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert len(result) == 0

    def test_multiple_env_vars(self):
        """Test loading multiple environment variables."""
        with patch.dict(
            os.environ,
            {
                "IRIS_HOST": "multi.host",
                "IRIS_PORT": "5555",
                "IRIS_NAMESPACE": "MULTI",
            },
        ):
            from iris_devtester.config.discovery import _load_from_environment

            result = _load_from_environment()
            assert result["host"] == "multi.host"
            assert result["port"] == 5555
            assert result["namespace"] == "MULTI"


class TestLoadFromDotenv:
    """Test _load_from_dotenv() function."""

    def test_loads_from_existing_dotenv(self):
        """Test loading from existing .env file."""
        dotenv_content = "IRIS_HOST=dotenv.host\nIRIS_PORT=8888\n"
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=dotenv_content)
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result["host"] == "dotenv.host"
            assert result["port"] == 8888

    def test_skips_nonexistent_dotenv(self):
        """Test that missing .env file is silently skipped."""
        with patch("pathlib.Path.exists", return_value=False):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result == {}

    def test_handles_dotenv_io_error(self):
        """Test that IOError reading .env is handled gracefully."""
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", side_effect=IOError("Permission denied")
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result == {}

    def test_skips_comments_in_dotenv(self):
        """Test that comments are skipped in .env."""
        dotenv_content = "# This is a comment\nIRIS_HOST=host.value\n"
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=dotenv_content)
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert "IRIS_HOST" not in result
            assert result["host"] == "host.value"

    def test_skips_empty_lines_in_dotenv(self):
        """Test that empty lines are skipped in .env."""
        dotenv_content = "IRIS_HOST=host.value\n\nIRIS_PORT=9999\n"
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=dotenv_content)
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result["host"] == "host.value"
            assert result["port"] == 9999

    def test_removes_double_quotes_in_dotenv(self):
        """Test that double quotes are removed from .env values."""
        dotenv_content = 'IRIS_PASSWORD="secret123"\n'
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=dotenv_content)
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result["password"] == "secret123"

    def test_removes_single_quotes_in_dotenv(self):
        """Test that single quotes are removed from .env values."""
        dotenv_content = "IRIS_PASSWORD='secret123'\n"
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=dotenv_content)
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result["password"] == "secret123"

    def test_ignores_malformed_lines_in_dotenv(self):
        """Test that malformed lines without '=' are skipped."""
        dotenv_content = "IRIS_HOST=valid.host\nINVALID_LINE\n"
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=dotenv_content)
        ):
            from iris_devtester.config.discovery import _load_from_dotenv

            result = _load_from_dotenv()
            assert result["host"] == "valid.host"


class TestParseAutoCreate:
    """Test _parse_auto_create() function."""

    def test_parses_true_values(self):
        """Test parsing of true-like values."""
        from iris_devtester.config.discovery import _parse_auto_create

        assert _parse_auto_create("true") is True
        assert _parse_auto_create("True") is True
        assert _parse_auto_create("TRUE") is True
        assert _parse_auto_create("1") is True
        assert _parse_auto_create("yes") is True
        assert _parse_auto_create("YES") is True

    def test_parses_false_values(self):
        """Test parsing of false-like values."""
        from iris_devtester.config.discovery import _parse_auto_create

        assert _parse_auto_create("false") is False
        assert _parse_auto_create("False") is False
        assert _parse_auto_create("FALSE") is False
        assert _parse_auto_create("0") is False
        assert _parse_auto_create("no") is False
        assert _parse_auto_create("NO") is False

    def test_returns_none_for_invalid_values(self):
        """Test that invalid values return None."""
        from iris_devtester.config.discovery import _parse_auto_create

        assert _parse_auto_create("maybe") is None
        assert _parse_auto_create("invalid") is None
        assert _parse_auto_create("") is None


# ============================================================================
# Tests for iris_devtester/containers/models.py
# ============================================================================


class TestContainerHealthStatus:
    """Test ContainerHealthStatus enum."""

    def test_all_enum_values(self):
        """Test that all enum values exist."""
        from iris_devtester.containers.models import ContainerHealthStatus

        assert ContainerHealthStatus.HEALTHY.value == "healthy"
        assert ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE.value == "running_not_accessible"
        assert ContainerHealthStatus.NOT_RUNNING.value == "not_running"
        assert ContainerHealthStatus.NOT_FOUND.value == "not_found"
        assert ContainerHealthStatus.STALE_REFERENCE.value == "stale_reference"
        assert ContainerHealthStatus.DOCKER_ERROR.value == "docker_error"

    def test_enum_is_str_enum(self):
        """Test that ContainerHealthStatus is a string enum."""
        from iris_devtester.containers.models import ContainerHealthStatus

        status = ContainerHealthStatus.HEALTHY
        assert isinstance(status, str)
        assert status == "healthy"


class TestHealthCheckLevel:
    """Test HealthCheckLevel enum."""

    def test_all_enum_values(self):
        """Test that all enum values exist."""
        from iris_devtester.containers.models import HealthCheckLevel

        assert HealthCheckLevel.MINIMAL.value == "minimal"
        assert HealthCheckLevel.STANDARD.value == "standard"
        assert HealthCheckLevel.FULL.value == "full"

    def test_enum_is_str_enum(self):
        """Test that HealthCheckLevel is a string enum."""
        from iris_devtester.containers.models import HealthCheckLevel

        level = HealthCheckLevel.STANDARD
        assert isinstance(level, str)
        assert level == "standard"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_healthy_factory_method(self):
        """Test ValidationResult.healthy() factory method."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult.healthy("iris_db", "abc123", 0.15)
        assert result.success is True
        assert result.status == ContainerHealthStatus.HEALTHY
        assert result.container_name == "iris_db"
        assert result.container_id == "abc123"
        assert result.validation_time == 0.15
        assert result.message == "Container 'iris_db' is running and accessible"
        assert result.remediation_steps == []

    def test_not_found_factory_method(self):
        """Test ValidationResult.not_found() factory method."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult.not_found("iris_db", ["iris_test", "iris_dev"], 0.12)
        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_FOUND
        assert result.container_name == "iris_db"
        assert result.container_id is None
        assert result.available_containers == ["iris_test", "iris_dev"]
        assert len(result.remediation_steps) == 3

    def test_not_running_factory_method(self):
        """Test ValidationResult.not_running() factory method."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult.not_running("iris_db", "def456", 0.10)
        assert result.success is False
        assert result.status == ContainerHealthStatus.NOT_RUNNING
        assert result.container_name == "iris_db"
        assert result.container_id == "def456"
        assert "docker start iris_db" in result.remediation_steps[0]

    def test_not_running_with_custom_status(self):
        """Test ValidationResult.not_running() with custom container status."""
        from iris_devtester.containers.models import ValidationResult

        result = ValidationResult.not_running("iris_db", "def456", 0.10, "restarting")
        assert "restarting" in result.message

    def test_not_accessible_factory_method(self):
        """Test ValidationResult.not_accessible() factory method."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult.not_accessible("iris_db", "ghi789", "exec failed", 0.08)
        assert result.success is False
        assert result.status == ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE
        assert result.container_name == "iris_db"
        assert result.container_id == "ghi789"
        assert "exec failed" in result.message
        assert len(result.remediation_steps) == 3

    def test_stale_reference_factory_method(self):
        """Test ValidationResult.stale_reference() factory method."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult.stale_reference(
            "iris_db", "old" * 10, "new" * 10, 0.20
        )
        assert result.success is False
        assert result.status == ContainerHealthStatus.STALE_REFERENCE
        assert result.container_name == "iris_db"
        assert "old" * 4 in result.message
        assert "new" * 4 in result.message

    def test_docker_error_factory_method(self):
        """Test ValidationResult.docker_error() factory method."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        error = RuntimeError("Docker daemon not responding")
        result = ValidationResult.docker_error("iris_db", error, 0.05)
        assert result.success is False
        assert result.status == ContainerHealthStatus.DOCKER_ERROR
        assert result.container_id is None
        assert "Docker daemon not responding" in result.message

    def test_format_message_success(self):
        """Test format_message() for successful validation."""
        from iris_devtester.containers.models import ValidationResult

        result = ValidationResult.healthy("iris_db", "abc123", 0.1)
        message = result.format_message()
        assert "is healthy" in message
        assert "iris_db" in message

    def test_format_message_failure_with_remediation(self):
        """Test format_message() for failed validation with remediation."""
        from iris_devtester.containers.models import ValidationResult

        result = ValidationResult.not_found("iris_db", ["iris_test"], 0.1)
        message = result.format_message()
        assert "Container validation failed" in message
        assert "What went wrong" in message
        assert "How to fix it" in message
        assert "Available containers" in message

    def test_format_message_multiline_steps(self):
        """Test format_message() with multi-line remediation steps."""
        from iris_devtester.containers.models import ValidationResult, ContainerHealthStatus

        result = ValidationResult(
            success=False,
            status=ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE,
            container_name="iris_db",
            container_id="abc123",
            message="Test error",
            remediation_steps=["Step 1:\n  Sub-step A\n  Sub-step B"],
        )
        message = result.format_message()
        assert "Step 1:" in message
        assert "Sub-step A" in message
        assert "Sub-step B" in message


class TestContainerHealth:
    """Test ContainerHealth dataclass."""

    def test_basic_creation(self):
        """Test basic ContainerHealth creation."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            container_id="abc123",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
        )
        assert health.container_name == "iris_db"
        assert health.container_id == "abc123"
        assert health.running is True
        assert health.accessible is True

    def test_tables_visible_property_true(self):
        """Test tables_visible property when schemas exist."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas={"USER": 5, "SAMPLES": 3},
        )
        assert health.tables_visible is True

    def test_tables_visible_property_false(self):
        """Test tables_visible property when schemas are empty."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas={},
        )
        assert health.tables_visible is False

    def test_tables_visible_property_none(self):
        """Test tables_visible property when schemas are None."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas=None,
        )
        assert health.tables_visible is False

    def test_is_healthy_method(self):
        """Test is_healthy() method."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health_ok = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
        )
        assert health_ok.is_healthy() is True

        health_not_ok = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.NOT_RUNNING,
            running=False,
            accessible=False,
            docker_sdk_version="6.1.0",
        )
        assert health_not_ok.is_healthy() is False

    def test_report_method_healthy(self):
        """Test report() method for healthy container."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            container_id="abc123",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas={"USER": 5},
        )
        report = health.report()
        assert "iris_db" in report
        assert "healthy" in report
        assert "USER: 5 table(s)" in report

    def test_report_method_no_schemas(self):
        """Test report() method when schemas probe not run."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas=None,
        )
        report = health.report()
        assert "(probe not run)" in report

    def test_report_method_empty_schemas(self):
        """Test report() method when no schemas visible."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas={},
        )
        report = health.report()
        assert "No schemas visible" in report

    def test_to_dict_method(self):
        """Test to_dict() method."""
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus

        health = ContainerHealth(
            container_name="iris_db",
            container_id="abc123",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            started_at="2026-01-01T10:00:00Z",
            port_bindings={"1972/tcp": "11972"},
            image="intersystemsdc/iris-community:latest",
            schemas={"USER": 5},
        )
        result = health.to_dict()
        assert result["container_name"] == "iris_db"
        assert result["container_id"] == "abc123"
        assert result["status"] == "healthy"
        assert result["running"] is True
        assert result["schemas"] == {"USER": 5}


class TestFHIRContainerHealth:
    """Test FHIRContainerHealth dataclass."""

    def test_basic_creation(self):
        """Test basic FHIRContainerHealth creation."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=True,
            endpoint="http://localhost:8080/fhir/r4",
        )
        assert health.container_name == "fhir_db"
        assert health.accessible is True
        assert health.endpoint == "http://localhost:8080/fhir/r4"

    def test_ready_property_true(self):
        """Test ready property when accessible and fhir_version set."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=True,
            endpoint="http://localhost:8080/fhir/r4",
            fhir_version="4.0.1",
        )
        assert health.ready is True

    def test_ready_property_false_not_accessible(self):
        """Test ready property when not accessible."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=False,
            endpoint="http://localhost:8080/fhir/r4",
            fhir_version="4.0.1",
        )
        assert health.ready is False

    def test_ready_property_false_no_version(self):
        """Test ready property when fhir_version is None."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=True,
            endpoint="http://localhost:8080/fhir/r4",
            fhir_version=None,
        )
        assert health.ready is False

    def test_report_method_ready(self):
        """Test report() method when FHIR is ready."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=True,
            endpoint="http://localhost:8080/fhir/r4",
            fhir_version="4.0.1",
            resource_types_count=85,
        )
        report = health.report()
        assert "fhir_db" in report
        assert "http://localhost:8080/fhir/r4" in report
        assert "4.0.1" in report
        assert "85 types" in report

    def test_report_method_not_ready(self):
        """Test report() method when FHIR not ready."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=False,
            endpoint="http://localhost:8080/fhir/r4",
            fhir_version=None,
        )
        report = health.report()
        assert "Foundation.Install" in report

    def test_report_method_with_error(self):
        """Test report() method when error is set."""
        from iris_devtester.containers.models import FHIRContainerHealth

        health = FHIRContainerHealth(
            container_name="fhir_db",
            accessible=False,
            endpoint="http://localhost:8080/fhir/r4",
            error="Connection timeout",
        )
        report = health.report()
        assert "Connection timeout" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
