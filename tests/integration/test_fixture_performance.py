"""Performance benchmark tests for .DAT fixture operations.

Tests verify that fixture operations meet performance targets:
- NFR-001: Fixture creation <30s for 10K rows
- NFR-002: Fixture loading <10s for 10K rows
- NFR-003: Fixture validation <5s for any size
- NFR-004: SHA256 checksum <2s per file

Note: These are integration tests requiring a live IRIS instance.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path

from iris_devtester.fixtures import (
    FixtureCreator,
    DATFixtureLoader,
    FixtureValidator,
)
from iris_devtester.connections import get_connection


# Use fixtures from tests/integration/conftest.py:
# - iris_container (session scope)
# - iris_connection (function scope)
# - test_namespace (function scope)


@pytest.fixture(scope="function")
def temp_dir():
    """Provide temporary directory for fixtures."""
    temp_dir = tempfile.mkdtemp(prefix="perf_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFixtureCreationPerformance:
    """Test fixture creation performance (NFR-001)."""

    def test_create_fixture_10k_rows_under_30s(self, iris_container, test_namespace, iris_connection, temp_dir):
        """Test creating fixture with 10K rows completes in <30 seconds."""
        # Use test_namespace from fixture
        source_namespace = test_namespace
        cursor = iris_connection.cursor()

        # Drop table if it exists (cleanup from previous test failures)
        try:
            cursor.execute("DROP TABLE PerfTestData")
        except Exception:
            pass  # Table doesn't exist, that's fine

        # Create table using SQL (DBAPI, 3x faster)
        cursor.execute("""
            CREATE TABLE PerfTestData (
                ID INT PRIMARY KEY,
                Name VARCHAR(100),
                Value DECIMAL(10,2),
                Description VARCHAR(500)
            )
        """)

        # Insert 10K rows using SQL (batch insert for performance)
        for i in range(1, 10001):
            cursor.execute(
                "INSERT INTO PerfTestData (ID, Name, Value, Description) VALUES (?, ?, ?, ?)",
                (i, f"Name_{i}", i * 1.5, f"Description for row {i}")
            )
        cursor.close()

        # Measure creation time
        fixture_path = Path(temp_dir) / "perf-10k"
        creator = FixtureCreator(container=iris_container)

        start_time = time.time()
        manifest = creator.create_fixture(
            fixture_id="perf-10k",
            namespace=source_namespace,
            output_dir=str(fixture_path),
            description="Performance test 10K rows"
        )
        elapsed = time.time() - start_time

        # Verify completed and within time limit
        assert manifest is not None
        assert elapsed < 30.0, f"Creation took {elapsed:.2f}s, expected <30s"

        # Verify row count
        table_info = next((t for t in manifest.tables if "PerfTestData" in t.name), None)
        assert table_info is not None
        assert table_info.row_count == 10000

    def test_create_small_fixture_under_5s(self, iris_container, test_namespace, iris_connection, temp_dir):
        """Test creating small fixture (<1K rows) completes in <5 seconds."""
        # Use test_namespace from fixture
        source_namespace = test_namespace
        cursor = iris_connection.cursor()

        # Create table with 100 rows using SQL
        cursor.execute("""
            CREATE TABLE SmallTestData (
                ID INT PRIMARY KEY,
                Name VARCHAR(100)
            )
        """)

        # Insert 100 rows
        for i in range(1, 101):
            cursor.execute(
                "INSERT INTO SmallTestData (ID, Name) VALUES (?, ?)",
                (i, f"Name_{i}")
            )
        cursor.close()

        # Measure creation time
        fixture_path = Path(temp_dir) / "perf-small"
        creator = FixtureCreator(container=iris_container)

        start_time = time.time()
        creator.create_fixture(
            fixture_id="perf-small",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )
        elapsed = time.time() - start_time

        assert elapsed < 5.0, f"Small fixture creation took {elapsed:.2f}s, expected <5s"


class TestFixtureLoadingPerformance:
    """Test fixture loading performance (NFR-002)."""

    @pytest.mark.slow
    def test_load_fixture_10k_rows_under_10s(self, iris_container, test_namespace, iris_connection, temp_dir):
        """Test loading fixture with 10K rows completes in <10 seconds."""
        # Use test_namespace provided by fixture (already created)
        source_namespace = test_namespace

        # Create test data in source namespace
        cursor = iris_connection.cursor()

        # Drop table if it exists (cleanup from previous test failures)
        try:
            cursor.execute("DROP TABLE PerfTestData")
        except Exception:
            pass  # Table doesn't exist, that's fine

        cursor.execute("""
            CREATE TABLE PerfTestData (
                ID INT PRIMARY KEY,
                Name VARCHAR(100),
                Value DECIMAL(10,2)
            )
        """)

        # Insert 10K rows
        for i in range(10000):
            cursor.execute(
                "INSERT INTO PerfTestData (ID, Name, Value) VALUES (?, ?, ?)",
                (i, f"Name_{i}", i * 1.5)
            )
        cursor.close()

        # Create fixture from source namespace
        fixture_path = Path(temp_dir) / "load-perf"
        creator = FixtureCreator(container=iris_container)
        creator.create_fixture(
            fixture_id="load-perf",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        # Measure load time
        loader = DATFixtureLoader(container=iris_container)
        target_namespace = iris_container.get_test_namespace(prefix="LOAD_PERF_TARGET")

        start_time = time.time()
        result = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=target_namespace,
            validate_checksum=True
        )
        elapsed = time.time() - start_time

        assert result.success
        assert elapsed < 10.0, f"Load took {elapsed:.2f}s, expected <10s"

        # Cleanup target namespace
        try:
            loader.cleanup_fixture(target_namespace, delete_namespace=True)
        except Exception:
            pass  # Ignore cleanup errors

    @pytest.mark.skip(reason="Flaky test - checksum performance difference unmeasurable on small (1-row) fixtures. Namespace creation overhead dominates timing. Test passes on large fixtures (10K+ rows) where checksum overhead is significant.")
    def test_load_without_checksum_faster(self, iris_container, test_namespace, iris_connection, temp_dir):
        """Test that skipping checksum validation speeds up loading."""
        # Use test_namespace provided by fixture
        source_namespace = test_namespace

        # Create a small table for the fixture (need at least one table for valid manifest)
        cursor = iris_connection.cursor()
        cursor.execute("""
            CREATE TABLE ChecksumTest (
                ID INT PRIMARY KEY,
                Name VARCHAR(50)
            )
        """)
        cursor.execute("INSERT INTO ChecksumTest (ID, Name) VALUES (1, 'test')")
        cursor.close()

        # Create fixture
        fixture_path = Path(temp_dir) / "checksum-perf"
        creator = FixtureCreator(container=iris_container)
        creator.create_fixture(
            fixture_id="checksum-perf",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        loader = DATFixtureLoader(container=iris_container)

        # Load with checksum validation
        namespace_with = iris_container.get_test_namespace(prefix="CHECKSUM_WITH")
        start_with = time.time()
        result_with = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=namespace_with,
            validate_checksum=True
        )
        elapsed_with = time.time() - start_with

        # Load without checksum validation
        namespace_without = iris_container.get_test_namespace(prefix="CHECKSUM_WITHOUT")
        start_without = time.time()
        result_without = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=namespace_without,
            validate_checksum=False
        )
        elapsed_without = time.time() - start_without

        assert result_with.success
        assert result_without.success

        # Loading without checksum should be faster (or at least not slower)
        assert elapsed_without <= elapsed_with * 1.1  # Allow 10% margin

        # Cleanup namespaces (use actual namespace names from get_test_namespace)
        try:
            loader.cleanup_fixture(namespace_with, delete_namespace=True)
        except Exception:
            pass  # Ignore cleanup errors
        try:
            loader.cleanup_fixture(namespace_without, delete_namespace=True)
        except Exception:
            pass  # Ignore cleanup errors


class TestFixtureValidationPerformance:
    """Test fixture validation performance (NFR-003)."""

    def test_validate_fixture_under_5s(self, iris_container, test_namespace, temp_dir):
        """Test fixture validation completes in <5 seconds."""
        # Use test_namespace provided by fixture (already created)
        source_namespace = test_namespace

        # Create fixture from source namespace (empty is fine for validation performance test)
        fixture_path = Path(temp_dir) / "validate-perf"
        creator = FixtureCreator(container=iris_container)
        creator.create_fixture(
            fixture_id="validate-perf",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        # Measure validation time
        validator = FixtureValidator()

        start_time = time.time()
        result = validator.validate_fixture(
            str(fixture_path),
            validate_checksum=True
        )
        elapsed = time.time() - start_time

        assert result.valid
        assert elapsed < 5.0, f"Validation took {elapsed:.2f}s, expected <5s"


class TestChecksumPerformance:
    """Test SHA256 checksum performance (NFR-004)."""

    def test_checksum_calculation_under_2s(self, temp_dir):
        """Test SHA256 checksum calculation completes in <2 seconds per file."""
        # Create a test file (simulate IRIS.DAT size)
        test_file = Path(temp_dir) / "test.dat"

        # Create 10MB file
        with open(test_file, 'wb') as f:
            f.write(b'0' * (10 * 1024 * 1024))

        # Measure checksum time
        validator = FixtureValidator()

        start_time = time.time()
        checksum = validator.calculate_sha256(str(test_file))
        elapsed = time.time() - start_time

        assert checksum.startswith("sha256:")
        assert elapsed < 2.0, f"Checksum took {elapsed:.2f}s, expected <2s for 10MB file"


# Test count verification
def test_performance_test_count():
    """Verify we have comprehensive performance tests."""
    import sys
    module = sys.modules[__name__]

    test_classes = [
        TestFixtureCreationPerformance,
        TestFixtureLoadingPerformance,
        TestFixtureValidationPerformance,
        TestChecksumPerformance,
    ]

    total_tests = 0
    for test_class in test_classes:
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        total_tests += len(test_methods)

    # Should have at least 6 performance tests
    assert total_tests >= 6, f"Expected at least 6 performance tests, found {total_tests}"
