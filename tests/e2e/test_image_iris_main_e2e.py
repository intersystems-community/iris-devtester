"""E2E (CliRunner, faked Docker): the iris-main architecture gate runs before any build."""

import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import image_group

pytestmark = pytest.mark.e2e


def _args(kit, main, platform="linux/amd64"):
    return ["build", str(kit), "--platform", platform, "--iris-main", str(main), "--no-start"]


def test_arch_mismatch_exits_2_before_build_dir(fake_runner, installer_kit, elf_arm64):
    res = CliRunner().invoke(image_group, _args(installer_kit, elf_arm64))
    assert res.exit_code == 2, res.output
    assert "Build context" not in res.output
    assert fake_runner.build_calls == []
    assert "arm64" in res.output and "amd64" in res.output
    assert "docker create --platform linux/amd64" in res.output


def test_matching_arch_proceeds_to_docker_build(fake_runner, installer_kit, elf_amd64):
    res = CliRunner().invoke(image_group, _args(installer_kit, elf_amd64))
    assert res.exit_code == 0, res.output
    assert len(fake_runner.build_calls) == 1
    assert fake_runner.build_calls[0]["argv"][:2] == ["docker", "build"]


def test_env_var_source_used(fake_runner, installer_kit, elf_amd64):
    res = CliRunner().invoke(
        image_group,
        ["build", str(installer_kit), "--platform", "linux/amd64", "--no-start"],
        env={"IDT_IRIS_MAIN": str(elf_amd64)},
    )
    assert res.exit_code == 0, res.output
    assert "IDT_IRIS_MAIN" in res.output
