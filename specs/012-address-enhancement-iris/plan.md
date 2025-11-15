# Implementation Plan: DBAPI Package Compatibility

**Branch**: `012-address-enhancement-iris` | **Date**: 2025-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/tdyar/ws/iris-devtester/specs/012-address-enhancement-iris/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ Loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ No NEEDS CLARIFICATION - all requirements clear
   → Detect Project Type: Python library (single project)
   → Set Structure Decision: Standard Python package layout
3. Fill the Constitution Check section
   → ✅ Based on CONSTITUTION.md principles
4. Evaluate Constitution Check section
   → ✅ No violations - aligns with principles
   → Update Progress Tracking: Initial Constitution Check ✅
5. Execute Phase 0 → research.md
   → ✅ Research modern vs legacy package APIs
6. Execute Phase 1 → contracts, data-model.md, quickstart.md
   → ✅ Generate compatibility contracts
7. Re-evaluate Constitution Check section
   → ✅ No new violations
   → Update Progress Tracking: Post-Design Constitution Check ✅
8. Plan Phase 2 → Task generation approach described
9. STOP - Ready for /tasks command
```

## Summary

**Primary Requirement**: Add support for the modern `intersystems-irispython` package while maintaining backward compatibility with the legacy `intersystems-iris` package.

**Technical Approach**: Implement automatic package detection at connection initialization time. Try importing `intersystems-irispython` first (modern), fall back to `intersystems-iris` (legacy), and provide clear error messages if neither is available. Update all DBAPI connection code paths (connections module, fixtures module, testing utilities) to use the detection logic.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- Modern: `intersystems-irispython>=5.3.0` (optional)
- Legacy: `intersystems-iris>=3.0.0` (optional)
- Existing: `testcontainers>=4.0.0`, `testcontainers-iris>=1.2.2`, `docker>=6.0.0`

**Storage**: IRIS database (via DBAPI connection)
**Testing**: pytest with contract, integration, and unit tests
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: single (Python library package)
**Performance Goals**: Package detection <10ms overhead (NFR-001)
**Constraints**:
- Must maintain 95%+ test coverage (NFR-003)
- Zero breaking changes for existing users (FR-002)
- Constitutional error message format (NFR-002)

**Scale/Scope**:
- Affects ~5 modules (connections/, fixtures/, testing/, utils/)
- ~10 files need updates
- Backward compatibility mandatory

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle #1: Automatic Remediation Over Manual Intervention
✅ **COMPLIANT** - Automatic package detection and fallback
- Detects available package automatically
- Falls back gracefully if modern package unavailable
- No manual configuration required (aligns with Principle #4)

### Principle #2: Choose the Right Tool for the Job
✅ **COMPLIANT** - Maintains DBAPI priority
- Modern `intersystems-irispython` uses DBAPI (fast SQL)
- Legacy `intersystems-iris` uses DBAPI (fast SQL)
- Both packages support the same DBAPI operations
- JDBC fallback remains unchanged

✅ **ENHANCED** - Improves tool selection
- Modern package has better performance characteristics
- Prioritizes modern package when both installed
- Maintains backward compatibility

### Principle #3: Isolation by Default
✅ **COMPLIANT** - No impact
- Package compatibility doesn't affect test isolation
- Containers still isolated per test
- Namespace isolation unchanged

### Principle #4: Zero Configuration Viable
✅ **COMPLIANT** - Zero config maintained
- Automatic package detection
- No user configuration required
- Works out of the box with either package

### Principle #5: Fail Fast with Guidance
✅ **COMPLIANT** - Clear error messages required
- FR-005: Clear error when neither package installed
- NFR-002: Constitutional error format (What/Why/How/Docs)
- FR-010: Log which package detected for debugging

### Principle #6: Enterprise Ready, Community Friendly
✅ **COMPLIANT** - Both editions supported
- Works with both packages
- No edition-specific dependencies
- Community and Enterprise both supported

### Principle #7: Medical-Grade Reliability
✅ **COMPLIANT** - Quality maintained
- NFR-003: 95%+ test coverage requirement
- FR-008: Version compatibility validation
- Contract tests for both packages
- Integration tests with real IRIS

### Principle #8: Document the Blind Alleys
✅ **COMPLIANT** - Documentation required
- NFR-004: Document both packages and differences
- Research phase will document why modern package preferred
- Learnings document for package migration

**Constitution Check Result**: ✅ **PASS** - All principles upheld, no violations

## Project Structure

### Documentation (this feature)
```
specs/012-address-enhancement-iris/
├── spec.md              # Feature specification
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (package API research)
├── data-model.md        # Phase 1 output (connection abstraction)
├── quickstart.md        # Phase 1 output (usage guide)
├── contracts/           # Phase 1 output (compatibility contracts)
│   ├── modern-package-contract.json
│   ├── legacy-package-contract.json
│   └── detection-logic-contract.json
└── tasks.md             # Phase 2 output (NOT created by /plan)
```

### Source Code (repository root)
```
iris_devtester/
├── connections/
│   ├── __init__.py
│   ├── dbapi.py          # ✏️ UPDATE: Add package detection
│   ├── connection.py     # ✏️ UPDATE: Use detected package
│   └── manager.py        # ✏️ UPDATE: Log package selection
├── fixtures/
│   ├── __init__.py
│   ├── creator.py        # ✏️ UPDATE: Use package-agnostic DBAPI
│   ├── loader.py         # ✏️ UPDATE: Use package-agnostic DBAPI
│   └── validator.py      # (No changes needed)
├── utils/
│   ├── __init__.py
│   ├── password_reset.py # ✏️ UPDATE: Use detected package
│   └── dbapi_compat.py   # 🆕 NEW: Package detection module
└── testing/
    ├── __init__.py
    └── schema_reset.py   # ✏️ UPDATE: Use package-agnostic DBAPI

