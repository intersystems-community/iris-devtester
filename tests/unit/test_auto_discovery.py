"""
Unit tests for auto-discovery module.

Tests verify Docker and native IRIS instance detection.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.connections.auto_discovery import (
    _detect_port_from_docker,
    _detect_port_from_native,
    auto_detect_iris_host_and_port,
    auto_detect_iris_port,
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
        mock_output = "iris_db\t0.0.0.0:51773->1972/tcp\n"

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
        mock_output = "Configuration 'IRIS'\n" "    SuperServers: 51972\n"

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


# --------------------------------------------------------------------------
# Multi-container determinism tests (container_name parameter)
# --------------------------------------------------------------------------

# Simulates a dev machine running 10+ IRIS containers simultaneously.
# Without container_name, the first match from docker ps wins (non-deterministic).
# With container_name, only the pinned container is matched (deterministic).
MULTI_CONTAINER_DOCKER_OUTPUT = (
    "iris-rag-main\t0.0.0.0:11972->1972/tcp, :::11972->1972/tcp\n"
    "iris-vector-graph-main\t0.0.0.0:21972->1972/tcp, :::21972->1972/tcp\n"
    "iris-analytics\t0.0.0.0:31972->1972/tcp\n"
    "iris-dev-test\t0.0.0.0:1972->1972/tcp, :::1972->1972/tcp\n"
    "postgres_db\t0.0.0.0:5432->5432/tcp\n"
    "redis\t0.0.0.0:6379->6379/tcp\n"
    "iris-ml-pipeline\t0.0.0.0:41972->1972/tcp\n"
)


class TestContainerNamePinning:
    """Test deterministic container selection via container_name parameter.

    Verifies the fix for the multi-container non-determinism bug:
    on machines with 10+ IRIS containers, auto-detection used to return
    whichever container appeared first in 'docker ps' output.

    The container_name parameter pins detection to a specific container.
    """

    def test_detect_port_pinned_to_specific_container(self):
        """Pin to iris-vector-graph-main -> should return port 21972."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            port = _detect_port_from_docker(container_name="iris-vector-graph-main")

            assert port == 21972

    def test_detect_port_pinned_to_different_container(self):
        """Pin to iris-dev-test -> should return port 1972."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            port = _detect_port_from_docker(container_name="iris-dev-test")

            assert port == 1972

    def test_detect_port_pinned_to_nonexistent_container(self):
        """Pin to container that doesn't exist -> should return None."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            port = _detect_port_from_docker(container_name="iris-does-not-exist")

            assert port is None

    def test_detect_port_without_pinning_returns_first_match(self):
        """Without container_name, returns the first container's port (legacy behavior)."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            port = _detect_port_from_docker()

            # First container in docker ps output is iris-rag-main on port 11972
            assert port == 11972

    def test_auto_detect_iris_port_with_container_name(self):
        """auto_detect_iris_port passes container_name to Docker detection."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            port = auto_detect_iris_port(container_name="iris-analytics")

            assert port == 31972

    def test_auto_detect_host_and_port_with_container_name(self):
        """auto_detect_iris_host_and_port passes container_name to Docker detection."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            host, port = auto_detect_iris_host_and_port(
                container_name="iris-ml-pipeline",
            )

            assert host == "localhost"
            assert port == 41972

    def test_container_name_none_is_backward_compatible(self):
        """container_name=None behaves identically to the old parameterless call."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )

            port_explicit_none = _detect_port_from_docker(container_name=None)
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=MULTI_CONTAINER_DOCKER_OUTPUT,
            )
            port_no_arg = _detect_port_from_docker()

            assert port_explicit_none == port_no_arg

    def test_container_name_with_no_docker(self):
        """container_name specified but Docker not available -> falls back to native."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:

            def side_effect(*args, **kwargs):
                cmd = args[0]
                if cmd[0] == "docker":
                    raise FileNotFoundError("docker not found")
                elif cmd[0] == "iris":
                    return MagicMock(returncode=0, stdout="SuperServers: 1972\n")
                return MagicMock(returncode=1)

            mock_run.side_effect = side_effect

            # container_name is Docker-only; should gracefully fall back to native
            port = auto_detect_iris_port(container_name="iris-vector-graph-main")

            assert port == 1972

    def test_pinned_container_not_running_no_native(self):
        """Pinned container not in docker ps and no native -> returns None."""
        with patch("iris_devtester.connections.auto_discovery.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            host, port = auto_detect_iris_host_and_port(
                container_name="iris-vector-graph-main",
            )

            assert host is None
            assert port is None
