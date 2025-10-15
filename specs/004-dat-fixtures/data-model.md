# Data Model: IRIS .DAT Fixture Management

**Feature**: 004-dat-fixtures
**Date**: 2025-10-14
**Phase**: 1 (Design)

## Overview

This document defines the data models (entities, dataclasses, schemas) for Feature 004. All models use Python dataclasses for simplicity and type safety (no external dependencies required).

---

## Core Entities

### 1. FixtureManifest

Primary entity representing a complete .DAT fixture with metadata and table information.

**Purpose**: Describes fixture contents, creation metadata, and provides references to .DAT files with checksums.

**Python Dataclass**:
```python
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
from datetime import datetime


@dataclass
class FixtureManifest:
    """
    Manifest describing a .DAT fixture.

    A fixture is a directory containing:
    - manifest.json (this schema)
    - IRIS.DAT (single database file containing all tables)

    Example manifest.json:
    {
      "fixture_id": "test-entities-100",
      "version": "1.0.0",
      "schema_version": "1.0",
      "description": "Test fixture with 100 RAG entities from USER namespace",
      "created_at": "2025-10-14T15:30:00Z",
      "iris_version": "2024.1",
      "namespace": "USER",
      "dat_file": "IRIS.DAT",
      "checksum": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "tables": [
        {
          "name": "RAG.Entities",
          "row_count": 100
        },
        {
          "name": "RAG.EntityMetadata",
          "row_count": 100
        }
      ]
    }
    """

    # Required fields
    fixture_id: str  # Unique identifier (e.g., "test-entities-100")
    version: str  # Semantic version (e.g., "1.0.0")
    schema_version: str  # Manifest format version (current: "1.0")
    description: str  # Human-readable description
    created_at: str  # ISO 8601 timestamp (e.g., "2025-10-14T15:30:00Z")
    iris_version: str  # IRIS version used for export (e.g., "2024.1")
    namespace: str  # Source namespace (e.g., "USER", "USER_TEST_100")
    dat_file: str  # Relative path to IRIS.DAT file (typically "IRIS.DAT")
    checksum: str  # SHA256 checksum of IRIS.DAT file
    tables: List["TableInfo"]  # List of tables included in this fixture

    # Optional fields
    features: Optional[Dict[str, Any]] = None  # Additional metadata
    known_queries: Optional[List[Dict[str, Any]]] = None  # Test scenarios

    def to_json(self, indent: int = 2) -> str:
        """
        Serialize manifest to JSON string.

        Args:
            indent: JSON indentation (default: 2 spaces)

        Returns:
            JSON string representation
        """
        data = asdict(self)
        return json.dumps(data, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "FixtureManifest":
        """
        Deserialize manifest from JSON string.

        Args:
            json_str: JSON string to parse

        Returns:
            FixtureManifest instance

        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Convert table dicts to TableInfo objects
        if "tables" in data:
            data["tables"] = [TableInfo(**t) for t in data["tables"]]

        try:
            return cls(**data)
        except TypeError as e:
            raise ValueError(f"Missing required field: {e}")

    @classmethod
    def from_file(cls, manifest_path: str) -> "FixtureManifest":
        """
        Load manifest from file.

        Args:
            manifest_path: Path to manifest.json file

        Returns:
            FixtureManifest instance

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If manifest is invalid
        """
        with open(manifest_path, "r") as f:
            return cls.from_json(f.read())

    def to_file(self, manifest_path: str) -> None:
        """
        Save manifest to file.

        Args:
            manifest_path: Path to manifest.json file
        """
        with open(manifest_path, "w") as f:
            f.write(self.to_json())

    def validate(self) -> "ValidationResult":
        """
        Validate manifest structure and contents.

        Returns:
            ValidationResult with errors and warnings
        """
        from .validator import validate_manifest
        return validate_manifest(self)
```

