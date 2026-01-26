"""Unit tests for password pre-configuration feature (001-preconfigure-passwords)."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestWithPreconfiguredPassword:
    """Tests for with_preconfigured_password() API."""

    def test_sets_preconfigure_password_and_returns_self(self):
        """Method sets internal state and returns self for chaining."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._password = None

            result = container.with_preconfigured_password("TestPassword")

            assert result is container
            assert container._preconfigure_password == "TestPassword"
            assert container._password == "TestPassword"

    def test_raises_on_empty_password(self):
        """Empty password raises ValueError."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._password = None

            with pytest.raises(ValueError, match="Password cannot be empty"):
                container.with_preconfigured_password("")


class TestWithCredentials:
    """Tests for with_credentials() API."""

    def test_sets_both_username_and_password(self):
        """Method sets both username and password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None
            container._password = None
            container._username = None

            result = container.with_credentials("_SYSTEM", "SecurePass")

            assert result is container
            assert container._preconfigure_password == "SecurePass"
            assert container._preconfigure_username == "_SYSTEM"
            assert container._password == "SecurePass"
            assert container._username == "_SYSTEM"

    def test_raises_on_empty_password(self):
        """Empty password raises ValueError."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            with pytest.raises(ValueError, match="Password cannot be empty"):
                container.with_credentials("user", "")

    def test_raises_on_empty_username(self):
        """Empty username raises ValueError."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._preconfigure_username = None

            with pytest.raises(ValueError, match="Username cannot be empty"):
                container.with_credentials("", "password")


class TestStartWithPreconfig:
    """Tests for start() method with pre-configuration."""

    def test_start_applies_password_env_var(self):
        """Start method applies password to container environment."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = "TestPass"
            container._preconfigure_username = None
            container._password_preconfigured = False
            container.with_env = MagicMock(return_value=container)
            container.get_config = MagicMock()

            # Mock parent start
            with patch.object(IRISContainer.__bases__[0], "start", return_value=container):
                container.start()

            container.with_env.assert_called_with("IRIS_PASSWORD", "TestPass")
            assert container._password_preconfigured is True

    def test_start_applies_username_env_var(self):
        """Start method applies username to container environment when set."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = "TestPass"
            container._preconfigure_username = "TestUser"
            container._password_preconfigured = False
            container.with_env = MagicMock(return_value=container)
            container.get_config = MagicMock()

            # Mock parent start
            with patch.object(IRISContainer.__bases__[0], "start", return_value=container):
                container.start()

            # Check both calls were made
            calls = container.with_env.call_args_list
            assert any(
                call[0] == ("IRIS_PASSWORD", "TestPass") for call in calls
            ), "IRIS_PASSWORD not set"
            assert any(
                call[0] == ("IRIS_USERNAME", "TestUser") for call in calls
            ), "IRIS_USERNAME not set"


class TestEdgeCases:
    """Edge case tests for password pre-configuration."""

    def test_invalid_empty_password_via_api(self):
        """Empty password via API raises immediately."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._password = None

            with pytest.raises(ValueError):
                container.with_preconfigured_password("")

    def test_with_preconfigured_password_updates_both_fields(self):
        """with_preconfigured_password updates both _preconfigure_password and _password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = None
            container._password = "OldPassword"

            container.with_preconfigured_password("NewPassword")

            assert container._preconfigure_password == "NewPassword"
            assert container._password == "NewPassword"
