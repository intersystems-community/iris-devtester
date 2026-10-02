import shutil
import subprocess

import pytest

from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.iris_main import PUBLIC_IMAGE, extract_from_image, resolve_iris_main


def _cp(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, out, err)


def _copier(src):
    def _do(argv):
        shutil.copy(src, argv[-1])
        return _cp()

    return _do


def test_extract_runs_create_cp_rm(fake_runner, elf_arm64, tmp_path):
    fake_runner.script(["docker", "cp"], _copier(elf_arm64))
    dest = tmp_path / "out" / "iris-main"
    dest.parent.mkdir()
    extract_from_image("some/image:1", "linux/arm64", dest)
    assert fake_runner.calls == [
        ["docker", "create", "--platform", "linux/arm64", "some/image:1"],
        ["docker", "cp", "cid123:/iris-main", str(dest)],
        ["docker", "rm", "cid123"],
    ]
    assert dest.exists()


def test_rm_runs_when_cp_fails(fake_runner, tmp_path):
    fake_runner.script(["docker", "cp"], _cp(1, "", "Could not find the file /iris-main"))
    with pytest.raises(ImageCommandError) as ei:
        extract_from_image("some/image:1", "linux/arm64", tmp_path / "iris-main")
    assert ei.value.exit_code == 2
    assert "/iris-main" in ei.value.what
    assert fake_runner.argvs("docker", "rm") == [["docker", "rm", "cid123"]]


def test_create_failure_has_no_rm(fake_runner, tmp_path):
    fake_runner.script(["docker", "create"], _cp(1, "", "pull access denied"))
    with pytest.raises(ImageCommandError) as ei:
        extract_from_image("some/image:1", "linux/arm64", tmp_path / "iris-main")
    assert ei.value.exit_code == 1
    assert "pull access denied" in ei.value.what
    assert fake_runner.argvs("docker", "rm") == []


def test_resolve_image_checks_arch_and_cleans_up_on_mismatch(fake_runner, elf_amd64):
    fake_runner.script(["docker", "cp"], _copier(elf_amd64))
    with pytest.raises(ImageCommandError) as ei:
        resolve_iris_main(image="some/image:1", platform="linux/arm64", env={}, echo=lambda m: None)
    assert ei.value.exit_code == 2
    assert fake_runner.argvs("docker", "rm")  # temp container removed


def test_version_mismatch_warns_and_continues(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp"], _copier(elf_arm64))
    lines = []
    res = resolve_iris_main(
        image="repo/iris:2025.1.0",
        platform="linux/arm64",
        env={},
        kit_name="IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz",
        echo=lines.append,
    )
    res.cleanup()
    text = "\n".join(lines).lower()
    assert "warning" in text or "⚠" in text
    assert "2025.1" in text and "2026.3" in text


def test_matching_version_is_silent(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp"], _copier(elf_arm64))
    lines = []
    res = resolve_iris_main(
        image="repo/iris:2026.3.0",
        platform="linux/arm64",
        env={},
        kit_name="IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz",
        echo=lines.append,
    )
    res.cleanup()
    assert "⚠" not in "\n".join(lines)


def test_container_version_mismatch_warns(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp", "c1:/iris-main"], _copier(elf_arm64))
    fake_runner.script(
        ["docker", "exec", "c1", "/iris-main", "--version"], _cp(0, "iris-main 2024.1.2\n")
    )
    lines = []
    res = resolve_iris_main(
        container="c1",
        platform="linux/arm64",
        env={},
        kit_name="IRIS-2026.3.0AI.1.0.tar.gz",
        echo=lines.append,
    )
    res.cleanup()
    assert any("⚠" in line for line in lines)


def test_unparseable_version_is_ignored(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp", "c1:/iris-main"], _copier(elf_arm64))
    fake_runner.script(["docker", "exec", "c1", "/iris-main", "--version"], _cp(1, "", "nope"))
    lines = []
    res = resolve_iris_main(
        container="c1",
        platform="linux/arm64",
        env={},
        kit_name="K-2026.3.tar.gz",
        echo=lines.append,
    )
    res.cleanup()
    assert not any("⚠" in line for line in lines)


def test_cleanup_removes_temp_dir(fake_runner, elf_arm64):
    fake_runner.script(["docker", "cp"], _copier(elf_arm64))
    res = resolve_iris_main(
        image="repo/iris:1", platform="linux/arm64", env={}, echo=lambda m: None
    )
    parent = res.path.parent
    assert parent.exists()
    res.cleanup()
    assert not parent.exists()


def test_public_image_constant():
    assert PUBLIC_IMAGE.endswith("iris-community:latest-preview")
