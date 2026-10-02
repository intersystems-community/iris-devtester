"""Fixtures for the ``idt image`` tests.

Two seams are faked:

* ``iris_devtester.cli.image.runner`` -- every subprocess the commands start.
* the Docker SDK client (``docker.from_env``).

The health wait and the password helpers get their own small fakes.
"""

import importlib
import io
import subprocess
import tarfile
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import pytest

ELF_MAGIC = b"\x7fELF"


def _elf_header(e_machine: int) -> bytes:
    """20-byte stub: magic, 64-bit, little endian, version 1, e_type 2, e_machine."""
    hdr = bytearray(20)
    hdr[0:4] = ELF_MAGIC
    hdr[4] = 2
    hdr[5] = 1
    hdr[6] = 1
    hdr[16:18] = (2).to_bytes(2, "little")
    hdr[18:20] = e_machine.to_bytes(2, "little")
    assert len(hdr) == 20
    return bytes(hdr)


@pytest.fixture
def elf_arm64(tmp_path):
    path = tmp_path / "iris-main-arm64"
    path.write_bytes(_elf_header(0xB7))
    return path


@pytest.fixture
def elf_amd64(tmp_path):
    path = tmp_path / "iris-main-amd64"
    path.write_bytes(_elf_header(0x3E))
    return path


@pytest.fixture
def installer_kit(tmp_path):
    """Tiny ISC installer kit: a .tar.gz containing ``irisinstall_silent``."""
    path = tmp_path / "IRISHealth-2026.3.0AI.140.0-dockerubuntuarm64.tar.gz"
    with tarfile.open(path, "w:gz") as tf:
        data = b"#!/bin/sh\nexit 0\n"
        info = tarfile.TarInfo("IRIS-kit/irisinstall_silent")
        info.size = len(data)
        info.mode = 0o755
        tf.addfile(info, io.BytesIO(data))
        data2 = b"#!/bin/sh\n"
        info2 = tarfile.TarInfo("IRIS-kit/irisinstall")
        info2.size = len(data2)
        tf.addfile(info2, io.BytesIO(data2))
    return path


@pytest.fixture
def image_archive(tmp_path):
    """Tiny docker-save style archive: a tar with ``manifest.json``."""
    path = tmp_path / "IRIS-2026.2.0AI.127.0-docker.tar.gz"
    with tarfile.open(path, "w:gz") as tf:
        data = b"[]"
        info = tarfile.TarInfo("manifest.json")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return path


def _result(rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr=stderr)


class FakeRunner:
    """Records argv and returns scripted results for the runner module."""

    def __init__(self):
        self.calls: List[List[str]] = []
        self.timeouts: List[Optional[float]] = []
        self.build_calls: List[Dict[str, Any]] = []
        self._scripts: List[tuple] = []
        self.run_hooks: List[Callable[[List[str]], None]] = []
        self.build_lines: List[str] = ["Step 1/1 : FROM ubuntu"]
        self.build_rc = 0
        self.build_exc: Optional[BaseException] = None

    def script(self, prefix, result=None, exc=None):
        """Script a result, a callable ``f(argv) -> result`` or an exception for ``prefix``."""
        self._scripts.append((list(prefix), result, exc))

    def argvs(self, *prefix):
        return [c for c in self.calls if c[: len(prefix)] == list(prefix)]

    # the patched primitives
    def _run(self, argv, timeout=None, **kwargs):
        argv = list(argv)
        self.calls.append(argv)
        self.timeouts.append(timeout)
        for hook in self.run_hooks:
            hook(argv)
        for prefix, result, exc in reversed(self._scripts):
            if argv[: len(prefix)] == prefix:
                if exc is not None:
                    raise exc
                if callable(result):
                    return result(argv)
                return result
        if argv[:2] == ["docker", "load"]:
            return _result(stdout="Loaded image: iris-test:1\n")
        if argv[:2] == ["docker", "create"]:
            return _result(stdout="cid123\n")
        return _result()

    def run_build(self, argv, timeout, on_line=None, **kwargs):
        from iris_devtester.cli.image import runner as real

        self.calls.append(list(argv))
        self.build_calls.append({"argv": list(argv), "timeout": timeout})
        if self.build_exc is not None:
            raise self.build_exc
        last = ""
        for line in self.build_lines:
            if on_line:
                on_line(line)
            last = line
        return real.BuildResult(returncode=self.build_rc, last_line=last, elapsed=0.0)


