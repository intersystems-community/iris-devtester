"""Container-name collision handling.

Only containers that carry idt's creation label may ever be removed, and a
container that is running or holds data additionally needs ``--replace``.
"""

from typing import Any, Callable

import click

from iris_devtester.cli.image.errors import EXIT_BAD_INPUT, ImageCommandError
from iris_devtester.cli.image.options import (
    LABEL_CREATED_BY,
    LABEL_CREATED_BY_VALUE,
    LABEL_IMAGE,
)

# Labelled containers in these states never ran, so there is nothing to lose.
_DISPOSABLE = {"created", "dead"}
# Statuses whose refusal reason is "it is running" (a process exists); the rest "holds data".
_RUNNING_LIKE = {"running", "restarting", "paused"}


def _image_of(container: Any) -> str:
    try:
        tags = container.image.tags
        if tags:
            return str(tags[0])
    except Exception:  # noqa: BLE001 - image may be gone
        pass
    try:
        return str(container.labels.get(LABEL_IMAGE) or "unknown image")
    except Exception:  # noqa: BLE001
        return "unknown image"


def resolve_name_collision(
    client: Any, name: str, replace: bool, echo: Callable[[str], None] = click.echo
) -> None:
    """Make ``name`` available or refuse with an :class:`ImageCommandError` (exit 2)."""
    import docker

    try:
        existing = client.containers.get(name)
    except docker.errors.NotFound:
        return
    existing.reload()
    status = existing.status
    labelled = (existing.labels or {}).get(LABEL_CREATED_BY) == LABEL_CREATED_BY_VALUE

    if not labelled:
        raise ImageCommandError(
            what=f"Container '{name}' already exists ({status}) and " "it was not created by idt.",
            why="idt only removes containers it created itself, even with --replace, so your "
            "own containers and their data are never touched.",
            fix=f"Remove it yourself with: docker rm -f {name}\n"
            "Or choose another name with --name.",
            exit_code=EXIT_BAD_INPUT,
            title="Container name already in use",
        )

    if status in _DISPOSABLE:
        echo(f"  → Removing stale idt container '{name}' ({status}, {_image_of(existing)})")
        existing.remove(force=True, v=False)
        return

    if not replace:
        reason = "it is running" if status in _RUNNING_LIKE else "it holds data"
        raise ImageCommandError(
            what=f"Container '{name}' already exists ({status}): {reason}.",
            why="Replacing it would stop it and discard its writable layer.",
            fix=(
                f"Re-run with --replace to remove and recreate it,\n"
                f"or remove it yourself with: docker rm -f {name}\n"
                f"or choose another name with --name."
            ),
            exit_code=EXIT_BAD_INPUT,
            title="Container name already in use",
        )

    echo(f"  → Replacing idt container '{name}' (status: {status}, image: {_image_of(existing)})")
    existing.remove(force=True, v=False)
