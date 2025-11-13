
# Implementation Plan: Container Lifecycle CLI Commands

**Branch**: `008-add-container-lifecycle` | **Date**: 2025-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/tdyar/ws/iris-devtester/specs/008-add-container-lifecycle/spec.md`

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

Add container lifecycle management CLI commands to iris-devtester, enabling zero-config container operations from command line. Current CLI only manages existing containers (status, test-connection, enable-callin, reset-password) but cannot start, stop, or create containers. This violates Constitutional Principle #4 "Zero Configuration Viable" - users must write Python code or use docker-compose for basic container operations.

**Primary Requirement**: CLI commands for complete container lifecycle - start, stop, restart, up, logs, remove.

**Technical Approach**: Extend iris_devtester.cli module with new container lifecycle commands using Click framework, wrapping existing IRISContainer Python API with zero-config YAML support.

## Technical Context
**Language/Version**: Python 3.9+ (matching existing pyproject.toml)
**Primary Dependencies**: Click 8.0+, testcontainers-iris 1.2.2+, python-dotenv 1.0+, PyYAML for config file support
**Storage**: YAML configuration files (iris-config.yml), Docker volumes for container persistence
**Testing**: pytest with integration tests using testcontainers
**Target Platform**: Linux, macOS, Windows (wherever Docker runs)
**Project Type**: Single project with CLI extension
**Performance Goals**: Container start <30s (IRIS startup time), logs streaming real-time
**Constraints**: Zero-config must work (no required config file), Constitutional error message format (What/Why/How/Docs)
**Scale/Scope**: Single container management per command (not orchestration), docker-compose style UX

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle #1: Automatic Remediation Over Manual Intervention
✅ **PASS** - Feature implements automatic remediation:
- Auto health check before reporting "started"
- Auto enable-callin service if DBAPI installed (FR-034)
- Auto port conflict detection (FR-028)
- Auto disk space detection (FR-029)
- No "run this command" errors - CLI does it

### Principle #2: Choose the Right Tool for the Job
✅ **PASS** - Not directly applicable (no IRIS queries), but:
- Uses Docker SDK (correct tool for container management)
- Wraps existing IRISContainer API (correct abstraction)

### Principle #3: Isolation by Default
✅ **PASS** - Not directly applicable (CLI doesn't manage test isolation)
- Container management respects existing isolation principles
- Each command operates on specified container only

### Principle #4: Zero Configuration Viable
✅ **PASS** - This IS the core requirement (FR-009):
- `iris-devtester container up` works with zero config
- Falls back to Community edition defaults
- Config file optional, not required

### Principle #5: Fail Fast with Guidance
✅ **PASS** - Required by FR-027:
- Constitutional error format (What/Why/How/Docs)
- Docker validation before commands (FR-025, FR-026)
- Pre-flight checks (port, disk, license)

### Principle #6: Enterprise Ready, Community Friendly
✅ **PASS** - Required by FR-012, FR-016:
- Config supports both editions
- Community edition as default
- Enterprise via license key in config

### Principle #7: Medical-Grade Reliability
✅ **PASS** - Required by implementation:
- Comprehensive integration tests
- Idempotent commands (FR-024)
- Health check validation
- 95%+ coverage target

### Principle #8: Document the Blind Alleys
⏳ **PENDING** - Will document during research:
- Config file format choices (YAML vs JSON vs TOML)
- Docker SDK vs subprocess patterns
- Health check strategies

**GATE STATUS**: ✅ PASS - No violations, proceed to Phase 0

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
├── cli/
│   ├── __init__.py
│   ├── main.py              # Existing CLI entry point
│   └── container.py         # NEW - Container lifecycle commands group
├── containers/              # Existing IRISContainer API
│   ├── __init__.py
│   └── iris_container.py
├── config/                  # Existing configuration
│   ├── __init__.py
│   └── discovery.py
└── utils/                   # Existing utilities
    ├── __init__.py
    └── password_reset.py

tests/
├── unit/
│   └── cli/
│       └── test_container_cli.py  # NEW - Unit tests for CLI commands
├── integration/
│   └── cli/
│       └── test_container_lifecycle_integration.py  # NEW - End-to-end CLI tests
└── contract/
    └── cli/
        └── test_container_cli_contract.py  # NEW - Contract tests for CLI

examples/
└── cli/
    ├── iris-config.yml      # NEW - Example configuration file
    └── container_workflow.sh  # NEW - Example CLI workflow
```

