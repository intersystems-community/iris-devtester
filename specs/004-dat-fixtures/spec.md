# Feature Specification: IRIS .DAT Fixture Management

**Feature Branch**: `004-dat-fixtures`
**Created**: 2025-10-07
**Status**: Draft
**Input**: User description: "dat-fixtures"

## Execution Flow (main)
```
1. Parse user description from Input
   → Description: "dat-fixtures" (interpreted as .DAT file fixture management for IRIS testing)
2. Extract key concepts from description
   → Identified: .DAT file management, test fixtures, database state export/import, checksum validation
3. For each unclear aspect:
   → No major ambiguities - scope is clear from rag-templates spec
4. Fill User Scenarios & Testing section
   → Defined developer workflows for fixture creation, loading, and validation
5. Generate Functional Requirements
   → 6 major functional requirement areas identified
6. Identify Key Entities
   → DAT files, manifests, fixtures, checksums
7. Run Review Checklist
   → Spec complete and ready for planning
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT developers need and WHY
- ❌ Avoid HOW to implement (specific IRIS APIs, ObjectScript internals)
- 👥 Written for IRIS test developers and QA engineers

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As an IRIS application developer, I need to export database namespaces as .DAT fixtures and load them instantly in test environments, so that I can replace slow test setup (minutes of data generation) with fast fixture loading (seconds), version-control known-good database states, and ensure reproducible testing across all environments.

**Important Note**: Fixtures are **namespace-scoped** - they export an entire IRIS namespace to a single IRIS.DAT file. You cannot export individual tables; instead, organize test data into dedicated namespaces (e.g., `USER_TEST_100`) for fixture creation.

### Acceptance Scenarios

1. **Given** I have a namespace with test data I want to preserve, **When** I run `iris-devtools fixture create --namespace USER_TEST`, **Then** I get a fixture directory containing IRIS.DAT and manifest.json with metadata and checksum

2. **Given** I have a .DAT fixture directory, **When** I run `iris-devtools fixture load` pointing to that directory, **Then** the entire namespace is loaded into my test database in under 10 seconds for 10K rows

3. **Given** I have a fixture directory, **When** I run `iris-devtools fixture validate`, **Then** I see confirmation that the IRIS.DAT checksum matches and all referenced tables exist

4. **Given** I'm writing pytest tests, **When** I use the Python API `DATFixtureLoader`, **Then** I can programmatically load and cleanup fixtures within my test lifecycle

5. **Given** I want to use fixtures declaratively in pytest, **When** I use `@pytest.mark.dat_fixture("path")` decorator, **Then** fixtures auto-load before my test class and auto-cleanup afterward

6. **Given** I have a fixture manifest, **When** I inspect it, **Then** I see human-readable metadata including table names, row counts, checksums, and optional features like known queries

### Edge Cases

- What happens when IRIS.DAT file is corrupted? (Checksum validation fails, clear error, no partial load)
- How does system handle namespace conflicts during load? (Error if target namespace exists, suggest alternate name)
- What happens when fixture load fails midway? (Atomic operation - namespace mount succeeds or fails completely)
- How does system handle concurrent fixture loads? (Thread-safe, each gets unique target namespace)
- What happens when manifest.json is missing? (Clear error message, no attempt to load)
- How does system handle very large fixtures (>100MB)? (Progress indicators for checksum calculation, database mount is near-instant)

## Requirements *(mandatory)*

### Functional Requirements

**FR-001: DAT Fixture Creation**
- System MUST provide CLI command to export IRIS namespace to .DAT fixture
- System MUST create manifest.json with namespace, metadata, table list, row counts, and SHA256 checksum
- System MUST validate namespace existence before export
- System MUST export entire namespace (all tables) to single IRIS.DAT file
- CLI syntax: `iris-devtools fixture create --name <name> --namespace <namespace> --output <dir>`

**FR-002: DAT Fixture Loading**
- System MUST provide CLI command to load .DAT fixture into test database
- System MUST validate IRIS.DAT checksum before loading any data
- System MUST perform atomic loading (entire namespace loaded or none)
- System MUST be idempotent (can reload same fixture multiple times)
- System MUST support loading to different target namespace than source
- CLI syntax: `iris-devtools fixture load --fixture <dir> --namespace <target-namespace>`

**FR-003: Fixture Validation**
- System MUST provide CLI command to validate .DAT fixture integrity
- System MUST verify manifest.json exists and is valid JSON
- System MUST check IRIS.DAT file exists
- System MUST validate SHA256 checksum matches manifest
- System MUST report namespace, row counts, and table names from manifest
- System MUST exit with code 0 on success, non-zero on failure

**FR-004: Python API**
- System MUST provide `DATFixtureLoader` class with connection configuration
- System MUST provide `load_fixture(fixture_path, target_namespace)` method returning manifest
- System MUST provide `validate_fixture(fixture_path)` method returning validation result
- System MUST provide `cleanup_fixture(manifest)` method to remove loaded namespace
- System MUST raise clear exceptions on all error conditions
- System MUST be thread-safe for parallel test execution

**FR-005: Pytest Integration**
- System MUST provide pytest decorator `@pytest.mark.dat_fixture("path")`
- System MUST auto-load fixtures on test class setup
- System MUST auto-cleanup fixtures on test class teardown
- System MUST support pytest scopes: function, class, module, session

**FR-006: Manifest Format**
- System MUST use JSON format with required fields: `fixture_id`, `version`, `namespace`, `dat_file`, `checksum`, `tables`
- System MUST include single `checksum` field for IRIS.DAT file (SHA256 format: "sha256:...")
- System MUST include for each table: `name`, `row_count` (no individual file or checksum)
- System MUST support optional fields: `description`, `created_at`, `features`, `known_queries`
- System MUST include schema version for future compatibility
- System MUST write human-readable format (indented JSON)

### Non-Functional Requirements

**NFR-001: Performance**
- Fixture creation MUST complete in <30 seconds for 10K rows
- Fixture loading MUST complete in <10 seconds for 10K rows
- Fixture validation MUST complete in <5 seconds for any fixture size

**NFR-002: Reliability**
- Checksum validation MUST prevent loading corrupted fixtures (100% detection)
- Loading MUST be atomic (rollback on any failure)
- Error messages MUST be clear and actionable

**NFR-003: Compatibility**
- System MUST support IRIS Community and Enterprise editions
- System MUST work with IRIS 2024.1+
- System MUST support Python 3.9+

**NFR-004: Usability**
- CLI MUST provide clear help messages for all commands
- Long operations MUST show progress indicators
- System MUST provide verbose mode for debugging

### Key Entities

- **DAT Fixture**: A directory containing single IRIS.DAT file and manifest.json representing a complete namespace
  - Contains single IRIS.DAT file (entire namespace backup)
  - Includes manifest.json with namespace, metadata, table list, and checksum
  - Version-controlled and shareable across teams

- **Manifest**: JSON file describing fixture contents
  - Required: fixture_id, version, namespace, dat_file, checksum, tables array
  - Single checksum for IRIS.DAT file (SHA256)
  - Each table: name, row_count (for documentation/validation)
  - Optional: description, created_at, features, known_queries
  - Schema version for compatibility

- **Table Info**: Metadata for a single table in fixture
  - Name (e.g., "RAG.Entities")
  - Row count (for validation)
  - Note: All tables stored in single IRIS.DAT file

- **Fixture Loader**: Component that loads IRIS.DAT into IRIS database
  - Validates IRIS.DAT checksum before loading
  - Performs atomic loading (mount entire namespace or none)
  - Thread-safe for parallel tests
  - Supports cleanup/teardown (namespace removal)

- **Fixture Creator**: Component that exports namespace to IRIS.DAT
  - Uses IRIS backup routine (BACKUP^DBACK)
  - Exports entire namespace to single IRIS.DAT file
  - Calculates SHA256 checksum
  - Generates manifest.json with table list and metadata

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (specific IRIS APIs noted but not mandated)
- [x] Focused on user value and business needs
- [x] Written for test developers (appropriate technical audience)
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (performance targets specified)
- [x] Scope is clearly bounded (fixture management only)
- [x] Dependencies identified (IRIS 2024.1+, Python 3.9+)

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted (.DAT files, fixtures, checksums, test data)
- [x] Ambiguities marked (none - scope clear from rag-templates)
- [x] User scenarios defined (6 scenarios + edge cases)
- [x] Requirements generated (6 FR areas + 4 NFR areas)
- [x] Entities identified (5 key entities)
- [x] Review checklist passed

---

## Notes

### Alignment with Constitutional Principles
- **Principle #4**: Zero Configuration Viable - Auto-discovers IRIS connection
- **Principle #5**: Fail Fast with Guidance - Clear errors with checksums and validation
- **Principle #7**: Medical-Grade Reliability - Atomic operations, checksum validation

### Dependencies
- Feature 003 (Connection Manager) - ✅ Complete
- IRIS Python SDK or ObjectScript execution capability
- pytest framework

### Related Features
- Feature 002 and future features will benefit from fast, reproducible test fixtures
- Enables version-controlled test data for all IRIS projects
- Replaces slow programmatic test data generation

### Success Metrics
1. Load 10K row fixture in <10 seconds ✅
2. 100% checksum validation accuracy ✅
3. Reduce test setup time by 80%+ vs. programmatic generation
4. Adoption in 3+ IRIS projects within 6 months

### Implementation Phases
1. **Phase 1**: Core functionality - manifest (namespace-scoped), validation, SHA256 checksum
2. **Phase 2**: DAT loading - loader class, namespace mounting, CLI command, error handling
3. **Phase 3**: DAT creation - creator class, BACKUP^DBACK integration, manifest generation
4. **Phase 4**: Pytest integration - decorator, auto-cleanup (namespace removal), fixture helpers
5. **Phase 5**: Polish - list/info commands, docs, examples

### Open Questions (to be resolved during planning)
1. ~~Does IRIS Python SDK support .DAT export/load directly, or do we need ObjectScript?~~ **RESOLVED**: Use BACKUP^DBACK routine via DBAPI cursor for backup, database mounting for load
2. ~~Should fixtures create temporary namespaces for isolation?~~ **RESOLVED**: Yes, each fixture load can specify unique target namespace
3. Should iris-devtools recommend Git LFS for .DAT files >10MB?
4. Should there be a central registry of available fixtures?
5. How to handle fixtures when namespace schema changes (tables added/removed after fixture creation)?
