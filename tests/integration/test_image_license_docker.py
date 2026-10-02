# flake8: noqa: F811
"""Integration: a license key in the working directory never reaches an image layer."""

import subprocess
import uuid

import pytest

from tests.unit.image.conftest import elf_arm64, installer_kit  # noqa: F401

pytestmark = pytest.mark.integration

SENTINEL = "IDT035-SENTINEL-LICENSE-KEY-TEXT"


def _docker_ok() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not _docker_ok(), reason="Docker is not available")
def test_key_absent_from_history_and_saved_image(tmp_path, monkeypatch, installer_kit, elf_arm64):
    from iris_devtester.cli.image.build import write_build_context
    from iris_devtester.cli.image.license import discover_license_key

    (tmp_path / "iris.key").write_text(SENTINEL)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IRIS_LICENSE_KEY", raising=False)
    res = discover_license_key(None)
    assert res.path is not None  # the key really is discoverable

    ctx = tmp_path / "ctx"
    ctx.mkdir()
    write_build_context(ctx, installer_kit, elf_arm64)
    # Replace the (slow, network-needing) real Dockerfile with a tiny one that
    # still copies the whole generated context into the image.
    (ctx / "Dockerfile").write_text("FROM scratch\nCOPY . /ctx/\n")

    tag = f"idt035-license-test:{uuid.uuid4().hex[:8]}"
    try:
        build = subprocess.run(
            ["docker", "build", "-t", tag, str(ctx)], capture_output=True, text=True, timeout=240
        )
        assert build.returncode == 0, build.stderr
        history = subprocess.run(
            ["docker", "history", "--no-trunc", tag], capture_output=True, text=True, timeout=60
        )
        saved = subprocess.run(["docker", "save", tag], capture_output=True, timeout=120)
        assert history.returncode == 0 and saved.returncode == 0
        assert SENTINEL not in history.stdout
        assert SENTINEL.encode() not in saved.stdout
    finally:
        subprocess.run(["docker", "rmi", "-f", tag], capture_output=True, timeout=60)
