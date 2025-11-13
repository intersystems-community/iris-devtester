# Implementation Plan: Fix Critical Container Creation Bugs

**Branch**: `010-fix-critical-bugs` | **Date**: 2025-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-fix-critical-bugs/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path ✓
2. Fill Technical Context ✓
3. Fill Constitution Check section ✓
4. Evaluate Constitution Check → No violations ✓
5. Execute Phase 0 → research.md ✓
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md ✓
7. Re-evaluate Constitution Check ✓ PASS
8. Plan Phase 2 → Task generation approach ✓
9. STOP - Ready for /tasks command ✓
```

## Summary

Fix three critical bugs in iris-devtester container creation:
1. **Image name bug**: Use `intersystemsdc/iris-community` (not `intersystems/iris-community`)
2. **Silent failure bug**: Replace "Failed to create container: 0" with constitutional error messages
3. **Volume mounting bug**: Apply volume mounts from ContainerConfig to actual containers

**Technical Approach**:
- Fix `ContainerConfig.get_image_name()` method to use correct image names
- Enhance error handling in `iris_container_adapter.py` to catch and translate specific Docker errors
- Add volume mounting support to `IRISContainerManager.create_from_config()`
- Add integration tests to verify all three fixes

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- testcontainers-iris >= 1.2.2
- docker-py >= 7.0.0
- pydantic >= 2.0.0
- click >= 8.0.0

**Storage**: N/A (container configuration only)
**Testing**: pytest with testcontainers for integration tests
**Target Platform**: Linux/macOS/Windows with Docker Desktop
**Project Type**: Single Python package (iris-devtester)
**Performance Goals**: Container creation <30 seconds, error detection immediate
**Constraints**:
- Must maintain backwards compatibility with existing config files
- Must not break 35 existing contract tests
- Error messages must follow constitutional 4-part format
**Scale/Scope**: Bug fixes affecting 3 files (container_config.py, iris_container_adapter.py, container.py), ~100 lines changed

## Constitution Check

### Principle 1: Automatic Remediation Over Manual Intervention
- **Status**: ✅ PASS - Bug Fix 2 improves automatic error handling
- **Analysis**: Enhanced error messages provide clear remediation steps, moving toward auto-remediation

### Principle 2: Choose the Right Tool for the Job
- **Status**: ✅ PASS - Already using testcontainers-iris for container management
- **Analysis**: No new tools introduced, fixes improve existing tool usage

### Principle 3: Isolation by Default
- **Status**: ✅ PASS - No impact on test isolation
- **Analysis**: Bug fixes don't affect test isolation patterns

### Principle 4: Zero Configuration Viable
- **Status**: ✅ PASS - Fixes improve zero-config experience
- **Analysis**: Bug Fix 1 enables default config to work (was failing with wrong image name)

### Principle 5: Fail Fast with Guidance
- **Status**: ✅ ENHANCED - Bug Fix 2 directly implements this principle
- **Analysis**: Constitutional error messages replace silent failures

### Principle 6: Enterprise Ready, Community Friendly
- **Status**: ✅ PASS - Bug Fix 1 ensures Community edition works correctly
- **Analysis**: Separate image names for Community (`intersystemsdc/iris-community`) vs Enterprise (`intersystems/iris`)

### Principle 7: Medical-Grade Reliability
- **Status**: ✅ ENHANCED - Bug fixes improve reliability
- **Analysis**: Integration tests verify fixes, error handling prevents silent failures

### Principle 8: Document the Blind Alleys
- **Status**: ✅ PASS - Will document why `intersystems/iris-community` doesn't work
- **Analysis**: Add to learnings why Docker Hub uses `intersystemsdc/` prefix for Community images

**Gate Result**: ✅ PASS - No constitutional violations, fixes enhance constitutional compliance

## Project Structure

### Documentation (this feature)
```
specs/010-fix-critical-bugs/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (IN PROGRESS)
├── research.md          # Phase 0 output (NEXT)
├── data-model.md        # Phase 1 output (minimal - config changes only)
├── quickstart.md        # Phase 1 output (verification steps)
└── contracts/           # Phase 1 output (test contracts)
    ├── image-name-contract.json
    ├── error-handling-contract.json
    └── volume-mount-contract.json
