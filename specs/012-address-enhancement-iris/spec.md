# Feature Specification: DBAPI Package Compatibility

**Feature Branch**: `012-address-enhancement-iris`
**Created**: 2025-01-13
**Status**: Draft
**Input**: User description: "Address enhancement: iris-devtester DBAPI Compatibility - Support both intersystems-irispython and legacy iris.irissdk packages"

## Execution Flow (main)
```
1. Parse user description from Input
   → Feature clear: Add support for intersystems-irispython package
2. Extract key concepts from description
   → Actors: Python developers using iris-devtester
   → Actions: Create DBAPI connections, execute DAT fixture operations
   → Data: Connection parameters, database credentials
   → Constraints: Must maintain backward compatibility with legacy package
3. For each unclear aspect:
   → No major ambiguities - technical details well-specified in issue
4. Fill User Scenarios & Testing section
   → User flow clear: Install package, use fixtures, expect compatibility
5. Generate Functional Requirements
   → Each requirement testable via import tests and connection tests
6. Identify Key Entities
   → N/A - no new data entities, just connection handling
7. Run Review Checklist
   → All requirements testable
   → No implementation details in spec (only in enhancement request)
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a Python developer using iris-devtester with the modern `intersystems-irispython` package (v5.3.0+), I want to create and load DAT fixtures without encountering AttributeError exceptions, so that I can use all iris-devtester features regardless of which IRIS Python package is installed in my environment.

### Acceptance Scenarios

1. **Given** a Python environment with `intersystems-irispython` package installed, **When** a developer attempts to create a DAT fixture using iris-devtester CLI or Python API, **Then** the operation completes successfully without AttributeError exceptions

2. **Given** a Python environment with the legacy `intersystems-iris` package installed, **When** a developer attempts to create a DAT fixture using iris-devtester CLI or Python API, **Then** the operation completes successfully (backward compatibility maintained)

3. **Given** a Python environment with `intersystems-irispython` package installed, **When** a developer establishes a DBAPI connection to IRIS, **Then** the connection uses the modern `intersystems_iris.dbapi._DBAPI` module

4. **Given** a Python environment with neither package installed, **When** iris-devtester attempts a DBAPI connection, **Then** the system provides a clear error message indicating which package to install

5. **Given** a Python environment with both packages installed, **When** iris-devtester creates a connection, **Then** the modern package takes precedence while maintaining compatibility

### Edge Cases

- What happens when the user has an outdated version of `intersystems-irispython` that doesn't support the expected API?
  - System must detect version incompatibility and fall back gracefully or provide clear error

- How does the system handle partial installations where modules are present but corrupted?
  - Connection logic must validate module functionality before attempting to use it

- What happens when using JDBC fallback mode alongside the new DBAPI packages?
  - JDBC fallback should continue to work as designed in Constitutional Principle #2

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support DBAPI connections using the modern `intersystems-irispython` package (v5.3.0+)

- **FR-002**: System MUST maintain backward compatibility with the legacy `intersystems-iris` package for existing users

- **FR-003**: System MUST detect which IRIS Python package is installed and use the appropriate connection method automatically

- **FR-004**: System MUST prioritize the modern `intersystems-irispython` package when both packages are installed

- **FR-005**: System MUST provide clear error messages when neither IRIS Python package is installed, guiding users to install the appropriate package

- **FR-006**: DAT fixture creation functionality MUST work with both modern and legacy IRIS Python packages

- **FR-007**: DAT fixture loading functionality MUST work with both modern and legacy IRIS Python packages

- **FR-008**: System MUST validate that the detected package version is compatible before attempting to use it

- **FR-009**: All existing iris-devtester features (connections, password reset, schema validation) MUST continue to work with both packages

- **FR-010**: System MUST log which DBAPI package is being used for debugging and transparency

### Non-Functional Requirements

- **NFR-001**: Package detection and selection MUST occur during connection initialization with negligible performance overhead (<10ms)

- **NFR-002**: Error messages MUST follow Constitutional Principle #5 (Fail Fast with Guidance) with What/Why/How/Docs format

- **NFR-003**: Solution MUST maintain 95%+ test coverage requirement from Constitutional Principle #7

- **NFR-004**: Documentation MUST be updated to reflect both supported packages and their differences

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (both packages work, no AttributeError)
- [x] Scope is clearly bounded (DBAPI compatibility only)
- [x] Dependencies and assumptions identified (package versions, backward compatibility)

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted (actors: developers, actions: DBAPI connections, constraints: backward compatibility)
- [x] Ambiguities marked (none - issue well-specified)
- [x] User scenarios defined (5 acceptance scenarios, 3 edge cases)
- [x] Requirements generated (10 functional, 4 non-functional)
- [x] Entities identified (N/A - connection handling only)
- [x] Review checklist passed

---

## Context & Background

### Problem Statement

iris-devtester v1.2.2 currently depends on the legacy `intersystems-iris` package which uses `iris.irissdk` for DBAPI connections. However, the modern IRIS Python ecosystem has migrated to `intersystems-irispython` package (v5.3.0+) which uses `intersystems_iris.dbapi._DBAPI` for connections.

Users installing iris-devtester in environments with only `intersystems-irispython` encounter AttributeError when attempting to use DAT fixtures or any DBAPI-dependent functionality.

### Impact Assessment

**Current State**:
- iris-devtester DAT fixtures: **Unusable** in `intersystems-irispython` environments
- Affects: All users of iris-vector-rag, modern IRIS projects, new installations
- Severity: **High** - breaks core functionality

**Post-Fix State**:
- iris-devtester DAT fixtures: **Fully functional** in both package environments
- Backward compatibility: **Maintained** for legacy users
- User experience: **Seamless** - automatic package detection

### Success Metrics

1. **Functional Success**:
   - DAT fixture creation works with `intersystems-irispython`
   - DAT fixture loading works with `intersystems-irispython`
   - All existing tests pass with both packages

2. **Compatibility Success**:
   - Zero breaking changes for existing users on legacy package
   - Both packages supported simultaneously

3. **Quality Success**:
   - 95%+ test coverage maintained
   - All Constitutional Principles upheld
   - Clear documentation for both packages

---

## Constitutional Compliance

This feature aligns with iris-devtester's core principles:

- **Principle #2 (DBAPI First, JDBC Fallback)**: Maintains DBAPI priority while adding modern package support
- **Principle #4 (Zero Configuration Viable)**: Automatic package detection requires no user configuration
- **Principle #5 (Fail Fast with Guidance)**: Clear error messages when packages missing or incompatible
- **Principle #7 (Medical-Grade Reliability)**: 95%+ coverage requirement maintained with package compatibility tests

---
