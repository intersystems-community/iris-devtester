
# Implementation Plan: Multi-Project Port Isolation

**Branch**: `013-add-semantics-to` | **Date**: 2025-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/tdyar/ws/iris-devtester/specs/013-add-semantics-to/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path → ✅ COMPLETE
2. Fill Technical Context → ✅ COMPLETE
3. Fill Constitution Check → ✅ COMPLETE
4. Evaluate Constitution Check → ✅ PASS (no violations)
5. Execute Phase 0 → research.md → IN PROGRESS
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
7. Re-evaluate Constitution Check
8. Plan Phase 2 → Describe task generation approach
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 9. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

Enable multiple projects to use iris-devtester simultaneously without port conflicts. The system will automatically assign unique IRIS superserver ports (1972-1981) to each project based on the project's absolute directory path, persist assignments across container restarts, and support manual port overrides when needed. Implementation uses a user-specific port registry (JSON file in `~/.iris-devtester/`) with atomic file locking for race-condition safety.

**Technical Approach**: Extend `testcontainers-iris` with a `PortRegistry` class that manages port assignments using file-based locking and Docker container inspection for staleness detection. Integrate seamlessly into existing `IRISContainer` initialization without breaking changes.

## Technical Context

**Language/Version**: Python 3.9+ (per pyproject.toml:10)
**Primary Dependencies**:
- testcontainers>=4.0.0 (container management)
- testcontainers-iris>=1.2.2 (IRIS container support)
- docker>=6.0.0 (Docker SDK for container inspection)
- filelock>=3.0.0 (NEW - atomic file operations)

**Storage**: JSON file-based port registry (`~/.iris-devtester/port-registry.json`)
**Testing**: pytest>=8.0.0 with contract tests, integration tests, unit tests
**Target Platform**: Linux, macOS, Windows (cross-platform requirement from NFR-006)

**Project Type**: Single Python package (iris_devtester)

**Performance Goals**: Port assignment <5 seconds (NFR-001)

