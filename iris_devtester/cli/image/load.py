"""``idt image load`` -- load a docker-save tarball and start a container."""

import tarfile
from pathlib import Path
from typing import Optional

import click

from iris_devtester.cli.image import image_group, runner
from iris_devtester.cli.image.common import (
    create_and_start_container,
    derive_name_from_tarball,
    print_manual_start_hint,
    run_image_command,
)
from iris_devtester.cli.image.errors import (
    EXIT_BAD_INPUT,
    EXIT_FAILURE,
    ImageCommandError,
    load_timeout_error,
)
from iris_devtester.cli.image.options import HEALTH_TIMEOUT, LOAD_TIMEOUT, StartOptions


def _is_installer_kit(tarball_path: Path) -> bool:
    """True if the tarball is an ISC installer kit (has irisinstall), not a docker save."""
    try:
        with tarfile.open(tarball_path, "r:gz") as tf:
            names = tf.getnames()
        return any(n.endswith("/irisinstall") or n == "irisinstall" for n in names)
    except Exception:
        return False


def _do_load(
    tarball,
    name,
    superserver_port,
    web_port,
    password,
    show_password,
    replace,
    no_start,
    no_unexpire,
    timeout,
    load_timeout,
):
    tarball_path = Path(tarball)
    web_port_val: Optional[int] = web_port if web_port and web_port > 0 else None

    if _is_installer_kit(tarball_path):
        raise ImageCommandError(
            what=f"{tarball_path.name} is an ISC installer kit (contains irisinstall), "
            "not a docker-save archive.",
            why="'docker load' only accepts docker-save archives, so it would fail on this file.",
            fix=f"idt image build {tarball_path.name} --tag <image:tag> --name <container>",
            exit_code=EXIT_BAD_INPUT,
            title="Wrong kind of tarball",
        )

    click.echo(f"⏳ Loading image from {tarball_path.name} ...")
    try:
        result = runner.run_docker_load(str(tarball_path), timeout=load_timeout)
    except runner.LoadTimeout as exc:
        raise load_timeout_error(exc.limit, exc.elapsed) from exc
    if result.returncode != 0:
        raise ImageCommandError(
            what=f"docker load failed (exit {result.returncode}): {result.stderr.strip()}",
            why="The image was not imported, so no container can be started from it.",
            fix=(
                "Check Docker is running ('docker info'), the archive is intact "
                f"('tar -tzf {tarball_path.name} | head') and there is free disk space "
                "('docker system df')."
            ),
            exit_code=EXIT_FAILURE,
            title="Image load failed",
        )

    image_ref = None
    for line in result.stdout.splitlines():
        if line.startswith("Loaded image:") or line.startswith("Loaded image ID:"):
            image_ref = line.split(":", 1)[1].strip()
            break
    if not image_ref:
        raise ImageCommandError(
            what="docker load succeeded but produced no image tag. "
            f"Output: {result.stdout.strip()}",
            why="Without an image reference idt cannot start a container from the archive.",
            fix="Check the archive with 'docker load -i <file>' and 'docker images'; "
            "re-save the image with a tag ('docker save repo:tag -o file.tar').",
            exit_code=EXIT_FAILURE,
            title="No image tag in archive",
        )
    click.echo(f"✓ Image loaded: {image_ref}")

    container_name = name or derive_name_from_tarball(tarball_path)
    options = StartOptions(
        name=container_name,
        superserver_port=superserver_port,
        web_port=web_port_val,
        password=password,
        show_password=show_password,
        replace=replace,
        no_unexpire=no_unexpire,
        health_timeout=timeout,
    )

    if no_start:
        click.echo("  → --no-start: skipping container creation")
        print_manual_start_hint(image_ref, options)
        return

    click.echo(f"  → Container name: {container_name}")
    click.echo(f"  → SuperServer port: {superserver_port}")
    if web_port_val:
        click.echo(f"  → Web port: {web_port_val}")
    create_and_start_container(image_ref, options, command="load")


@image_group.command(name="load")
@click.argument("tarball", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--name",
    type=str,
    default=None,
    help="Container name (default: derived from tarball filename)",
)
@click.option(
    "--port",
    "superserver_port",
    type=int,
    default=1972,
    show_default=True,
    help="Host port mapped to IRIS SuperServer (1972)",
)
@click.option(
    "--web-port",
    type=int,
    default=52773,
    show_default=True,
    help="Host port mapped to IRIS Web gateway (52773). Pass 0 to skip.",
)
@click.option(
    "--password", default="SYS", show_default=True, help="Password to set on _SYSTEM after start"
)
@click.option(
    "--replace",
    is_flag=True,
    default=False,
    help="Replace an existing container of the same name if idt created it "
    "(containers idt did not create are never removed)",
)
@click.option(
    "--show-password",
    is_flag=True,
    default=False,
    help="Print the real password in the connection summary (masked by default)",
)
@click.option(
    "--no-start",
    is_flag=True,
    default=False,
    help="Load image only; do not create or start a container",
)
@click.option(
    "--no-unexpire",
    is_flag=True,
    default=False,
    help="Skip wildcard password unexpire after start",
)
@click.option(
    "--load-timeout",
    type=int,
    default=LOAD_TIMEOUT,
    show_default=True,
    help="Time limit in seconds for the docker load (image import) phase only",
)
@click.option(
    "--timeout",
    type=int,
    default=HEALTH_TIMEOUT,
    show_default=True,
    help="Time limit in seconds for the IRIS health wait only",
)
def load_image(**params):
    """
    Load a docker-save IRIS tarball and start a container from it.

    Works on tarballs that docker load accepts (contain manifest.json) --
    typically the docker_kits/ downloads from kits-web.

    For singlefile_kits/ installer tarballs (contain irisinstall) use:
      idt image build <tarball>

    \b
    Examples:
        idt image load IRIS-2026.3.0AI.125.0-docker.tar.gz
        idt image load myimage.tar.gz --name my-iris --port 31972 --web-port 52774
        idt image load myimage.tar.gz --no-start
    """
    run_image_command(lambda: _do_load(**params), secrets=[params["password"]])