```

### Source Code (repository root)
```
iris_devtester/
├── config/
│   └── container_config.py        # [FIX] get_image_name() method (line 266)
├── utils/
│   └── iris_container_adapter.py  # [FIX] Add volume mounting, enhance error translation
├── cli/
│   └── container.py                # [UPDATE] Error handling for silent failures
└── ...

tests/
├── integration/
│   └── test_bug_fixes.py          # [NEW] Integration tests for all 3 bugs
└── unit/
    └── utils/
        └── test_iris_container_adapter.py  # [UPDATE] Unit tests for volume mounting
```

**Structure Decision**: Single Python package structure maintained. Bug fixes affect existing modules, no new architectural components needed.

## Phase 0: Outline & Research

### Research Topics

1. **Docker Hub Image Names**
   - Task: Verify correct image names for IRIS Community and Enterprise editions
   - Why: Bug Fix 1 requires understanding Docker Hub naming conventions
   - Expected finding: Community images use `intersystemsdc/` prefix, Enterprise use `intersystems/`

2. **testcontainers-iris Volume Mounting API**
   - Task: Research how to mount volumes using testcontainers-iris library
   - Why: Bug Fix 3 requires adding volume mounting support
   - Expected finding: IRISContainer has `with_volume_mapping()` or similar method

3. **Docker Error Types and Detection**
   - Task: Identify common Docker errors and their exception types
   - Why: Bug Fix 2 requires distinguishing error types for better messages
   - Expected finding: ImageNotFound, PortConflict, PermissionDenied exceptions

4. **Error Message Best Practices**
   - Task: Review constitutional error message format requirements
   - Why: Ensure Bug Fix 2 follows established patterns
   - Expected finding: 4-part format (What/Why/How/Docs)

5. **Backwards Compatibility Concerns**
   - Task: Identify any risks of breaking existing configs or tests
   - Why: NFR-001 requires backwards compatibility
   - Expected finding: Image name change is transparent, volume mounting is additive

### Research Execution

*Delegating to research.md generation...*

**Output**: [research.md](./research.md) (to be generated)

## Phase 1: Design & Contracts

### Data Model Changes

**Modified Entity**: ContainerConfig (iris_devtester/config/container_config.py)

Changes:
- `get_image_name()` method logic updated
- No new fields added (volumes field already exists)
- Validation rules unchanged

See [data-model.md](./data-model.md) for details (to be generated)

### API Contracts

**Contract 1**: Image Name Correction (FR-001, FR-002, FR-003)
- Input: ContainerConfig with `edition="community"` and `image_tag="latest"`
- Expected: `get_image_name()` returns `"intersystemsdc/iris-community:latest"`
- File: `contracts/image-name-contract.json`

**Contract 2**: Error Message Format (FR-005, FR-006, FR-007)
- Input: Docker exception (ImageNotFound, PortConflict, etc.)
- Expected: Translated exception with 4-part message (What/Why/How/Docs)
- File: `contracts/error-handling-contract.json`

**Contract 3**: Volume Mounting (FR-010, FR-011, FR-012, FR-014)
- Input: ContainerConfig with `volumes=["./data:/external"]`
- Expected: Container has volume mount visible via `docker inspect`
- File: `contracts/volume-mount-contract.json`

### Contract Tests

Tests to be generated in Phase 1:
1. `test_image_name_community()` - Verify Community edition uses `intersystemsdc/`
2. `test_image_name_enterprise()` - Verify Enterprise edition uses `intersystems/`
3. `test_image_name_with_tag()` - Verify tag appending works correctly
4. `test_error_translation_image_not_found()` - Verify ImageNotFound error translation
5. `test_error_translation_port_conflict()` - Verify port conflict error translation
6. `test_volume_mounting_single()` - Verify single volume mount
7. `test_volume_mounting_multiple()` - Verify multiple volume mounts
8. `test_volume_mounting_validation()` - Verify invalid path detection

All tests should FAIL initially (no implementation yet).

### Integration Test Scenarios

From spec acceptance scenarios:

**Scenario 1**: Image name verification
```python
def test_community_edition_uses_correct_image():
    """Verify Community edition containers use intersystemsdc/iris-community"""
    config = ContainerConfig(edition="community", image_tag="latest")
    iris = IRISContainerManager.create_from_config(config)
    iris.start()
    container = iris.get_wrapped_container()
    image = container.attrs['Config']['Image']
    assert image == "intersystemsdc/iris-community:latest"
