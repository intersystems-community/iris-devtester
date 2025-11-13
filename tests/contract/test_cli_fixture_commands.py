"""Contract tests for CLI fixture commands.

Validates that all CLI commands defined in contracts/cli-commands.yaml exist
with correct signatures and options.

These tests verify:
1. All 5 CLI commands exist (create, load, validate, list, info)
2. Required options are present
3. Optional flags are supported
4. Commands are properly integrated with click framework
5. Help text is available

CRITICAL: These are contract tests - they validate API signatures,
not functionality. They should pass immediately after CLI implementation.
"""


import pytest

pytestmark = pytest.mark.contract
from click.testing import CliRunner
from iris_devtester.cli.fixture_commands import fixture, create, load, validate, list, info


class TestFixtureGroupCommand:
    """Test the main 'fixture' command group."""

    def test_fixture_group_exists(self):
        """Fixture group command should exist."""
        assert fixture is not None

    def test_fixture_group_is_click_group(self):
        """Fixture command should be a Click group."""
        assert hasattr(fixture, 'commands')

    def test_fixture_group_has_help(self):
        """Fixture group should have help text."""
        runner = CliRunner()
        result = runner.invoke(fixture, ['--help'])
        assert result.exit_code == 0
        assert 'Manage IRIS .DAT fixtures' in result.output

    def test_fixture_group_has_all_commands(self):
        """Fixture group should have all 5 commands."""
        assert 'create' in fixture.commands
        assert 'load' in fixture.commands
        assert 'validate' in fixture.commands
        assert 'list' in fixture.commands
        assert 'info' in fixture.commands


class TestCreateCommand:
    """Test 'fixture create' command contract."""

    def test_create_command_exists(self):
        """Create command should exist."""
        assert create is not None

    def test_create_has_required_options(self):
        """Create command should have all required options."""
        runner = CliRunner()
        result = runner.invoke(create, ['--help'])
        assert result.exit_code == 0
        assert '--name' in result.output
        assert '--namespace' in result.output
        assert '--output' in result.output

    def test_create_has_optional_options(self):
        """Create command should have optional description and version."""
        runner = CliRunner()
        result = runner.invoke(create, ['--help'])
        assert result.exit_code == 0
        assert '--description' in result.output
        assert '--version' in result.output

    def test_create_has_verbose_flag(self):
        """Create command should have --verbose flag."""
        runner = CliRunner()
        result = runner.invoke(create, ['--help'])
        assert result.exit_code == 0
        assert '--verbose' in result.output

    def test_create_requires_name(self):
        """Create command should fail without --name."""
        runner = CliRunner()
        result = runner.invoke(create, ['--namespace', 'USER', '--output', '/tmp'])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output

    def test_create_requires_namespace(self):
        """Create command should fail without --namespace."""
        runner = CliRunner()
        result = runner.invoke(create, ['--name', 'test', '--output', '/tmp'])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output

    def test_create_requires_output(self):
        """Create command should fail without --output."""
        runner = CliRunner()
        result = runner.invoke(create, ['--name', 'test', '--namespace', 'USER'])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output


class TestLoadCommand:
    """Test 'fixture load' command contract."""

    def test_load_command_exists(self):
        """Load command should exist."""
        assert load is not None

    def test_load_has_required_options(self):
        """Load command should have --fixture option."""
        runner = CliRunner()
        result = runner.invoke(load, ['--help'])
        assert result.exit_code == 0
        assert '--fixture' in result.output

    def test_load_has_optional_namespace(self):
        """Load command should have optional --namespace."""
        runner = CliRunner()
        result = runner.invoke(load, ['--help'])
        assert result.exit_code == 0
        assert '--namespace' in result.output

    def test_load_has_no_validate_flag(self):
        """Load command should have --no-validate flag."""
        runner = CliRunner()
        result = runner.invoke(load, ['--help'])
        assert result.exit_code == 0
        assert '--no-validate' in result.output

    def test_load_has_verbose_flag(self):
        """Load command should have --verbose flag."""
        runner = CliRunner()
        result = runner.invoke(load, ['--help'])
        assert result.exit_code == 0
        assert '--verbose' in result.output

    def test_load_requires_fixture(self):
        """Load command should fail without --fixture."""
        runner = CliRunner()
        result = runner.invoke(load, [])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output


class TestValidateCommand:
    """Test 'fixture validate' command contract."""

    def test_validate_command_exists(self):
        """Validate command should exist."""
        assert validate is not None

    def test_validate_has_required_options(self):
        """Validate command should have --fixture option."""
        runner = CliRunner()
        result = runner.invoke(validate, ['--help'])
        assert result.exit_code == 0
        assert '--fixture' in result.output

    def test_validate_has_no_checksums_flag(self):
        """Validate command should have --no-checksums flag."""
        runner = CliRunner()
        result = runner.invoke(validate, ['--help'])
        assert result.exit_code == 0
        assert '--no-checksums' in result.output

    def test_validate_has_recalc_flag(self):
        """Validate command should have --recalc flag."""
        runner = CliRunner()
        result = runner.invoke(validate, ['--help'])
        assert result.exit_code == 0
        assert '--recalc' in result.output

    def test_validate_has_verbose_flag(self):
        """Validate command should have --verbose flag."""
        runner = CliRunner()
        result = runner.invoke(validate, ['--help'])
        assert result.exit_code == 0
        assert '--verbose' in result.output

    def test_validate_requires_fixture(self):
        """Validate command should fail without --fixture."""
        runner = CliRunner()
        result = runner.invoke(validate, [])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output


