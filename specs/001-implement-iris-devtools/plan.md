# Implementation Plan: IRIS DevTools Package

**Branch**: `001-implement-iris-devtester` | **Date**: 2025-10-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-implement-iris-devtester/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path ✓
2. Fill Technical Context ✓
3. Fill Constitution Check ✓
4. Evaluate Constitution Check → PASS (extraction project, aligns with all principles)
5. Execute Phase 0 → research.md (in progress)
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
7. Re-evaluate Constitution Check
8. Plan Phase 2 → Describe task generation approach
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

IRIS DevTools is a battle-tested Python package extracting proven infrastructure from the rag-templates production codebase. It provides automatic, reliable connection management, test isolation, schema validation, and password remediation for InterSystems IRIS development. The primary requirement is to organize and enhance existing production code (~1000 lines) into a reusable PyPI package while maintaining 100% backwards compatibility and adding testcontainers integration.

**Primary Value**: Eliminates hundreds of developer hours wasted on infrastructure issues by codifying years of production debugging experience.

## Technical Context

**Language/Version**: Python 3.9+ (matches rag-templates production environment)
**Primary Dependencies**:
- `testcontainers>=4.0.0` - Container lifecycle management
- `testcontainers-iris-python>=1.2.2` - IRIS-specific container support
- `python-dotenv>=1.0.0` - Environment configuration
- `intersystems-irispython>=3.2.0` - DBAPI driver (optional, recommended)
- `jaydebeapi>=1.2.3` - JDBC fallback driver (optional)

**Storage**: InterSystems IRIS database (both Community and Enterprise editions)

**Testing**: pytest 8.0+ with:
- Unit tests (mocked dependencies)
- Integration tests (real IRIS containers via testcontainers)
- E2E tests (full workflow validation)
- Contract tests (API boundaries)

**Target Platform**:
- Linux (primary, CI/CD)
- macOS (developer workstations)
- Windows (secondary, best-effort)

**Project Type**: Single Python package (library + CLI utilities)

**Performance Goals**:
- Connection establishment: <500ms (DBAPI), <2s (JDBC)
- Password reset: <10s (automatic remediation)
- Test isolation overhead: <5s per test (namespace), <30s per test (container)
- Container startup: <30s (Community), <45s (Enterprise with license)

**Constraints**:
- Must maintain 95%+ test coverage (medical-grade reliability)
- Must support both DBAPI and JDBC connection types
- Must work with zero configuration (pip install && pytest)
- Must preserve rag-templates backwards compatibility
- Must support both Community and Enterprise IRIS editions

**Scale/Scope**:
- ~1000 lines of proven production code to extract
- 5 major modules (connections, containers, testing, config, utils)
- 38 functional requirements
- 7 key entities
- Target: <2000 lines total package code
- Target: ~1500 lines test code (95%+ coverage)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: Automatic Remediation Over Manual Intervention
- ✅ **PASS**: Password reset automation is core requirement (FR-004)
- ✅ **PASS**: Connection retry with backoff required (FR-026)
- ✅ **PASS**: Automatic schema reset on mismatch (FR-015)
- ✅ **PASS**: Container lifecycle automatic (FR-023)

### Principle 2: DBAPI First, JDBC Fallback
- ✅ **PASS**: Explicit requirement FR-001 (DBAPI first)
- ✅ **PASS**: Explicit requirement FR-002 (JDBC fallback)
- ✅ **PASS**: Connection type logging required (FR-027)

### Principle 3: Isolation by Default
- ✅ **PASS**: Isolated environments by default (FR-009)
- ✅ **PASS**: Namespace and container strategies (FR-010)
- ✅ **PASS**: Automatic cleanup even on failure (FR-013)
- ✅ **PASS**: Testcontainers integration required (FR-019)

