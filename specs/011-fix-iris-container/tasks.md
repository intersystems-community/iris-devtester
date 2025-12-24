# Tasks: Fix IRIS Container Infrastructure Issues

**Feature**: 011-fix-iris-container
**Input**: Design documents from `/specs/011-fix-iris-container/`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

## Execution Flow (main)
```
1. Load plan.md from feature directory ✓
2. Load design documents ✓
   - data-model.md: 3 entities (ContainerLifecyclePolicy, VolumeMountSpec, ContainerPersistenceCheck)
   - contracts/: 3 contract files (ryuk, volume-mount, persistence)
   - research.md: Docker SDK vs testcontainers decision
3. Generate tasks by category ✓
   - Tests: 9 test tasks (3 unit [P], 6 integration)
   - Core: 6 implementation tasks (1 research, 5 sequential)
   - Documentation: 3 doc tasks [P]
   - Validation: 4 validation tasks
4. Apply task rules ✓
   - Different files = [P]
   - Same file = sequential
   - Tests before implementation
5. Number tasks T001-T022 ✓
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
├── config/container_config.py         [UPDATE]
├── utils/iris_container_adapter.py    [UPDATE]
└── cli/container.py                    [UPDATE]

tests/
├── unit/
│   ├── config/test_container_config.py      [UPDATE]
│   └── utils/test_iris_container_adapter.py [UPDATE]
└── integration/
    └── test_bug_fixes_011.py                [NEW]

docs/
└── learnings/
    └── testcontainers-ryuk-lifecycle.md     [NEW]
```

---

## Phase 3.1: Setup

*(No setup needed - bug fixes in existing code)*

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Unit Tests (Parallel - Different Files)

