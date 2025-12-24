"""
Unit tests for auto-discovery module.

Tests verify Docker and native IRIS instance detection.
"""

import subprocess
from unittest.mock import MagicMock, patch
import pytest

from iris_devtester.connections.auto_discovery import (
    auto_detect_iris_port,
    auto_detect_iris_host_and_port,
    _detect_port_from_docker,
    _detect_port_from_native,
)


class TestDockerDetection:
    """Test Docker container port detection."""

    def test_detect_port_from_docker_with_standard_mapping(self):
        """
        Test detection with standard port mapping.

        Expected: Detects port 1972 from Docker output.
        """
        mock_output = (
            "iris_db\t0.0.0.0:1972->1972/tcp, :::1972->1972/tcp\n"
            "postgres_db\t0.0.0.0:5432->5432/tcp\n"
        )

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            port = _detect_port_from_docker()

            assert port == 1972

    def test_detect_port_from_docker_with_custom_mapping(self):
        """
        Test detection with custom port mapping (e.g., 51773->1972).

        Expected: Detects external port 51773.
        """
        mock_output = (
            "iris_db\t0.0.0.0:51773->1972/tcp\n"
        )

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            port = _detect_port_from_docker()

            assert port == 51773

    def test_detect_port_from_docker_no_iris_container(self):
        """
        Test detection when no IRIS container running.

        Expected: Returns None.
        """
        mock_output = "postgres_db\t0.0.0.0:5432->5432/tcp\n"

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            port = _detect_port_from_docker()

            assert port is None

    def test_detect_port_from_docker_not_installed(self):
        """
        Test detection when Docker not installed.

        Expected: Returns None gracefully.
        """
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("docker not found")

            port = _detect_port_from_docker()

            assert port is None

    def test_detect_port_from_docker_not_running(self):
        """
        Test detection when Docker daemon not running.

        Expected: Returns None gracefully.
        """
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            port = _detect_port_from_docker()

            assert port is None


class TestNativeDetection:
    """Test native IRIS instance detection."""

    def test_detect_port_from_native_standard_output(self):
        """
        Test detection from 'iris list' standard output.

        Expected: Detects port 1972.
        """
        mock_output = (
            "Configuration 'IRIS'\n"
            "    Directory:    /usr/irissys\n"
            "    SuperServers: 1972\n"
            "    WebServers:   52773\n"
        )

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            port = _detect_port_from_native()

            assert port == 1972

    def test_detect_port_from_native_custom_port(self):
        """
        Test detection with custom SuperServer port.

        Expected: Detects custom port.
        """
        mock_output = (
            "Configuration 'IRIS'\n"
            "    SuperServers: 51972\n"
        )

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            port = _detect_port_from_native()

            assert port == 51972

    def test_detect_port_from_native_not_installed(self):
        """
        Test detection when IRIS not installed.

        Expected: Returns None gracefully.
        """
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("iris not found")

            port = _detect_port_from_native()

            assert port is None

    def test_detect_port_from_native_no_instances(self):
        """
        Test detection when no IRIS instances running.

        Expected: Returns None.
        """
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="No configurations found\n",
            )

            port = _detect_port_from_native()

            assert port is None


class TestCombinedAutoDetection:
    """Test combined auto-detection logic."""

    def test_auto_detect_prefers_docker(self):
        """
        Test that Docker detection is preferred over native.

        Expected: Uses Docker port when both available.
        """
        docker_output = "iris_db\t0.0.0.0:1972->1972/tcp\n"
        native_output = "SuperServers: 51972\n"

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                cmd = args[0]
                if cmd[0] == "docker":
                    return MagicMock(returncode=0, stdout=docker_output)
                elif cmd[0] == "iris":
                    return MagicMock(returncode=0, stdout=native_output)
                return MagicMock(returncode=1)

            mock_run.side_effect = side_effect

            port = auto_detect_iris_port()

            # Should use Docker port (1972) not native (51972)
            assert port == 1972

    def test_auto_detect_falls_back_to_native(self):
        """
        Test fallback to native when Docker unavailable.

        Expected: Uses native IRIS port.
        """
        native_output = "SuperServers: 1972\n"

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                cmd = args[0]
                if cmd[0] == "docker":
                    raise FileNotFoundError("docker not found")
                elif cmd[0] == "iris":
                    return MagicMock(returncode=0, stdout=native_output)
                return MagicMock(returncode=1)

            mock_run.side_effect = side_effect

            port = auto_detect_iris_port()

            assert port == 1972

    def test_auto_detect_returns_none_when_nothing_found(self):
        """
        Test behavior when no IRIS instances found.

        Expected: Returns None gracefully.
        """
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            port = auto_detect_iris_port()

            assert port is None

    def test_auto_detect_host_and_port_docker(self):
        """
        Test host/port detection from Docker.

        Expected: Returns (localhost, port).
        """
        docker_output = "iris_db\t0.0.0.0:1972->1972/tcp\n"

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=docker_output,
            )

            host, port = auto_detect_iris_host_and_port()

            assert host == "localhost"
            assert port == 1972

    def test_auto_detect_host_and_port_native(self):
        """
        Test host/port detection from native IRIS.

        Expected: Returns (localhost, port).
        """
        native_output = "SuperServers: 1972\n"

        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                cmd = args[0]
                if cmd[0] == "docker":
                    return MagicMock(returncode=1)  # No Docker
                elif cmd[0] == "iris":
                    return MagicMock(returncode=0, stdout=native_output)
                return MagicMock(returncode=1)

            mock_run.side_effect = side_effect

            host, port = auto_detect_iris_host_and_port()

            assert host == "localhost"
            assert port == 1972

    def test_auto_detect_host_and_port_not_found(self):
        """
        Test behavior when no instances found.

        Expected: Returns (None, None).
        """
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            host, port = auto_detect_iris_host_and_port()

            assert host is None
            assert port is None