**Field Descriptions**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `fixture_id` | str | Yes | Unique identifier for fixture | `"test-entities-100"` |
| `version` | str | Yes | Semantic version of fixture | `"1.0.0"` |
| `schema_version` | str | Yes | Manifest format version | `"1.0"` |
| `description` | str | Yes | Human-readable description | `"Test data with 100 entities from USER"` |
| `created_at` | str | Yes | ISO 8601 creation timestamp | `"2025-10-14T15:30:00Z"` |
| `iris_version` | str | Yes | IRIS version for export | `"2024.1"` |
| `namespace` | str | Yes | Source namespace | `"USER"` or `"USER_TEST_100"` |
| `dat_file` | str | Yes | Relative path to IRIS.DAT | `"IRIS.DAT"` |
| `checksum` | str | Yes | SHA256 checksum of IRIS.DAT | `"sha256:e3b0c44..."` |
| `tables` | List[TableInfo] | Yes | List of tables in fixture | See TableInfo below |
| `features` | Dict[str, Any] | No | Custom metadata | `{"use_case": "rag_testing"}` |
| `known_queries` | List[Dict] | No | Test query scenarios | See examples below |

**Example `known_queries`**:
```json
{
  "known_queries": [
    {
      "name": "count_entities",
      "sql": "SELECT COUNT(*) FROM RAG.Entities",
      "expected_result": 100
    },
    {
      "name": "find_by_type",
      "sql": "SELECT * FROM RAG.Entities WHERE EntityType = 'Person'",
      "expected_count": 25
    }
  ]
}
```

---

### 2. TableInfo

Metadata for a single table within a fixture.

**Purpose**: Describes one table stored inside the fixture's IRIS.DAT file, including row count for validation.

**Python Dataclass**:
```python
@dataclass
class TableInfo:
    """
    Information about a single table in a fixture.

    Note: All tables are stored in a single IRIS.DAT file.
    This class tracks which tables are included in the fixture.
    """

    name: str  # Qualified table name (e.g., "RAG.Entities")
    row_count: int  # Number of rows exported (for validation)

    def __str__(self) -> str:
        return f"{self.name} ({self.row_count} rows)"
```

**Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | str | Qualified table name | `"RAG.Entities"` |
| `row_count` | int | Number of rows in table | `100` |

**Important Notes**:
- **No `file` field**: All tables are stored in a single `IRIS.DAT` file
- **No per-table checksum**: Checksum validation applies to the entire IRIS.DAT file
- **Table list**: Manifest tracks which tables are included in the fixture for validation purposes

---

### 3. ValidationResult

Result of manifest or fixture validation.

**Purpose**: Provides structured feedback on validation status, errors, and warnings.

**Python Dataclass**:
```python
@dataclass
class ValidationResult:
    """
    Result of fixture validation.

    Contains validation status, error messages, warnings, and the validated manifest (if valid).
    """

    valid: bool  # Overall validation status
    errors: List[str] = field(default_factory=list)  # Validation errors
    warnings: List[str] = field(default_factory=list)  # Non-fatal issues
    manifest: Optional[FixtureManifest] = None  # Parsed manifest (if valid)

    def raise_if_invalid(self) -> None:
        """
        Raise FixtureValidationError if validation failed.

        Raises:
            FixtureValidationError: If valid=False, with formatted error messages
        """
        if not self.valid:
            from .exceptions import FixtureValidationError

            error_msg = (
                "Fixture validation failed\n"
                "\n"
                "What went wrong:\n"
            )
            for error in self.errors:
                error_msg += f"  - {error}\n"

            if self.warnings:
                error_msg += "\nWarnings:\n"
                for warning in self.warnings:
                    error_msg += f"  - {warning}\n"

            error_msg += (
                "\n"
                "How to fix it:\n"
                "  1. Check manifest.json for syntax errors\n"
                "  2. Verify all .DAT files exist\n"
                "  3. Recalculate checksums: iris-devtools fixture validate --recalc\n"
            )

            raise FixtureValidationError(error_msg)

    def __str__(self) -> str:
        if self.valid:
            return "✅ Validation passed"

        msg = f"❌ Validation failed ({len(self.errors)} errors"
        if self.warnings:
            msg += f", {len(self.warnings)} warnings"
        msg += ")"
        return msg
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `valid` | bool | True if validation passed, False otherwise |
| `errors` | List[str] | List of error messages (validation failures) |
| `warnings` | List[str] | List of warning messages (non-fatal issues) |
| `manifest` | Optional[FixtureManifest] | Parsed manifest if validation succeeded |

**Usage Examples**:
```python
# Validate and raise on error
result = validate_fixture("./fixtures/test-100")
result.raise_if_invalid()

# Check validation status
if result.valid:
    print(f"Fixture has {len(result.manifest.tables)} tables")
else:
    print(f"Validation failed: {result.errors}")

# Display warnings
if result.warnings:
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

---

### 4. LoadResult

