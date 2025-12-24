# Implementation Plan: Fix IRIS Container Infrastructure Issues

**Branch**: `011-fix-iris-container` | **Date**: 2025-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-fix-iris-container/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path ✓
   → Spec found: 18 functional requirements, 4 non-functional requirements
2. Fill Technical Context ✓
   → Project Type: Single Python package (iris-devtester)
   → Structure: Existing iris_devtester/ source tree
3. Fill Constitution Check section ✓
   → Evaluated against 8 constitutional principles
4. Evaluate Constitution Check section ✓
   → No violations detected
   → Update Progress Tracking: Initial Constitution Check ✓
5. Execute Phase 0 → research.md ✓
   → Research testcontainers ryuk, volume mounting, container lifecycle
6. Execute Phase 1 → contracts, data-model.md, quickstart.md ✓
7. Re-evaluate Constitution Check section ✓
   → No new violations after design
   → Update Progress Tracking: Post-Design Constitution Check ✓
8. Plan Phase 2 → Task generation approach documented ✓
9. STOP - Ready for /tasks command ✓
```

**IMPORTANT**: The /plan command STOPS at step 8. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

**Primary Requirement**: Fix three critical container infrastructure failures preventing benchmark tests from running:
1. Testcontainers ryuk service immediately removes CLI-managed containers
2. Volume mounts specified in configuration are not applied to containers
3. Containers don't persist for long-running benchmark test execution

**Technical Approach**:
- Investigate testcontainers-iris lifecycle management and ryuk cleanup behavior
- Fix volume mounting implementation in IRISContainerManager
- Add container persistence verification after creation
- Implement direct Docker SDK fallback for CLI-managed containers
- Enhance error messages to distinguish between creation, mount, and cleanup failures

**Success Metric**: Benchmark success rate improves from 0/24 (0.0%) to >22/24 (>90%)

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- `testcontainers>=4.0.0` - Container management
- `testcontainers-iris>=1.2.2` - IRIS container support
- `docker>=6.0.0` - Docker SDK for Python
- `pydantic>=2.0.0` - Configuration validation
- `click>=8.0.0` - CLI framework

**Storage**: N/A (container configuration only)
**Testing**: pytest with integration tests using real Docker containers
**Target Platform**: Linux, macOS (Docker-compatible environments)
**Project Type**: Single Python package (iris-devtester)
**Performance Goals**:
- Container creation with volumes: <60 seconds
- Volume mount verification: <5 seconds
- Container persistence: Until explicit cleanup (30+ minutes for benchmarks)

**Constraints**:
- Must maintain backward compatibility with iris-devtester 1.2.1 configurations
- All 35 existing contract tests must pass (no regression)
- Volume mounts must support Docker syntax: `host:container` and `host:container:mode`
- Must work with testcontainers-iris library and direct Docker SDK

**Scale/Scope**:
- 3 core bug fixes in existing code
- Affects 2 source files (container_config.py, iris_container_adapter.py)
- 1 CLI command (container up)
- Benchmark infrastructure with 24 tests

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Constitutional Principle Compliance

**Principle #1: Automatic Remediation Over Manual Intervention**
- ✅ **COMPLIANT**: Volume mount validation added (FR-016)
- ✅ **COMPLIANT**: Container persistence verification (FR-017)
- ✅ **COMPLIANT**: Constitutional error messages with remediation (FR-014)

**Principle #2: Choose the Right Tool for the Job**
- ✅ **COMPLIANT**: Feature uses Docker SDK for container management (appropriate tool)
- ✅ **COMPLIANT**: testcontainers-iris for IRIS-specific operations
- ✅ **COMPLIANT**: No SQL/ObjectScript execution involved

**Principle #3: Isolation by Default**
- ✅ **COMPLIANT**: Fix enables proper test isolation for benchmark infrastructure
- ✅ **COMPLIANT**: Volume mounts allow each test to have isolated workspace
- ✅ **COMPLIANT**: Container persistence until explicit cleanup

**Principle #4: Zero Configuration Viable**
- ✅ **COMPLIANT**: Fixes don't add new required configuration
- ✅ **COMPLIANT**: Volume mounts are optional (backward compatible)
- ✅ **COMPLIANT**: Existing configurations continue to work

**Principle #5: Fail Fast with Guidance**
- ✅ **COMPLIANT**: FR-014 requires What/Why/How/Docs error format
- ✅ **COMPLIANT**: FR-015 distinguishes creation/mount/cleanup failures
- ✅ **COMPLIANT**: FR-013 eliminates misleading "Failed to create container: 0"

**Principle #6: Enterprise Ready, Community Friendly**
- ✅ **COMPLIANT**: Fixes apply to both Community and Enterprise editions
- ✅ **COMPLIANT**: Bug Fix #1 in v1.2.1 already fixed Community image name
- ✅ **COMPLIANT**: No edition-specific changes required

**Principle #7: Medical-Grade Reliability**
- ✅ **COMPLIANT**: NFR-003 requires all 35 contract tests to pass
- ✅ **COMPLIANT**: Integration tests with real Docker containers (not mocks)
- ✅ **COMPLIANT**: Container persistence verification before reporting success

**Principle #8: Document the Blind Alleys**
- ✅ **COMPLIANT**: Will document testcontainers ryuk cleanup behavior
- ✅ **COMPLIANT**: Will document volume mounting gotchas
- ✅ **COMPLIANT**: Add to docs/learnings/ per constitutional requirement

**Result**: ✅ ALL CONSTITUTIONAL PRINCIPLES COMPLIANT

## Project Structure

### Documentation (this feature)
```
specs/011-fix-iris-container/
├── spec.md              # Feature specification (✓ complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── ryuk-lifecycle-contract.json
│   ├── volume-mount-verification-contract.json
│   └── container-persistence-contract.json
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
iris_devtester/
├── config/
│   └── container_config.py         # [UPDATE] Add volume path validation
├── utils/
│   └── iris_container_adapter.py   # [FIX] Volume mounting, ryuk handling, persistence
└── cli/
    └── container.py                 # [UPDATE] Enhanced error messages

