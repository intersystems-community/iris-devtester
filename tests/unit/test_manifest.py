"""
Unit tests for manifest data models.

Tests cover:
- FixtureManifest serialization/deserialization
- TableInfo validation
- ValidationResult error handling
- LoadResult string representations
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime


class TestTableInfo:
    """Unit tests for TableInfo dataclass."""

    def test_create_with_valid_data(self):
        """Test creating TableInfo with valid data."""
        from iris_devtester.fixtures import TableInfo

        table = TableInfo(name="RAG.Entities", row_count=100)

        assert table.name == "RAG.Entities"
        assert table.row_count == 100

    def test_str_representation(self):
        """Test TableInfo string representation."""
        from iris_devtester.fixtures import TableInfo

        table = TableInfo(name="RAG.Entities", row_count=100)
        result = str(table)

        assert "RAG.Entities" in result
        assert "100 rows" in result

    def test_rejects_negative_row_count(self):
        """Test that TableInfo rejects negative row_count."""
        from iris_devtester.fixtures import TableInfo

        with pytest.raises(ValueError) as exc_info:
            TableInfo(name="Test.Table", row_count=-1)

        assert "non-negative" in str(exc_info.value)

    def test_accepts_zero_row_count(self):
        """Test that TableInfo accepts zero row_count (empty table)."""
        from iris_devtester.fixtures import TableInfo

        table = TableInfo(name="Empty.Table", row_count=0)
        assert table.row_count == 0


class TestFixtureManifestSerialization:
    """Unit tests for FixtureManifest JSON serialization."""

    def test_to_json_basic(self):
        """Test basic manifest serialization to JSON."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test fixture",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        json_str = manifest.to_json()
        data = json.loads(json_str)

        assert data["fixture_id"] == "test-fixture"
        assert data["version"] == "1.0.0"
        assert data["namespace"] == "USER"
        assert data["checksum"] == "sha256:abc123"
        assert len(data["tables"]) == 1
        assert data["tables"][0]["name"] == "Test.Table"
        assert data["tables"][0]["row_count"] == 100

    def test_to_json_with_optional_fields(self):
        """Test manifest serialization with optional fields."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[],
            features={"use_case": "testing", "dataset": "sample"},
            known_queries=[{"name": "find_all", "sql": "SELECT * FROM Test"}]
        )

        json_str = manifest.to_json()
        data = json.loads(json_str)

        assert data["features"]["use_case"] == "testing"
        assert data["known_queries"][0]["name"] == "find_all"

    def test_to_json_custom_indent(self):
        """Test manifest serialization with custom indentation."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[]
        )

        json_str = manifest.to_json(indent=4)
        # Should have 4-space indentation
        assert "    " in json_str


class TestFixtureManifestDeserialization:
    """Unit tests for FixtureManifest JSON deserialization."""

    def test_from_json_basic(self):
        """Test basic manifest deserialization from JSON."""
        from iris_devtester.fixtures import FixtureManifest

        json_str = """
        {
            "fixture_id": "test-fixture",
            "version": "1.0.0",
            "schema_version": "1.0",
            "description": "Test fixture",
            "created_at": "2025-10-14T00:00:00Z",
            "iris_version": "2024.1",
            "namespace": "USER",
            "dat_file": "IRIS.DAT",
            "checksum": "sha256:abc123",
            "tables": [
                {"name": "Test.Table", "row_count": 100}
            ]
        }
        """

        manifest = FixtureManifest.from_json(json_str)

        assert manifest.fixture_id == "test-fixture"
        assert manifest.version == "1.0.0"
        assert manifest.namespace == "USER"
        assert len(manifest.tables) == 1
        assert manifest.tables[0].name == "Test.Table"

    def test_from_json_invalid_json(self):
        """Test that from_json raises ValueError for invalid JSON."""
        from iris_devtester.fixtures import FixtureManifest

        with pytest.raises(ValueError) as exc_info:
            FixtureManifest.from_json("not valid json{")

        assert "Invalid JSON" in str(exc_info.value)

    def test_from_json_missing_required_field(self):
        """Test that from_json raises ValueError for missing required fields."""
        from iris_devtester.fixtures import FixtureManifest

        json_str = """
        {
            "fixture_id": "test",
            "version": "1.0.0"
        }
        """

        with pytest.raises(ValueError) as exc_info:
            FixtureManifest.from_json(json_str)

        assert "Missing required field" in str(exc_info.value)

    def test_roundtrip_serialization(self):
        """Test that serialization -> deserialization preserves data."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        original = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[
                TableInfo(name="Table1", row_count=100),
                TableInfo(name="Table2", row_count=200)
            ]
        )

        json_str = original.to_json()
        restored = FixtureManifest.from_json(json_str)

        assert restored.fixture_id == original.fixture_id
        assert restored.version == original.version
        assert restored.namespace == original.namespace
        assert len(restored.tables) == len(original.tables)
        assert restored.tables[0].name == original.tables[0].name
        assert restored.tables[1].row_count == original.tables[1].row_count


class TestFixtureManifestFileOperations:
    """Unit tests for FixtureManifest file I/O."""

    def test_to_file_creates_file(self):
        """Test that to_file creates manifest.json file."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest.to_file(str(manifest_path))

            assert manifest_path.exists()
            assert manifest_path.is_file()

    def test_to_file_creates_parent_dirs(self):
        """Test that to_file creates parent directories if needed."""
        from iris_devtester.fixtures import FixtureManifest

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "nested" / "dirs" / "manifest.json"
            manifest.to_file(str(manifest_path))

            assert manifest_path.exists()

    def test_from_file_reads_manifest(self):
        """Test that from_file reads manifest from disk."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        original = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            original.to_file(str(manifest_path))

            loaded = FixtureManifest.from_file(str(manifest_path))

            assert loaded.fixture_id == original.fixture_id
            assert loaded.tables[0].name == original.tables[0].name

    def test_from_file_missing_file_raises_error(self):
        """Test that from_file raises FileNotFoundError for missing file."""
        from iris_devtester.fixtures import FixtureManifest

        with pytest.raises(FileNotFoundError):
            FixtureManifest.from_file("/nonexistent/manifest.json")


class TestFixtureManifestValidation:
    """Unit tests for FixtureManifest validation."""

    def test_validate_valid_manifest(self):
        """Test validation of valid manifest."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        result = manifest.validate()

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_empty_fixture_id(self):
        """Test validation catches empty fixture_id."""
        from iris_devtester.fixtures import FixtureManifest

        manifest = FixtureManifest(
            fixture_id="",  # Empty
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[]
        )

        result = manifest.validate()

        assert result.valid is False
        assert any("fixture_id" in err for err in result.errors)

    def test_validate_invalid_checksum_format(self):
        """Test validation catches invalid checksum format."""
        from iris_devtester.fixtures import FixtureManifest

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="invalid_checksum",  # Missing sha256: prefix
            tables=[]
        )

        result = manifest.validate()

        assert result.valid is False
        assert any("checksum" in err for err in result.errors)

    def test_validate_duplicate_table_names(self):
        """Test validation catches duplicate table names."""
        from iris_devtester.fixtures import FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[
                TableInfo(name="Test.Table", row_count=100),
                TableInfo(name="Test.Table", row_count=200)  # Duplicate
            ]
        )

        result = manifest.validate()

        assert result.valid is False
        assert any("Duplicate" in err for err in result.errors)


