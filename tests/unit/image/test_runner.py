import os
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from iris_devtester.cli.image import runner
from iris_devtester.cli.image.options import StartOptions


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_run_build_streams_lines():
    lines = []
    res = runner.run_build(["sh", "-c", "echo a; echo b"], timeout=10, on_line=lines.append)
    assert lines == ["a", "b"]
    assert res.returncode == 0
    assert res.last_line == "b"


def test_run_build_reports_nonzero_rc():
    res = runner.run_build(["sh", "-c", "echo oops; exit 3"], timeout=10)
    assert res.returncode == 3
    assert res.last_line == "oops"


@pytest.mark.skipif(os.name == "nt", reason="process groups are posix only")
def test_run_build_timeout_kills_tree():
    pids = []

    def on_line(line):
        if line.isdigit():
            pids.append(int(line))

    start = time.monotonic()
    with pytest.raises(runner.BuildTimeout) as ei:
        runner.run_build(
            ["sh", "-c", "sleep 30 & echo $!; wait"],
            timeout=1,
            on_line=on_line,
        )
    assert time.monotonic() - start < 5
    assert ei.value.limit == 1
    assert ei.value.elapsed >= 1
    assert pids
    for _ in range(20):
        if not _alive(pids[0]):
            break
        time.sleep(0.1)
    assert not _alive(pids[0])
    # the process group itself is gone
    with pytest.raises(ProcessLookupError):
        os.killpg(os.getpgid(pids[0]), 0)


@pytest.mark.skipif(os.name == "nt", reason="process groups are posix only")
def test_run_build_sigkill_after_grace_when_sigterm_ignored(monkeypatch):
    monkeypatch.setattr(runner, "KILL_GRACE", 1)
    start = time.monotonic()
    with pytest.raises(runner.BuildTimeout):
        runner.run_build(
            ["sh", "-c", "trap '' TERM; echo ready; sleep 30"],
            timeout=1,
        )
    elapsed = time.monotonic() - start
    assert 1.5 <= elapsed < 6


def test_build_timeout_carries_last_line():
    with pytest.raises(runner.BuildTimeout) as ei:
        runner.run_build(["sh", "-c", "echo last words; exec sleep 30"], timeout=1)
    assert ei.value.last_line == "last words"
    assert isinstance(ei.value, TimeoutError)


def test_terminate_tree_windows_branch(monkeypatch):
    killed = []
    proc = SimpleNamespace(kill=lambda: killed.append(True), pid=1)
    monkeypatch.setattr(os, "name", "nt")
    runner._terminate_tree(proc, signal.SIGTERM)
    assert killed == [True]


def test_terminate_tree_posix_uses_killpg(monkeypatch):
    calls = []
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(os, "getpgid", lambda pid: 4242)
    monkeypatch.setattr(os, "killpg", lambda pg, sig: calls.append((pg, sig)))
    runner._terminate_tree(SimpleNamespace(pid=7), signal.SIGTERM)
    assert calls == [(4242, signal.SIGTERM)]


def test_terminate_tree_ignores_vanished_process(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")

    def gone(pid):
        raise ProcessLookupError

    monkeypatch.setattr(os, "getpgid", gone)
    runner._terminate_tree(SimpleNamespace(pid=7), signal.SIGTERM)  # no raise


def test_run_docker_load_returns_result(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return subprocess.CompletedProcess(argv, 0, "Loaded image: x:1\n", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    res = runner.run_docker_load("/tmp/a.tar", timeout=12)
    assert seen["argv"] == ["docker", "load", "-i", "/tmp/a.tar"]
    assert seen["kw"]["timeout"] == 12
    assert res.stdout.startswith("Loaded")


def test_run_docker_load_timeout(monkeypatch):
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    with pytest.raises(runner.LoadTimeout) as ei:
        runner.run_docker_load("/tmp/a.tar", timeout=7)
    assert ei.value.limit == 7
    assert isinstance(ei.value, TimeoutError)


def _opts(**kw):
    base = dict(name="c1", superserver_port=1972, web_port=52773, password="SYS")
    base.update(kw)
    return StartOptions(**base)


def test_docker_run_argv_basic():
    argv = runner.docker_run_argv("img:1", _opts())
    assert argv == [
        "docker", "run", "-d", "--name", "c1",
        "-p", "1972:1972", "-p", "52773:52773", "img:1",
    ]  # fmt: skip


def test_docker_run_argv_options():
    argv = runner.docker_run_argv(
        "img:1",
        _opts(web_port=None, cap_ipc_lock=True, labels={"a": "b"}, license_mount="/k/iris.key"),
    )
    assert "52773" not in " ".join(argv)
    assert ["--cap-add", "CAP_IPC_LOCK"] == argv[
        argv.index("--cap-add") : argv.index("--cap-add") + 2
    ]
    assert ["--label", "a=b"] == argv[argv.index("--label") : argv.index("--label") + 2]
    assert "-v" in argv
    assert argv[argv.index("-v") + 1] == "/k/iris.key:/usr/irissys/mgr/iris.key:ro"
    assert argv[-1] == "img:1"


def test_run_docker_run_uses_run_timeout(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["kw"] = kw
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    runner.run_docker_run("img:1", _opts(run_timeout=33))
    assert seen["kw"]["timeout"] == 33


def test_run_docker_run_timeout(monkeypatch):
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 60)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    with pytest.raises(runner.RunTimeout):
        runner.run_docker_run("img:1", _opts())


def test_run_docker_generic(monkeypatch):
    def fake_run(argv, **kw):
        return subprocess.CompletedProcess(argv, 0, "out", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run_docker(["ps"], timeout=5).stdout == "out"


def test_run_docker_generic_timeout(monkeypatch):
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 5)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    with pytest.raises(TimeoutError):
        runner.run_docker(["ps"], timeout=5)


def test_sys_executable_available():
    assert sys.executable  # sanity: tests above rely on sh, not python
