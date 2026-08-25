"""Unit tests for config/auto_discovery.py — all subprocess-based, no Docker or IRIS needed."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest


class TestTestIrisPort:
    def test_returns_true_when_success_in_stdout(self):
        from iris_devtester.config.auto_discovery import _test_iris_port

        mock_result = MagicMock(stdout="SUCCESS", returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            assert _test_iris_port(1972) is True

    def test_returns_false_when_failed_in_stdout(self):
        from iris_devtester.config.auto_discovery import _test_iris_port

        mock_result = MagicMock(stdout="FAILED", returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            assert _test_iris_port(1972) is False

    def test_returns_false_on_timeout(self):
        from iris_devtester.config.auto_discovery import _test_iris_port

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("python", 5)):
            assert _test_iris_port(1972) is False

    def test_returns_false_on_file_not_found(self):
        from iris_devtester.config.auto_discovery import _test_iris_port

        with patch("subprocess.run", side_effect=FileNotFoundError("python not found")):
            assert _test_iris_port(1972) is False

    def test_returns_false_on_generic_exception(self):
        from iris_devtester.config.auto_discovery import _test_iris_port

        with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
            assert _test_iris_port(1972) is False

    def test_returns_false_on_empty_stdout(self):
        from iris_devtester.config.auto_discovery import _test_iris_port

        mock_result = MagicMock(stdout="", returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            assert _test_iris_port(1972) is False


class TestDiscoverIrisPort:
    def test_returns_first_successful_port(self):
        from iris_devtester.config.auto_discovery import discover_iris_port

        def fake_test(port, timeout=5):
            return port == 11972

        with patch("iris_devtester.config.auto_discovery._test_iris_port", side_effect=fake_test):
            result = discover_iris_port([1972, 11972, 21972])
        assert result == 11972

    def test_returns_none_when_no_port_responds(self):
        from iris_devtester.config.auto_discovery import discover_iris_port

        with patch("iris_devtester.config.auto_discovery._test_iris_port", return_value=False):
            result = discover_iris_port([1972, 11972])
        assert result is None

    def test_uses_default_ports_when_none_given(self):
        from iris_devtester.config.auto_discovery import discover_iris_port

        with patch("iris_devtester.config.auto_discovery._test_iris_port", return_value=False) as mock_test:
            discover_iris_port()
        # Default ports [31972, 1972, 11972, 21972] should all be tried
        assert mock_test.call_count == 4

    def test_returns_first_default_port_on_success(self):
        from iris_devtester.config.auto_discovery import discover_iris_port

        with patch("iris_devtester.config.auto_discovery._test_iris_port", return_value=True):
            result = discover_iris_port()
        assert result == 31972  # first in default list


class TestDiscoverDockerIris:
    def test_finds_iris_container_by_port_mapping(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        docker_output = "my-iris\t0.0.0.0:11972->1972/tcp, 0.0.0.0:52773->52773/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris()

        assert config is not None
        assert config["port"] == 11972
        assert config["host"] == "localhost"
        assert config["container_name"] == "my-iris"

    def test_returns_none_when_no_iris_containers(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        docker_output = "postgres\t0.0.0.0:5432->5432/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris()

        assert config is None

    def test_returns_none_on_docker_ps_failure(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        mock_result = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris()

        assert config is None

    def test_returns_none_when_docker_not_installed(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            config = discover_docker_iris()

        assert config is None

    def test_returns_none_on_docker_timeout(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            config = discover_docker_iris()

        assert config is None

    def test_pins_to_specific_container_name(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        docker_output = (
            "iris-project-a\t0.0.0.0:1972->1972/tcp\n"
            "iris-project-b\t0.0.0.0:11972->1972/tcp\n"
        )
        mock_result = MagicMock(returncode=0, stdout=docker_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris(container_name="iris-project-b")

        assert config is not None
        assert config["port"] == 11972

    def test_returns_none_when_pinned_container_not_found(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        docker_output = "iris-project-a\t0.0.0.0:1972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris(container_name="iris-project-b")

        assert config is None

    def test_returns_none_on_generic_exception(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
            config = discover_docker_iris()

        assert config is None

    def test_skips_lines_without_port_mapping(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        # iris in name but no port mapping
        docker_output = "iris-no-ports\t\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris()

        assert config is None

    def test_handles_empty_stdout(self):
        from iris_devtester.config.auto_discovery import discover_docker_iris

        mock_result = MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            config = discover_docker_iris()

        assert config is None


class TestDiscoverNativeIris:
    def test_finds_running_instance(self):
        from iris_devtester.config.auto_discovery import discover_native_iris

        iris_list_output = (
            "Configuration 'IRIS':\n"
            "  status: running, since Mon Aug 25 10:00:00 2025\n"
            "  SuperServers: 1972\n"
        )
        mock_result = MagicMock(returncode=0, stdout=iris_list_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_native_iris()

        assert config is not None
        assert config["port"] == 1972
        assert config["host"] == "localhost"

    def test_returns_none_when_iris_not_running(self):
        from iris_devtester.config.auto_discovery import discover_native_iris

        iris_list_output = "Configuration 'IRIS':\n  status: down\n"
        mock_result = MagicMock(returncode=0, stdout=iris_list_output)
        with patch("subprocess.run", return_value=mock_result):
            config = discover_native_iris()

        assert config is None

    def test_returns_none_on_iris_command_failure(self):
        from iris_devtester.config.auto_discovery import discover_native_iris

        mock_result = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            config = discover_native_iris()

        assert config is None

    def test_returns_none_when_iris_not_installed(self):
        from iris_devtester.config.auto_discovery import discover_native_iris

        with patch("subprocess.run", side_effect=FileNotFoundError("iris not found")):
            config = discover_native_iris()

        assert config is None

    def test_returns_none_on_timeout(self):
        from iris_devtester.config.auto_discovery import discover_native_iris

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("iris", 5)):
            config = discover_native_iris()

        assert config is None

    def test_returns_none_on_generic_exception(self):
        from iris_devtester.config.auto_discovery import discover_native_iris

        with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
            config = discover_native_iris()

        assert config is None


class TestAutoDiscoverIris:
    def test_finds_via_docker_first(self):
        from iris_devtester.config.auto_discovery import auto_discover_iris

        docker_config = {"host": "localhost", "port": 11972, "username": "_SYSTEM",
                         "password": "SYS", "namespace": "USER", "container_name": "test"}
        with patch("iris_devtester.config.auto_discovery.discover_docker_iris", return_value=docker_config), \
             patch("iris_devtester.config.auto_discovery.discover_native_iris") as mock_native, \
             patch("iris_devtester.config.auto_discovery.discover_iris_port") as mock_scan:
            config = auto_discover_iris()

        assert config is docker_config
        mock_native.assert_not_called()
        mock_scan.assert_not_called()

    def test_falls_back_to_native_when_docker_fails(self):
        from iris_devtester.config.auto_discovery import auto_discover_iris

        native_config = {"host": "localhost", "port": 1972, "username": "_SYSTEM",
                         "password": "SYS", "namespace": "USER"}
        with patch("iris_devtester.config.auto_discovery.discover_docker_iris", return_value=None), \
             patch("iris_devtester.config.auto_discovery.discover_native_iris", return_value=native_config), \
             patch("iris_devtester.config.auto_discovery.discover_iris_port") as mock_scan:
            config = auto_discover_iris()

        assert config is native_config
        mock_scan.assert_not_called()

    def test_falls_back_to_port_scan(self):
        from iris_devtester.config.auto_discovery import auto_discover_iris

        with patch("iris_devtester.config.auto_discovery.discover_docker_iris", return_value=None), \
             patch("iris_devtester.config.auto_discovery.discover_native_iris", return_value=None), \
             patch("iris_devtester.config.auto_discovery.discover_iris_port", return_value=31972):
            config = auto_discover_iris()

        assert config is not None
        assert config["port"] == 31972

    def test_returns_none_when_all_fail(self):
        from iris_devtester.config.auto_discovery import auto_discover_iris

        with patch("iris_devtester.config.auto_discovery.discover_docker_iris", return_value=None), \
             patch("iris_devtester.config.auto_discovery.discover_native_iris", return_value=None), \
             patch("iris_devtester.config.auto_discovery.discover_iris_port", return_value=None):
            config = auto_discover_iris()

        assert config is None

    def test_passes_container_name_to_docker_discovery(self):
        from iris_devtester.config.auto_discovery import auto_discover_iris

        with patch("iris_devtester.config.auto_discovery.discover_docker_iris", return_value=None) as mock_docker, \
             patch("iris_devtester.config.auto_discovery.discover_native_iris", return_value=None), \
             patch("iris_devtester.config.auto_discovery.discover_iris_port", return_value=None):
            auto_discover_iris(container_name="my-iris")

        mock_docker.assert_called_once_with(container_name="my-iris")
