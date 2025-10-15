"""Fixture manifest data models and validation.

This module defines the data structures for IRIS .DAT fixture manifests,
including FixtureManifest, TableInfo, ValidationResult, and LoadResult.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


# Custom Exceptions
class FixtureError(Exception):
    """Base exception for fixture operations."""
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
    """Raised when file checksum doesn't match manifest."""
    pass


@dataclass
class TableInfo:
    """
    Information about a single table in a fixture.

    Note: All tables are stored in a single IRIS.DAT file.
    This class tracks which tables are included in the fixture.

    Attributes:
        name: Qualified table name (e.g., "RAG.Entities")
        row_count: Number of rows exported (for validation)
    """

    name: str  # Qualified table name (e.g., "RAG.Entities")
    row_count: int  # Number of rows exported (for validation)

    def __str__(self) -> str:
        return f"{self.name} ({self.row_count} rows)"

    def __post_init__(self):
        """Validate fields after initialization."""
        if self.row_count < 0:
            raise ValueError(f"row_count must be non-negative, got {self.row_count}")


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
    tables: List[TableInfo]  # List of tables included in this fixture

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
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r") as f:
            return cls.from_json(f.read())

    def to_file(self, manifest_path: str) -> None:
        """
        Save manifest to file.

        Args:
            manifest_path: Path to manifest.json file
        """
        path = Path(manifest_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(manifest_path, "w") as f:
            f.write(self.to_json())

    def validate(self) -> "ValidationResult":
        """
        Validate manifest structure and contents.

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        # Validate required fields
        if not self.fixture_id:
            errors.append("fixture_id is empty")
        if not self.version:
            errors.append("version is empty")
        if self.schema_version != "1.0":
            warnings.append(f"schema_version '{self.schema_version}' may not be supported")
        if not self.namespace:
            errors.append("namespace is empty")
        if not self.dat_file:
            errors.append("dat_file is empty")
        elif self.dat_file != "IRIS.DAT":
            warnings.append(f"dat_file '{self.dat_file}' should typically be 'IRIS.DAT'")
        if not self.checksum:
            errors.append("checksum is empty")
        elif not self.checksum.startswith("sha256:"):
            errors.append("checksum must start with 'sha256:'")
        if not self.tables:
            errors.append("tables list is empty")

        # Validate table names are unique
        table_names = [t.name for t in self.tables]
        if len(table_names) != len(set(table_names)):
            errors.append("Duplicate table names found")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            manifest=self
        )


@dataclass
class ValidationResult:
    """
    Result of fixture validation.

    Attributes:
        valid: True if validation passed
        errors: List of error messages
        warnings: List of warning messages
        manifest: The manifest that was validated (if available)
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manifest: Optional[FixtureManifest] = None

    def raise_if_invalid(self) -> None:
        """
        Raise FixtureValidationError if validation failed.

        Raises:
            FixtureValidationError: If valid is False
        """
        if not self.valid:
            error_msg = "Fixture validation failed:\n"
            for error in self.errors:
                error_msg += f"  - {error}\n"
            raise FixtureValidationError(error_msg.strip())

    def __str__(self) -> str:
        if self.valid:
            msg = "✅ Validation passed"
            if self.warnings:
                msg += f"\nWarnings ({len(self.warnings)}):"
                for warning in self.warnings:
                    msg += f"\n  - {warning}"
            return msg
        else:
            msg = f"❌ Validation failed ({len(self.errors)} errors"
            if self.warnings:
                msg += f", {len(self.warnings)} warnings"
            msg += ")"
            for error in self.errors:
                msg += f"\n  - {error}"
            if self.warnings:
                msg += "\nWarnings:"
                for warning in self.warnings:
                    msg += f"\n  - {warning}"
            return msg


@dataclass
class LoadResult:
    """
    Result of fixture loading operation.

    Attributes:
        success: True if loading succeeded
        manifest: The loaded fixture manifest
        namespace: Target namespace where fixture was loaded
        tables_loaded: List of table names that were loaded
        elapsed_seconds: Time taken to load fixture
    """

    success: bool
    manifest: FixtureManifest
    namespace: str
    tables_loaded: List[str]
    elapsed_seconds: float

    def __str__(self) -> str:
        if self.success:
            return (
                f"✅ Fixture loaded: {self.manifest.fixture_id}\n"
                f"Namespace: {self.namespace}\n"
                f"Tables: {len(self.tables_loaded)}\n"
                f"Time: {self.elapsed_seconds:.2f}s"
            )
        else:
            return f"❌ Fixture load failed: {self.manifest.fixture_id}"

    def summary(self) -> str:
        """
        Get detailed summary of load operation.

        Returns:
            Detailed summary string
        """
        summary = str(self)
        if self.success and self.tables_loaded:
            summary += "\n\nTables loaded:"
            for table_name in self.tables_loaded:
                # Find row count from manifest
                table_info = next((t for t in self.manifest.tables if t.name == table_name), None)
                if table_info:
                    summary += f"\n  - {table_info}"
                else:
                    summary += f"\n  - {table_name}"
        return summary
