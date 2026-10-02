"""Unit tests for the in-house IRIS testcontainer base.

iris-devtester used to subclass ``testcontainers.iris.IRISContainer`` from the
CaretDev ``testcontainers-iris`` package, which hard-requires ``sqlalchemy-iris``.
sqlalchemy-iris ships its own ``iris/__init__.py`` that collides with
intersystems-irispython under some resolvers (uv), turning ``iris.connect`` into
a stub. These tests pin the absorbed behavior and guard against the dependency
creeping back in.
"""

import logging
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import docker.errors
import pytest
from testcontainers.core.exceptions import ContainerStartException

from iris_devtester.containers._base import IRISDockerContainer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean_iris_env(monkeypatch):
    for var in ("IRIS_USERNAME", "IRIS_PASSWORD", "IRIS_NAMESPACE"):
        monkeypatch.delenv(var, raising=False)


class TestNoCaretDevDependency:
    def test_import_does_not_pull_sqlalchemy_or_testcontainers_iris(self):
        code = (
            "import sys\n"
            "import iris_devtester\n"
            "import iris_devtester.containers\n"
            "import iris_devtester.utils.iris_container_adapter\n"
            "import iris_devtester.cli\n"
            "bad = [m for m in sys.modules if m.startswith(('sqlalchemy', 'testcontainers.iris'))]\n"
            "print(','.join(bad))\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        assert out.stdout.strip() == ""

    def test_pyproject_does_not_depend_on_testcontainers_iris(self):
        text = (REPO_ROOT / "pyproject.toml").read_text()
        assert "testcontainers-iris" not in text
        assert "sqlalchemy-iris" not in text

    def test_packaging_declared(self):
        # dbapi_compat imports packaging; it used to arrive transitively via
        # the CaretDev chain, so a clean install broke once that was dropped.
        text = (REPO_ROOT / "pyproject.toml").read_text()
        deps_block = text.split("dependencies = [", 1)[1].split("]", 1)[0]
        assert '"packaging' in deps_block

    def test_iris_container_uses_in_house_base(self):
        from iris_devtester.containers import iris_container

        assert issubclass(iris_container.IRISContainer, IRISDockerContainer)

    def test_adapter_uses_iris_devtester_container(self):
        from iris_devtester.containers.iris_container import IRISContainer
        from iris_devtester.utils import iris_container_adapter

        assert iris_container_adapter.IRISContainer is IRISContainer


class TestInit:
    def test_defaults(self, monkeypatch):
        for var in ("IRIS_USERNAME", "IRIS_PASSWORD", "IRIS_NAMESPACE"):
            monkeypatch.delenv(var, raising=False)
        c = IRISDockerContainer()
        assert c.image == "intersystemsdc/iris-community:latest"
        assert c.port == 1972
        # No baked-in test/test %ALL account (upstream testcontainers-iris default)
        assert c.username is None
        assert c.password is None
        assert c.namespace == "USER"
        assert c.license_key is None
        assert 1972 in c.ports

    def test_env_fallbacks(self, monkeypatch):
        monkeypatch.setenv("IRIS_USERNAME", "envuser")
        monkeypatch.setenv("IRIS_PASSWORD", "envpw")
        monkeypatch.setenv("IRIS_NAMESPACE", "ENVNS")
        c = IRISDockerContainer()
        assert (c.username, c.password, c.namespace) == ("envuser", "envpw", "ENVNS")

    def test_explicit_args_win(self, monkeypatch):
        monkeypatch.setenv("IRIS_USERNAME", "envuser")
        c = IRISDockerContainer(
            image="img:1", port=1999, username="u", password="p", namespace="NS", license_key="/k"
        )
        assert (c.image, c.port, c.username, c.password, c.namespace) == (
            "img:1",
            1999,
            "u",
            "p",
            "NS",
        )
        assert c.license_key == "/k"
        assert 1999 in c.ports


class TestConfigure:
    def test_no_license_no_volume(self):
        c = IRISDockerContainer()
        c.with_volume_mapping = MagicMock()
        c._configure()
        c.with_volume_mapping.assert_not_called()

    def test_license_mapped_read_only(self):
        c = IRISDockerContainer(license_key="/tmp/iris.key")
        c.with_volume_mapping = MagicMock()
        c._configure()
        c.with_volume_mapping.assert_called_once_with(
            "/tmp/iris.key", "/usr/irissys/mgr/iris.key", "ro"
        )


def _started(c, exit_code=0, output=b"IDT_OK\n"):
    """Attach a fake docker container whose exec_run returns a fixed result."""
    c._container = MagicMock()
    c._container.exec_run.return_value = SimpleNamespace(exit_code=exit_code, output=output)
    return c._container.exec_run


class TestConnect:
    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_user_namespace_skips_create_database(self, mock_wait):
        c = IRISDockerContainer(username="u", password="p")
        exec_run = _started(c)
        c._connect()
        mock_wait.assert_called_once()
        predicate = mock_wait.call_args.kwargs["predicate"]
        assert predicate("... Enabling logons ...")
        assert not predicate("still starting")
        assert exec_run.call_count == 1
        script = exec_run.call_args.args[0][-1]
        assert "Security.Users).Create(" in script
        assert "-U %SYS" in script
        assert exec_run.call_args.kwargs["environment"] == {
            "IDT_USERNAME": "u",
            "IDT_PASSWORD": "p",
        }

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_custom_namespace_creates_database(self, mock_wait):
        c = IRISDockerContainer(namespace="MYNS")
        exec_run = _started(c)
        c._connect()
        assert exec_run.call_count == 1
        script = exec_run.call_args.args[0][-1]
        assert "CREATE DATABASE" in script
        assert "%SQL.Statement).%ExecDirect" in script
        assert exec_run.call_args.kwargs["environment"] == {"IDT_NAMESPACE": "MYNS"}
        assert "MYNS" not in script

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_no_credentials_creates_no_user(self, mock_wait):
        c = IRISDockerContainer()
        exec_run = _started(c)
        c._connect()
        mock_wait.assert_called_once()
        exec_run.assert_not_called()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_env_credentials_opt_in_to_user_creation(self, mock_wait, monkeypatch):
        monkeypatch.setenv("IRIS_USERNAME", "envuser")
        monkeypatch.setenv("IRIS_PASSWORD", "envpw")
        c = IRISDockerContainer()
        exec_run = _started(c)
        c._connect()
        assert exec_run.call_args.kwargs["environment"] == {
            "IDT_USERNAME": "envuser",
            "IDT_PASSWORD": "envpw",
        }

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_iris_container_creates_no_extra_user(self, mock_wait):
        from iris_devtester.containers.iris_container import IRISContainer

        c = IRISContainer()
        exec_run = _started(c)
        c._connect()
        exec_run.assert_not_called()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_expired_community_license_raises_guidance(self, mock_wait):
        mock_wait.side_effect = TimeoutError("did not emit logs")
        c = IRISDockerContainer(
            image="containers.intersystems.com/intersystems/iris-community:2025.1"
        )
        c.get_logs = MagicMock(
            return_value=(
                b"Error: Invalid Community Edition license, may have exceeded core limit.",
                b"",
            )
        )
        with pytest.raises(RuntimeError) as exc:
            c._connect()
        msg = str(exc.value)
        assert "iris-community:2025.1" in msg
        assert "expired" in msg
        assert "latest-em" in msg
        assert isinstance(exc.value.__cause__, TimeoutError)

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_license_error_stops_wait_early(self, mock_wait):
        # Fail fast: predicate must also match the license error so we don't
        # sit through the full log-wait timeout on a dead container.
        c = IRISDockerContainer(image="img:old")
        c.get_logs = MagicMock(return_value=(b"Invalid Community Edition license", b""))
        exec_run = _started(c)
        with pytest.raises(RuntimeError, match="community license rejected"):
            c._connect()
        predicate = mock_wait.call_args.kwargs["predicate"]
        assert predicate("Error: Invalid Community Edition license, may have exceeded core limit")
        exec_run.assert_not_called()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_other_timeouts_propagate_unchanged(self, mock_wait):
        mock_wait.side_effect = TimeoutError("did not emit logs")
        c = IRISDockerContainer()
        c.get_logs = MagicMock(return_value=(b"something else", b""))
        with pytest.raises(TimeoutError):
            c._connect()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_timeout_path_states_logs_unreadable(self, mock_wait):
        mock_wait.side_effect = TimeoutError("did not emit logs")
        c = IRISDockerContainer()
        c.get_logs = MagicMock(side_effect=docker.errors.APIError("container gone"))
        with pytest.raises(TimeoutError) as exc:
            c._connect()
        msg = str(exc.value)
        assert "did not emit logs" in msg
        assert "licence check could not read the container logs" in msg
        assert isinstance(exc.value.__cause__, TimeoutError)
        assert c._community_license_rejected() is False


class TestLicenceCheckPolicy:
    def test_docker_error_warns_and_returns_false(self, caplog):
        c = IRISDockerContainer()
        c.get_logs = MagicMock(side_effect=docker.errors.APIError("container gone"))
        with caplog.at_level(logging.WARNING, logger="iris_devtester.containers._base"):
            assert c._community_license_rejected() is False
        assert any(
            r.levelno == logging.WARNING and "container gone" in r.getMessage()
            for r in caplog.records
        )

    def test_container_not_started_warns_and_returns_false(self, caplog):
        c = IRISDockerContainer()
        c.get_logs = MagicMock(side_effect=ContainerStartException("not started"))
        with caplog.at_level(logging.WARNING, logger="iris_devtester.containers._base"):
            assert c._community_license_rejected() is False
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_programming_errors_propagate(self):
        c = IRISDockerContainer()
        c.get_logs = MagicMock(side_effect=RuntimeError("bug"))
        with pytest.raises(RuntimeError, match="bug"):
            c._community_license_rejected()
        c.get_logs = MagicMock(side_effect=AttributeError("bug"))
        with pytest.raises(AttributeError):
            c._community_license_rejected()

    def test_rejected_log_returns_true(self):
        c = IRISDockerContainer()
        c.get_logs = MagicMock(return_value=(b"x Invalid Community Edition license y", b""))
        assert c._community_license_rejected() is True

    def test_accepted_log_returns_false(self):
        c = IRISDockerContainer()
        c.get_logs = MagicMock(return_value=(b"Enabling logons", b""))
        assert c._community_license_rejected() is False

    def test_none_streams_tolerated(self):
        c = IRISDockerContainer()
        c.get_logs = MagicMock(return_value=(None, None))
        assert c._community_license_rejected() is False


class TestLicenceUnreadableEndToEnd:
    """T014: fake container whose logs fail and whose health never arrives."""

    def test_surfaces_message_and_warning(self, caplog):
        c = IRISDockerContainer(image="img:x")
        c.get_logs = MagicMock(side_effect=docker.errors.APIError("socket closed"))
        with patch(
            "iris_devtester.containers._base.wait_for_logs",
            side_effect=TimeoutError("Container did not emit logs in 1 s"),
        ):
            with caplog.at_level(logging.WARNING, logger="iris_devtester.containers._base"):
                with pytest.raises(TimeoutError) as exc:
                    c._connect()
        assert "licence check could not read the container logs" in str(exc.value)
        assert "socket closed" in str(exc.value)
        assert any("socket closed" in r.getMessage() for r in caplog.records)


class TestStart:
    def test_start_order(self):
        c = IRISDockerContainer()
        order = []
        c._configure = lambda: order.append("configure")
        c._connect = lambda: order.append("connect")
        with patch(
            "testcontainers.core.container.DockerContainer.start",
            lambda self: order.append("docker_start") or self,
        ):
            assert c.start() is c
        assert order == ["configure", "docker_start", "connect"]


class TestConnectionUrl:
    def test_requires_started_container(self):
        c = IRISDockerContainer()
        with pytest.raises(Exception, match="not been started"):
            c.get_connection_url()

    def test_url_format(self):
        c = IRISDockerContainer(username="u", password="p w/@", namespace="NS")
        c._container = MagicMock()
        c.get_container_host_ip = MagicMock(return_value="h")
        c.get_exposed_port = MagicMock(return_value=40000)
        assert c.get_connection_url() == "iris://u:p w%2F%40@h:40000/NS"
        c.get_exposed_port.assert_called_once_with(1972)

    def test_url_defaults_to_system_credentials(self):
        c = IRISDockerContainer()
        c._container = MagicMock()
        c.get_exposed_port = MagicMock(return_value=1)
        assert c.get_connection_url(host="x") == "iris://_SYSTEM:SYS@x:1/USER"

    def test_iris_container_url_uses_its_credentials(self):
        from iris_devtester.containers.iris_container import IRISContainer

        c = IRISContainer(username="admin", password="pw")
        c._container = MagicMock()
        c.get_exposed_port = MagicMock(return_value=2)
        assert c.get_connection_url(host="x") == "iris://admin:pw@x:2/USER"

    def test_url_host_override(self):
        c = IRISDockerContainer(username="u", password="p")
        c._container = MagicMock()
        c.get_exposed_port = MagicMock(return_value=1)
        assert c.get_connection_url(host="x") == "iris://u:p@x:1/USER"


NASTY_PASSWORD = "a\"b'c$(x)"


class TestNamespaceValidation:
    @pytest.mark.parametrize("ns", ["MY_NS", "A", "A" * 64, "user", "USER", "Ns9_x"])
    def test_accepts(self, ns):
        assert IRISDockerContainer(namespace=ns).namespace == ns

    @pytest.mark.parametrize(
        "ns",
        ["", "A" * 65, "1NS", "MY NS; rm", "my-ns", "%SYS", "a'b", 'a"b', "_NS", "NS\n"],
    )
    def test_rejects(self, ns):
        # empty string falls back to USER through the "or" chain, so only the
        # non-empty values are checked for rejection here
        if ns == "":
            assert IRISDockerContainer(namespace=ns).namespace == "USER"
            return
        with pytest.raises(ValueError) as exc:
            IRISDockerContainer(namespace=ns)
        msg = str(exc.value)
        assert "Invalid namespace" in msg
        assert "What went wrong" in msg
        assert "How to fix it" in msg
        assert "IRIS_NAMESPACE" in msg

    def test_validation_runs_before_start(self):
        with patch("testcontainers.core.container.DockerContainer.start") as docker_start:
            with pytest.raises(ValueError):
                c = IRISDockerContainer(namespace="MY NS; rm")
                c.start()
        docker_start.assert_not_called()

    def test_env_source_is_validated_and_named(self, monkeypatch):
        monkeypatch.setenv("IRIS_NAMESPACE", "bad ns")
        with pytest.raises(ValueError) as exc:
            IRISDockerContainer()
        assert "IRIS_NAMESPACE" in str(exc.value)

    def test_invalid_namespace_errors_even_without_user(self):
        with pytest.raises(ValueError):
            IRISDockerContainer(namespace="x y")


class TestUsernameValidation:
    @pytest.mark.parametrize("name", ["bob", "_svc", "a.b@c-d", "U" * 128, "9lives"])
    def test_accepts(self, name):
        assert IRISDockerContainer(username=name, password="pw").username == name

    @pytest.mark.parametrize("name", ["a b", "a'b", 'a"b', "U" * 129, ".lead", "a;b"])
    def test_rejects_when_password_set(self, name):
        with pytest.raises(ValueError) as exc:
            IRISDockerContainer(username=name, password="pw")
        msg = str(exc.value)
        assert "Invalid username" in msg
        assert "IRIS_USERNAME" in msg
        assert "What went wrong" in msg and "How to fix it" in msg
        assert "pw" not in msg.replace("password", "")

    def test_env_source_is_validated_and_named(self, monkeypatch):
        monkeypatch.setenv("IRIS_USERNAME", "bad name")
        monkeypatch.setenv("IRIS_PASSWORD", "pw")
        with pytest.raises(ValueError) as exc:
            IRISDockerContainer()
        assert "IRIS_USERNAME" in str(exc.value)


class TestOptInRules:
    def test_username_without_password_ignores_invalid_username(self):
        c = IRISDockerContainer(username="bad name; drop")
        assert c.username == "bad name; drop"

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_username_without_password_runs_no_command(self, mock_wait):
        c = IRISDockerContainer(username="bad name")
        exec_run = _started(c)
        c._connect()
        exec_run.assert_not_called()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_password_without_username_runs_no_command(self, mock_wait):
        c = IRISDockerContainer(password=NASTY_PASSWORD)
        exec_run = _started(c)
        c._connect()
        exec_run.assert_not_called()

    def test_invalid_namespace_without_user_still_raises(self):
        with pytest.raises(ValueError):
            IRISDockerContainer(namespace="MY NS")

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_namespace_user_runs_no_create_database(self, mock_wait):
        c = IRISDockerContainer(namespace="USER")
        exec_run = _started(c)
        c._connect()
        exec_run.assert_not_called()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_env_sources_drive_user_creation(self, mock_wait, monkeypatch):
        monkeypatch.setenv("IRIS_USERNAME", "svc")
        monkeypatch.setenv("IRIS_PASSWORD", NASTY_PASSWORD)
        monkeypatch.setenv("IRIS_NAMESPACE", "APP")
        c = IRISDockerContainer()
        exec_run = _started(c)
        c._connect()
        assert exec_run.call_count == 2
        assert exec_run.call_args.kwargs["environment"]["IDT_PASSWORD"] == NASTY_PASSWORD


class TestPasswordHandling:
    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_quoted_password_reaches_environment_unchanged(self, mock_wait):
        c = IRISDockerContainer(username="u", password=NASTY_PASSWORD)
        exec_run = _started(c)
        c._connect()
        assert exec_run.call_args.kwargs["environment"]["IDT_PASSWORD"] == NASTY_PASSWORD
        command = exec_run.call_args.args[0]
        assert isinstance(command, list)
        assert all(NASTY_PASSWORD not in part for part in command)
        assert all('a"b' not in part for part in command)

    @pytest.mark.parametrize("bad", ["", "a\x00b"])
    def test_invalid_password_rejected_without_echo(self, bad):
        with pytest.raises(ValueError) as exc:
            IRISDockerContainer(username="u", password=bad)
        msg = str(exc.value)
        assert "password must be non-empty and must not contain a NUL character" in msg
        if bad:
            assert bad not in msg
            assert "a" + "\x00" not in msg

    def test_empty_password_without_username_is_unset(self):
        assert IRISDockerContainer(password="").password in (None, "")

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_password_never_logged(self, mock_wait, caplog):
        caplog.set_level(logging.DEBUG, logger="iris_devtester")
        c = IRISDockerContainer(username="u", password=NASTY_PASSWORD, namespace="APP")
        _started(c)
        c._connect()
        for record in caplog.records:
            assert NASTY_PASSWORD not in record.getMessage()
            assert "IDT_PASSWORD" not in record.getMessage()

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_password_never_logged_on_failure(self, mock_wait, caplog):
        caplog.set_level(logging.DEBUG, logger="iris_devtester")
        c = IRISDockerContainer(username="u", password=NASTY_PASSWORD)
        _started(c, exit_code=1, output=("IDT_ERR:bad " + NASTY_PASSWORD).encode())
        with pytest.raises(RuntimeError) as exc:
            c._connect()
        assert NASTY_PASSWORD not in str(exc.value)
        for record in caplog.records:
            assert NASTY_PASSWORD not in record.getMessage()


class TestExecFailures:
    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_create_database_failure_raises_structured_error(self, mock_wait):
        c = IRISDockerContainer(namespace="APP")
        _started(c, exit_code=1, output=b"IDT_ERR:already exists")
        with pytest.raises(RuntimeError) as exc:
            c._connect()
        msg = str(exc.value)
        assert "create database" in msg.lower()
        assert "'APP'" in msg
        assert "exit code 1" in msg
        assert "What went wrong" in msg and "How to fix it" in msg

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_create_user_failure_raises_structured_error(self, mock_wait):
        c = IRISDockerContainer(username="svc", password=NASTY_PASSWORD)
        _started(c, exit_code=1, output=b"IDT_ERR:boom")
        with pytest.raises(RuntimeError) as exc:
            c._connect()
        msg = str(exc.value)
        assert "create user" in msg.lower()
        assert "'svc'" in msg
        assert NASTY_PASSWORD not in msg
        assert "What went wrong" in msg and "How to fix it" in msg

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_create_database_failure_stops_before_user_step(self, mock_wait):
        c = IRISDockerContainer(username="svc", password="pw", namespace="APP")
        exec_run = _started(c, exit_code=1, output=b"IDT_ERR:x")
        with pytest.raises(RuntimeError):
            c._connect()
        assert exec_run.call_count == 1

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_commands_are_constant_across_values(self, mock_wait):
        seen = []
        for user, pw, ns in [("a", "x", "N1"), ("b_c", NASTY_PASSWORD, "N2_x")]:
            c = IRISDockerContainer(username=user, password=pw, namespace=ns)
            exec_run = _started(c)
            c._connect()
            seen.append([call.args[0] for call in exec_run.call_args_list])
        assert seen[0] == seen[1]

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_output_scrubbed_of_password_in_error(self, mock_wait):
        c = IRISDockerContainer(username="svc", password="s3cretvalue")
        _started(c, exit_code=1, output=b"IDT_ERR:bad s3cretvalue here")
        with pytest.raises(RuntimeError) as exc:
            c._connect()
        assert "s3cretvalue" not in str(exc.value)


class TestDeadCodeRemoved:
    """FR-012 / T016."""

    def test_no_driver_attribute(self):
        assert not hasattr(IRISDockerContainer(), "driver")

    def test_driver_keyword_rejected(self):
        with pytest.raises(TypeError, match="driver"):
            IRISDockerContainer(driver="iris")

    def test_iris_container_derives_from_base_directly(self):
        from iris_devtester.containers.iris_container import IRISContainer

        assert IRISContainer.__bases__ == (IRISDockerContainer,)
        assert IRISDockerContainer in IRISContainer.__mro__
        assert all(k.__name__ != "_IRISMockContainer" for k in IRISContainer.__mro__)

    def test_module_has_no_fallback_names(self):
        from iris_devtester.containers import iris_container

        for name in ("IRISBase", "_ActualBase", "_IRISMockContainer"):
            assert not hasattr(iris_container, name)
