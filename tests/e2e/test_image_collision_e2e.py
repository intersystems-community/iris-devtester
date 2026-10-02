"""E2E (CliRunner, faked Docker): same-name reruns need --replace."""

import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import image_group

pytestmark = pytest.mark.e2e


def test_second_load_refused_then_replaced(
    fake_runner, fake_docker, fake_health, fake_password, image_archive
):
    args = ["load", str(image_archive), "--name", "twice"]
    first = CliRunner().invoke(image_group, args)
    assert first.exit_code == 0, first.output
    old = fake_docker.containers.store["twice"]

    second = CliRunner().invoke(image_group, args)
    assert second.exit_code == 2
    assert "--replace" in second.output
    assert "What went wrong:" in second.output
    assert old.removed == []
    assert len(fake_runner.argvs("docker", "run")) == 1

    third = CliRunner().invoke(image_group, args + ["--replace"])
    assert third.exit_code == 0, third.output
    assert old.removed == [{"force": True, "v": False}]
    assert len(fake_runner.argvs("docker", "run")) == 2
