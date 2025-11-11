"""Contract tests for 'container logs' CLI command."""

import pytest
from click.testing import CliRunner
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestContainerLogsContract:
    """Contract tests for container logs command."""

    def test_logs_command_accepts_container_name(self, cli_runner):
        result = cli_runner.invoke(container_group, ["logs", "my_iris"])
        assert "no such command" not in result.output.lower()

    def test_logs_command_accepts_follow_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["logs", "--follow"])
        assert "no such option" not in result.output.lower()

        result = cli_runner.invoke(container_group, ["logs", "-f"])
        assert "no such option" not in result.output.lower()

    def test_logs_command_accepts_tail_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["logs", "--tail", "50"])
        assert "no such option" not in result.output.lower()

    def test_logs_command_accepts_since_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["logs", "--since", "2025-01-10T14:30:00"])
        assert "no such option" not in result.output.lower()

    def test_logs_command_has_help_text(self, cli_runner):
        result = cli_runner.invoke(container_group, ["logs", "--help"])
        assert result.exit_code == 0
        assert "Display container logs" in result.output
        assert "--follow" in result.output
        assert "--tail" in result.output
        assert "--since" in result.output
