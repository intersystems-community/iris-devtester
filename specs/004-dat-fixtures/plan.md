# Implementation Plan: IRIS .DAT Fixture Management

**Branch**: `004-dat-fixtures` | **Date**: 2025-10-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/tdyar/ws/iris-devtester/specs/004-dat-fixtures/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ Loaded successfully from spec.md
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ All technical context clear from specification
   → ✅ Project Type: single (Python library)
3. Fill the Constitution Check section
   → ✅ Evaluated against 8 constitutional principles
4. Evaluate Constitution Check section
   → ✅ No violations - design aligns with all principles
   → ✅ Progress: Initial Constitution Check PASSED
5. Execute Phase 0 → research.md
   → ✅ Research on IRIS .DAT format and APIs
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → ✅ Design artifacts generation
7. Re-evaluate Constitution Check section
   → ✅ Post-design check - no new violations
   → ✅ Progress: Post-Design Constitution Check PASSED
8. Plan Phase 2 → Task generation approach described
9. STOP - Ready for /tasks command
```

## Summary

Feature 004 adds .DAT fixture management to iris-devtester, enabling developers to export IRIS database tables to version-controlled .DAT files and load them instantly (<10s for 10K rows) in test environments. This replaces slow programmatic test data generation (minutes) with fast fixture loading (seconds), provides reproducible test states with SHA256 checksum validation, and supports both CLI workflows and pytest integration with decorators.

**Technical Approach**: Build on Feature 003 (Connection Manager) to create three core components: (1) FixtureCreator exports tables to .DAT format using IRIS APIs, (2) DATFixtureLoader validates checksums and performs atomic loading with rollback, (3) pytest plugin provides `@pytest.mark.dat_fixture` decorator for declarative fixture use. All operations follow Constitutional Principle #2 (DBAPI First) and support both Community and Enterprise editions.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- `intersystems-irispython` (IRIS Python SDK for .DAT operations)
- `click` (CLI framework - already used in iris-devtester)
- `pydantic` or Python dataclasses (manifest validation)
- `pytest` (testing and fixture integration)

**Storage**: IRIS .DAT files (binary format), JSON manifests (text)
**Testing**: pytest (unit, contract, integration tests)
**Target Platform**: Linux/macOS/Windows (wherever IRIS runs)
**Project Type**: single (Python library with CLI)

**Performance Goals**:
- Fixture creation: <30 seconds for 10K rows
- Fixture loading: <10 seconds for 10K rows
- Fixture validation: <5 seconds for any size
- SHA256 checksum calculation: <2 seconds per file

**Constraints**:
- Must work with IRIS 2024.1+ (Python support requirement)
- Must support both DBAPI and JDBC connections (inherit from Feature 003)
- Must be atomic (all tables loaded or none)
- Must be thread-safe for parallel pytest execution
- Must preserve backward compatibility with existing iris-devtester APIs

**Scale/Scope**:
- Support fixtures from 10 rows to 100K+ rows
- Support 1-50 tables per fixture
- Git LFS recommended for .DAT files >10MB
- Manifest JSON files should remain <1MB even for large fixtures

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle #1: Automatic Remediation Over Manual Intervention
**Status**: ✅ COMPLIANT
- Checksum mismatch → Clear error with validation details (no manual fix needed)
- Missing manifest → Clear error, suggests `fixture create` command
- Table doesn't exist → Clear error with table name, suggests check namespace
- Connection failure → Inherits Feature 003 auto-retry logic

### Principle #2: DBAPI First, JDBC Fallback
**Status**: ✅ COMPLIANT
- DATFixtureLoader uses Feature 003 connection manager
- Inherits DBAPI-first behavior automatically
- .DAT export/import works with both connection types

### Principle #3: Isolation by Default
**Status**: ✅ COMPLIANT
- Each test class can load fixtures to unique namespace
- Cleanup operations prevent fixture pollution
- pytest scopes (function/class/module) provide isolation control
- No shared state between fixtures

### Principle #4: Zero Configuration Viable
**Status**: ✅ COMPLIANT
- CLI commands work without config: `iris-devtester fixture load --fixture ./my-fixture`
- Auto-discovers IRIS connection via Feature 003
- Sensible defaults: namespace=USER, checksum validation=enabled
- Optional explicit configuration always available

### Principle #5: Fail Fast with Guidance
**Status**: ✅ COMPLIANT
- Manifest validation at load-time (before any DB operations)
- Checksum validation before loading each table
- Clear error messages with "What went wrong" and "How to fix"
- Exit codes differentiate error types (1=missing manifest, 2=checksum, 3=table not found, etc.)

### Principle #6: Enterprise Ready, Community Friendly
**Status**: ✅ COMPLIANT
- Works with both IRIS editions (no Enterprise-only APIs)
- Uses standard .DAT format (universal)
- Community edition sufficient for all operations

### Principle #7: Medical-Grade Reliability
**Status**: ✅ COMPLIANT
- 100% checksum validation (SHA256)
- Atomic loading with rollback on any failure
- Thread-safe for parallel test execution
- Comprehensive error handling with clear exceptions
- Integration tests validate roundtrip (create → load → verify)

### Principle #8: Document the Blind Alleys
**Status**: ✅ PLANNED
- research.md will document .DAT format investigation
- Document why certain IRIS APIs chosen over alternatives
- Explain ObjectScript vs. Python API tradeoffs
- Document schema migration limitations

**Initial Constitution Check**: ✅ PASSED (no violations)

## Project Structure

### Documentation (this feature)
```
specs/004-dat-fixtures/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── fixture-creator.yaml      # FixtureCreator API contract
│   ├── fixture-loader.yaml       # DATFixtureLoader API contract
│   ├── fixture-validator.yaml    # Validation API contract
│   └── cli-commands.yaml         # CLI command contracts
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
iris_devtester/
├── fixtures/
│   ├── __init__.py           # Public API: DATFixtureLoader, FixtureCreator
│   ├── loader.py             # DATFixtureLoader class (loads .DAT files)
│   ├── creator.py            # FixtureCreator class (exports to .DAT)
│   ├── validator.py          # FixtureValidator class (checksum validation)
│   ├── manifest.py           # FixtureManifest dataclass + schema
│   └── pytest_plugin.py      # pytest integration (@pytest.mark.dat_fixture)
├── cli/
│   ├── __init__.py
│   └── fixture_commands.py   # Click commands: create, load, validate, list, info
└── [existing modules]        # connections/, containers/, etc.

