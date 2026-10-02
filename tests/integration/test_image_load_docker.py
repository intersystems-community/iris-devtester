# flake8: noqa: F811
"""Integration: ``idt image load`` against a real Docker daemon.

Uses a tiny local image (busybox) saved to an archive; the IRIS health wait and
password steps are faked because the image is not IRIS.  The test creates and
removes its own uniquely named container.
"""

import subprocess
import uuid

import pytest
from click.testing import CliRunner

from tests.unit.image.conftest import fake_health, fake_password  # noqa: F401

pytestmark = pytest.mark.integration


def _docker(*args, timeout=120, **kw):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, **kw)


def _docker_ok() -> bool:
    try:
        return _docker("info", timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def tiny_archive(tmp_path):
    if not _docker_ok():
        pytest.skip("Docker is not available")
    source = "busybox:latest"
    if _docker("image", "inspect", source).returncode != 0:
        if _docker("pull", source, timeout=180).returncode != 0:
            pytest.skip("busybox is not available locally and cannot be pulled")
    tag = f"idt035-load-test:{uuid.uuid4().hex[:8]}"
    assert _docker("tag", source, tag).returncode == 0
    archive = tmp_path / "idt035-load-test.tar"
    try:
        saved = _docker("save", "-o", str(archive), tag)
        assert saved.returncode == 0, saved.stderr
    finally:
        _docker("rmi", tag)  # untag only; `docker load` restores it
    yield archive, tag
    _docker("rmi", "-f", tag)


def test_load_starts_labelled_container_with_masked_password(
    tiny_archive, fake_health, fake_password
):
    from iris_devtester.cli.image import image_group

    archive, tag = tiny_archive
    name = f"idt035-load-{uuid.uuid4().hex[:8]}"
    try:
        res = CliRunner().invoke(
            image_group,
            ["load", str(archive), "--name", name, "--port", "0", "--web-port", "0",
             "--password", "Int3gr@tion"],
        )  # fmt: skip
        if res.exit_code != 0 and "port" in res.output.lower():
            pytest.skip(f"host port mapping unavailable: {res.output[-200:]}")
        assert res.exit_code == 0, res.output
        assert "Int3gr@tion" not in res.output
        assert "********" in res.output
        labels = _docker("inspect", "-f", "{{json .Config.Labels}}", name)
        assert labels.returncode == 0, labels.stderr
        assert '"io.iris-devtester.created-by":"idt"' in labels.stdout
        assert f'"io.iris-devtester.image":"{tag}"' in labels.stdout
    finally:
        _docker("rm", "-f", name)
