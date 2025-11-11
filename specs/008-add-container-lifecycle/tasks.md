# Tasks: Container Lifecycle CLI Commands

**Feature**: 008-add-container-lifecycle
**Input**: Design documents from `/Users/tdyar/ws/iris-devtester/specs/008-add-container-lifecycle/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/cli-commands.md, quickstart.md

## Execution Flow
```
1. Load plan.md → Extract tech stack (Python 3.9+, Click 8.0+, PyYAML, docker-py)
2. Load data-model.md → Extract entities (ContainerConfig, ContainerState)
3. Load contracts/cli-commands.md → Extract 7 CLI commands
4. Load quickstart.md → Extract 4 integration scenarios
5. Generate tasks by TDD approach:
   → Setup: dependencies, project structure
   → Tests First: contract tests for all 7 commands (MUST FAIL)
   → Core: data models, utilities
   → Implementation: CLI command handlers
   → Integration: tests, wiring, examples
   → Polish: docs, examples
6. Apply parallelization: Different files → [P]
7. Validate: All contracts have tests, TDD order preserved
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Phase 3.1: Setup & Dependencies

- [ ] **T001** Add PyYAML>=6.0 dependency to pyproject.toml [dependencies] section
- [ ] **T002** [P] Create iris_devtester/cli/container.py with Click command group structure
- [ ] **T003** [P] Create iris_devtester/config/yaml_loader.py for YAML parsing

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.4

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (CLI Command Contracts)

- [ ] **T004** [P] Contract test `container up` command in tests/contract/cli/test_container_up_contract.py
  - Test flags: --config, --detach/--no-detach, --timeout
  - Test exit codes: 0, 1, 2, 3, 4, 5, 6
  - Test output format (success, idempotent, errors)
  - Verify Constitutional error message format

- [ ] **T005** [P] Contract test `container start` command in tests/contract/cli/test_container_start_contract.py
  - Test CONTAINER_NAME argument
  - Test flags: --config, --timeout
  - Test exit codes: 0, 1, 2, 5
  - Test output format (existing, created new)

- [ ] **T006** [P] Contract test `container stop` command in tests/contract/cli/test_container_stop_contract.py
  - Test CONTAINER_NAME argument
  - Test flags: --timeout
  - Test exit codes: 0, 1, 2
  - Test idempotency (already stopped)

- [ ] **T007** [P] Contract test `container restart` command in tests/contract/cli/test_container_restart_contract.py
  - Test CONTAINER_NAME argument
  - Test flags: --timeout
  - Test exit codes: 0, 1, 2, 5

- [ ] **T008** [P] Contract test `container status` command in tests/contract/cli/test_container_status_contract.py
  - Test CONTAINER_NAME argument
  - Test flags: --format (text, json)
  - Test exit codes: 0, 2
  - Test JSON schema validation (ContainerStatus)

- [ ] **T009** [P] Contract test `container logs` command in tests/contract/cli/test_container_logs_contract.py
  - Test CONTAINER_NAME argument
  - Test flags: --follow, --tail, --since
  - Test exit codes: 0, 2

- [ ] **T010** [P] Contract test `container remove` command in tests/contract/cli/test_container_remove_contract.py
  - Test CONTAINER_NAME argument
  - Test flags: --force, --volumes
  - Test exit codes: 0, 1, 2, 3
  - Test idempotency behavior

## Phase 3.3: Data Models & Configuration

- [ ] **T011** [P] Create ContainerConfig dataclass in iris_devtester/config/container_config.py
  - Fields: edition, container_name, superserver_port, webserver_port, namespace, password, license_key, volumes, image_tag
  - Validation: __post_init__ with port range, edition check, container name regex, namespace regex
  - Methods: from_yaml(), from_env(), default()
  - Use Pydantic for validation

- [ ] **T012** [P] Create ContainerState dataclass in iris_devtester/cli/container_state.py
  - Fields: container_id, container_name, status, health_status, created_at, started_at, finished_at, ports, image, config_source
  - State transition validation
  - Methods: from_docker_container()

- [ ] **T013** [P] Unit tests for ContainerConfig validation in tests/unit/config/test_container_config.py
  - Test invalid ports (below 1024, above 65535)
  - Test invalid edition
  - Test missing license_key for enterprise
  - Test invalid container_name format
  - Test invalid namespace format