tests/
├── contract/
│   └── cli/
│       └── test_container_lifecycle.py  # [UPDATE] Add persistence tests
├── integration/
│   └── test_bug_fixes_011.py            # [NEW] Ryuk, volumes, persistence tests
└── unit/
    ├── config/
    │   └── test_container_config.py     # [UPDATE] Add volume validation tests
    └── utils/
        └── test_iris_container_adapter.py  # [UPDATE] Add volume mount tests

docs/
└── learnings/
    └── testcontainers-ryuk-lifecycle.md  # [NEW] Document ryuk cleanup behavior
```

**Structure Decision**: Single Python package structure (Option 1). This is an existing codebase with established structure. Feature fixes bugs in existing modules rather than adding new ones.

## Phase 0: Outline & Research

### Research Tasks

1. **Testcontainers Ryuk Cleanup Behavior**
   - How does testcontainers ryuk service work?
   - When does it cleanup containers?
   - How to prevent cleanup of CLI-managed containers?
   - Can we disable ryuk for specific containers?
   - What labels/configurations trigger immediate cleanup?

2. **Volume Mounting with testcontainers-iris**
   - What is the correct API for volume mounting in testcontainers-iris?
   - Why is `with_volume_mapping()` not working in current implementation?
   - Are there known issues with testcontainers volume mounting?
   - Do we need Docker SDK fallback for volume mounting?

3. **Container Persistence Strategies**
   - How do CLI-managed containers differ from pytest-managed containers?
   - Can we detach containers from testcontainers lifecycle?
   - Should we use Docker SDK directly for CLI commands?
   - What's the best pattern for long-running test infrastructure?

4. **Error "Failed to create container: 0" Root Cause**
   - What causes exit code 0 in container creation failure?
   - Is this a testcontainers-iris issue or our adapter issue?
   - How do we detect vs creation failure, mount failure, cleanup?

**Output**: research.md with findings and recommended approaches

## Phase 1: Design & Contracts

### Data Model (data-model.md)

**Entities**:

1. **ContainerLifecyclePolicy**
   - Type: Configuration enum
   - Values: `TESTCONTAINERS_MANAGED`, `CLI_MANAGED`, `PERSISTENT`
   - Purpose: Determines cleanup behavior
   - Default: `CLI_MANAGED` for CLI commands

2. **VolumeMountSpec**
   - Fields:
     - `host_path`: str (absolute path on host)
     - `container_path`: str (path inside container)
     - `mode`: str ("rw" or "ro")
     - `validated`: bool (host path exists check)
   - Purpose: Structured volume mount representation
   - Validation: Host path must exist before container creation

3. **ContainerPersistenceCheck**
   - Fields:
     - `container_name`: str
     - `created_at`: datetime
     - `persisted`: bool (container still exists after creation)
     - `volume_mounts_verified`: bool (all volumes accessible)
     - `error_details`: Optional[str]
   - Purpose: Post-creation verification results
   - Used by: Container creation to verify success

### API Contracts (contracts/ directory)

1. **ryuk-lifecycle-contract.json**
   - Purpose: Prevent testcontainers ryuk cleanup of CLI containers
   - Test: Create container via CLI, wait 60 seconds, verify still exists
   - Expected: Container persists until explicit removal
   - Contract violation: Container removed within 60 seconds

2. **volume-mount-verification-contract.json**
   - Purpose: Verify volume mounts are applied and accessible
   - Test: Create container with volume, exec into container, read mounted file
   - Expected: File from host is readable at container path
   - Contract violation: Volume not mounted or file not accessible

3. **container-persistence-contract.json**
   - Purpose: Long-running containers for benchmark infrastructure
   - Test: Create container, run 24 operations over 30 minutes, verify container exists
   - Expected: Container available for full duration
   - Contract violation: Container disappears before explicit cleanup

### Quickstart (quickstart.md)

**Manual Test Scenarios**:

1. Create container with workspace volume mount
2. Verify container persists for 5 minutes
3. Verify workspace files accessible from container
4. Verify SimpleTestRunner class can be loaded
5. Clean up container explicitly

**Expected Outcomes**:
- Container creation: <60 seconds
- Volume mount verification: <5 seconds
- Container remains available for benchmark duration
- No "Failed to create container: 0" errors

### Agent Context Update

Run agent context update script (executed in Phase 1 implementation below).

**Output**: data-model.md, contracts/*.json, quickstart.md, CLAUDE.md updated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Load base template**: `.specify/templates/tasks-template.md`

2. **Generate contract test tasks** (Phase 3.2: Tests First):
   - T001 [P]: Write unit tests for volume path validation (ContainerConfig)
   - T002 [P]: Write unit tests for volume mount parsing (IRISContainerManager)
   - T003 [P]: Write unit tests for persistence verification
   - T004: Write integration test for ryuk lifecycle (real container)
   - T005: Write integration test for volume mounting (real Docker volumes)
   - T006: Write integration test for 30-minute persistence

3. **Generate implementation tasks** (Phase 3.3: Core Implementation):
   - T007: Research testcontainers ryuk behavior
   - T008 [P]: Add volume path validation to ContainerConfig
   - T009: Fix volume mounting in IRISContainerManager.create_from_config()
   - T010: Add container persistence verification after creation
   - T011: Implement ryuk prevention for CLI-managed containers
   - T012: Enhance error messages to distinguish failure types

4. **Generate documentation tasks** (Phase 3.4: Documentation):
   - T013 [P]: Create docs/learnings/testcontainers-ryuk-lifecycle.md
   - T014 [P]: Update CHANGELOG.md with v1.2.2 notes
   - T015 [P]: Update CLI command help text

5. **Generate validation tasks** (Phase 3.5: Validation):
   - T016: Run all 35 contract tests (regression check)
   - T017: Run new unit tests (verify fixes)
   - T018: Run integration tests with real containers
   - T019: Run benchmark infrastructure end-to-end

**Ordering Strategy**:
- TDD order: Tests T001-T006 before implementation T007-T012
- Research T007 before implementation (understand ryuk first)
- Parallel tasks [P]: Different files, no dependencies
- Sequential tasks: Same file modifications
- Validation at end: T016-T019 after all implementation

**Dependencies**:
```
Setup: None (bug fixes in existing code)

Tests First (T001-T006):
  T001, T002, T003 → Parallel (different test files)
  T004, T005, T006 → Sequential (integration tests, share Docker)

Implementation (T007-T012):
  T007 → Research (must complete first)
  T008 → After T001 (parallel with T009-T011)
  T009 → After T002, T007 (depends on ryuk research)
  T010 → After T003 (parallel with T008)
  T011 → After T007, T009 (ryuk + volume mounting)
  T012 → After T008-T011 (error messages last)

Documentation (T013-T015):
  All parallel (different files)

Validation (T016-T019):
  T016 → After all implementation (regression)
  T017 → After T016 (new unit tests)
  T018 → After T017 (integration tests)
  T019 → After T018 (full benchmark)
```

**Estimated Output**: 19 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, verify 22/24 benchmark pass rate)

## Complexity Tracking
*No constitutional violations detected*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---
*Based on IRIS DevTools Constitution v1.0.0 - See `CONSTITUTION.md`*
