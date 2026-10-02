import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import image_group, runner
from iris_devtester.cli.image.build import render_dockerfile, write_build_context

SENTINEL = "SENTINEL-LICENSE-TEXT-123"


@pytest.fixture
def key_file(tmp_path):
    p = tmp_path / "keys" / "iris.key"
    p.parent.mkdir()
    p.write_text(SENTINEL)
    return p


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("IRIS_LICENSE_KEY", raising=False)
    monkeypatch.chdir(tmp_path)


def _args(kit, main, *extra):
    return ["build", str(kit), "--platform", "linux/arm64", "--iris-main", str(main), *extra]


def test_write_build_context_has_no_key(tmp_path, installer_kit, elf_arm64):
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    write_build_context(ctx, installer_kit, elf_arm64)
    assert sorted(p.name for p in ctx.iterdir()) == ["Dockerfile", "iris-main", "iris.kit.tar.gz"]
    assert "iris.key" not in (ctx / "Dockerfile").read_text()


def test_dockerfile_has_no_key_copy():
    text = render_dockerfile()
    assert "iris.key" not in text
    assert "COPY" in text  # kit and iris-main copies remain


def test_cli_context_excludes_key_even_when_license_given(
    fake_runner, installer_kit, elf_arm64, key_file, monkeypatch
):
    snaps = []
    inner = fake_runner.run_build

    def spy(argv, timeout, on_line=None, **kw):
        ctx = Path(argv[-1])
        snaps.append(
            {
                "files": sorted(os.listdir(ctx)),
                "dockerfile": (ctx / "Dockerfile").read_text(),
                "blob": b"".join((ctx / f).read_bytes() for f in os.listdir(ctx)),
            }
        )
        return inner(argv, timeout, on_line=on_line, **kw)

    monkeypatch.setattr(runner, "run_build", spy)
    res = CliRunner().invoke(
        image_group, _args(installer_kit, elf_arm64, "--license", str(key_file), "--no-start")
    )
    assert res.exit_code == 0, res.output
    assert "iris.key" not in snaps[0]["files"]
    assert "iris.key" not in snaps[0]["dockerfile"]
    assert SENTINEL.encode() not in snaps[0]["blob"]


def test_docker_run_mounts_key_read_only(
    fake_runner, fake_docker, fake_health, fake_password, installer_kit, elf_arm64, key_file
):
    res = CliRunner().invoke(
        image_group, _args(installer_kit, elf_arm64, "--license", str(key_file), "--name", "lic")
    )
    assert res.exit_code == 0, res.output
    (argv,) = fake_runner.argvs("docker", "run")
    assert "-v" in argv
    assert argv[argv.index("-v") + 1] == f"{key_file.resolve()}:/usr/irissys/mgr/iris.key:ro"


def test_no_mount_without_key(
    fake_runner, fake_docker, fake_health, fake_password, installer_kit, elf_arm64
):
    res = CliRunner().invoke(image_group, _args(installer_kit, elf_arm64, "--name", "nolic"))
    assert res.exit_code == 0, res.output
    (argv,) = fake_runner.argvs("docker", "run")
    assert "-v" not in argv
    assert "No license key" in res.output or "no license key" in res.output.lower()


def test_cwd_key_is_used_and_reported(
    fake_runner, fake_docker, fake_health, fake_password, installer_kit, elf_arm64, tmp_path
):
    (tmp_path / "iris.key").write_text(SENTINEL)
    res = CliRunner().invoke(image_group, _args(installer_kit, elf_arm64, "--name", "cwdlic"))
    assert res.exit_code == 0, res.output
    assert str((tmp_path / "iris.key").resolve()) in res.output
    (argv,) = fake_runner.argvs("docker", "run")
    assert f"{(tmp_path / 'iris.key').resolve()}:/usr/irissys/mgr/iris.key:ro" in argv


def test_env_key_is_used(
    fake_runner, fake_docker, fake_health, fake_password, installer_kit, elf_arm64, key_file
):
    res = CliRunner().invoke(
        image_group,
        _args(installer_kit, elf_arm64, "--name", "envlic"),
        env={"IRIS_LICENSE_KEY": str(key_file)},
    )
    assert res.exit_code == 0, res.output
    (argv,) = fake_runner.argvs("docker", "run")
    assert f"{key_file.resolve()}:/usr/irissys/mgr/iris.key:ro" in argv


def test_manual_start_hint_includes_mount(fake_runner, installer_kit, elf_arm64, key_file):
    res = CliRunner().invoke(
        image_group, _args(installer_kit, elf_arm64, "--license", str(key_file), "--no-start")
    )
    assert res.exit_code == 0, res.output
    assert f"-v {key_file.resolve()}:/usr/irissys/mgr/iris.key:ro" in res.output


def test_explicit_missing_license_exits_2(fake_runner, installer_kit, elf_arm64, tmp_path):
    res = CliRunner().invoke(
        image_group, _args(installer_kit, elf_arm64, "--license", str(tmp_path / "gone.key"))
    )
    assert res.exit_code == 2
    assert "What went wrong:" in res.output
    assert fake_runner.build_calls == []
