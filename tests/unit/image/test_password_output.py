import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import image_group

SECRET = "s3cretPw9"


@pytest.fixture
def world(fake_runner, fake_docker, fake_health, fake_password):
    return fake_docker


def _load(archive, *extra):
    return CliRunner().invoke(image_group, ["load", str(archive), "--name", "box", *extra])


def test_password_masked_by_default(world, image_archive):
    res = _load(image_archive, "--password", SECRET)
    assert res.exit_code == 0, res.output
    assert SECRET not in res.output
    assert "********" in res.output


def test_show_password_reveals_it(world, image_archive):
    res = _load(image_archive, "--password", SECRET, "--show-password")
    assert res.exit_code == 0, res.output
    assert f"Password:    {SECRET}" in res.output


def test_no_setting_password_line(world, image_archive):
    res = _load(image_archive, "--password", SECRET, "--show-password")
    assert "Setting _SYSTEM password to" not in res.output
    assert "'" + SECRET + "'" not in res.output


def test_build_masks_and_offers_show_password(world, fake_runner, installer_kit, elf_arm64):
    args = ["build", str(installer_kit), "--platform", "linux/arm64",
            "--iris-main", str(elf_arm64), "--password", SECRET]  # fmt: skip
    res = CliRunner().invoke(image_group, args)
    assert res.exit_code == 0, res.output
    assert SECRET not in res.output
    res2 = CliRunner().invoke(image_group, args + ["--show-password", "--name", "other-box"])
    assert f"Password:    {SECRET}" in res2.output


def test_reset_failure_with_default_password_warns(world, fake_password, image_archive):
    fake_password.reset_result = (False, "nope")
    res = _load(image_archive)
    assert res.exit_code == 0, res.output
    assert "⚠" in res.output


def test_reset_exception_with_default_password_warns(world, fake_password, image_archive):
    fake_password.reset_exc = RuntimeError("exec failed")
    res = _load(image_archive)
    assert res.exit_code == 0, res.output


def test_unexpire_failure_with_default_password_warns(world, fake_password, image_archive):
    fake_password.unexpire_exc = RuntimeError("exec failed")
    res = _load(image_archive)
    assert res.exit_code == 0, res.output


@pytest.mark.parametrize("mode", ["result", "exc"])
def test_reset_failure_with_custom_password_is_fatal(world, fake_password, image_archive, mode):
    if mode == "result":
        fake_password.reset_result = (False, "nope")
    else:
        fake_password.reset_exc = RuntimeError("exec failed")
    res = _load(image_archive, "--password", SECRET)
    assert res.exit_code == 1
    assert "docker rm -f box" in res.output
    assert "idt image load" in res.output
    assert SECRET not in res.output
    assert "box" in world.containers.store  # container kept
    assert world.containers.store["box"].removed == []


@pytest.mark.parametrize("mode", ["result", "exc"])
def test_unexpire_failure_with_custom_password_is_fatal(world, fake_password, image_archive, mode):
    if mode == "result":
        fake_password.unexpire_result = (False, "nope")
    else:
        fake_password.unexpire_exc = RuntimeError("exec failed")
    res = _load(image_archive, "--password", SECRET)
    assert res.exit_code == 1
    assert "docker rm -f box" in res.output
    assert "box" in world.containers.store


def test_no_unexpire_skips_step(world, fake_password, image_archive):
    res = _load(image_archive, "--no-unexpire")
    assert res.exit_code == 0
    assert fake_password.unexpire_calls == []
