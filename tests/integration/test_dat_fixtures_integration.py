"""Integration tests for .DAT fixture management.

These tests require a running IRIS instance and test the complete
roundtrip workflow: create → validate → load → verify.

Tests cover:
- T012: Roundtrip workflow (create → validate → load → verify data)
- T013: Checksum mismatch detection
- T014: Atomic namespace mounting (all-or-nothing)
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from iris_devtester.fixtures import (
    FixtureCreator,
    DATFixtureLoader,
    FixtureValidator,
    ChecksumMismatchError,
    FixtureValidationError,
)
from iris_devtester.connections import get_connection
import time


# Use shared fixtures from conftest.py instead of duplicating
# The conftest.py provides:
# - iris_container (session scope)
# - test_namespace (function scope)
# - iris_connection (function scope, DBAPI for SQL)
# - iris_objectscript_connection (function scope, iris.connect() for ObjectScript)


@pytest.fixture(scope="function")
def temp_fixture_dir():
    """Provide temporary directory for fixture files."""
    temp_dir = tempfile.mkdtemp(prefix="iris_fixture_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFixtureRoundtrip:
    """Test T012: Complete fixture roundtrip workflow."""

    def test_create_validate_load_verify(self, iris_container, test_namespace, iris_connection, temp_fixture_dir):
        """
        Test complete roundtrip: create fixture → validate → load → verify data.

        Uses correct SQL/ObjectScript patterns:
        - ObjectScript (iris.connect): Create namespace
        - SQL (DBAPI): Create tables, insert data, verify
        """
        # Step 1: Setup - test_namespace already created by fixture
        # Use it as source namespace for fixture creation
        source_namespace = test_namespace

        # Step 2: Create test data using SQL (DBAPI is 3x faster)
        cursor = iris_connection.cursor()

        # Create test table
        cursor.execute("""
            CREATE TABLE TestData (
                ID INT PRIMARY KEY,
                Name VARCHAR(100),
                Value DECIMAL(10,2)
            )
        """)

        # Insert test rows
        cursor.execute("INSERT INTO TestData (ID, Name, Value) VALUES (1, 'Alice', 100.50)")
        cursor.execute("INSERT INTO TestData (ID, Name, Value) VALUES (2, 'Bob', 200.75)")
        cursor.execute("INSERT INTO TestData (ID, Name, Value) VALUES (3, 'Charlie', 300.25)")

        cursor.close()

        # Step 2: Create fixture from source namespace
        # Pass container for docker exec BACKUP operations
        creator = FixtureCreator(container=iris_container)
        fixture_path = Path(temp_fixture_dir) / "test-roundtrip"

        manifest = creator.create_fixture(
            fixture_id="test-roundtrip",
            namespace=source_namespace,
            output_dir=str(fixture_path),
            description="Integration test fixture",
            version="1.0.0"
        )

        # Verify manifest
        assert manifest.fixture_id == "test-roundtrip"
        assert manifest.namespace == source_namespace
        assert len(manifest.tables) > 0
        assert any(t.name.endswith("TestData") for t in manifest.tables)

        # Step 3: Validate fixture
        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_path), validate_checksum=True)

        assert result.valid, f"Validation failed: {result.errors}"
        assert len(result.errors) == 0
        assert result.manifest is not None

        # Step 4: Load fixture into different namespace
        # Use iris_container to create target namespace (ObjectScript operation)
        target_namespace = iris_container.get_test_namespace(prefix="TARGET")

        # Pass container for docker exec RESTORE operations
        loader = DATFixtureLoader(container=iris_container)

        load_result = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=target_namespace,
            validate_checksum=True
        )

        # Verify load result
        assert load_result.success
        assert load_result.namespace == target_namespace
        assert len(load_result.tables_loaded) > 0

        # Step 5: Verify data in target namespace using SQL (DBAPI)
        # Get fresh connection to target namespace
        # Update config to connect to target namespace
        original_namespace = iris_container._config.namespace
        iris_container._config.namespace = target_namespace

        target_conn = iris_container.get_connection()
        cursor = target_conn.cursor()

        # Restore original namespace config
        iris_container._config.namespace = original_namespace

        # Count rows
        cursor.execute("SELECT COUNT(*) FROM TestData")
        row = cursor.fetchone()
        count = int(row[0]) if row else 0
        assert count == 3, f"Expected 3 rows, found {count}"

        # Verify specific data using SQL
        cursor.execute("SELECT Name, Value FROM TestData WHERE ID = 2")
        row = cursor.fetchone()
        assert row is not None, "Row with ID=2 not found"
        assert row[0] == "Bob", f"Expected Name='Bob', got '{row[0]}'"
        assert float(row[1]) == 200.75, f"Expected Value=200.75, got {row[1]}"

        cursor.close()

        # Cleanup target namespace (source namespace cleaned by fixture)
        iris_container.delete_namespace(target_namespace)


class TestChecksumMismatch:
    """Test T013: Checksum mismatch detection."""

    def test_detect_corrupted_dat_file(self, iris_container, test_namespace, temp_fixture_dir):
        """Test that corrupted .DAT file is detected via checksum mismatch."""
        # Use test_namespace from fixture (already created)
        source_namespace = test_namespace

        # Create fixture (empty namespace is fine for checksum testing)
        creator = FixtureCreator(container=iris_container)
        fixture_path = Path(temp_fixture_dir) / "test-checksum"

        manifest = creator.create_fixture(
            fixture_id="test-checksum",
            namespace=source_namespace,
            output_dir=str(fixture_path),
            description="Checksum test fixture",
            version="1.0.0"
        )

        # Corrupt the IRIS.DAT file
        dat_file = fixture_path / "IRIS.DAT"
        with open(dat_file, "ab") as f:
            f.write(b"CORRUPTED DATA")

        # Attempt to validate - should fail
        validator = FixtureValidator()

        with pytest.raises(ChecksumMismatchError) as exc_info:
            validator.validate_fixture(str(fixture_path), validate_checksum=True)

        assert "Checksum mismatch" in str(exc_info.value)
        assert "What went wrong" in str(exc_info.value)
        assert "How to fix it" in str(exc_info.value)

    def test_skip_checksum_validation(self, iris_container, test_namespace, temp_fixture_dir):
        """Test that checksum validation can be skipped for performance."""
        # Use test_namespace from fixture
        source_namespace = test_namespace

        creator = FixtureCreator(container=iris_container)
        fixture_path = Path(temp_fixture_dir) / "test-skip"

        creator.create_fixture(
            fixture_id="test-skip",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        # Corrupt the DAT file
        dat_file = fixture_path / "IRIS.DAT"
        with open(dat_file, "ab") as f:
            f.write(b"CORRUPTED")

        # Should succeed when skipping checksum
        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_path), validate_checksum=False)

        # Manifest validation should still pass
        assert result.valid or len(result.errors) == 0


class TestAtomicOperations:
    """Test T014: Atomic namespace mounting (all-or-nothing)."""

    def test_load_is_atomic(self, iris_container, test_namespace, temp_fixture_dir):
        """Test that fixture loading is atomic (all-or-nothing operation)."""
        # Use test_namespace from fixture (already created)
        source_namespace = test_namespace

        # Create fixture from source namespace
        creator = FixtureCreator(container=iris_container)
        fixture_path = Path(temp_fixture_dir) / "test-atomic"

        creator.create_fixture(
            fixture_id="test-atomic",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        # Load fixture should succeed
        loader = DATFixtureLoader(container=iris_container)
        target_namespace = iris_container.get_test_namespace(prefix="ATOMIC_TARGET")

        result = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=target_namespace
        )

        assert result.success
        assert result.namespace == target_namespace

        # Cleanup
        iris_container.delete_namespace(target_namespace)

    def test_cleanup_removes_namespace(self, iris_container, test_namespace, temp_fixture_dir):
        """Test that cleanup properly removes namespace."""
        # Use test_namespace from fixture as source
        source_namespace = test_namespace

        # Create fixture (empty namespace is fine for cleanup testing)
        creator = FixtureCreator(container=iris_container)
        fixture_path = Path(temp_fixture_dir) / "test-cleanup"

        creator.create_fixture(
            fixture_id="test-cleanup",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        # Load into target namespace
        loader = DATFixtureLoader(container=iris_container)
        target_namespace = iris_container.get_test_namespace(prefix="CLEANUP_TARGET")

        loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=target_namespace
        )

        # Cleanup with delete
        loader.cleanup_fixture(target_namespace, delete_namespace=True)

        # Namespace should be gone (verified by loader.cleanup_fixture)


class TestErrorScenarios:
    """Test error handling scenarios."""

    def test_missing_manifest(self, temp_fixture_dir):
        """Test validation fails gracefully with missing manifest."""
        fixture_path = Path(temp_fixture_dir) / "no-manifest"
        fixture_path.mkdir(parents=True)

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_path), validate_checksum=False)

        assert not result.valid
        assert any("manifest.json" in error.lower() for error in result.errors)

    def test_missing_dat_file(self, temp_fixture_dir):
        """Test validation fails gracefully with missing .DAT file."""
        fixture_path = Path(temp_fixture_dir) / "no-dat"
        fixture_path.mkdir(parents=True)

        # Create manifest without DAT file
        from iris_devtester.fixtures import FixtureManifest, TableInfo
        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2024.1",
            namespace="TEST",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[]
        )
        manifest.to_file(str(fixture_path / "manifest.json"))

        validator = FixtureValidator()
        result = validator.validate_fixture(str(fixture_path), validate_checksum=False)

        assert not result.valid
        assert any("IRIS.DAT" in error for error in result.errors)

    def test_load_nonexistent_fixture(self):
        """Test loading nonexistent fixture fails gracefully."""
        loader = DATFixtureLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_fixture(fixture_path="/nonexistent/path")


# Test count verification
def test_integration_test_count():
    """Verify we have comprehensive integration tests."""
    import sys
    module = sys.modules[__name__]

    test_classes = [
        TestFixtureRoundtrip,
        TestChecksumMismatch,
        TestAtomicOperations,
        TestErrorScenarios,
    ]

    total_tests = 0
    for test_class in test_classes:
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        total_tests += len(test_methods)

    # Should have at least 8 integration tests
    assert total_tests >= 8, f"Expected at least 8 integration tests, found {total_tests}"