class TestListCommand:
    """Test 'fixture list' command contract."""

    def test_list_command_exists(self):
        """List command should exist."""
        assert list is not None

    def test_list_has_path_argument(self):
        """List command should accept path argument."""
        runner = CliRunner()
        result = runner.invoke(list, ['--help'])
        assert result.exit_code == 0
        # Path is a positional argument with default
        assert 'PATH' in result.output or 'path' in result.output or 'fixtures' in result.output

    def test_list_has_verbose_flag(self):
        """List command should have --verbose flag."""
        runner = CliRunner()
        result = runner.invoke(list, ['--help'])
        assert result.exit_code == 0
        assert '--verbose' in result.output

    def test_list_path_is_optional(self):
        """List command should work without path (uses default)."""
        runner = CliRunner()
        # Should not fail for missing required argument
        # Will fail because directory doesn't exist, but not for missing arg
        result = runner.invoke(list, [])
        # Exit code may be 0 or 1 depending on directory existence
        # Just verify it doesn't complain about missing required argument
        assert 'Missing argument' not in result.output


class TestInfoCommand:
    """Test 'fixture info' command contract."""

    def test_info_command_exists(self):
        """Info command should exist."""
        assert info is not None

    def test_info_has_required_options(self):
        """Info command should have --fixture option."""
        runner = CliRunner()
        result = runner.invoke(info, ['--help'])
        assert result.exit_code == 0
        assert '--fixture' in result.output

    def test_info_has_json_flag(self):
        """Info command should have --json flag."""
        runner = CliRunner()
        result = runner.invoke(info, ['--help'])
        assert result.exit_code == 0
        assert '--json' in result.output

    def test_info_requires_fixture(self):
        """Info command should fail without --fixture."""
        runner = CliRunner()
        result = runner.invoke(info, [])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output


class TestCLIIntegration:
    """Test CLI command integration."""

    def test_all_commands_accessible_from_fixture_group(self):
        """All commands should be accessible from fixture group."""
        assert fixture.commands['create'] == create
        assert fixture.commands['load'] == load
        assert fixture.commands['validate'] == validate
        assert fixture.commands['list'] == list
        assert fixture.commands['info'] == info

    def test_fixture_group_help_lists_all_commands(self):
        """Fixture group help should list all commands."""
        runner = CliRunner()
        result = runner.invoke(fixture, ['--help'])
        assert result.exit_code == 0
        assert 'create' in result.output
        assert 'load' in result.output
        assert 'validate' in result.output
        assert 'list' in result.output
        assert 'info' in result.output

    def test_all_commands_have_help_text(self):
        """All commands should have help text."""
        runner = CliRunner()

        for cmd_name in ['create', 'load', 'validate', 'list', 'info']:
            result = runner.invoke(fixture, [cmd_name, '--help'])
            assert result.exit_code == 0, f"{cmd_name} --help failed"
            assert len(result.output) > 0, f"{cmd_name} has no help text"


class TestCLIErrorHandling:
    """Test CLI error handling contract."""

    def test_create_handles_file_exists_error(self):
        """Create should handle FileExistsError gracefully."""
        # This is a contract test - we just verify the command runs
        # without throwing unhandled exceptions for expected error cases
        runner = CliRunner()
        # Missing args will cause error, but should be handled
        result = runner.invoke(create, ['--name', 'test', '--namespace', 'USER', '--output', '/tmp/nonexistent'])
        # Should exit with error code, not crash
        assert result.exit_code != 0

    def test_load_handles_file_not_found(self):
        """Load should handle FileNotFoundError gracefully."""
        runner = CliRunner()
        result = runner.invoke(load, ['--fixture', '/nonexistent/path'])
        # Should exit with error code, not crash
        assert result.exit_code != 0

    def test_validate_handles_file_not_found(self):
        """Validate should handle FileNotFoundError gracefully."""
        runner = CliRunner()
        result = runner.invoke(validate, ['--fixture', '/nonexistent/path'])
        # Should exit with error code, not crash
        assert result.exit_code != 0

    def test_list_handles_missing_directory(self):
        """List should handle missing directory gracefully."""
        runner = CliRunner()
        result = runner.invoke(list, ['/nonexistent/directory'])
        # Should exit with error code, not crash
        assert result.exit_code != 0

    def test_info_handles_missing_fixture(self):
        """Info should handle missing fixture gracefully."""
        runner = CliRunner()
        result = runner.invoke(info, ['--fixture', '/nonexistent/path'])
        # Should exit with error code, not crash
        assert result.exit_code != 0


# Test count verification
def test_cli_contract_test_count():
    """Verify we have comprehensive CLI contract tests."""
    # We should have at least 39 tests covering all CLI aspects
    import sys
    module = sys.modules[__name__]
    test_classes = [
        TestFixtureGroupCommand,
        TestCreateCommand,
        TestLoadCommand,
        TestValidateCommand,
        TestListCommand,
        TestInfoCommand,
        TestCLIIntegration,
        TestCLIErrorHandling,
    ]

    total_tests = 0
    for test_class in test_classes:
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        total_tests += len(test_methods)

    assert total_tests >= 39, f"Expected at least 39 CLI contract tests, found {total_tests}"