- [ ] **T014** [P] Unit tests for YAML loader in tests/unit/config/test_yaml_loader.py
  - Test valid YAML parsing
  - Test invalid YAML syntax
  - Test missing required fields
  - Test type coercion

- [ ] **T015** [P] Unit tests for configuration hierarchy in tests/unit/config/test_config_hierarchy.py
  - Test explicit config file path
  - Test default ./iris-config.yml discovery
  - Test environment variable fallback
  - Test zero-config defaults

- [ ] **T016** Implement YAML loader in iris_devtester/config/yaml_loader.py
  - load_yaml() function
  - validate_schema() function
  - Integration with ContainerConfig.from_yaml()

## Phase 3.4: Core Utilities

- [ ] **T017** [P] Create Docker SDK wrapper functions in iris_devtester/cli/docker_utils.py
  - validate_docker() - Check Docker installed and running
  - pull_image() - Pull IRIS image with progress
  - create_container() - Create container from ContainerConfig
  - start_container() - Start existing container
  - stop_container() - Stop with graceful shutdown
  - remove_container() - Remove container and optionally volumes
  - get_container() - Get container by name

- [ ] **T018** [P] Create health check implementation in iris_devtester/cli/health_check.py
  - wait_for_healthy() - Multi-layer health check
  - Layer 1: Container running check
  - Layer 2: Docker health check (if defined)
  - Layer 3: IRIS SuperServer port check (port 1972)
  - Timeout handling with progress messages

- [ ] **T019** [P] Create Constitutional error message formatters in iris_devtester/cli/error_messages.py
  - docker_not_running_error() - Docker daemon not accessible
  - docker_not_installed_error() - Docker not found
  - port_conflict_error() - Port already in use
  - disk_space_error() - Insufficient disk space
  - license_validation_error() - Invalid license key
  - container_not_found_error() - Container doesn't exist
  - All follow 4-part format (What/Why/How/Docs)

- [ ] **T020** [P] Create progress indicator utilities in iris_devtester/cli/progress.py
  - spinner() - Active operations (⚡)
  - success() - Completed operations (✓)
  - error() - Failed operations (✗)
  - info() - Sub-steps (→)
  - Progress messages during long operations

- [ ] **T021** [P] Unit tests for Docker SDK wrappers in tests/unit/cli/test_docker_utils.py
  - Mock docker.from_env()
  - Test validate_docker() with Docker not running
  - Test create_container() with valid config
  - Test error handling for all operations

## Phase 3.5: CLI Command Implementations (ONLY after tests are failing)

- [ ] **T022** Implement `container up` command in iris_devtester/cli/container.py
  - Command decorator with options (--config, --detach, --timeout)
  - Idempotent check-then-act pattern
  - Load configuration (file → env → defaults)
  - Docker validation
  - Pull image if needed
  - Create or start container
  - Wait for health check
  - Enable CallIn service (if DBAPI installed)
  - Display connection information
  - Handle all 6 error scenarios (exit codes 1-6)

- [ ] **T023** Implement `container start` command in iris_devtester/cli/container.py
  - Command decorator with options (--config, --timeout)
  - Check if container exists
  - If exists: start and wait for health
  - If not exists: create from config (like `up`)
  - Display status and uptime

- [ ] **T024** Implement `container stop` command in iris_devtester/cli/container.py
  - Command decorator with options (--timeout)
  - Idempotent check (already stopped → success)
  - Graceful shutdown with SIGTERM
  - Force kill after timeout (SIGKILL)
  - Display final status and uptime

- [ ] **T025** Implement `container restart` command in iris_devtester/cli/container.py
  - Command decorator with options (--timeout)
  - Stop then start sequence
  - Wait for health check
  - Display restart duration

- [ ] **T026** Implement `container status` command in iris_devtester/cli/container.py
  - Command decorator with options (--format text/json)
  - Query Docker for container state
  - Text format: Human-readable status display
  - JSON format: Structured ContainerStatus schema
  - Handle container not found

