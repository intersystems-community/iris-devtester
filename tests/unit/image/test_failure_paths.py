"""One test per failure path of ``load`` and ``build``: exit code + three-part message."""

import subprocess

from click.testing import CliRunner

from iris_devtester.cli.image import image_group

PARTS = ("What went wrong:", "Why it matters:", "How to fix it:")


def _fix_section(output):
    return output.split("How to fix it:", 1)[1]


def _assert_contract(res, code):
    assert res.exit_code == code, res.output
    for part in PARTS:
        assert part in res.output
    fix = _fix_section(res.output)
    assert any(tok in fix for tok in ("idt ", "docker ", "--")), fix


def _cp(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, out, err)


def _build(kit, main, *extra):
    return ["build", str(kit), "--platform", "linux/arm64", "--iris-main", str(main), *extra]


def test_installer_kit_to_load_points_at_build(fake_runner, installer_kit):
    res = CliRunner().invoke(image_group, ["load", str(installer_kit)])
    _assert_contract(res, 2)
    assert "idt image build" in res.output
    assert fake_runner.calls == []


def test_docker_run_failure(fake_runner, fake_docker, image_archive):
    fake_runner.script(["docker", "run"], _cp(125, "", "port is already allocated"))
    res = CliRunner().invoke(image_group, ["load", str(image_archive)])
    _assert_contract(res, 1)
    assert "port is already allocated" in res.output
    assert "--port" in res.output


def test_docker_load_failure(fake_runner, image_archive):
    fake_runner.script(["docker", "load"], _cp(1, "", "no space left on device"))
    res = CliRunner().invoke(image_group, ["load", str(image_archive)])
    _assert_contract(res, 1)
    assert "no space left on device" in res.output


def test_no_image_tag_in_archive(fake_runner, image_archive):
    fake_runner.script(["docker", "load"], _cp(0, "nothing useful\n"))
    res = CliRunner().invoke(image_group, ["load", str(image_archive)])
    _assert_contract(res, 1)
    assert "no image tag" in res.output.lower()


def test_docker_build_failure(fake_runner, installer_kit, elf_arm64):
    fake_runner.build_rc = 1
    fake_runner.build_lines = ["ERROR: step 4 failed"]
    res = CliRunner().invoke(image_group, _build(installer_kit, elf_arm64, "--no-start"))
    _assert_contract(res, 1)
    assert "ERROR: step 4 failed" in res.output
    assert "--keep-build-dir" in res.output


def test_missing_iris_main(fake_runner, installer_kit):
    res = CliRunner().invoke(
        image_group, ["build", str(installer_kit), "--platform", "linux/arm64", "--no-start"]
    )
    _assert_contract(res, 2)
    assert "iris-main" in res.output
    assert "docker cp" in res.output


def test_catch_all(fake_runner, installer_kit, elf_arm64):
    fake_runner.build_exc = KeyError("boom")
    res = CliRunner().invoke(image_group, _build(installer_kit, elf_arm64, "--no-start"))
    _assert_contract(res, 1)
    assert "Unexpected error" in res.output
    assert "--keep-build-dir" in res.output


def test_no_raw_traceback(fake_runner, image_archive):
    fake_runner.script(["docker", "load"], _cp(1, "", "boom"))
    res = CliRunner().invoke(image_group, ["load", str(image_archive)])
    assert "Traceback" not in res.output


def test_container_exits_during_health_wait(
    fake_runner, fake_docker, fake_health, fake_password, image_archive
):
    fake_health.exc = RuntimeError("Container failed to start (status: exited)")
    res = CliRunner().invoke(image_group, ["load", str(image_archive), "--name", "dies"])
    _assert_contract(res, 1)
    assert "docker logs dies" in res.output
    assert "Unexpected error" not in res.output
    assert "dies" in fake_docker.containers.store
