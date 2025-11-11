"""CLI commands for iris-devtools."""

import click
from .fixture_commands import fixture
from .container import container_group as container


@click.group()
@click.version_option(version="1.1.0", prog_name="iris-devtester")
def main():
    """
    iris-devtester - Battle-tested InterSystems IRIS infrastructure utilities.

    Provides tools for container management, fixture handling, and testing.
    """
    pass


# Register subcommands
main.add_command(fixture)
main.add_command(container)


__all__ = ["main", "fixture", "container"]
