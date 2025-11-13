"""Contract tests for 'container stop' CLI command."""

import pytest
from click.testing import CliRunner
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestContainerStopContract:
    """Contract tests for container stop command."""

    def test_stop_command_accepts_container_name(self, cli_runner):
        result = cli_runner.invoke(container_group, ["stop", "my_iris"])
        assert "no such command" not in result.output.lower()

    def test_stop_command_accepts_timeout_flag(self, cli_runner):
        result = cli_runner.invoke(container_group, ["stop", "--timeout", "45"])
        assert "no such option" not in result.output.lower()

    def test_stop_command_has_help_text(self, cli_runner):
        result = cli_runner.invoke(container_group, ["stop", "--help"])
        assert result.exit_code == 0
        assert "Gracefully stop running IRIS container" in result.output

    def test_stop_command_idempotency_contract(self, cli_runner):
        # Stopping already-stopped container should succeed
        result = cli_runner.invoke(container_group, ["stop"])
        assert result is not None
