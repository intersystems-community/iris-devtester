# Tasks: Fix Namespace Auto-Creation Container Lookup

**Input**: Design documents from `/specs/027-fix-namespace-lookup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/namespace-strategy.md

**Tests**: Test tasks are included as this is a bug fix requiring regression coverage and the contracts define explicit test scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `iris_devtester/`, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Verify existing tests pass before making changes (baseline)

- [x] T001 Run existing test suite to establish passing baseline: `pytest tests/unit/test_namespace_utils.py tests/integration/test_implicit_namespace.py -v`
- [x] T002 Read current implementation of `ensure_namespace_exists()` in `iris_devtester/utils/namespace.py` (lines 141-173) and `get_connection()` in `iris_devtester/connections/connection.py` (lines 24-133) to confirm line numbers match plan

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the new `iris.connect()`-based namespace functions that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `check_namespace_via_iris_connect(config, namespace)` in `iris_devtester/utils/namespace.py` — new function that connects to `%SYS` via `iris.connect()`, calls `classMethodValue("Config.Namespaces", "Exists", namespace)`, returns `True`/`False`. Must handle edge cases inline: (a) `%SYS` access denied → log warning, return `False`, (b) connection refused → log warning, return `False`, (c) empty string `container_name` treated as unset. Catches all exceptions gracefully per Contract 2.
- [x] T004 Implement `create_namespace_via_iris_connect(config, namespace)` in `iris_devtester/utils/namespace.py` — new function that connects to `%SYS` via `iris.connect()`, calls `classMethodValue("Config.Namespaces", "Create", namespace, properties)` with default properties `{"Globals": "USER", "Routines": "USER"}` per `docs/SQL_VS_OBJECTSCRIPT.md` lines 115-119. Returns `True`/`False`. Must handle same edge cases as T003. Catches all exceptions gracefully per Contract 3.
- [x] T005 Add unit tests for `check_namespace_via_iris_connect()` in `tests/unit/test_namespace_utils.py` — mock `iris.connect()` and `iris.createIRIS()` to test all 4 scenarios from Contract 2 (exists, not exists, access denied, connection refused)
- [x] T006 Add unit tests for `create_namespace_via_iris_connect()` in `tests/unit/test_namespace_utils.py` — mock `iris.connect()` to test success and failure paths per Contract 3

**Checkpoint**: Two new functions implemented and unit-tested. Existing behavior unchanged.

---

## Phase 3: User Story 1 - Clean Connection with Explicit Config (Priority: P1) MVP

**Goal**: Eliminate spurious Docker container lookup errors when an explicit `IRISConfig` is provided without a `container_name`. This is the primary reported bug.

**Independent Test**: Call `get_connection(config=IRISConfig(host="localhost", port=1972, namespace="USER"))` when no container named `iris_db` exists. Verify zero Docker-related errors in logs.

### Tests for User Story 1

- [x] T007 [P] [US1] Add unit test for strategy selection in `tests/unit/test_namespace_utils.py` — parametrize across all `auto_create` × `container_name` combinations from Contract 1 scenarios 1-8: `auto_create=False` → skip (no subprocess, no iris.connect), `auto_create=True` + `container_name=None` → iris.connect() (no subprocess), `auto_create=None` + localhost + no container → iris.connect(), `auto_create=None` + remote + no container → skip. Mock subprocess to assert it is never called in iris.connect() scenarios.
- [x] T008 [P] [US1] Add negative test for hardcoded `iris_db` in `tests/unit/test_namespace_utils.py` — per Contract 4, verify no subprocess call contains `iris_db` when `container_name=None`

### Implementation for User Story 1

- [x] T009 [US1] Refactor `ensure_namespace_exists()` in `iris_devtester/utils/namespace.py` — remove `container_name = config.container_name or "iris_db"` (line 162). Replace with strategy selection: if `container_name` is set (non-None, non-empty) use Docker exec path, else use `check_namespace_via_iris_connect()` and `create_namespace_via_iris_connect()` from Phase 2. Per FR-001, FR-004.
- [x] T010 [US1] Remove `iris_db` fallback from `get_connection()` password reset path in `iris_devtester/connections/connection.py` — change line 122 from `getattr(config, "container_name", "iris_db") or "iris_db"` to `getattr(config, "container_name", None)`. If `container_name` is None, skip Docker-based password reset. Per Contract 5.
- [x] T011 [US1] Update log messages in `iris_devtester/utils/namespace.py` — per FR-005, ensure log messages distinguish "no container available for Docker exec, using iris.connect()" (DEBUG) from "namespace does not exist" (INFO). Existing namespace already exists case should log at DEBUG only (acceptance scenario 3).

**Checkpoint**: Explicit config connections produce zero Docker-related errors. Run `pytest tests/unit/test_namespace_utils.py -v` — all tests pass.

---

## Phase 4: User Story 2 - iris.connect()-Based Namespace Verification (Priority: P2)

**Goal**: Enable namespace existence checking and creation via `iris.connect()` for any reachable IRIS instance, including remote hosts.

**Independent Test**: Connect to an IRIS instance via explicit host/port. Verify namespace existence is checked via `iris.connect()` to `%SYS`, not `docker exec`.

### Tests for User Story 2

- [x] T012 [P] [US2] Add integration test in `tests/integration/test_implicit_namespace.py` — test that explicit `IRISConfig` with `host` and `port` (no `container_name`) checks namespace existence via `iris.connect()`. Verify by checking that no subprocess calls occur during namespace verification.

### Implementation for User Story 2

- [x] T013 [US2] Verify `check_namespace_via_iris_connect()` works end-to-end against a live IRIS instance in `tests/integration/test_implicit_namespace.py` — connect to running test container via host/port, confirm `Config.Namespaces.Exists("USER")` returns True via `iris.connect()` path
- [x] T014 [US2] Verify edge case handling end-to-end in `tests/integration/test_implicit_namespace.py` — confirm that graceful fallback works against live IRIS when `%SYS` access is restricted or connection parameters are incorrect (edge cases already implemented in T003/T004)

**Checkpoint**: Namespace verification works via `iris.connect()` without Docker. Run `pytest tests/integration/test_implicit_namespace.py -v` — all tests pass.

---

## Phase 5: User Story 3 - Preserve Docker-Based Auto-Creation (Priority: P3)

**Goal**: Verify existing Docker-exec-based namespace auto-creation continues to work when `container_name` is known (auto-discovered configs).

**Independent Test**: Call `get_connection()` with no arguments when a Docker container is running. Verify namespace auto-creation still works via Docker exec.

### Tests for User Story 3

- [x] T015 [P] [US3] Add unit test for Docker exec strategy selection in `tests/unit/test_namespace_utils.py` — test that `ensure_namespace_exists()` with `container_name="my-iris"` uses Docker exec path (Contract 1, scenarios 2, 7). Mock subprocess to verify it IS called with correct container name.

### Implementation for User Story 3

- [x] T016 [US3] Verify backward compatibility of Docker exec path in `iris_devtester/utils/namespace.py` — ensure `check_namespace_exists()` and `create_namespace()` functions are unchanged and still called when `container_name` is set. No code changes expected — this is a verification task.
- [x] T017 [US3] Add integration test in `tests/integration/test_implicit_namespace.py` — test auto-discovered config path: call `get_connection()` with no explicit config when a test container is running, verify namespace operations use Docker exec against the discovered container name (not `iris_db`)

**Checkpoint**: All three user stories work independently. Run full test suite: `pytest tests/unit/test_namespace_utils.py tests/integration/test_implicit_namespace.py -v`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cleanup

- [x] T018 Run full project test suite to verify backward compatibility: `pytest -v`
- [x] T019 [P] Validate quickstart.md scenarios manually — test the before/after examples from `specs/027-fix-namespace-lookup/quickstart.md`
- [x] T020 [P] Add blind alley documentation to `docs/learnings/` — document why SQL/DBAPI was rejected for namespace existence check in favor of `iris.connect()` (per research.md R6 and Constitution Principle 10)
- [x] T021 Review log output for all code paths — verify SC-001 (zero Docker errors with explicit config) and SC-004 (only actionable messages)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2). Can run in parallel with US1.
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2). Can run in parallel with US1/US2.
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Phase 2 foundational functions. Core bug fix — MVP.
- **User Story 2 (P2)**: Depends only on Phase 2. Independent of US1 (uses same foundational functions but different test scenarios).
- **User Story 3 (P3)**: Depends only on Phase 2. Independent of US1/US2 (tests the Docker exec path, not the new iris.connect() path).

### Within Each User Story

- Tests written first (verify they describe expected behavior)
- Implementation tasks in dependency order
- Checkpoint validation before moving to next story

### Parallel Opportunities

Within Phase 2:
- T003 and T004 can run in parallel (different functions, same file — coordinate writes)
- T005 and T006 can run in parallel (different test functions)

Within Phase 3 (US1):
- T007 and T008 can run in parallel (different test functions)

Across Phases 3-5:
- US1, US2, US3 can all start after Phase 2 completes — they test different code paths

Within Phase 6:
- T019 and T020 can run in parallel (different files/activities)

---

## Parallel Example: User Story 1

```bash
# After Phase 2 completes, launch US1 tests in parallel:
Task: "Unit test for strategy selection in tests/unit/test_namespace_utils.py"  # T007
Task: "Negative test for hardcoded iris_db in tests/unit/test_namespace_utils.py"  # T008

