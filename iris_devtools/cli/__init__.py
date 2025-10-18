"""CLI commands for iris-devtools."""

import click
from .fixture_commands import fixture


@click.group()
@click.version_option(version="1.0.0", prog_name="iris-devtools")
def main():
    """
    iris-devtools - Battle-tested InterSystems IRIS infrastructure utilities.

    Provides tools for container management, fixture handling, and testing.
    """
    pass


# Register subcommands
main.add_command(fixture)


__all__ = ["main", "fixture"]
