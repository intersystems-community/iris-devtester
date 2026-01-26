# Tasks: Fast Container Startup & Dev Cycle Optimization

**Input**: Design documents from `/specs/018-fast-container-startup/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/
**Branch**: `018-fast-container-startup`

---

## User Story Mapping

| Story | Priority | Description | Requirements |
|-------|----------|-------------|--------------|
| US1 | P1 | Container Reuse | FR-001, FR-002, FR-003 |
| US2 | P1 | Health Check Caching | FR-007, FR-008, FR-009 |
| US3 | P2 | Pre-baked Dev Image | FR-004, FR-005, FR-006 |
| US4 | P2 | AI-Friendly Output | FR-010-FR-014 |
| US5 | P3 | pytest Plugin Integration | FR-015, FR-016, FR-017 |

---

## Phase 1: Setup

- [ ] T001 Create directory structure: `iris_devtester/containers/`, `iris_devtester/output/`, `docker/`
- [ ] T002 [P] Create `iris_devtester/containers/__init__.py` with module exports
- [ ] T003 [P] Create `iris_devtester/output/__init__.py` with module exports

---

## Phase 2: Foundational (Blocking)

**HealthCache must be implemented first - used by ContainerPool**

- [ ] T004 [P] Copy contract tests from `specs/018-fast-container-startup/contracts/health_cache.py` to `tests/contract/test_health_cache_contract.py`
- [ ] T005 Implement `HealthCacheEntry` dataclass in `iris_devtester/containers/health_cache.py`
- [ ] T006 Implement `HealthCache` class with get/set/invalidate in `iris_devtester/containers/health_cache.py`
- [ ] T007 Implement `HealthCache.from_env()` for TTL from environment in `iris_devtester/containers/health_cache.py`
- [ ] T008 Verify all health_cache contract tests pass

---

## Phase 3: User Story 1 - Container Reuse [US1]

**Goal**: Reuse existing IRIS containers to reduce test startup from 90s to <5s
**Independent Test**: `pytest tests/contract/test_container_pool_contract.py tests/integration/test_container_reuse.py`

- [ ] T009 [P] [US1] Copy contract tests from `specs/018-fast-container-startup/contracts/container_pool.py` to `tests/contract/test_container_pool_contract.py`
- [ ] T010 [US1] Implement `ContainerRef` dataclass in `iris_devtester/containers/pool.py`
- [ ] T011 [US1] Implement `ContainerStatus` enum in `iris_devtester/containers/pool.py`
- [ ] T012 [US1] Implement `ContainerPool` singleton with `instance()` and `_reset()` in `iris_devtester/containers/pool.py`
- [ ] T013 [US1] Implement `ContainerPool.get_or_create()` using Docker SDK in `iris_devtester/containers/pool.py`
- [ ] T014 [US1] Implement `ContainerPool.acquire()` and `release()` in `iris_devtester/containers/pool.py`
- [ ] T015 [US1] Implement `ContainerPool.health_check()` with cache integration in `iris_devtester/containers/pool.py`
- [ ] T016 [US1] Verify all container_pool contract tests pass
- [ ] T017 [P] [US1] Create integration test `tests/integration/test_container_reuse.py` for end-to-end container reuse

---

## Phase 4: User Story 2 - Namespace Isolation [US2]

**Goal**: Provide namespace-based test isolation so tests don't pollute each other
**Independent Test**: `pytest tests/contract/test_namespace_contract.py tests/integration/test_namespace_isolation.py`

- [ ] T018 [P] [US2] Copy contract tests from `specs/018-fast-container-startup/contracts/test_namespace.py` to `tests/contract/test_namespace_contract.py`
- [ ] T019 [US2] Implement `TestNamespace` dataclass in `iris_devtester/containers/namespace.py`
- [ ] T020 [US2] Implement `TestNamespace.create_unique()` factory method in `iris_devtester/containers/namespace.py`
- [ ] T021 [US2] Implement `TestNamespace.create()` using Config.Namespaces via iris.connect() in `iris_devtester/containers/namespace.py`
- [ ] T022 [US2] Implement `TestNamespace.drop()` with idempotency in `iris_devtester/containers/namespace.py`
- [ ] T023 [US2] Implement `TestNamespace.execute_sql()` using DBAPI in `iris_devtester/containers/namespace.py`
- [ ] T024 [US2] Implement `TestNamespace.register_cleanup()` with atexit handler in `iris_devtester/containers/namespace.py`
- [ ] T025 [US2] Verify all namespace contract tests pass
- [ ] T026 [P] [US2] Create integration test `tests/integration/test_namespace_isolation.py` for parallel namespace isolation

---

## Phase 5: User Story 3 - Pre-baked Dev Image [US3]

**Goal**: Provide pre-configured dev image with passwords already reset (saves 8s per startup)
**Independent Test**: `docker build -f docker/Dockerfile.dev . && docker run --rm iris-devtester-dev:latest iris session IRIS -U USER "Write 1"`

- [ ] T027 [US3] Create `docker/Dockerfile.dev` based on intersystemsdc/iris-community:latest
- [ ] T028 [US3] Add password reset script to Dockerfile.dev (PasswordExternal, ChangePassword=0)
- [ ] T029 [US3] Add CallIn service enablement to Dockerfile.dev
- [ ] T030 [US3] Add build instructions to `docker/README.md`
- [ ] T031 [US3] Test Dockerfile.dev builds and starts correctly

---

## Phase 6: User Story 4 - AI-Friendly Output [US4]

**Goal**: Reduce test output from 200+ lines to <50 lines for AI token efficiency
**Independent Test**: `pytest tests/contract/test_output_formatter_contract.py tests/unit/test_output_formatter.py`

- [ ] T032 [P] [US4] Copy contract tests from `specs/018-fast-container-startup/contracts/output_formatter.py` to `tests/contract/test_output_formatter_contract.py`
- [ ] T033 [US4] Implement `OutputFormatter` dataclass in `iris_devtester/output/formatter.py`
- [ ] T034 [US4] Implement `OutputFormatter._truncate_middle()` in `iris_devtester/output/formatter.py`
- [ ] T035 [US4] Implement `OutputFormatter._deduplicate_lines()` in `iris_devtester/output/formatter.py`
- [ ] T036 [US4] Implement `OutputFormatter.format_test_output()` in `iris_devtester/output/formatter.py`
- [ ] T037 [US4] Implement `OutputFormatter.summarize_container_logs()` in `iris_devtester/output/formatter.py`
- [ ] T038 [US4] Implement `OutputFormatter.format_error()` in `iris_devtester/output/formatter.py`
- [ ] T039 [US4] Verify all output_formatter contract tests pass
- [ ] T040 [P] [US4] Create unit test `tests/unit/test_output_formatter.py` for edge cases

---

## Phase 7: User Story 5 - pytest Plugin [US5]

**Goal**: Add `--reuse-container` flag to pytest for seamless container reuse
**Independent Test**: `pytest --co -q --reuse-container` (should not error)

- [ ] T041 [US5] Add `pytest_addoption` hook for `--reuse-container` flag in `iris_devtester/testing/pytest_plugin.py`
- [ ] T042 [US5] Add `reuse_container` fixture (session scope) in `iris_devtester/testing/pytest_plugin.py`
- [ ] T043 [US5] Update `iris_container` fixture to use ContainerPool when `--reuse-container` in `iris_devtester/testing/pytest_plugin.py`
- [ ] T044 [US5] Add auto-detection of `iris-dev` container in `iris_devtester/testing/pytest_plugin.py`
- [ ] T045 [US5] Add warning message when container reuse enabled in `iris_devtester/testing/pytest_plugin.py`
- [ ] T046 [US5] Test `--reuse-container` flag works correctly

---

## Phase 8: Polish & Integration

- [ ] T047 Update `iris_devtester/containers/__init__.py` to export ContainerPool, TestNamespace, HealthCache
- [ ] T048 Update `iris_devtester/output/__init__.py` to export OutputFormatter
- [ ] T049 [P] Add feature documentation to `docs/features/fast-container-startup.md`
- [ ] T050 [P] Update CHANGELOG.md with v1.6.0 release notes
- [ ] T051 Run full test suite: `pytest tests/ --no-cov -q`
- [ ] T052 Validate quickstart scenarios from `specs/018-fast-container-startup/quickstart.md`

---

## Dependencies

```
Phase 2 (HealthCache) ─┬─► Phase 3 (ContainerPool) ─► Phase 4 (Namespace)
                       │                              │
                       └──────────────────────────────┴─► Phase 7 (pytest plugin)

