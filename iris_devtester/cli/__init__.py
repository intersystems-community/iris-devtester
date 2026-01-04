"""CLI commands for iris-devtester."""

import click
from iris_devtester import __version__
from .fixture_commands import fixture
from .container import container_group as container
from .connection_commands import test_connection


@click.group()
@click.version_option(version=__version__, prog_name="iris-devtester")
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
