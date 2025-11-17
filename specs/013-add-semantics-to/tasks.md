# Tasks: Multi-Project Port Isolation

**Feature**: 013-add-semantics-to
**Input**: Design documents from `/Users/tdyar/ws/iris-devtester/specs/013-add-semantics-to/`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Summary

Enable multiple projects to use iris-devtester simultaneously without port conflicts through automatic port assignment (1972-1981) based on project directory path. Implementation uses file-based port registry with atomic locking and Docker SDK for container inspection.

**Tech Stack** (from plan.md):
- Python 3.9+
- testcontainers>=4.0.0, testcontainers-iris>=1.2.2
- docker>=6.0.0
- filelock>=3.0.0 (NEW dependency)
- pytest>=8.0.0

**Key Entities** (from data-model.md):
- PortAssignment: Tracks port-to-project mappings
- PortRegistry: Manages assignments with file locking

**API Contracts** (from contracts/):
- PortRegistry API (9 contract tests)
- IRISContainer integration (9 contract tests)

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- File paths are absolute where needed for clarity

---

## Phase 3.1: Setup & Dependencies

- [ ] **T001** Create iris_devtester/ports/ module structure
  - Files: `iris_devtester/ports/__init__.py`, `assignment.py`, `registry.py`, `exceptions.py`
  - Create `tests/contract/`, `tests/unit/ports/`, `tests/integration/ports/`

- [ ] **T002** Add filelock dependency to pyproject.toml
  - Update `dependencies` section: `filelock>=3.13.0`
  - Update `optional-dependencies.dev`: ensure docker SDK present

