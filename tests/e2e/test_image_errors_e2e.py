"""E2E (CliRunner, faked Docker): happy path masks the password; installer kit fails exit 2."""

import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import image_group

pytestmark = pytest.mark.e2e


def test_load_archive_succeeds_with_masked_password(
    fake_runner, fake_docker, fake_health, fake_password, image_archive
):
    res = CliRunner().invoke(
        image_group, ["load", str(image_archive), "--name", "e2e-box", "--password", "Zx9-secret"]
    )
    assert res.exit_code == 0, res.output
    assert "Zx9-secret" not in res.output
    assert "********" in res.output
    assert "is ready" in res.output
    assert fake_docker.containers.store["e2e-box"].status == "running"


def test_load_installer_kit_fails_with_exit_2(fake_runner, installer_kit):
    res = CliRunner().invoke(image_group, ["load", str(installer_kit)])
    assert res.exit_code == 2
    assert "What went wrong:" in res.output
    assert "idt image build" in res.output
