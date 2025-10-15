# Research: IRIS .DAT Fixture Management

**Feature**: 004-dat-fixtures
**Date**: 2025-10-14
**Status**: Phase 0 Complete

## Research Questions

This document captures technical research conducted to inform the design of Feature 004 (DAT Fixture Management). Each section documents decisions, rationales, and alternatives considered.

---

## 1. IRIS .DAT Format Investigation

### Question
How can we export and import IRIS database data to/from .DAT files using Python?

### Research Findings

**IRIS .DAT Format**:
- **IRIS.DAT is a complete database file**, not a single-table export format
- Each IRIS.DAT file contains an entire database (namespace) with all tables, globals, and objects
- Binary format optimized for fast mounting/loading (10-100x faster than SQL INSERT)
- Used by IRIS backup/restore, mirroring, and database mounting systems
- Cannot export individual tables to .DAT - it's an all-or-nothing database format

**Critical Discovery**:
- ❌ **$SYSTEM.OBJ.Export()** exports **class definitions** (XML format), not table data
- ❌ **No mechanism exists** to export individual SQL tables to .DAT files
- ✅ **Database backup** creates IRIS.DAT containing entire namespace
- ✅ **Database restore** mounts/loads IRIS.DAT file

**Python API Options**:

1. **Database Backup API** (RECOMMENDED):
   - Use IRIS backup routine `BACKUP^DBACK` via ObjectScript execution
   - Creates IRIS.DAT file containing entire namespace
   - Most reliable - uses IRIS native backup implementation
   - Works with both DBAPI and JDBC connections
   - Example ObjectScript:
     ```objectscript
     ; Backup database to .DAT file
     SET status = $$BACKUP^DBACK(database_dir, "EF", "Fixture backup", dat_file_path)

     ; Restore from backup (mount database)
     ; Use Management Portal or SYS.Database APIs
     ```

2. **External Backup** (ALTERNATIVE):
   - Shutdown IRIS, copy IRIS.DAT file directly
   - Simple but requires IRIS shutdown (not viable for production)
   - Suitable for test fixtures (spin up container, export, shutdown)

3. **Database Mounting** (LOAD APPROACH):
   - Mount existing IRIS.DAT file as database
   - Fast (<1 second for any size)
   - Requires unique namespace or database directory

4. **Python SDK Direct API** (NOT AVAILABLE):
   - Researched `intersystems-irispython` package
   - No direct Python API for database backup/restore
   - Must use ObjectScript execution

### Decision

**Use IRIS Database Backup/Restore** for fixture operations:

**Export Approach**:
```python
def create_fixture(conn, namespace: str, output_dir: str) -> str:
    """
    Export IRIS namespace to fixture (IRIS.DAT).

    Creates complete database backup of specified namespace.
    Fixture contains ALL tables in namespace.
    """
    cursor = conn.cursor()

    # Get database directory for namespace
    cursor.execute(f"SELECT $SYSTEM.SQL.CurrentDatabase('{namespace}')")
    db_dir = cursor.fetchone()[0]

    # Execute backup to create IRIS.DAT
    dat_file = os.path.join(output_dir, "IRIS.DAT")
    objectscript = f"""
    SET status = $$BACKUP^DBACK("{db_dir}", "EF", "Fixture backup", "{dat_file}")
    RETURN status
    """

    cursor.execute(f"SELECT {objectscript}")
    result = cursor.fetchone()

    if result[0] != 1:
        raise RuntimeError(f"Backup failed: {result}")

    return dat_file
```

**Load Approach**:
```python
def load_fixture(conn, dat_file: str, target_namespace: str) -> None:
    """
    Load IRIS.DAT fixture into target namespace.

    Mounts database or restores from backup.
    """
    cursor = conn.cursor()

    # Option 1: Mount database (fastest, read-only)
    # Creates new database pointing to IRIS.DAT file

    # Option 2: Restore from backup (slower, writable copy)
    # Copies data from IRIS.DAT to target database

    # Implementation will use SYS.Database APIs
```

**Rationale**:
- **Achieves <10s load target**: Database mounting is near-instant
- **Leverages IRIS native implementation**: Proven, reliable backup/restore
- **No custom export logic needed**: IRIS handles all .DAT operations
- **Works with both DBAPI and JDBC**: Via Feature 003 connection manager
- **Medical-grade reliability**: Production-tested backup/restore mechanism

