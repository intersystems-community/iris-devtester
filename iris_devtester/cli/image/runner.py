"""The subprocess seam for ``idt image``.

Every external process the image commands start goes through this module, so
tests replace these functions (or ``_run``) instead of ``subprocess``.
"""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from iris_devtester.cli.image.options import KILL_GRACE, LICENSE_MOUNT_TARGET, StartOptions


class PhaseTimeout(TimeoutError):
    """A phase exceeded its time limit."""

    phase = "phase"

    def __init__(self, phase: str, limit: float, elapsed: float, last_line: str = "") -> None:
        super().__init__(f"{phase} timed out after {limit}s")
        self.phase = phase
        self.limit = limit
        self.elapsed = elapsed
        self.last_line = last_line


class BuildTimeout(PhaseTimeout):
    """``docker build`` exceeded ``--build-timeout``."""


class LoadTimeout(PhaseTimeout):
    """``docker load`` exceeded ``--load-timeout``."""


class RunTimeout(PhaseTimeout):
    """``docker run`` exceeded the run timeout."""


@dataclass
class BuildResult:
    returncode: int
    last_line: str
    elapsed: float


def _run(argv: List[str], timeout: Optional[float] = None, **kwargs: Any):
    """The only ``subprocess.run`` call site (patched by tests)."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, **kwargs)


def run_docker(argv: List[str], timeout: float):
    """Run an arbitrary docker command, mapping ``TimeoutExpired`` to ``TimeoutError``."""
    try:
        return _run(argv, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise PhaseTimeout(" ".join(argv[:2]), timeout, float(timeout)) from exc


def run_docker_load(path: str, timeout: float):
    """``docker load -i path`` with an enforced limit."""
    start = time.monotonic()
    try:
        return _run(["docker", "load", "-i", str(path)], timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise LoadTimeout("load", timeout, time.monotonic() - start) from exc


def docker_run_argv(image_ref: str, options: StartOptions) -> List[str]:
    """The ``docker run`` command for ``options`` (also used for manual-start hints)."""
    argv = ["docker", "run", "-d", "--name", options.name]
    argv += ["-p", f"{options.superserver_port}:1972"]
    if options.web_port:
        argv += ["-p", f"{options.web_port}:52773"]
    if options.cap_ipc_lock:
        argv += ["--cap-add", "CAP_IPC_LOCK"]
    for key, value in options.labels.items():
        argv += ["--label", f"{key}={value}"]
    if options.license_mount:
        argv += ["-v", f"{options.license_mount}:{LICENSE_MOUNT_TARGET}:ro"]
    argv.append(image_ref)
    return argv


def run_docker_run(image_ref: str, options: StartOptions):
    """Start the container; returns the completed process."""
    start = time.monotonic()
    try:
        return _run(docker_run_argv(image_ref, options), timeout=options.run_timeout)
    except subprocess.TimeoutExpired as exc:
        raise RunTimeout("run", options.run_timeout, time.monotonic() - start) from exc


def _terminate_tree(proc: Any, sig: int = signal.SIGTERM) -> None:
    """Signal the whole process group (posix) or kill the CLI process (Windows).

    On Windows there are no process groups here, so only the ``docker`` CLI
    process is killed; buildx children may linger until the daemon notices.
    """
    if os.name == "nt":
        try:
            proc.kill()
        except OSError:
            pass
        return
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError):
        pass


def run_build(
    argv: List[str], timeout: float, on_line: Optional[Callable[[str], None]] = None
) -> BuildResult:
    """Run a build, streaming output lines, enforcing ``timeout``.

    On expiry the process group gets SIGTERM, then SIGKILL after ``KILL_GRACE``
    seconds, and :class:`BuildTimeout` is raised.
    """
    kwargs: dict = {}
    if os.name != "nt":
        kwargs["start_new_session"] = True
    start = time.monotonic()
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs
    )
    timed_out = threading.Event()
    timers: List[threading.Timer] = []

    def _expire() -> None:
        if proc.poll() is not None:
            return
        timed_out.set()
        _terminate_tree(proc, signal.SIGTERM)
        hard = threading.Timer(KILL_GRACE, _terminate_tree, args=(proc, signal.SIGKILL))
        hard.daemon = True
        timers.append(hard)
        hard.start()

    timer = threading.Timer(timeout, _expire)
    timer.daemon = True
    timers.append(timer)
    timer.start()
    last_line = ""
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip()
            if line:
                last_line = line
                if on_line:
                    on_line(line)
        proc.wait()
    finally:
        for t in list(timers):
            t.cancel()
        if proc.poll() is None:
            _terminate_tree(proc, signal.SIGKILL)
            proc.wait()
    elapsed = time.monotonic() - start
    if timed_out.is_set():
        raise BuildTimeout("build", timeout, elapsed, last_line)
    return BuildResult(returncode=proc.returncode, last_line=last_line, elapsed=elapsed)
