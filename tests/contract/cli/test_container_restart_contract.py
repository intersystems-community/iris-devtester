"""Contract tests for 'container restart' CLI command."""

import pytest
from click.testing import CliRunner
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestContainerRestartContract:
    """Contract tests for container restart command."""

    def test_restart_command_accepts_container_name(self, cli_runner):
        result = cli_runner.invoke(container_group, ["restart", "my_iris"])
        assert "no such command" not in result.output.lower()

    def test_restart_command_accepts_timeout_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["restart", "--timeout", "90"])
        assert "no such option" not in result.output.lower()

    def test_restart_command_has_help_text(self, cli_runner):
        result = cli_runner.invoke(container_group, ["restart", "--help"])
        assert result.exit_code == 0
        assert "Restart IRIS container" in result.output
