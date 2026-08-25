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


class TestStartCPFDoesNotUsePlaintext:
    """start() must not pass plaintext password into PasswordHash= CPF field.

    PasswordHash= expects hash,salt PBKDF2 format. Passing plaintext sets a
    corrupt hash — no login works. The fix: use SECURE_DEFAULTS CPF (handles
    CallIn + expiry flags) then reset password post-start via PasswordExternal.
    """

    def test_cpf_merge_does_not_contain_plaintext_password(self):
        """CPF content passed to with_cpf_merge must not contain the plaintext password."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = "MySecret123"
            container._preconfigure_username = None
            container._password_preconfigured = False
            container._port_registry = None
            container._preferred_port = None
            container._project_path = None
            container._port_assignment = None
            container._cpf_temp_files = []
            container._container_name = "test-iris"
            container.with_env = MagicMock(return_value=container)
            container.get_config = MagicMock()

            cpf_calls = []
            def capture_cpf(content):
                cpf_calls.append(content)
                return container
            container.with_cpf_merge = capture_cpf

            with patch.object(IRISContainer.__bases__[0], "start", return_value=container), \
                 patch("iris_devtester.containers.iris_container.reset_password", return_value=MagicMock(success=True)):
                container.start()

            assert cpf_calls, "with_cpf_merge was never called"
            for cpf_content in cpf_calls:
                assert "MySecret123" not in cpf_content, (
                    "Plaintext password must not appear in CPF content — "
                    "PasswordHash= expects hash,salt PBKDF2 format, not plaintext"
                )

    def test_password_reset_called_post_start_when_preconfigured(self):
        """When preconfigure_password is set, reset_password() must be called after super().start()."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
            container = IRISContainer.__new__(IRISContainer)
            container._preconfigure_password = "MySecret123"
            container._preconfigure_username = None
            container._password_preconfigured = False
            container._port_registry = None
            container._preferred_port = None
            container._project_path = None
            container._port_assignment = None
            container._cpf_temp_files = []
            container._container_name = "test-iris"
            container.with_env = MagicMock(return_value=container)
            container.with_cpf_merge = MagicMock(return_value=container)
            container.get_config = MagicMock()

            with patch.object(IRISContainer.__bases__[0], "start", return_value=container), \
                 patch("iris_devtester.containers.iris_container.reset_password") as mock_reset:
                mock_reset.return_value = MagicMock(success=True)
                container.start()

            mock_reset.assert_called_once()
            call_kwargs = mock_reset.call_args
            # Must pass the plaintext password, not a hash
            passed_password = call_kwargs[1].get("new_password") or call_kwargs[0][2] if call_kwargs[0] else None
            if passed_password is None and call_kwargs[1]:
                passed_password = call_kwargs[1].get("new_password")
            assert passed_password == "MySecret123", (
                f"reset_password must receive the plaintext password, got: {passed_password}"
            )


class TestAttachUnexpirePasswords:
    """attach() should call unexpire_all_passwords() to handle enterprise images."""

    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_attach_calls_unexpire_by_default(self, mock_docker, mock_get_config):
        """attach() calls unexpire_all_passwords() by default."""
        from iris_devtester.containers import IRISContainer
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}, "Networks": {}}
        }
        mock_container.name = "my-iris"
        mock_client.containers.get.return_value = mock_container

        with patch("iris_devtester.containers.iris_container.unexpire_all_passwords") as mock_unexpire:
            mock_unexpire.return_value = (True, "ok")
            IRISContainer.attach("my-iris")

        mock_unexpire.assert_called_once_with("my-iris")

    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_attach_skips_unexpire_when_disabled(self, mock_docker, mock_get_config):
        """attach(unexpire_passwords=False) skips the unexpire call."""
        from iris_devtester.containers import IRISContainer

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}, "Networks": {}}
        }
        mock_container.name = "my-iris"
        mock_client.containers.get.return_value = mock_container

        with patch("iris_devtester.containers.iris_container.unexpire_all_passwords") as mock_unexpire:
            IRISContainer.attach("my-iris", unexpire_passwords=False)

        mock_unexpire.assert_not_called()

    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_attach_swallows_unexpire_failure(self, mock_docker, mock_get_config):
        """attach() must not raise if unexpire_all_passwords() fails."""
        from iris_devtester.containers import IRISContainer

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"1972/tcp": [{"HostPort": "1972"}]}, "Networks": {}}
        }
        mock_container.name = "my-iris"
        mock_client.containers.get.return_value = mock_container

        with patch("iris_devtester.containers.iris_container.unexpire_all_passwords") as mock_unexpire:
            mock_unexpire.return_value = (False, "container not running")
            # Must not raise
            iris = IRISContainer.attach("my-iris")

        assert iris is not None


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
            container._port_registry = None
            container._preferred_port = None
            container._project_path = None
            container._port_assignment = None
            container._container_name = "test-iris"
            container.with_env = MagicMock(return_value=container)
            container.with_cpf_merge = MagicMock(return_value=container)
            container.get_config = MagicMock()

            with patch.object(IRISContainer.__bases__[0], "start", return_value=container), \
                 patch("iris_devtester.containers.iris_container.reset_password", return_value=MagicMock(success=True)):
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
            container._port_registry = None
            container._preferred_port = None
            container._project_path = None
            container._port_assignment = None
            container._container_name = "test-iris"
            container.with_env = MagicMock(return_value=container)
            container.with_cpf_merge = MagicMock(return_value=container)
            container.get_config = MagicMock()

            with patch.object(IRISContainer.__bases__[0], "start", return_value=container), \
                 patch("iris_devtester.containers.iris_container.reset_password", return_value=MagicMock(success=True)):
                container.start()

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
