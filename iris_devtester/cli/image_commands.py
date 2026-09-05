"""Image management CLI commands — load or build kits-web tarballs into containers."""

import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import click

from iris_devtester.utils import progress


# ── Shared helpers ────────────────────────────────────────────────────────────

def _derive_name_from_tarball(tarball_path: Path) -> str:
    stem = tarball_path.stem
    if stem.endswith(".tar"):
        stem = stem[:-4]
    name = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    if len(name) > 40:
        name = name[:40].rstrip("-")
    return name


def _docker_run(
    image: str,
    container_name: str,
    superserver_port: int,
    web_port: Optional[int],
    cap_ipc_lock: bool = False,
    timeout: int = 60,
) -> None:
    cmd = ["docker", "run", "-d", "--name", container_name, "-p", f"{superserver_port}:1972"]
    if web_port:
        cmd += ["-p", f"{web_port}:52773"]
    if cap_ipc_lock:
        cmd += ["--cap-add", "CAP_IPC_LOCK"]
    cmd.append(image)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"docker run failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )


def _start_and_fixup(
    ctx,
    image_ref: str,
    container_name: str,
    superserver_port: int,
    web_port_val: Optional[int],
    password: str,
    no_unexpire: bool,
    timeout: int,
    cap_ipc_lock: bool = False,
) -> None:
    """Start container from image_ref, wait healthy, unexpire, reset password."""
    import docker

    client = docker.from_env()

    # Collision check
    try:
        existing = client.containers.get(container_name)
        existing.reload()
        raise click.ClickException(
            f"Container '{container_name}' already exists (status: {existing.status}).\n"
            f"Remove it first:  docker rm -f {container_name}\n"
            f"Or pick a different name with --name."
        )
    except docker.errors.NotFound:
        pass

    click.echo(f"⏳ Starting container '{container_name}' ...")
    _docker_run(image_ref, container_name, superserver_port, web_port_val,
                cap_ipc_lock=cap_ipc_lock, timeout=60)
    click.echo(f"✓ Container '{container_name}' started")

    from iris_devtester.utils import health_checks

    click.echo("⏳ Waiting for IRIS to become healthy ...")
    container_obj = client.containers.get(container_name)

    try:
        health_checks.wait_for_healthy(
            container_obj, timeout=timeout, progress_callback=lambda m: click.echo(f"  {m}")
        )
    except TimeoutError as e:
        raise RuntimeError(str(e))
    click.echo("✓ IRIS is healthy")

    if not no_unexpire:
        click.echo("⏳ Unexpiring all passwords ...")
        try:
            from iris_devtester.utils.password import unexpire_all_passwords
            unexpire_all_passwords(container_name)
            click.echo("✓ Passwords unexpired")
        except Exception as e:
            click.secho(f"  ⚠ Unexpire failed (non-fatal): {e}", fg="yellow")

    click.echo(f"⏳ Setting _SYSTEM password to '{password}' ...")
    try:
        from iris_devtester.utils.password import reset_password
        ok, msg = reset_password(
            container_name=container_name,
            username="_SYSTEM",
            new_password=password,
            hostname="localhost",
            port=superserver_port,
            verify=False,
        )
        if ok:
            click.echo("✓ Password set")
        else:
            click.secho(f"  ⚠ Password reset reported failure (non-fatal): {msg}", fg="yellow")
    except Exception as e:
        click.secho(f"  ⚠ Password reset failed (non-fatal): {e}", fg="yellow")

    click.echo(f"\n✓ Container '{container_name}' is ready")
    progress.print_connection_info(
        container_name=container_name,
        superserver_port=superserver_port,
        webserver_port=web_port_val or 0,
        namespace="USER",
        password=password,
    )


def _is_installer_kit(tarball_path: Path) -> bool:
    """Return True if the tarball is an ISC installer kit (has irisinstall), not a docker save."""
    try:
        with tarfile.open(tarball_path, "r:gz") as tf:
            names = tf.getnames()
        return any(n.endswith("/irisinstall") or n == "irisinstall" for n in names)
    except Exception:
        return False


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
{license_line}

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
    chown 51773:51773 /usr/irissys/bin/irisstart /usr/irissys/bin/irisstop /usr/irissys/bin/irisforce && \\
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


