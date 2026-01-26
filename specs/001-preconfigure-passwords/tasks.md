# Tasks: Pre-configure Passwords at Container Startup

**Input**: Design documents from `/specs/001-preconfigure-passwords/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Included per project standards (pytest for Python library)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- **Library code**: `iris_devtester/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/contract/`

---

## Phase 1: Setup

**Purpose**: No new project setup needed - extending existing library

- [x] T001 Verify current test suite passes before changes by running `pytest tests/`
- [x] T002 Review existing IRISContainer.start() implementation in iris_devtester/containers/iris_container.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure changes that enable all user story implementations

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Add `_preconfigure_password`, `_password_preconfigured`, `_preconfigure_username` attributes to IRISContainer.__init__() in iris_devtester/containers/iris_container.py
- [x] T004 Add `_should_preconfigure()` private method to detect if pre-configuration should be used (checks env var or explicit flag) in iris_devtester/containers/iris_container.py
- [x] T005 Add `_apply_password_preconfig()` private method to apply IRIS_PASSWORD/IRIS_USERNAME env vars to container in iris_devtester/containers/iris_container.py
- [x] T006 Add `_verify_preconfig_success()` private method to verify credentials work after container ready in iris_devtester/containers/iris_container.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 + User Story 2 - Core Pre-configuration with Backward Compatibility (Priority: P1) 🎯 MVP

**Goal**: Enable password pre-configuration via IRIS_PASSWORD env var while maintaining 100% backward compatibility

**Independent Test**: Start container with IRIS_PASSWORD env var set, verify immediate connection without password reset step. Also verify existing behavior unchanged when env var not set.

**Note**: US1 and US2 are combined because backward compatibility (US2) must be verified alongside the new feature (US1) - they are not independently deliverable.

### Tests for User Story 1+2

- [x] T007 [P] [US1] Create contract test for pre-configuration detection in tests/contract/test_preconfig_contract.py
- [x] T008 [P] [US2] Create contract test for backward compatibility (no env var = password reset) in tests/contract/test_preconfig_contract.py
- [x] T009 [P] [US1] Create integration test for env var pre-configuration in tests/integration/test_password_preconfig_integration.py
- [x] T010 [P] [US2] Create integration test for existing behavior unchanged in tests/integration/test_password_preconfig_integration.py

### Implementation for User Story 1+2

- [x] T011 [US1] Modify IRISContainer.start() to call _should_preconfigure() and _apply_password_preconfig() before super().start() in iris_devtester/containers/iris_container.py
- [x] T012 [US1] Modify IRISContainer.start() to call _verify_preconfig_success() after container ready in iris_devtester/containers/iris_container.py
- [x] T013 [US1] Implement fallback logic: if _verify_preconfig_success() returns False, call existing reset_password() in iris_devtester/containers/iris_container.py
- [x] T014 [US1] Add INFO logging when pre-configuration is used vs password reset in iris_devtester/containers/iris_container.py
- [x] T015 [US2] Ensure start() behavior unchanged when IRIS_PASSWORD env var not set (existing password reset path) in iris_devtester/containers/iris_container.py
- [x] T016 [US1] Add unit tests for _should_preconfigure() logic in tests/unit/test_password_preconfig.py
- [x] T017 [US1] Add unit tests for _apply_password_preconfig() logic in tests/unit/test_password_preconfig.py

**Checkpoint**: User Story 1+2 complete - pre-configuration works via env var with fallback, existing behavior preserved

---

## Phase 4: User Story 3 - Programmatic API (Priority: P2)

**Goal**: Provide explicit API methods for password pre-configuration

**Independent Test**: Use `with_preconfigured_password()` or `with_credentials()` methods and verify immediate authentication

### Tests for User Story 3

- [x] T018 [P] [US3] Create contract test for with_preconfigured_password() method in tests/contract/test_preconfig_contract.py
- [x] T019 [P] [US3] Create contract test for with_credentials() method in tests/contract/test_preconfig_contract.py
- [x] T020 [P] [US3] Create integration test for programmatic API in tests/integration/test_password_preconfig_integration.py

### Implementation for User Story 3

- [x] T021 [US3] Implement with_preconfigured_password(password: str) method returning self in iris_devtester/containers/iris_container.py
- [x] T022 [US3] Implement with_credentials(username: str, password: str) method returning self in iris_devtester/containers/iris_container.py
- [x] T023 [US3] Update _should_preconfigure() to check explicit API flag (not just env var) in iris_devtester/containers/iris_container.py
- [x] T024 [US3] Add precedence logic: API > env var when both present in iris_devtester/containers/iris_container.py
- [x] T025 [US3] Add unit tests for with_preconfigured_password() in tests/unit/test_password_preconfig.py
- [x] T026 [US3] Add unit tests for with_credentials() in tests/unit/test_password_preconfig.py

**Checkpoint**: User Story 3 complete - programmatic API works alongside env var approach

---

## Phase 5: User Story 4 - CI/CD Optimization (Priority: P3)

**Goal**: Validate feature works in CI/CD context (already enabled by US1, this is validation)

**Independent Test**: Set IRIS_PASSWORD in CI-like context, verify pre-configuration automatic

### Tests for User Story 4

- [x] T027 [P] [US4] Create integration test simulating CI environment variables in tests/integration/test_password_preconfig_integration.py

### Implementation for User Story 4

- [x] T028 [US4] Verify IRIS_PASSWORD detection works from os.environ (already implemented in US1) in iris_devtester/containers/iris_container.py
- [x] T029 [US4] Add documentation example for CI/CD usage in specs/001-preconfigure-passwords/quickstart.md

**Checkpoint**: User Story 4 complete - CI/CD use case validated

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T030 [P] Add edge case test: invalid password (empty) in tests/unit/test_password_preconfig.py
- [x] T031 [P] Add edge case test: unsupported image fallback in tests/integration/test_password_preconfig_integration.py
- [x] T032 [P] Add edge case test: API and env var conflict (API wins) in tests/unit/test_password_preconfig.py
- [x] T033 Update docstrings for all new methods in iris_devtester/containers/iris_container.py
- [x] T034 Add type hints for all new methods in iris_devtester/containers/iris_container.py
- [x] T035 Run full test suite and verify no regressions: `pytest tests/`
- [x] T036 Run mypy type checking: `mypy iris_devtester/`
- [x] T037 Run linting: `black . && isort . && flake8 iris_devtester/`
- [ ] T038 Validate quickstart.md examples work end-to-end (requires Docker)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Stories 1+2 (P1): Must complete first (MVP)
  - User Story 3 (P2): Can start after US1+2 complete
  - User Story 4 (P3): Can start after US1 complete (validation only)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1+2 (P1)**: Can start after Foundational (Phase 2) - Core feature + backward compat
- **User Story 3 (P2)**: Depends on US1+2 (uses same _should_preconfigure logic)
- **User Story 4 (P3)**: Depends on US1 (validates env var detection)

### Within Each User Story

- Tests written FIRST, ensure they FAIL before implementation
- Private methods before public API
- Core logic before edge cases
- Verify tests pass after implementation

### Parallel Opportunities

- T007, T008, T009, T010 can run in parallel (different test files/cases)
- T018, T019, T020 can run in parallel
- T030, T031, T032 can run in parallel (edge case tests)
- Phase 6 polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1+2 Tests

```bash
# Launch all tests for User Story 1+2 together:
Task: "Contract test for pre-configuration detection in tests/contract/test_preconfig_contract.py"
Task: "Contract test for backward compatibility in tests/contract/test_preconfig_contract.py"
Task: "Integration test for env var pre-configuration in tests/integration/test_password_preconfig_integration.py"
Task: "Integration test for existing behavior unchanged in tests/integration/test_password_preconfig_integration.py"
```

---

## Implementation Strategy

### MVP First (User Story 1+2 Only)

1. Complete Phase 1: Setup (verify baseline)
2. Complete Phase 2: Foundational (add private methods)
3. Complete Phase 3: User Story 1+2 (core feature + backward compat)
4. **STOP and VALIDATE**: Test pre-configuration works, existing behavior unchanged
5. Can release as minor version bump

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1+2 → Test independently → Release v1.x.0 (MVP!)
3. Add User Story 3 → Test independently → Release v1.x.1 (API enhancement)
4. Add User Story 4 → Validate CI/CD → Documentation update
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 combined because backward compatibility cannot be tested independently
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Single file modifications (iris_container.py) - most tasks are sequential within that file

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 38 |
| **Phase 1 (Setup)** | 2 |
| **Phase 2 (Foundational)** | 4 |
| **Phase 3 (US1+2)** | 11 |
| **Phase 4 (US3)** | 9 |
| **Phase 5 (US4)** | 3 |
| **Phase 6 (Polish)** | 9 |
| **Parallel Opportunities** | 14 tasks marked [P] |

**MVP Scope**: Phases 1-3 (17 tasks) delivers core value