class TestValidationResult:
    """Unit tests for ValidationResult dataclass."""

    def test_create_valid_result(self):
        """Test creating valid ValidationResult."""
        from iris_devtester.fixtures import ValidationResult

        result = ValidationResult(valid=True, errors=[], warnings=[])

        assert result.valid is True
        assert len(result.errors) == 0

    def test_create_invalid_result(self):
        """Test creating invalid ValidationResult."""
        from iris_devtester.fixtures import ValidationResult

        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )

        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_raise_if_invalid_raises_on_invalid(self):
        """Test that raise_if_invalid raises error for invalid result."""
        from iris_devtester.fixtures import ValidationResult, FixtureValidationError

        result = ValidationResult(valid=False, errors=["Test error"])

        with pytest.raises(FixtureValidationError) as exc_info:
            result.raise_if_invalid()

        assert "Test error" in str(exc_info.value)

    def test_raise_if_invalid_no_raise_on_valid(self):
        """Test that raise_if_invalid doesn't raise for valid result."""
        from iris_devtester.fixtures import ValidationResult

        result = ValidationResult(valid=True)

        # Should not raise
        result.raise_if_invalid()

    def test_str_representation_valid(self):
        """Test ValidationResult string for valid result."""
        from iris_devtester.fixtures import ValidationResult

        result = ValidationResult(valid=True, warnings=["Minor issue"])
        result_str = str(result)

        assert "✅" in result_str or "Validation passed" in result_str

    def test_str_representation_invalid(self):
        """Test ValidationResult string for invalid result."""
        from iris_devtester.fixtures import ValidationResult

        result = ValidationResult(valid=False, errors=["Error 1"])
        result_str = str(result)

        assert "❌" in result_str or "failed" in result_str.lower()


class TestLoadResult:
    """Unit tests for LoadResult dataclass."""

    def test_create_successful_result(self):
        """Test creating successful LoadResult."""
        from iris_devtester.fixtures import LoadResult, FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        result = LoadResult(
            success=True,
            manifest=manifest,
            namespace="USER",
            tables_loaded=["Test.Table"],
            elapsed_seconds=1.5
        )

        assert result.success is True
        assert result.namespace == "USER"
        assert len(result.tables_loaded) == 1
        assert result.elapsed_seconds == 1.5

    def test_str_representation_success(self):
        """Test LoadResult string for successful load."""
        from iris_devtester.fixtures import LoadResult, FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[]
        )

        result = LoadResult(
            success=True,
            manifest=manifest,
            namespace="USER",
            tables_loaded=[],
            elapsed_seconds=1.0
        )

        result_str = str(result)

        assert "✅" in result_str or "Fixture loaded" in result_str
        assert "USER" in result_str
        assert "1.00s" in result_str or "1.0" in result_str

    def test_summary_includes_table_info(self):
        """Test that summary includes table information."""
        from iris_devtester.fixtures import LoadResult, FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        result = LoadResult(
            success=True,
            manifest=manifest,
            namespace="USER",
            tables_loaded=["Test.Table"],
            elapsed_seconds=1.0
        )

        summary = result.summary()

        assert "Test.Table" in summary
        assert "100 rows" in summary
