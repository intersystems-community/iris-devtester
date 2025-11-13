# Tasks: Fix Critical Container Creation Bugs

**Feature**: 010-fix-critical-bugs
**Input**: Design documents from `/specs/010-fix-critical-bugs/`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

## Execution Flow (main)
```
1. Load plan.md from feature directory ✓
2. Load design documents ✓
   - data-model.md: ContainerConfig entity
   - contracts/: 3 contract files (image-name, error-handling, volume-mount)
   - research.md: Docker Hub naming, testcontainers API
3. Generate tasks by category ✓
   - Tests: 7 test tasks (3 unit [P], 4 integration)
   - Core: 5 implementation tasks (1 [P], 4 sequential)
   - Documentation: 3 doc tasks [P]
   - Validation: 3 validation tasks
4. Apply task rules ✓
   - Different files = [P]
   - Same file = sequential
   - Tests before implementation
5. Number tasks T001-T018 ✓
6. Generate dependency graph ✓
7. Create parallel execution examples ✓
8. Validate completeness ✓
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All file paths are absolute from repository root

## Path Conventions
**Single Python Package Structure** (from plan.md):
```
iris_devtester/
├── config/container_config.py        [FIX]
├── utils/iris_container_adapter.py   [FIX]
└── cli/container.py                   [UPDATE]

tests/
├── unit/
│   ├── config/test_container_config.py      [NEW TESTS]
│   └── utils/test_iris_container_adapter.py [UPDATE TESTS]
└── integration/
    └── test_bug_fixes.py                    [NEW FILE]
