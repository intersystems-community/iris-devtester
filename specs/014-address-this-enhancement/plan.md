
# Implementation Plan: Defensive Container Validation

**Branch**: `014-address-this-enhancement` | **Date**: 2025-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-address-this-enhancement/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code, or `AGENTS.md` for all other agents).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Enhance IRISContainer class with defensive container validation to detect and provide clear guidance for Docker container ID caching issues. When containers are recreated with new IDs, the system will automatically detect stale references and provide actionable remediation steps instead of cryptic error messages.

## Technical Context
**Language/Version**: Python 3.9+ (to match iris-devtester requirements)
**Primary Dependencies**: docker>=6.0.0, testcontainers>=4.0.0, testcontainers-iris>=1.2.2
**Storage**: N/A (container metadata only)
**Testing**: pytest (unit, contract, integration tests)
**Target Platform**: Linux, macOS, Windows (Docker-compatible platforms)
**Project Type**: Single library package
**Performance Goals**: <2 seconds for container validation checks
**Constraints**: Must work with existing IRISContainer API, backward compatible
**Scale/Scope**: Python API additions to IRISContainer class

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle #1: AUTOMATIC REMEDIATION OVER MANUAL INTERVENTION
**Status**: ✅ COMPLIANT
- Validation detects stale container references automatically
- Error messages include specific remediation commands
- Users don't need to manually inspect Docker daemon state

### Principle #5: FAIL FAST WITH GUIDANCE
**Status**: ✅ COMPLIANT
- Container validation runs before operations
- Structured error messages with "What went wrong" and "How to fix it"
- Lists available containers when specified container not found
- Clear distinction between "not found" and "not accessible"

### Principle #7: MEDICAL-GRADE RELIABILITY
**Status**: ✅ COMPLIANT
- Comprehensive validation (existence + accessibility)
- Non-destructive read-only checks
- Idempotent validation (safe to retry)
- Logging for diagnostics
- Health check endpoint for proactive monitoring

**Overall**: ✅ NO VIOLATIONS - Feature aligns with constitutional principles

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
iris_devtester/
├── containers/
│   ├── iris_container.py         # Enhanced with validation methods
│   ├── validation.py              # NEW: ContainerValidator class
│   └── models.py                  # NEW: ContainerHealth, ValidationResult dataclasses
├── utils/
│   └── container_status.py        # Existing - will integrate with new validation
└── __init__.py

tests/
├── contract/
│   └── test_container_validation_api.py  # NEW: API contract tests
├── integration/
│   └── test_container_validation.py      # NEW: Integration tests with real containers
└── unit/
    └── test_validation_models.py         # NEW: Unit tests for dataclasses
