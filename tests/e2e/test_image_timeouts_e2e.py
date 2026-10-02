"""E2E: a slow build is cut off by --build-timeout (exit 5, under 5 s)."""

import time

import pytest
from click.testing import CliRunner

from iris_devtester.cli.image import image_group, runner

pytestmark = pytest.mark.e2e


@pytest.mark.skipif(not __import__("shutil").which("sleep"), reason="needs sleep(1)")
def test_slow_build_times_out(monkeypatch, installer_kit, elf_arm64):
    real = runner.run_build

    def slow(argv, timeout, on_line=None, **kw):
        return real(["sleep", "30"], timeout, on_line=on_line)

    monkeypatch.setattr(runner, "run_build", slow)
    start = time.monotonic()
    res = CliRunner().invoke(
        image_group,
        [
            "build", str(installer_kit), "--platform", "linux/arm64",
            "--iris-main", str(elf_arm64), "--build-timeout", "1", "--no-start",
        ],
    )  # fmt: skip
    elapsed = time.monotonic() - start
    assert res.exit_code == 5, res.output
    assert elapsed < 5
    for part in ("What went wrong:", "Why it matters:", "How to fix it:"):
        assert part in res.output
    assert "Unexpected error" not in res.output