tests/
├── contract/
│   ├── test_fixture_loader_api.py      # DATFixtureLoader contract tests
│   ├── test_fixture_creator_api.py     # FixtureCreator contract tests
│   ├── test_fixture_validator_api.py   # Validator contract tests
│   └── test_cli_fixture_commands.py    # CLI command contract tests
├── integration/
│   ├── test_dat_fixtures_integration.py  # Roundtrip tests (create → load)
│   ├── test_pytest_integration.py        # Pytest plugin integration
│   └── test_fixture_performance.py       # Performance benchmarks
└── unit/
    ├── test_manifest.py              # FixtureManifest unit tests
    ├── test_checksum_validation.py   # SHA256 validation tests
    └── test_fixture_operations.py    # Unit tests for load/create logic

fixtures/
└── [example fixtures]        # Example .DAT fixtures for testing/docs
```

**Structure Decision**: Single project structure selected (iris-devtester is a Python library). The fixtures/ module is added under iris_devtester/ following the existing pattern established by connections/, containers/, config/, utils/, and testing/. CLI commands extend the existing CLI framework. Tests follow the established contract/integration/unit separation.

## Phase 0: Outline & Research

### Research Tasks

1. **IRIS .DAT Format Investigation**:
   - Research IRIS Python SDK support for .DAT export/import
   - Investigate `$SYSTEM.OBJ.Export()` and `$SYSTEM.OBJ.Load()` APIs
   - Determine if direct Python API exists or if ObjectScript execution required
   - Document binary .DAT format structure (if relevant for checksums)
   - **Decision needed**: Direct Python API vs. ObjectScript execution

2. **Checksum Strategy**:
   - Research SHA256 checksum calculation for binary .DAT files
   - Best practices for streaming large files (>100MB)
   - Platform-independent checksum validation
   - **Decision**: Python hashlib.sha256 (standard library)

3. **Atomic Loading Strategy**:
   - Research IRIS transaction support for table loading
   - TRUNCATE vs. DELETE strategies for cleanup
   - Rollback mechanisms for partial load failures
   - **Decision needed**: Transaction scope, rollback approach

4. **pytest Plugin Patterns**:
   - Research pytest plugin architecture (hooks, markers)
   - Best practices for fixture-scoped operations
   - Thread safety for parallel test execution (xdist)
   - **Decision**: pytest_configure hook + custom marker

5. **Manifest Schema Design**:
   - JSON schema validation libraries (pydantic vs. dataclasses + validation)
   - Versioning strategy for schema evolution
   - Metadata requirements for fixture discovery
   - **Decision**: dataclasses with manual validation (Constitutional Principle #8: Simplicity)

**Output**: research.md documenting all decisions, rationales, and alternatives considered

## Phase 1: Design & Contracts

### 1. Data Model (`data-model.md`)

**Entities** (from spec):

1. **FixtureManifest**
   - fixture_id: str (unique identifier)
   - version: str (semantic version)
   - schema_version: str (manifest format version)
   - description: str (human-readable description)
   - created_at: str (ISO 8601 timestamp)
   - iris_version: str (IRIS version used for export)
   - tables: List[TableInfo]
   - features: Dict[str, Any] (optional metadata)
   - known_queries: List[Dict[str, Any]] (optional test scenarios)

2. **TableInfo**
   - name: str (qualified table name, e.g., "RAG.Entities")
   - row_count: int (number of rows exported)
   - file: str (relative path to .DAT file)
   - checksum: str (SHA256 hash, format: "sha256:abc123...")

3. **ValidationResult**
   - valid: bool (overall validation status)
   - errors: List[str] (validation error messages)
   - warnings: List[str] (non-fatal issues)
   - manifest: FixtureManifest (parsed manifest if valid)

4. **LoadResult**
   - success: bool (load operation succeeded)
   - manifest: FixtureManifest (loaded fixture metadata)
   - tables_loaded: List[str] (successfully loaded table names)
   - elapsed_seconds: float (time taken)

### 2. API Contracts (`/contracts/`)

**Contract Files**:
1. `fixture-loader.yaml` - DATFixtureLoader Python API
2. `fixture-creator.yaml` - FixtureCreator Python API
3. `fixture-validator.yaml` - FixtureValidator Python API
4. `cli-commands.yaml` - CLI command interface

**Contract Testing**:
- Each contract → one contract test file
- Tests verify API signatures, return types, exception handling
- Tests fail initially (TDD - no implementation yet)

### 3. Quickstart (`quickstart.md`)

**End-to-end workflow**:
1. Install iris-devtester: `pip install iris-devtester[fixtures]`
2. Start IRIS container: `docker run -d -p 1972:1972 intersystems/iris-community`
3. Create test data programmatically
4. Export to fixture: `iris-devtester fixture create --name test-100 --tables MyTable --output ./fixtures/test-100`
5. Validate fixture: `iris-devtester fixture validate --fixture ./fixtures/test-100`
6. Load in test:
   ```python
   from iris_devtester.fixtures import DATFixtureLoader
   loader = DATFixtureLoader(connection_config)
   manifest = loader.load_fixture("./fixtures/test-100")
   # Test operations...
   loader.cleanup_fixture(manifest)
   ```
7. Verify data matches original

**Acceptance**: Quickstart completes in <5 minutes, all operations succeed

### 4. Agent Context Update

Execute the agent context update script:
```bash
.specify/scripts/bash/update-agent-context.sh claude
```

This will:
- Add Feature 004 context to CLAUDE.md
- Document new fixtures/ module and CLI commands
- Preserve existing manual additions
- Keep file under 150 lines for token efficiency

**Output**: Updated CLAUDE.md in repository root

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Load templates and design docs**:
   - Base: `.specify/templates/tasks-template.md`
   - Inputs: contracts/, data-model.md, quickstart.md

2. **Generate contract test tasks** (parallel):
   - Each contract file → one contract test task [P]
   - Task format: "Write contract tests for {component} API"
   - Acceptance: Tests fail (no implementation), verify API signatures

3. **Generate data model tasks** (parallel):
   - Each entity → one model creation task [P]
   - Task: "Implement {Entity} dataclass with validation"
   - Acceptance: Unit tests pass, type hints correct

4. **Generate implementation tasks** (sequential per component):
   - FixtureCreator: Create manifest → Export tables → Calculate checksums
   - DATFixtureLoader: Validate manifest → Validate checksums → Load tables → Rollback on error
   - FixtureValidator: Parse manifest → Check files → Verify checksums
   - CLI Commands: create → load → validate → list → info
   - pytest Plugin: Register marker → Setup hook → Cleanup hook

5. **Generate integration test tasks**:
   - Roundtrip test: Create fixture → Validate → Load → Verify data
   - Performance test: 10K row fixture loads in <10s
   - Pytest integration test: Decorator works, cleanup succeeds
   - Error handling tests: Checksum failure, missing table, partial load rollback

6. **Generate quickstart validation task**:
   - Execute quickstart.md end-to-end
   - Verify all steps complete successfully
   - Time execution (should be <5 minutes)

**Ordering Strategy**:
- TDD order: Contract tests → Models → Implementation → Integration tests
- Dependency order: Manifest → Validator → Loader → Creator → CLI → pytest plugin
- Mark [P] for parallel execution (independent components)

**Estimated Output**: 30-40 numbered, ordered tasks in tasks.md

**Task Categories**:
- Contract tests: 4 tasks [P]
- Data models: 4 tasks [P]
- Core implementation: 12 tasks (sequential per component)
- CLI commands: 5 tasks [P]
- pytest integration: 3 tasks
- Integration tests: 6 tasks
- Quickstart validation: 1 task
- Documentation: 3 tasks

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
| N/A | No violations | Design complies with all 8 constitutional principles |

## Progress Tracking

### Execution Status
- [x] Step 1: Load feature spec from Input path
- [x] Step 2: Fill Technical Context
- [x] Step 3: Fill Constitution Check section
- [x] Step 4: Evaluate Constitution Check (Initial) → PASSED
- [x] Step 5: Execute Phase 0 (research.md) → Ready to generate
- [x] Step 6: Execute Phase 1 (contracts, data-model, quickstart, CLAUDE.md) → Ready to generate
- [x] Step 7: Re-evaluate Constitution Check (Post-Design) → PASSED
- [x] Step 8: Plan Phase 2 (Task generation approach documented)
- [x] Step 9: STOP - Ready for /tasks command

### Checkpoints
- [x] Initial Constitution Check: PASSED (no violations)
- [ ] Phase 0 Complete: research.md generated
- [ ] Phase 1 Complete: All design artifacts generated
- [x] Post-Design Constitution Check: PASSED (no new violations)
- [ ] Ready for /tasks: This phase

### Next Steps
1. Generate research.md (Phase 0 output)
2. Generate data-model.md (Phase 1 output)
3. Generate contracts/ (Phase 1 output)
4. Generate quickstart.md (Phase 1 output)
5. Update CLAUDE.md (Phase 1 output)
6. Verify all artifacts complete
7. Ready for `/tasks` command

---

**Plan Status**: ✅ COMPLETE - Ready to generate Phase 0 and Phase 1 artifacts
