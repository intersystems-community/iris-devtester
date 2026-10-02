"""``idt image build`` -- build an image from an ISC installer kit and start it."""

import platform as _platform
import shutil
import tempfile
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
    EXIT_FAILURE,
    ImageCommandError,
    build_timeout_error,
)
from iris_devtester.cli.image.iris_main import resolve_iris_main
from iris_devtester.cli.image.license import discover_license_key
from iris_devtester.cli.image.options import BUILD_TIMEOUT, HEALTH_TIMEOUT, StartOptions

_DOCKERFILE_TEMPLATE = """\
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \\
    libcap2-bin \\
    tini \\
    libssl3 \\
    libstdc++6 \\
    libicu74 \\
    && rm -rf /var/lib/apt/lists/* \\
    && ln -s /usr/bin/tini /tini

ARG ISC_PACKAGE_INSTANCENAME=IRIS
ARG ISC_PACKAGE_INSTALLDIR=/usr/irissys
ARG ISC_PACKAGE_MGRUSER=irisowner
ARG ISC_PACKAGE_IRISUSER=irisowner
ARG ISC_PACKAGE_MGRGROUP=irisowner
ARG ISC_PACKAGE_IRISGROUP=irisowner

ENV ISC_PACKAGE_INSTANCENAME=${{ISC_PACKAGE_INSTANCENAME}} \\
    ISC_PACKAGE_INSTALLDIR=${{ISC_PACKAGE_INSTALLDIR}} \\
    ISC_PACKAGE_MGRUSER=${{ISC_PACKAGE_MGRUSER}} \\
    ISC_PACKAGE_IRISUSER=${{ISC_PACKAGE_IRISUSER}} \\
    ISC_PACKAGE_MGRGROUP=${{ISC_PACKAGE_MGRGROUP}} \\
    ISC_PACKAGE_IRISGROUP=${{ISC_PACKAGE_IRISGROUP}} \\
    IRISSYS=/home/irisowner/irissys \\
    ISC_DEFAULT_PASSWORD=SYS \\
    PATH=/usr/irissys/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN useradd -m irisowner --uid 51773 && \\
    chmod 755 /home/irisowner && \\
    groupadd -r iscagent && \\
    usermod -a -G iscagent irisowner && \\
    mkdir -p /usr/irissys && \\
    chown -R 51773:51773 /usr/irissys

COPY --chown=51773:51773 iris.kit.tar.gz /tmp/iris.tar.gz

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN mkdir -p /tmp/work && \\
    tar -C /tmp/work -xzf /tmp/iris.tar.gz && \\
    KIT_DIR=$(find /tmp/work -maxdepth 1 -name 'IRIS*' -type d | head -1) && \\
    cd "$KIT_DIR" && \\
    export ISC_PACKAGE_USER_PASSWORD=SYS && \\
    export ISC_PACKAGE_STARTIRIS=Y && \\
    export ISC_PACKAGE_UNICODE=Y && \\
    export ISC_PACKAGE_INITIAL_SECURITY=Normal && \\
    export ISC_PACKAGE_WEB_CONFIGURE=N && \\
    mkdir -p /home/irisowner/irissys && \\
    ./irisinstall_silent && \\
    cd /usr/irissys/dev/Container && \\
    ISC_PACKAGE_INSTANCENAME=IRIS \\
    ISC_PACKAGE_INSTALLDIR=/usr/irissys \\
    ISC_PACKAGE_MGRUSER=irisowner \\
    ISC_PACKAGE_MGRGROUP=irisowner \\
    ISC_PACKAGE_IRISUSER=irisowner \\
    ISC_PACKAGE_IRISGROUP=irisowner \\
    IRISSYS=/home/irisowner/irissys \\
    bash imageBuildSteps.sh && \\
    rm -rf /tmp/work /tmp/iris.tar.gz && \\
    chown -R 51773:51773 /home/irisowner/irissys && \\
    chmod 755 /home/irisowner/irissys && \\
    chown 51773:51773 /usr/irissys/bin/irisstart /usr/irissys/bin/irisstop \\
        /usr/irissys/bin/irisforce && \\
    chmod 755 /usr/irissys/bin/irisstart /usr/irissys/bin/irisstop /usr/irissys/bin/irisforce

RUN cp /usr/irissys/bin/irisdb /usr/irissys/bin/iriscp && \\
    setcap "cap_ipc_lock+ep" /usr/irissys/bin/iriscp && \\
    chown 51773:51773 /usr/irissys/bin/iriscp /usr/irissys/bin/irisdb && \\
    chmod 755 /usr/irissys/bin/iriscp /usr/irissys/bin/irisdb

COPY --chown=51773:51773 iris-main /iris-main
RUN chmod +x /iris-main

USER 51773
WORKDIR /home/irisowner

EXPOSE 1972/tcp 52773/tcp 8888/tcp

ENTRYPOINT ["/iris-main"]
"""