# Then implement sequentially (same file):
Task: "Refactor ensure_namespace_exists() in iris_devtester/utils/namespace.py"  # T009
Task: "Remove iris_db fallback in iris_devtester/connections/connection.py"  # T010
Task: "Update log messages in iris_devtester/utils/namespace.py"  # T011
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline verification)
2. Complete Phase 2: Foundational (new iris.connect() functions)
3. Complete Phase 3: User Story 1 (remove iris_db fallback, wire up strategy selection)
4. **STOP and VALIDATE**: Run `pytest tests/unit/test_namespace_utils.py -v` — the primary bug is fixed
5. This alone resolves the reported issue

### Incremental Delivery

1. Setup + Foundational → New functions ready
2. User Story 1 → Bug fix complete, explicit configs work cleanly (MVP!)
3. User Story 2 → iris.connect() path validated end-to-end against live IRIS
4. User Story 3 → Backward compatibility verified for auto-discovered configs
5. Polish → Documentation, full regression, log review

---

## Notes

- All production changes are in 2 files: `iris_devtester/utils/namespace.py` and `iris_devtester/connections/connection.py`
- The `iris.connect()` approach was chosen over SQL/DBAPI per Constitution Principle 2 (see research.md R6)
- The `iris_db` hardcoded default is only removed from the namespace path — other utility functions (enable_callin, password, etc.) are out of scope
- Total estimated LOC delta: ~150 lines (new functions + tests)
