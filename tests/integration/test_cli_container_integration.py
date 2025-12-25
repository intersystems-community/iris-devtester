"""
Integration tests for CLI container commands.

Tests verify CLI commands work end-to-end with real IRIS containers via subprocess.
"""

import pytest
import subprocess
import sys


class TestCLIContainerCommands:
    """Integration tests for iris-devtester container CLI commands."""

    def test_reset_password_command(self, iris_container):
        """
        Test reset-password CLI command on real container.

        Expected: Exit code 0, password reset successful.
        """
        container_name = iris_container.get_container_name()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "iris_devtester.cli",
                "container",
                "reset-password",
                container_name,
                "--user",
                "_SYSTEM",
                "--password",
                "SYS",
            ],
            capture_output=True,
            text=True,
            timeout=60,  # Allow up to 60s for password verification on slow systems
        )

        assert result.returncode == 0, f"Command should succeed: {result.stderr}"
        assert "reset" in result.stdout.lower() or "success" in result.stdout.lower()

    def test_enable_callin_command(self, iris_container):
        """
        Test enable-callin CLI command on real container.

        Expected: Exit code 0, CallIn service enabled.
        """
        container_name = iris_container.get_container_name()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "iris_devtester.cli",
                "container",
                "enable-callin",
                container_name,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Command should succeed: {result.stderr}"
        assert "enabled" in result.stdout.lower() or "configured" in result.stdout.lower()

    def test_test_connection_command(self, iris_container):
        """
        Test test-connection CLI command on real container.

        Expected: Exit code 0, connection successful message.
        """
        container_name = iris_container.get_container_name()

        # Enable CallIn first (required for connection)
        iris_container.enable_callin_service()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "iris_devtester.cli",
                "container",
                "test-connection",
                container_name,
                "--namespace",
                "USER",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Command should succeed: {result.stderr}"
        assert "successful" in result.stdout.lower()
        assert "USER" in result.stdout

    def test_status_command(self, iris_container):
        """
        Test status CLI command on real container.

        Expected: Exit code 0, multi-line status report.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "iris_devtester.cli",
                "container",
                "status",
                container_name,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Command should succeed: {result.stderr}"

        # Verify multi-line status report (current format)
        assert f"Container: {container_name}" in result.stdout
        assert "Status:" in result.stdout
        assert "Health:" in result.stdout
        assert "Uptime:" in result.stdout
        assert "Ports:" in result.stdout
        assert "Image:" in result.stdout

    def test_cli_commands_fail_for_nonexistent_container(self):
        """
        Test that CLI commands fail gracefully for non-existent container.

        Expected: Exit code 1 (Abort), error message with remediation.
        """
        nonexistent_container = "nonexistent_container_xyz"

        # Test enable-callin (fastest command)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "iris_devtester.cli",
                "container",
                "enable-callin",
                nonexistent_container,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1, "Should exit with code 1 (Abort)"
        # Error messages go to stderr, not stdout
        assert "not running" in result.stderr.lower()