tests/
├── contract/
│   ├── test_modern_package_contract.py   # 🆕 NEW
│   ├── test_legacy_package_contract.py   # 🆕 NEW
│   └── test_package_detection.py         # 🆕 NEW
├── integration/
│   ├── test_fixtures_with_modern.py      # 🆕 NEW
│   ├── test_fixtures_with_legacy.py      # 🆕 NEW
│   └── test_dual_package_env.py          # 🆕 NEW
└── unit/
    ├── connections/
    │   └── test_dbapi_compat.py          # 🆕 NEW
    └── fixtures/
        └── test_package_detection.py     # 🆕 NEW

docs/
└── learnings/
    └── package-migration-guide.md        # 🆕 NEW
```

**Structure Decision**: Standard Python library layout. This is a single-project package with no frontend/backend split. Source code in `iris_devtester/`, tests in `tests/` organized by type (contract/integration/unit), documentation in `docs/` and `specs/`.

## Phase 0: Outline & Research
*Goal: Resolve all technical unknowns and establish concrete decisions*

### Research Tasks

1. **Modern Package API Research**
   - Task: "Research `intersystems-irispython` package DBAPI interface"
   - Questions:
     - What is the import path? (`intersystems_iris.dbapi._DBAPI`)
     - What is the connection function signature?
     - Are there any API differences from legacy package?
     - What versions are compatible?
   - Output: API comparison table in research.md

2. **Legacy Package API Research**
   - Task: "Research `intersystems-iris` package DBAPI interface"
   - Questions:
     - What is the import path? (`iris.irissdk`)
     - What is the connection function signature?
     - What versions are we supporting?
   - Output: API documentation in research.md

3. **Package Detection Best Practices**
   - Task: "Research Python package detection patterns"
   - Questions:
     - How to detect if a package is installed?
     - How to validate version compatibility?
     - How to handle import failures gracefully?
   - Output: Detection strategy in research.md

4. **Backward Compatibility Patterns**
   - Task: "Research Python library backward compatibility patterns"
   - Questions:
     - How to support multiple package versions?
     - How to test compatibility without installing both?
     - How to handle deprecated features?
   - Output: Compatibility strategy in research.md

### Research Consolidation

All findings will be documented in `research.md` with format:
- **Decision**: Package detection via try/except import chain
- **Rationale**: Pythonic, zero-config, performant
- **Alternatives considered**: Configuration file, environment variables
- **Implementation approach**: Modern first, legacy fallback, clear errors

**Output**: `specs/012-address-enhancement-iris/research.md`

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

### 1. Data Model (`data-model.md`)

**Entities**: Not applicable - this is a connection compatibility feature, not a data model feature.

**Abstractions**:

1. **DBAPIPackageInfo** (detection result)
   - `package_name`: str ("intersystems-irispython" | "intersystems-iris")
   - `import_path`: str (e.g., "intersystems_iris.dbapi._DBAPI")
   - `version`: str (e.g., "5.3.0")
   - `connect_function`: callable
   - `detection_time_ms`: float

2. **ConnectionAdapter** (abstraction layer)
   - `get_connection()`: Returns DBAPI connection
   - `get_package_info()`: Returns DBAPIPackageInfo
   - `validate_package()`: Validates package compatibility

### 2. API Contracts (`contracts/`)

**Contract 1: Modern Package Detection**
```json
{
  "contract_id": "modern-package-detection",
  "given": "intersystems-irispython is installed",
  "when": "iris-devtester attempts DBAPI connection",
  "then": {
    "package_detected": "intersystems-irispython",
    "import_path_used": "intersystems_iris.dbapi._DBAPI",
    "connection_successful": true,
    "detection_time_ms": "<10"
  }
}
```

**Contract 2: Legacy Package Fallback**
```json
{
  "contract_id": "legacy-package-fallback",
  "given": "Only intersystems-iris is installed",
  "when": "iris-devtester attempts DBAPI connection",
  "then": {
    "package_detected": "intersystems-iris",
    "import_path_used": "iris.irissdk",
    "connection_successful": true,
    "modern_package_attempted": true,
    "fallback_occurred": true
  }
}
```

**Contract 3: No Package Error**
```json
{
  "contract_id": "no-package-error",
  "given": "Neither IRIS package is installed",
  "when": "iris-devtester attempts DBAPI connection",
  "then": {
    "error_raised": "ImportError",
    "error_format": "Constitutional (What/Why/How/Docs)",
    "suggests_package": "intersystems-irispython",
    "provides_install_command": true
  }
}
```

**Contract 4: Package Priority**
```json
{
  "contract_id": "package-priority-modern-first",
  "given": "Both packages are installed",
  "when": "iris-devtester attempts DBAPI connection",
  "then": {
    "package_selected": "intersystems-irispython",
    "legacy_package_ignored": true,
    "reasoning_logged": true
  }
}
```

### 3. Contract Tests

Generate failing tests for each contract:

```python
# tests/contract/test_modern_package_contract.py
def test_modern_package_detection():
    """Contract: Modern package detected when installed."""
    # Setup: Ensure only modern package available
    # Execute: Attempt connection
    # Assert: Modern package used, connection successful
    assert False  # Fails until implemented

