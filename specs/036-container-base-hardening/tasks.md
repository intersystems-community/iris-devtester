# Tasks: Container Base Hardening

**Input**: Design documents in `/specs/036-container-base-hardening/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: Mandatory and written first in every phase. Each phase ends with a gate: its tests must pass before the next phase starts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelisable (different files, no dependency on an incomplete task)
- Unit tests: `pytest tests/unit -m "not integration and not e2e"`. Integration tests use `@pytest.mark.integration` and need Docker.

## Phase 1: Setup and probe

- [x] T001 Write `tests/integration/test_base_quoted_password.py` (`@pytest.mark.integration`): start an `IRISDockerContainer` on a community image, run a fixed `iris session` command through `exec_run(environment={"IDT_PW": 'a"b\'c$(x)'})` that reads the value with the environment-variable lookup and writes it to a known global, then read the global back and assert it equals the input exactly (confirms the FR-017 assumption)
- [x] T002 Run T001 against the community image and the health image; record the result in `specs/036-container-base-hardening/research.md` under "Unverified". If it fails, stop and switch to the stdin fallback in research.md before T003
- [x] T003 Baseline: run `pytest tests/unit -m "not integration and not e2e" --cov=iris_devtester --cov-report=term | tail` and note the current coverage percentage in `research.md` so each later step can be compared

## Phase 2: User Story 1 - Any password or namespace is handled safely (P1)

**Goal**: constant command, values through the environment, validation, exit-status checks.
**Independent test**: `a"b'c$(x)` password works; `MY NS; rm` rejected before `start()`.

### Tests first

- [x] T004 [P] [US1] Add to `tests/unit/test_iris_base_container.py`: namespace pattern tests (accepts `MY_NS`, `A`, 64-char name; rejects empty, 65 chars, leading digit, `MY NS; rm`, `my-ns`, `%SYS`, quotes); username pattern tests (accepts `bob`, `_svc`, `a.b@c-d`; rejects space, quote, 129 chars); both run in the constructor, before `start()`, and `start()` is never reached (assert `docker` not called)
- [x] T005 [P] [US1] Add to the same file: password tests: `a"b'c$(x)` reaches `exec_run` unchanged in `environment` and appears in no command string; empty and NUL passwords raise `ValueError` whose text does not contain the value; no `logger` call contains the password (capture logs)
- [x] T006 [P] [US1] Add opt-in tests: username without password -> no user command and invalid username ignored; password without username -> no user; invalid namespace with no user still raises; namespace `USER` -> no create-database command; environment-variable sources (`IRIS_USERNAME`, `IRIS_PASSWORD`, `IRIS_NAMESPACE`) validated and named in the error
- [x] T007 [P] [US1] Add exit-status tests: non-zero exit for create database raises a structured error naming "create database"; same for "create user"; error text has what/how-to-fix and no password; the command strings passed to `exec_run` are constant across different values
- [x] T008 [US1] Add `tests/unit/test_iris_container_credentials.py`: `IRISContainer` with a bad namespace raises the same `ValueError` (FR-008)
- [x] T009 [US1] Add E2E-level test in the integration file from T001: create a user whose password contains a quote via `IRISContainer`, connect as that user with the exact password, and assert success (phase gate)

### Implementation

- [x] T010 [US1] Add the two pattern constants and validation helpers to `iris_devtester/containers/_base.py`; call them from `__init__` for the effective namespace, username and password values per the opt-in rules; raise structured `ValueError`s per `contracts/validation-contract.md`
- [x] T011 [US1] Replace the two `%`-formatted commands in `_base.py` `_connect` with fixed argv lists and `environment=` mappings; check both results' exit status and raise structured errors naming the step; ensure no debug log contains the password or the environment mapping

**Gate**: T004-T009 pass (T009 needs Docker).

## Phase 3: User Story 2 - Licence problems are never silently hidden (P2)

### Tests first

- [x] T012 [P] [US2] Replace the test pinning the swallow (`tests/unit/test_iris_base_container.py`, the case where `get_logs` raises `Exception("container gone")`) with: Docker error -> warning logged, returns False; container-not-started error -> warning, False; `RuntimeError` propagates; rejected log -> True; accepted log -> False
- [x] T013 [P] [US2] Add timeout-path test: when `get_logs` raises a Docker error during the start-up timeout path, the raised `TimeoutError` message states the licence check could not read logs; helper still returns `bool`
- [x] T014 [US2] Add an E2E-style test with a fake container whose `get_logs` fails and whose health never arrives; assert the surfaced message and the logged warning (phase gate)

### Implementation

- [x] T015 [US2] In `_base.py`, narrow `_community_license_rejected` to `docker.errors.DockerException` and the testcontainers container-start exception, log the exception at warning, keep the boolean return; thread the "could not read logs" note into the timeout-path message

**Gate**: T012-T014 pass.

## Phase 4: User Story 3 - No dead code (P2)

### Step one: safe deletions

#### Tests first

- [x] T016 [P] [US3] Add tests in `tests/unit/test_iris_base_container.py`: `IRISDockerContainer(...)` has no `driver` attribute and rejects `driver=`; `IRISContainer.__mro__` includes `IRISDockerContainer` and no class named `_IRISMockContainer`; module has no `IRISBase` or `_ActualBase`
- [x] T017 [US3] Update `tests/unit/test_iris_base_container.py` (delete the `c.driver == "iris"` assertion) and re-point the two `IRISBase.start` patches in `tests/unit/test_iris_container_extra.py` to `IRISDockerContainer.start`