### Principle 4: Zero Configuration Viable
- ✅ **PASS**: Core requirement FR-029 (zero-config must work)
- ✅ **PASS**: Auto-discovery from multiple sources (FR-006)
- ✅ **PASS**: Sensible defaults required (FR-007)
- ✅ **PASS**: pip install && pytest must work (acceptance scenario #1)

### Principle 5: Fail Fast with Guidance
- ✅ **PASS**: Actionable errors required (FR-024)
- ✅ **PASS**: Diagnosis + remediation + docs (FR-025)
- ✅ **PASS**: Distinguish error types (FR-028)

### Principle 6: Enterprise Ready, Community Friendly
- ✅ **PASS**: Support both editions (FR-022)
- ✅ **PASS**: Community default, Enterprise optional
- ✅ **PASS**: Auto-detection of edition features

### Principle 7: Medical-Grade Reliability
- ✅ **PASS**: 95%+ coverage required (FR-034)
- ✅ **PASS**: Comprehensive error handling (FR-024-028)
- ✅ **PASS**: Logging and diagnostics (FR-027, FR-032)
- ✅ **PASS**: Idempotent operations (test cleanup, schema reset)

### Principle 8: Document the Blind Alleys
- ✅ **PASS**: docs/learnings/ required (FR-037)
- ✅ **PASS**: Performance comparisons (DBAPI vs JDBC)
- ✅ **PASS**: "Why not X?" documentation required
- ✅ **PASS**: Extraction preserves production learnings

**Initial Constitution Check: PASS** ✓

All 8 principles are satisfied by the feature requirements. This is an extraction project that codifies existing constitutional compliance from rag-templates.

## Project Structure

### Documentation (this feature)
```
specs/001-implement-iris-devtester/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── connection-api.md
│   ├── testing-fixtures-api.md
│   └── container-api.md
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
iris-devtester/
├── iris_devtester/                    # Main package
│   ├── __init__.py                   # Package exports
│   ├── connections/                  # Connection management
│   │   ├── __init__.py
│   │   ├── manager.py                # IRISConnectionManager (DBAPI/JDBC)
│   │   ├── recovery.py               # Password reset handler
│   │   └── pooling.py                # Connection pool (optional)
│   ├── containers/                   # Container management
│   │   ├── __init__.py
│   │   ├── iris_container.py         # Enhanced IRISContainer
│   │   └── wait_strategies.py        # Custom wait strategies
│   ├── testing/                      # pytest utilities
│   │   ├── __init__.py
│   │   ├── fixtures.py               # pytest fixtures
│   │   ├── preflight.py              # Pre-flight checks
│   │   ├── schema_manager.py         # Schema validation/reset
│   │   ├── cleanup.py                # Test cleanup
│   │   ├── state.py                  # Test state tracking
│   │   └── models.py                 # Data models
│   ├── config/                       # Configuration
│   │   ├── __init__.py
│   │   ├── discovery.py              # Auto-discovery
│   │   └── defaults.py               # Default configs
│   └── utils/                        # Utilities
│       ├── __init__.py
│       ├── docker_helpers.py         # Docker utilities
│       └── diagnostics.py            # Diagnostic tools
│
├── tests/                            # Test suite
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/                         # Unit tests (mocked)
│   │   ├── test_connection_manager.py
│   │   ├── test_password_recovery.py
│   │   ├── test_config_discovery.py
│   │   └── test_schema_validator.py
│   ├── integration/                  # Integration tests (real IRIS)
│   │   ├── test_dbapi_connection.py
│   │   ├── test_jdbc_fallback.py
│   │   ├── test_container_lifecycle.py
│   │   └── test_schema_reset.py
│   └── e2e/                          # End-to-end tests
│       ├── test_zero_config_workflow.py
│       ├── test_password_remediation_workflow.py
│       └── test_parallel_test_isolation.py
│
├── docs/                             # Documentation
│   ├── getting-started.md
│   ├── api-reference.md
│   ├── migration-guide.md
│   ├── troubleshooting.md
│   └── learnings/                    # Blind alleys documentation
│       ├── why-dbapi-first.md
│       ├── why-testcontainers.md
│       └── callin-service-requirement.md
│
├── examples/                         # Usage examples
│   ├── basic_connection.py
│   ├── zero_config_test.py
│   └── advanced_isolation.py
│
├── pyproject.toml                    # Package configuration
├── README.md                         # User-facing docs
├── CONSTITUTION.md                   # Core principles
└── CLAUDE.md                         # AI context (updated in Phase 1)
```

**Structure Decision**: Single Python package structure chosen because:
- Library-first design (not web/mobile app)
- Clear separation of concerns (connections, containers, testing, config, utils)
- Follows standard Python package layout conventions
- Supports both library usage and CLI utilities
- Testable with pytest standard practices

## Phase 0: Outline & Research

### Research Tasks

Since this is an **extraction project** with proven source code in `~/ws/rag-templates/`, research focuses on:

1. **Source Code Analysis**:
   - Map rag-templates code to new package structure
   - Identify dependencies and coupling
   - Extract reusable components vs. project-specific code
   - Identify test patterns to port

2. **Enhancement Opportunities**:
   - testcontainers-iris-python integration patterns
   - Modern Python type hints (TypedDict, Protocol)
   - pytest best practices (fixtures, markers, parametrize)
   - Connection pooling strategies

3. **Technology Best Practices**:
   - Python 3.9+ type hints and dataclasses
   - pytest 8.0+ fixture scoping patterns
   - testcontainers lifecycle management
   - DBAPI 2.0 specification compliance
   - JDBC connection URL patterns for IRIS

4. **Performance Baselines**:
   - DBAPI vs JDBC benchmarks (already documented: 3x speedup)
   - Container startup times
   - Connection pool overhead
   - Schema validation caching impact

**Output**: research.md documenting:
- Source code mapping (rag-templates → iris-devtester)
- Technology decisions with rationale
- Performance benchmarks and targets
- Migration compatibility strategy

## Phase 1: Design & Contracts

*Prerequisites: research.md complete*

### 1. Data Model (`data-model.md`)

Extract entities from feature spec:

**Core Entities**:
- Connection (metadata, driver type, credentials)
- Configuration (auto-discovered params, overrides)
- SchemaDefinition (tables, columns, validation rules)
- SchemaValidationResult (success/failure, mismatches)
- TestState (isolation level, namespace, cleanup registry)
- ContainerConfig (edition, image, ports, env vars)
- PasswordResetResult (success, new password, error details)

**Relationships**:
- Configuration → Connection (1:N - one config creates many connections)
- TestState → Connection (1:1 - each test state has one connection)
- TestState → ContainerConfig (1:1 optional - container-level isolation)
- SchemaDefinition → SchemaValidationResult (1:N - validated multiple times)

### 2. API Contracts (`contracts/`)

Generate from functional requirements:

**connection-api.md**:
- `get_iris_connection(config=None) → Connection` (FR-006, FR-007)
- `reset_password_if_needed(connection) → PasswordResetResult` (FR-004)
- `test_connection(config) → bool` (FR-032)

**testing-fixtures-api.md**:
- `@pytest.fixture iris_db() → Connection` (FR-030)
- `@pytest.fixture isolated_iris() → Connection` (FR-009)
- `validate_schema(conn, expected) → SchemaValidationResult` (FR-014)
- `reset_schema(conn, definition) → None` (FR-015)

**container-api.md**:
- `IRISContainer.community() → IRISContainer` (FR-022)
- `IRISContainer.enterprise(license_key) → IRISContainer` (FR-022)
- `wait_for_ready() → None` (FR-020, FR-021)

### 3. Contract Tests

Generate failing tests from contracts (TDD):
- `tests/contract/test_connection_api.py`
- `tests/contract/test_testing_fixtures_api.py`
- `tests/contract/test_container_api.py`

Each test validates interface signatures and basic behavior (will fail until implemented).

### 4. Integration Test Scenarios

Extract from user stories:
- Zero-config workflow test (story: pip install && pytest)
- Password remediation workflow test (story: expired credentials)
- Parallel isolation test (story: 50 tests in parallel)
- DBAPI/JDBC fallback test (story: connection attempt)
- Schema validation test (story: schema mismatch)

### 5. Quickstart (`quickstart.md`)

Step-by-step validation of primary user story:
```python
# 1. Install
pip install iris-devtester

# 2. Write test
def test_my_iris_feature(iris_db):
    # iris_db fixture auto-configured
    cursor = iris_db.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1

# 3. Run
pytest  # Just works!
```

### 6. Update CLAUDE.md

Incremental update (preserving manual content):
- Add iris-devtester technical context
- Note testcontainers integration
- Reference CONSTITUTION.md principles
- Update recent changes (Feature 001)

**Output**: data-model.md, contracts/, failing contract tests, quickstart.md, updated CLAUDE.md

## Phase 2: Task Planning Approach

*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Load templates and artifacts**:
   - `.specify/templates/tasks-template.md` as base
   - Load Phase 1 contracts and data model
   - Load quickstart validation steps

2. **Generate TDD task sequence**:
   - **Phase 0**: Setup tasks (project structure, dependencies)
   - **Phase 1**: Data model tasks (create entity classes)
   - **Phase 2**: Contract test tasks (write failing tests)
   - **Phase 3**: Implementation tasks (make tests pass)
   - **Phase 4**: Integration tasks (real IRIS testing)
   - **Phase 5**: Documentation tasks (examples, API docs)

3. **Task ordering rules**:
   - Tests before implementation (TDD)
   - Models before services (dependency order)
   - Core utilities before high-level APIs
   - Unit tests before integration tests
   - Mark [P] for parallel execution (independent modules)

4. **Extraction-specific tasks**:
   - Extract from rag-templates tasks
   - Port and adapt tasks
   - Add type hints tasks
   - Update imports tasks
   - Backwards compatibility validation tasks

**Ordering Strategy**:
```
Setup (1-5) →
Models [P] (6-10) →
Core Utils [P] (11-15) →
Connection Manager (16-20) →
Container Wrapper (21-25) →
Testing Fixtures (26-30) →
Integration Tests (31-35) →
E2E Tests (36-40) →
Documentation (41-45) →
Validation (46-50)
```

**Estimated Output**: 45-50 numbered, ordered tasks in tasks.md

Tasks will reference:
- Source files in `~/ws/rag-templates/` to extract
- Target files in `iris_devtester/` to create
- Test files to write/run
- Documentation to update

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No violations detected. This extraction project aligns perfectly with all 8 constitutional principles. The rag-templates source code was built with these principles in mind (they were extracted from that production experience).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | N/A | N/A |

## Progress Tracking

*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command) - 74 tasks ready
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS (all 8 principles satisfied by design)
- [x] All NEEDS CLARIFICATION resolved (extraction project, source well-defined)
- [x] Complexity deviations documented (none)

---
*Based on IRIS DevTools Constitution v1.0.0 - See `CONSTITUTION.md`*