Result of fixture loading operation.

**Purpose**: Provides feedback on load success, performance metrics, and loaded tables.

**Python Dataclass**:
```python
@dataclass
class LoadResult:
    """
    Result of fixture load operation.

    Contains load status, manifest, list of successfully loaded tables, and performance metrics.
    """

    success: bool  # Load operation succeeded
    manifest: FixtureManifest  # Loaded fixture metadata
    tables_loaded: List[str]  # Successfully loaded table names
    elapsed_seconds: float  # Time taken to load fixture

    def __str__(self) -> str:
        if self.success:
            return (
                f"✅ Loaded {len(self.tables_loaded)} tables "
                f"in {self.elapsed_seconds:.2f}s"
            )
        return "❌ Load failed"

    def summary(self) -> str:
        """
        Generate detailed summary of load operation.

        Returns:
            Multi-line summary string
        """
        lines = [
            f"Fixture: {self.manifest.fixture_id}",
            f"Status: {'Success' if self.success else 'Failed'}",
            f"Tables loaded: {len(self.tables_loaded)}",
            f"Time elapsed: {self.elapsed_seconds:.2f}s",
        ]

        if self.tables_loaded:
            lines.append("\nTables:")
            for table_name in self.tables_loaded:
                # Find row count from manifest
                table_info = next(
                    (t for t in self.manifest.tables if t.name == table_name),
                    None
                )
                if table_info:
                    lines.append(f"  - {table_name} ({table_info.row_count} rows)")
                else:
                    lines.append(f"  - {table_name}")

        return "\n".join(lines)
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if all tables loaded successfully |
| `manifest` | FixtureManifest | Metadata of loaded fixture |
| `tables_loaded` | List[str] | List of successfully loaded table names |
| `elapsed_seconds` | float | Total time for load operation |

**Usage Examples**:
```python
# Load fixture and check result
result = loader.load_fixture("./fixtures/test-100")

if result.success:
    print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")

# Display detailed summary
print(result.summary())

# Performance check
if result.elapsed_seconds > 10:
    print("Warning: Load took longer than expected")
```

---

## Type Aliases

Common type aliases for clarity:

```python
from typing import TypeAlias

# Path types
FixturePath: TypeAlias = str  # Path to fixture directory
DATFilePath: TypeAlias = str  # Path to .DAT file
ManifestPath: TypeAlias = str  # Path to manifest.json

# Checksum type
Checksum: TypeAlias = str  # Format: "sha256:abc123..."

# Connection type (from Feature 003)
IRISConnection: TypeAlias = Any  # iris_devtools.connections.IRISConnection
```

---

## Relationships

```
FixtureManifest (1) ──> (N) TableInfo
    │
    └─> Describes directory containing:
        - manifest.json (this object serialized)
        - *.dat files (referenced by TableInfo.file)

ValidationResult ──> (0..1) FixtureManifest
    │
    └─> Contains validated manifest if validation succeeded

LoadResult ──> (1) FixtureManifest
    │
    └─> Contains manifest of loaded fixture
```

---

## Validation Rules

### FixtureManifest Validation

```python
def validate_manifest(manifest: FixtureManifest) -> ValidationResult:
    """
    Validate manifest structure and contents.

    Checks:
    1. Required fields present
    2. Schema version supported
    3. Tables list not empty
    4. Each table has valid checksum format
    5. No duplicate table names

    Returns:
        ValidationResult with errors and warnings
    """
    errors = []
    warnings = []

    # Required fields
    if not manifest.fixture_id:
        errors.append("fixture_id is required")
    if not manifest.version:
        errors.append("version is required")
    if not manifest.schema_version:
        errors.append("schema_version is required")

    # Schema version compatibility
    if manifest.schema_version not in ["1.0"]:
        errors.append(f"Unsupported schema version: {manifest.schema_version}")

    # Tables validation
    if not manifest.tables:
        errors.append("At least one table required")
    else:
        # Check for duplicate table names
        table_names = [t.name for t in manifest.tables]
        if len(table_names) != len(set(table_names)):
            errors.append("Duplicate table names found")

        # Validate each table
        for table in manifest.tables:
            if not table.name:
                errors.append("Table name is required")
            if table.row_count < 0:
                errors.append(f"Invalid row count for {table.name}: {table.row_count}")
            if not table.checksum.startswith("sha256:"):
                errors.append(f"Invalid checksum format for {table.name}")

    # Warnings (non-fatal)
    if not manifest.description:
        warnings.append("No description provided")

    return ValidationResult(
        valid=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        manifest=manifest if len(errors) == 0 else None
    )
