"""Locate and validate the ``iris-main`` entrypoint for ``idt image build``.

Sources, in order of precedence: ``--iris-main`` > ``IDT_IRIS_MAIN`` >
``--iris-main-container`` > ``--iris-main-image`` > auto-detect from a running
container of the right architecture.  Every candidate is checked against the
build platform by reading its ELF header before anything is built.
"""

import os
import re
import shutil
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Tuple

import click

from iris_devtester.cli.image import runner
from iris_devtester.cli.image.errors import (
    EXIT_BAD_INPUT,
    EXIT_FAILURE,
    ImageCommandError,
)

ENV_VAR = "IDT_IRIS_MAIN"
PUBLIC_IMAGE = "containers.intersystems.com/intersystems/iris-community:latest-preview"
HELPER_CONTAINER = "idt-iris-main"

_ELF_MACHINES = {0xB7: "arm64", 0x3E: "amd64"}
_ARCH_ALIASES = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "amd64": "amd64",
    "x86_64": "amd64",
    "x86-64": "amd64",
}
_VERSION_RE = re.compile(r"(\d{4})\.(\d+)")


@dataclass
class IrisMainResolution:
    path: Path
    source: str
    arch: str
    cleanup: Optional[Callable[[], None]] = None


def platform_arch(platform: str) -> str:
    """``linux/arm64/v8`` -> ``arm64``; unknown architectures are bad input."""
    parts = platform.lower().split("/")
    raw = parts[1] if len(parts) > 1 else parts[0]
    arch = _ARCH_ALIASES.get(raw)
    if arch is None:
        raise ImageCommandError(
            what=f"Unsupported build platform '{platform}'.",
            why="iris-main can only be validated for linux/arm64 and linux/amd64.",
            fix="Pass --platform linux/arm64 or --platform linux/amd64.",
            exit_code=EXIT_BAD_INPUT,
            title="Unsupported platform",
        )
    return arch


def extraction_commands(platform: str) -> str:
    """The documented way to obtain iris-main for ``platform`` from the public image."""
    return (
        f"  docker create --platform {platform} --name {HELPER_CONTAINER} {PUBLIC_IMAGE}\n"
        f"  docker cp {HELPER_CONTAINER}:/iris-main ./iris-main\n"
        f"  docker rm {HELPER_CONTAINER}\n"
        "then pass: --iris-main ./iris-main  (or set IDT_IRIS_MAIN=./iris-main)"
    )


def _bad_file(path: Path, platform: str, detail: str) -> ImageCommandError:
    return ImageCommandError(
        what=f"{path} is not a valid iris-main binary: {detail}.",
        why="A wrong or damaged entrypoint makes the image fail at startup, after a long build.",
        fix=f"Get a fresh copy of iris-main for {platform}:\n{extraction_commands(platform)}",
        exit_code=EXIT_BAD_INPUT,
        title="Invalid iris-main",
    )


def elf_arch(path: Path, platform: str = "linux/arm64") -> str:
    """Architecture (``arm64``/``amd64``) from the ELF header of ``path``."""
    try:
        with open(path, "rb") as fh:
            hdr = fh.read(20)
    except OSError as exc:
        raise _bad_file(path, platform, f"cannot be read ({exc.strerror or exc})") from exc
    if len(hdr) < 20:
        raise _bad_file(path, platform, "file is truncated")
    if hdr[0:4] != b"\x7fELF":
        raise _bad_file(path, platform, "not an ELF file")
    if hdr[4] != 2 or hdr[5] != 1:
        raise _bad_file(path, platform, "not a 64-bit little-endian ELF")
    (machine,) = struct.unpack_from("<H", hdr, 18)
    arch = _ELF_MACHINES.get(machine)
    if arch is None:
        raise _bad_file(path, platform, f"unsupported machine type 0x{machine:x}")
    return arch


def check_elf_arch(path: Path, platform: str) -> str:
    """Return the architecture of ``path`` if it matches ``platform``, else raise (exit 2)."""
    want = platform_arch(platform)
    actual = elf_arch(Path(path), platform)
    if actual != want:
        raise ImageCommandError(
            what=f"iris-main at {path} is built for {actual} but the build platform "
            f"{platform} needs {want}.",
            why="An entrypoint of the wrong architecture cannot run; the container would exit "
            "immediately after a long build.",
            fix=f"Use an iris-main for {platform}:\n{extraction_commands(platform)}",
            exit_code=EXIT_BAD_INPUT,
            title="iris-main architecture mismatch",
        )
    return actual


