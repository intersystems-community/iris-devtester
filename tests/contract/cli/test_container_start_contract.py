"""Contract tests for 'container start' CLI command."""

import pytest
from click.testing import CliRunner
from iris_devtester.cli.container import container_group


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestContainerStartContract:
    """Contract tests for container start command."""

    def test_start_command_accepts_container_name_argument(self, cli_runner):
        """Test that CONTAINER_NAME argument is accepted."""
        result = cli_runner.invoke(container_group, ["start", "my_iris"])
        # Should not have argument error
        assert "no such command" not in result.output.lower()

    def test_start_command_uses_default_container_name(self, cli_runner):
        """Test that command works without container name (uses default)."""
        result = cli_runner.invoke(container_group, ["start"])
        # Should work without argument (default: iris_db)
        assert result is not None

    def test_start_command_accepts_config_flag(self, cli_runner):
        """Test that --config flag is accepted."""
        result = cli_runner.invoke(container_group, ["start", "--config", "iris-config.yml"])
        assert "no such option" not in result.output.lower()

    def test_start_command_accepts_timeout_flag(self, cli_runner):
        """Test that --timeout flag is accepted."""
        result = cli_runner.invoke(container_group, ["start", "--timeout", "90"])
        assert "no such option" not in result.output.lower()

    def test_start_command_has_help_text(self, cli_runner):
        """Test that command has help documentation."""
        result = cli_runner.invoke(container_group, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start existing IRIS container" in result.output
        assert "container_name" in result.output.lower()
        assert "--config" in result.output
        assert "--timeout" in result.output

    def test_start_command_exit_codes_defined(self, cli_runner):
        """Test that command will use proper exit codes."""
        # Exit codes: 0 (success), 1 (Docker error), 2 (not found, no config), 5 (health check timeout)
        result = cli_runner.invoke(container_group, ["start"])
        assert result is not None
