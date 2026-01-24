"""Unit tests for password pre-configuration feature (001-preconfigure-passwords)."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestShouldPreconfigure:
    """Tests for IRISContainer._should_preconfigure() logic."""

    def test_returns_true_when_preconfigure_password_set_via_api(self):
        """When with_preconfigured_password() was called, should return True."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("IRIS_PASSWORD", None)

            from iris_devtester.containers.iris_container import IRISContainer

            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = "SYS"
                container._preconfigure_username = None

                assert container._should_preconfigure() is True

    def test_returns_true_when_iris_password_env_var_set(self):
        """When IRIS_PASSWORD env var is set, should return True."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {"IRIS_PASSWORD": "MyPassword"}, clear=False):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = None
                container._preconfigure_username = None

                assert container._should_preconfigure() is True

    def test_returns_false_when_no_preconfig_set(self):
        """When neither API nor env var set, should return False."""
        from iris_devtester.containers.iris_container import IRISContainer

        env_without_iris = {k: v for k, v in os.environ.items() if k != "IRIS_PASSWORD"}
        with patch.dict(os.environ, env_without_iris, clear=True):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = None
                container._preconfigure_username = None

                assert container._should_preconfigure() is False


class TestApplyPasswordPreconfig:
    """Tests for IRISContainer._apply_password_preconfig() logic."""

    def test_applies_password_from_api(self):
        """When password set via API, applies it to container env."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {}, clear=True):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = "APIPassword"
                container._preconfigure_username = None
                container._password = "OldPassword"
                container._username = "OldUser"
                container.with_env = MagicMock(return_value=container)

                container._apply_password_preconfig()

                container.with_env.assert_any_call("IRIS_PASSWORD", "APIPassword")
                assert container._password == "APIPassword"

    def test_applies_password_from_env_var(self):
        """When password set via env var, applies it to container."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {"IRIS_PASSWORD": "EnvPassword"}, clear=False):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = None
                container._preconfigure_username = None
                container._password = "OldPassword"
                container._username = "OldUser"
                container.with_env = MagicMock(return_value=container)

                container._apply_password_preconfig()

                container.with_env.assert_any_call("IRIS_PASSWORD", "EnvPassword")
                assert container._password == "EnvPassword"

    def test_api_takes_precedence_over_env_var(self):
        """When both API and env var set, API takes precedence."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {"IRIS_PASSWORD": "EnvPassword"}, clear=False):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = "APIPassword"
                container._preconfigure_username = None
                container._password = "OldPassword"
                container._username = "OldUser"
                container.with_env = MagicMock(return_value=container)

                container._apply_password_preconfig()

                container.with_env.assert_any_call("IRIS_PASSWORD", "APIPassword")
                assert container._password == "APIPassword"

    def test_applies_username_when_set(self):
        """When username set via API, applies it to container env."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict(os.environ, {}, clear=True):
            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
                container = IRISContainer.__new__(IRISContainer)
                container._preconfigure_password = "Password"
                container._preconfigure_username = "CustomUser"
                container._password = "OldPassword"
                container._username = "OldUser"
                container.with_env = MagicMock(return_value=container)

                container._apply_password_preconfig()

                container.with_env.assert_any_call("IRIS_USERNAME", "CustomUser")
                assert container._username == "CustomUser"


class TestWithPreconfiguredPassword:
    """Tests for with_preconfigured_password() API."""

    def test_sets_preconfigure_password_and_returns_self(self):
        """Method sets internal state and returns self for chaining."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None

            result = container.with_preconfigured_password("TestPassword")

            assert result is container
            assert container._preconfigure_password == "TestPassword"

    def test_raises_on_empty_password(self):
        """Empty password raises ValueError."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None

            with pytest.raises(ValueError, match="Password cannot be empty"):
                container.with_preconfigured_password("")


class TestWithCredentials:
    """Tests for with_credentials() API."""

    def test_sets_both_username_and_password(self):
        """Method sets both username and password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            result = container.with_credentials("_SYSTEM", "SecurePass")

            assert result is container
            assert container._preconfigure_password == "SecurePass"
            assert container._preconfigure_username == "_SYSTEM"

    def test_raises_on_empty_password(self):
        """Empty password raises ValueError."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            with pytest.raises(ValueError, match="Password cannot be empty"):
                container.with_credentials("user", "")

    def test_raises_on_empty_username(self):
        """Empty username raises ValueError."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            with pytest.raises(ValueError, match="Username cannot be empty"):
                container.with_credentials("", "password")


class TestEdgeCases:
    """Edge case tests for password pre-configuration."""

    def test_invalid_empty_password_via_api(self):
        """Empty password via API raises immediately."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS_IRIS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None

            with pytest.raises(ValueError):
                container.with_preconfigured_password("")