```

---

## Serialization Examples

### FixtureManifest to JSON

```python
manifest = FixtureManifest(
    fixture_id="test-entities-100",
    version="1.0.0",
    schema_version="1.0",
    description="Test fixture with 100 RAG entities",
    created_at="2025-10-14T15:30:00Z",
    iris_version="2024.1",
    tables=[
        TableInfo(
            name="RAG.Entities",
            row_count=100,
            file="RAG.Entities.dat",
            checksum="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ),
        TableInfo(
            name="RAG.EntityMetadata",
            row_count=100,
            file="RAG.EntityMetadata.dat",
            checksum="sha256:a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447"
        )
    ],
    features={"use_case": "rag_testing", "dataset": "synthetic"},
    known_queries=[
        {
            "name": "count_entities",
            "sql": "SELECT COUNT(*) FROM RAG.Entities",
            "expected_result": 100
        }
    ]
)

# Serialize to JSON
json_str = manifest.to_json()

# Save to file
manifest.to_file("./fixtures/test-entities-100/manifest.json")
```

**Output JSON**:
```json
{
  "fixture_id": "test-entities-100",
  "version": "1.0.0",
  "schema_version": "1.0",
  "description": "Test fixture with 100 RAG entities",
  "created_at": "2025-10-14T15:30:00Z",
  "iris_version": "2024.1",
  "tables": [
    {
      "name": "RAG.Entities",
      "row_count": 100,
      "file": "RAG.Entities.dat",
      "checksum": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    {
      "name": "RAG.EntityMetadata",
      "row_count": 100,
      "file": "RAG.EntityMetadata.dat",
      "checksum": "sha256:a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447"
    }
  ],
  "features": {
    "use_case": "rag_testing",
    "dataset": "synthetic"
  },
  "known_queries": [
    {
      "name": "count_entities",
      "sql": "SELECT COUNT(*) FROM RAG.Entities",
      "expected_result": 100
    }
  ]
}
```

### JSON to FixtureManifest

```python
# Load from file
manifest = FixtureManifest.from_file("./fixtures/test-entities-100/manifest.json")

# Load from JSON string
json_str = '{"fixture_id": "test-100", ...}'
manifest = FixtureManifest.from_json(json_str)

# Access fields
print(f"Fixture: {manifest.fixture_id}")
print(f"Tables: {len(manifest.tables)}")
for table in manifest.tables:
    print(f"  - {table.name}: {table.row_count} rows")
```

---

## Error Types

Custom exception types for fixture operations:

```python
class FixtureError(Exception):
    """Base exception for all fixture operations."""
    pass


class FixtureValidationError(FixtureError):
    """Raised when fixture validation fails."""
    pass


class FixtureLoadError(FixtureError):
    """Raised when fixture loading fails."""
    pass


class FixtureCreateError(FixtureError):
    """Raised when fixture creation fails."""
    pass


class ChecksumMismatchError(FixtureValidationError):
    """Raised when .DAT file checksum doesn't match manifest."""
    pass
```

---

## Schema Versioning

**Current Version**: `"1.0"`

**Versioning Strategy**:
- Major version (e.g., `"2.0"`): Breaking changes to required fields
- Minor version (e.g., `"1.1"`): New optional fields, backward compatible

**Future Versions** (planned):
1. **1.1**: Add optional `compression` field for compressed .DAT files
2. **1.2**: Add optional `dependencies` field for fixture dependencies
3. **2.0**: Add required `iris_edition` field (Community/Enterprise)

**Compatibility**:
- Reader MUST support all 1.x versions (backward compatible)
- Reader MAY reject 2.x versions if not supported
- Unknown optional fields MUST be ignored (forward compatible)

---

## Implementation Checklist

- [ ] Create `iris_devtools/fixtures/manifest.py` with dataclasses
- [ ] Add `__init__.py` exports
- [ ] Write unit tests for serialization/deserialization
- [ ] Write unit tests for validation logic
- [ ] Add type hints to all methods
- [ ] Document all public APIs with docstrings
- [ ] Test with real IRIS .DAT files
- [ ] Verify JSON schema matches examples

---

**Phase 1 Data Model Complete** - Ready for contract generation