def _find_iris_main_from_running_container() -> Optional[str]:
    """Try to find iris-main by copying it from the first running IRIS container."""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return None
    for cname in result.stdout.splitlines():
        cname = cname.strip()
        if not cname:
            continue
        # Check if iris-main exists in this container
        probe = subprocess.run(
            ["docker", "exec", cname, "test", "-f", "/iris-main"],
            capture_output=True, timeout=5,
        )
        if probe.returncode == 0:
            return cname
    return None


def _copy_iris_main(src_container: str, dest_path: Path) -> None:
    result = subprocess.run(
        ["docker", "cp", f"{src_container}:/iris-main", str(dest_path)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to copy iris-main from '{src_container}':\n{result.stderr.strip()}"
        )


# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group(name="image")
def image_group():
    """
    Docker image management commands.

    \b
    Load or build kits-web IRIS tarballs into Docker images and containers.

    \b
    QUICK START:
      # Docker-save tarball (has manifest.json inside):
      idt image load IRIS-2026.2.0AI.127.0-docker.tar.gz

      # ISC installer kit (has irisinstall inside — most singlefile_kits):
      idt image build IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz \\
          --tag irishealth-ai:140 --name hs-iris --port 31974
    """
    pass


# ── idt image load ────────────────────────────────────────────────────────────

@image_group.command(name="load")
@click.argument("tarball", type=click.Path(exists=True, dir_okay=False))
@click.option("--name", type=str, default=None,
              help="Container name (default: derived from tarball filename)")
@click.option("--port", "superserver_port", type=int, default=1972, show_default=True,
              help="Host port mapped to IRIS SuperServer (1972)")
@click.option("--web-port", type=int, default=52773, show_default=True,
              help="Host port mapped to IRIS Web gateway (52773). Pass 0 to skip.")
@click.option("--password", default="SYS", show_default=True,
              help="Password to set on _SYSTEM after start")
@click.option("--no-start", is_flag=True, default=False,
              help="Load image only; do not create or start a container")
@click.option("--no-unexpire", is_flag=True, default=False,
              help="Skip wildcard password unexpire after start")
@click.option("--timeout", type=int, default=300, show_default=True,
              help="Timeout in seconds for load + start + health check")
@click.pass_context
def load_image(ctx, tarball, name, superserver_port, web_port, password,
               no_start, no_unexpire, timeout):
    """
    Load a docker-save IRIS tarball and start a container from it.

    Works on tarballs that docker load accepts (contain manifest.json) —
    typically the docker_kits/ downloads from kits-web.

    For singlefile_kits/ installer tarballs (contain irisinstall) use:
      idt image build <tarball>

    \b
    Examples:
        idt image load IRIS-2026.3.0AI.125.0-docker.tar.gz
        idt image load myimage.tar.gz --name my-iris --port 31972 --web-port 52774
        idt image load myimage.tar.gz --no-start
    """
    tarball_path = Path(tarball)
    web_port_val: Optional[int] = web_port if web_port and web_port > 0 else None

    try:
        # Detect installer kit and redirect
        if _is_installer_kit(tarball_path):
            raise click.ClickException(
                f"{tarball_path.name} is an ISC installer kit (contains irisinstall),\n"
                "not a docker-save archive. Use:\n\n"
                f"  idt image build {tarball_path.name} --tag <image:tag> --name <container>\n"
            )

        click.echo(f"⏳ Loading image from {tarball_path.name} ...")
        result = subprocess.run(
            ["docker", "load", "-i", str(tarball_path)],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"docker load failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )

        image_ref = None
        for line in result.stdout.splitlines():
            if line.startswith("Loaded image:"):
                image_ref = line.split(":", 1)[1].strip()
                break
            if line.startswith("Loaded image ID:"):
                image_ref = line.split(":", 1)[1].strip()
                break
        if not image_ref:
            raise RuntimeError(
                f"docker load succeeded but produced no image tag.\nOutput:\n{result.stdout}"
            )

        click.echo(f"✓ Image loaded: {image_ref}")

        if no_start:
            click.echo("  → --no-start: skipping container creation")
            click.echo(f"\nTo start manually:\n  docker run -d -p {superserver_port}:1972 {image_ref}")
            ctx.exit(0)
            return

        container_name = name or _derive_name_from_tarball(tarball_path)
        click.echo(f"  → Container name: {container_name}")
        click.echo(f"  → SuperServer port: {superserver_port}")
        if web_port_val:
            click.echo(f"  → Web port: {web_port_val}")

        _start_and_fixup(ctx, image_ref, container_name, superserver_port,
                         web_port_val, password, no_unexpire, timeout)
        ctx.exit(0)

    except click.ClickException:
        raise
    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except RuntimeError as e:
        progress.print_error(str(e))
        ctx.exit(1)
    except Exception as e:
        progress.print_error(f"Unexpected error: {e}")
        ctx.exit(1)


# ── idt image build ───────────────────────────────────────────────────────────

@image_group.command(name="build")
@click.argument("tarball", type=click.Path(exists=True, dir_okay=False))
@click.option("--tag", "image_tag", type=str, default=None,
              help="Image tag to produce (default: derived from tarball filename, e.g. irishealth-ai:140)")
@click.option("--name", type=str, default=None,
              help="Container name after start (default: derived from tarball filename)")
@click.option("--port", "superserver_port", type=int, default=1972, show_default=True,
              help="Host port mapped to IRIS SuperServer (1972)")
@click.option("--web-port", type=int, default=52773, show_default=True,
              help="Host port mapped to IRIS Web gateway (52773). Pass 0 to skip.")
@click.option("--license", "license_key", type=click.Path(exists=True), default=None,
              help="Path to iris.key (searches ./iris.key and ~/ws/iris-devtester/iris.key if not given)")
@click.option("--iris-main-container", type=str, default=None,
              help="Running container to copy /iris-main from (auto-detected if not given)")
@click.option("--iris-main", "iris_main_path", type=click.Path(exists=True), default=None,
              help="Local path to iris-main binary (alternative to --iris-main-container)")
@click.option("--password", default="SYS", show_default=True,
              help="Password to set on _SYSTEM after start")
@click.option("--no-start", is_flag=True, default=False,
              help="Build image only; do not create or start a container")
@click.option("--no-unexpire", is_flag=True, default=False,
              help="Skip wildcard password unexpire after start")
@click.option("--platform", "build_platform", type=str, default=None,
              help="Docker --platform override (e.g. linux/arm64). Auto-detected if not given.")
@click.option("--timeout", type=int, default=900, show_default=True,
              help="Total timeout in seconds (build ~5-8 min + start + health check)")
@click.option("--keep-build-dir", is_flag=True, default=False,
              help="Don't delete the temp build directory after build (useful for debugging)")
@click.pass_context
def build_image(ctx, tarball, image_tag, name, superserver_port, web_port, license_key,
                iris_main_container, iris_main_path, password, no_start, no_unexpire,
                build_platform, timeout, keep_build_dir):
    """
    Build a Docker image from an ISC installer kit tarball (singlefile_kits).

    The kits-web singlefile_kits/ tarballs contain irisinstall_silent, not
    docker layers. This command builds a Docker image from them using the same
    Dockerfile approach used internally by InterSystems for official images.

    \b
    Prerequisites (resolved automatically when possible):
      iris-main   — copied from any running IRIS container (or --iris-main)
      iris.key    — searched at ./iris.key, ~/ws/iris-devtester/iris.key,
                    or supplied via --license

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
    tarball_path = Path(tarball)
    web_port_val: Optional[int] = web_port if web_port and web_port > 0 else None
    build_dir: Optional[Path] = None

    try:
        # ── Derive image tag ─────────────────────────────────────────────────
        if not image_tag:
            image_tag = _derive_name_from_tarball(tarball_path)
            click.echo(f"  → Image tag: {image_tag} (derived from filename)")
        else:
            click.echo(f"  → Image tag: {image_tag}")

        container_name = name or _derive_name_from_tarball(tarball_path)
        click.echo(f"  → Container name: {container_name}")

        # ── Detect platform ──────────────────────────────────────────────────
        if not build_platform:
            import platform as _platform
            machine = _platform.machine().lower()
            if machine in ("arm64", "aarch64"):
                build_platform = "linux/arm64"
            else:
                build_platform = "linux/amd64"
        click.echo(f"  → Platform: {build_platform}")

        # ── Resolve iris.key ─────────────────────────────────────────────────
        key_path: Optional[Path] = None
        if license_key:
            key_path = Path(license_key)
        else:
            candidates = [
                Path.cwd() / "iris.key",
                Path(__file__).parents[2] / "iris.key",  # repo root
                Path.home() / "ws" / "iris-devtester" / "iris.key",
            ]
            for c in candidates:
                if c.exists():
                    key_path = c
                    break

        if key_path:
            click.echo(f"  → License key: {key_path}")
        else:
            click.secho(
                "  ⚠ No iris.key found — building without license.\n"
                "    For enterprise/HealthShare images this may fail at startup.\n"
                "    Supply one with: --license /path/to/iris.key",
                fg="yellow",
            )

        # ── Resolve iris-main ────────────────────────────────────────────────
        resolved_iris_main: Optional[Path] = None
        if iris_main_path:
            resolved_iris_main = Path(iris_main_path)
            click.echo(f"  → iris-main: {resolved_iris_main} (explicit)")
        else:
            src_container = iris_main_container or _find_iris_main_from_running_container()
            if src_container:
                click.echo(f"  → iris-main: copying from container '{src_container}' ...")
                # Will be copied into build_dir below
            else:
                raise RuntimeError(
                    "Could not find iris-main.\n\n"
                    "iris-main is the IRIS container entrypoint. Copy it from any running IRIS container:\n"
                    "  docker cp <container>:/iris-main /tmp/iris-main\n"
                    "Then pass:\n"
                    "  idt image build <kit> --iris-main /tmp/iris-main\n"
                    "Or start any IRIS container first (e.g. 'idt container up --edition light')\n"
                    "and idt will find it automatically."
                )

        # ── Create build directory ───────────────────────────────────────────
        build_dir = Path(tempfile.mkdtemp(prefix="idt-image-build-"))
        click.echo(f"\n⏳ Build context: {build_dir}")

        # Copy kit
        kit_dest = build_dir / "iris.kit.tar.gz"
        click.echo(f"⏳ Copying kit to build context ({tarball_path.stat().st_size // (1024*1024)} MB) ...")
        shutil.copy2(tarball_path, kit_dest)
        click.echo("✓ Kit copied")

        # Copy iris-main
        iris_main_dest = build_dir / "iris-main"
        if resolved_iris_main:
            shutil.copy2(resolved_iris_main, iris_main_dest)
        else:
            _copy_iris_main(src_container, iris_main_dest)
        iris_main_dest.chmod(0o755)
        click.echo("✓ iris-main ready")

        # Copy iris.key
        if key_path:
            shutil.copy2(key_path, build_dir / "iris.key")
            license_line = "COPY --chown=51773:51773 iris.key /usr/irissys/mgr/iris.key"
        else:
            license_line = "# No iris.key — community/evaluation build"

        # Write Dockerfile
        dockerfile = _DOCKERFILE_TEMPLATE.format(license_line=license_line)
        (build_dir / "Dockerfile").write_text(dockerfile)
        click.echo("✓ Dockerfile written")

        # ── docker build ─────────────────────────────────────────────────────
        build_timeout = max(timeout - 120, 300)  # reserve 120s for start+health
        click.echo(f"\n⏳ Building image '{image_tag}' (this takes 5–8 minutes) ...")
        build_cmd = [
            "docker", "build",
            "--platform", build_platform,
            "-t", image_tag,
            str(build_dir),
        ]
        click.echo(f"  → {' '.join(build_cmd)}")

        build_proc = subprocess.Popen(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert build_proc.stdout is not None
        last_line = ""
        for line in build_proc.stdout:
            line = line.rstrip()
            if line:
                click.echo(f"  {line}")
                last_line = line

        build_proc.wait(timeout=build_timeout)
        if build_proc.returncode != 0:
            raise RuntimeError(
                f"docker build failed (exit {build_proc.returncode}).\n"
                f"Last output line: {last_line}"
            )

        click.echo(f"✓ Image '{image_tag}' built successfully")

        if no_start:
            click.echo(
                f"\n  → --no-start: image built, container not started.\n"
                f"  To start manually:\n"
                f"    docker run -d --name <name> -p {superserver_port}:1972 {image_tag}"
            )
            ctx.exit(0)
            return

        # ── Start + fixup ─────────────────────────────────────────────────────
        click.echo(f"\n  → SuperServer port: {superserver_port}")
        if web_port_val:
            click.echo(f"  → Web port: {web_port_val}")

        _start_and_fixup(ctx, image_tag, container_name, superserver_port,
                         web_port_val, password, no_unexpire, timeout=120,
                         cap_ipc_lock=True)
        ctx.exit(0)

    except click.ClickException:
        raise
    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except RuntimeError as e:
        progress.print_error(str(e))
        ctx.exit(1)
    except Exception as e:
        progress.print_error(f"Unexpected error: {e}")
        ctx.exit(1)
    finally:
        if build_dir and build_dir.exists() and not keep_build_dir:
            shutil.rmtree(build_dir, ignore_errors=True)
        elif build_dir and keep_build_dir:
            click.echo(f"  → Build directory kept at: {build_dir}")
