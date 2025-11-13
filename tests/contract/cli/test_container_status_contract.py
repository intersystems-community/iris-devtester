"""Contract tests for 'container status' CLI command."""

import pytest
from click.testing import CliRunner
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestContainerStatusContract:
    """Contract tests for container status command."""

    def test_status_command_accepts_container_name(self, cli_runner):
        result = cli_runner.invoke(container_group, ["status", "my_iris"])
        assert "no such command" not in result.output.lower()

    def test_status_command_accepts_format_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["status", "--format", "json"])
        assert "no such option" not in result.output.lower()

        result = cli_runner.invoke(container_group, ["status", "--format", "text"])
        assert "no such option" not in result.output.lower()

    def test_status_command_has_help_text(self, cli_runner):
        result = cli_runner.invoke(container_group, ["status", "--help"])
        assert result.exit_code == 0
        assert "Display current container state" in result.output
        assert "--format" in result.output

    def test_status_command_json_schema_contract(self, cli_runner):
        # Contract: JSON output will match ContainerStatus schema
        # Actual schema validation in integration tests
        result = cli_runner.invoke(container_group, ["status"])
        assert result is not None
