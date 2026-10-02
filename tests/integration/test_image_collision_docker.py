"""Integration: collision rule against a real Docker daemon (own, uniquely named containers)."""

import subprocess
import uuid

import pytest

from iris_devtester.cli.image.collision import resolve_name_collision
from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.options import build_labels

pytestmark = pytest.mark.integration


def _client():
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


@pytest.fixture
def docker_client():
    client = _client()
    if client is None:
        pytest.skip("Docker is not available")
    return client


@pytest.fixture
def scratch_image(docker_client):
    tag = f"idt035-collision:{uuid.uuid4().hex[:8]}"
    out = subprocess.run(
        ["docker", "build", "-t", tag, "-"],
        input="FROM scratch\nLABEL idt035=1\n",
        capture_output=True,
        text=True,
        timeout=120,
    )
    if out.returncode != 0:
        pytest.skip(f"cannot build scratch image: {out.stderr[:200]}")
    yield tag
    subprocess.run(["docker", "rmi", "-f", tag], capture_output=True, timeout=60)


def test_labelled_removed_unlabelled_survives(docker_client, scratch_image):
    suffix = uuid.uuid4().hex[:8]
    mine = f"idt035-mine-{suffix}"
    theirs = f"idt035-theirs-{suffix}"
    try:
        docker_client.containers.create(
            scratch_image, command=["/none"], name=mine, labels=build_labels(scratch_image)
        )
        docker_client.containers.create(scratch_image, command=["/none"], name=theirs)

        lines = []
        resolve_name_collision(docker_client, mine, True, echo=lines.append)
        assert len(lines) == 1
        with pytest.raises(Exception):
            docker_client.containers.get(mine)

        with pytest.raises(ImageCommandError) as ei:
            resolve_name_collision(docker_client, theirs, True, echo=lines.append)
        assert ei.value.exit_code == 2
        assert docker_client.containers.get(theirs) is not None
    finally:
        for name in (mine, theirs):
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
