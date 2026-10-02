import shutil
import subprocess

import pytest

from iris_devtester.cli.image import iris_main
from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.iris_main import (
    PUBLIC_IMAGE,
    _find_container_with_iris_main,
    resolve_iris_main,
)


def _cp(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, out, err)


def _copier(src):
    """Scripted ``docker cp`` that drops ``src`` at the destination argument."""

    def _do(argv):
        shutil.copy(src, argv[-1])
        return _cp()

    return _do


def _resolve(lines, **kw):
    kw.setdefault("platform", "linux/arm64")
    kw.setdefault("env", {})
    return resolve_iris_main(echo=lines.append, **kw)


def test_option_beats_env(elf_arm64, elf_amd64):
    lines = []
    res = _resolve(lines, option=str(elf_arm64), env={"IDT_IRIS_MAIN": str(elf_amd64)})
    assert res.path == elf_arm64
    assert res.source == "option"
    assert any("--iris-main" in line for line in lines)


def test_env_used_when_no_option(elf_arm64):
    lines = []
    res = _resolve(lines, env={"IDT_IRIS_MAIN": str(elf_arm64)})
    assert res.path == elf_arm64
    assert res.source == "env"
    assert any("IDT_IRIS_MAIN" in line for line in lines)


def test_missing_env_path_exits_2(tmp_path):
    with pytest.raises(ImageCommandError) as ei:
        _resolve([], env={"IDT_IRIS_MAIN": str(tmp_path / "gone")})
    assert ei.value.exit_code == 2
    assert "IDT_IRIS_MAIN" in ei.value.what


def test_missing_option_path_exits_2(tmp_path):
    with pytest.raises(ImageCommandError) as ei:
        _resolve([], option=str(tmp_path / "gone"))
    assert ei.value.exit_code == 2


def test_option_arch_is_checked(elf_amd64):
    with pytest.raises(ImageCommandError) as ei:
        _resolve([], option=str(elf_amd64), platform="linux/arm64")
    assert ei.value.exit_code == 2


def test_container_source(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp", "mycont:/iris-main"], _copier(elf_arm64))
    lines = []
    res = _resolve(lines, container="mycont")
    try:
        assert res.source == "container mycont"
        assert res.path.read_bytes() == elf_arm64.read_bytes()
        assert res.arch == "arm64"
        assert any("mycont" in line for line in lines)
    finally:
        res.cleanup()
    assert not res.path.exists()


def test_container_cp_failure(fake_runner):
    fake_runner.script(["docker", "cp"], _cp(1, "", "no such container"))
    with pytest.raises(ImageCommandError) as ei:
        _resolve([], container="mycont")
    assert "no such container" in ei.value.what


def test_container_beats_image(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp", "mycont:/iris-main"], _copier(elf_arm64))
    res = _resolve([], container="mycont", image="some/image:1")
    res.cleanup()
    assert fake_runner.argvs("docker", "create") == []


def test_image_beats_autodetect(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp", "cid123:/iris-main"], _copier(elf_arm64))
    res = _resolve([], image="some/image:1")
    res.cleanup()
    assert res.source == "image some/image:1"
    assert fake_runner.argvs("docker", "ps") == []


def test_autodetect_skips_wrong_architecture(fake_runner, elf_arm64, elf_amd64):
    fake_runner.script(["docker", "ps"], _cp(0, "wrong\nright\n"))
    fake_runner.script(["docker", "exec"], _cp(0))

    def cp(argv):
        src = elf_arm64 if argv[2].startswith("wrong:") else elf_amd64
        shutil.copy(src, argv[-1])
        return _cp()

    fake_runner.script(["docker", "cp"], cp)
    lines = []
    res = _resolve(lines, platform="linux/amd64")
    try:
        assert res.source == "auto-detected container right"
        assert res.arch == "amd64"
    finally:
        res.cleanup()


def test_autodetect_skips_containers_without_iris_main(fake_runner, elf_arm64):
    fake_runner.script(["docker", "ps"], _cp(0, "plain\nirisbox\n"))
    fake_runner.script(["docker", "exec", "plain"], _cp(1))
    fake_runner.script(["docker", "exec", "irisbox"], _cp(0))
    fake_runner.script(["docker", "cp"], _copier(elf_arm64))
    res = _resolve([])
    res.cleanup()
    assert res.source == "auto-detected container irisbox"


def test_helper_name_and_return(fake_runner, elf_arm64, tmp_path):
    fake_runner.script(["docker", "ps"], _cp(0, "irisbox\n"))
    fake_runner.script(["docker", "exec"], _cp(0))
    fake_runner.script(["docker", "cp"], _copier(elf_arm64))
    found = _find_container_with_iris_main("linux/arm64", tmp_path)
    assert found is not None
    name, path = found
    assert name == "irisbox"
    assert path.read_bytes() == elf_arm64.read_bytes()


def test_helper_returns_none_when_docker_ps_fails(fake_runner, tmp_path):
    fake_runner.script(["docker", "ps"], _cp(1))
    assert _find_container_with_iris_main("linux/arm64", tmp_path) is None


def test_nothing_found_gives_exact_commands(fake_runner):
    fake_runner.script(["docker", "ps"], _cp(0, ""))
    with pytest.raises(ImageCommandError) as ei:
        _resolve([], platform="linux/amd64")
    err = ei.value
    assert err.exit_code == 2
    assert f"docker create --platform linux/amd64 --name idt-iris-main {PUBLIC_IMAGE}" in err.fix
    assert "docker cp idt-iris-main:/iris-main" in err.fix
    assert "docker rm idt-iris-main" in err.fix
    assert PUBLIC_IMAGE == "containers.intersystems.com/intersystems/iris-community:latest-preview"


def test_module_exposes_ordering_doc():
    assert "IDT_IRIS_MAIN" in iris_main.__doc__
