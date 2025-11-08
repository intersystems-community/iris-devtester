# Tasks: Docker-Compose & Existing Container Support

**Input**: Design documents from `/Users/tdyar/ws/iris-devtester/specs/006-address-docker-compose/`
**Prerequisites**: plan.md ✅, spec.md ✅
**Branch**: `006-address-docker-compose`
**Target**: v1.0.1 (HIGH priority items)

## Execution Flow

Based on plan.md Phase 1 design and API contracts:
1. **Tech Stack**: Python 3.9+, Click (CLI), Docker SDK
2. **Core Utilities**: enable_callin.py, test_connection.py, container_status.py
3. **CLI Module**: container_commands.py (4 commands)
4. **IRISContainer Enhancement**: attach() class method
5. **Documentation**: Docker-compose example, README updates

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Exact file paths included in each task

## Phase 3.1: Setup

- [x] **T001** Create Python module stubs for new utilities
  Files: `iris_devtester/utils/enable_callin.py`, `iris_devtester/utils/test_connection.py`, `iris_devtester/utils/container_status.py`
  Purpose: Establish file structure per plan.md Phase 1

- [x] **T002** Create CLI module stub for container commands
  File: `iris_devtester/cli/container_commands.py`
  Purpose: New Click command group for container operations

- [x] **T003** [P] Verify dependencies in pyproject.toml
  Check: `click>=8.0.0`, `docker>=6.0.0` already present (per plan.md)
  No changes needed - document verification

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (Utilities)

- [ ] **T004** [P] Contract test: enable_callin_service signature
  File: `tests/contract/test_enable_callin_api.py`
  Contract: `enable_callin_service(container_name: str, timeout: int) -> Tuple[bool, str]`
  Verify: Function exists, accepts params, returns (bool, str)

- [ ] **T005** [P] Contract test: test_connection signature
  File: `tests/contract/test_test_connection_api.py`
  Contract: `test_connection(container_name: str, namespace: str, timeout: int) -> Tuple[bool, str]`
  Verify: Function exists, accepts params, returns (bool, str)

- [ ] **T006** [P] Contract test: get_container_status signature
  File: `tests/contract/test_container_status_api.py`
  Contract: `get_container_status(container_name: str) -> Tuple[bool, str]`
  Verify: Function exists, returns status report

### Contract Tests (CLI Commands)

- [ ] **T007** [P] Contract test: CLI reset-password command exists
  File: `tests/contract/test_cli_container_commands.py`
  Test: `iris-devtester container reset-password --help` succeeds
  Verify: Command exists and shows help text

- [ ] **T008** [P] Contract test: CLI enable-callin command exists
  File: `tests/contract/test_cli_container_commands.py`
  Test: `iris-devtester container enable-callin --help` succeeds
  Verify: Command exists and shows help text

- [ ] **T009** [P] Contract test: CLI test-connection command exists
  File: `tests/contract/test_cli_container_commands.py`
  Test: `iris-devtester container test-connection --help` succeeds
  Verify: Command exists and shows help text

- [ ] **T010** [P] Contract test: CLI status command exists
  File: `tests/contract/test_cli_container_commands.py`
  Test: `iris-devtester container status --help` succeeds
  Verify: Command exists and shows help text

### Contract Tests (IRISContainer)

- [ ] **T011** [P] Contract test: IRISContainer.attach() method exists
  File: `tests/contract/test_iriscontainer_attach.py`
  Contract: `IRISContainer.attach(container_name: str) -> IRISContainer`
  Verify: Class method exists, returns IRISContainer instance

- [ ] **T012** [P] Contract test: IRISContainer.attach() rejects lifecycle methods
  File: `tests/contract/test_iriscontainer_attach.py`
  Contract: Attached container raises error on start(), stop(), __enter__
  Verify: Lifecycle methods disabled for attached containers

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Standalone Utilities (FR-006, FR-007, FR-005)