# tests/contract/test_legacy_package_contract.py
def test_legacy_package_fallback():
    """Contract: Legacy package used when modern unavailable."""
    assert False  # Fails until implemented

# tests/contract/test_package_detection.py
def test_no_package_error():
    """Contract: Clear error when neither package available."""
    assert False  # Fails until implemented

def test_package_priority():
    """Contract: Modern package prioritized over legacy."""
    assert False  # Fails until implemented
```

### 4. Quickstart Guide (`quickstart.md`)

Extract test scenarios from spec acceptance criteria:

**Scenario 1**: Using modern package
```python
# Install modern package
pip install intersystems-irispython>=5.3.0

# Use iris-devtester (automatic detection)
from iris_devtester.fixtures import FixtureCreator
creator = FixtureCreator(container=iris)
# Works automatically - no code changes needed
```

**Scenario 2**: Using legacy package (backward compatibility)
```python
# Existing users with legacy package
pip install intersystems-iris>=3.0.0

# Use iris-devtester (automatic detection)
from iris_devtester.fixtures import FixtureCreator
creator = FixtureCreator(container=iris)
# Works automatically - no migration required
```

**Scenario 3**: Clear error when no package
```python
# No IRIS package installed
from iris_devtester.connections import get_iris_connection

# Raises clear error:
# ImportError: No IRIS Python package detected
#
# What went wrong:
#   Neither intersystems-irispython nor intersystems-iris found
#
# How to fix it:
#   Install the modern IRIS Python package:
#   → pip install intersystems-irispython>=5.3.0
#
# Documentation: https://iris-devtester.readthedocs.io/dbapi-packages/
```

**Output Files**:
- `specs/012-address-enhancement-iris/data-model.md`
- `specs/012-address-enhancement-iris/contracts/modern-package-contract.json`
- `specs/012-address-enhancement-iris/contracts/legacy-package-contract.json`
- `specs/012-address-enhancement-iris/contracts/detection-logic-contract.json`
- `specs/012-address-enhancement-iris/quickstart.md`

## Phase 2: Task Planning (NOT executed by /plan)
*This section describes the approach for the /tasks command*

### Task Generation Approach

**Strategy**: TDD (Test-Driven Development) with 3-layer testing
1. **Contract tests first** - Define expected behavior (Phase 1 output)
2. **Unit tests** - Test package detection logic in isolation
3. **Integration tests** - Test with real IRIS containers and both packages

**Task Organization**:

1. **Setup Tasks** (T001-T003)
   - Create detection module structure
   - Add type hints and interfaces
   - Update dependencies in pyproject.toml

2. **Core Implementation** (T004-T010)
   - Implement package detection logic
   - Add modern package support
   - Add legacy package fallback
   - Implement error handling
   - Add logging and debugging

3. **Integration Tasks** (T011-T015)
   - Update connections module
   - Update fixtures module
   - Update testing utilities
   - Update CLI commands

4. **Testing Tasks** (T016-T022)
   - Write unit tests (package detection)
   - Write contract tests (all 4 contracts)
   - Write integration tests (both packages)
   - Test error scenarios

5. **Documentation Tasks** (T023-T025)
   - Update README with package info
   - Create migration guide
   - Update API documentation

**Dependencies**:
- T004 depends on T001-T003 (setup)
- T011-T015 depend on T004-T010 (core implementation)
- T016-T022 depend on T011-T015 (integration)
- T023-T025 can run in parallel after T016-T022

**Execution Order**: Setup → Core → Integration → Testing → Documentation

This approach will be fully detailed in `tasks.md` by the /tasks command.

## Progress Tracking

### Phase 0: Research ✅
- [x] Modern package API researched
- [x] Legacy package API researched
- [x] Package detection patterns researched
- [x] Backward compatibility patterns researched
- [x] research.md created

### Phase 1: Design & Contracts ✅
- [x] Data model defined (abstractions documented)
- [x] API contracts created (4 contracts)
- [x] Contract tests generated (failing tests)
- [x] Quickstart scenarios extracted
- [x] data-model.md created
- [x] contracts/ directory created
- [x] quickstart.md created

### Phase 2: Tasks (NOT executed by /plan)
- [ ] Task breakdown created
- [ ] Dependency graph defined
- [ ] Execution order established
- [ ] tasks.md created ← Ready for /tasks command

### Constitution Compliance ✅
- [x] Initial constitution check passed
- [x] Post-design constitution check passed
- [x] No violations detected
- [x] All 8 principles upheld

## Complexity Tracking

**Complexity Introduced**: Low
- Single new module (`dbapi_compat.py`)
- Abstraction layer for package detection
- Updates to existing connection code

**Justification**: Required for modern package support
- Modern `intersystems-irispython` is the current standard
- Legacy users need backward compatibility
- Automatic detection aligns with Constitutional Principle #4 (Zero Config)

**Mitigation**:
- Well-tested detection logic (95%+ coverage)
- Clear error messages (Constitutional Principle #5)
- Comprehensive documentation (migration guide)

**Alternatives Considered**:
1. ❌ **Force migration** - Breaking change, violates Principle #6
2. ❌ **Manual configuration** - Violates Principle #4 (Zero Config)
3. ✅ **Automatic detection** - Maintains all principles, zero breaking changes

## Next Steps

**Ready for**: `/tasks` command

The planning phase is complete with:
- ✅ Specification analyzed
- ✅ Constitution compliance verified
- ✅ Research approach defined
- ✅ Design artifacts outlined
- ✅ Contract tests specified
- ✅ Task generation strategy described

**Command to proceed**: `/tasks` (will generate tasks.md with detailed implementation tasks)

---

**Status**: ✅ Planning complete - Ready for task generation