@pytest.fixture
def fake_runner(monkeypatch):
    runner = importlib.import_module("iris_devtester.cli.image.runner")
    fake = FakeRunner()
    monkeypatch.setattr(runner, "_run", fake._run)
    monkeypatch.setattr(runner, "run_build", fake.run_build)
    return fake


class FakeContainer:
    def __init__(self, name, status="running", labels=None, image="iris-test:1", docker=None):
        self.name = name
        self.status = status
        self.labels = dict(labels or {})
        self.image = SimpleNamespace(tags=[image] if image else [])
        self.removed: List[Dict[str, Any]] = []
        self._docker = docker
        self.id = "id-" + name

    def reload(self):
        return None

    def remove(self, force=False, v=False):
        self.removed.append({"force": force, "v": v})
        if self._docker is not None:
            self._docker.containers.store.pop(self.name, None)


class FakeContainers:
    def __init__(self, docker):
        self._docker = docker
        self.store: Dict[str, FakeContainer] = {}

    def get(self, name):
        import docker

        if name not in self.store:
            raise docker.errors.NotFound(f"No such container: {name}")
        return self.store[name]


class FakeDocker:
    def __init__(self):
        self.containers = FakeContainers(self)

    def add(self, name, status="running", labels=None, image="iris-test:1"):
        c = FakeContainer(name, status, labels, image, docker=self)
        self.containers.store[name] = c
        return c

    def on_docker_run(self, argv):
        if argv[:3] == ["docker", "run", "-d"] and "--name" in argv:
            name = argv[argv.index("--name") + 1]
            labels = {}
            for i, a in enumerate(argv):
                if a == "--label":
                    k, _, v = argv[i + 1].partition("=")
                    labels[k] = v
            self.add(name, "running", labels, argv[-1])


@pytest.fixture
def fake_docker(monkeypatch, fake_runner):
    import docker

    fake = FakeDocker()
    monkeypatch.setattr(docker, "from_env", lambda *a, **k: fake)
    fake_runner.run_hooks.append(fake.on_docker_run)
    return fake


class FakeHealth:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.exc: Optional[BaseException] = None


@pytest.fixture
def fake_health(monkeypatch):
    from iris_devtester.utils import health_checks

    fake = FakeHealth()

    def _wait(container, timeout=60, progress_callback=None):
        fake.calls.append({"container": container, "timeout": timeout})
        if fake.exc is not None:
            raise fake.exc

    monkeypatch.setattr(health_checks, "wait_for_healthy", _wait)
    return fake


class FakePassword:
    def __init__(self):
        self.unexpire_calls: List[str] = []
        self.reset_calls: List[Dict[str, Any]] = []
        self.unexpire_result = (True, "ok")
        self.unexpire_exc: Optional[BaseException] = None
        self.reset_result = (True, "ok")
        self.reset_exc: Optional[BaseException] = None


@pytest.fixture
def fake_password(monkeypatch):
    from iris_devtester.utils import password as pw

    fake = FakePassword()

    def _unexpire(container_name="iris_db", timeout=30):
        fake.unexpire_calls.append(container_name)
        if fake.unexpire_exc is not None:
            raise fake.unexpire_exc
        return fake.unexpire_result

    def _reset(**kwargs):
        fake.reset_calls.append(kwargs)
        if fake.reset_exc is not None:
            raise fake.reset_exc
        return fake.reset_result

    monkeypatch.setattr(pw, "unexpire_all_passwords", _unexpire)
    monkeypatch.setattr(pw, "reset_password", _reset)
    return fake