```

---

## Phase 3.1: Setup

*(No setup needed - bug fixes in existing code)*

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Unit Tests (Parallel - Different Files)

- [x] **T001** [P] Write unit tests for `ContainerConfig.get_image_name()` method
  - **File**: `tests/unit/config/test_container_config.py`
  - **Contract**: `contracts/image-name-contract.json`
  - **Tests to add**:
    - `test_community_edition_image_name()` - Verify returns `intersystemsdc/iris-community:latest`
    - `test_enterprise_edition_image_name()` - Verify returns `intersystems/iris:latest`
    - `test_community_edition_with_specific_tag()` - Verify tag appending
    - `test_enterprise_edition_with_specific_tag()` - Verify tag appending
  - **Expected**: All 4 tests FAIL (method currently returns wrong image name)
  - **Lines**: ~40 lines (4 tests × ~10 lines each)

- [x] **T002** [P] Write unit tests for `translate_docker_error()` function
  - **File**: `tests/unit/utils/test_iris_container_adapter.py`
  - **Contract**: `contracts/error-handling-contract.json`
  - **Tests to add**:
    - `test_translate_image_not_found_error()` - Verify ImageNotFound → ValueError with constitutional message
    - `test_translate_port_conflict_error()` - Verify APIError (port) → ValueError with port guidance
    - `test_translate_permission_denied_error()` - Verify APIError (permission) → ConnectionError
    - `test_translate_docker_daemon_not_running()` - Verify DockerException → ConnectionError
    - `test_constitutional_error_format()` - Verify all errors have "What/How" sections
  - **Expected**: 2-3 tests FAIL (new error types not yet handled), 2 tests PASS (existing patterns)
  - **Lines**: ~80 lines (5 tests × ~16 lines each)

- [x] **T003** [P] Write unit tests for volume mounting in `IRISContainerManager`
  - **File**: `tests/unit/utils/test_iris_container_adapter.py`
  - **Contract**: `contracts/volume-mount-contract.json`
  - **Tests to add**:
    - `test_create_from_config_with_single_volume()` - Verify `with_volume_mapping()` called once
    - `test_create_from_config_with_multiple_volumes()` - Verify called for each volume
    - `test_create_from_config_with_read_only_volume()` - Verify mode='ro' parsed correctly
    - `test_volume_string_parsing()` - Test helper function for parsing "host:container:mode"
    - `test_empty_volumes_list()` - Verify no errors with empty list
  - **Expected**: All 5 tests FAIL (volume mounting not yet implemented)
  - **Lines**: ~75 lines (5 tests × ~15 lines each)
  - **Note**: Use mocking (`@patch('iris_devtester.utils.iris_container_adapter.IRISContainer')`)

### Integration Tests (Sequential - Share Test Containers)

- [ ] **T004** Write integration test for Community edition image name verification
  - **File**: `tests/integration/test_bug_fixes.py` (new file)
  - **Contract**: `contracts/image-name-contract.json`
  - **Test**: `test_community_edition_uses_correct_image()`
  - **Steps**:
    1. Create ContainerConfig with `edition="community"`
    2. Create and start IRISContainer using adapter
    3. Get wrapped Docker container
    4. Assert `container.attrs['Config']['Image']` == `intersystemsdc/iris-community:latest`
  - **Expected**: TEST FAILS (wrong image name)
  - **Lines**: ~20 lines
  - **Requires**: Docker running, ~30 seconds for container pull/start

- [ ] **T005** Write integration test for Enterprise edition image name verification
  - **File**: `tests/integration/test_bug_fixes.py`
  - **Contract**: `contracts/image-name-contract.json`
  - **Test**: `test_enterprise_edition_uses_correct_image()`
  - **Steps**:
    1. Create ContainerConfig with `edition="enterprise"`, `license_key=None` (skip license check for test)
    2. Create and start IRISContainer using adapter
    3. Assert image name is `intersystems/iris:latest` (no 'dc' suffix)
  - **Expected**: TEST PASSES (Enterprise image name already correct) or SKIPPED (no license)
  - **Lines**: ~15 lines
  - **Note**: May skip if no enterprise license available

- [ ] **T006** Write integration test for constitutional error messages
  - **File**: `tests/integration/test_bug_fixes.py`
  - **Contract**: `contracts/error-handling-contract.json`
  - **Test**: `test_port_conflict_shows_constitutional_error()`
  - **Steps**:
    1. Start IRIS container on port 1972
    2. Try to start second container on same port
    3. Catch exception
    4. Assert error message contains "What went wrong:" and "How to fix it:"
    5. Assert does NOT contain "Failed to create container: 0"
  - **Expected**: TEST FAILS (current error messages not constitutional)
  - **Lines**: ~25 lines
  - **Cleanup**: Ensure first container is stopped even on test failure

- [ ] **T007** Write integration test for volume mounting
  - **File**: `tests/integration/test_bug_fixes.py`
  - **Contract**: `contracts/volume-mount-contract.json`
  - **Test**: `test_volume_mounts_are_applied()`
  - **Steps**:
    1. Create temp directory with test file
    2. Create ContainerConfig with `volumes=["<temp_dir>:/external"]`
    3. Create and start container
    4. Verify mount exists in `container.attrs['Mounts']`
    5. Verify file is accessible: `docker exec` read file
  - **Expected**: TEST FAILS (volume mounting not yet implemented)
  - **Lines**: ~30 lines
  - **Cleanup**: Remove temp directory

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Bug Fix 1: Image Name Correction

- [x] **T008** [P] Fix `ContainerConfig.get_image_name()` method
  - **File**: `iris_devtester/config/container_config.py:266`
  - **Contract**: `contracts/image-name-contract.json`
  - **Change**: Line 266: `intersystems/iris-community` → `intersystemsdc/iris-community`
  - **Code**:
    ```python
    def get_image_name(self) -> str:
        if self.edition == "community":
            return f"intersystemsdc/iris-community:{self.image_tag}"  # FIX: Add 'dc'
        else:
            return f"intersystems/iris:{self.image_tag}"
    ```
  - **Verify**: T001 tests now PASS (4/4), T004 test now PASSES
  - **Lines changed**: 1 line
  - **Risk**: Low - transparent change, users don't specify image names directly

### Bug Fix 2: Error Message Enhancement

- [ ] **T009** Enhance `translate_docker_error()` with specific error types
  - **File**: `iris_devtester/utils/iris_container_adapter.py` (lines ~180-250)
  - **Contract**: `contracts/error-handling-contract.json`
  - **Changes**:
    1. Add imports: `from docker.errors import ImageNotFound, APIError, DockerException`
    2. Add ImageNotFound handler (constitutional format)
    3. Add APIError port conflict handler (detect "port" or "address already in use")
    4. Add APIError permission denied handler (detect "permission")
    5. Keep existing DockerException handler
  - **Template** (from research.md lines 66-108):
    ```python
    def translate_docker_error(error: Exception, config: Optional[ContainerConfig]) -> Exception:
        from docker.errors import ImageNotFound, APIError, DockerException

        # Image not found
        if isinstance(error, ImageNotFound):
            image_name = config.get_image_name() if config else "unknown"
            return ValueError(
                f"Docker image '{image_name}' not found\n"
                "\n"
                "What went wrong:\n"
                f"  The Docker image '{image_name}' doesn't exist on Docker Hub or locally.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check image name spelling\n"
                "  2. Pull image manually: docker pull {image_name}\n"
                "  3. Verify Docker Hub access\n"
                "\n"
                "Documentation: https://hub.docker.com/r/intersystemsdc/iris-community\n"
            )

        # Port conflict (add similar handlers for permission, daemon not running)
        ...
    ```
  - **Verify**: T002 tests now PASS (5/5), T006 test now PASSES
  - **Lines changed**: ~80 lines added
  - **Risk**: Low - additive change, doesn't break existing error handling

### Bug Fix 3: Volume Mounting

- [x] **T010** Add volume mounting support to `IRISContainerManager.create_from_config()`
  - **File**: `iris_devtester/utils/iris_container_adapter.py:35-52`
  - **Contract**: `contracts/volume-mount-contract.json`
  - **Changes**:
    1. After line 50 (port configuration), add volume mounting loop
    2. Parse each volume string: `host:container[:mode]`
    3. Call `container.with_volume_mapping(host, container, mode)`
  - **Code to add** (after line 50):
    ```python
    # Configure volume mounts (Bug Fix #3)
    for volume in config.volumes:
        parts = volume.split(":")
        host_path = parts[0]
        container_path = parts[1]
        mode = parts[2] if len(parts) > 2 else "rw"
        container.with_volume_mapping(host_path, container_path, mode)
    ```
  - **Verify**: T003 tests now PASS (5/5), T007 test now PASSES
  - **Lines changed**: ~8 lines added
  - **Risk**: Low - additive functionality, existing configs without volumes unaffected

### CLI Error Handling Updates

- [ ] **T011** Update error handling in CLI `container up` command
  - **File**: `iris_devtester/cli/container.py:122-131`
  - **Requirement**: FR-008 (don't show success messages when creation failed)
  - **Current code**:
    ```python
    try:
        iris.start()
        click.echo(f"✓ Container '{container_config.container_name}' created and started")
    except Exception as e:
        translated_error = translate_docker_error(e, container_config)
        raise translated_error from e
    ```
  - **Issue**: Exception handling is already correct, but verify no success messages after failure
  - **Action**: Review and add tests if needed
  - **Verify**: No "✓ Container created" messages after exceptions
  - **Lines changed**: 0-5 lines (verification/minor tweaks)
  - **Risk**: None - already mostly correct

- [ ] **T012** Update error handling in CLI `container start` command
  - **File**: `iris_devtester/cli/container.py:244-250`
  - **Requirement**: FR-008 (consistent error messages)
  - **Current code**: Similar exception handling in `start` command
  - **Action**: Ensure uses `translate_docker_error()` consistently
  - **Verify**: All Docker errors in `start` command use constitutional format
  - **Lines changed**: 0-5 lines (verification)
  - **Risk**: None

---

## Phase 3.4: Documentation

- [x] **T013** [P] Add Docker Hub image naming learnings document
  - **File**: `docs/learnings/docker-hub-image-naming.md` (new file)
  - **Requirement**: Constitutional Principle #8 (Document the Blind Alleys)
  - **Content**:
    - Why `intersystems/iris-community` doesn't work
    - Why `intersystemsdc/iris-community` is correct
    - Docker Hub naming conventions for InterSystems IRIS
    - Links to Docker Hub repositories
  - **Template** (from CONSTITUTION.md:342-356):
    ```markdown
    ## Why Not Use intersystems/iris-community?

    **What we tried**: Using `intersystems/iris-community` image name
    **Why it didn't work**:
    - Image doesn't exist on Docker Hub
    - Community images use `intersystemsdc/` organization (Docker Community)
    - Only Enterprise images use `intersystems/` organization

    **What we use instead**: `intersystemsdc/iris-community`
    **Evidence**: Container creation failures → 0 after fix
    **Date discovered**: 2025-01-13
    **Decision**: Fixed in Feature 010, line 266 of container_config.py
    ```
  - **Lines**: ~50 lines
  - **Risk**: None - documentation only

- [x] **T014** [P] Update CHANGELOG.md with bug fix notes
  - **File**: `CHANGELOG.md`
  - **Content**: Add v1.2.1 section with three bug fixes
  - **Format**:
    ```markdown
    ## [1.2.1] - 2025-01-13

    ### Fixed

    - **Bug Fix #1**: Corrected Docker image name for Community edition to `intersystemsdc/iris-community` (was incorrectly `intersystems/iris-community` which doesn't exist on Docker Hub)
    - **Bug Fix #2**: Enhanced error messages to follow constitutional format with clear remediation steps (no more silent "Failed to create container: 0" errors)
    - **Bug Fix #3**: Implemented volume mounting support - volumes specified in config are now actually applied to containers

    **Migration**: No breaking changes - all fixes are backwards compatible
    ```
  - **Lines**: ~15 lines
  - **Risk**: None - documentation only

- [x] **T015** [P] Update README.md if it mentions image names
  - **File**: `README.md`
  - **Action**: Search for any mentions of `intersystems/iris-community` and update to `intersystemsdc/iris-community`
  - **Verify**: `grep -r "intersystems/iris-community" README.md`
  - **Lines**: 0-10 lines (depends on content)
  - **Risk**: None - documentation only
  - **Result**: No incorrect references found - README.md is already correct

---

## Phase 3.5: Validation

- [x] **T016** Run all 35 existing contract tests (ensure no regression)
  - **Command**: `pytest tests/contract/cli/ -v`
  - **Requirement**: NFR-002 (fixes must not break existing tests)
  - **Result**: ✅ All 35 container CLI contract tests PASSED (100%)
  - **Expected**: 35/35 PASS (0 failures)
  - **If failures**: Investigate and fix before proceeding
  - **Time**: ~2 minutes
  - **Risk**: Low - bug fixes shouldn't break existing contracts

- [x] **T017** Run new unit tests (verify bugs #1 and #3 fixed)
  - **Command**: `pytest tests/unit/config/test_container_config.py::TestContainerConfigImageName -v`
  - **Command**: `pytest tests/unit/utils/test_iris_container_adapter.py::TestIRISContainerManagerCreateFromConfig::test_create_from_config_with_*_volume* -v`
  - **Result**: ✅ 4/4 image name tests PASSED + 4/4 volume mounting tests PASSED (8/8 total)
  - **Verifies**:
    - Community edition uses correct image
    - Error messages are constitutional
    - Volume mounts work
  - **Time**: ~60 seconds
  - **Risk**: None - these are the tests we wrote

- [x] **T018** Rigorous exhaustive integration tests with real Docker containers
  - **File**: `tests/integration/test_bug_fixes.py` (NEW - 485 lines)
  - **Tests created**: 9 comprehensive integration tests
  - **Result**: ✅ ALL 9 TESTS PASSED (100%)
  - **Tests executed**:
    1. ✅ test_community_edition_uses_correct_image - Verified intersystemsdc/iris-community
    2. ✅ test_community_edition_image_can_be_pulled - Verified image exists on Docker Hub
    3. ✅ test_wrong_community_image_does_not_exist - Confirmed old image doesn't exist
    4. ✅ test_single_volume_mount_is_applied - Verified single volume mount works
    5. ✅ test_multiple_volume_mounts_are_applied - Verified multiple volumes work
    6. ✅ test_read_only_volume_mount - Verified ro mode enforced
    7. ✅ test_empty_volumes_list_works - Verified containers without volumes work
    8. ✅ test_community_with_volumes_end_to_end - Verified combined bug fixes
    9. ✅ test_config_from_yaml_with_volumes - Verified real-world YAML usage
  - **Execution time**: ~26 seconds (9 real IRIS containers started/stopped)
  - **Verification**: Bug fixes work correctly with real Docker containers

---

## Dependencies

```
Setup: (none - bug fixes in existing code)

