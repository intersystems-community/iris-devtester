"""Pieces shared by ``idt image load`` and ``idt image build``."""

import dataclasses
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

import click

from iris_devtester.cli.image import runner
from iris_devtester.cli.image.collision import resolve_name_collision
from iris_devtester.cli.image.errors import (
    EXIT_FAILURE,
    EXIT_TIMEOUT,
    ImageCommandError,
    health_timeout_error,
    render_error,
)
from iris_devtester.cli.image.options import DEFAULT_PASSWORD, StartOptions, build_labels
from iris_devtester.utils import progress


def derive_name_from_tarball(tarball_path: Path) -> str:
    stem = tarball_path.stem
    if stem.endswith(".tar"):
        stem = stem[:-4]
    name = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    if len(name) > 40:
        name = name[:40].rstrip("-")
    return name


def _timeout_error(exc: BaseException) -> ImageCommandError:
    """Generic exit-5 conversion for any timeout that reached the wrapper."""
    if isinstance(exc, runner.PhaseTimeout):
        what = f"The {exc.phase} phase timed out after {exc.limit}s (elapsed {exc.elapsed:.0f}s)."
    elif isinstance(exc, subprocess.TimeoutExpired):
        what = f"Command timed out after {exc.timeout}s: {' '.join(map(str, exc.cmd))}"
    else:
        what = str(exc) or "An operation timed out."
    return ImageCommandError(
        what=what,
        why="The operation did not finish in time, so the result is unknown.",
        fix="Check 'docker ps -a' and 'docker images', then retry with a larger timeout.",
        exit_code=EXIT_TIMEOUT,
        title="Timed out",
    )


def _fail(err: ImageCommandError, secrets: Iterable[Optional[str]]) -> None:
    click.echo(render_error(err, secrets=secrets), err=True)
    raise click.exceptions.Exit(err.exit_code)


def run_image_command(func: Callable[[], None], secrets: Iterable[Optional[str]] = ()) -> None:
    """Run ``func`` and render any failure exactly once with the right exit code."""
    secrets = list(secrets)
    try:
        func()
    except (click.exceptions.Exit, click.ClickException, click.Abort):
        raise
    except (SystemExit, KeyboardInterrupt):
        raise
    except ImageCommandError as exc:
        _fail(exc, secrets)
    except (TimeoutError, subprocess.TimeoutExpired) as exc:
        _fail(_timeout_error(exc), secrets)
    except Exception as exc:  # noqa: BLE001 - last-resort catch-all
        _fail(
            ImageCommandError(
                what=f"Unexpected error: {exc}",
                why="This is not a failure idt knows how to explain.",
                fix=(
                    "Re-run with --keep-build-dir (build) to keep the build context for "
                    "inspection, and file an issue with the command and this message."
                ),
                exit_code=EXIT_FAILURE,
            ),
            secrets,
        )


def print_manual_start_hint(image_ref: str, options: StartOptions) -> None:
    """Tell the user how to start the container themselves (``--no-start``)."""
    click.echo("\nTo start manually:")
    click.echo("  " + " ".join(runner.docker_run_argv(image_ref, options)))


def _password_step_failed(
    step: str, options: StartOptions, detail: str, command: str
) -> ImageCommandError:
    return ImageCommandError(
        what=f"Could not {step} in container '{options.name}': {detail}",
        why=(
            "The container is running but _SYSTEM does not have the password you asked for, "
            "so connections using --password will be refused."
        ),
        fix=(
            f"The container was kept so you can inspect it (docker logs {options.name}).\n"
            f"Remove it with:  docker rm -f {options.name}\n"
            f"Then re-run the same 'idt image {command}' command."
        ),
        exit_code=EXIT_FAILURE,
        title="Password setup failed",
    )


def create_and_start_container(
    image_ref: str, options: StartOptions, command: str = "load"
) -> None:
    """Start a container from ``image_ref``, wait healthy, unexpire, reset password."""
    import docker

    from iris_devtester.utils import health_checks
    from iris_devtester.utils import password as pw

    client = docker.from_env()

    resolve_name_collision(client, options.name, options.replace)
    options = dataclasses.replace(options, labels=build_labels(image_ref))

    click.echo(f"⏳ Starting container '{options.name}' ...")
    result = runner.run_docker_run(image_ref, options)
    if result.returncode != 0:
        raise ImageCommandError(
            what=f"docker run failed (exit {result.returncode}): {result.stderr.strip()}",
            why="No container was started, so there is nothing to connect to.",
            fix=(
                "Check which ports are in use with 'docker ps', then choose free ones with "
                "--port and --web-port, or pick another container with --name."
            ),
            exit_code=EXIT_FAILURE,
            title="Could not start the container",
        )
    click.echo(f"✓ Container '{options.name}' started")

    click.echo("⏳ Waiting for IRIS to become healthy ...")
    container_obj = client.containers.get(options.name)

    health_start = time.monotonic()
    try:
        health_checks.wait_for_healthy(
            container_obj,
            timeout=options.health_timeout,
            progress_callback=lambda m: click.echo(f"  {m}"),
        )
    except TimeoutError as e:
        raise health_timeout_error(
            options.name, options.health_timeout, time.monotonic() - health_start, str(e)
        ) from e
    except RuntimeError as e:
        raise ImageCommandError(
            what=f"Container '{options.name}' did not become healthy: {e}",
            why="IRIS is not running, so there is nothing to connect to. The container was kept.",
            fix=(
                f"Inspect it with: docker logs {options.name}\n"
                f"Remove it with:  docker rm -f {options.name}"
            ),
            exit_code=EXIT_FAILURE,
            title="Container failed to become healthy",
        ) from e
    click.echo("✓ IRIS is healthy")

    is_default = options.password == DEFAULT_PASSWORD

    if not options.no_unexpire:
        click.echo("⏳ Unexpiring all passwords ...")
        failure: Optional[str] = None
        try:
            ok, msg = pw.unexpire_all_passwords(options.name)
            if not ok:
                failure = str(msg)
        except Exception as e:
            failure = str(e)
        if failure is None:
            click.echo("✓ Passwords unexpired")
        elif is_default:
            click.secho(f"  ⚠ Unexpire failed (non-fatal): {failure}", fg="yellow")
        else:
            raise _password_step_failed("unexpire passwords", options, failure, command)

    click.echo("⏳ Setting _SYSTEM password ...")
    failure = None
    try:
        ok, msg = pw.reset_password(
            container_name=options.name,
            username="_SYSTEM",
            new_password=options.password,
            hostname="localhost",
            port=options.superserver_port,
            verify=False,
        )
        if not ok:
            failure = str(msg)
    except Exception as e:
        failure = str(e)
    if failure is None:
        click.echo("✓ Password set")
    elif is_default:
        click.secho(
            f"  ⚠ Password reset failed (non-fatal, default password): {failure}", fg="yellow"
        )
    else:
        raise _password_step_failed("set the _SYSTEM password", options, failure, command)

    click.echo(f"\n✓ Container '{options.name}' is ready")
    progress.print_connection_info(
        container_name=options.name,
        superserver_port=options.superserver_port,
        webserver_port=options.web_port or 0,
        namespace="USER",
        password=options.password,
        show_password=options.show_password,
    )
