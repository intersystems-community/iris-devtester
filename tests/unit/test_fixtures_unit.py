"""Unit tests for fixture modules (loader, creator, validator).

Tests cover:
- FixtureLoader: instantiation, load methods, validation
- FixtureCreator: instantiation, create operations
- FixtureValidator: checksum validation, manifest validation, fixture validation
- Pure unit tests (no Docker/IRIS required)
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.fixtures.loader import FixtureLoader
from iris_devtester.fixtures.creator import FixtureCreator
from iris_devtester.fixtures.validator import FixtureValidator
from iris_devtester.fixtures.manifest import (
    ChecksumMismatchError,
    FixtureCreateError,
    FixtureLoadError,
    FixtureManifest,
    FixtureValidationError,
    TableInfo,
    ValidationResult,
)


class TestFixtureValidator:
    """Test FixtureValidator class."""

    def test_instantiation(self):
        """Test that FixtureValidator can be instantiated."""
        validator = FixtureValidator()
        assert validator is not None

    def test_calculate_sha256_valid_file(self, tmp_path):
        """Test calculating SHA256 for a valid file."""
        # Create a test file with known content
        test_file = tmp_path / "test.txt"
        test_content = b"test content"
        test_file.write_bytes(test_content)

        validator = FixtureValidator()
        checksum = validator.calculate_sha256(str(test_file))

        # Verify format
        assert checksum.startswith("sha256:")
        # Verify it matches expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()
        assert checksum == f"sha256:{expected_hash}"

    def test_calculate_sha256_nonexistent_file(self):
        """Test that calculating SHA256 for nonexistent file raises FileNotFoundError."""
        validator = FixtureValidator()

        with pytest.raises(FileNotFoundError, match="not found"):
            validator.calculate_sha256("/nonexistent/file.txt")

    def test_validate_checksum_match(self, tmp_path):
        """Test checksum validation with matching checksum."""
        test_file = tmp_path / "test.txt"
        test_content = b"test data"
        test_file.write_bytes(test_content)

        validator = FixtureValidator()
        expected_checksum = f"sha256:{hashlib.sha256(test_content).hexdigest()}"

        # Should not raise
        result = validator.validate_checksum(str(test_file), expected_checksum)
        assert result is True

    def test_validate_checksum_mismatch(self, tmp_path):
        """Test checksum validation with mismatched checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test data")

        validator = FixtureValidator()
        wrong_checksum = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

        with pytest.raises(ChecksumMismatchError, match="Checksum mismatch"):
            validator.validate_checksum(str(test_file), wrong_checksum)

    def test_validate_checksum_invalid_format(self, tmp_path):
        """Test checksum validation with invalid checksum format."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test data")

        validator = FixtureValidator()

        with pytest.raises(ValueError, match="Invalid checksum format"):
            validator.validate_checksum(str(test_file), "invalid_checksum")

    def test_validate_fixture_directory_not_found(self):
        """Test validating fixture from nonexistent directory."""
        validator = FixtureValidator()

        with pytest.raises(FileNotFoundError, match="not found"):
            validator.validate_fixture("/nonexistent/fixture")

    def test_validate_fixture_not_directory(self, tmp_path):
        """Test validating fixture path that is not a directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        validator = FixtureValidator()
        result = validator.validate_fixture(str(test_file))

        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_fixture_missing_manifest(self, tmp_path):
        """Test validating fixture without manifest.json."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_dir))

        assert result.valid is False
        assert "manifest.json not found" in result.errors

    def test_validate_fixture_invalid_manifest(self, tmp_path):
        """Test validating fixture with invalid manifest JSON."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        manifest_file = fixture_dir / "manifest.json"
        manifest_file.write_text("{ invalid json }")

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_dir))

        assert result.valid is False
        # Check that there's an error about manifest loading
        assert any("Failed to load manifest" in error for error in result.errors)

    def test_validate_fixture_missing_dat_file(self, tmp_path):
        """Test validating fixture without IRIS.DAT file."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create valid manifest pointing to missing DAT file
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_dir), validate_checksum=False)

        assert result.valid is False
        assert "IRIS.DAT not found" in result.errors

    def test_validate_fixture_checksum_skip(self, tmp_path):
        """Test validating fixture without checksum verification."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create manifest
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:invalid",
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        # Create DAT file
        dat_file = fixture_dir / "IRIS.DAT"
        dat_file.write_bytes(b"test data")

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_dir), validate_checksum=False)

        # Should succeed because we skipped checksum validation
        assert result.valid is True

    def test_validate_fixture_valid(self, tmp_path):
        """Test validating a completely valid fixture."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create DAT file and calculate its checksum
        dat_file = fixture_dir / "IRIS.DAT"
        dat_content = b"test fixture data"
        dat_file.write_bytes(dat_content)
        checksum = f"sha256:{hashlib.sha256(dat_content).hexdigest()}"

        # Create manifest with correct checksum
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=checksum,
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_dir), validate_checksum=True)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_recalculate_checksums(self, tmp_path):
        """Test recalculating checksums in manifest."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create DAT file
        dat_file = fixture_dir / "IRIS.DAT"
        dat_content = b"test fixture data"
        dat_file.write_bytes(dat_content)

        # Create manifest with old checksum
        old_checksum = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=old_checksum,
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        validator = FixtureValidator()
        updated_manifest = validator.recalculate_checksums(str(fixture_dir), create_backup=False)

        # Verify checksum was updated
        expected_checksum = f"sha256:{hashlib.sha256(dat_content).hexdigest()}"
        assert updated_manifest.checksum == expected_checksum
        assert updated_manifest.checksum != old_checksum

    def test_get_fixture_size(self, tmp_path):
        """Test getting fixture size statistics."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create DAT file with known size
        dat_file = fixture_dir / "IRIS.DAT"
        dat_content = b"x" * 1024  # 1KB
        dat_file.write_bytes(dat_content)

        # Create manifest
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        validator = FixtureValidator()
        sizes = validator.get_fixture_size(str(fixture_dir))

        assert "total_bytes" in sizes
        assert "manifest_bytes" in sizes
        assert "dat_bytes" in sizes
        assert sizes["dat_bytes"] == 1024
        assert sizes["total_mb"] > 0

    def test_validate_manifest(self, tmp_path):
        """Test validating manifest structure."""
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )

        validator = FixtureValidator()
        result = validator.validate_manifest(manifest)

        assert result.valid is True
        assert len(result.errors) == 0


class TestFixtureLoader:
    """Test FixtureLoader class."""

    def test_instantiation_no_container(self):
        """Test FixtureLoader instantiation without container."""
        loader = FixtureLoader()
        assert loader is not None
        assert loader.container is None

    def test_instantiation_with_container(self):
        """Test FixtureLoader instantiation with container."""
        mock_container = MagicMock()
        loader = FixtureLoader(container=mock_container)
        assert loader.container is mock_container

    def test_instantiation_with_connection_config(self):
        """Test FixtureLoader instantiation with connection config."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        loader = FixtureLoader(connection_config=config)
        assert loader.connection_config is config

    def test_validate_fixture_calls_validator(self, tmp_path):
        """Test that validate_fixture delegates to FixtureValidator."""
        # Create a valid fixture directory
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        dat_file = fixture_dir / "IRIS.DAT"
        dat_content = b"test data"
        dat_file.write_bytes(dat_content)

        checksum = f"sha256:{hashlib.sha256(dat_content).hexdigest()}"
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=checksum,
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        loader = FixtureLoader()
        result_manifest = loader.validate_fixture(str(fixture_dir), validate_checksum=True)

        assert result_manifest.fixture_id == "test-fixture"

    def test_validate_fixture_invalid_raises_error(self):
        """Test that validate_fixture raises on invalid fixture."""
        loader = FixtureLoader()

        # validate_fixture can raise FileNotFoundError or FixtureValidationError
        with pytest.raises((FixtureValidationError, FileNotFoundError)):
            loader.validate_fixture("/nonexistent/fixture")

    def test_load_manifest_success(self, tmp_path):
        """Test loading a valid manifest."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        loader = FixtureLoader()
        loaded = loader._load_manifest(str(fixture_dir))

        assert loaded.fixture_id == "test-fixture"
        assert loaded.namespace == "USER"

    def test_load_manifest_missing_raises_error(self, tmp_path):
        """Test that loading missing manifest raises error."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        loader = FixtureLoader()

        with pytest.raises(FixtureLoadError, match="Manifest not found"):
            loader._load_manifest(str(fixture_dir))

    def test_cleanup_fixture_requires_namespace(self):
        """Test that cleanup_fixture requires namespace."""
        loader = FixtureLoader()

        with pytest.raises(ValueError, match="Namespace is required"):
            loader.cleanup_fixture("")

    def test_cleanup_fixture_requires_container(self):
        """Test that cleanup_fixture requires container."""
        loader = FixtureLoader()

        with pytest.raises(RuntimeError, match="IRIS container required"):
            loader.cleanup_fixture("TEST_NS")

    @patch("iris_devtester.fixtures.loader.IRISContainer")
    def test_cleanup_fixture_calls_container(self, mock_container_class):
        """Test that cleanup_fixture delegates to container."""
        mock_container = MagicMock()
        loader = FixtureLoader(container=mock_container)

        loader.cleanup_fixture("TEST_NS", delete_namespace=True)

        mock_container.delete_namespace.assert_called_once_with("TEST_NS")

    def test_get_connection_requires_config_or_container(self):
        """Test that get_connection works with connection_config or container."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        loader = FixtureLoader(connection_config=config)

        # Mock the imported function at its source
        with patch(
            "iris_devtester.connections.connection.get_connection"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            result = loader.get_connection()
            assert result is mock_conn


class TestFixtureCreator:
    """Test FixtureCreator class."""

    def test_instantiation(self):
        """Test FixtureCreator instantiation."""
        creator = FixtureCreator()
        assert creator is not None

    def test_instantiation_with_config(self):
        """Test FixtureCreator instantiation with connection config."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        creator = FixtureCreator(connection_config=config)
        assert creator.connection_config is config

    def test_instantiation_with_container(self):
        """Test FixtureCreator instantiation with container."""
        mock_container = MagicMock()
        creator = FixtureCreator(container=mock_container)
        assert creator.container is mock_container

    def test_create_fixture_output_dir_exists_raises_error(self, tmp_path):
        """Test that create_fixture raises if output directory exists."""
        output_dir = tmp_path / "fixture"
        output_dir.mkdir()

        creator = FixtureCreator()

        with pytest.raises(FileExistsError, match="already exists"):
            creator.create_fixture(
                fixture_id="test",
                namespace="USER",
                output_dir=str(output_dir),
            )

    def test_create_fixture_requires_container(self, tmp_path):
        """Test that create_fixture requires container for export."""
        output_dir = tmp_path / "fixture"

        creator = FixtureCreator()

        with pytest.raises(FixtureCreateError, match="container parameter"):
            creator.create_fixture(
                fixture_id="test",
                namespace="USER",
                output_dir=str(output_dir),
            )

    def test_export_namespace_to_dat_requires_container(self, tmp_path):
        """Test that export_namespace_to_dat requires container."""
        creator = FixtureCreator()

        with pytest.raises(FixtureCreateError, match="container parameter"):
            creator.export_namespace_to_dat("USER", str(tmp_path / "test.dat"))

    def test_calculate_checksum(self, tmp_path):
        """Test calculate_checksum delegates to validator."""
        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test content")

        creator = FixtureCreator()
        checksum = creator.calculate_checksum(str(test_file))

        assert checksum.startswith("sha256:")

    def test_get_connection(self):
        """Test get_connection with config."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        creator = FixtureCreator(connection_config=config)

        # Patch at the import location within creator
        with patch(
            "iris_devtester.fixtures.creator.FixtureCreator.get_connection"
        ) as mock_method:
            mock_conn = MagicMock()
            # First call returns mock, second call returns it too
            type(mock_method).return_value = mock_conn

            # Test through get_connection directly
            assert creator._connection is None
            # This will use real implementation
            # Just verify the function exists and is callable
            assert callable(creator.get_connection)

    def test_get_namespace_tables_requires_connection(self):
        """Test get_namespace_tables with mock connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("USER", "Table1"),
            ("USER", "Table2"),
        ]

        # Mock row count queries
        mock_cursor.fetchone.side_effect = [(10,), (20,)]

        creator = FixtureCreator()
        tables = creator.get_namespace_tables(connection=mock_conn, namespace="USER")

        assert len(tables) == 2
        assert tables[0].name == "USER.Table1"
        assert tables[0].row_count == 10

    def test_get_iris_version_with_connection(self):
        """Test get_iris_version."""
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        creator = FixtureCreator(connection_config=config)

        with patch(
            "iris_devtester.fixtures.creator.FixtureCreator.get_connection"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = ("2025.1",)
            mock_get_conn.return_value = mock_conn

            version = creator._get_iris_version()

            assert version == "2025.1"

    def test_get_iris_version_fallback_on_error(self):
        """Test get_iris_version returns 'unknown' on error."""
        creator = FixtureCreator()

        with patch(
            "iris_devtester.fixtures.creator.FixtureCreator.get_connection"
        ) as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            version = creator._get_iris_version()

            assert version == "unknown"


class TestTableInfo:
    """Test TableInfo dataclass."""

    def test_instantiation(self):
        """Test creating TableInfo."""
        table = TableInfo(name="USER.TestTable", row_count=100)
        assert table.name == "USER.TestTable"
        assert table.row_count == 100

    def test_str_representation(self):
        """Test string representation of TableInfo."""
        table = TableInfo(name="USER.TestTable", row_count=100)
        assert str(table) == "USER.TestTable (100 rows)"

    def test_negative_row_count_raises_error(self):
        """Test that negative row count raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            TableInfo(name="USER.TestTable", row_count=-1)


class TestFixtureManifestSerialization:
    """Test FixtureManifest JSON serialization."""

    def test_to_json(self):
        """Test serializing manifest to JSON."""
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test fixture",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="User.Table", row_count=50)],
        )

        json_str = manifest.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["fixture_id"] == "test-fixture"
        assert len(data["tables"]) == 1

    def test_from_json(self):
        """Test deserializing manifest from JSON."""
        json_str = """{
            "fixture_id": "test-fixture",
            "version": "1.0.0",
            "schema_version": "1.0",
            "description": "Test",
            "created_at": "2025-01-01T00:00:00Z",
            "iris_version": "2025.1",
            "namespace": "USER",
            "dat_file": "IRIS.DAT",
            "checksum": "sha256:abc123",
            "tables": [{"name": "User.Table", "row_count": 50}]
        }"""

        manifest = FixtureManifest.from_json(json_str)

        assert manifest.fixture_id == "test-fixture"
        assert len(manifest.tables) == 1
        assert manifest.tables[0].name == "User.Table"

    def test_from_json_invalid(self):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            FixtureManifest.from_json("{ invalid json }")

    def test_from_file(self, tmp_path):
        """Test loading manifest from file."""
        manifest_file = tmp_path / "manifest.json"
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="User.Table", row_count=50)],
        )
        manifest.to_file(str(manifest_file))

        loaded = FixtureManifest.from_file(str(manifest_file))
        assert loaded.fixture_id == "test-fixture"

    def test_to_file_and_from_file_roundtrip(self, tmp_path):
        """Test complete roundtrip: to_file and from_file."""
        manifest_file = tmp_path / "manifest.json"
        original = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test fixture",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123def456",
            tables=[
                TableInfo(name="User.Table1", row_count=100),
                TableInfo(name="User.Table2", row_count=200),
            ],
        )

        original.to_file(str(manifest_file))
        loaded = FixtureManifest.from_file(str(manifest_file))

        assert loaded.fixture_id == original.fixture_id
        assert loaded.checksum == original.checksum
        assert len(loaded.tables) == 2


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid ValidationResult."""
        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[],
        )
        result = ValidationResult(valid=True, manifest=manifest)

        assert result.valid is True
        assert result.manifest is manifest

    def test_invalid_result_with_errors(self):
        """Test creating an invalid ValidationResult with errors."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
        )

        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_raise_if_invalid_with_valid_result(self):
        """Test raise_if_invalid doesn't raise for valid result."""
        result = ValidationResult(valid=True)
        # Should not raise
        result.raise_if_invalid()

    def test_raise_if_invalid_with_invalid_result(self):
        """Test raise_if_invalid raises for invalid result."""
        result = ValidationResult(valid=False, errors=["Error 1"])

        with pytest.raises(FixtureValidationError):
            result.raise_if_invalid()

    def test_str_representation_valid(self):
        """Test string representation of valid result."""
        result = ValidationResult(valid=True)
        str_repr = str(result)
        assert "Validation passed" in str_repr or "✅" in str_repr

    def test_str_representation_invalid(self):
        """Test string representation of invalid result."""
        result = ValidationResult(valid=False, errors=["Error 1"])
        str_repr = str(result)
        assert "Validation failed" in str_repr or "❌" in str_repr
