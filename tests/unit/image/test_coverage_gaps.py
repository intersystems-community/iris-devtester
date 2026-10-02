"""Small branch tests that keep ``iris_devtester/cli/image`` above 95% coverage."""

import platform as _platform
import shutil
import subprocess
import tarfile
from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import collision, image_group, runner
from iris_devtester.cli.image.iris_main import _find_container_with_iris_main
from iris_devtester.cli.image.license import LicenseResolution
from iris_devtester.cli.image.load import _is_installer_kit


def _cp(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, out, err)


@pytest.mark.parametrize(
    "machine,expected",
    [("arm64", "linux/arm64"), ("aarch64", "linux/arm64"), ("x86_64", "linux/amd64")],
)
def test_default_platform_follows_host(
    monkeypatch, fake_runner, installer_kit, elf_arm64, elf_amd64, machine, expected
):
    monkeypatch.setattr(_platform, "machine", lambda: machine)
    main = elf_arm64 if expected.endswith("arm64") else elf_amd64
    res = CliRunner().invoke(
        image_group, ["build", str(installer_kit), "--iris-main", str(main), "--no-start"]
    )
    assert res.exit_code == 0, res.output
    assert f"Platform: {expected}" in res.output
    assert expected in fake_runner.build_calls[0]["argv"]


def test_build_from_container_source_cleans_temp_dir(fake_runner, installer_kit, elf_arm64):
    seen = []

    def cp(argv):
        seen.append(argv[-1])
        shutil.copy(elf_arm64, argv[-1])
        return _cp()

    fake_runner.script(["docker", "cp"], cp)
    res = CliRunner().invoke(
        image_group,
        ["build", str(installer_kit), "--platform", "linux/arm64",
         "--iris-main-container", "src1", "--no-start"],
    )  # fmt: skip
    assert res.exit_code == 0, res.output
    import os

    assert seen and not os.path.exists(os.path.dirname(seen[0]))


def test_corrupt_tarball_is_not_an_installer_kit(tmp_path):
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(b"not a tarball")
    assert _is_installer_kit(bad) is False


def test_plain_docker_archive_is_not_an_installer_kit(image_archive):
    assert _is_installer_kit(image_archive) is False


def test_installer_kit_with_top_level_irisinstall(tmp_path):
    kit = tmp_path / "k.tar.gz"
    src = tmp_path / "irisinstall"
    src.write_text("x")
    with tarfile.open(kit, "w:gz") as tf:
        tf.add(src, arcname="irisinstall")
    assert _is_installer_kit(kit) is True


def test_image_of_falls_back_to_label_then_unknown():
    class Broken:
        @property
        def image(self):
            raise RuntimeError("image gone")

        labels = {"io.iris-devtester.image": "lab:1"}

    assert collision._image_of(Broken()) == "lab:1"

    class Broken2:
        @property
        def image(self):
            raise RuntimeError

        @property
        def labels(self):
            raise RuntimeError

    assert collision._image_of(Broken2()) == "unknown image"


def test_find_container_skips_blank_and_failed_copy(fake_runner, tmp_path):
    fake_runner.script(["docker", "ps"], _cp(0, "\nbroken\n"))
    fake_runner.script(["docker", "exec"], _cp(0))
    fake_runner.script(["docker", "cp"], _cp(1, "", "boom"))
    assert _find_container_with_iris_main("linux/arm64", tmp_path) is None


def test_license_describe_without_key():
    assert LicenseResolution(None, None).describe() == "no license key"


def test_terminate_tree_windows_oserror(monkeypatch):
    import os

    def bad_kill():
        raise OSError("gone")

    monkeypatch.setattr(os, "name", "nt")
    runner._terminate_tree(SimpleNamespace(kill=bad_kill, pid=1))  # swallowed


def test_run_build_kills_leftover_process_on_reader_error():
    def boom(line):
        raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError):
        runner.run_build(["sh", "-c", "echo hi; exec sleep 30"], timeout=30, on_line=boom)


def test_wrapper_passes_abort_through():
    from iris_devtester.cli.image.common import run_image_command

    @click.command()
    def cmd():
        def abort():
            raise click.Abort()

        run_image_command(abort)

    assert CliRunner().invoke(cmd, []).exit_code == 1


def test_wrapper_system_exit_passes_through():
    from iris_devtester.cli.image.common import run_image_command

    @click.command()
    def cmd():
        def leave():
            raise SystemExit(7)

        run_image_command(leave)

    assert CliRunner().invoke(cmd, []).exit_code == 7
