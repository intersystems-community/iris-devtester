"""CLI commands for iris-devtools."""

import click
from .fixture_commands import fixture
from .container import container_group as container
from .connection_commands import test_connection


@click.group()
@click.version_option(version="1.2.0", prog_name="iris-devtester")
def main():
    """
    iris-devtester - Battle-tested InterSystems IRIS infrastructure utilities.

    Provides tools for container management, fixture handling, and testing.
    """
    pass


# Register subcommands
main.add_command(fixture)
main.add_command(container)
main.add_command(test_connection)


__all__ = ["main", "fixture", "container", "test_connection"]
