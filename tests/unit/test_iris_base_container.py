"""Unit tests for the in-house IRIS testcontainer base.

iris-devtester used to subclass ``testcontainers.iris.IRISContainer`` from the
CaretDev ``testcontainers-iris`` package, which hard-requires ``sqlalchemy-iris``.
sqlalchemy-iris ships its own ``iris/__init__.py`` that collides with
intersystems-irispython under some resolvers (uv), turning ``iris.connect`` into
a stub. These tests pin the absorbed behavior and guard against the dependency
creeping back in.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.containers._base import IRISDockerContainer

REPO_ROOT = Path(__file__).resolve().parents[2]


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

        assert iris_container.HAS_TESTCONTAINERS is True
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
        assert c.username == "test"
        assert c.password == "test"
        assert c.namespace == "USER"
        assert c.driver == "iris"
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


class TestConnect:
    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_user_namespace_skips_create_database(self, mock_wait):
        c = IRISDockerContainer(username="u", password="p")
        c.exec = MagicMock()
        c._connect()
        mock_wait.assert_called_once_with(c, predicate="Enabling logons")
        assert c.exec.call_count == 1
        cmd = c.exec.call_args[0][0]
        assert "Security.Users).Create(\"u\",\"%ALL\",\"p\")" in cmd
        assert "-U %SYS" in cmd

    @patch("iris_devtester.containers._base.wait_for_logs")
    def test_custom_namespace_creates_database(self, mock_wait):
        c = IRISDockerContainer(namespace="MYNS")
        c.exec = MagicMock()
        c._connect()
        cmds = [call[0][0] for call in c.exec.call_args_list]
        assert len(cmds) == 2
        assert 'CREATE DATABASE MYNS' in cmds[0]
        assert "%SQL.Statement).%ExecDirect" in cmds[0]


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

    def test_url_host_override(self):
        c = IRISDockerContainer(username="u", password="p")
        c._container = MagicMock()
        c.get_exposed_port = MagicMock(return_value=1)
        assert c.get_connection_url(host="x") == "iris://u:p@x:1/USER"