- [ ] **T027** Implement `container logs` command in iris_devtester/cli/container.py
  - Command decorator with options (--follow, --tail, --since)
  - Stream logs from Docker container
  - Follow mode: Continuous streaming (CTRL+C to exit)
  - Tail mode: Last N lines
  - Since mode: Logs after timestamp

- [ ] **T028** Implement `container remove` command in iris_devtester/cli/container.py
  - Command decorator with options (--force, --volumes)
  - Check running state (error if running without --force)
  - Stop if --force
  - Remove container
  - Remove volumes if --volumes
  - Display confirmation

## Phase 3.6: Integration Tests

- [ ] **T029** [P] Integration test: Zero-config quick start in tests/integration/cli/test_container_lifecycle_zero_config.py
  - Test `container up` with no config file
  - Verify Community edition defaults
  - Verify container running and healthy
  - Test connection to SuperServer port 1972
  - Cleanup

- [ ] **T030** [P] Integration test: Configuration file workflow in tests/integration/cli/test_container_lifecycle_with_config.py
  - Create iris-config.yml with custom settings
  - Test `container up --config iris-config.yml`
  - Verify custom ports and namespace
  - Test idempotency (run `up` again)
  - Cleanup

- [ ] **T031** [P] Integration test: Container lifecycle management in tests/integration/cli/test_container_lifecycle_full.py
  - Test sequence: up → status → stop → start → restart → remove
  - Verify state transitions
  - Verify idempotency at each step
  - Test --format json output parsing

- [ ] **T032** [P] Integration test: Enterprise edition in tests/integration/cli/test_container_enterprise.py
  - Create enterprise config with license key
  - Test `container up` with enterprise edition
  - Verify license validation (if testable)
  - Cleanup

- [ ] **T033** [P] Integration test: Error handling in tests/integration/cli/test_container_errors.py
  - Test Docker not running error
  - Test invalid config file error
  - Test port conflict error (simulate)
  - Verify Constitutional error message format
  - Verify exit codes

- [ ] **T034** [P] Integration test: Logs streaming in tests/integration/cli/test_container_logs.py
  - Start container
  - Test `logs --tail 10`
  - Test `logs --since` with timestamp
  - Test log output format

- [ ] **T035** [P] Integration test: Multiple containers in tests/integration/cli/test_container_multiple.py
  - Create iris-dev.yml (container_name: iris_dev)
  - Create iris-test.yml (container_name: iris_test)
  - Start both containers
  - Verify both running independently
  - Test status for each
  - Cleanup both

## Phase 3.7: Integration & Wiring

- [ ] **T036** Register container command group in iris_devtester/cli/main.py
  - Import container_group from iris_devtester.cli.container
  - Add cli.add_command(container_group)
  - Verify `iris-devtester container --help` works

- [ ] **T037** Create example iris-config.yml in examples/cli/iris-config-community.yml
  - Community edition example
  - All fields documented with comments
  - Default values shown

- [ ] **T038** [P] Create example iris-config-enterprise.yml in examples/cli/iris-config-enterprise.yml
  - Enterprise edition example
  - License key placeholder
  - Volume mappings example

- [ ] **T039** [P] Create example workflow script in examples/cli/container_workflow.sh
  - Demonstrate common CLI commands
  - Zero-config quick start
  - Config file usage
  - Container lifecycle management

- [ ] **T040** Update pyproject.toml version to 1.1.0
  - Increment version from 1.0.2 → 1.1.0 (minor version for new feature)
  - Verify all dependencies added

## Phase 3.8: Polish

- [ ] **T041** [P] Update CHANGELOG.md with Feature 008 changes
  - Add ## [1.1.0] - 2025-01-10 section
  - List all 7 new CLI commands
  - Mention zero-config support
  - Mention Constitutional error messages

- [ ] **T042** [P] Update README.md with container CLI examples
  - Add "Container Lifecycle Management" section
  - Show zero-config quick start
  - Link to quickstart.md for full guide

- [ ] **T043** [P] Run full test suite and verify 95%+ coverage
  - pytest --cov=iris_devtester --cov-report=html
  - Verify coverage for new modules (cli/container.py, config/container_config.py, etc.)
  - Fix any coverage gaps

## Dependencies