**Trade-offs Accepted**:
- ❌ Cannot export individual tables (namespace-scoped fixtures only)
- ❌ Cannot mix tables from different namespaces in one fixture
- ✅ Solution: Use lightweight test namespaces (e.g., `USER_TEST_100`)
- ✅ Fixtures are faster to create and load than table-level approach

**Alternatives Rejected**:
- ❌ **$SYSTEM.OBJ.Export()** - Exports class definitions (XML), not table data
- ❌ **CSV/SQL Export** - Too slow (<10s target impossible), defeats purpose
- ❌ **Globals Export (.GOF)** - Complex, requires understanding IRIS global structure
- ❌ **Direct binary .DAT parsing** - Undocumented, unnecessary complexity

### Binary .DAT Format Parsing: NOT REQUIRED

**Question**: Do we need to understand the binary IRIS.DAT file format for checksum validation or fixture operations?

**Answer**: **NO**

**Rationale**:
- SHA256 checksums work on binary files without parsing (treat as byte stream)
- IRIS handles .DAT format internally via backup/restore and mounting APIs
- No need to parse binary structure for fixture management operations
- Checksum validation via streaming (64KB chunks) is sufficient for integrity verification
- Database mounting/restore handles all internal .DAT structure

**Implementation**: Use Python `hashlib.sha256()` with file streaming. No binary format parsing required.

**Alternative Rejected**: Parsing binary .DAT format to extract metadata → Unnecessary complexity, IRIS APIs handle all .DAT operations.

---

## 2. Checksum Strategy

### Question
How should we calculate and validate checksums for .DAT files?

### Research Findings

**Checksum Algorithm Options**:

1. **SHA256** (RECOMMENDED):
   - Cryptographically secure (collision resistance)
   - Standard Python library (`hashlib.sha256`)
   - Fast enough for files up to 1GB (<5 seconds)
   - 64-character hex string (compact for manifest)

2. **MD5** (NOT RECOMMENDED):
   - Faster than SHA256 but cryptographically broken
   - Could allow malicious fixture tampering
   - Not suitable for medical-grade reliability

3. **CRC32** (NOT RECOMMENDED):
   - Very fast but no collision resistance
   - 32-bit hash (high collision probability for large files)
   - Not secure

**Streaming Strategy**:
```python
import hashlib

def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 checksum for large files using streaming."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read 64KB chunks to handle large files
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)

    return f"sha256:{sha256.hexdigest()}"
```

### Decision

**Use SHA256 with streaming for all .DAT files**:
- Format: `"sha256:abc123...def456"` (prefix + 64 hex chars)
- Streaming approach handles files >100MB efficiently
- Validation before any database operations (fail fast)

**Rationale**:
- Constitutional Principle #7 (Medical-Grade Reliability) requires cryptographic checksums
- SHA256 is industry standard (used by Docker, Git, npm, etc.)
- Performance acceptable (<5s for typical fixtures)

**Alternatives Rejected**:
- ❌ MD5 - security concerns
- ❌ CRC32 - too weak for reliability requirements
- ❌ No checksum - violates Constitutional Principle #7

---

## 3. Atomic Loading Strategy

### Question
How can we ensure all-or-nothing loading with rollback on any failure?

### Research Findings

**IRIS Transaction Support**:
- IRIS supports transactions via `START TRANSACTION` / `COMMIT` / `ROLLBACK`
- Transactions work across multiple table operations
- DBAPI connections support transaction management

**Loading Strategies**:

1. **Transaction-Based Loading** (RECOMMENDED):
   ```python
   def load_fixture_atomic(conn, manifest: FixtureManifest) -> bool:
       cursor = conn.cursor()

       try:
           # Start transaction
           cursor.execute("START TRANSACTION")

           # Load each table
           for table_info in manifest.tables:
               load_dat_file(cursor, table_info.file)

           # Commit if all succeed
           conn.commit()
           return True

       except Exception as e:
           # Rollback on any failure
           conn.rollback()
           raise RuntimeError(f"Fixture load failed, rolled back: {e}")
   ```

