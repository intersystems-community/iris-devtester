"""
Contract tests for CLI container commands.

These tests verify that CLI commands exist and have proper signatures.
Tests use subprocess to verify CLI --help works without requiring implementation.

TDD Workflow:
1. Write tests (this file) - signature tests pass, behavior tests skip
2. Implement iris_devtester/cli/container_commands.py
3. All tests pass
"""

import pytest
import subprocess
import sys


class TestResetPasswordCommand:
    """Test reset-password CLI command contract (T007)."""

    def test_reset_password_command_exists(self):
        """Contract: iris-devtester container reset-password --help succeeds."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "reset-password", "--help"],
            capture_output=True,
            text=True
        )
        # Command should exist and show help (exit code 0)
        assert result.returncode == 0
        assert "reset-password" in result.stdout.lower() or "password" in result.stdout.lower()

    def test_reset_password_accepts_container_name(self):
        """Contract: Command accepts container_name argument."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "reset-password", "--help"],
            capture_output=True,
            text=True
        )
        # Help should mention container_name or similar argument
        assert "container" in result.stdout.lower() or "CONTAINER_NAME" in result.stdout

    def test_reset_password_has_user_option(self):
        """Contract: Command has --user option."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "reset-password", "--help"],
            capture_output=True,
            text=True
        )
        assert "--user" in result.stdout

    def test_reset_password_has_password_option(self):
        """Contract: Command has --password option."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "reset-password", "--help"],
            capture_output=True,
            text=True
        )
        assert "--password" in result.stdout


class TestEnableCallinCommand:
    """Test enable-callin CLI command contract (T008)."""

    def test_enable_callin_command_exists(self):
        """Contract: iris-devtester container enable-callin --help succeeds."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "enable-callin", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "callin" in result.stdout.lower()

    def test_enable_callin_accepts_container_name(self):
        """Contract: Command accepts container_name argument."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "enable-callin", "--help"],
            capture_output=True,
            text=True
        )
        assert "container" in result.stdout.lower() or "CONTAINER_NAME" in result.stdout


class TestTestConnectionCommand:
    """Test test-connection CLI command contract (T009)."""

    def test_test_connection_command_exists(self):
        """Contract: iris-devtester container test-connection --help succeeds."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "test-connection", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "connection" in result.stdout.lower() or "test" in result.stdout.lower()

    def test_test_connection_accepts_container_name(self):
        """Contract: Command accepts container_name argument."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "test-connection", "--help"],
            capture_output=True,
            text=True
        )
        assert "container" in result.stdout.lower() or "CONTAINER_NAME" in result.stdout

    def test_test_connection_has_namespace_option(self):
        """Contract: Command has --namespace option."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "test-connection", "--help"],
            capture_output=True,
            text=True
        )
        assert "--namespace" in result.stdout


class TestStatusCommand:
    """Test status CLI command contract (T010)."""

    def test_status_command_exists(self):
        """Contract: iris-devtester container status --help succeeds."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "status", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "status" in result.stdout.lower()

    def test_status_accepts_container_name(self):
        """Contract: Command accepts container_name argument."""
        result = subprocess.run(
            [sys.executable, "-m", "iris_devtester.cli", "container", "status", "--help"],
            capture_output=True,
            text=True
        )
        assert "container" in result.stdout.lower() or "CONTAINER_NAME" in result.stdout
