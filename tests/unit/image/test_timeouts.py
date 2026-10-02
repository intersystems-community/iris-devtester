import re
import shutil
import subprocess
from pathlib import Path

from click.testing import CliRunner

from iris_devtester.cli.image import image_group, runner
from iris_devtester.cli.image.build import build_image
from iris_devtester.cli.image.load import load_image


def _build_args(kit, main, *extra):
    return ["build", str(kit), "--platform", "linux/arm64", "--iris-main", str(main), *extra]


def _opt(cmd, name):
    return next(p for p in cmd.params if name in p.opts)


# ---- options reach their phase -------------------------------------------------


def test_build_timeout_reaches_run_build_without_floor(fake_runner, installer_kit, elf_arm64):
    res = CliRunner().invoke(
        image_group, _build_args(installer_kit, elf_arm64, "--no-start", "--build-timeout", "60")
    )
    assert res.exit_code == 0, res.output
    assert fake_runner.build_calls[0]["timeout"] == 60


def test_load_timeout_reaches_run_docker_load(fake_runner, image_archive):
    res = CliRunner().invoke(
        image_group, ["load", str(image_archive), "--no-start", "--load-timeout", "42"]
    )
    assert res.exit_code == 0, res.output
    idx = fake_runner.calls.index(["docker", "load", "-i", str(image_archive)])
    assert fake_runner.timeouts[idx] == 42


def test_timeout_reaches_wait_for_healthy_on_load(
    fake_runner, fake_docker, fake_health, fake_password, image_archive
):
    res = CliRunner().invoke(image_group, ["load", str(image_archive), "--timeout", "77"])
    assert res.exit_code == 0, res.output
    assert fake_health.calls[0]["timeout"] == 77


def test_timeout_reaches_wait_for_healthy_on_build(
    fake_runner, fake_docker, fake_health, fake_password, installer_kit, elf_arm64
):
    res = CliRunner().invoke(image_group, _build_args(installer_kit, elf_arm64, "--timeout", "33"))
    assert res.exit_code == 0, res.output
    assert fake_health.calls[0]["timeout"] == 33


def test_defaults():
    assert _opt(build_image, "--build-timeout").default == 900
    assert _opt(build_image, "--timeout").default == 120
    assert _opt(load_image, "--load-timeout").default == 300
    assert _opt(load_image, "--timeout").default == 120


def test_help_text_names_phase():
    assert "build" in _opt(build_image, "--build-timeout").help.lower()
    assert "health" in _opt(build_image, "--timeout").help.lower()
    assert "load" in _opt(load_image, "--load-timeout").help.lower()
    assert "health" in _opt(load_image, "--timeout").help.lower()


# ---- messages -------------------------------------------------------------------


def test_build_timeout_message(fake_runner, installer_kit, elf_arm64):
    fake_runner.build_exc = runner.BuildTimeout("build", 60, 61.4, "Step 3/9 : RUN install")
    res = CliRunner().invoke(
        image_group, _build_args(installer_kit, elf_arm64, "--build-timeout", "60")
    )
    assert res.exit_code == 5
    for part in ("What went wrong:", "Why it matters:", "How to fix it:"):
        assert part in res.output
    assert "60" in res.output and "61" in res.output
    assert "Step 3/9 : RUN install" in res.output
    assert "--build-timeout" in res.output
    assert "Unexpected error" not in res.output


def test_load_timeout_message(fake_runner, image_archive):
    fake_runner.script(["docker", "load"], exc=subprocess.TimeoutExpired(["docker", "load"], 9))
    res = CliRunner().invoke(image_group, ["load", str(image_archive), "--load-timeout", "9"])
    assert res.exit_code == 5
    assert "docker images" in res.output
    assert "--load-timeout" in res.output
    assert "Unexpected error" not in res.output


def test_health_timeout_message_and_container_kept(
    fake_runner, fake_docker, fake_health, fake_password, image_archive
):
    fake_health.exc = TimeoutError("port not open")
    res = CliRunner().invoke(image_group, ["load", str(image_archive), "--name", "slowbox"])
    assert res.exit_code == 5
    assert "slowbox" in res.output
    assert "docker logs slowbox" in res.output
    assert "docker rm -f slowbox" in res.output
    assert "Unexpected error" not in res.output
    assert "slowbox" in fake_docker.containers.store  # not removed
    assert fake_docker.containers.store["slowbox"].removed == []


def _context_dir(output):
    m = re.search(r"Build context: (\S+)", output)
    assert m, output
    return Path(m.group(1))


def test_build_dir_removed_on_timeout(fake_runner, installer_kit, elf_arm64):
    fake_runner.build_exc = runner.BuildTimeout("build", 1, 1.0, "x")
    res = CliRunner().invoke(
        image_group, _build_args(installer_kit, elf_arm64, "--build-timeout", "1")
    )
    assert res.exit_code == 5
    assert not _context_dir(res.output).exists()


def test_build_dir_kept_with_flag(fake_runner, installer_kit, elf_arm64):
    fake_runner.build_exc = runner.BuildTimeout("build", 1, 1.0, "x")
    res = CliRunner().invoke(
        image_group,
        _build_args(installer_kit, elf_arm64, "--build-timeout", "1", "--keep-build-dir"),
    )
    kept = _context_dir(res.output)
    try:
        assert res.exit_code == 5
        assert kept.exists()
    finally:
        shutil.rmtree(kept, ignore_errors=True)