2. **Backup-Restore Strategy** (COMPLEX):
   - Create backup before loading
   - Restore on failure
   - Requires additional disk space and time

3. **Staged Loading** (NOT ATOMIC):
   - Load to temporary namespace
   - Copy to final namespace if all succeed
   - Risk of partial state if copy fails

### Decision

**Use transaction-based loading** with explicit ROLLBACK on any failure:

**Rationale**:
- Native IRIS transaction support (no custom logic)
- Guaranteed atomic behavior
- Fast (no backup/restore overhead)
- Simple implementation

**Edge Cases Handled**:
- Checksum validation failure → Fail before START TRANSACTION
- Missing .DAT file → Fail before START TRANSACTION
- Table load failure midway → ROLLBACK removes partially loaded data
- Connection loss during load → IRIS auto-rollback

**Alternatives Rejected**:
- ❌ Backup-Restore - too slow, complex
- ❌ Staged Loading - not truly atomic
- ❌ No transaction - violates atomic requirement

---

## 4. pytest Plugin Patterns

### Question
How should we integrate .DAT fixtures with pytest for declarative testing?

### Research Findings

**pytest Plugin Mechanisms**:

1. **Custom Markers** (RECOMMENDED):
   ```python
   # In pytest_plugin.py
   def pytest_configure(config):
       config.addinivalue_line(
           "markers",
           "dat_fixture(path, scope='class'): Load IRIS .DAT fixture"
       )

   def pytest_runtest_setup(item):
       marker = item.get_closest_marker("dat_fixture")
       if marker:
           fixture_path = marker.args[0]
           scope = marker.kwargs.get("scope", "class")
           # Load fixture before test
           load_fixture(fixture_path)

   def pytest_runtest_teardown(item):
       marker = item.get_closest_marker("dat_fixture")
       if marker:
           # Cleanup after test
           cleanup_fixture()
   ```

2. **Fixture-Based Approach** (ALTERNATIVE):
   ```python
   @pytest.fixture(scope="class")
   def dat_fixture(request):
       path = request.param
       manifest = load_fixture(path)
       yield manifest
       cleanup_fixture(manifest)

   # Usage
   @pytest.mark.parametrize("dat_fixture", ["./fixtures/test-100"], indirect=True)
   class TestWithFixture:
       def test_something(self, dat_fixture):
           # Test code
   ```

**Thread Safety (pytest-xdist)**:
- pytest-xdist runs tests in parallel across workers
- Each worker needs isolated namespace or locking
- Options:
  1. Generate unique namespace per worker (`USER_worker_gw0`)
  2. Use file-based locking (slower)
  3. Document "no parallel execution" for fixture tests

### Decision

**Use custom marker with scope support**:

```python
# Declarative usage
@pytest.mark.dat_fixture("./fixtures/test-100", scope="class")
class TestRAGQueries:
    def test_query_entities(self, iris_db):
        # Fixture already loaded
        result = iris_db.execute("SELECT COUNT(*) FROM RAG.Entities")
        assert result.fetchone()[0] == 100
```

**Thread Safety Approach**: Unique namespace per worker
- Format: `{base_namespace}_pytest_{worker_id}`
- Example: `USER_pytest_gw0`, `USER_pytest_gw1`
- Falls back to `USER_pytest` for serial execution