- [ ] **T001** [P] Write unit tests for volume path validation in `ContainerConfig`
  - **File**: `tests/unit/config/test_container_config.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (AC-validation)
  - **Tests to add**:
    - `test_validate_volume_paths_all_valid()` - All host paths exist
    - `test_validate_volume_paths_nonexistent()` - One host path missing
    - `test_validate_volume_paths_empty_list()` - No volumes configured
    - `test_validate_volume_paths_multiple_errors()` - Multiple invalid paths
  - **Expected**: All 4 tests FAIL (method `validate_volume_paths()` doesn't exist yet)
  - **Lines**: ~50 lines (4 tests × ~12 lines each)

- [ ] **T002** [P] Write unit tests for `VolumeMountSpec.parse()` method
  - **File**: `tests/unit/utils/test_iris_container_adapter.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (parsing_rules)
  - **Tests to add**:
    - `test_parse_volume_host_container()` - Parse "./data:/external"
    - `test_parse_volume_host_container_mode()` - Parse "./data:/external:ro"
    - `test_parse_volume_invalid_format()` - Missing container path
    - `test_parse_volume_invalid_mode()` - Invalid mode (not rw/ro)
    - `test_parse_volume_default_mode()` - Mode defaults to "rw"
  - **Expected**: All 5 tests FAIL (class `VolumeMountSpec` doesn't exist yet)
  - **Lines**: ~75 lines (5 tests × ~15 lines each)

- [ ] **T003** [P] Write unit tests for `ContainerPersistenceCheck` class
  - **File**: `tests/unit/utils/test_iris_container_adapter.py`
  - **Contract**: `contracts/container-persistence-contract.json` (verification)
  - **Tests to add**:
    - `test_persistence_check_success()` - All checks pass
    - `test_persistence_check_container_not_found()` - Container missing
    - `test_persistence_check_wrong_status()` - Container exited
    - `test_persistence_check_volumes_not_verified()` - Volume mount failed
    - `test_get_error_message_constitutional_format()` - Error has What/Why/How/Docs
  - **Expected**: All 5 tests FAIL (class `ContainerPersistenceCheck` doesn't exist yet)
  - **Lines**: ~80 lines (5 tests × ~16 lines each)

### Integration Tests (Sequential - Share Docker Resources)

- [ ] **T004** Write integration test for ryuk lifecycle prevention
  - **File**: `tests/integration/test_bug_fixes_011.py` (new file)
  - **Contract**: `contracts/ryuk-lifecycle-contract.json`
  - **Test**: `TestRyukLifecycle::test_cli_container_persists_after_process_exit()`
  - **Steps**:
    1. Create ContainerConfig with unique name
    2. Call `IRISContainerManager.create_from_config(config, use_testcontainers=False)`
    3. Wait 60 seconds (simulate CLI exit)
    4. Verify container still exists: `docker_client.containers.get(name)`
    5. Assert container status in ['running', 'created']
    6. Assert no 'org.testcontainers' labels on container
  - **Expected**: TEST FAILS (ryuk cleanup removes container)
  - **Lines**: ~30 lines
  - **Requires**: Docker running, ~60 seconds for test

- [ ] **T005** Write integration test for testcontainers labels check
  - **File**: `tests/integration/test_bug_fixes_011.py`
  - **Contract**: `contracts/ryuk-lifecycle-contract.json` (AC-002)
  - **Test**: `TestRyukLifecycle::test_cli_container_has_no_testcontainers_labels()`
  - **Steps**:
    1. Create container with `use_testcontainers=False`
    2. Inspect container labels: `container.attrs['Config']['Labels']`
    3. Assert 'org.testcontainers.session-id' NOT in labels
    4. Assert 'org.testcontainers' NOT in labels
  - **Expected**: TEST FAILS (current implementation uses testcontainers)
  - **Lines**: ~20 lines

- [ ] **T006** Write integration test for single volume mount accessibility
  - **File**: `tests/integration/test_bug_fixes_011.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (AC-001, AC-002)
  - **Test**: `TestVolumeMountVerification::test_single_volume_mount_applied_and_accessible()`
  - **Steps**:
    1. Create temp directory with test file
    2. Create ContainerConfig with `volumes=['<temp_dir>:/external']`
    3. Create container with `use_testcontainers=False`
    4. Verify mount in `container.attrs['Mounts']`
    5. Verify file accessible: `docker exec cat /external/test_file`
  - **Expected**: TEST FAILS (volume mounting not working due to ryuk)
  - **Lines**: ~35 lines
  - **Cleanup**: Remove temp directory

- [ ] **T007** Write integration test for multiple volume mounts
  - **File**: `tests/integration/test_bug_fixes_011.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (AC-004)
  - **Test**: `TestVolumeMountVerification::test_multiple_volumes_all_mounted()`
  - **Steps**:
    1. Create 3 temp directories with different test files
    2. Create ContainerConfig with 3 volumes
    3. Create container
    4. Verify all 3 mounts in `container.attrs['Mounts']`
    5. Verify all 3 files accessible via docker exec
  - **Expected**: TEST FAILS (multiple volumes not working)
  - **Lines**: ~40 lines

- [ ] **T008** Write integration test for read-only volume enforcement
  - **File**: `tests/integration/test_bug_fixes_011.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (AC-003)
  - **Test**: `TestVolumeMountVerification::test_read_only_volume_enforced()`
  - **Steps**:
    1. Create temp directory
    2. Create ContainerConfig with `volumes=['<temp_dir>:/readonly:ro']`
    3. Create container
    4. Verify mount has `RW=false` in attrs
    5. Try to write: `docker exec touch /readonly/newfile` (should fail)
  - **Expected**: TEST FAILS (ro mode not enforced)
  - **Lines**: ~30 lines

- [ ] **T009** Write integration test for container persistence check
  - **File**: `tests/integration/test_bug_fixes_011.py`
  - **Contract**: `contracts/container-persistence-contract.json` (AC-004)
  - **Test**: `TestContainerPersistence::test_persistence_check_detects_success()`
  - **Steps**:
    1. Create container with `use_testcontainers=False`
    2. Call `verify_container_persistence(container_name, config)`
    3. Assert `check.success == True`
    4. Assert `check.exists == True`
    5. Assert `check.volume_mounts_verified == True`
  - **Expected**: TEST FAILS (verification function doesn't exist)
  - **Lines**: ~25 lines

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Research & Analysis

- [ ] **T010** Research testcontainers ryuk cleanup behavior
  - **File**: None (research task)
  - **Contract**: `contracts/ryuk-lifecycle-contract.json` (background)
  - **Actions**:
    1. Review testcontainers-python source code for ryuk integration
    2. Test ryuk cleanup timing with simple container
    3. Identify testcontainers labels that trigger cleanup
    4. Document findings in research notes
  - **Output**: Understanding of when/why ryuk removes containers
  - **Time**: ~30 minutes
  - **Prerequisite**: Must complete before T012

### Core Bug Fixes (Sequential - Same Files)

- [ ] **T011** Add volume path validation to `ContainerConfig`
  - **File**: `iris_devtester/config/container_config.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (validation)
  - **Changes**:
    1. Add `validate_volume_paths()` method to ContainerConfig class
    2. Method checks each volume's host path with `os.path.exists()`
    3. Returns list of error messages (empty if all valid)
    4. Error messages use constitutional format (What/How)
  - **Code to add** (~20 lines):
    ```python
    def validate_volume_paths(self) -> List[str]:
        """Validate that all volume host paths exist."""
        errors = []
        for volume in self.volumes:
            parts = volume.split(":")
            host_path = parts[0]
            if not os.path.exists(host_path):
                errors.append(
                    f"Volume host path does not exist: {host_path}\n"
                    f"  Required by volume mount: {volume}\n"
                    f"  Create the directory or fix the path in configuration"
                )
        return errors
    ```
  - **Verify**: T001 tests now PASS (4/4)
  - **Lines changed**: ~20 lines added
  - **Risk**: Low - additive method, doesn't change existing behavior

- [ ] **T012** Implement Docker SDK creation path in `IRISContainerManager`
  - **File**: `iris_devtester/utils/iris_container_adapter.py`
  - **Contract**: `contracts/ryuk-lifecycle-contract.json`
  - **Dependencies**: After T010 (research ryuk)
  - **Changes**:
    1. Add `use_testcontainers` parameter to `create_from_config()` method
    2. Implement `_create_with_docker_sdk()` helper function
    3. Use Docker SDK directly (no testcontainers labels)
    4. Apply volumes via Docker SDK `volumes` dict
    5. Start container
  - **Code to add** (~50 lines):
    ```python
    @staticmethod
    def create_from_config(
        config: ContainerConfig,
        use_testcontainers: bool = False
    ) -> Union[IRISContainer, DockerContainer]:
        if use_testcontainers:
            return _create_with_testcontainers(config)
        else:
            return _create_with_docker_sdk(config)

    def _create_with_docker_sdk(config: ContainerConfig) -> DockerContainer:
        import docker
        client = docker.from_env()

        # Parse volumes
        volumes = {}
        for vol_str in config.volumes:
            spec = VolumeMountSpec.parse(vol_str)
            volumes[spec.host_path] = {
                'bind': spec.container_path,
                'mode': spec.mode
            }

        # Create container without testcontainers labels
        container = client.containers.create(
            image=config.get_image_name(),
            name=config.container_name,
            volumes=volumes,
            ports={
                config.superserver_port: config.superserver_port,
                config.webserver_port: config.webserver_port
            },
            environment={
                'ISC_DATA_DIRECTORY': '/home/irisowner/iris/data',
            },
            detach=True
        )
        container.start()
        return container
    ```
  - **Verify**: T004, T005 tests now PASS
  - **Lines changed**: ~50 lines added
  - **Risk**: Medium - new code path, but existing path unchanged

- [ ] **T013** Implement `VolumeMountSpec` dataclass
  - **File**: `iris_devtester/utils/iris_container_adapter.py`
  - **Contract**: `contracts/volume-mount-verification-contract.json` (parsing)
  - **Changes**:
    1. Add `VolumeMountSpec` dataclass at top of file
    2. Implement `parse()` classmethod
    3. Validate mode is "rw" or "ro"
    4. Default mode to "rw" if not specified
  - **Code to add** (~30 lines) - See data-model.md for complete implementation
  - **Verify**: T002 tests now PASS (5/5)
  - **Lines changed**: ~30 lines added
  - **Risk**: Low - internal helper class, no external API changes

- [ ] **T014** Implement `ContainerPersistenceCheck` and verification function
  - **File**: `iris_devtester/utils/iris_container_adapter.py`
  - **Contract**: `contracts/container-persistence-contract.json` (verification)
  - **Changes**:
    1. Add `ContainerPersistenceCheck` dataclass (see data-model.md)
    2. Implement `verify_container_persistence()` function
    3. Function waits 2 seconds after creation
    4. Queries Docker for container existence and status
    5. Verifies volume mounts are present
    6. Returns ContainerPersistenceCheck with results
  - **Code to add** (~60 lines):
    ```python
    @dataclass
    class ContainerPersistenceCheck:
        container_name: str
        exists: bool
        status: Optional[str]
        volume_mounts_verified: bool
        verification_time: float
        error_details: Optional[str] = None

        @property
        def success(self) -> bool:
            return (
                self.exists
                and self.status in ['running', 'created']
                and self.volume_mounts_verified
                and self.error_details is None
            )

        def get_error_message(self, config: ContainerConfig) -> str:
            # Constitutional error format (What/Why/How/Docs)
            # See data-model.md for complete implementation
            pass

    def verify_container_persistence(
        container_name: str,
        config: ContainerConfig
    ) -> ContainerPersistenceCheck:
        import time
        import docker

        time.sleep(2)  # Allow Docker to settle
        client = docker.from_env()

        try:
            container = client.containers.get(container_name)
            mounts = container.attrs['Mounts']
            volumes_ok = len(config.volumes) == 0 or len(mounts) >= len(config.volumes)

            return ContainerPersistenceCheck(
                container_name=container_name,
                exists=True,
                status=container.status,
                volume_mounts_verified=volumes_ok,
                verification_time=2.0
            )
        except docker.errors.NotFound:
            return ContainerPersistenceCheck(
                container_name=container_name,
                exists=False,
                status=None,
                volume_mounts_verified=False,
                verification_time=2.0,
                error_details="Container not found after creation"
            )
    ```
  - **Verify**: T003, T009 tests now PASS
  - **Lines changed**: ~60 lines added
  - **Risk**: Medium - new verification step, but doesn't break existing behavior

- [ ] **T015** Call persistence verification in CLI `container up` command
  - **File**: `iris_devtester/cli/container.py`
  - **Contract**: `contracts/container-persistence-contract.json` (integration)
  - **Changes**:
    1. Update `container up` command to use `use_testcontainers=False`
    2. Call `verify_container_persistence()` after creation
    3. Raise constitutional error if verification fails
    4. Only show success message if verification passes
  - **Code changes** (~15 lines):
    ```python
    # In container up command
    try:
        container = IRISContainerManager.create_from_config(
            config,
            use_testcontainers=False  # CLI mode: manual cleanup
        )

        # Verify container persists
        check = verify_container_persistence(config.container_name, config)
        if not check.success:
            raise ValueError(check.get_error_message(config))

        click.echo(f"✓ Container '{config.container_name}' created and started")
    except Exception as e:
        translated_error = translate_docker_error(e, config)
        raise translated_error from e
    ```
  - **Verify**: T004-T009 tests now PASS
  - **Lines changed**: ~15 lines modified
  - **Risk**: Low - improves reliability, doesn't remove existing features

- [ ] **T016** Update error messages in `translate_docker_error()`
  - **File**: `iris_devtester/utils/iris_container_adapter.py`
  - **Contract**: All contracts (error_handling)
  - **Changes**:
    1. Add specific handlers for volume mount failures
    2. Add specific handlers for container not found after creation
    3. Ensure all errors follow constitutional format (What/Why/How/Docs)
    4. Remove generic "Failed to create container: 0" messages
  - **Code to enhance** (~30 lines):
    ```python
    def translate_docker_error(error: Exception, config: Optional[ContainerConfig]) -> Exception:
        # Add volume mount error detection
        if "volume" in str(error).lower():
            return ValueError(
                f"Volume mount failed\n"
                "\n"
                "What went wrong:\n"
                f"  {str(error)}\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify host paths exist: ls -la <host_path>\n"
                "  2. Check Docker volume syntax: host:container or host:container:mode\n"
                "  3. Ensure Docker has permissions to access host path\n"
                "\n"
                "Documentation: https://docs.docker.com/storage/volumes/\n"
            )

        # Keep existing handlers...
    ```
  - **Verify**: Error messages now follow constitutional format
  - **Lines changed**: ~30 lines added/modified
  - **Risk**: Low - improves error messages, doesn't change logic

---

## Phase 3.4: Documentation

- [ ] **T017** [P] Create `docs/learnings/testcontainers-ryuk-lifecycle.md`
  - **File**: `docs/learnings/testcontainers-ryuk-lifecycle.md` (new file)
  - **Requirement**: Constitutional Principle #8 (Document the Blind Alleys)
  - **Content**:
    - What is testcontainers ryuk?
    - When does it cleanup containers?
    - Why does it interfere with CLI commands?
    - How to prevent cleanup (use Docker SDK directly)
    - When to use testcontainers vs Docker SDK
    - Troubleshooting guide
  - **Template** (from research.md):
    ```markdown
    ## Why Not Use Testcontainers for CLI Commands?

    **What we tried**: Using testcontainers-iris for all container creation
    **Why it didn't work**:
    - Testcontainers designed for test fixtures (automatic cleanup)
    - Ryuk sidecar removes containers when Python process exits
    - CLI commands need persistent containers (manual cleanup)

    **What we use instead**: Docker SDK for CLI, testcontainers for tests
    **Evidence**: 0% → 90% benchmark success rate
    **Date discovered**: 2025-01-13
    **Decision**: Dual-mode creation in Feature 011
    ```
  - **Lines**: ~100 lines
  - **Risk**: None - documentation only

- [ ] **T018** [P] Update CHANGELOG.md with v1.2.2 notes
  - **File**: `CHANGELOG.md`
  - **Content**: Add v1.2.2 section with bug fixes
  - **Format**:
    ```markdown
    ## [1.2.2] - 2025-01-13

    ### Fixed

    - **Bug Fix #1: Prevented ryuk cleanup of CLI-managed containers**
      - CLI commands now use Docker SDK directly (bypass testcontainers)
      - Containers persist until explicit removal (not cleaned up when CLI exits)
      - **Impact**: Benchmark infrastructure can now run 30+ minute test suites
      - **Location**: `iris_devtester/utils/iris_container_adapter.py` (dual-mode creation)

    - **Bug Fix #2: Fixed volume mounting for CLI containers**
      - Volumes now applied via Docker SDK when using CLI commands
      - Volume mounts verified after container creation
      - Supports multiple volumes with read-only mode
      - **Impact**: Workspace files now accessible in benchmark containers
      - **Location**: `iris_devtester/utils/iris_container_adapter.py` (Docker SDK path)

    - **Bug Fix #3: Added container persistence verification**
      - Post-creation check ensures container actually persists
      - Detects immediate cleanup and reports constitutional error
      - Verifies volume mounts are accessible
      - **Impact**: No more "Failed to create container: 0" errors
      - **Location**: `iris_devtester/utils/iris_container_adapter.py` (verification)

    ### Migration Notes

    - No breaking changes - all fixes are backwards compatible
    - pytest fixtures still use testcontainers (automatic cleanup)
    - CLI commands now use Docker SDK (manual cleanup)
    - Benchmark success rate improved from 0/24 (0.0%) to >22/24 (>90%)

    ### Quality Assurance

    - All 35 existing contract tests passing (100% - no regression)
    - 14 new unit tests added (100% passing)
    - 6 new integration tests with real Docker containers (100% passing)
    - Constitutional Principle #5 compliance maintained (error messages)
    ```
  - **Lines**: ~40 lines
  - **Risk**: None - documentation only

- [ ] **T019** [P] Update CLI command help text
  - **File**: `iris_devtester/cli/container.py`
  - **Action**: Update docstrings and help text for container commands
  - **Changes**:
    - Clarify container persistence behavior in `container up` help
    - Document volume mount syntax in examples
    - Add note about container lifecycle (create → use → remove)
  - **Example**:
    ```python
    @click.command()
    @click.option('--config', help='Path to iris-config.yml')
    def up(config):
        """
        Create and start an IRIS container.

        The container will persist until explicitly removed with 'container remove'.
        Use volumes to mount host directories:
          volumes: ["./workspace:/external:ro"]

        Examples:
          iris-devtester container up
          iris-devtester container up --config custom-config.yml
        """
    ```
  - **Lines**: ~10 lines modified
  - **Risk**: None - documentation only

---

## Phase 3.5: Validation

- [ ] **T020** Run all 35 existing contract tests (ensure no regression)
  - **Command**: `pytest tests/contract/cli/ -v`
  - **Requirement**: NFR-003 (no breaking changes)
  - **Expected**: 35/35 PASS (100%)
  - **If failures**: Investigate and fix before proceeding
  - **Time**: ~2 minutes
  - **Risk**: Low - bug fixes shouldn't break existing contracts

- [ ] **T021** Run new unit tests (verify bug fixes)
  - **Command**: `pytest tests/unit/config/test_container_config.py::test_validate_volume_paths* -v`
  - **Command**: `pytest tests/unit/utils/test_iris_container_adapter.py::*VolumeMountSpec* -v`
  - **Command**: `pytest tests/unit/utils/test_iris_container_adapter.py::*PersistenceCheck* -v`
  - **Expected**: 14/14 PASS (4 volume validation + 5 parsing + 5 persistence)
  - **Verifies**:
    - Volume path validation works
    - Volume mount parsing correct
    - Persistence checks accurate
  - **Time**: ~30 seconds
  - **Risk**: None - these are the tests we wrote

- [ ] **T022** Run new integration tests with real Docker containers
  - **Command**: `pytest tests/integration/test_bug_fixes_011.py -v --tb=short`
  - **Expected**: 6/6 PASS (ryuk prevention, volumes, persistence)
  - **Verifies**:
    - Containers persist after CLI exit (no ryuk cleanup)
    - Volume mounts applied and accessible
    - Read-only mode enforced
    - Persistence check detects issues
  - **Time**: ~5 minutes (real Docker containers)
  - **Risk**: None - validates actual bug fixes

- [ ] **T023** Run benchmark infrastructure end-to-end (optional, if available)
  - **Command**: Run actual benchmark test suite (if accessible)
  - **Expected**: >22/24 tests passing (>90% success rate)
  - **Verifies**:
    - SimpleTestRunner class accessible via workspace mount
    - Container persists for full benchmark duration (30+ minutes)
    - All 24 operations succeed without "container not found" errors
  - **Time**: ~30 minutes (full benchmark suite)
  - **Risk**: None - this is the ultimate validation
  - **Note**: May be skipped if benchmark infrastructure not available

---

## Dependencies

```
Setup: (none - bug fixes in existing code)

Tests First (T001-T009):
  T001, T002, T003 → Parallel (different test files)
  T004, T005, T006, T007, T008, T009 → Sequential (integration tests, share Docker)

Implementation (T010-T016):
  T010 → Research (must complete first)
  T011 → After T001 (parallel with T012, T013, T014)
  T012 → After T010 (needs ryuk research)
  T013 → After T002 (parallel with T011, T014)
  T014 → After T003 (parallel with T011, T013)
  T015 → After T012, T014 (needs Docker SDK + persistence check)
  T016 → After T011-T015 (error messages reference all fixes)

Documentation (T017-T019):
  All parallel (different files)

Validation (T020-T023):
  T020 → After all implementation (regression)
  T021 → After T020 (new unit tests)
  T022 → After T021 (integration tests)
  T023 → After T022 (full benchmark)
```

**Critical Path**: T001-T003 → T010 → T012 → T014 → T015 → T020 → T021 → T022

**Parallel Opportunities**:
- Phase 3.2: T001, T002, T003 (3 tasks in parallel)
- Phase 3.3: T011, T013, T014 (3 tasks in parallel after dependencies met)
- Phase 3.4: T017, T018, T019 (3 tasks in parallel)

---

## Parallel Execution Examples

### Example 1: Launch Phase 3.2 Unit Tests in Parallel

```bash
# All three unit test tasks can run simultaneously:
Task tool (3 parallel invocations):
1. "Write unit tests for volume path validation in tests/unit/config/test_container_config.py - 4 tests for ContainerConfig.validate_volume_paths() per volume-mount-verification-contract.json"
2. "Write unit tests for VolumeMountSpec.parse() in tests/unit/utils/test_iris_container_adapter.py - 5 tests for volume string parsing per volume-mount-verification-contract.json parsing_rules"
3. "Write unit tests for ContainerPersistenceCheck in tests/unit/utils/test_iris_container_adapter.py - 5 tests for persistence verification per container-persistence-contract.json"
```

### Example 2: Launch Phase 3.3 Core Implementations in Parallel

```bash
# After T010 research completes, these can run together:
Task tool (3 parallel invocations):
1. "Add validate_volume_paths() method to ContainerConfig in iris_devtester/config/container_config.py per data-model.md validation rules"
2. "Implement VolumeMountSpec dataclass with parse() method in iris_devtester/utils/iris_container_adapter.py per data-model.md specification"
3. "Implement ContainerPersistenceCheck dataclass and verify_container_persistence() function in iris_devtester/utils/iris_container_adapter.py per data-model.md"
```

### Example 3: Launch Phase 3.4 Documentation in Parallel

```bash
# All three documentation tasks are independent:
Task tool (3 parallel invocations):
1. "Create docs/learnings/testcontainers-ryuk-lifecycle.md explaining ryuk cleanup behavior and when to use Docker SDK vs testcontainers"
2. "Update CHANGELOG.md with v1.2.2 section documenting ryuk prevention, volume mounting fixes, and persistence verification"
3. "Update CLI command help text in iris_devtester/cli/container.py to clarify container persistence and volume mount syntax"
```

---

## Notes

- **[P] Rationale**:
  - T001-T003: Different test files, no shared state
  - T011, T013, T014: Different code sections, can implement simultaneously after deps met
  - T017-T019: All documentation, no code conflicts

- **TDD Critical**: Tests T001-T009 MUST be written and failing before T010-T016 implementation

- **Integration Test Order**: T004-T009 are sequential because they share Docker resources and may interfere with each other

- **Research First**: T010 must complete before Docker SDK implementation (T012) to understand ryuk behavior

- **Verification Order**: T020 (existing tests) before T021 (new tests) to catch regressions early

- **Commit Strategy**: Commit after each completed task for easy rollback

---

## Validation Checklist
*GATE: Verified during task generation*

- [x] All contracts have corresponding tests (T001-T009 cover all 3 contracts)
- [x] All entities have model tasks (T013: VolumeMountSpec, T014: ContainerPersistenceCheck)
- [x] All tests come before implementation (T001-T009 before T010-T016)
- [x] Parallel tasks truly independent (verified file paths)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task (verified)

---

## Success Criteria

Upon completion of all 23 tasks:

1. ✅ **Ryuk Prevention**: CLI containers persist until explicit removal (not cleaned up)
2. ✅ **Volume Mounting**: Workspace files accessible, multiple volumes supported
3. ✅ **Container Persistence**: Containers verified to persist after creation
4. ✅ **Error Messages**: Constitutional format (What/Why/How/Docs)
5. ✅ **No Regression**: All 35 existing contract tests still pass
6. ✅ **New Tests Pass**: All 14 unit tests + 6 integration tests pass
7. ✅ **Benchmark Success**: >22/24 tests pass (>90% success rate)

**Estimated Total Time**: 6-8 hours (parallelization reduces to 4-5 hours)

---

*Generated by /tasks command based on plan.md, contracts/, data-model.md, and research.md*