def render_dockerfile() -> str:
    """The Dockerfile for the build. It never references a license key."""
    return _DOCKERFILE_TEMPLATE.format()


def write_build_context(build_dir: Path, kit: Path, iris_main: Path) -> None:
    """Populate ``build_dir`` with the kit, iris-main and Dockerfile (never a license key)."""
    shutil.copy2(kit, build_dir / "iris.kit.tar.gz")
    dest = build_dir / "iris-main"
    if iris_main.resolve() != dest.resolve():
        shutil.copy2(iris_main, dest)
    dest.chmod(0o755)
    (build_dir / "Dockerfile").write_text(render_dockerfile())


def _do_build(
    tarball,
    image_tag,
    name,
    superserver_port,
    web_port,
    license_key,
    iris_main_container,
    iris_main_image,
    iris_main_path,
    password,
    show_password,
    replace,
    no_start,
    no_unexpire,
    build_platform,
    timeout,
    build_timeout,
    keep_build_dir,
):
    tarball_path = Path(tarball)
    web_port_val: Optional[int] = web_port if web_port and web_port > 0 else None
    build_dir: Optional[Path] = None
    iris_main_cleanup = None

    try:
        if not image_tag:
            image_tag = derive_name_from_tarball(tarball_path)
            click.echo(f"  → Image tag: {image_tag} (derived from filename)")
        else:
            click.echo(f"  → Image tag: {image_tag}")

        container_name = name or derive_name_from_tarball(tarball_path)
        click.echo(f"  → Container name: {container_name}")

        if not build_platform:
            machine = _platform.machine().lower()
            build_platform = "linux/arm64" if machine in ("arm64", "aarch64") else "linux/amd64"
        click.echo(f"  → Platform: {build_platform}")

        license_res = discover_license_key(license_key)
        if license_res.path:
            click.echo(f"  → License key: {license_res.describe()} (mounted read-only at run)")
        elif license_res.notice:
            click.secho(f"  ⚠ {license_res.notice.message}", fg="yellow")

        main_res = resolve_iris_main(
            option=iris_main_path,
            container=iris_main_container,
            image=iris_main_image,
            platform=build_platform,
            kit_name=tarball_path.name,
        )
        iris_main_cleanup = main_res.cleanup

        build_dir = Path(tempfile.mkdtemp(prefix="idt-image-build-"))
        click.echo(f"\n⏳ Build context: {build_dir}")
        click.echo(
            f"⏳ Copying kit to build context ({tarball_path.stat().st_size // (1024*1024)} MB) ..."
        )
        write_build_context(build_dir, tarball_path, main_res.path)
        click.echo("✓ Kit, iris-main and Dockerfile written")

        click.echo(f"\n⏳ Building image '{image_tag}' (this takes 5–8 minutes) ...")
        build_cmd = [
            "docker",
            "build",
            "--platform",
            build_platform,
            "-t",
            image_tag,
            str(build_dir),
        ]
        click.echo(f"  → {' '.join(build_cmd)}")

        try:
            result = runner.run_build(
                build_cmd, timeout=build_timeout, on_line=lambda ln: click.echo(f"  {ln}")
            )
        except runner.BuildTimeout as exc:
            raise build_timeout_error(exc.limit, exc.elapsed, exc.last_line) from exc
        if result.returncode != 0:
            raise ImageCommandError(
                what=f"docker build failed (exit {result.returncode}). "
                f"Last output line: {result.last_line}",
                why="No image was produced, so there is nothing to start.",
                fix="Read the build output above; re-run with --keep-build-dir to keep the "
                "build context (Dockerfile, kit, iris-main) for inspection.",
                exit_code=EXIT_FAILURE,
                title="Image build failed",
            )
        click.echo(f"✓ Image '{image_tag}' built successfully")

        options = StartOptions(
            name=container_name,
            superserver_port=superserver_port,
            web_port=web_port_val,
            password=password,
            show_password=show_password,
            replace=replace,
            no_unexpire=no_unexpire,
            health_timeout=timeout,
            cap_ipc_lock=True,
            license_mount=str(license_res.path) if license_res.path else None,
        )
        if no_start:
            click.echo("\n  → --no-start: image built, container not started.")
            print_manual_start_hint(image_tag, options)
            return

        click.echo(f"\n  → SuperServer port: {superserver_port}")
        if web_port_val:
            click.echo(f"  → Web port: {web_port_val}")
        create_and_start_container(image_tag, options, command="build")
    finally:
        if iris_main_cleanup:
            iris_main_cleanup()
        if build_dir and build_dir.exists() and not keep_build_dir:
            shutil.rmtree(build_dir, ignore_errors=True)
        elif build_dir and keep_build_dir:
            click.echo(f"  → Build directory kept at: {build_dir}")


