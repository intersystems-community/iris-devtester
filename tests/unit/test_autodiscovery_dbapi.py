"""Unit tests for iris_devtester/connections/auto_discovery.py — port detection from Docker and native.

Focus: Comprehensive coverage of docker/native port detection paths.
Tests subprocess mocking patterns, regex extraction, and error handling paths.
"""

import logging
import re
import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from iris_devtester.connections.auto_discovery import (
    auto_detect_iris_host_and_port,
    auto_detect_iris_port,
    _detect_port_from_docker,
    _detect_port_from_native,
)


class TestAutoDetectIrisPort:
    """Test the main auto_detect_iris_port() function."""

    def test_returns_port_from_docker_when_available(self):
        """Should return port from Docker detection first."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=11972,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
        ) as mock_native:
            result = auto_detect_iris_port()
            assert result == 11972
            mock_native.assert_not_called()

    def test_returns_port_from_native_when_docker_unavailable(self):
        """Should fall back to native detection when Docker fails."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=None,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
            return_value=1972,
        ):
            result = auto_detect_iris_port()
            assert result == 1972

    def test_returns_none_when_both_fail(self):
        """Should return None when both Docker and native detection fail."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=None,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
            return_value=None,
        ):
            result = auto_detect_iris_port()
            assert result is None

    def test_passes_container_name_to_docker_detection(self):
        """Should pass container_name to Docker detection."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=11972,
        ) as mock_docker:
            auto_detect_iris_port(container_name="my-iris")
            mock_docker.assert_called_once_with(container_name="my-iris")

    def test_logs_port_found_from_docker(self, caplog):
        """Should log when port is found from Docker."""
        with caplog.at_level(logging.INFO), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=11972,
        ):
            result = auto_detect_iris_port()
            assert result == 11972
            assert "Auto-detected IRIS port 11972 from Docker" in caplog.text

    def test_logs_port_found_from_native(self, caplog):
        """Should log when port is found from native."""
        with caplog.at_level(logging.INFO), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=None,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
            return_value=1972,
        ):
            result = auto_detect_iris_port()
            assert result == 1972
            assert "Auto-detected IRIS port 1972 from native instance" in caplog.text

    def test_logs_debug_when_no_port_found(self, caplog):
        """Should log debug message when no port found."""
        with caplog.at_level(logging.DEBUG), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=None,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
            return_value=None,
        ):
            result = auto_detect_iris_port()
            assert result is None
            assert "Could not auto-detect IRIS port" in caplog.text