```

**Scenario 2**: Error message quality
```python
def test_port_conflict_shows_clear_error():
    """Verify port conflict shows constitutional error message"""
    # Start container on port 1972
    iris1 = IRISContainer(port=1972).start()

    # Try to start another on same port
    with pytest.raises(ValueError) as exc_info:
        iris2 = IRISContainer(port=1972).start()

    error_msg = str(exc_info.value)
    assert "Port 1972 is already in use" in error_msg
    assert "How to fix it:" in error_msg
    assert "What went wrong:" in error_msg
```

**Scenario 3**: Volume mounting
```python
def test_volume_mounts_are_applied():
    """Verify volumes from config are mounted in container"""
    config = ContainerConfig(
        volumes=["./test-data:/external"]
    )
    iris = IRISContainerManager.create_from_config(config)
    iris.start()
    container = iris.get_wrapped_container()
    mounts = container.attrs['Mounts']

    # Verify mount exists
    external_mount = next(m for m in mounts if m['Destination'] == '/external')
    assert external_mount is not None
```

### Quickstart Validation

See [quickstart.md](./quickstart.md) for step-by-step verification (to be generated)

### Agent Context Update

Will execute: `.specify/scripts/bash/update-agent-context.sh claude`

**Output**: Updated CLAUDE.md in repository root with Bug Fix 010 context

## Phase 2: Task Planning Approach

**Task Generation Strategy**:

This phase will be executed by the `/tasks` command, which will generate tasks.md based on:

1. **Test Tasks** (TDD order - write tests first):
   - T001: Write unit tests for `ContainerConfig.get_image_name()` fix [P]
   - T002: Write unit tests for error translation in `translate_docker_error()` [P]
   - T003: Write unit tests for volume mounting in `IRISContainerManager` [P]
   - T004: Write integration test for Community edition image name verification
   - T005: Write integration test for Enterprise edition image name verification
   - T006: Write integration test for constitutional error messages
   - T007: Write integration test for volume mounting

2. **Implementation Tasks** (make tests pass):
   - T008: Fix `ContainerConfig.get_image_name()` to use correct Docker Hub image names [P]
   - T009: Enhance `translate_docker_error()` to handle ImageNotFound, PortConflict
   - T010: Add volume mounting support to `IRISContainerManager.create_from_config()`
   - T011: Update error handling in CLI `container up` command
   - T012: Update error handling in CLI `container start` command

3. **Documentation Tasks**:
   - T013: Add learnings doc explaining Docker Hub image naming conventions [P]
   - T014: Update CHANGELOG.md with bug fix notes [P]
   - T015: Update README.md with corrected image names if mentioned [P]

4. **Validation Tasks**:
   - T016: Run all 35 existing contract tests (ensure no breakage)
   - T017: Run new integration tests (verify all 3 bugs fixed)
   - T018: Manual smoke test: `iris-devtester container up`

**Ordering Strategy**:
- Tests before implementation (TDD)
- Unit tests can run in parallel [P]
- Integration tests depend on implementation
- Documentation can be updated in parallel [P]
- Validation runs last

**Estimated Output**: ~18 numbered tasks in tasks.md

**Dependency Relationships**:
- T008 depends on T001 (tests must exist first)
- T009 depends on T002
- T010 depends on T003
- T011-T012 depend on T008-T010
- T016-T018 depend on all implementation tasks

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, verify success criteria)

## Complexity Tracking

*No constitutional violations - table not needed*

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research planning complete
- [x] Phase 0: Research document generated (research.md)
- [x] Phase 1: Design complete (/plan command)
  - [x] data-model.md generated
  - [x] contracts/ directory created with 3 contracts
  - [x] quickstart.md generated
  - [x] CLAUDE.md updated
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command) - tasks.md with 18 tasks
- [ ] Phase 4: Implementation complete - NEXT STEP: /implement
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (none identified)
- [x] Complexity deviations documented (none needed)

---
*Based on Constitution v1.0.0 - See `/CONSTITUTION.md`*