@image_group.command(name="build")
@click.argument("tarball", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--tag",
    "image_tag",
    type=str,
    default=None,
    help="Image tag to produce (default: derived from tarball filename, e.g. irishealth-ai:140)",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Container name after start (default: derived from tarball filename)",
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
    "--license",
    "license_key",
    type=click.Path(),
    default=None,
    help="Path to iris.key, mounted read-only at run (never baked into the image). "
    "Default: $IRIS_LICENSE_KEY, then ./iris.key",
)
@click.option(
    "--iris-main-container",
    type=str,
    default=None,
    help="Running container to copy /iris-main from (auto-detected if not given)",
)
@click.option(
    "--iris-main-image",
    type=str,
    default=None,
    help="Image to extract /iris-main from (docker create + cp; never started)",
)
@click.option(
    "--iris-main",
    "iris_main_path",
    type=click.Path(),
    default=None,
    help="Local path to iris-main binary (alternative to --iris-main-container)",
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
    help="Build image only; do not create or start a container",
)
@click.option(
    "--no-unexpire", is_flag=True, default=False, help="Skip wildcard password unexpire after start"
)
@click.option(
    "--platform",
    "build_platform",
    type=str,
    default=None,
    help="Docker --platform override (e.g. linux/arm64). Auto-detected if not given.",
)
@click.option(
    "--build-timeout",
    type=int,
    default=BUILD_TIMEOUT,
    show_default=True,
    help="Time limit in seconds for the docker build phase only "
    "(macOS/Linux kill the whole build process group; Windows kills only the docker CLI)",
)
@click.option(
    "--timeout",
    type=int,
    default=HEALTH_TIMEOUT,
    show_default=True,
    help="Time limit in seconds for the IRIS health wait only",
)
@click.option(
    "--keep-build-dir",
    is_flag=True,
    default=False,
    help="Don't delete the temp build directory after build (useful for debugging)",
)
def build_image(**params):
    """
    Build a Docker image from an ISC installer kit tarball (singlefile_kits).

    The kits-web singlefile_kits/ tarballs contain irisinstall_silent, not
    docker layers. This command builds a Docker image from them using the same
    Dockerfile approach used internally by InterSystems for official images.

    \b
    Prerequisites (resolved automatically when possible):
      iris-main   — copied from any running IRIS container (or --iris-main)
      iris.key    — --license, else $IRIS_LICENSE_KEY, else ./iris.key;
                    mounted read-only when the container starts

    \b
    Examples:
        # Minimal — auto-detect everything
        idt image build IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz

        # Explicit tag + container name + port
        idt image build IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz \\
            --tag irishealth-ai:140 --name hs-iris --port 31974 --web-port 52777

        # Build image only, start manually later
        idt image build IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz \\
            --tag irishealth-ai:140 --no-start
    """
    run_image_command(lambda: _do_build(**params), secrets=[params["password"]])
