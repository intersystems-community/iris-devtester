import click
import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import common, runner
from iris_devtester.cli.image.errors import ImageCommandError
from iris_devtester.cli.image.options import StartOptions


def _invoke(fn, secrets=()):
    @click.command()
    def cmd():
        common.run_image_command(fn, secrets=secrets)

    return CliRunner().invoke(cmd, [])


def test_success_exits_zero():
    assert _invoke(lambda: None).exit_code == 0


def test_renders_image_command_error_once_and_uses_its_code():
    def boom():
        raise ImageCommandError("bad thing", "matters", "do this", exit_code=2)

    res = _invoke(boom)
    assert res.exit_code == 2
    assert res.output.count("What went wrong:") == 1
    assert "bad thing" in res.output


@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("slow"),
        runner.BuildTimeout("build", 1, 2.0, "x"),
        runner.LoadTimeout("load", 1, 2.0),
    ],
)
def test_timeouts_exit_5_without_unexpected_error(exc):
    def boom():
        raise exc

    res = _invoke(boom)
    assert res.exit_code == 5
    assert "Unexpected error" not in res.output
    assert "How to fix it:" in res.output


def test_subprocess_timeout_exit_5():
    import subprocess

    def boom():
        raise subprocess.TimeoutExpired(["docker"], 3)

    res = _invoke(boom)
    assert res.exit_code == 5
    assert "Unexpected error" not in res.output


def test_unknown_exception_exits_1_with_guidance():
    def boom():
        raise KeyError("weird")

    res = _invoke(boom)
    assert res.exit_code == 1
    assert "--keep-build-dir" in res.output
    assert "issue" in res.output.lower()


def test_secrets_are_masked_in_unknown_errors():
    def boom():
        raise RuntimeError("could not use s3cretPw")

    res = _invoke(boom, secrets=["s3cretPw"])
    assert "s3cretPw" not in res.output


def test_click_exceptions_pass_through():
    def boom():
        raise click.UsageError("bad usage")

    res = _invoke(boom)
    assert res.exit_code == 2
    assert "bad usage" in res.output


def test_exit_passes_through():
    def leave():
        raise click.exceptions.Exit(0)

    assert _invoke(leave).exit_code == 0


def test_no_start_hint_prints_docker_run(capsys):
    opts = StartOptions(name="n1", superserver_port=1972, web_port=52773, password="SYS")
    common.print_manual_start_hint("img:1", opts)
    out = capsys.readouterr().out
    assert "To start manually" in out
    assert "docker run -d --name n1 -p 1972:1972" in out
    assert out.strip().endswith("img:1")


def test_derive_name_from_tarball(tmp_path):
    p = tmp_path / "IRIS-2026.2.0AI.127.0-docker.tar.gz"
    assert common.derive_name_from_tarball(p) == "iris-2026-2-0ai-127-0-docker"
    long = tmp_path / ("a" * 60 + ".tar.gz")
    assert len(common.derive_name_from_tarball(long)) <= 40