#### Implementation

- [x] T018 [US3] In `_base.py` remove `driver` (parameter, attribute, docs) and `self.image = image`; in `iris_container.py` remove `_IRISMockContainer`, `IRISBase`, `_ActualBase` and its try/except so `IRISContainer` subclasses `IRISDockerContainer`
- [x] T019 [US3] Run the unit suite; compare coverage to the T003 baseline; fix regressions (gate for step two)

### Step two: remove `HAS_TESTCONTAINERS`

#### Tests first

- [x] T020 [P] [US3] Rewrite the 10 `False` patch sites and the one `True` site in `tests/unit/test_iris_container_extra.py` to test the single remaining path (constructor without the warning; `attach()` via `get_config()`); delete tests that only pinned the removed branch
- [x] T021 [P] [US3] Rewrite the 11 `False` patch sites in `tests/unit/test_password_preconfig.py` the same way, and remove the `HAS_TESTCONTAINERS is True` assertion in `tests/unit/test_iris_base_container.py`
- [x] T022 [US3] Compare `tests/contract/test_preconfig_contract.py` line by line with `tests/unit/test_password_preconfig.py`; write the list of unique assertions in a comment at the top of the PR notes (`specs/036-container-base-hardening/research.md`); rewrite those as real contract tests with no patching, delete the rest; the file must not patch any nonexistent attribute (FR-014)
- [x] T023 [US3] Add a guard test `tests/unit/test_no_dead_names.py` asserting `grep`-equivalent absence of `HAS_TESTCONTAINERS`, `_IRISMockContainer`, `_ActualBase`, `IRISBase` and `driver=` in `iris_devtester/` (SC-006)

#### Implementation

- [x] T024 [US3] Remove `HAS_TESTCONTAINERS`, its constructor warning and the manual host/port `False` branch in `attach()` from `iris_container.py`
- [x] T025 [US3] Run `pytest tests/unit -m "not integration and not e2e" --cov=iris_devtester --cov-fail-under=90`; add tests for any new uncovered lines until coverage is at or above the T003 baseline

**Gate**: T016-T023 pass; coverage at or above 90%.

## Phase 5: User Story 4 - `container up` containers are recognisable (P3)

### Tests first

- [x] T026 [P] [US4] Write `tests/unit/test_container_labels.py`: `IRISContainerManager._create_with_docker_sdk` passes `labels` with both keys to the Docker client; image label omitted when the ref is empty; the existing `iris-devtester.config.source` key is untouched; `idt container up` (via `CliRunner`, Docker faked) results in a container create call carrying the labels; `container up` output is unchanged (compare with current output snapshot)
- [x] T027 [US4] Add `tests/integration/test_container_up_labels.py` (`@pytest.mark.integration`): run `idt container up`, inspect labels with the Docker SDK, remove the container (phase gate)

### Implementation

- [x] T028 [US4] Add the labels in `iris_devtester/utils/iris_container_adapter.py::_create_with_docker_sdk` and, if `container up` creates containers through the testcontainers path, through `with_kwargs(labels=...)` in the same adapter; reuse the constants from feature 035's `cli/image/options.py` if present, otherwise define them once in `iris_devtester/containers/labels.py` and import from both features

**Gate**: T026-T027 pass.

## Phase 6: User Story 5 - Decisions are written down (P3)

- [x] T029 [P] [US5] Write `docs/learnings/container-base-dead-code-and-env-transfer.md`: why the fallback base and `HAS_TESTCONTAINERS` were dropped (testcontainers is a hard dependency), why values travel by environment rather than being escaped, the probe result from T002, the namespace rule and why it is conservative, and the follow-up for `utils/password.py` and `utils/namespace.py` (same interpolation; FR-019)
- [x] T030 [P] [US5] Add CHANGELOG.md entries: base deliberately does not derive from `DbContainer` (deprecated for removal; see `docs/learnings/testcontainers-iris-removal.md`); `driver` parameter removed; new validation rules and errors; licence check now logs Docker failures at warning; `container up` containers carry idt labels (FR-018)
- [x] T031 [US5] Run `markdownlint-cli2 --fix` and `prettier --write` on every new or edited `.md` file; walk through `quickstart.md` steps 1-6

## Phase 7: Polish

- [x] T032 [P] Run `black . && isort . && flake8 iris_devtester/containers iris_devtester/utils/iris_container_adapter.py && mypy iris_devtester/`; fix findings
- [x] T033 Run the full unit suite with the coverage gate and the Docker-gated tests; confirm T003 baseline is met or exceeded

## Dependencies and order

- Phase 1 (probe) gates everything: a failed probe changes the Phase 2 approach.
- US1 -> US2 (both edit `_base.py`) -> US3 step one -> step two. US4 and US5 can start after US1; US5's note needs the T002 result.
- Feature 035 reads the labels defined here; land T028 before relying on `container up` containers being replaceable there.

## Parallel examples

- Phase 2: T004-T007 in parallel.
- Phase 4 step two: T020 and T021 in parallel.
- Phase 6: T029 and T030 in parallel.

## Implementation strategy

- MVP: Phases 1-2 (safe values); it fixes the injection and the opaque start-up failure on its own.
- Deletions ship in two reviewable steps so the test-heavy flag removal has its own review and coverage check.
- No push, issue filing or publishing without explicit permission.
