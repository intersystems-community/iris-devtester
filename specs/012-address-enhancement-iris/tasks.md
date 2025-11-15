# Tasks: DBAPI Package Compatibility

**Feature**: 012-address-enhancement-iris
**Input**: Design documents from `/Users/tdyar/ws/iris-devtester/specs/012-address-enhancement-iris/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Execution Flow (main)
```
1. Load plan.md from feature directory ✅
   → Tech stack: Python 3.9+, pytest, testcontainers
   → Libraries: intersystems-irispython (optional), intersystems-iris (optional)
   → Structure: iris_devtester/utils/dbapi_compat.py (new), updates to connections/, fixtures/, testing/
2. Load optional design documents ✅
   → data-model.md: DBAPIPackageInfo, DBAPIConnectionAdapter abstractions
   → contracts/: 4 contract files (modern, legacy, no-package, priority)
   → research.md: Try/except import chain, version validation, logging strategy
3. Generate tasks by category ✅
   → Setup: Create dbapi_compat module, add type hints
   → Tests: 4 contract tests, 6 integration tests, 5 unit tests
   → Core: Package detection, adapter, version validation, error handling
   → Integration: Update connections, fixtures, testing utilities
   → Polish: Unit tests, documentation, migration guide
4. Apply task rules ✅
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001-T030) ✅
6. Generate dependency graph ✅
7. Create parallel execution examples ✅
8. Validate task completeness ✅
   → All 4 contracts have tests ✅
   → All abstractions have implementations ✅
   → All integration points updated ✅