```

**Structure Decision**: Single project structure. Feature adds new validation module to existing `iris_devtester/containers/` package, integrating with existing IRISContainer class. Existing `container_status.py` utility will be enhanced to use the new validation infrastructure.

## Phase 0: Outline & Research

**Status**: ✅ COMPLETE

**Research Questions Addressed**:
1. Docker SDK container validation best practices
2. Container health check patterns (progressive validation)
3. Error message formatting for medical-grade reliability
4. Stale container ID detection strategies

**Key Decisions**:
- Use Docker SDK (not subprocess) for container inspection
- Progressive validation strategy (fast → slow checks)
- Dataclasses for results (not dicts) for type safety
- Integration with existing `container_status.py` utility

**Output**: ✅ `research.md` complete (all NEEDS CLARIFICATION resolved)

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETE

**Entities Defined** (in `data-model.md`):
1. `ContainerHealthStatus` - Enum of container health states
2. `ValidationResult` - Validation outcome with remediation steps
3. `ContainerHealth` - Detailed health metadata
4. `HealthCheckLevel` - Validation depth enum

**API Contracts** (in `contracts/container-validation-api.md`):
1. `validate_container()` - Standalone validation function
2. `ContainerValidator` - Stateful validator with caching
3. `IRISContainer.validate()` - Integration with IRISContainer
4. `IRISContainer.assert_healthy()` - Assertion-style validation

**Test Scenarios** (in `quickstart.md`):
1. Detecting recreated containers (stale ID)
2. Proactive health checks before tests
3. Listing available containers
4. Fast validation for CI/CD
5. Cached validation for repeated checks
6. Assertion-style validation
7. Handling Docker daemon down
8. Production-ready retry logic

**Output**: ✅ All artifacts complete
- ✅ `data-model.md` (3 dataclasses + 2 enums)
- ✅ `contracts/container-validation-api.md` (4 public APIs)
- ✅ `quickstart.md` (8 usage scenarios)

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Data Model Tasks** (from `data-model.md`):
   - T001: Create `ContainerHealthStatus` enum [P]
   - T002: Create `HealthCheckLevel` enum [P]
   - T003: Create `ValidationResult` dataclass with factory methods [P]
   - T004: Create `ContainerHealth` dataclass [P]
   - T005: Unit tests for data models [depends: T001-T004]

2. **Validation Core Tasks** (from `contracts/container-validation-api.md`):
   - T006: Create `validation.py` module skeleton
   - T007: Implement `validate_container()` function [depends: T003]
   - T008: Implement `ContainerValidator` class [depends: T003]
   - T009: Contract tests for `validate_container()` [depends: T007]
   - T010: Contract tests for `ContainerValidator` [depends: T008]

3. **IRISContainer Integration Tasks**:
   - T011: Add `validate()` method to IRISContainer [depends: T007]
   - T012: Add `assert_healthy()` method to IRISContainer [depends: T011]
   - T013: Contract tests for IRISContainer validation methods [depends: T011, T012]

4. **Error Message Tasks** (Constitutional Principle #5):
   - T014: Implement `ValidationResult.format_message()` [depends: T003]
   - T015: Unit tests for error message formatting [depends: T014]

5. **Integration Tasks**:
   - T016: Enhance `container_status.py` to use new validation [depends: T007]
   - T017: Integration tests with real containers [depends: T007, T008]

6. **Performance Tasks** (<2s SLA):
   - T018: Add timeout handling to validation checks [depends: T007]
   - T019: Implement caching in ContainerValidator [depends: T008]
   - T020: Performance tests (validate SLA) [depends: T018, T019]

7. **Documentation Tasks**:
   - T021: Update CLAUDE.md with validation context
   - T022: Add docstrings to all public APIs [depends: T007, T008, T011, T012]

**Ordering Strategy**:
- TDD order: Contract tests before implementation (T009 before T007, etc.)
- Dependency order: Data models → Core validation → Integration
- Mark [P] for parallel execution (T001-T004 can run in parallel)

**Estimated Output**: ~22 numbered, dependency-ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

**Status**: ✅ NO VIOLATIONS

No constitutional violations detected. Feature aligns with all applicable principles:
- Principle #1: Automatic remediation ✅
- Principle #5: Fail fast with guidance ✅
- Principle #7: Medical-grade reliability ✅

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✅
- [x] Phase 1: Design complete (/plan command) ✅
- [x] Phase 2: Task planning complete (/plan command - describe approach only) ✅
- [ ] Phase 3: Tasks generated (/tasks command) - NEXT STEP
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅
- [x] All NEEDS CLARIFICATION resolved ✅ (scope=Python API, performance=<2s)
- [x] Complexity deviations documented ✅ (none - no violations)

**Artifacts Created**:
- ✅ `plan.md` - This file (complete)
- ✅ `research.md` - Phase 0 research (complete)
- ✅ `data-model.md` - Data models and entities (complete)
- ✅ `contracts/container-validation-api.md` - API contracts (complete)
- ✅ `quickstart.md` - Usage scenarios (complete)

**Ready for /tasks command**: ✅ YES

---
*Based on CONSTITUTION.md - See `/Users/tdyar/ws/iris-devtester/CONSTITUTION.md`*
