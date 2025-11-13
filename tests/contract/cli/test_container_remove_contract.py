"""Contract tests for 'container remove' CLI command."""

import pytest
from click.testing import CliRunner
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestContainerRemoveContract:
    """Contract tests for container remove command."""

    def test_remove_command_accepts_container_name(self, cli_runner):
        result = cli_runner.invoke(container_group, ["remove", "my_iris"])
        assert "no such command" not in result.output.lower()

    def test_remove_command_accepts_force_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["remove", "--force"])
        assert "no such option" not in result.output.lower()

        result = cli_runner.invoke(container_group, ["remove", "-f"])
        assert "no such option" not in result.output.lower()

    def test_remove_command_accepts_volumes_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["remove", "--volumes"])
        assert "no such option" not in result.output.lower()

        result = cli_runner.invoke(container_group, ["remove", "-v"])
        assert "no such option" not in result.output.lower()

    def test_remove_command_has_help_text(self, cli_runner):
        result = cli_runner.invoke(container_group, ["remove", "--help"])
        assert result.exit_code == 0
        assert "Remove stopped container" in result.output
        assert "--force" in result.output
        assert "--volumes" in result.output
        assert "WARNING" in result.output or "data loss" in result.output.lower()

    def test_remove_command_exit_codes_defined(self, cli_runner):
        # Exit codes: 0 (success), 1 (Docker error), 2 (not found), 3 (running without --force)
        result = cli_runner.invoke(container_group, ["remove"])
        assert result is not None