9. Return: SUCCESS (30 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 3.1: Setup (T001-T003)

### T001: Create dbapi_compat module structure ✅
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Action**: Create new module with:
- Module docstring explaining DBAPI package compatibility
- Empty placeholder for `detect_dbapi_package()` function
- Empty placeholder for `DBAPIConnectionAdapter` class
- Empty placeholder for `get_connection()` function
- Empty placeholder for `get_package_info()` function
**Success**: File exists with placeholders, imports cleanly

### T002: Add type hints and dataclass for DBAPIPackageInfo ✅
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Action**: Define DBAPIPackageInfo dataclass with:
- `package_name: str`
- `import_path: str`
- `version: str`
- `connect_function: Callable`
- `detection_time_ms: float`
**Dependencies**: T001
**Success**: Dataclass defined, type hints correct, no import errors

### T003 [P]: Configure logging for package detection ✅
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Action**: Add logging setup:
- Import logging module
- Create logger instance (`logger = logging.getLogger(__name__)`)
- Add log level documentation (INFO/DEBUG/ERROR)
**Success**: Logger configured, ready for use in detection functions

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### T004 [P]: Contract test for modern package detection ✅
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_modern_package_contract.py`
**Contract**: `contracts/modern-package-contract.json`
**Action**: Create failing contract test with:
- `test_modern_package_detected()`: Mock intersystems-irispython available, verify detected
- `test_modern_package_import_path()`: Verify import_path is "intersystems_iris.dbapi._DBAPI"
- `test_connection_successful()`: Verify connection succeeds with modern package
- `test_detection_time_under_threshold()`: Verify detection_time_ms < 10
- `test_package_info_correct()`: Verify package_name, version correct
- `test_logging_modern_package()`: Verify INFO log contains "intersystems-irispython"
- `test_version_validation()`: Verify version >= 5.3.0 enforced
**Success**: 7 tests created, all fail with "not implemented" or ImportError

### T005 [P]: Contract test for legacy package fallback ✅
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_legacy_package_contract.py`
**Contract**: `contracts/legacy-package-contract.json`
**Action**: Create failing contract test with:
- `test_legacy_package_detected()`: Mock only intersystems-iris available, verify detected
- `test_legacy_package_import_path()`: Verify import_path is "iris.irissdk"
- `test_connection_successful()`: Verify connection succeeds with legacy package
- `test_modern_package_attempted_first()`: Verify DEBUG log shows fallback
- `test_fallback_occurred()`: Verify fallback from modern to legacy happened
- `test_detection_time_under_threshold()`: Verify detection_time_ms < 10
- `test_package_info_correct()`: Verify package_name is "intersystems-iris"
- `test_logging_legacy_package()`: Verify INFO log contains "intersystems-iris (legacy)"
- `test_version_validation()`: Verify version >= 3.0.0 enforced
- `test_backward_compatibility_fixtures()`: Verify DAT fixtures work with legacy
- `test_backward_compatibility_connections()`: Verify connections work with legacy
**Success**: 11 tests created, all fail with "not implemented" or ImportError

### T006 [P]: Contract test for no package error ✅
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_package_detection.py`
**Contract**: `contracts/no-package-error-contract.json`
**Action**: Create failing contract test (class `TestNoPackageError`) with:
- `test_import_error_raised()`: Mock neither package available, verify ImportError
- `test_error_message_has_header()`: Verify error starts with "No IRIS Python package detected"
- `test_error_message_has_what_section()`: Verify "What went wrong:" in error
- `test_error_message_has_why_section()`: Verify "Why this happened:" in error
- `test_error_message_has_how_section()`: Verify "How to fix it:" in error
- `test_error_message_has_documentation_link()`: Verify "Documentation:" + URL in error
- `test_error_message_suggests_modern_package()`: Verify "intersystems-irispython>=5.3.0" in error
- `test_error_message_provides_install_command()`: Verify "pip install" in error
- `test_error_message_mentions_both_packages()`: Verify both packages mentioned
- `test_logging_error_level()`: Verify ERROR log for detection failure
- `test_both_imports_attempted()`: Verify both modern and legacy imports tried
**Success**: 11 tests created, all fail with "not implemented" or ImportError

### T007 [P]: Contract test for package priority ✅
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_package_detection.py`
**Contract**: `contracts/package-priority-contract.json`
**Action**: Create failing contract test (class `TestPackagePriority`) with:
- `test_modern_package_selected()`: Mock both packages, verify modern selected
- `test_legacy_package_not_attempted()`: Verify no fallback log when modern available
- `test_connection_uses_modern_package()`: Verify connection from modern package
- `test_detection_time_under_threshold()`: Verify detection_time_ms < 10
- `test_package_info_shows_modern()`: Verify package_name is "intersystems-irispython"
- `test_logging_modern_package_selected()`: Verify INFO log shows modern selected
- `test_no_fallback_in_logs()`: Verify no "trying legacy" in logs
- `test_modern_invalid_legacy_valid_raises_error()`: Modern v5.2.0 (invalid), legacy v3.2.0 (valid) → error
- `test_modern_valid_legacy_invalid_uses_modern()`: Modern v5.3.0, legacy v2.9.0 → uses modern
**Success**: 9 tests created, all fail with "not implemented" or ImportError

### T008 [P]: Integration test for fixtures with modern package
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/test_fixtures_with_modern.py`
**Scenario**: Quickstart Scenario 5 (DAT fixtures with modern package)
**Action**: Create integration test with real IRIS container:
- `test_create_fixture_with_modern_package()`: Create DAT fixture, verify success
- `test_load_fixture_with_modern_package()`: Load DAT fixture, verify tables loaded
- `test_checksum_validation_with_modern_package()`: Verify checksums validated
**Success**: 3 tests created, all fail (implementation not complete)

### T009 [P]: Integration test for fixtures with legacy package
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/test_fixtures_with_legacy.py`
**Scenario**: Quickstart Scenario 2 (legacy package backward compatibility)
**Action**: Create integration test with real IRIS container:
- `test_create_fixture_with_legacy_package()`: Create DAT fixture, verify success
- `test_load_fixture_with_legacy_package()`: Load DAT fixture, verify tables loaded
- `test_backward_compatibility_maintained()`: Verify no code changes needed
**Success**: 3 tests created, all fail (implementation not complete)

### T010 [P]: Integration test for dual package environment
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/test_dual_package_env.py`
**Scenario**: Quickstart Scenario 4 (both packages installed)
**Action**: Create integration test simulating both packages:
- `test_modern_prioritized_when_both_installed()`: Verify modern selected
- `test_connection_works_with_priority()`: Verify connection succeeds
- `test_fixtures_work_with_priority()`: Verify DAT operations work
**Success**: 3 tests created, all fail (implementation not complete)

### T011 [P]: Unit test for package detection logic
**File**: `/Users/tdyar/ws/iris-devtester/tests/unit/connections/test_dbapi_compat.py`
**Action**: Create unit tests for detection with mocks:
- `test_detect_modern_package_success()`: Mock modern package, verify detection
- `test_detect_legacy_package_success()`: Mock legacy package, verify detection
- `test_detect_no_package_error()`: Mock neither package, verify error
- `test_detect_both_packages_prioritizes_modern()`: Mock both, verify modern selected
- `test_version_validation_modern_min_version()`: Test version >= 5.3.0 check
- `test_version_validation_legacy_min_version()`: Test version >= 3.0.0 check
- `test_version_validation_too_old_error()`: Test version too old raises error
- `test_detection_time_measurement()`: Verify detection_time_ms populated
- `test_singleton_adapter_caching()`: Verify adapter is singleton
**Success**: 9 tests created, all fail (implementation not complete)

### T012 [P]: Unit test for connection adapter
**File**: `/Users/tdyar/ws/iris-devtester/tests/unit/connections/test_dbapi_compat.py`
**Action**: Create unit tests for DBAPIConnectionAdapter:
- `test_adapter_initialization()`: Verify adapter initializes with detected package
- `test_adapter_connect_delegates_to_package()`: Verify connect() uses package's connect()
- `test_adapter_get_package_info()`: Verify get_package_info() returns correct info
- `test_adapter_zero_overhead()`: Verify direct function call (no wrapper)
**Success**: 4 tests created, all fail (implementation not complete)

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### T013: Implement package detection logic
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Dependencies**: T001, T002, T003, T004-T007 (tests must fail first)
**Action**: Implement `detect_dbapi_package()` function:
- Try importing `intersystems_iris.dbapi._DBAPI` first
- If ImportError, try `iris.irissdk` second
- If both fail, raise DBAPIPackageNotFoundError with constitutional format
- Measure detection time with `time.perf_counter()`
- Log INFO when package detected, DEBUG on fallback, ERROR on failure
- Return DBAPIPackageInfo with all fields populated
**Success**: T004-T007 contract tests pass (modern, legacy, no-package, priority)

### T014: Implement version validation
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Dependencies**: T013
**Action**: Implement `validate_package_version()` function:
- Use `importlib.metadata.version()` to get package version
- Use `packaging.version.Version` for comparison
- Validate modern package >= 5.3.0
- Validate legacy package >= 3.0.0
- Raise ImportError with constitutional format if version too old
**Success**: Version validation tests pass (T004, T005, T011)

### T015: Implement DBAPIConnectionAdapter class
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Dependencies**: T013, T014
**Action**: Implement DBAPIConnectionAdapter:
- `__init__()`: Call detect_dbapi_package() and store result
- `connect()`: Delegate to detected package's connect function
- `get_package_info()`: Return cached DBAPIPackageInfo
- Implement as singleton pattern (module-level instance)
**Success**: Adapter tests pass (T012), connection tests pass

### T016: Implement convenience functions
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Dependencies**: T015
**Action**: Implement public API functions:
- `get_connection(*args, **kwargs)`: Call adapter.connect()
- `get_package_info()`: Call adapter.get_package_info()
- Update module `__all__` export list
**Success**: Functions work, can be imported and used

### T017: Implement constitutional error class
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/dbapi_compat.py`
**Dependencies**: T013
**Action**: Implement DBAPIPackageNotFoundError:
- Subclass ImportError
- Error message follows What/Why/How/Docs format
- Include both package options (modern and legacy)
- Include pip install commands
- Include documentation link
**Success**: T006 no-package error tests pass

---

## Phase 3.4: Integration

### T018: Update connections/dbapi.py to use dbapi_compat
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/connections/dbapi.py`
**Dependencies**: T016
**Action**: Replace direct imports with dbapi_compat:
- Remove `import iris.irissdk` if present
- Add `from iris_devtester.utils.dbapi_compat import get_connection`
- Replace `iris.irissdk.connect()` with `get_connection()`
- Update all DBAPI connection code paths
**Success**: Connections work with both packages, no direct imports

### T019: Update connections/connection.py to use adapter
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/connections/connection.py`
**Dependencies**: T018
**Action**: Update connection manager:
- Use `get_connection()` from dbapi_compat
- Remove any hardcoded package imports
**Success**: Connection manager works with both packages

### T020: Update connections/manager.py to log package selection
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/connections/manager.py`
**Dependencies**: T019
**Action**: Add package detection logging:
- Import `get_package_info()` from dbapi_compat
- Log which package is being used at INFO level
- Include package version in log message
**Success**: Logs show package selection (FR-010 satisfied)

### T021: Update fixtures/creator.py to use dbapi_compat
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/fixtures/creator.py`
**Dependencies**: T016
**Action**: Replace direct imports with dbapi_compat:
- Remove `import iris.irissdk` if present
- Add `from iris_devtester.utils.dbapi_compat import get_connection`
- Replace all DBAPI connection calls with `get_connection()`
**Success**: DAT fixture creation works with both packages (T008, T009 pass)

### T022: Update fixtures/loader.py to use dbapi_compat
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/fixtures/loader.py`
**Dependencies**: T021
**Action**: Replace direct imports with dbapi_compat:
- Remove `import iris.irissdk` if present
- Add `from iris_devtester.utils.dbapi_compat import get_connection`
- Replace all DBAPI connection calls with `get_connection()`
**Success**: DAT fixture loading works with both packages (T008, T009 pass)

### T023: Update testing/schema_reset.py to use dbapi_compat
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/testing/schema_reset.py`
**Dependencies**: T016
**Action**: Replace direct imports with dbapi_compat:
- Remove `import iris.irissdk` if present
- Add `from iris_devtester.utils.dbapi_compat import get_connection`
- Replace all DBAPI connection calls with `get_connection()`
**Success**: Schema reset works with both packages

### T024: Update utils/password_reset.py to use dbapi_compat
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/password_reset.py`
**Dependencies**: T016
**Action**: Replace direct imports with dbapi_compat:
- Remove `import iris.irissdk` if present
- Add `from iris_devtester.utils.dbapi_compat import get_connection`
- Replace all DBAPI connection calls with `get_connection()`
**Success**: Password reset works with both packages

---

## Phase 3.5: Polish

### T025 [P]: Update README.md with package compatibility info
**File**: `/Users/tdyar/ws/iris-devtester/README.md`
**Dependencies**: T024 (all integration complete)
**Action**: Add section on DBAPI package support:
- Document both supported packages
- Explain automatic detection
- Show installation commands for both packages
- Mention modern package recommended
- Link to migration guide
**Success**: README explains package compatibility clearly

### T026 [P]: Create package migration guide
**File**: `/Users/tdyar/ws/iris-devtester/docs/learnings/package-migration-guide.md`
**Dependencies**: T024 (all integration complete)
**Action**: Create comprehensive migration guide:
- When to use modern vs legacy package
- How to check which package is installed
- How to upgrade from legacy to modern
- Performance comparison
- Troubleshooting package detection issues
- Version compatibility matrix
**Success**: Migration guide created, linked from README

### T027 [P]: Update pyproject.toml dependencies
**File**: `/Users/tdyar/ws/iris-devtester/pyproject.toml`
**Dependencies**: T024 (all integration complete)
**Action**: Update dependencies to reflect optional packages:
- Make both packages optional dependencies
- Add to `[project.optional-dependencies]` section
- Document that at least one is required for DBAPI
- Update dependency comments
**Success**: pyproject.toml reflects optional nature of both packages

### T028 [P]: Add package detection to CLI diagnostics
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/cli/diagnostics.py` (or similar)
**Dependencies**: T024 (all integration complete)
**Action**: Add package info to diagnostics output:
- Call `get_package_info()` in diagnostics command
- Display package name, version, import path
- Display detection time
- Show whether modern or legacy
**Success**: CLI shows package information clearly

### T029 [P]: Run full integration test suite
**File**: All integration tests (T008, T009, T010)
**Dependencies**: T024 (all integration complete)
**Action**: Execute comprehensive integration tests:
- Run all integration tests with modern package
- Run all integration tests with legacy package
- Run all integration tests with both packages
- Verify 95%+ test coverage maintained
**Success**: All integration tests pass, coverage >= 95%

### T030: Update CHANGELOG.md for Feature 012
**File**: `/Users/tdyar/ws/iris-devtester/CHANGELOG.md`
**Dependencies**: T029 (all tests passing)
**Action**: Add Feature 012 entry to changelog:
- Version bump to v1.3.0
- Feature: DBAPI Package Compatibility
- List all functional requirements satisfied
- List all non-functional requirements satisfied
- Document backward compatibility
- Document performance characteristics
- Link to migration guide
**Success**: CHANGELOG.md updated, ready for release

---

## Dependencies Graph

```
Setup:
T001 → T002 → T003

Tests (must fail first):
T004, T005, T006, T007, T008, T009, T010, T011, T012 (all parallel)

Core Implementation:
T001,T002,T003 → T013 (package detection)
T013 → T014 (version validation)
T013 → T017 (error class)
T013,T014 → T015 (adapter)
T015 → T016 (convenience functions)

Integration (sequential - modifying existing files):
T016 → T018 (connections/dbapi.py)
T018 → T019 (connections/connection.py)
T019 → T020 (connections/manager.py)
T016 → T021 (fixtures/creator.py)
T021 → T022 (fixtures/loader.py)
T016 → T023 (testing/schema_reset.py)
T016 → T024 (utils/password_reset.py)

Polish (all parallel after integration):
T024 → T025, T026, T027, T028, T029 (all parallel)
T029 → T030 (changelog last)
```

---

## Parallel Execution Examples

### Phase 3.2: Launch all contract tests together
```bash
# All contract tests can run in parallel (different files)
# Using Task agent (example):
Task: "Create contract test for modern package detection in tests/contract/test_modern_package_contract.py per T004"
Task: "Create contract test for legacy package fallback in tests/contract/test_legacy_package_contract.py per T005"
Task: "Create contract test for no package error in tests/contract/test_package_detection.py (TestNoPackageError class) per T006"
Task: "Create contract test for package priority in tests/contract/test_package_detection.py (TestPackagePriority class) per T007"
```

### Phase 3.2: Launch integration and unit tests together
```bash
# Integration and unit tests can run in parallel (different files)
Task: "Create integration test for fixtures with modern package in tests/integration/test_fixtures_with_modern.py per T008"
Task: "Create integration test for fixtures with legacy package in tests/integration/test_fixtures_with_legacy.py per T009"
Task: "Create integration test for dual package environment in tests/integration/test_dual_package_env.py per T010"
Task: "Create unit tests for package detection logic in tests/unit/connections/test_dbapi_compat.py per T011"
Task: "Create unit tests for connection adapter in tests/unit/connections/test_dbapi_compat.py per T012"
```

### Phase 3.5: Launch all polish tasks together
```bash
# Documentation and polish tasks can run in parallel (different files)
Task: "Update README.md with package compatibility info per T025"
Task: "Create package migration guide in docs/learnings/package-migration-guide.md per T026"
Task: "Update pyproject.toml dependencies per T027"
Task: "Add package detection to CLI diagnostics per T028"
Task: "Run full integration test suite per T029"
```

---

## Notes

### TDD Workflow
1. **Phase 3.2**: Write ALL tests first (T004-T012)
2. **Verify**: Run pytest - ALL tests MUST FAIL
3. **Phase 3.3**: Implement core logic (T013-T017)
4. **Verify**: Run pytest - contract tests SHOULD PASS
5. **Phase 3.4**: Integration (T018-T024)
6. **Verify**: Run pytest - ALL tests SHOULD PASS

### Constitutional Compliance Checkpoints
- **T013**: Package detection must be automatic (Principle #4)
- **T014**: Version validation with clear errors (Principle #5)
- **T017**: Constitutional error format (Principle #5)
- **T020**: Logging for transparency (Principle #5, FR-010)
- **T029**: 95%+ coverage (Principle #7, NFR-003)

### Performance Checkpoints
- **T011**: Verify detection_time_ms < 10ms (NFR-001)
- **T015**: Verify zero connection overhead
- **T029**: Verify no performance regression

### Parallel Execution Rules
- [P] tasks = different files, can run together
- Sequential tasks = same file or dependencies
- Always verify tests before implementation

---

## Task Validation Checklist

- [x] All 4 contracts have corresponding tests (T004-T007)
- [x] All abstractions have implementation tasks (T013-T017)
- [x] All integration points updated (T018-T024)
- [x] All tests come before implementation (Phase 3.2 before 3.3)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD workflow enforced (tests must fail first)
- [x] Constitutional compliance verified
- [x] Performance requirements tracked

---

## Execution Status

**Total Tasks**: 30
**Setup**: 3 tasks (T001-T003)
**Tests**: 9 tasks (T004-T012) - Must fail before implementation
**Core**: 5 tasks (T013-T017) - Implement only after tests fail
**Integration**: 7 tasks (T018-T024) - Sequential updates
**Polish**: 6 tasks (T025-T030) - Final documentation and validation

**Status**: ✅ Tasks generated - Ready for execution via `/implement`

---

**Next Command**: `/implement` (will execute tasks in dependency order)
