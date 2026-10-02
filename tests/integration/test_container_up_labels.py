"""Feature 036 T027: ``idt container up`` labels the container it creates.

Creates one uniquely named container and removes it. Skips without Docker or
when the image is not present locally.
"""

import uuid

import pytest
from click.testing import CliRunner

pytestmark = [pytest.mark.integration, pytest.mark.slow]

IMAGE = "intersystemsdc/iris-community:latest-em"


def test_container_up_applies_idt_labels():
    docker = pytest.importorskip("docker")
    try:
        client = docker.from_env()
        client.ping()
        client.images.get(IMAGE)
    except Exception as exc:
        pytest.skip(f"Docker or image unavailable: {exc}")

    from iris_devtester.cli.container import container_group

    name = f"idt036-up-{uuid.uuid4().hex[:8]}"
    try:
        result = CliRunner().invoke(
            container_group,
            ["up", "--name", name, "--image", IMAGE, "--auto-port", "--timeout", "180"],
        )
        assert result.exit_code == 0, result.output
        labels = client.containers.get(name).labels
        assert labels["io.iris-devtester.created-by"] == "idt"
        assert labels["io.iris-devtester.image"] == IMAGE
    finally:
        try:
            client.containers.get(name).remove(force=True, v=True)
        except docker.errors.NotFound:
            pass