**Critical TDD Ordering**:
- T004-T010 (contract tests) MUST complete before T022-T028 (implementations)
- T013-T015 (data model tests) MUST complete before T011-T012, T016 (implementations)
- T021 (utility tests) MUST complete before T017-T020 (utility implementations)

**Module Dependencies**:
- T011-T016 (config/data models) blocks T022-T028 (CLI commands need ContainerConfig)
- T017-T021 (utilities) blocks T022-T028 (CLI commands need Docker wrappers)
- T022-T028 (implementations) blocks T029-T035 (integration tests)
- T036 (registration) blocks manual testing
- T001-T003 (setup) blocks everything

**Parallel Opportunities**:
- T004-T010: All contract tests (different files)
- T011-T015: Data model tasks (different files)
- T017-T020: Utility tasks (different files)
- T029-T035: Integration tests (different files)
- T037-T039: Examples (different files)
- T041-T043: Polish tasks (different files)

## Parallel Execution Examples

### Phase 3.2: Launch all contract tests together
```bash
# All 7 contract tests can run in parallel (different files)
Task: "Contract test container up in tests/contract/cli/test_container_up_contract.py"
Task: "Contract test container start in tests/contract/cli/test_container_start_contract.py"
Task: "Contract test container stop in tests/contract/cli/test_container_stop_contract.py"
Task: "Contract test container restart in tests/contract/cli/test_container_restart_contract.py"
Task: "Contract test container status in tests/contract/cli/test_container_status_contract.py"
Task: "Contract test container logs in tests/contract/cli/test_container_logs_contract.py"
Task: "Contract test container remove in tests/contract/cli/test_container_remove_contract.py"
```

### Phase 3.3: Launch data model tests together
```bash
# Data model tests (different files)
Task: "Unit tests for ContainerConfig validation in tests/unit/config/test_container_config.py"
Task: "Unit tests for YAML loader in tests/unit/config/test_yaml_loader.py"
Task: "Unit tests for configuration hierarchy in tests/unit/config/test_config_hierarchy.py"
```

### Phase 3.6: Launch integration tests together
```bash
# All integration tests (different files)
Task: "Integration test zero-config in tests/integration/cli/test_container_lifecycle_zero_config.py"
Task: "Integration test config file in tests/integration/cli/test_container_lifecycle_with_config.py"
Task: "Integration test full lifecycle in tests/integration/cli/test_container_lifecycle_full.py"
Task: "Integration test enterprise in tests/integration/cli/test_container_enterprise.py"
Task: "Integration test error handling in tests/integration/cli/test_container_errors.py"
Task: "Integration test logs in tests/integration/cli/test_container_logs.py"
Task: "Integration test multiple containers in tests/integration/cli/test_container_multiple.py"
```

## Notes

- **[P] tasks**: Different files, no dependencies → safe to parallelize
- **TDD critical**: Verify contract tests FAIL before writing implementations
- **Idempotency**: Test by running commands multiple times
- **Constitutional errors**: All must follow What/Why/How/Docs format
- **Commit strategy**: Commit after each task completion
- **Coverage target**: 95%+ for medical-grade reliability

## Validation Checklist

- [x] All 7 CLI commands have contract tests (T004-T010)
- [x] All 2 entities have model tasks (T011-T012)
- [x] All contract tests come before implementations (T004-T010 before T022-T028)
- [x] Parallel tasks are truly independent (different files, no shared state)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] All quickstart workflows have integration tests (T029-T035)
- [x] Constitutional error messages tested (T033)
- [x] Zero-config tested (T029)
- [x] Idempotency tested (T030, T031)

## Task Count Summary

- **Setup**: 3 tasks (T001-T003)
- **Contract Tests**: 7 tasks (T004-T010) [P]
- **Data Models**: 6 tasks (T011-T016, some [P])
- **Core Utilities**: 5 tasks (T017-T021) [P]
- **CLI Implementations**: 7 tasks (T022-T028)
- **Integration Tests**: 7 tasks (T029-T035) [P]
- **Integration & Wiring**: 5 tasks (T036-T040, some [P])
- **Polish**: 3 tasks (T041-T043) [P]

**Total**: 43 tasks (as estimated: 35-40 range, actual 43)

---

**Status**: Tasks ready for execution. Next: Begin Phase 3.1 (Setup) or run tasks in TDD order.
