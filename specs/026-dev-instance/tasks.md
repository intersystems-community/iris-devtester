# Tasks: The Dev Instance (Warm Start)

**Feature**: The Dev Instance (Warm Start)
**Branch**: `026-dev-instance`
**Status**: Pending

## Implementation Strategy

We will follow an **MVP-first** approach, prioritizing **User Story 1 (Instant Connection)** to deliver the "SQLite Vision" as quickly as possible. Foundational Docker volume and container management will be implemented first to support this.

## Phase 1: Setup

- [ ] T000 Fix core container port mapping bug in `iris_devtester/utils/iris_container_adapter.py`
- [ ] T001 Create `iris_devtester/containers/dev_instance.py` (Implement `DevInstance` and `DockerVolumeManager` from `data-model.md`)
- [ ] T002 Create `iris_devtester/cli/dev_commands.py` (Implement `idt dev` command set from `contracts/cli.md`)
- [ ] T003 [P] Create `tests/unit/test_dev_instance_logic.py` for logic verification
- [ ] T004 [P] Create `tests/integration/test_dev_instance.py` for container verification

## Phase 2: Foundational (Engine & Volume Management)

- [ ] T005 Implement `DockerVolumeManager` in `iris_devtester/containers/dev_instance.py` to handle `idt-dev-data`
- [ ] T006 Implement `DevInstanceManager` in `iris_devtester/containers/dev_instance.py` with `get_or_create()`, `is_running()`, and `ensure_ready()`
- [ ] T007 [P] Implement Project ID hashing logic in `iris_devtester/utils/namespace.py` (referenced in US1)

## Phase 3: User Story 1 - Instant Connection (Priority: P1)

**Goal**: Achieve < 500ms connection time when the dev engine is running.

- [ ] T008 [US1] Update `discover_config()` in `iris_devtester/config/discovery.py` to prioritize `idt-dev-instance`
- [ ] T009 [US1] Implement Implicit Start logic in `get_connection()` within `iris_devtester/connections/connection.py`
- [ ] T010 [US1] Integrate Project-specific Namespace auto-creation into the connection flow in `iris_devtester/connections/connection.py`
- [ ] T011 [US1] Implement `IRISContainer.dev()` factory method in `iris_devtester/containers/iris_container.py`
- [ ] T012 [P] [US1] Verify warm-start connection performance (< 500ms) in `tests/integration/test_dev_instance.py`
- [ ] T012a [US1] Verify volume persistence (data survives `down` / `up` cycle) in `tests/integration/test_dev_instance.py`
- [ ] T012b [US1] Verify project isolation (Project A cannot see Project B data) in `tests/integration/test_dev_instance.py`

## Phase 4: User Story 2 - Managed Dev Instance Lifecycle (Priority: P2)

**Goal**: Provide a simple CLI for managing the persistent engine.

- [ ] T013 [US2] Implement `idt dev up` command in `iris_devtester/cli/dev_commands.py`
- [ ] T014 [US2] Implement `idt dev down` command in `iris_devtester/cli/dev_commands.py` (with `--volumes` support)
- [ ] T015 [US2] Implement `idt dev status` command in `iris_devtester/cli/dev_commands.py`
- [ ] T016 [US2] Implement `idt dev logs` command in `iris_devtester/cli/dev_commands.py`
- [ ] T017 [US2] Register `dev` group in the main CLI entry point `iris_devtester/cli/__init__.py`

## Phase 5: User Story 3 - Automatic Readiness Optimization (Priority: P3)

**Goal**: Minimize cold-start overhead.

- [ ] T018 [US3] Implement optimized TCP port probing (50ms timeout) in `iris_devtester/containers/wait_strategies.py`
- [ ] T019 [US3] Refactor `DevInstanceManager` to use the optimized probe for fast-path checks
- [ ] T020 [P] [US3] Benchmark cold-start vs warm-start readiness in `tests/integration/test_dev_instance.py`

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T021 [P] Ensure all `docker exec` calls in the dev instance use `-u irisowner`
- [ ] T022 Update `README.md` with "The Dev Instance" section and `idt dev` commands
- [ ] T023 Ensure all new public methods have Google-style docstrings
- [ ] T024 Final validation of SQLite-level ergonomics Principle #9 compliance

## Dependencies

1. **Phase 2** (Foundational) blocks **Phase 3** (US1).
2. **Phase 3** (US1) provides the core logic for **Phase 4** (US2).
3. **Phase 5** (US3) is an optimization of Phase 2/3.

## Parallel Execution Examples

### Parallel Track A (Implementation)
- T005, T006, T007 (Foundational)

### Parallel Track B (Testing/Refinement)
- T003, T004 (Setup Tests)
- T012, T020 (Integration Benchmarks)
- T021, T023 (Refinement)
