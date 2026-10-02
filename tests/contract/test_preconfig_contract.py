"""Contract tests for password pre-configuration API (001-preconfigure-passwords).

Rewritten in feature 036 (T022). The previous file patched a nonexistent module
attribute and called methods that no longer exist, so none of its tests ran.
Everything it asserted about ``with_preconfigured_password`` / ``with_credentials``
(chaining, storing, rejecting empty values) is covered by
``tests/unit/test_password_preconfig.py`` and was deleted here. What remains is
the behaviour that file does not pin: precedence over the process environment
and backward compatibility when the API is unused.
"""

from unittest.mock import MagicMock, patch

from iris_devtester.containers.iris_container import IRISContainer


def _bare_container(password=None, username=None):
    container = IRISContainer.__new__(IRISContainer)
    container._preconfigure_password = password
    container._preconfigure_username = username
    container._password_preconfigured = False
    container._port_registry = None
    container._preferred_port = None
    container._project_path = None
    container._port_assignment = None
    container._cpf_temp_files = []
    container._container_name = "contract-iris"
    container.with_env = MagicMock(return_value=container)
    container.with_cpf_merge = MagicMock(return_value=container)
    container.get_config = MagicMock(return_value=MagicMock(host="localhost", port=1972))
    container.get_container_name = MagicMock(return_value="contract-iris")
    return container


def _start(container):
    with (
        patch.object(IRISContainer.__bases__[0], "start", return_value=container),
        patch(
            "iris_devtester.containers.iris_container.reset_password",
            return_value=MagicMock(success=True),
        ) as reset,
    ):
        container.start()
    return reset


class TestApiPrecedenceContract:
    """Contract: the programmatic API wins over the IRIS_PASSWORD process variable."""

    def test_api_password_takes_precedence_over_env_var(self, monkeypatch):
        monkeypatch.setenv("IRIS_PASSWORD", "EnvPassword")
        container = _bare_container(password="APIPassword")

        reset = _start(container)

        container.with_env.assert_any_call("IRIS_PASSWORD", "APIPassword")
        values = [call.args[1] for call in container.with_env.call_args_list]
        assert "EnvPassword" not in values
        assert reset.call_args.kwargs["new_password"] == "APIPassword"


class TestBackwardCompatibilityContract:
    """Contract: nothing is pre-configured unless the API is used."""

    def test_start_without_preconfiguration_sets_no_credentials(self, monkeypatch):
        monkeypatch.delenv("IRIS_PASSWORD", raising=False)
        container = _bare_container()

        reset = _start(container)

        container.with_env.assert_not_called()
        reset.assert_not_called()