Phase 6 (OutputFormatter) is independent, can run in parallel with US1-US5

Phase 5 (Dockerfile) is independent, can run anytime
```

**Blocking Dependencies**:
- T005-T008 (HealthCache) blocks T012-T016 (ContainerPool uses HealthCache)
- T010-T016 (ContainerPool) blocks T019-T026 (Namespace uses ContainerRef)
- T012-T016 (ContainerPool) blocks T041-T046 (pytest plugin uses ContainerPool)

**Independent Tracks** (can run in parallel):
- US3 (Dockerfile) - no code dependencies
- US4 (OutputFormatter) - no code dependencies

---

## Parallel Execution Examples

### Example 1: Contract Tests (Phase start)
```bash
# Launch T004, T009, T018, T032 in parallel (different files)
pytest tests/contract/test_health_cache_contract.py &
pytest tests/contract/test_container_pool_contract.py &
pytest tests/contract/test_namespace_contract.py &
pytest tests/contract/test_output_formatter_contract.py &
```

### Example 2: Independent User Stories
```bash
# US3 and US4 can run in parallel with US1/US2
# Track A: Container reuse (US1, US2)
# Track B: Dockerfile (US3)
# Track C: OutputFormatter (US4)
```

---

## Implementation Strategy

**MVP (User Story 1 only)**:
- Complete Phase 1-3 (Setup, HealthCache, ContainerPool)
- Delivers 80% of value (container reuse)
- ~16 tasks, testable independently

**Incremental Delivery**:
1. MVP: Container reuse working (`--reuse-container` basic)
2. +US2: Namespace isolation (parallel tests)
3. +US3: Pre-baked image (faster first-time setup)
4. +US4: AI-friendly output (token efficiency)
5. +US5: Full pytest integration (seamless UX)

---

## Validation Checklist

- [x] All contracts have corresponding tests (4 contract files → 4 test files)
- [x] All entities have model tasks (ContainerPool, TestNamespace, HealthCache, OutputFormatter)
- [x] All tests come before implementation (TDD order maintained)
- [x] Parallel tasks truly independent (different files marked [P])
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] User stories independently testable

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 52 |
| Phase 1 (Setup) | 3 |
| Phase 2 (Foundational) | 5 |
| Phase 3 (US1 - Container Reuse) | 9 |
| Phase 4 (US2 - Namespace) | 9 |
| Phase 5 (US3 - Dockerfile) | 5 |
| Phase 6 (US4 - Output) | 9 |
| Phase 7 (US5 - pytest) | 6 |
| Phase 8 (Polish) | 6 |
| Parallel Opportunities | 12 tasks marked [P] |

**Suggested MVP Scope**: Phases 1-3 (17 tasks) - delivers container reuse, the core 80% speedup.