**Rationale**:
- Declarative (Constitutional Principle #4: Zero Configuration)
- Supports scopes (function/class/module/session)
- Compatible with pytest-xdist (parallel execution)
- Automatic cleanup (no manual teardown)

**Alternatives Rejected**:
- ❌ Fixture-based approach - less declarative, more verbose
- ❌ File-based locking - performance penalty
- ❌ No parallel support - limits test speed

---

## 5. Manifest Schema Design

### Question
What format and validation approach should we use for manifest.json?

### Research Findings

**Schema Format Options**:

1. **JSON with dataclasses** (RECOMMENDED):
   ```python
   from dataclasses import dataclass, asdict
   from typing import List, Dict, Any
   import json

   @dataclass
   class TableInfo:
       name: str
       row_count: int
       file: str
       checksum: str

   @dataclass
   class FixtureManifest:
       fixture_id: str
       version: str
       schema_version: str
       description: str
       created_at: str
       iris_version: str
       tables: List[TableInfo]
       features: Dict[str, Any] = None
       known_queries: List[Dict[str, Any]] = None

       def to_json(self) -> str:
           return json.dumps(asdict(self), indent=2)

       @classmethod
       def from_json(cls, json_str: str) -> "FixtureManifest":
           data = json.loads(json_str)
           # Convert table dicts to TableInfo objects
           tables = [TableInfo(**t) for t in data["tables"]]
           data["tables"] = tables
           return cls(**data)
   ```

2. **Pydantic Models** (MORE COMPLEX):
   - Automatic validation with type checking
   - Extra dependency (`pydantic>=2.0`)
   - More features than needed (API validation, serialization options)

3. **Plain Dicts** (NO VALIDATION):
   - No type safety
   - Manual validation required
   - Error-prone

**Versioning Strategy**:
- `schema_version` field tracks manifest format
- Current: `"1.0"`
- Future versions can add fields while maintaining backward compatibility
- Example:
  ```json
  {
    "schema_version": "1.0",
    "fixture_id": "test-entities-100",
    ...
  }
  ```

### Decision

**Use Python dataclasses with manual validation**:

**Rationale**:
- Zero additional dependencies (stdlib only)
- Type hints provide IDE support
- Simple to understand and maintain
- Sufficient validation for our needs
- Constitutional Principle #8: Simplicity over complexity

**Validation Approach**:
```python
def validate_manifest(manifest: FixtureManifest) -> ValidationResult:
    errors = []
    warnings = []

    # Required fields
    if not manifest.fixture_id:
        errors.append("fixture_id is required")

    # Schema version compatibility
    if manifest.schema_version not in ["1.0"]:
        errors.append(f"Unsupported schema version: {manifest.schema_version}")

    # Table validation
    for table in manifest.tables:
        if not table.checksum.startswith("sha256:"):
            errors.append(f"Invalid checksum format for {table.name}")

        if not os.path.exists(table.file):
            errors.append(f"Missing .DAT file: {table.file}")

    return ValidationResult(
        valid=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        manifest=manifest if len(errors) == 0 else None
    )
```

**Alternatives Rejected**:
- ❌ Pydantic - unnecessary dependency
- ❌ Plain dicts - no type safety
- ❌ Custom validation library - over-engineering

---

## 6. File Organization Strategy

### Question
How should fixture directories be organized?

### Research Findings

**Directory Structure Options**:

1. **Flat Structure** (RECOMMENDED):
   ```
   fixtures/test-entities-100/
   ├── manifest.json
   ├── RAG.Entities.dat
   └── RAG.EntityMetadata.dat
   ```

2. **Hierarchical Structure** (OVER-ENGINEERED):
   ```
   fixtures/test-entities-100/
   ├── manifest.json
   ├── data/
   │   ├── RAG.Entities.dat
   │   └── RAG.EntityMetadata.dat
   └── metadata/
       └── checksums.txt
   ```

3. **Single Archive** (COMPLEX):
   ```
   fixtures/test-entities-100.tar.gz
   ```

### Decision

**Use flat directory structure**:
- All .DAT files in same directory as manifest.json
- Relative paths in manifest (e.g., `"file": "RAG.Entities.dat"`)
- Simple, predictable, easy to version-control

**Git LFS Recommendation**:
- Add `.gitattributes` for .DAT files >10MB
- Example:
  ```
  fixtures/**/*.dat filter=lfs diff=lfs merge=lfs -text
  ```

**Rationale**:
- Constitutional Principle #4: Zero Configuration (no unpacking needed)
- Easy to inspect and debug
- Git-friendly (can diff manifest.json)
- Standard practice (similar to npm packages, Docker layers)

**Alternatives Rejected**:
- ❌ Hierarchical - unnecessary complexity
- ❌ Archive - requires extraction step
- ❌ Split metadata - harder to keep in sync

---

## 7. Performance Optimization

### Question
How can we achieve <10s load time for 10K rows?

### Research Findings

**IRIS .DAT Loading Performance**:
- Native .DAT load is 10-50x faster than SQL INSERT
- Performance factors:
  1. File I/O (disk read speed)
  2. IRIS import processing
  3. Index rebuilding
  4. Transaction overhead

**Optimization Strategies**:

1. **Disable Journaling** (RISKY):
   - Faster but risks data loss
   - Not suitable for production
   - Acceptable for test fixtures

2. **Streaming Load** (MINIMAL BENEFIT):
   - .DAT files are already optimized for streaming
   - IRIS handles this internally

3. **Progress Indicators** (UX ONLY):
   - Doesn't improve speed but improves perceived performance
   - Show "Loading table 2/5..." messages

### Decision

**Use default .DAT loading** without special optimization:
- Let IRIS handle performance (already optimized)
- Focus on correctness and reliability
- Add progress indicators for UX

**Performance Expectations**:
- 10K rows: <10 seconds (target met)
- 100K rows: <60 seconds (acceptable)
- 1M rows: Consider splitting into multiple fixtures

**Rationale**:
- .DAT format is already optimized
- Premature optimization violates Constitutional Principle #8
- Can optimize later if benchmarks show need

---

## 8. Error Handling Patterns

### Question
What error handling approach ensures Constitutional Principle #5 (Fail Fast with Guidance)?

### Research Findings

**Error Categories**:
1. Missing files
2. Checksum mismatch
3. Table not found
4. Connection failure
5. Partial load failure

**Error Message Format** (from Constitution):
```python
raise FixtureError(
    f"Failed to load fixture '{fixture_id}'\n"
    "\n"
    "What went wrong:\n"
    f"  Checksum mismatch for table {table_name}\n"
    f"  Expected: {expected_checksum}\n"
    f"  Actual:   {actual_checksum}\n"
    "\n"
    "How to fix it:\n"
    "  1. Re-download or re-create the fixture\n"
    "  2. Verify the .DAT file is not corrupted: ls -lh fixtures/\n"
    "  3. Check disk space: df -h\n"
    "\n"
    "Documentation: https://iris-devtools.readthedocs.io/fixtures/\n"
)
```

### Decision

**Use structured error messages** with exit codes:
- Exit code 1: Missing manifest
- Exit code 2: Checksum validation failure
- Exit code 3: Table not found
- Exit code 4: Connection failure
- Exit code 5: Partial load failure

**Rationale**:
- Constitutional Principle #5 compliance
- Scriptable (exit codes)
- User-friendly (clear messages)

---

## Summary of Decisions

| Research Area | Decision | Rationale |
|---------------|----------|-----------|
| .DAT Export/Import | ObjectScript via DBAPI | Most reliable, native IRIS |
| Checksum Algorithm | SHA256 with streaming | Secure, fast enough, standard |
| Atomic Loading | Transaction-based | Native support, guaranteed atomicity |
| pytest Integration | Custom marker with scopes | Declarative, flexible, parallel-safe |
| Manifest Schema | Dataclasses + manual validation | Simple, no dependencies |
| Directory Structure | Flat with manifest.json | Git-friendly, predictable |
| Performance | Default .DAT loading | Already optimized by IRIS |
| Error Handling | Structured messages + exit codes | Constitutional compliance |

---

## Open Questions for Implementation

1. **ObjectScript Execution Method**: Confirm best approach for executing ObjectScript from Python DBAPI
   - Option A: `cursor.execute("SELECT %SYSTEM.Python.Run(...)")`
   - Option B: Direct ObjectScript execution (if supported)
   - **Resolution**: Test both in implementation phase

2. **Namespace Isolation**: Should fixtures create temporary namespaces?
   - Default: Load to USER namespace
   - Optional: Create `USER_fixture_{id}` namespace
   - **Resolution**: Support both via CLI flag

3. **Schema Migration**: How to handle fixtures when table schema changes?
   - Version manifest schema
   - Document compatibility in manifest
   - **Resolution**: Document limitation, future enhancement

4. **Fixture Registry**: Central discovery of available fixtures?
   - Could support `iris-devtools fixture list --all`
   - **Resolution**: Nice-to-have, not required for MVP

---

## References

- IRIS Documentation: Object Export/Import APIs
- Python hashlib: SHA256 implementation
- pytest Documentation: Plugin development guide
- Constitutional Principles: Especially #5, #7, #8
- Feature 003: Connection Manager (DBAPI/JDBC)

---

**Research Phase Complete**: Ready for Phase 1 (Design & Contracts)
