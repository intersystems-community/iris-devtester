# Research: Image Command Hardening

All product decisions were made in the wayfinder tickets; this records them with rationale and the implementation facts fixed during planning. No NEEDS CLARIFICATION remain.

## Build timeout enforcement (T2, R1)

- **Decision**: `Popen(..., start_new_session=True)`; a `threading.Timer` sends SIGTERM to the process group, then SIGKILL after about 3 s; the read loop checks a `timed_out` event and raises `TimeoutError` instead of treating rc 130 as a plain failure.
- **Rationale**: R1 measured a 5 s limit returning in 5.5 s with the build step cancelled and nothing left in the builder. Killing only the CLI leaves buildx children running.
- **Alternatives**: `subprocess.run(timeout=)` (cannot stream output); killing the docker CLI only (children linger); `taskkill` on Windows (out of scope).
- **Platform**: `os.killpg` on macOS and Linux; on Windows `Popen.kill()` with a documented caveat.

## Load timeout (T2)

- **Decision**: keep `subprocess.run(timeout=load_timeout)` and catch `TimeoutExpired`; the message says to check `docker images`.
- **Rationale**: the daemon may finish the import after the client is killed.

## License key (T1, R1)

- **Decision**: mount read-only at run time; never copy into the build context.
- **Rationale**: R1 showed a BuildKit secret works but adds cache-key and single-RUN constraints, and the image stays license-free with a mount. Secret support is held in reserve.
- **Alternatives**: bake the key (leaks into layers); BuildKit secret (no step needs a licensed instance).

## Error contract (T3)

- **Decision**: `ImageCommandError(what, why, fix, exit_code)` raised at the failure site, rendered once by `run_image_command`.
- **Alternatives**: pattern-match stderr (deferred follow-on); keep ad hoc `ClickException` (inconsistent).
- **Note**: click's own usage errors exit 2 already, matching the "bad input" code.

## Password display (T3)

- **Decision**: `print_connection_info(..., show_password=True)` default preserves `container up`; `image` passes `show_password` from `--show-password`, which defaults to False.
- **Rationale**: avoids touching `tests/unit/test_progress.py` and other callers.

## Collision and labels (T4)

- **Decision**: labels `io.iris-devtester.created-by=idt` and `io.iris-devtester.image=<ref>` added through `docker run --label`; collision rule evaluated from `container.labels` and `container.status` via the Docker SDK.
- **Rationale**: `exited` is not auto-removed because no volume is mounted, so data lives in the writable layer.

## iris-main (T5)

- **Decision**: ELF check with `struct.unpack_from('<H', header, 18)`; bytes 0-3 must be `7f 45 4c 46`, byte 4 `02`, byte 5 `01`; `e_machine` 0xB7 for arm64, 0x3E for amd64. Byte 7 is not asserted.
- **Image extraction**: `docker create --platform`, `docker cp`, `docker rm` in a try/finally.
- **Version**: only a warning, from the source container's `/iris-main --version` when one is running; otherwise skipped.
- **Alternatives**: strict version gate (no evidence of harm; needs a container to run `--version`).

## Package layout (T6)

- **Decision**: package with a shim; `StartOptions` frozen dataclass; one `run_image_command` wrapper.
- **Import path**: `iris_devtester/cli/__init__.py` imports `image_group` from `.image_commands`; the shim keeps that line valid.

## Tests (T7)

- **Decision**: patch `runner` functions and the Docker SDK client; real `tarfile` on generated fixtures; characterisation tests as `xfail(strict=True)`; one gated integration test; 95% on `cli/image/`.
- **Timeout tests** use a real `sleep 30` with a 1 s limit through the runner, so they exercise the process-group kill.
