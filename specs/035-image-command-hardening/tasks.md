# Tasks: Image Command Hardening

**Input**: Design documents in `/specs/035-image-command-hardening/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: Mandatory and written first in every phase. Each phase ends with a gate: its E2E/integration tests must pass before the next phase starts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelisable (different files, no dependency on an incomplete task)
- Fixtures live in `tests/unit/image/conftest.py`; the subprocess seam is `iris_devtester/cli/image/runner.py`, the second seam is the Docker SDK client (plan.md).
- Unit tests: `pytest tests/unit/image -m "not integration and not e2e"`. E2E here means `CliRunner` runs of the full command with only those two seams faked. Docker-gated tests use `@pytest.mark.integration`.

## Phase 1: Setup

- [x] T001 Run `black iris_devtester/cli/image_commands.py` as a formatting-only change and confirm `git diff --stat` touches no other file (FR-033)
- [x] T002 Create `tests/unit/image/__init__.py` and `tests/unit/image/conftest.py` with fixtures: `installer_kit` (tiny `.tar.gz` containing `irisinstall_silent`), `image_archive` (tiny tar with `manifest.json`), `elf_arm64` and `elf_amd64` (20-byte stub headers with e_machine 0xB7 and 0x3E), `fake_runner` (records argv, scripted results, patches `iris_devtester.cli.image.runner`), `fake_docker` (patches the Docker SDK client: containers with status, labels, image) (FR-035)
- [x] T003 Write characterisation tests in `tests/unit/image/test_characterisation.py` against `iris_devtester.cli.image_commands` with `CliRunner`, each `@pytest.mark.xfail(strict=True)` and named for the defect: build timeout not enforced (slow fake build, 1 s limit), password echoed in output, health wait hard-coded to 120 ignoring `--timeout`, `TimeoutExpired` reported as "Unexpected error" (FR-034)
- [x] T004 Write a passing baseline test in `tests/unit/image/test_shim.py` asserting `from iris_devtester.cli.image_commands import image_group` works, `iris_devtester.cli.image` is the same object as `image_group` in `iris_devtester/cli/__init__.py`, and `idt image --help` lists `load` and `build`
- [x] T005 Run T003 and T004; confirm T003 xfails and T004 passes on the unchanged code

## Phase 2: Foundational (blocks all stories)

- [x] T006 [P] Write `tests/unit/image/test_errors.py`: `ImageCommandError` holds what/why/fix/exit_code; `render_error` emits title, "What went wrong:", "Why it matters:", "How to fix it:"; rejects empty `fix`; never includes a supplied password string; exit codes limited to 1, 2, 5
- [x] T007 [P] Write `tests/unit/image/test_options.py`: `StartOptions` is frozen; constants `BUILD_TIMEOUT=900`, `LOAD_TIMEOUT=300`, `HEALTH_TIMEOUT=120`, `RUN_TIMEOUT=60`, `KILL_GRACE=3`; label keys exact
- [x] T008 [P] Write `tests/unit/image/test_runner.py`: `run_build` streams lines to a callback; a real `sleep 30` with 1 s limit raises `BuildTimeout` within 5 s and leaves no child process (check with `os.killpg` probe); SIGKILL follows after the grace period when SIGTERM is ignored; `run_docker_load` raises `LoadTimeout` on `subprocess.TimeoutExpired`; Windows branch (patched `os.name`) uses `Popen.kill()`
- [x] T009 [P] Write `tests/unit/image/test_common.py`: `run_image_command` renders an `ImageCommandError` once and exits with its code; `TimeoutError`/`BuildTimeout`/`LoadTimeout` exit 5 and never print "Unexpected error"; an unknown exception exits 1 with a fix mentioning `--keep-build-dir` and filing an issue; `--no-start` helper prints the manual `docker run` hint
- [x] T010 [P] Write `tests/unit/test_progress.py` additions: `print_connection_info` default still prints the real password; `show_password=False` prints `********` and "(set with --password)"
- [x] T011 Implement `iris_devtester/cli/image/errors.py` (`ImageCommandError`, `render_error`, exit-code constants) to pass T006
- [x] T012 Implement `iris_devtester/cli/image/options.py` (`StartOptions`, constants, label keys) to pass T007
- [x] T013 Implement `iris_devtester/cli/image/runner.py` (`run_build` with `Popen(start_new_session=True)` + `threading.Timer` killpg SIGTERM then SIGKILL, `run_docker_load`, `run_docker_run` using `RUN_TIMEOUT`, `BuildTimeout`, `LoadTimeout`) to pass T008
- [x] T014 Add `show_password: bool = True` to `print_connection_info` in `iris_devtester/utils/progress.py` to pass T010
- [x] T015 Move the existing code into `iris_devtester/cli/image/` without behaviour change: `__init__.py` (image_group), `load.py`, `build.py`, `common.py` (`create_and_start_container`, renamed from `_start_and_fixup`; `run_image_command`; `--no-start` helper to pass T009); remove the unused `ctx` parameters, the unused `timeout` parameter and the unreachable `return` after `ctx.exit(0)` (FR-015, FR-031, FR-032)
- [x] T016 Replace `iris_devtester/cli/image_commands.py` with a shim that re-exports `image_group`; run T003, T004, T006-T010 and confirm the suite passes with T003 still xfailing (phase gate)

**Checkpoint**: package exists, shim works, shared pieces tested, characterisation tests still xfail.

## Phase 3: User Story 1 - Commands that stop when they should (P1)

**Goal**: enforced per-phase timeouts, exit 5 everywhere.
**Independent test**: slow fake build with 1 s limit exits 5 within 5 s.

### Tests first

- [x] T017 [P] [US1] Write `tests/unit/image/test_timeouts.py`: `--build-timeout 60` reaches `run_build` as 60 (no floor); `--load-timeout` reaches `run_docker_load`; `--timeout` reaches `wait_for_healthy`; help text of each timeout option names its phase; defaults are 900, 300, 120
- [x] T018 [P] [US1] In the same file, add message tests: build timeout message has phase, limit, elapsed, last output line, retry hint; load timeout message contains `docker images`; health timeout message names the container, `docker logs <name>` and `docker rm -f <name>` and the container is not removed; build directory removed unless `--keep-build-dir`
- [x] T019 [US1] Write `tests/e2e/test_image_timeouts_e2e.py` (`@pytest.mark.e2e`): `CliRunner` runs `build` with a real `sleep 30` via the runner seam and `--build-timeout 1`; asserts exit code 5, elapsed under 5 s, three-part message, no "Unexpected error"
- [x] T020 [US1] Flip the T003 timeout-related xfails (build timeout, hard-coded 120, "Unexpected error") to normal tests or delete them where T017-T019 supersede, after the implementation below passes

### Implementation

- [x] T021 [US1] Add `--build-timeout` to `iris_devtester/cli/image/build.py` and `--load-timeout` to `iris_devtester/cli/image/load.py`; redefine `--timeout` as the health wait and pass it through `StartOptions` to `wait_for_healthy`
- [x] T022 [US1] Convert `BuildTimeout`, `LoadTimeout` and health `TimeoutError` into `ImageCommandError` with exit 5 and the messages in contracts/error-format.md; leave the container running on health timeout (FR-007)
- [x] T023 [US1] Remove the build directory on timeout unless `--keep-build-dir`; document the Windows fallback in a code comment and the help text

**Gate**: T017-T019 pass.

## Phase 4: User Story 2 - Clear failures, no leaked passwords (P1)

**Goal**: shared error contract and masked password.
**Independent test**: each failure path asserts exit code plus three message parts.

### Tests first

- [x] T024 [P] [US2] Write `tests/unit/image/test_failure_paths.py` with one test per failure in `load` and `build` (installer kit to `load` -> exit 2 pointing at `build`; `docker run` failure; `docker load` failure; no image tag in archive; `docker build` failure; missing iris-main; catch-all): assert exit code from the table, the three parts, a concrete fix, and no raw stderr without a fix
- [x] T025 [P] [US2] Write `tests/unit/image/test_password_output.py`: default output has no password string and shows `********`; `--show-password` shows it; the `Setting _SYSTEM password to '...'` line is absent; failed reset with default password -> warning, exit 0; failed reset or unexpire with non-default `--password` -> exit 1, container kept, message names `docker rm -f <name>` and the re-run
- [x] T026 [US2] Write `tests/e2e/test_image_errors_e2e.py` (`@pytest.mark.e2e`): `CliRunner` full `load` of the generated image archive with faked Docker succeeds with masked password; same with an installer kit fails exit 2

### Implementation

- [x] T027 [US2] Raise `ImageCommandError` at every failure site in `iris_devtester/cli/image/load.py`, `build.py`, `common.py` (replace `RuntimeError` and `click.ClickException` uses); render only in `run_image_command`
- [x] T028 [US2] Remove the password echo, add `--show-password` to both commands, pass `show_password` to `print_connection_info`; implement the default/non-default `--password` reset-failure rule in `common.py` (FR-012 to FR-014)
- [x] T029 [US2] Flip the password-echo xfail in `tests/unit/image/test_characterisation.py` to a normal test

**Gate**: T024-T026 pass; `pytest tests/unit/test_progress.py` unchanged.

## Phase 5: User Story 3 - License keys stay out of images (P1)

**Goal**: mount, never bake.
**Independent test**: build context and `docker run` argv inspected.

### Tests first

- [x] T030 [P] [US3] Write `tests/unit/image/test_license.py`: discovery order `--license` > `IRIS_LICENSE_KEY` > `./iris.key`; package-parent and `~/ws/iris-devtester/iris.key` candidates are not consulted (assert no `Path.exists` on them); missing key returns a notice and continues; explicit missing path (option or env) raises `ImageCommandError` exit 2; the used path is reported
- [x] T031 [P] [US3] Write `tests/unit/image/test_build_context.py`: generated build context contains no `iris.key`; the Dockerfile has no key COPY; `docker run` argv contains `-v <key>:/usr/irissys/mgr/iris.key:ro` only when a key resolves; the printed manual-start hint includes the same mount
- [x] T032 [US3] Write `tests/integration/test_image_license_docker.py` (`@pytest.mark.integration`, skipped without Docker): build a tiny image with the dummy key present in cwd, assert the key text is absent from `docker history` and `docker save` output

### Implementation

- [x] T033 [US3] Implement `iris_devtester/cli/image/license.py` (`discover_license_key`, `LicenseNotice`) and wire `--license`/`IRIS_LICENSE_KEY`/`./iris.key` into `build.py`
- [x] T034 [US3] Remove the key copy and the hard-coded candidate paths from the context builder; add the read-only mount to `run_docker_run` and the manual-start hint via `StartOptions.license_mount`

**Gate**: T030-T032 pass.

## Phase 6: User Story 4 - Safe handling of existing containers (P2)

**Goal**: labels and the collision rule.
**Independent test**: table of (labelled, status, replace) outcomes.

### Tests first

- [x] T035 [P] [US4] Write `tests/unit/image/test_collision.py`: parametrised over every row of the data-model table; labelled `created`/`dead` removed with exactly one announcement line; labelled running/exited/paused/restarting refuse exit 2 without `--replace` and remove with it; unlabelled refuses even with `--replace`; `--replace` removes the container only (`v=False`); refusal reason is one of the three phrases; the `--replace` hint appears only for labelled containers; three-part message
- [x] T036 [P] [US4] Write `tests/unit/image/test_labels.py`: `docker run` argv contains both `--label` arguments for `load` and `build`, with `io.iris-devtester.image=<ref>`
- [x] T037 [US4] Write `tests/e2e/test_image_collision_e2e.py` (`@pytest.mark.e2e`): `CliRunner` runs `load` twice with the same name against the fake Docker; second run exits 2; with `--replace` succeeds
- [x] T038 [US4] Write `tests/integration/test_image_collision_docker.py` (`@pytest.mark.integration`): with real Docker, create a labelled `created` container and an unlabelled one; assert the first is removed and the second survives `--replace`

### Implementation

- [x] T039 [US4] Implement `iris_devtester/cli/image/collision.py` (`resolve_name_collision`) and call it from `create_and_start_container`
- [x] T040 [US4] Add the two labels in `run_docker_run` from `StartOptions.labels`; add `--replace` to both commands

**Gate**: T035-T038 pass.

## Phase 7: User Story 5 - Trustworthy iris-main (P2)

**Goal**: ordered sources, ELF architecture check, image extraction, clear failure.
**Independent test**: stub binaries vs `--platform`.

### Tests first

- [x] T041 [P] [US5] Write `tests/unit/image/test_iris_main_elf.py`: accepts arm64 for `linux/arm64` and amd64 for `linux/amd64`; rejects mismatch (exit 2, names both architectures); rejects truncated and non-ELF files with a bad-file message; does not assert OS ABI byte
- [x] T042 [P] [US5] Write `tests/unit/image/test_iris_main_sources.py`: order `--iris-main` > `IDT_IRIS_MAIN` > `--iris-main-container` > `--iris-main-image` > arch-filtered auto-detect; missing env path -> exit 2; the chosen source is logged; auto-detect skips wrong-architecture containers; helper is named `_find_container_with_iris_main`
- [x] T043 [P] [US5] Write `tests/unit/image/test_iris_main_image.py`: extraction runs `docker create --platform <p>`, `docker cp`, `docker rm`; the temporary container is removed on success and when `cp` fails; version mismatch warns and continues; nothing found -> exit 2 with the exact `docker create`/`docker cp`/`docker rm` commands for the platform and the public `containers.intersystems.com/intersystems/iris-community:latest-preview`
- [x] T044 [US5] Write `tests/e2e/test_image_iris_main_e2e.py` (`@pytest.mark.e2e`): `CliRunner` runs `build --platform linux/amd64 --iris-main <arm64 stub>`; exit 2 before the build directory is populated; with the amd64 stub, the build proceeds to the faked `docker build`

### Implementation

- [x] T045 [US5] Implement `iris_devtester/cli/image/iris_main.py` (`check_elf_arch` with `struct.unpack_from('<H', hdr, 18)`, `resolve_iris_main`, `extract_from_image` with try/finally cleanup, `_find_container_with_iris_main`)
- [x] T046 [US5] Wire `--iris-main-image`, `IDT_IRIS_MAIN` and the ELF check into `build.py` ahead of populating the build directory; replace the old `RuntimeError` hint

**Gate**: T041-T044 pass.

## Phase 8: User Story 6 - Structure and coverage (P3)

**Goal**: 95% on the package, behaviour pinned.
**Independent test**: coverage command.

- [x] T047 [US6] Write `tests/integration/test_image_load_docker.py` (`@pytest.mark.integration`, skipped without Docker): `idt image load` of a tiny real image archive starts a labelled container and reports a masked password; remove the container afterwards
- [x] T048 [US6] Run `pytest tests/unit/image --cov=iris_devtester/cli/image --cov-report=term-missing --cov-fail-under=95`; add tests for every uncovered branch in `iris_devtester/cli/image/`
- [x] T049 [US6] Run `pytest tests/unit -m "not integration and not e2e"` and `pytest tests/e2e -m e2e -k image`; confirm the global 90% gate holds and `tests/unit/test_progress.py` is untouched
- [x] T050 [P] [US6] Run `black . && isort . && flake8 iris_devtester/cli/image && mypy iris_devtester/cli/image` and fix findings

**Gate**: T047-T050 pass.

## Phase 9: Documentation and polish

- [x] T051 [P] Write `docs/learnings/image-build-installer-kit.md`: why the key is mounted not baked (R1 BuildKit secret findings), why `docker load` fails on installer kits, `CAP_IPC_LOCK` and `setcap`, macOS/Linux-only timeout enforcement, the unverified iris-main version-mismatch question (FR-037)
- [x] T052 [P] Add CHANGELOG.md entries: `--timeout` on `build` now means the health wait only; new `--build-timeout`, `--load-timeout`, `--replace`, `--show-password`, `--iris-main-image`, `IDT_IRIS_MAIN`; password masked by default for `image`; key no longer searched outside the three sources; exit-code table
- [x] T053 [P] Update `skills/` and `README` references to the `idt image` options if they exist (grep `--timeout` and `iris.key` under `skills/`, `docs/`, `README.md`)
- [x] T054 Run `markdownlint-cli2 --fix` and `prettier --write` on every new or edited `.md` file; run the quickstart in `specs/035-image-command-hardening/quickstart.md` steps 1-6 by hand where Docker is available

## Dependencies and order

- Phase 1 -> Phase 2 -> stories in order: US1, US2, US3 (P1), US4, US5 (P2), US6 (P3) -> Phase 9.
- US1 and US2 both touch `common.py`; do US1 first. US3-US5 touch `build.py`; do them in order to avoid conflicts.
- Within a phase: tests (marked [P] where in different files) before implementation.

## Parallel examples

- Phase 2: T006-T010 can be written in parallel; T011-T014 in parallel once their tests exist.
- Phase 5: T030 and T031 in parallel.
- Phase 7: T041-T043 in parallel.
- Phase 9: T051-T053 in parallel.

## Implementation strategy

- MVP: Phases 1-3 (timeouts), then Phase 4 (errors and password); both P1 stories ship a safe CLI even if later phases slip.
- Each phase is independently releasable; stop at any gate.
- No push, issue filing or publishing without explicit permission.
