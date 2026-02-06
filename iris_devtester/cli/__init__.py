"""CLI commands for iris-devtester."""

import click

from iris_devtester import __version__

from .connection_commands import test_connection
from .container import container_group as container
from .fixture_commands import fixture


@click.group()
@click.version_option(version=__version__, prog_name="iris-devtester")
def main():
    """
    iris-devtester - Python testing toolkit for InterSystems IRIS databases.

    \b
    WHAT THIS TOOL DOES:
      Manages IRIS database containers, fixtures, and connections for testing.
      Designed for CI/CD pipelines, local development, and AI agent automation.

    \b
    CONTAINER EDITIONS:
      community   Full IRIS Community (~3.5GB) - default, all features
      light       Minimal for CI/CD (~580MB) - SQL/DBAPI only, 6x smaller
      enterprise  Licensed IRIS - requires iris.key file

    \b
    QUICK START:
      iris-devtester container up                    # Start community
      iris-devtester container up --edition light    # Start light (CI/CD)
      iris-devtester container list                  # List containers
      iris-devtester test-connection                 # Verify connectivity
      iris-devtester container status                # Check health

    \b
    COMMON WORKFLOWS:
      Local dev:    container up → test-connection → (your tests)
      CI/CD:        container up --edition light → test-connection → pytest
      Fixtures:     fixture load --fixture ./data → (verify data)

    \b
    FOR AI AGENTS:
      All commands support --help for detailed options. Commands return
      structured exit codes (0=success, 1=error, 2=not found, 5=timeout).
      Use 'container list --format json' for machine-readable output.
    """
    pass


# Register subcommands
main.add_command(fixture)
main.add_command(container)
main.add_command(test_connection)


__all__ = ["main", "fixture", "container", "test_connection"]