- [ ] **T003** [P] Create port exception classes in `iris_devtester/ports/exceptions.py`
  - PortExhaustedError, PortConflictError, PortAssignmentTimeoutError
  - Each with structured error messages (Principle #5: Fail Fast with Guidance)

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests for PortRegistry API

- [ ] **T004** [P] Contract test: assign_port() returns port in range
  - File: `tests/contract/test_port_registry_contract.py`
  - Test: `test_assign_port_returns_port_in_range()`
  - Expected to FAIL (PortRegistry not implemented yet)

- [ ] **T005** [P] Contract test: assign_port() is idempotent
  - File: `tests/contract/test_port_registry_contract.py`
  - Test: `test_assign_port_idempotent()`
  - Expected to FAIL

- [ ] **T006** [P] Contract test: preferred_port validation
  - File: `tests/contract/test_port_registry_contract.py`
  - Tests: `test_assign_port_with_preferred_port()`, `test_assign_port_raises_conflict_for_used_preferred_port()`
  - Expected to FAIL

- [ ] **T007** [P] Contract test: port exhaustion handling
  - File: `tests/contract/test_port_registry_contract.py`
  - Test: `test_assign_port_raises_exhausted_when_all_ports_used()`
  - Expected to FAIL

- [ ] **T008** [P] Contract test: release_port() removes assignment
  - File: `tests/contract/test_port_registry_contract.py`
  - Test: `test_release_port_removes_assignment()`
  - Expected to FAIL

- [ ] **T009** [P] Contract test: concurrent port assignment (race condition)
  - File: `tests/contract/test_port_registry_contract.py`
  - Test: `test_concurrent_assign_from_two_projects_unique_ports()`
  - Uses threading to simulate race condition
  - Expected to FAIL

- [ ] **T009.5** [P] Contract test: cleanup_stale() edge cases
  - File: `tests/contract/test_port_registry_contract.py`
  - Test: `test_cleanup_stale_detects_manually_removed_container()`
    - Start container, assign port, manually `docker rm`, call cleanup_stale()
    - Verify: Assignment marked stale and removed
  - Test: `test_cleanup_stale_preserves_ryuk_exited_containers()`
    - Start container, stop via IRISContainer.stop(), verify 'exited' status
    - Call cleanup_stale()
    - Verify: Assignment NOT marked stale (testcontainers cleanup in progress)
  - Test: `test_cleanup_stale_docker_daemon_restart()`
    - Mock Docker daemon restart scenario (containers persist)
    - Verify: No false positives (containers still exist)
  - Expected to FAIL (cleanup_stale not implemented yet)

### Contract Tests for IRISContainer Integration

- [ ] **T010** [P] Contract test: backwards compatibility (no port_registry)
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_backwards_compatibility_no_port_registry()`
  - Expected to FAIL (integration not implemented yet)

- [ ] **T011** [P] Contract test: auto-assignment with port_registry
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_auto_assignment_with_port_registry()`
  - Expected to FAIL

- [ ] **T012** [P] Contract test: auto-detect project path from cwd
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_auto_detect_project_path_from_cwd()`
  - Expected to FAIL

- [ ] **T013** [P] Contract test: manual port preference
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_manual_port_preference_with_registry()`
  - Expected to FAIL

- [ ] **T014** [P] Contract test: port conflict raises error
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_port_conflict_raises_error()`
  - Expected to FAIL

- [ ] **T015** [P] Contract test: stop() releases port assignment
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_stop_releases_port_assignment()`
  - Expected to FAIL

- [ ] **T016** [P] Contract test: multiple containers get unique ports
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_multiple_containers_unique_ports()`
  - Expected to FAIL

- [ ] **T017** [P] Contract test: idempotent start for same project
  - File: `tests/contract/test_container_integration_contract.py`
  - Test: `test_idempotent_start_for_same_project()`
  - Expected to FAIL

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models

- [ ] **T018** [P] Implement PortAssignment dataclass
  - File: `iris_devtester/ports/assignment.py`
  - Fields: project_path, port, assigned_at, assignment_type, status, container_name
  - Methods: `to_dict()`, `from_dict()` for JSON serialization
  - State transitions: active → released/stale
  - **Validate**: T004, T005 should start passing

- [ ] **T019** Implement PortRegistry class with file locking
  - File: `iris_devtester/ports/registry.py`
  - Depends on: T018 (PortAssignment)
  - Methods: `__init__()`, `assign_port()`, `release_port()`, `get_assignment()`, `list_all()`, `clear_all()`
  - Use filelock for atomic read-modify-write
  - JSON persistence at `~/.iris-devtester/port-registry.json`
  - **Validate**: T004-T009 should pass (all PortRegistry contract tests)

- [ ] **T020** Implement PortRegistry.cleanup_stale() with Docker SDK
  - File: `iris_devtester/ports/registry.py` (add method)
  - Depends on: T019
  - Use `docker.from_env().containers.list(all=True, filters={'name': 'iris_*'})`
  - Mark assignments as stale if container doesn't exist
  - Remove stale assignments from registry

### IRISContainer Integration

- [ ] **T021** Integrate PortRegistry into IRISContainer.__init__()
  - File: `iris_devtester/containers/iris_container.py` (modify existing)
  - Depends on: T019, T020
  - Add parameters: `port_registry`, `project_path`, `preferred_port`
  - Backwards compatibility: if port_registry is None, use default port 1972
  - Auto-detect project_path from `os.getcwd()` if None
  - **Validate**: T010-T017 should pass (all container integration tests)

- [ ] **T022** Implement IRISContainer.start() port assignment
  - File: `iris_devtester/containers/iris_container.py` (modify existing method)
  - Depends on: T021
  - Call `port_registry.assign_port()` before container start
  - Handle PortExhaustedError, PortConflictError with structured messages
  - Update container name to include project hash

- [ ] **T023** Implement IRISContainer.stop() port release
  - File: `iris_devtester/containers/iris_container.py` (modify existing method)
  - Depends on: T021
  - Call `port_registry.release_port()` after container stop
  - Only if port_registry is not None

- [ ] **T024** Add IRISContainer.get_assigned_port() and get_project_path() methods
  - File: `iris_devtester/containers/iris_container.py`
  - Depends on: T021
  - Return assigned port and project path for inspection

### CLI Commands

- [ ] **T025** [P] Implement `iris-devtester ports list` command
  - File: `iris_devtester/cli/ports.py` (new file)
  - Depends on: T019 (PortRegistry must exist)
  - Show all active/stale assignments in table format
  - Columns: Project Path, Port, Type (auto/manual), Status, Container

- [ ] **T026** [P] Implement `iris-devtester ports clear` command
  - File: `iris_devtester/cli/ports.py`
  - Depends on: T019
  - Call `PortRegistry().clear_all()`
  - Confirm before clearing (interactive)

- [ ] **T027** [P] Implement `iris-devtester ports inspect <project-path>` command
  - File: `iris_devtester/cli/ports.py`
  - Depends on: T019
  - Show detailed assignment info for specific project
  - Include container status if exists

---

## Phase 3.4: Integration Tests (End-to-End Validation)

- [ ] **T028** [P] Integration test: multi-project isolation (Acceptance #1, #3)
  - File: `tests/integration/ports/test_multi_project_isolation.py`
  - Depends on: T019, T021, T022, T023
  - Scenario: Start 2 projects simultaneously, verify unique ports, test concurrent access
  - Based on quickstart.md scenario

- [ ] **T029** [P] Integration test: port persistence (Acceptance #2)
  - File: `tests/integration/ports/test_port_persistence.py`
  - Depends on: T019, T021, T022, T023
  - Scenario: Start container, stop, restart → same port assigned

- [ ] **T030** [P] Integration test: port exhaustion handling (Acceptance #4, #5)
  - File: `tests/integration/ports/test_port_exhaustion.py`
  - Depends on: T019, T021, T022
  - Scenario: Fill 10 ports, verify 11th fails with PortExhaustedError
  - Verify error message includes remediation steps

- [ ] **T031** [P] Integration test: stale assignment cleanup
  - File: `tests/integration/ports/test_stale_cleanup.py`
  - Depends on: T020 (cleanup_stale)
  - Scenario: Start container, manually remove via Docker, call cleanup_stale()
  - Verify port released and available for reuse

- [ ] **T032** [P] Integration test: manual port override and conflicts
  - File: `tests/integration/ports/test_manual_port_override.py`
  - Depends on: T019, T021, T022
  - Scenario: Manual port assignment, conflict detection, error handling

---

## Phase 3.5: Polish & Documentation

### Unit Tests

- [ ] **T033** [P] Unit test: PortAssignment serialization (to_dict/from_dict)
  - File: `tests/unit/ports/test_port_assignment.py`
  - Test JSON round-trip, datetime handling, field validation

- [ ] **T034** [P] Unit test: PortRegistry file locking timeout
  - File: `tests/unit/ports/test_port_registry.py`
  - Mock filelock timeout, verify PortAssignmentTimeoutError raised

- [ ] **T035** [P] Unit test: Port exception error messages
  - File: `tests/unit/ports/test_exceptions.py`
  - Verify structured error messages include remediation steps (Principle #5)

### Performance & Quality

- [ ] **T036** Performance test: Port assignment <5 seconds (NFR-001)
  - File: `tests/integration/ports/test_performance.py`
  - Measure latency for assign_port() under load
  - Verify <5 second timeout budget met

- [ ] **T037** Verify 95%+ test coverage for ports module
  - Run: `pytest --cov=iris_devtester.ports --cov-report=term-missing`
  - Constitutional requirement (Principle #7)

### Documentation

- [ ] **T038** [P] Update README.md with multi-project port isolation usage
  - Add section: "Multi-Project Development"
  - Include example: Using port registry with IRISContainer

- [ ] **T039** [P] Update CLAUDE.md with ports module context
  - Already done by update-agent-context.sh in Phase 1
  - Verify: File locking patterns, Docker SDK notes, port registry design

- [ ] **T040** Execute quickstart.md scenario manually
  - Run: `python specs/013-add-semantics-to/quickstart.md` (as Python script)
  - Verify: Two projects get unique ports, concurrent access works, cleanup succeeds

---

## Dependencies

### Critical Path (Sequential)
1. **Setup** (T001-T003) → Everything else
2. **Contract Tests** (T004-T017) → Implementation (MUST FAIL FIRST - TDD)
3. **PortAssignment** (T018) → PortRegistry (T019)
4. **PortRegistry** (T019) → cleanup_stale (T020)
5. **PortRegistry** (T019) → IRISContainer integration (T021)
6. **IRISContainer integration** (T021) → start/stop modifications (T022, T023)
7. **Core implementation** (T018-T024) → Integration tests (T028-T032)

### Parallel Opportunities
- **T004-T017**: All contract tests (different files)
- **T018, T003**: PortAssignment and exceptions (different files)
- **T025-T027**: All CLI commands (same file, but independent functions)
- **T028-T032**: All integration tests (different files)
- **T033-T035**: All unit tests (different files)
- **T038-T039**: Documentation updates (different files)

---

## Parallel Execution Examples

### Example 1: Contract Tests (T004-T017)
```bash
# All 14 contract tests can run in parallel (different test files):
Task: "Contract test: assign_port() returns port in range in tests/contract/test_port_registry_contract.py"
Task: "Contract test: assign_port() is idempotent in tests/contract/test_port_registry_contract.py"
Task: "Contract test: preferred_port validation in tests/contract/test_port_registry_contract.py"
Task: "Contract test: port exhaustion handling in tests/contract/test_port_registry_contract.py"
Task: "Contract test: release_port() removes assignment in tests/contract/test_port_registry_contract.py"
Task: "Contract test: concurrent port assignment in tests/contract/test_port_registry_contract.py"
Task: "Contract test: backwards compatibility in tests/contract/test_container_integration_contract.py"
Task: "Contract test: auto-assignment in tests/contract/test_container_integration_contract.py"
# ... etc
```

### Example 2: Integration Tests (T028-T032)
```bash
# All integration tests can run in parallel (different files):
Task: "Integration test: multi-project isolation in tests/integration/ports/test_multi_project_isolation.py"
Task: "Integration test: port persistence in tests/integration/ports/test_port_persistence.py"
Task: "Integration test: port exhaustion in tests/integration/ports/test_port_exhaustion.py"
Task: "Integration test: stale cleanup in tests/integration/ports/test_stale_cleanup.py"
Task: "Integration test: manual port override in tests/integration/ports/test_manual_port_override.py"
```

### Example 3: CLI Commands (T025-T027)
```bash
# CLI commands are in same file but independent functions - can parallelize:
Task: "Implement iris-devtester ports list in iris_devtester/cli/ports.py"
Task: "Implement iris-devtester ports clear in iris_devtester/cli/ports.py"
Task: "Implement iris-devtester ports inspect in iris_devtester/cli/ports.py"
```

---

## Validation Checklist
*GATE: All must pass before feature is complete*

- [x] All contracts have corresponding tests (T004-T017 cover both contracts)
- [x] All entities have model tasks (T018: PortAssignment, T019: PortRegistry)
- [x] All tests come before implementation (Phase 3.2 before 3.3)
- [x] Parallel tasks truly independent (verified: different files or independent functions)
- [x] Each task specifies exact file path ✓
- [x] No task modifies same file as another [P] task (CLI tasks in same file but independent)
- [x] Constitutional principles enforced:
  - Principle #5: Structured error messages (T003, T035)
  - Principle #7: 95%+ coverage (T037)
  - TDD workflow: Tests before implementation

---

## Success Criteria (from plan.md)

- ✓ All contract tests pass (T004-T017)
- ✓ All integration tests pass (T028-T032)
- ✓ Quickstart.md completes successfully (T040)
- ✓ Port assignment <5 seconds (T036: NFR-001)
- ✓ 95%+ test coverage (T037: Principle #7)
- ✓ No breaking changes to existing IRISContainer users (T010: backwards compatibility test)

---

**Total Tasks**: 41 (40 original + T009.5 edge case test)
**Estimated Parallel Batches**:
- Batch 1: T001-T003 (setup)
- Batch 2: T004-T017 including T009.5 (15 contract tests in parallel)
- Batch 3: T018, T003 (models in parallel)
- Batch 4: T019-T020 (sequential)
- Batch 5: T021-T024 (sequential - same file)
- Batch 6: T025-T027 (CLI in parallel)
- Batch 7: T028-T032 (5 integration tests in parallel)
- Batch 8: T033-T035 (unit tests in parallel)
- Batch 9: T036-T037 (performance/coverage)
- Batch 10: T038-T040 (docs/validation)

**Estimated Time**: 8-12 hours for experienced developer following TDD workflow

---

*Generated from Feature 013 design artifacts - Based on IRIS DevTools Constitution v1.0.0*
