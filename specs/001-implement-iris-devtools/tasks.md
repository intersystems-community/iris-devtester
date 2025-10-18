# Tasks: IRIS DevTools Package Implementation

**Input**: Design documents from `/specs/001-implement-iris-devtools/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md
**Source Code**: `~/ws/rag-templates/` (extraction project)

## Execution Summary

This is an **extraction and enhancement** project (~1000 lines from rag-templates → ~1700 lines iris-devtools):
- Extract proven code from rag-templates production
- Add testcontainers integration
- Enhance with Python 3.9+ type hints
- Package for PyPI distribution
- Maintain backwards compatibility

**Key Principles** (CONSTITUTION.md):
1. TDD: Tests before implementation
2. DBAPI first, JDBC fallback
3. Isolation by default
4. Zero-config viable
5. 95%+ test coverage

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **Source paths**: `~/ws/rag-templates/` (extraction source)
- **Target paths**: `iris_devtools/` (new package)

---

## Phase 3.1: Project Setup

- [x] **T001** Create package structure with all directories
  - Create: `iris_devtools/`, `iris_devtools/connections/`, `iris_devtools/containers/`, `iris_devtools/testing/`, `iris_devtools/config/`, `iris_devtools/utils/`
  - Create: `tests/`, `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/contract/`
  - Create: `docs/`, `docs/learnings/`, `examples/`
  - All directories need `__init__.py` files

- [x] **T002** Initialize Python package with pyproject.toml
  - Already exists, verify dependencies match plan.md
  - Core: `testcontainers>=4.0.0`, `testcontainers-iris-python>=1.2.2`, `python-dotenv>=1.0.0`
  - Optional: `intersystems-irispython>=3.2.0`, `jaydebeapi>=1.2.3`
  - Dev: `pytest>=8.0`, `pytest-cov`, `black`, `isort`, `mypy`
  - Verify Python 3.9+ requirement

- [x] **T003** [P] Configure linting and formatting tools
  - Already configured in pyproject.toml (black line-length 100, isort compatible)
  - Verify configuration matches plan.md standards

- [x] **T004** [P] Create initial package exports in iris_devtools/__init__.py
  - Export main convenience functions: `get_iris_connection`, `IRISConfig`, `IRISContainer`
  - Set `__version__ = "1.0.0"`
  - Keep minimal for now, expand as modules are built

---

## Phase 3.2: Data Models (TDD - Tests First) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL**: These tests MUST be written and MUST FAIL before ANY implementation in Phase 3.3

- [x] **T005** [P] Contract test for Connection Management API in tests/contract/test_connection_api.py
  - Test `get_iris_connection()` signature and basic behavior
  - Test `reset_password_if_needed()` interface
  - Test `test_connection()` interface
  - Test `IRISConnectionManager` class interface
  - All tests should FAIL (not implemented yet)
  - Reference: `specs/001-implement-iris-devtools/contracts/connection-api.md`

- [x] **T006** [P] Contract test for Testing Fixtures API in tests/contract/test_testing_fixtures_api.py
  - Test `iris_db` fixture interface
  - Test `iris_db_shared` fixture interface
  - Test `iris_container` fixture interface
  - Test `validate_schema()` function signature
  - Test `reset_schema()` function signature
  - All tests should FAIL (not implemented yet)
  - Reference: `specs/001-implement-iris-devtools/contracts/testing-fixtures-api.md`

- [x] **T007** [P] Contract test for Container Management API in tests/contract/test_container_api.py
  - Test `IRISContainer.community()` class method
  - Test `IRISContainer.enterprise()` class method
  - Test `get_connection()` method
  - Test `wait_for_ready()` method
  - Test `reset_password()` method
  - All tests should FAIL (not implemented yet)
  - Reference: `specs/001-implement-iris-devtools/contracts/container-api.md`

- [x] **T008** [P] Unit test for IRISConfig model in tests/unit/test_iris_config.py
  - Test default values
  - Test validation rules (port range, namespace non-empty, timeout positive)
  - Test serialization/deserialization
  - Should FAIL (model not implemented)

- [x] **T009** [P] Unit test for ConnectionInfo model in tests/unit/test_connection_info.py
  - Test fields and defaults
  - Test timestamp generation
  - Should FAIL (model not implemented)

- [x] **T010** [P] Unit test for SchemaDefinition models in tests/unit/test_schema_models.py
  - Test SchemaDefinition, TableDefinition, ColumnDefinition, IndexDefinition
  - Test relationships and nesting
  - Should FAIL (models not implemented)

- [x] **T011** [P] Unit test for validation result models in tests/unit/test_validation_results.py
  - Test SchemaValidationResult, SchemaMismatch
  - Test PasswordResetResult
  - Test TestState, CleanupAction
  - Test ContainerConfig
  - Should FAIL (models not implemented)

---

## Phase 3.3: Core Models (ONLY after tests are failing)

- [x] **T012** [P] Create IRISConfig dataclass in iris_devtools/config/models.py
  - Extract from: N/A (new, but based on rag-templates config patterns)
  - Implement with Python 3.9+ dataclass and type hints
  - Add `__post_init__` validation
  - Make T008 pass

- [x] **T013** [P] Create ConnectionInfo dataclass in iris_devtools/connections/models.py
  - Extract from: N/A (new metadata class)
  - Implement with dataclass, datetime handling
  - Make T009 pass

- [x] **T014** [P] Create schema model classes in iris_devtools/testing/models.py
  - Extract from: `~/ws/rag-templates/tests/utils/schema_models.py` (~120 lines)
  - Port SchemaDefinition, TableDefinition, ColumnDefinition, IndexDefinition
  - Port SchemaValidationResult, SchemaMismatch
  - Add type hints, enhance with dataclasses
  - Make T010 pass

- [x] **T015** [P] Create validation and state models in iris_devtools/testing/models.py (same file as T014)
  - Extract PasswordResetResult pattern from rag-templates
  - Create TestState, CleanupAction, ContainerConfig classes
  - Add type hints and validation
  - Make T011 pass

---

## Phase 3.4: Configuration & Discovery

- [x] **T016** Unit test for configuration discovery in tests/unit/test_config_discovery.py
  - Test environment variable discovery
  - Test .env file loading
  - Test Docker container inspection
  - Test default values
  - Test priority hierarchy (explicit > env > .env > docker > defaults)
  - Should FAIL (discovery not implemented)

- [x] **T017** Create configuration discovery in iris_devtools/config/discovery.py
  - Extract patterns from: `~/ws/rag-templates/common/iris_connection_manager.py` (config logic)
  - New functionality: consolidate scattered env var handling
  - Implement auto-discovery from environment, .env, Docker
  - Make T016 pass

- [x] **T018** [P] Create default configurations in iris_devtools/config/defaults.py
  - Define DEFAULT_HOST = "localhost"
  - Define DEFAULT_PORT = 1972
  - Define DEFAULT_NAMESPACE = "USER"
  - Define default credentials (SuperUser/SYS)
  - Document why these defaults (zero-config principle)

- [x] **T019** Update iris_devtools/config/__init__.py exports
  - Export IRISConfig, discover_config, defaults
  - Clean public API

---

## Phase 3.5: Connection Management (Core)

- [ ] **T020** Unit test for DBAPI connection in tests/unit/test_dbapi_connection.py
  - Mock intersystems_irispython
  - Test connection establishment
  - Test error handling
  - Should FAIL (not implemented)

- [ ] **T021** Unit test for JDBC connection in tests/unit/test_jdbc_connection.py
  - Mock jaydebeapi
  - Test connection establishment
  - Test error handling
  - Should FAIL (not implemented)

- [ ] **T022** Unit test for connection fallback logic in tests/unit/test_connection_fallback.py
  - Test DBAPI attempted first
  - Test JDBC fallback on DBAPI failure
  - Test logging of driver selection
  - Should FAIL (not implemented)

- [ ] **T023** Extract and enhance connection manager in iris_devtools/connections/manager.py
  - Extract from: `~/ws/rag-templates/common/iris_connection_manager.py` (~500 lines total)
  - Extract core IRISConnectionManager class
  - Implement DBAPI-first, JDBC-fallback logic
  - Add type hints, enhance error messages
  - Integrate with IRISConfig model
  - Make T020, T021, T022 pass

- [ ] **T024** Unit test for password reset in tests/unit/test_password_reset.py
  - Mock Docker exec calls
  - Test password change detection
  - Test automatic reset
  - Test environment variable updates
  - Should FAIL (not implemented)

- [ ] **T025** Extract and enhance password reset handler in iris_devtools/connections/recovery.py
  - Extract from: `~/ws/rag-templates/tests/utils/iris_password_reset.py` (~200 lines)
  - Extract from: `~/ws/rag-templates/common/iris_connection_manager.py` (password reset integration)
  - Implement IRISPasswordResetHandler class
  - Add automatic detection and remediation
  - Make T024 pass

- [ ] **T026** Implement convenience functions in iris_devtools/connections/__init__.py
  - Implement `get_iris_connection(config=None)` wrapper
  - Implement `reset_password_if_needed()` wrapper
  - Implement `test_connection()` helper
  - Make T005 pass (connection API contract tests)
  - Export clean public API

---

## Phase 3.6: Container Management

- [ ] **T027** Unit test for wait strategies in tests/unit/test_wait_strategies.py
  - Mock Docker container
  - Test IRISReadyWaitStrategy checks (port, process, query)
  - Test timeout handling
  - Should FAIL (not implemented)

- [ ] **T028** Create custom wait strategies in iris_devtools/containers/wait_strategies.py
  - New code: implement IRISReadyWaitStrategy
  - Verify port open, process running, database ready
  - Test namespace existence
  - Make T027 pass

- [ ] **T029** Unit test for enhanced IRISContainer in tests/unit/test_iris_container.py
  - Mock testcontainers base class
  - Test .community() class method
  - Test .enterprise() class method
  - Test get_connection() integration
  - Test password reset integration
  - Should FAIL (not implemented)

- [ ] **T030** Create enhanced IRIS container in iris_devtools/containers/iris_container.py
  - Extend testcontainers.iris.IRISContainer (don't replace)
  - Implement .community() and .enterprise() class methods
  - Integrate wait_for_ready() with custom wait strategies
  - Integrate get_connection() with connection manager
  - Integrate reset_password() with recovery handler
  - Make T029 pass, T007 pass (container API contract tests)

- [ ] **T031** Update iris_devtools/containers/__init__.py exports
  - Export IRISContainer, IRISReadyWaitStrategy
  - Clean public API

---

## Phase 3.7: Testing Utilities

- [ ] **T032** Unit test for schema validator in tests/unit/test_schema_validator.py
  - Mock IRIS connection
  - Test schema query and comparison
  - Test mismatch detection
  - Test caching
  - Should FAIL (not implemented)

- [ ] **T033** Extract and enhance schema manager in iris_devtools/testing/schema_manager.py
  - Extract from: `~/ws/rag-templates/tests/utils/schema_validator.py` (~200 lines)
  - Extract from: `~/ws/rag-templates/tests/fixtures/schema_reset.py` (~100 lines)
  - Merge SchemaValidator and SchemaResetter into unified SchemaManager
  - Implement validate_schema() and reset_schema() functions
  - Add caching support
  - Make T032 pass

- [ ] **T034** [P] Unit test for cleanup handler in tests/unit/test_cleanup.py
  - Mock cleanup actions (drop table, stop container)
  - Test priority ordering
  - Test error handling (cleanup failures)
  - Should FAIL (not implemented)

- [ ] **T035** [P] Extract cleanup handler in iris_devtools/testing/cleanup.py
  - Extract from: `~/ws/rag-templates/tests/fixtures/database_cleanup.py` (~100 lines)
  - Port DatabaseCleanupHandler, CleanupRegistry
  - Implement register_cleanup() function
  - Make T034 pass

- [ ] **T036** [P] Unit test for test state in tests/unit/test_test_state.py
  - Test TestState creation and management
  - Test state registry
  - Should FAIL (not implemented)

- [ ] **T037** [P] Extract test state manager in iris_devtools/testing/state.py
  - Extract from: `~/ws/rag-templates/tests/fixtures/database_state.py` (~80 lines)
  - Port TestDatabaseState, TestStateRegistry
  - Enhance with TestState model from T015
  - Make T036 pass

- [ ] **T038** [P] Unit test for preflight checks in tests/unit/test_preflight.py
  - Mock Docker availability, IRIS connectivity
  - Test PreflightChecker validation
  - Should FAIL (not implemented)

- [ ] **T039** [P] Extract preflight checker in iris_devtools/testing/preflight.py
  - Extract from: `~/ws/rag-templates/tests/utils/preflight_checks.py` (~150 lines)
  - Port PreflightChecker class
  - Add automatic remediation attempts
  - Make T038 pass

---

## Phase 3.8: pytest Fixtures

- [ ] **T040** Extract and create pytest fixtures in iris_devtools/testing/fixtures.py
  - Extract from: `~/ws/rag-templates/tests/conftest.py` (Feature 028 sections, ~200 lines)
  - Implement `iris_db` fixture (function-scoped, isolated)
  - Implement `iris_db_shared` fixture (module-scoped, shared)
  - Implement `iris_container` fixture (container access)
  - Integrate with connection manager, cleanup handler, state manager
  - Make T006 pass (testing fixtures API contract tests)

- [ ] **T041** Create conftest.py for pytest plugin in iris_devtools/testing/conftest.py
  - Register fixtures for auto-discovery
  - Configure pytest markers (iris, slow, isolation_required, enterprise_only)
  - Export pytest plugin entrypoint

- [ ] **T042** Update iris_devtools/testing/__init__.py exports
  - Export fixtures, validate_schema, reset_schema, register_cleanup
  - Export models (SchemaDefinition, etc.)
  - Clean public API

---

## Phase 3.9: Utilities

- [ ] **T043** [P] Unit test for Docker helpers in tests/unit/test_docker_helpers.py
  - Mock Docker API
  - Test container inspection
  - Test port discovery
  - Should FAIL (not implemented)

- [ ] **T044** [P] Create Docker helpers in iris_devtools/utils/docker_helpers.py
  - New code: extract Docker utility patterns from rag-templates
  - Implement container inspection, port discovery
  - Make T043 pass

- [ ] **T045** [P] Unit test for diagnostics in tests/unit/test_diagnostics.py
  - Mock connection testing, performance profiling
  - Test diagnostic report generation
  - Should FAIL (not implemented)

- [ ] **T046** [P] Create diagnostics module in iris_devtools/utils/diagnostics.py
  - New code: diagnostic and troubleshooting utilities
  - Connection testing, performance profiling, error reporting
  - Make T045 pass

- [ ] **T047** [P] Update iris_devtools/utils/__init__.py exports
  - Export Docker helpers, diagnostics
  - Clean public API

---

## Phase 3.10: Integration Tests (Real IRIS)

**Note**: These require actual IRIS containers, slower than unit tests

- [ ] **T048** [P] Integration test for DBAPI connection in tests/integration/test_dbapi_connection.py
  - Use real IRISContainer
  - Test DBAPI connection establishment
  - Test basic queries
  - Verify performance (<500ms)

- [ ] **T049** [P] Integration test for JDBC fallback in tests/integration/test_jdbc_fallback.py
  - Mock DBAPI unavailable (uninstall intersystems-irispython for test)
  - Verify JDBC fallback works
  - Test basic queries via JDBC

- [ ] **T050** [P] Integration test for password remediation in tests/integration/test_password_remediation.py
  - Create container with expired password
  - Verify automatic password reset
  - Verify environment variable update
  - Verify connection works after reset

- [ ] **T051** [P] Integration test for container lifecycle in tests/integration/test_container_lifecycle.py
  - Test container start/stop
  - Test wait_for_ready()
  - Test health checks
  - Test cleanup

- [ ] **T052** [P] Integration test for schema validation in tests/integration/test_schema_validation.py
  - Create test schema
  - Validate matches
  - Introduce mismatch
  - Verify detection and reset

- [ ] **T053** [P] Integration test for test isolation in tests/integration/test_test_isolation.py
  - Run multiple tests with iris_db fixture
  - Verify each gets isolated environment
  - Verify cleanup happens
  - Verify no pollution between tests

---

## Phase 3.11: End-to-End Tests (Full Workflows)

- [ ] **T054** [P] E2E test for zero-config workflow in tests/e2e/test_zero_config_workflow.py
  - No configuration provided
  - Auto-discovery works
  - Connection established
  - Queries work
  - Cleanup automatic
  - Reference: quickstart.md Step 2-3

- [ ] **T055** [P] E2E test for explicit config workflow in tests/e2e/test_explicit_config_workflow.py
  - Provide explicit IRISConfig
  - Connection works
  - Overrides defaults correctly

- [ ] **T056** [P] E2E test for parallel test execution in tests/e2e/test_parallel_execution.py
  - Run 5+ tests in parallel (pytest -n 5)
  - Verify isolation maintained
  - Verify performance gain
  - Reference: quickstart.md Step 6.3

- [ ] **T057** [P] E2E test for schema validation workflow in tests/e2e/test_schema_workflow.py
  - Define schema
  - Validate
  - Make changes
  - Detect mismatches
  - Auto-reset
  - Reference: quickstart.md Step 6.2

---

## Phase 3.12: Documentation

- [ ] **T058** [P] Create getting started guide in docs/getting-started.md
  - Installation instructions
  - Zero-config example
  - Explicit config example
  - Common use cases

- [ ] **T059** [P] Create API reference in docs/api-reference.md
  - Document all public APIs
  - Include examples for each function
  - Cross-reference contracts/

- [ ] **T060** [P] Create migration guide in docs/migration-guide.md
  - Backwards compatibility notes
  - rag-templates → iris-devtools migration steps
  - Code examples (before/after)

- [ ] **T061** [P] Create troubleshooting guide in docs/troubleshooting.md
  - Common errors and solutions
  - Docker issues
  - Connection issues
  - Password reset issues
  - Performance tuning

- [ ] **T062** [P] Document "Why DBAPI first?" in docs/learnings/why-dbapi-first.md
  - Benchmark results (3x speedup)
  - When to use JDBC
  - Constitutional principle explanation

- [ ] **T063** [P] Document "Why testcontainers?" in docs/learnings/why-testcontainers.md
  - vs docker-compose
  - vs shared database
  - Isolation benefits
  - Performance considerations

- [ ] **T064** [P] Document CallIn service requirement in docs/learnings/callin-service-requirement.md
  - Extract from existing rag-templates learnings
  - DBAPI requires CallIn enabled
  - How to enable
  - Troubleshooting

- [ ] **T064a** [P] Document embedded Python considerations in docs/learnings/embedded-python-considerations.md
  - Explain embedded vs external Python
  - Clarify iris-devtools scope (external only)
  - Use case comparison (embedded for stored procedures, external for apps)
  - Connection type comparison table
  - FAQ: Why not embedded Python support?
  - Constitutional alignment (PyPI, testing, zero-config)

---

## Phase 3.13: Examples

- [ ] **T065** [P] Create basic connection example in examples/basic_connection.py
  - Zero-config connection
  - Simple query
  - Cleanup

- [ ] **T066** [P] Create zero-config test example in examples/zero_config_test.py
  - Minimal pytest example
  - Using iris_db fixture
  - Demonstrates auto-discovery

- [ ] **T067** [P] Create advanced isolation example in examples/advanced_isolation.py
  - Container vs namespace isolation
  - Performance comparison
  - When to use which

---

## Phase 3.14: Package Polish

- [ ] **T068** Run full test suite and achieve 95%+ coverage
  - `pytest --cov=iris_devtools --cov-report=html`
  - Verify coverage ≥95%
  - Add tests for any uncovered lines

- [ ] **T069** [P] Format all code with black and isort
  - `black iris_devtools/ tests/`
  - `isort iris_devtools/ tests/`

- [ ] **T070** [P] Type check with mypy
  - `mypy iris_devtools/`
  - Fix any type errors

- [ ] **T071** [P] Lint with flake8
  - `flake8 iris_devtools/ tests/`
  - Fix any linting issues

- [ ] **T072** Update README.md with badges and quickstart
  - Add badges (PyPI, coverage, tests)
  - Include quickstart example
  - Link to full documentation

- [ ] **T073** Verify backwards compatibility with rag-templates
  - Import test: can import old API names?
  - Behavior test: do old patterns still work?
  - Document any breaking changes (should be none for v1.0.0)

- [ ] **T074** Run quickstart validation from specs/001-implement-iris-devtools/quickstart.md
  - Execute all steps in quickstart.md
  - Verify all tests pass
  - Verify zero-config works
  - Verify performance targets met

---

## Dependencies

**Critical Path** (these block everything else):
```
T001 (structure) → T002 (dependencies) → Everything else
T005-T011 (test tasks) → T012-T047 (implementation)
```

**Module Dependencies**:
```
Models (T012-T015) → All other modules
Config (T016-T019) → Connection (T020-T026)
Connection (T020-T026) → Container (T027-T031), Testing (T032-T042)
Container (T027-T031) → Testing fixtures (T040-T042)
Testing models (T032-T042) → Integration tests (T048-T053)
```

**Test Order** (TDD):
```
Contract tests (T005-T007) → Implementation → Integration (T048-T053) → E2E (T054-T057)
```

---

## Parallel Execution Examples

### Example 1: Contract Tests (Phase 3.2)
All contract tests can run in parallel (different files, no dependencies):
```bash
# Launch T005-T007 together
pytest tests/contract/test_connection_api.py &
pytest tests/contract/test_testing_fixtures_api.py &
pytest tests/contract/test_container_api.py &
wait
```

### Example 2: Model Creation (Phase 3.3)
All model files can be created in parallel:
```bash
# T012-T015 in parallel
# Different files, no dependencies
```

### Example 3: Integration Tests (Phase 3.10)
All integration tests can run in parallel:
```bash
pytest tests/integration/ -n auto  # pytest-xdist parallel execution
```

### Example 4: Documentation (Phase 3.12)
All docs can be written in parallel:
```bash
# T058-T064 in parallel
# Different markdown files
```

---

## Validation Checklist

**Before starting implementation**:
- [x] All contracts have corresponding tests (T005-T007)
- [x] All entities have model tasks (T012-T015)
- [x] All tests come before implementation (Phase 3.2 before 3.3+)
- [x] Parallel tasks truly independent (marked [P] correctly)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task

**After implementation**:
- [ ] All contract tests pass
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] 95%+ test coverage achieved
- [ ] All code formatted (black + isort)
- [ ] All code type-checked (mypy)
- [ ] All code linted (flake8)
- [ ] Quickstart validation passes
- [ ] Backwards compatibility verified

---

## Task Execution Tips

1. **Start with structure**: T001-T004 set up everything
2. **TDD strictly**: Write failing tests (T005-T011) before ANY implementation
3. **Extract carefully**: Reference source files in `~/ws/rag-templates/`
4. **Type hints**: Add full Python 3.9+ type hints to all extracted code
5. **Test coverage**: Check coverage after each module (`pytest --cov`)
6. **Incremental**: Commit after each task
7. **Constitutional**: Verify each implementation follows CONSTITUTION.md principles

---

**Total Tasks**: 74
**Estimated Parallel Groups**: 15 (can reduce wall-clock time significantly)
**Source Extraction**: ~1080 lines from rag-templates
**New Code**: ~630 lines
**Target Total**: ~1710 lines package code + ~1500 lines tests

**Ready for execution**: ✅
**Next step**: Execute T001 to create project structure