def _explicit_file(raw: str, origin: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_file():
        raise ImageCommandError(
            what=f"iris-main file given by {origin} does not exist: {raw}",
            why="idt cannot build an image without an entrypoint.",
            fix=f"Point {origin} at an existing iris-main file, or remove it to auto-detect.",
            exit_code=EXIT_BAD_INPUT,
            title="iris-main not found",
        )
    return path


def extract_from_image(image_ref: str, platform: str, dest: Path) -> Path:
    """Copy ``/iris-main`` out of ``image_ref`` via a throwaway (never started) container."""
    created = runner.run_docker(["docker", "create", "--platform", platform, image_ref], 120)
    if created.returncode != 0:
        raise ImageCommandError(
            what=f"docker create failed for image {image_ref}: {created.stderr.strip()}",
            why="iris-main cannot be extracted without creating a temporary container.",
            fix=f"Check the image exists ('docker pull --platform {platform} {image_ref}') "
            "and that Docker is running.",
            exit_code=EXIT_FAILURE,
            title="Could not extract iris-main",
        )
    cid = created.stdout.strip()
    try:
        copied = runner.run_docker(["docker", "cp", f"{cid}:/iris-main", str(dest)], 120)
        if copied.returncode != 0:
            raise ImageCommandError(
                what=f"Image {image_ref} has no /iris-main: {copied.stderr.strip()}",
                why="Only IRIS images that use iris-main as entrypoint can be the source.",
                fix=f"Use another image, or:\n{extraction_commands(platform)}",
                exit_code=EXIT_BAD_INPUT,
                title="Could not extract iris-main",
            )
    finally:
        runner.run_docker(["docker", "rm", cid], 60)
    return dest


def _copy_from_container(container: str, dest: Path) -> None:
    result = runner.run_docker(["docker", "cp", f"{container}:/iris-main", str(dest)], 120)
    if result.returncode != 0:
        raise ImageCommandError(
            what=f"Failed to copy iris-main from container '{container}': "
            f"{result.stderr.strip()}",
            why="Without iris-main the image has no entrypoint.",
            fix="Check the container exists and is an IRIS container ('docker ps'), or pass "
            "--iris-main <file>.",
            exit_code=EXIT_FAILURE,
            title="Could not copy iris-main",
        )


def _find_container_with_iris_main(platform: str, workdir: Path) -> Optional[Tuple[str, Path]]:
    """First running container whose ``/iris-main`` matches ``platform`` (copied to ``workdir``)."""
    ps = runner.run_docker(["docker", "ps", "--format", "{{.Names}}"], 10)
    if ps.returncode != 0:
        return None
    for cname in (line.strip() for line in ps.stdout.splitlines()):
        if not cname:
            continue
        probe = runner.run_docker(["docker", "exec", cname, "test", "-f", "/iris-main"], 10)
        if probe.returncode != 0:
            continue
        candidate = workdir / f"iris-main-{cname}"
        copied = runner.run_docker(["docker", "cp", f"{cname}:/iris-main", str(candidate)], 60)
        if copied.returncode != 0:
            continue
        try:
            check_elf_arch(candidate, platform)
        except ImageCommandError:
            candidate.unlink()
            continue
        return cname, candidate
    return None


def _version_of(text: str) -> Optional[Tuple[int, int]]:
    match = _VERSION_RE.search(text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def _warn_on_version_mismatch(
    source_version: Optional[Tuple[int, int]],
    source_desc: str,
    kit_name: Optional[str],
    echo: Callable[[str], None],
) -> None:
    kit_version = _version_of(kit_name or "")
    if source_version and kit_version and source_version != kit_version:
        echo(
            f"  ⚠ Warning: iris-main from {source_desc} looks like IRIS "
            f"{source_version[0]}.{source_version[1]} but the kit is "
            f"{kit_version[0]}.{kit_version[1]}; continuing (the build may still work)."
        )


def resolve_iris_main(
    *,
    option: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    container: Optional[str] = None,
    image: Optional[str] = None,
    platform: str,
    kit_name: Optional[str] = None,
    echo: Callable[[str], None] = click.echo,
) -> IrisMainResolution:
    """Pick, fetch and validate iris-main. The caller must run ``cleanup`` when set."""
    environ = os.environ if env is None else env

    if option:
        path = _explicit_file(option, "--iris-main")
        arch = check_elf_arch(path, platform)
        echo(f"  → iris-main: {path} (from --iris-main)")
        return IrisMainResolution(path, "option", arch)
    if environ.get(ENV_VAR):
        path = _explicit_file(environ[ENV_VAR], f"the {ENV_VAR} environment variable")
        arch = check_elf_arch(path, platform)
        echo(f"  → iris-main: {path} (from {ENV_VAR})")
        return IrisMainResolution(path, "env", arch)

    workdir = Path(tempfile.mkdtemp(prefix="idt-iris-main-"))

    def cleanup() -> None:
        shutil.rmtree(workdir, ignore_errors=True)

    try:
        if container:
            dest = workdir / "iris-main"
            _copy_from_container(container, dest)
            arch = check_elf_arch(dest, platform)
            source = f"container {container}"
            echo(f"  → iris-main: copied from container '{container}' (--iris-main-container)")
            probe = runner.run_docker(["docker", "exec", container, "/iris-main", "--version"], 10)
            version = _version_of(probe.stdout) if probe.returncode == 0 else None
            _warn_on_version_mismatch(version, f"container '{container}'", kit_name, echo)
        elif image:
            dest = workdir / "iris-main"
            extract_from_image(image, platform, dest)
            arch = check_elf_arch(dest, platform)
            source = f"image {image}"
            echo(f"  → iris-main: extracted from image '{image}' (--iris-main-image)")
            _warn_on_version_mismatch(_version_of(image), f"image '{image}'", kit_name, echo)
        else:
            found = _find_container_with_iris_main(platform, workdir)
            if found is None:
                raise ImageCommandError(
                    what=f"No usable iris-main was found for {platform}: none was given and no "
                    "running container has one of the right architecture.",
                    why="The image needs it as its entrypoint, so the build cannot proceed.",
                    fix=(
                        "Extract it from the public image:\n"
                        f"{extraction_commands(platform)}\n"
                        "or start any IRIS container (e.g. 'idt container up') and retry."
                    ),
                    exit_code=EXIT_BAD_INPUT,
                    title="iris-main not found",
                )
            cname, dest = found
            arch = platform_arch(platform)
            source = f"auto-detected container {cname}"
            echo(f"  → iris-main: copied from running container '{cname}' (auto-detected)")
    except BaseException:
        cleanup()
        raise
    return IrisMainResolution(dest, source, arch, cleanup)
