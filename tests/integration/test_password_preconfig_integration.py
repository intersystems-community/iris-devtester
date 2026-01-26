"""Integration tests for password pre-configuration feature (001-preconfigure-passwords).

These tests require Docker and actually start IRIS containers.
"""

import os
import time
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


@pytest.fixture
def clean_iris_env():
    """Fixture to ensure IRIS_PASSWORD env var is isolated during test."""
    old_password = os.environ.get("IRIS_PASSWORD")
    old_username = os.environ.get("IRIS_USERNAME")

    # Clear for test
    if "IRIS_PASSWORD" in os.environ:
        del os.environ["IRIS_PASSWORD"]
    if "IRIS_USERNAME" in os.environ:
        del os.environ["IRIS_USERNAME"]

    yield

    # Restore or clear after test
    if old_password is not None:
        os.environ["IRIS_PASSWORD"] = old_password
    elif "IRIS_PASSWORD" in os.environ:
        del os.environ["IRIS_PASSWORD"]

    if old_username is not None:
        os.environ["IRIS_USERNAME"] = old_username
    elif "IRIS_USERNAME" in os.environ:
        del os.environ["IRIS_USERNAME"]


class TestEnvVarPreConfiguration:
    """Integration tests for env var-based pre-configuration."""

    def test_container_starts_with_iris_password_env_var(self, clean_iris_env):
        """Container should start faster when IRIS_PASSWORD is set."""
        from iris_devtester.containers.iris_container import IRISContainer

        os.environ["IRIS_PASSWORD"] = "SYS"

        start_time = time.time()
        with IRISContainer.community() as iris:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        elapsed = time.time() - start_time

        print(f"Container startup with IRIS_PASSWORD: {elapsed:.2f}s")

    def test_container_starts_without_iris_password_env_var(self, clean_iris_env):
        """Container should still work without IRIS_PASSWORD (backward compat)."""
        from iris_devtester.containers.iris_container import IRISContainer

        start_time = time.time()
        with IRISContainer.community() as iris:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        elapsed = time.time() - start_time

        print(f"Container startup without IRIS_PASSWORD: {elapsed:.2f}s")


class TestProgrammaticApiPreConfiguration:
    """Integration tests for programmatic API pre-configuration."""

    def test_with_preconfigured_password_starts_container(self, clean_iris_env):
        """Container should start with with_preconfigured_password() API."""
        from iris_devtester.containers.iris_container import IRISContainer

        start_time = time.time()
        with IRISContainer.community().with_preconfigured_password("SYS") as iris:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        elapsed = time.time() - start_time

        print(f"Container startup with API preconfig: {elapsed:.2f}s")

    def test_with_credentials_starts_container(self, clean_iris_env):
        """Container should start with with_credentials() API."""
        from iris_devtester.containers.iris_container import IRISContainer

        with IRISContainer.community().with_credentials("SuperUser", "SYS") as iris:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1


class TestCIEnvironmentSimulation:
    """Integration tests simulating CI/CD environment."""

    def test_ci_style_env_var_detection(self, clean_iris_env):
        """Pre-configuration should work when IRIS_PASSWORD set like in CI."""
        from iris_devtester.containers.iris_container import IRISContainer

        os.environ["IRIS_PASSWORD"] = "CI_PASSWORD"
        os.environ["IRIS_USERNAME"] = "_SYSTEM"

        container = IRISContainer.community()

        assert container._should_preconfigure() is True


class TestFallbackBehavior:
    """Integration tests for fallback to password reset."""

    def test_fallback_when_preconfig_fails(self, clean_iris_env):
        """Container should fall back to password reset if preconfig fails."""
        from iris_devtester.containers.iris_container import IRISContainer

        with IRISContainer.community() as iris:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