**Constraints**:
- Atomic port assignment (NFR-003 - prevent race conditions)
- 95%+ port conflict detection accuracy (NFR-004)
- Zero configuration viable (Constitutional Principle #4)
- No breaking changes to existing API (FR-012)

**Scale/Scope**:
- Support 10 concurrent IRIS containers (FR-004)
- Ports 1972-1981 (10-port range)
- Single user per machine (multi-user out of scope for v1)

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: AUTOMATIC REMEDIATION OVER MANUAL INTERVENTION
✅ **PASS**: Port assignment is automatic by default. When port exhaustion occurs, system fails fast with guidance (FR-017, FR-018) including remediation steps (stop containers, use manual override).

### Principle 2: CHOOSE THE RIGHT TOOL FOR THE JOB
✅ **PASS**:
- Docker SDK for container inspection (stale detection)
- JSON for registry storage (simple, no SQL needed)
- File locking for atomic operations (appropriate for local registry)
- No SQL vs ObjectScript considerations (this is Python infrastructure, not IRIS operations)

### Principle 3: ISOLATION BY DEFAULT
✅ **PASS**: Each project gets isolated port assignment based on unique directory path. No shared state between projects except registry file (which is designed for concurrent access via file locking).

### Principle 4: ZERO CONFIGURATION VIABLE
✅ **PASS**: Auto-assignment by default (FR-011). Registry created automatically in `~/.iris-devtester/` on first use. Manual configuration optional via environment variables or constructor parameters.

### Principle 5: FAIL FAST WITH GUIDANCE
✅ **PASS**: Port exhaustion fails with clear error message including:
- Current port assignments (which ports in use)
- Which ports are available
- Remediation steps (stop containers or manual override)
(FR-017, FR-018)

### Principle 6: ENTERPRISE READY, COMMUNITY FRIENDLY
✅ **PASS**: Works with both Community and Enterprise IRIS editions (NFR-005). No edition-specific logic in port management.

### Principle 7: MEDICAL-GRADE RELIABILITY
✅ **PASS**:
- 95%+ test coverage required
- Atomic operations via file locking (NFR-003)
- 95%+ port conflict detection (NFR-004)
- Stale assignment cleanup (FR-015)
- Idempotent port assignment

### Principle 8: DOCUMENT THE BLIND ALLEYS
✅ **PASS**: Will document in research.md:
- Why not database-backed registry? (adds complexity, filesystem sufficient for local dev)
- Why not system-wide registry? (out of scope for v1, deferred to multi-user feature)
- Why file locking vs. process locking? (cross-platform, survives process crashes)

**Initial Constitution Check**: ✅ PASS (no violations, no complexity tracking needed)

## Project Structure

### Documentation (this feature)
```
specs/013-add-semantics-to/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── port-registry-api.md
│   └── container-integration-api.md
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
iris_devtester/
├── ports/                       # NEW MODULE
│   ├── __init__.py             # Exports PortRegistry, PortAssignment
│   ├── registry.py             # PortRegistry class (JSON file management)
│   ├── assignment.py           # PortAssignment dataclass
│   └── exceptions.py           # PortExhaustedError, PortConflictError
├── containers/
│   └── iris_container.py       # MODIFIED: Integrate port registry
├── cli/
│   └── ports.py                # NEW: CLI commands (list, clear, inspect)
└── utils/
    └── file_lock.py            # NEW: Cross-platform file locking utility

tests/
├── contract/
│   ├── test_port_registry_contract.py    # Port registry API contract tests
│   └── test_container_integration_contract.py  # Container integration tests
├── integration/
│   ├── test_multi_project_isolation.py   # End-to-end multi-project scenarios
│   ├── test_port_persistence.py          # Port persistence across restarts
│   └── test_port_exhaustion.py           # Port exhaustion handling
└── unit/
    ├── test_port_registry.py             # PortRegistry unit tests
    ├── test_port_assignment.py           # PortAssignment unit tests
    └── test_file_lock.py                 # File locking utility tests
```

**Structure Decision**: Single Python package (Option 1) with new `ports/` module. This is infrastructure code that extends the existing `iris_devtester` package, not a web/mobile application. The port registry integrates into the existing `containers/` module via composition (dependency injection of PortRegistry into IRISContainer).

## Phase 0: Outline & Research

### Research Topics

No NEEDS CLARIFICATION markers remain in Technical Context (all resolved during /clarify workflow). Research focuses on best practices and implementation patterns:

1. **File Locking Mechanisms (Cross-Platform)**
   - Research: Python's `filelock` library for atomic file operations
   - Rationale: Prevents race conditions when multiple processes start containers simultaneously
   - Platform support: Linux, macOS, Windows

2. **Docker Container Inspection Patterns**
   - Research: Docker SDK `containers.list()` for staleness detection
   - Rationale: Identify crashed containers to release stale port assignments
   - Pattern: Poll container status, mark assignments as stale if container not found

3. **JSON Registry Design**
   - Research: Structure for port-project mappings with metadata
   - Rationale: Simple, human-readable, no database dependency
   - Schema: `{ "assignments": [ { "project_path": "...", "port": 1972, ... } ] }`

4. **Backwards Compatibility Strategy**
   - Research: How to integrate port registry without breaking existing IRISContainer users
   - Rationale: FR-012 requires no breaking changes
   - Pattern: Optional dependency injection, fallback to default port 1972 if registry disabled

### Research Agent Dispatches

```
Task 1: "Research Python filelock library for atomic file operations in multi-process environment"
  → Focus: Platform compatibility (Linux/Mac/Windows), performance, error handling

Task 2: "Find best practices for Docker SDK container inspection and staleness detection"
  → Focus: Efficient polling, handling edge cases (ryuk cleanup, manual removal)

Task 3: "Research JSON schema design for port registry with extensibility for future features"
  → Focus: Schema versioning, migration strategy, backwards compatibility

Task 4: "Investigate testcontainers patterns for dependency injection and configuration"
  → Focus: Constructor patterns, environment variable integration, testcontainers best practices
```

**Output**: research.md with decisions, rationale, and alternatives considered

## Phase 1: Design & Contracts

*Prerequisites: research.md complete*

### 1. Data Model (data-model.md)

Entities extracted from spec.md (lines 159-172):

**PortAssignment**:
- Fields: project_path (str), port (int), assigned_at (datetime), assignment_type (auto|manual), status (active|released|stale)
- Validation: port in range 1972-1981 (or user-specified), project_path is absolute path
- State transitions: active → (container stops) → released, active → (container crashes) → stale

**PortRegistry**:
- Fields: registry_file_path (str), assignments (List[PortAssignment])
- Operations: assign_port(), release_port(), cleanup_stale(), get_assignment(), list_all()
- Concurrency: File locking for atomic read-modify-write

**Project** (conceptual, not stored):
- Identifier: Absolute directory path (e.g., `/Users/dev/project-a`)
- Derived from: `os.getcwd()` or explicit parameter

### 2. API Contracts (contracts/)

**Port Registry API** (`ports/registry.py`):
```python
class PortRegistry:
    def assign_port(self, project_path: str, preferred_port: Optional[int] = None) -> PortAssignment
    def release_port(self, project_path: str) -> None
    def cleanup_stale(self) -> List[PortAssignment]  # Returns released assignments
    def get_assignment(self, project_path: str) -> Optional[PortAssignment]
    def list_all() -> List[PortAssignment]
    def clear_all() -> None  # For testing/debugging
```

**Container Integration API** (`containers/iris_container.py`):
```python
class IRISContainer:
    def __init__(
        self,
        ...,  # existing parameters
        port_registry: Optional[PortRegistry] = None,  # NEW
        project_path: Optional[str] = None,  # NEW (auto-detected from cwd)
        preferred_port: Optional[int] = None,  # NEW (manual override)
    ):
        # If port_registry provided: use it for port assignment
        # Else: fallback to default port 1972 (backwards compatible)
```

### 3. Contract Tests

**`tests/contract/test_port_registry_contract.py`**:
- Test: assign_port() returns port in range 1972-1981
- Test: assign_port() with preferred_port validates availability
- Test: release_port() removes assignment from registry
- Test: cleanup_stale() detects crashed containers
- Test: get_assignment() returns None if no assignment exists
- Test: Concurrent assign_port() from 2 projects returns different ports

**`tests/contract/test_container_integration_contract.py`**:
- Test: IRISContainer with port_registry auto-assigns port
- Test: IRISContainer without port_registry uses default port 1972
- Test: IRISContainer with preferred_port uses that port
- Test: Port assignment persists in registry after container stop

### 4. Test Scenarios (from User Stories)

**Quickstart Scenario** (quickstart.md):
```python
# Scenario: Two projects running simultaneously
# Given: Project A in /Users/dev/project-a
#        Project B in /Users/dev/project-b
# When: Start IRIS containers for both projects
# Then: Project A gets port 1972, Project B gets port 1973
# Verify: Both containers accessible, no port conflicts
```

**Integration Test Scenarios** (tests/integration/):
1. test_multi_project_isolation.py: Acceptance scenario #1, #3
2. test_port_persistence.py: Acceptance scenario #2
3. test_port_exhaustion.py: Acceptance scenario #4, #5
4. test_edge_cases.py: Port conflict detection, stale assignments, manual overrides

### 5. Update CLAUDE.md

Run `.specify/scripts/bash/update-agent-context.sh claude` to update CLAUDE.md with:
- New `ports/` module context
- File locking patterns
- Docker SDK integration notes
- Port registry design decisions

**Output**: data-model.md, contracts/port-registry-api.md, contracts/container-integration-api.md, failing contract tests, quickstart.md, updated CLAUDE.md

## Phase 2: Task Planning Approach

*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. Load `.specify/templates/tasks-template.md` as base
2. Generate tasks from Phase 1 artifacts:
   - data-model.md → Entity creation tasks (PortAssignment, PortRegistry classes)
   - contracts/port-registry-api.md → Port registry implementation tasks
   - contracts/container-integration-api.md → IRISContainer integration tasks
   - quickstart.md → Integration test tasks
   - Constitutional requirements → CLI command tasks (list, clear, inspect ports)

**Task Categories**:
- **Contract Tests** (TDD - write first, expect failures):
  - Task: Write contract tests for PortRegistry API [P]
  - Task: Write contract tests for IRISContainer integration [P]

- **Data Models** (implement after contract tests exist):
  - Task: Implement PortAssignment dataclass [P]
  - Task: Implement PortRegistry class with file locking [depends on PortAssignment]

- **Infrastructure** (utilities needed by models):
  - Task: Implement cross-platform file locking utility [P]
  - Task: Implement Docker SDK container inspection [P]

- **Integration** (connect components):
  - Task: Integrate PortRegistry into IRISContainer [depends on PortRegistry]
  - Task: Add backwards compatibility fallback (default port 1972) [depends on integration]

- **CLI** (user-facing commands):
  - Task: Implement `iris-devtester ports list` command [P]
  - Task: Implement `iris-devtester ports clear` command [P]
  - Task: Implement `iris-devtester ports inspect <project-path>` command [P]

- **Integration Tests** (validate end-to-end scenarios):
  - Task: Write multi-project isolation integration tests
  - Task: Write port persistence integration tests
  - Task: Write port exhaustion handling integration tests
  - Task: Write edge case integration tests (stale detection, conflicts, manual overrides)

**Ordering Strategy**:
1. **Phase A - Infrastructure & Models** (parallel where marked [P]):
   - Contract tests first (TDD)
   - Data models next
   - Utilities in parallel

2. **Phase B - Integration**:
   - Connect PortRegistry to IRISContainer
   - Add backwards compatibility

3. **Phase C - User Interface**:
   - CLI commands (parallel)
   - Integration tests (validate complete feature)

**Estimated Output**: ~20-25 numbered, ordered tasks in tasks.md

**Dependencies**:
- Contract tests → Models (TDD workflow)
- Models → Integration (can't integrate until models exist)
- Integration → CLI (CLI uses integrated components)
- All → Integration tests (validate complete system)

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, validate NFR-001 <5s performance)

**Success Criteria**:
- All contract tests pass
- All integration tests pass
- Quickstart.md completes successfully with 2 concurrent projects
- Port assignment <5 seconds (NFR-001)
- 95%+ test coverage (Principle #7)
- No breaking changes to existing IRISContainer users (FR-012)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**No violations identified** - Constitution Check passed without requiring complexity justification.

## Progress Tracking

*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) - research.md generated
- [x] Phase 1: Design complete (/plan command) - data-model.md, contracts/, quickstart.md, CLAUDE.md updated
- [x] Phase 2: Task planning approach described (/plan command)
- [x] Phase 3: Tasks generated (/tasks command) - tasks.md with 40 numbered tasks
- [ ] Phase 4: Implementation complete - NEXT STEP
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (no violations)
- [x] Post-Design Constitution Check: PASS (re-validated after Phase 1)
- [x] All NEEDS CLARIFICATION resolved (via /clarify workflow)
- [x] Complexity deviations documented (N/A - no deviations)

**Next Step**: Begin implementation by executing tasks.md (Phase 4). Start with T001-T003 (setup), then T004-T017 (contract tests - TDD).

---
*Based on IRIS DevTools Constitution v1.0.0 - See `CONSTITUTION.md`*