**Structure Decision**: Single project (Python package). This feature extends the existing CLI module with a new `container` command group. The IRISContainer Python API already exists - this feature wraps it with CLI commands and adds YAML configuration file support.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Configuration & Data Model Tasks** (from data-model.md):
   - Create ContainerConfig dataclass with Pydantic validation
   - Create ContainerState dataclass
   - Create YAML loader/parser for iris-config.yml
   - Create configuration hierarchy resolver (file → env → defaults)
   - Test: ContainerConfig validation (ports, license, namespace)
   - Test: YAML parsing (valid/invalid schemas)

2. **CLI Command Tasks** (from contracts/cli-commands.md):
   - For each command (up, start, stop, restart, status, logs, remove):
     - Contract test: CLI flags and arguments [P]
     - Contract test: Exit codes and error messages [P]
     - Contract test: Output format validation [P]
     - Implementation: Command handler function
     - Integration test: End-to-end workflow

3. **Core Utilities Tasks**:
   - Docker SDK wrapper functions (pull, create, start, stop, remove)
   - Health check implementation (multi-layer: container/health/port)
   - Constitutional error message formatters (6+ error scenarios)
   - Progress indicator utilities (spinner, success, error)
   - Idempotency logic (check-then-act pattern)

4. **Integration Tasks**:
   - Register container command group in main.py CLI
   - Add PyYAML dependency to pyproject.toml
   - Create example iris-config.yml files (community + enterprise)
   - Update CLI documentation

**Ordering Strategy**:
- **Phase 1 (Foundation)**: Data models + validation (tasks 1-6) [P]
- **Phase 2 (CLI Commands)**: Contract tests first, then implementations (tasks 7-27)
  - Contract tests can run in parallel [P]
  - Implementation follows TDD (red → green)
- **Phase 3 (Integration)**: Wire everything together (tasks 28-32)
- **Phase 4 (Documentation)**: Examples and docs (tasks 33-35)

**Dependencies**:
- ContainerConfig must exist before CLI commands
- Docker SDK wrappers before command implementations
- Contract tests before implementations (TDD)
- All CLI commands before main.py integration

**Parallelization Opportunities**:
- All contract test tasks can run in parallel [P]
- All data model validation tests in parallel [P]
- CLI command implementations independent (after contracts) [P]

**Estimated Output**: 35-40 numbered, ordered tasks in tasks.md

**Key TDD Checkpoints**:
1. After task 6: Data model tests passing
2. After task 13: Contract tests ALL FAILING (red phase)
3. After task 27: Contract tests ALL PASSING (green phase)
4. After task 32: Integration tests passing
5. After task 35: Full feature complete

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✓
  - Created research.md with 7 research decisions
  - All technical unknowns resolved
  - Blind alleys documented (docker-compose library)
- [x] Phase 1: Design complete (/plan command) ✓
  - Created data-model.md (2 entities: ContainerConfig, ContainerState)
  - Created contracts/cli-commands.md (7 CLI commands fully specified)
  - Created quickstart.md (5-minute getting started guide)
  - Updated CLAUDE.md with feature context
- [x] Phase 2: Task planning approach complete (/plan command - describe approach only) ✓
  - Described 4 task generation categories
  - Defined ordering strategy (Foundation → CLI → Integration → Docs)
  - Identified parallelization opportunities
  - Estimated 35-40 tasks
- [x] Phase 3: Tasks generated (/tasks command) ✓
  - Created tasks.md with 43 numbered tasks (T001-T043)
  - 8 task categories: Setup, Contract Tests, Data Models, Core Utilities, CLI Implementations, Integration Tests, Integration & Wiring, Polish
  - 28 parallelizable tasks marked [P]
  - TDD ordering enforced (tests before implementations)
  - Dependency graph and parallel execution examples included
- [ ] Phase 4: Implementation execution (/implement command or manual) - NEXT
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✓
  - All 8 principles evaluated
  - Zero violations found
  - Automatic remediation required (FR-027, FR-028, FR-029, FR-034)
- [x] Post-Design Constitution Check: PASS ✓
  - Re-evaluated after Phase 1 design
  - Zero violations found
  - Constitutional error message format enforced (FR-027)
- [x] All NEEDS CLARIFICATION resolved ✓
  - Technical Context had no NEEDS CLARIFICATION
  - Research resolved all technical unknowns
- [x] Complexity deviations documented: N/A
  - No complexity violations
  - No deviations from constitutional principles

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
