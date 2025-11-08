"""
CLI commands for managing IRIS containers.

This module provides Click command group for container operations:
- reset-password: Reset _SYSTEM password
- enable-callin: Enable CallIn service
- test-connection: Test database connectivity
- status: Show comprehensive container status

Pattern: Follows fixture_commands.py Click structure.
"""

import click

# TODO: Import utilities when implemented in Phase 3.3
# from iris_devtester.utils.password_reset import reset_password
# from iris_devtester.utils.enable_callin import enable_callin_service
# from iris_devtester.utils.test_connection import test_connection
# from iris_devtester.utils.container_status import get_container_status


@click.group()
def container():
    """
    Manage IRIS containers.

    Commands for working with existing IRIS containers started via
    docker-compose, Docker CLI, or other orchestration tools.

    Complements IRISContainer class which manages container lifecycle.
    """
    pass


@container.command("reset-password")
@click.argument("container_name")
@click.option("--user", default="_SYSTEM", help="Username to reset (default: _SYSTEM)")
@click.option("--password", default="SYS", help="New password (default: SYS)")
def reset_password_command(container_name: str, user: str, password: str):
    """
    Reset password for IRIS user.

    Examples:
        iris-devtester container reset-password iris-fhir
        iris-devtester container reset-password iris-fhir --user _SYSTEM --password ISCDEMO
    """
    # TODO: Implement in Phase 3.3 (T017)
    click.echo("Command stub - to be implemented in Phase 3.3")
    raise NotImplementedError("To be implemented in Phase 3.3 (T017)")


@container.command("enable-callin")
@click.argument("container_name")
def enable_callin_command(container_name: str):
    """
    Enable CallIn service for DBAPI connections.

    CallIn service is required for:
    - DBAPI connections (intersystems-irispython)
    - Embedded Python (iris module)
    - Python callouts from ObjectScript

    Examples:
        iris-devtester container enable-callin iris-fhir
    """
    # TODO: Implement in Phase 3.3 (T017)
    click.echo("Command stub - to be implemented in Phase 3.3")
    raise NotImplementedError("To be implemented in Phase 3.3 (T017)")


@container.command("test-connection")
@click.argument("container_name")
@click.option("--namespace", default="USER", help="Namespace to test (default: USER)")
def test_connection_command(container_name: str, namespace: str):
    """
    Test connection to IRIS container.

    Validates database connectivity and reports connection status.

    Examples:
        iris-devtester container test-connection iris-fhir
        iris-devtester container test-connection iris-fhir --namespace FHIR
    """
    # TODO: Implement in Phase 3.3 (T017)
    click.echo("Command stub - to be implemented in Phase 3.3")
    raise NotImplementedError("To be implemented in Phase 3.3 (T017)")


@container.command("status")
@click.argument("container_name")
def status_command(container_name: str):
    """
    Show comprehensive container status.

    Displays:
    - Container running status
    - Health check status
    - CallIn service status
    - Password expiration status
    - Connection test result

    Examples:
        iris-devtester container status iris-fhir
    """
    # TODO: Implement in Phase 3.3 (T017)
    click.echo("Command stub - to be implemented in Phase 3.3")
    raise NotImplementedError("To be implemented in Phase 3.3 (T017)")