- [ ] **T013** [P] Implement enable_callin_service utility
  File: `iris_devtester/utils/enable_callin.py`
  Pattern: Follow `password_reset.py` (docker exec, return (bool, str))
  ObjectScript: `Set prop("Enabled")=1, Set prop("AutheEnabled")=48`
  Dependencies: None (standalone)

- [ ] **T014** [P] Implement test_connection utility
  File: `iris_devtester/utils/test_connection.py`
  Pattern: Follow `password_reset.py` (try iris.connect(), return (bool, str))
  Fallback: Docker exec if iris.connect() fails
  Dependencies: None (standalone)

- [ ] **T015** [P] Implement get_container_status utility
  File: `iris_devtester/utils/container_status.py`
  Data: Container health, CallIn enabled, password status, connection test
  Output: Multi-line status report string
  Dependencies: Calls enable_callin.py and test_connection.py (but they're complete)

- [ ] **T016** Update utils/__init__.py exports
  File: `iris_devtester/utils/__init__.py`
  Add: `enable_callin_service`, `test_connection`, `get_container_status` to __all__
  Dependencies: T013, T014, T015 complete

### CLI Commands (FR-002, FR-003, FR-004, FR-005)

- [ ] **T017** Implement CLI container command group
  File: `iris_devtester/cli/container_commands.py`
  Pattern: Follow `fixture_commands.py` Click structure
  Commands: reset-password, enable-callin, test-connection, status
  Dependencies: T013, T014, T015 (utilities must exist)

- [ ] **T018** Register container command group in CLI main
  File: `iris_devtester/cli/__init__.py`
  Change: Import and add `container` command group
  Verify: `iris-devtester container --help` works
  Dependencies: T017 complete

### IRISContainer Enhancement (FR-001)

- [ ] **T019** Implement IRISContainer.attach() class method
  File: `iris_devtester/containers/iris_container.py`
  Pattern: Similar to `IRISContainer.community()` class method
  Logic: Verify container exists/running, set `_attached=True` flag, return instance
  Dependencies: None (self-contained in iris_container.py)

- [ ] **T020** Add lifecycle guard to IRISContainer methods
  File: `iris_devtester/containers/iris_container.py`
  Logic: Check `_attached` flag in start(), stop(), __enter__, __exit__
  Error: Raise ValueError("Cannot manage lifecycle of attached container")
  Dependencies: T019 complete

## Phase 3.4: Integration Tests

- [ ] **T021** [P] Integration test: enable_callin_service on real container
  File: `tests/integration/test_enable_callin_integration.py`
  Setup: Start IRISContainer.community()
  Test: Call enable_callin_service(), verify AutheEnabled=48 via SQL
  Dependencies: T013 implementation complete

- [ ] **T022** [P] Integration test: test_connection on real container
  File: `tests/integration/test_test_connection_integration.py`
  Setup: Start IRISContainer.community()
  Test: Call test_connection(), verify connection succeeds
  Dependencies: T014 implementation complete

- [ ] **T023** [P] Integration test: get_container_status comprehensive
  File: `tests/integration/test_container_status_integration.py`
  Setup: Start IRISContainer.community()
  Test: Call get_container_status(), verify status report format
  Dependencies: T015 implementation complete

- [ ] **T024** [P] Integration test: CLI reset-password command
  File: `tests/integration/test_cli_container_integration.py`
  Setup: Start IRISContainer.community()
  Test: Run `iris-devtester container reset-password <name>` via subprocess
  Verify: Exit code 0, password changed
  Dependencies: T017, T018 complete

- [ ] **T025** [P] Integration test: CLI enable-callin command
  File: `tests/integration/test_cli_container_integration.py`
  Setup: Start IRISContainer.community()
  Test: Run `iris-devtester container enable-callin <name>` via subprocess
  Verify: Exit code 0, CallIn enabled
  Dependencies: T017, T018 complete

- [ ] **T026** [P] Integration test: CLI test-connection command
  File: `tests/integration/test_cli_container_integration.py`
  Setup: Start IRISContainer.community()
  Test: Run `iris-devtester container test-connection <name>` via subprocess
  Verify: Exit code 0, connection success message
  Dependencies: T017, T018 complete

- [ ] **T027** [P] Integration test: CLI status command
  File: `tests/integration/test_cli_container_integration.py`
  Setup: Start IRISContainer.community()
  Test: Run `iris-devtester container status <name>` via subprocess
  Verify: Exit code 0, multi-line status report
  Dependencies: T017, T018 complete

- [ ] **T028** Integration test: IRISContainer.attach() workflow
  File: `tests/integration/test_iriscontainer_attach_integration.py`
  Setup: Start IRISContainer.community(), get container name
  Test: Attach to existing container, call utility methods, verify lifecycle methods raise
  Dependencies: T019, T020 complete

## Phase 3.5: Examples & Documentation

- [ ] **T029** [P] Create docker-compose integration example (FR-008)
  File: `examples/10_docker_compose_integration.py`
  Content: Standalone utilities, IRISContainer.attach(), CLI commands
  Scenario: Licensed IRIS setup with docker-compose (from quickstart.md)
  Dependencies: T013, T014, T019 (core features implemented)

- [ ] **T030** [P] Update README.md with new utilities (FR-010)
  File: `README.md`
  Add: `unexpire_all_passwords()` documentation
  Add: `enable_callin_service()` documentation
  Add: `test_connection()` documentation
  Section: "Standalone Utilities" or "API Reference"
  Dependencies: None (documentation only)

- [ ] **T031** [P] Add AutheEnabled=48 explanation (FR-011)
  File: `iris_devtester/utils/enable_callin.py`
  Add: Named constant `AUTHE_PASSWORD_KERBEROS = 48`
  Add: Inline comment: "48 = 0x30 = Password (0x10) + Kerberos (0x20) authentication"
  Add: Docstring explanation
  Dependencies: T013 (can be done during or after implementation)

- [ ] **T032** [P] Raise password unexpiration log level (FR-012)
  File: `iris_devtester/containers/iris_container.py`
  Change: `logger.debug(...)` → `logger.info(...)` for unexpire_passwords calls
  Rationale: User visibility (from feedback issue #5)
  Dependencies: None (simple logging change)

## Phase 3.6: Polish & Quality

- [ ] **T033** [P] Unit test: enable_callin error handling
  File: `tests/unit/test_enable_callin.py`
  Cases: Container not found, Docker not running, timeout, permission denied
  Verify: Error messages follow Constitutional Principle #5 format
  Dependencies: T013 implementation complete

- [ ] **T034** [P] Unit test: test_connection error handling
  File: `tests/unit/test_test_connection.py`
  Cases: Container not found, IRIS not ready, connection refused, auth failed
  Verify: Error messages with remediation steps
  Dependencies: T014 implementation complete

- [ ] **T035** [P] Unit test: CLI command error messages
  File: `tests/unit/test_cli_container_commands.py`
  Cases: Missing container argument, invalid options, container not running
  Verify: User-friendly error output
  Dependencies: T017 implementation complete

- [ ] **T036** Run full test suite and verify coverage
  Command: `pytest --cov=iris_devtester --cov-report=html`
  Target: ≥94% coverage (Constitutional Principle #7)
  Files: All new modules (enable_callin.py, test_connection.py, container_status.py, container_commands.py)
  Dependencies: All implementation and test tasks complete

- [ ] **T037** Manual validation using quickstart.md scenario
  File: `specs/006-address-docker-compose/quickstart.md` (from plan.md Phase 1)
  Scenario: Docker-compose workflow (reset password → enable CallIn → test connection → status)
  Verify: All commands work, output is clear and helpful
  Dependencies: T017, T018 (CLI commands working)

- [ ] **T038** Update CHANGELOG.md for v1.0.1 release
  File: `CHANGELOG.md`
  Section: `## [1.0.1] - [Date]`
  Add: All FR-001 through FR-012 feature descriptions
  Add: "Fixes critical UX issue preventing docker-compose usage"
  Dependencies: All features implemented

## Dependencies Graph

```
Setup (T001-T003)
  ↓
Contract Tests (T004-T012) [ALL PARALLEL]
  ↓
Core Implementation:
  ├─ Utilities (T013-T016) [T013,T014,T015 parallel; T016 after all]
  ├─ CLI (T017-T018) [T017 depends on utilities; T018 depends on T017]
  └─ IRISContainer (T019-T020) [T019 first, T020 after]
  ↓
Integration Tests (T021-T028) [MOSTLY PARALLEL, grouped by dependency]
  ↓
Examples & Docs (T029-T032) [ALL PARALLEL]
  ↓
Polish (T033-T038) [T033-T035 parallel; T036 after all tests; T037-T038 final]
```

## Parallel Execution Examples

### Contract Tests (Phase 3.2)
```bash
# Execute T004-T012 together (9 contract tests):
# All test files are independent, no shared state
```

### Standalone Utilities (Phase 3.3)
```bash
# Execute T013, T014, T015 together:
# - enable_callin.py
# - test_connection.py
# - container_status.py
# All are separate files with no dependencies
```

### Integration Tests (Phase 3.4)
```bash
# Execute T021, T022, T023 together (utility integration tests):
# Each uses separate test file and IRIS container

# Execute T024-T027 together (CLI integration tests):
# All in same file but separate test methods - pytest handles parallelism
```

### Documentation (Phase 3.5)
```bash
# Execute T029, T030, T031, T032 together:
# All modify different files (example, README, source docs, logging)
```

## Notes

- **TDD Required**: Contract tests (T004-T012) MUST fail before starting implementation
- **Pattern Compliance**: All utilities follow `password_reset.py` pattern (proven success)
- **Constitutional**: Error messages follow Principle #5 (Fail Fast with Guidance)
- **Coverage**: Target ≥94% per Principle #7 (Medical-Grade Reliability)
- **Idempotent**: All operations safe to run multiple times
- **Git Commits**: Commit after each task or logical group
- **No [P] Conflicts**: Verified no parallel tasks modify same files

## Task Generation Rules Applied

1. **From plan.md Contracts** (plan.md:244-336):
   - enable_callin_service → T004 contract + T013 impl + T021 integration
   - test_connection → T005 contract + T014 impl + T022 integration
   - get_container_status → T006 contract + T015 impl + T023 integration
   - CLI commands (4) → T007-T010 contracts + T017 impl + T024-T027 integration
   - IRISContainer.attach() → T011-T012 contracts + T019-T020 impl + T028 integration

2. **From plan.md Structure** (plan.md:96-138):
   - New modules: enable_callin.py, test_connection.py, container_status.py
   - CLI module: container_commands.py
   - Updates: utils/__init__.py, iris_container.py
   - Example: 10_docker_compose_integration.py

3. **From spec.md Requirements**:
   - FR-001 → T019-T020, T028 (IRISContainer.attach)
   - FR-002-005 → T007-T010, T017-T018, T024-T027 (CLI commands)
   - FR-006-007 → T004-T005, T013-T014, T021-T022 (standalone utilities)
   - FR-008 → T029 (docker-compose example)
   - FR-009-012 → T030-T032, T033-T035 (docs, errors, logging)

4. **Ordering**: Setup → Contract Tests → Implementation → Integration → Docs → Polish

## Validation Checklist

- [x] All contracts have corresponding tests (T004-T012 cover all APIs)
- [x] All utilities have implementation tasks (T013-T015)
- [x] All tests come before implementation (Phase 3.2 before 3.3)
- [x] Parallel tasks truly independent (verified file conflicts)
- [x] Each task specifies exact file path
- [x] No [P] task modifies same file as another [P] task
- [x] Follows password_reset.py pattern (Constitutional requirement)
- [x] Constitutional Principle #5 compliance (error message structure in T033-T035)
- [x] Constitutional Principle #7 compliance (coverage target T036)

---

**Total Tasks**: 38 tasks
**Estimated Time**: 2-3 weeks (HIGH priority items for v1.0.1)
**Ready for Execution**: ✅ All tasks are specific and immediately actionable