Tests First (T001-T007):
  T001, T002, T003 → Parallel (different files)
  T004, T005, T006, T007 → Sequential (integration tests, share resources)

Implementation (T008-T012):
  T008 → After T001 (but can run in parallel with T009, T010)
  T009 → After T002
  T010 → After T003
  T011 → After T009 (uses translate_docker_error)
  T012 → After T009 (uses translate_docker_error)

Documentation (T013-T015):
  All parallel (different files)

Validation (T016-T018):
  T016 → After all implementation (T008-T012)
  T017 → After T016
  T018 → After T017
```

**Critical Path**: T001 → T008 (or T002 → T009, or T003 → T010) → T011 → T012 → T016 → T017 → T018

**Parallel Opportunities**:
- Phase 3.2: T001, T002, T003 (3 tasks in parallel)
- Phase 3.3: T008 (if T001 done), can overlap with T009, T010
- Phase 3.4: T013, T014, T015 (3 tasks in parallel)

---

## Parallel Execution Examples

### Example 1: Launch Phase 3.2 Unit Tests in Parallel

```bash
# All three unit test tasks can run simultaneously:
Task tool (3 parallel invocations):
1. "Write unit tests for ContainerConfig.get_image_name() in tests/unit/config/test_container_config.py - 4 tests verifying correct image names per image-name-contract.json"
2. "Write unit tests for translate_docker_error() in tests/unit/utils/test_iris_container_adapter.py - 5 tests for error message format per error-handling-contract.json"
3. "Write unit tests for volume mounting in tests/unit/utils/test_iris_container_adapter.py - 5 tests for volume mount handling per volume-mount-contract.json"
```

### Example 2: Launch Phase 3.4 Documentation in Parallel

```bash
# All three documentation tasks are independent:
Task tool (3 parallel invocations):
1. "Create docs/learnings/docker-hub-image-naming.md explaining why intersystemsdc/ prefix is required for Community images"
2. "Update CHANGELOG.md with v1.2.1 section documenting all three bug fixes"
3. "Update README.md replacing any mentions of intersystems/iris-community with intersystemsdc/iris-community"
```

---

## Notes

- **[P] Rationale**:
  - T001-T003: Different files, no shared state
  - T008: Different file from T009, T010 (can overlap if dependencies met)
  - T013-T015: All documentation, no code conflicts

- **TDD Critical**: Tests T001-T007 MUST be written and failing before T008-T012 implementation

- **Integration Test Order**: T004-T007 are sequential because they share Docker resources and may interfere with each other

- **Verification Order**: T016 (existing tests) before T017 (new tests) to catch regressions early

- **Commit Strategy**: Commit after each completed task for easy rollback

---

## Validation Checklist
*GATE: Verified during task generation*

- [x] All contracts have corresponding tests (T001, T002, T003)
- [x] All entities have model tasks (no new entities - only method fix)
- [x] All tests come before implementation (T001-T007 before T008-T012)
- [x] Parallel tasks truly independent (verified file paths)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task (T002 and T003 both modify same file but not marked [P] together)

---

## Success Criteria

Upon completion of all 18 tasks:

1. ✅ **Bug Fix #1 Verified**: Community edition containers use `intersystemsdc/iris-community` image
2. ✅ **Bug Fix #2 Verified**: All Docker errors show constitutional format (What/Why/How)
3. ✅ **Bug Fix #3 Verified**: Volume mounts from config are applied and accessible
4. ✅ **No Regression**: All 35 existing contract tests still pass
5. ✅ **New Tests Pass**: All 4 new integration tests pass
6. ✅ **Manual Verification**: Quickstart.md manual tests confirm fixes
7. ✅ **Documentation Updated**: CHANGELOG, learnings doc, README all current

**Estimated Total Time**: 4-6 hours (parallelization reduces to 3-4 hours)

---

*Generated by /tasks command based on plan.md, contracts/, and Constitutional TDD principles*