class TestAutoDetectIrisHostAndPort:
    """Test the auto_detect_iris_host_and_port() function."""

    def test_returns_localhost_and_port_from_docker(self):
        """Should return localhost and Docker port."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=11972,
        ):
            host, port = auto_detect_iris_host_and_port()
            assert host == "localhost"
            assert port == 11972

    def test_returns_localhost_and_port_from_native(self):
        """Should return localhost and native port."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=None,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
            return_value=1972,
        ):
            host, port = auto_detect_iris_host_and_port()
            assert host == "localhost"
            assert port == 1972

    def test_returns_none_none_when_both_fail(self):
        """Should return (None, None) when both fail."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=None,
        ), patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_native",
            return_value=None,
        ):
            host, port = auto_detect_iris_host_and_port()
            assert host is None
            assert port is None

    def test_passes_container_name_to_docker_detection(self):
        """Should pass container_name to Docker detection."""
        with patch(
            "iris_devtester.connections.auto_discovery._detect_port_from_docker",
            return_value=11972,
        ) as mock_docker:
            auto_detect_iris_host_and_port(container_name="iris-project-a")
            mock_docker.assert_called_once_with(container_name="iris-project-a")


class TestDetectPortFromDocker:
    """Test _detect_port_from_docker() function."""

    def test_finds_port_from_standard_mapping(self):
        """Should find port from 0.0.0.0:PORT->1972/tcp mapping."""
        docker_output = "my-iris\t0.0.0.0:11972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 11972

    def test_finds_port_from_ipv6_mapping(self):
        """Should find port from :::PORT->1972/tcp mapping (IPv6)."""
        docker_output = "my-iris\t:::11972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 11972

    def test_finds_first_matching_container_when_no_name_specified(self):
        """Should return first container with port 1972 mapping."""
        docker_output = "postgres\t0.0.0.0:5432->5432/tcp\nmy-iris\t0.0.0.0:1972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 1972

    def test_matches_pinned_container_name(self):
        """Should only match container with specified name."""
        docker_output = (
            "iris-a\t0.0.0.0:1972->1972/tcp\n"
            "iris-b\t0.0.0.0:11972->1972/tcp\n"
        )
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker(container_name="iris-b")
            assert result == 11972

    def test_returns_none_when_pinned_container_not_found(self):
        """Should return None when pinned container name not in output."""
        docker_output = "iris-a\t0.0.0.0:1972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker(container_name="iris-missing")
            assert result is None

    def test_finds_port_using_fallback_iris_name_heuristic(self):
        """Should use fallback heuristic for iris-named containers with 1972."""
        docker_output = "iris-custom\t0.0.0.0:31972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 31972

    def test_skips_lines_with_no_tab_separator(self):
        """Should skip lines without tab separator (malformed output)."""
        docker_output = "my-iris-0.0.0.0:1972->1972/tcp\nvalid-iris\t0.0.0.0:1972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 1972

    def test_skips_empty_lines(self):
        """Should skip empty lines in docker output."""
        docker_output = "\n\nmy-iris\t0.0.0.0:11972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 11972

    def test_returns_none_on_docker_ps_failure(self):
        """Should return None when docker ps returns error code."""
        mock_result = MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result is None

    def test_returns_none_when_docker_not_installed(self):
        """Should return None when docker command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            result = _detect_port_from_docker()
            assert result is None

    def test_returns_none_on_timeout(self):
        """Should return None on docker ps timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            result = _detect_port_from_docker()
            assert result is None

    def test_returns_none_on_value_error(self):
        """Should return None if port regex match fails to int()."""
        with patch(
            "subprocess.run",
            side_effect=ValueError("invalid port"),
        ):
            result = _detect_port_from_docker()
            assert result is None

    def test_raises_on_unhandled_exception(self):
        """Should not catch unhandled exceptions (e.g., RuntimeError)."""
        with patch("subprocess.run", side_effect=RuntimeError("unexpected error")):
            with pytest.raises(RuntimeError):
                _detect_port_from_docker()

    def test_logs_debug_when_docker_unavailable(self, caplog):
        """Should log debug message when docker ps fails."""
        with caplog.at_level(logging.DEBUG), patch(
            "subprocess.run", side_effect=FileNotFoundError("docker not found")
        ):
            result = _detect_port_from_docker()
            assert result is None
            assert "Error detecting port from Docker" in caplog.text

    def test_logs_debug_on_error(self, caplog):
        """Should log debug message on error."""
        with caplog.at_level(logging.DEBUG), patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)
        ):
            result = _detect_port_from_docker()
            assert result is None
            assert "Error detecting port from Docker" in caplog.text

    def test_logs_debug_when_port_found(self, caplog):
        """Should log debug message when port is found."""
        docker_output = "my-iris\t0.0.0.0:11972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with caplog.at_level(logging.DEBUG), patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 11972
            assert "Found IRIS port 11972 in Docker container my-iris" in caplog.text

    def test_calls_docker_ps_with_correct_format(self):
        """Should call docker ps with correct --format flag."""
        mock_result = MagicMock(returncode=0, stdout="")

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _detect_port_from_docker()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"]
            assert kwargs["capture_output"] is True
            assert kwargs["text"] is True
            assert kwargs["timeout"] == 5

    def test_returns_none_for_no_iris_port_in_output(self):
        """Should return None when no container with port 1972 mapping found."""
        docker_output = "db-server\t0.0.0.0:5432->5432/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result is None

    def test_extracts_correct_external_port_from_mapping(self):
        """Should extract the external port (before ->) not the internal port."""
        docker_output = "my-iris\t0.0.0.0:51773->52773/tcp, 0.0.0.0:21972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 21972  # The port mapped to 1972, not 52773

    def test_fallback_heuristic_finds_iris_named_container_with_port(self):
        """Should use fallback heuristic for iris-named containers mapping to 1972."""
        # When a container has 'iris' in name and 1972 in ports but regex doesn't match,
        # use fallback to extract any mapped port
        docker_output = "iris-custom-1972\t0.0.0.0:31972->1972/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 31972

    def test_fallback_heuristic_only_applies_to_iris_named_containers(self):
        """Fallback heuristic should not apply to containers without 'iris' in name."""
        # This container has a different internal port, so first regex won't match
        # but it still wouldn't match the fallback because no 'iris' in name
        docker_output = "db-server\t0.0.0.0:31972->3306/tcp, 0.0.0.0:1972->3307/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            # Has '1972' in ports but no '->1972/tcp' pattern and no 'iris' in name
            assert result is None

    def test_fallback_heuristic_requires_1972_in_ports(self):
        """Fallback heuristic should require 1972 string in ports."""
        docker_output = "iris-custom\t0.0.0.0:5432->5432/tcp\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            # Has 'iris' in name but no '1972' in ports string and no '->1972/tcp' pattern
            assert result is None

    def test_logs_debug_for_fallback_heuristic_match(self, caplog):
        """Should log debug when fallback heuristic finds a port."""
        # First regex won't match (3306->2306, not ->1972)
        # But has iris in name and 1972 in ports string
        docker_output = "iris-custom\t0.0.0.0:31972->3306/tcp, 1972\n"
        mock_result = MagicMock(returncode=0, stdout=docker_output)

        with caplog.at_level(logging.DEBUG), patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_docker()
            assert result == 31972
            assert "Found IRIS container 'iris-custom' with port 31972" in caplog.text


class TestDetectPortFromNative:
    """Test _detect_port_from_native() function."""

    def test_finds_port_from_superserver_line(self):
        """Should extract port from 'SuperServers: PORT' line."""
        iris_output = "Configuration 'IRIS':\n  SuperServers: 1972\n"
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result == 1972

    def test_finds_port_from_superserver_singular(self):
        """Should match 'SuperServer' singular variant."""
        iris_output = "Configuration 'IRIS':\n  SuperServer: 1972\n"
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result == 1972

    def test_handles_various_superserver_line_formats(self):
        """Should handle different whitespace in SuperServer line."""
        iris_output = "Configuration 'IRIS':\n  SuperServers:1972\n"
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result == 1972

    def test_returns_none_when_iris_not_running(self):
        """Should return None when SuperServer line absent."""
        iris_output = "Configuration 'IRIS':\n  status: down\n"
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result is None

    def test_returns_none_on_iris_list_failure(self):
        """Should return None when iris list command fails."""
        mock_result = MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result is None

    def test_returns_none_when_iris_not_installed(self):
        """Should return None when iris command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError("iris not found")):
            result = _detect_port_from_native()
            assert result is None

    def test_returns_none_on_timeout(self):
        """Should return None on iris list timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("iris", 5)):
            result = _detect_port_from_native()
            assert result is None

    def test_returns_none_on_value_error(self):
        """Should return None if port regex match fails to int()."""
        with patch(
            "subprocess.run",
            side_effect=ValueError("invalid port"),
        ):
            result = _detect_port_from_native()
            assert result is None

    def test_raises_on_unhandled_exception(self):
        """Should not catch unhandled exceptions (e.g., RuntimeError)."""
        with patch("subprocess.run", side_effect=RuntimeError("unexpected error")):
            with pytest.raises(RuntimeError):
                _detect_port_from_native()

    def test_logs_debug_when_iris_unavailable(self, caplog):
        """Should log debug message when iris not installed."""
        with caplog.at_level(logging.DEBUG), patch(
            "subprocess.run", side_effect=FileNotFoundError("iris not found")
        ):
            result = _detect_port_from_native()
            assert result is None
            assert "Error detecting port from native IRIS" in caplog.text

    def test_logs_debug_on_error(self, caplog):
        """Should log debug message on error."""
        with caplog.at_level(logging.DEBUG), patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("iris", 5)
        ):
            result = _detect_port_from_native()
            assert result is None
            assert "Error detecting port from native IRIS" in caplog.text

    def test_logs_debug_when_port_found(self, caplog):
        """Should log debug message when port is found."""
        iris_output = "Configuration 'IRIS':\n  SuperServers: 1972\n"
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with caplog.at_level(logging.DEBUG), patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result == 1972
            assert "Found IRIS port 1972 from native instance" in caplog.text

    def test_calls_iris_list_command(self):
        """Should call iris list with correct timeout."""
        mock_result = MagicMock(returncode=0, stdout="")

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _detect_port_from_native()
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["iris", "list"]
            assert kwargs["capture_output"] is True
            assert kwargs["text"] is True
            assert kwargs["timeout"] == 5

    def test_handles_multi_line_output(self):
        """Should find SuperServer line in multi-line output."""
        iris_output = (
            "Configuration 'IRIS':\n"
            "  status: running, since Mon Aug 25 10:00:00 2025\n"
            "  SuperServers: 1972\n"
            "  Web Server: 52773\n"
        )
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result == 1972

    def test_ignores_lines_without_superserver(self):
        """Should skip lines that don't contain 'SuperServer'."""
        iris_output = (
            "Configuration 'IRIS':\n"
            "  status: running\n"
            "  Port: 1972\n"
            "  Web: 52773\n"
        )
        mock_result = MagicMock(returncode=0, stdout=iris_output)

        with patch("subprocess.run", return_value=mock_result):
            result = _detect_port_from_native()
            assert result is None


class TestRegexPatterns:
    """Test the regex patterns used in port detection."""

    def test_docker_port_regex_matches_standard_format(self):
        """Test the docker port regex pattern."""
        pattern = r"(?:0\.0\.0\.0|:::):?(\d+)->1972/tcp"
        assert re.search(pattern, "0.0.0.0:11972->1972/tcp") is not None
        assert re.search(pattern, ":::11972->1972/tcp") is not None

    def test_docker_port_regex_doesnt_match_wrong_port(self):
        """Test docker regex doesn't match non-1972 mappings."""
        pattern = r"(?:0\.0\.0\.0|:::):?(\d+)->1972/tcp"
        assert re.search(pattern, "0.0.0.0:5432->5432/tcp") is None

    def test_native_superserver_regex_matches_variations(self):
        """Test superserver regex matches singular and plural."""
        pattern = r"SuperServer\w*:\s*(\d+)"
        assert re.search(pattern, "  SuperServers: 1972") is not None
        assert re.search(pattern, "  SuperServer: 1972") is not None
        assert re.search(pattern, "  SuperServers:1972") is not None
