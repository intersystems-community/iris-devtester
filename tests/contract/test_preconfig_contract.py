"""Contract tests for password pre-configuration API (001-preconfigure-passwords).

These tests define the public API contract that must be maintained.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestPreconfigurationDetectionContract:
    """Contract: Pre-configuration detection behavior."""

    def test_should_preconfigure_returns_true_when_api_used(self):
        """Contract: _should_preconfigure() returns True when with_preconfigured_password() called."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = "test"
            container._preconfigure_username = None

            assert container._should_preconfigure() is True

    def test_should_preconfigure_returns_true_when_env_var_set(self):
        """Contract: _should_preconfigure() returns True when IRIS_PASSWORD env var set."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {"IRIS_PASSWORD": "test"}, clear=False):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = None
                container._preconfigure_username = None

                assert container._should_preconfigure() is True


class TestBackwardCompatibilityContract:
    """Contract: Backward compatibility when pre-configuration not used."""

    def test_should_preconfigure_returns_false_when_nothing_set(self):
        """Contract: _should_preconfigure() returns False when neither API nor env var used."""
        from iris_devtester.containers.iris_container import IRISContainer

        env_without_iris = {k: v for k, v in os.environ.items() if k != "IRIS_PASSWORD"}
        with patch.dict(os.environ, env_without_iris, clear=True):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = None
                container._preconfigure_username = None

                assert container._should_preconfigure() is False


class TestProgrammaticApiContract:
    """Contract: Programmatic API for password pre-configuration."""

    def test_with_preconfigured_password_returns_self(self):
        """Contract: with_preconfigured_password() returns self for method chaining."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None

            result = container.with_preconfigured_password("password")

            assert result is container

    def test_with_preconfigured_password_stores_password(self):
        """Contract: with_preconfigured_password() stores password for later use."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None

            container.with_preconfigured_password("MyPassword")

            assert container._preconfigure_password == "MyPassword"

    def test_with_credentials_returns_self(self):
        """Contract: with_credentials() returns self for method chaining."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            result = container.with_credentials("user", "pass")

            assert result is container

    def test_with_credentials_stores_both_values(self):
        """Contract: with_credentials() stores both username and password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            container.with_credentials("_SYSTEM", "SYS")

            assert container._preconfigure_password == "SYS"
            assert container._preconfigure_username == "_SYSTEM"

    def test_with_preconfigured_password_rejects_empty(self):
        """Contract: with_preconfigured_password() raises ValueError for empty password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None

            with pytest.raises(ValueError):
                container.with_preconfigured_password("")

    def test_with_credentials_rejects_empty_password(self):
        """Contract: with_credentials() raises ValueError for empty password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            with pytest.raises(ValueError):
                container.with_credentials("user", "")

    def test_with_credentials_rejects_empty_username(self):
        """Contract: with_credentials() raises ValueError for empty username."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            with pytest.raises(ValueError):
                container.with_credentials("", "pass")


class TestApiPrecedenceContract:
    """Contract: Programmatic API takes precedence over environment variables."""

    def test_api_password_takes_precedence_over_env_var(self):
        """Contract: Programmatic API password overrides IRIS_PASSWORD env var."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {"IRIS_PASSWORD": "EnvPassword"}, clear=False):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = "APIPassword"
                container._preconfigure_username = None
                container._password = "initial"
                container._username = "user"
                container.with_env = MagicMock(return_value=container)

                container._apply_password_preconfig()

                container.with_env.assert_any_call("IRIS_PASSWORD", "APIPassword")
                assert container._password == "APIPassword"
