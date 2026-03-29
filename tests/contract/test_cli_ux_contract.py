import sys
import types

import pytest
from click.testing import CliRunner

from iris_devtester.cli.connection_commands import test_connection
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestFeature030CliUxContract:
    def test_test_connection_detects_password_change_required(self, cli_runner, monkeypatch):
        fake_dbapi = types.ModuleType("_DBAPI")

        def fake_connect(*args, **kwargs):
            raise Exception("1")

        fake_dbapi.connect = fake_connect
        monkeypatch.setitem(sys.modules, "intersystems_iris", types.ModuleType("intersystems_iris"))
        monkeypatch.setitem(
            sys.modules,
            "intersystems_iris.dbapi",
            types.ModuleType("intersystems_iris.dbapi"),
        )
        monkeypatch.setitem(sys.modules, "intersystems_iris.dbapi._DBAPI", fake_dbapi)

        result = cli_runner.invoke(
            test_connection,
            ["--host", "127.0.0.1", "--port", "1972", "--username", "_SYSTEM", "--password", "SYS"],
        )

        assert result.exit_code == 1
        assert "Password change required" in result.output

    def test_reset_password_timeout_option_exists_and_accepts_integer(self, cli_runner):
        help_result = cli_runner.invoke(container_group, ["reset-password", "--help"])
        assert help_result.exit_code == 0
        assert "--timeout" in help_result.output

        result = cli_runner.invoke(
            container_group, ["reset-password", "iris_db", "--timeout", "15"]
        )
        assert "no such option" not in result.output.lower()
        assert "Invalid value" not in result.output

    def test_container_up_port_option_exists_and_is_mutually_exclusive_with_auto_port(
        self, cli_runner
    ):
        help_result = cli_runner.invoke(container_group, ["up", "--help"])
        assert help_result.exit_code == 0
        assert "--port" in help_result.output

        result = cli_runner.invoke(container_group, ["up", "--port", "11972", "--auto-port"])
        assert result.exit_code != 0
        assert "Cannot use --port and --auto-port together" in result.output

    def test_container_exec_command_is_registered_and_exposes_objectscript_option(self, cli_runner):
        result = cli_runner.invoke(container_group, ["exec", "--help"])

        assert result.exit_code == 0
        assert "--objectscript" in result.output
        assert "--namespace" in result.output
        assert "--timeout" in result.output

    def test_test_connection_displays_password_line_masked_by_default(self, cli_runner):
        result = cli_runner.invoke(
            test_connection,
            [
                "--host",
                "127.0.0.1",
                "--port",
                "1972",
                "--username",
                "_SYSTEM",
                "--password",
                "SYS",
            ],
        )

        assert "Password:" in result.output
        assert "Password: S**" in result.output

    def test_container_test_connection_prints_deprecation_warning(self, cli_runner):
        result = cli_runner.invoke(container_group, ["test-connection", "iris_db"])

        assert "DEPRECATED" in result.output
        assert "idt test-connection --container" in result.output
