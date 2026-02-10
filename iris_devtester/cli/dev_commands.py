"""
CLI commands for managing the persistent IRIS Dev Instance.
"""

import click
import json
import logging
from typing import Optional

from iris_devtester.containers.dev_instance import (
    DevInstanceManager,
    DEV_INSTANCE_NAME,
    DEV_VOLUME_NAME,
    get_project_namespace
)
from iris_devtester.utils import progress

logger = logging.getLogger(__name__)


@click.group(name="dev")
def dev_group():
    """
    Manage the persistent IRIS Dev Instance (Warm Start).
    
    Provides a background IRIS container that stays running across projects
    to enable instant, isolated database connectivity.
    """
    pass


@dev_group.command(name="up")
@click.option("--image", help="IRIS Docker image to use")
@click.option("--force", is_flag=True, help="Force restart even if running")
def up(image: Optional[str], force: bool):
    """Start the background dev engine."""
    manager = DevInstanceManager()
    
    if manager.is_running() and not force:
        click.echo(f"✓ Dev instance '{DEV_INSTANCE_NAME}' is already running")
        return

    click.echo(f"⏳ Starting dev engine '{DEV_INSTANCE_NAME}'...")
    try:
        manager.ensure_ready(image=image, force=force)
        click.echo(f"✓ Dev engine is up and ready")
    except Exception as e:
        progress.print_error(f"Failed to start dev engine: {e}")
        raise click.Abort()


@dev_group.command(name="down")
@click.option("--volumes", is_flag=True, help="Also remove the persistent volume (data loss!)")
def down(volumes: bool):
    """Stop and remove the dev engine."""
    manager = DevInstanceManager()
    
    if volumes:
        click.echo("⚠️  WARNING: This will permanently delete all dev instance data!")
        click.confirm("Are you sure you want to continue?", abort=True)

    click.echo(f"⚡ Stopping dev engine '{DEV_INSTANCE_NAME}'...")
    manager.remove(remove_volumes=volumes)
    click.echo(f"✓ Dev engine removed")


@dev_group.command(name="status")
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def status(format: str):
    """Show the status of the engine and the current project's isolation."""
    manager = DevInstanceManager()
    instance = manager.get_instance()
    
    project_ns = get_project_namespace()
    
    status_data = {
        "engine_name": DEV_INSTANCE_NAME,
        "status": instance.status if instance else "not_created",
        "volume": DEV_VOLUME_NAME,
        "project_namespace": project_ns,
    }
    
    if format == "json":
        click.echo(json.dumps(status_data, indent=2))
    else:
        click.echo(f"Engine: {DEV_INSTANCE_NAME}")
        click.echo(f"Status: {status_data['status']}")
        click.echo(f"Volume: {DEV_VOLUME_NAME}")
        click.echo(f"Project Namespace: {project_ns}")


@dev_group.command(name="logs")
@click.option("--follow", "-f", is_flag=True, help="Stream logs continuously")
@click.option("--tail", type=int, default=100, help="Number of lines to show")
def logs(follow: bool, tail: int):
    """Display engine logs."""
    manager = DevInstanceManager()
    instance = manager.get_instance()
    
    if not instance:
        progress.print_error(f"Dev instance '{DEV_INSTANCE_NAME}' not found")
        return

    try:
        if follow:
            for line in instance.logs(stream=True, tail=tail, timestamps=True):
                click.echo(line.decode("utf-8", errors="ignore"), nl=False)
        else:
            click.echo(instance.logs(tail=tail, timestamps=True).decode("utf-8", errors="ignore"))
    except KeyboardInterrupt:
        pass
