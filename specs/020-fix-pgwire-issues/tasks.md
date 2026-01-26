---
description: "Task list for fixing pgwire-identified bugs in iris-devtester"
---

# Tasks: Fix pgwire-identified bugs in iris-devtester

**Input**: Design documents from `/specs/020-fix-pgwire-issues/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: TDD is mandatory per Constitution Principle #3. Tests MUST be written and fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `iris_devtester/`
- **Tests**: `tests/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and environment verification

- [ ] T001 Verify Docker environment and IRIS connectivity for integration tests
- [ ] T002 [P] Configure pytest to target IRIS 2024.1+ for local validation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure updates shared across fixes

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Add common test fixtures for IRIS 2024.1+ environments in tests/conftest.py
- [ ] T005 [P] Refactor `tests/conftest.py` to use `iris_container.get_connection()` and remove manual `time.sleep()` calls (Dogfooding)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 2 - Reliable Security Flag Management (Priority: P1) 🎯 MVP

**Goal**: Switch to `Security.Users.Modify` API for reliable ChangePassword flag clearing

**Independent Test**: Password reset call consistently clears security flags in IRIS 2024.1+ containers

### Tests for User Story 2
- [ ] T006 [US2] Create integration test for reliable password reset validation in tests/integration/test_password_reset_validation.py

### Implementation for User Story 2
- [ ] T007 [US2] Implement `##class(Security.Users.Modify)` logic string in `iris_devtester/utils/password_reset.py`
- [ ] T008 [US2] Refactor `_harden_iris_user` to use the `Modify` API for flag management in `iris_devtester/utils/password_reset.py`

**Checkpoint**: User Story 2 is fully functional and testable independently

---

## Phase 4: User Story 1 - Connect as non-_SYSTEM user (Priority: P1)

**Goal**: Allow auto-remediation for any connecting user (e.g., SuperUser)

**Independent Test**: `get_connection(username="SuperUser")` successfully triggers password reset for SuperUser

### Tests for User Story 1
- [ ] T009 [US1] Create integration test for custom user auto-remediation in tests/integration/test_custom_user_remediation.py

### Implementation for User Story 1
- [ ] T010 [US1] Update `reset_password` signature to accept `username` in `iris_devtester/utils/password_reset.py`
- [ ] T011 [US1] Update `reset_password_if_needed` to accept `username` in `iris_devtester/utils/password_reset.py`
- [ ] T012 [US1] Update `reset-password` CLI command to include user parameter in `iris_devtester/cli/container.py`
- [ ] T013 [US1] Pass `username` from connection attempt to `reset_password_if_needed` in `iris_devtester/connections/retry.py`

**Checkpoint**: User Stories 1 AND 2 work together to support enterprise user auto-remediation

---

## Phase 5: User Story 3 - Deterministic Container Readiness (Priority: P1)

**Goal**: Ensure IRIS security system is initialized before signaling container readiness

**Independent Test**: First connection attempt after readiness signal always succeeds

### Tests for User Story 3
- [ ] T014 [US3] Create integration test simulating startup race condition in tests/integration/test_container_readiness.py

### Implementation for User Story 3
- [ ] T015 [US3] Implement `iris session` application check in `IRISReadyWaitStrategy` in `iris_devtester/containers/wait_strategies.py`
- [ ] T023 [US3] Update `IRISContainer.wait_for_ready` to use `IRISReadyWaitStrategy` by default (formerly T004)

**Checkpoint**: Container readiness is now deterministic

---

## Phase 6: User Story 4 - Refreshable Test Data (Priority: P2)

**Goal**: Support re-loading fixtures into existing namespaces

**Independent Test**: `load_fixture` with `force_refresh=True` replaces data in existing USER namespace

### Tests for User Story 4
- [ ] T016 [US4] Create integration test for fixture refresh behavior in tests/integration/test_fixture_refresh.py

### Implementation for User Story 4
- [ ] T017 [US4] Add `force_refresh` parameter to `DATFixtureLoader.load_fixture` in `iris_devtester/fixtures/loader.py`
- [ ] T018 [US4] Implement namespace/database deletion logic for refresh in `iris_devtester/fixtures/loader.py`
- [ ] T019 [US4] Update `fixture load` CLI command to include `--force` flag in `iris_devtester/cli/fixture_commands.py`

**Checkpoint**: All user stories are complete and functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [ ] T020 [P] Update `AGENTS.md` and `README.md` with new parameters and capabilities
- [ ] T021 [P] Update troubleshooting guides in `docs/` with readiness check details
- [ ] T022 Run full integration test suite to verify no regressions across all features (Validates Dogfooding in conftest.py)


---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Independent
- **Foundational (Phase 2)**: Depends on Phase 1
- **US2 (Phase 3)**: Depends on Phase 2 (Foundational logic for reliable flags)
- **US1 (Phase 4)**: Depends on Phase 3 (Uses the improved API for custom users)
- **US3 (Phase 5)**: Independent after Phase 2
- **US4 (Phase 6)**: Independent after Phase 2
- **Polish (Phase 7)**: Depends on all implementation phases

### Parallel Opportunities

- Phase 5 (US3) and Phase 6 (US4) can run in parallel with each other and with Phase 3/4.
- T018 and T019 in Polish phase can run in parallel.

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete Setup + Foundational
2. Implement US2 (Reliable API)
3. Implement US1 (Parametrization)
4. **STOP and VALIDATE**: Verify custom user connections work reliably.

### Incremental Delivery

1. Foundation + US2 + US1 -> Reliable enterprise connections (MVP!)
2. US3 -> Stable startup
3. US4 -> Efficient data refresh
