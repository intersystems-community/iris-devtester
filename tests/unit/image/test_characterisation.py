"""Characterisation tests: each pins a defect of the pre-hardening commands.

They run against ``iris_devtester.cli.image_commands`` with only global
``subprocess`` and ``docker.from_env`` faked.  Each was strict-xfail until its
fix landed; they are now regular regression tests.
"""

import subprocess
import time

import docker
import pytest
from click.testing import CliRunner

from iris_devtester.cli.image_commands import image_group


class _SlowPopen:
    """Popen stand-in whose stdout trickles for ~3 s."""

    def __init__(self, *a, **k):
        self.returncode = 0
        self.stdout = self._gen()

    @staticmethod
    def _gen():
        for i in range(6):
            time.sleep(0.5)
            yield f"line {i}\n"

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return 0

    def kill(self):
        pass

    def terminate(self):
        pass


class _FakeContainer:
    status = "running"
    labels: dict = {}


class _FakeClient:
    class containers:  # noqa: N801
        @staticmethod
        def get(name):
            if getattr(_FakeClient, "started", False):
                return _FakeContainer()
            raise docker.errors.NotFound("nope")


def _completed(rc=0, out=""):
    return subprocess.CompletedProcess([], rc, out, "")


@pytest.fixture
def plain_world(monkeypatch, tmp_path):
    """Patch subprocess.run and docker so start-up 'succeeds' instantly."""
    _FakeClient.started = False

    def fake_run(argv, *a, **k):
        if argv[:2] == ["docker", "load"]:
            return _completed(out="Loaded image: iris-test:1\n")
        if argv[:3] == ["docker", "run", "-d"]:
            _FakeClient.started = True
        return _completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(docker, "from_env", lambda *a, **k: _FakeClient)
    from iris_devtester.utils import health_checks, password

    waits = []
    monkeypatch.setattr(
        health_checks,
        "wait_for_healthy",
        lambda c, timeout=60, progress_callback=None: waits.append(timeout),
    )
    monkeypatch.setattr(password, "unexpire_all_passwords", lambda *a, **k: (True, "ok"))
    monkeypatch.setattr(password, "reset_password", lambda **k: (True, "ok"))
    return waits


def _arm64_stub(tmp_path):
    hdr = bytearray(20)
    hdr[0:4] = b"\x7fELF"
    hdr[4], hdr[5], hdr[6] = 2, 1, 1
    hdr[18:20] = (0xB7).to_bytes(2, "little")
    p = tmp_path / "iris-main"
    p.write_bytes(bytes(hdr))
    return p


# Fixed in phase 3: --build-timeout is enforced.
def test_build_timeout_not_enforced(monkeypatch, tmp_path, installer_kit):
    real_popen = subprocess.Popen

    def slow_popen(argv, *a, **k):
        return real_popen(["sleep", "30"], *a, **k)

    monkeypatch.setattr(subprocess, "Popen", slow_popen)
    main = _arm64_stub(tmp_path)
    start = time.monotonic()
    result = CliRunner().invoke(
        image_group,
        [
            "build",
            str(installer_kit),
            "--platform",
            "linux/arm64",
            "--iris-main",
            str(main),
            "--no-start",
            "--build-timeout",
            "1",
        ],
    )
    assert result.exit_code == 5
    assert time.monotonic() - start < 5


# Fixed in phase 4: the password is masked by default.
def test_password_echoed_in_output(plain_world, image_archive):
    result = CliRunner().invoke(
        image_group, ["load", str(image_archive), "--password", "s3cretPw!"]
    )
    assert result.exit_code == 0
    assert "s3cretPw!" not in result.output


# Fixed in phase 3: --timeout is the health wait.
def test_health_wait_hardcoded_120(plain_world, monkeypatch, tmp_path, installer_kit):
    class _OkPopen(_SlowPopen):
        @staticmethod
        def _gen():
            yield "done\n"

    monkeypatch.setattr(subprocess, "Popen", _OkPopen)
    main = _arm64_stub(tmp_path)
    result = CliRunner().invoke(
        image_group,
        [
            "build",
            str(installer_kit),
            "--platform",
            "linux/arm64",
            "--iris-main",
            str(main),
            "--timeout",
            "30",
        ],
    )
    assert result.exit_code == 0, result.output
    assert plain_world == [30]


# Fixed structurally by the shared wrapper (phase 2); no longer xfail.
def test_timeout_expired_reported_as_unexpected_error(monkeypatch, image_archive):
    def boom(argv, *a, **k):
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(subprocess, "run", boom)
    result = CliRunner().invoke(image_group, ["load", str(image_archive)])
    assert "Unexpected error" not in result.output
    assert result.exit_code == 5
