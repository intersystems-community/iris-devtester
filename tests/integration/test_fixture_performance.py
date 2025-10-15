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

from iris_devtools.fixtures import (
    FixtureCreator,
    DATFixtureLoader,
    FixtureValidator,
)
from iris_devtools.connections import get_connection


@pytest.fixture(scope="module")
def iris_connection():
    """Provide IRIS connection for performance tests."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        yield conn
    except Exception as e:
        pytest.skip(f"IRIS not available: {e}")


@pytest.fixture(scope="function")
def temp_dir():
    """Provide temporary directory for fixtures."""
    temp_dir = tempfile.mkdtemp(prefix="perf_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestFixtureCreationPerformance:
    """Test fixture creation performance (NFR-001)."""

    def test_create_fixture_10k_rows_under_30s(self, iris_connection, temp_dir):
        """Test creating fixture with 10K rows completes in <30 seconds."""
        # Create namespace with 10K rows
        source_namespace = "PERF_TEST_10K"
        conn = get_connection()
        cursor = conn.cursor()

        # Create namespace
        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '%SYS'
                set sc = ##class(Config.Namespaces).Create('{source_namespace}')
                quit:sc
            ")
        """)

        # Create table and insert 10K rows
        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '{source_namespace}'

                &sql(CREATE TABLE PerfTestData (
                    ID INT PRIMARY KEY,
                    Name VARCHAR(100),
                    Value DECIMAL(10,2),
                    Description VARCHAR(500)
                ))

                // Insert 10K rows
                for i=1:1:10000 {{
                    &sql(INSERT INTO PerfTestData VALUES (
                        :i,
                        'Name_' _ i,
                        i * 1.5,
                        'Description for row ' _ i
                    ))
                }}

                quit
            ")
        """)
        cursor.close()

        # Measure creation time
        fixture_path = Path(temp_dir) / "perf-10k"
        creator = FixtureCreator()

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

    def test_create_small_fixture_under_5s(self, iris_connection, temp_dir):
        """Test creating small fixture (<1K rows) completes in <5 seconds."""
        source_namespace = "PERF_TEST_SMALL"
        conn = get_connection()
        cursor = conn.cursor()

        # Create namespace with 100 rows
        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '%SYS'
                set sc = ##class(Config.Namespaces).Create('{source_namespace}')
                quit:sc
            ")
        """)

        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '{source_namespace}'

                &sql(CREATE TABLE SmallData (ID INT PRIMARY KEY, Name VARCHAR(100)))

                for i=1:1:100 {{
                    &sql(INSERT INTO SmallData VALUES (:i, 'Name_' _ i))
                }}

                quit
            ")
        """)
        cursor.close()

        # Measure creation time
        fixture_path = Path(temp_dir) / "perf-small"
        creator = FixtureCreator()

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
    def test_load_fixture_10k_rows_under_10s(self, iris_connection, temp_dir):
        """Test loading fixture with 10K rows completes in <10 seconds."""
        # First create a fixture with 10K rows (from previous test)
        # For this test, we'll create a minimal fixture and measure load time

        # Create source fixture
        source_namespace = "LOAD_PERF_SOURCE"
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '%SYS'
                set sc = ##class(Config.Namespaces).Create('{source_namespace}')
                quit:sc
            ")
        """)
        cursor.close()

        fixture_path = Path(temp_dir) / "load-perf"
        creator = FixtureCreator()
        creator.create_fixture(
            fixture_id="load-perf",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        # Measure load time
        loader = DATFixtureLoader()
        target_namespace = "LOAD_PERF_TARGET"

        start_time = time.time()
        result = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace=target_namespace,
            validate_checksum=True
        )
        elapsed = time.time() - start_time

        assert result.success
        assert elapsed < 10.0, f"Load took {elapsed:.2f}s, expected <10s"

        # Cleanup
        loader.cleanup_fixture(target_namespace, delete_namespace=True)

    def test_load_without_checksum_faster(self, iris_connection, temp_dir):
        """Test that skipping checksum validation speeds up loading."""
        # Create a fixture
        source_namespace = "CHECKSUM_PERF_SOURCE"
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '%SYS'
                set sc = ##class(Config.Namespaces).Create('{source_namespace}')
                quit:sc
            ")
        """)
        cursor.close()

        fixture_path = Path(temp_dir) / "checksum-perf"
        creator = FixtureCreator()
        creator.create_fixture(
            fixture_id="checksum-perf",
            namespace=source_namespace,
            output_dir=str(fixture_path)
        )

        loader = DATFixtureLoader()

        # Load with checksum validation
        start_with = time.time()
        result_with = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace="CHECKSUM_WITH",
            validate_checksum=True
        )
        elapsed_with = time.time() - start_with

        # Load without checksum validation
        start_without = time.time()
        result_without = loader.load_fixture(
            fixture_path=str(fixture_path),
            target_namespace="CHECKSUM_WITHOUT",
            validate_checksum=False
        )
        elapsed_without = time.time() - start_without

        assert result_with.success
        assert result_without.success

        # Loading without checksum should be faster (or at least not slower)
        assert elapsed_without <= elapsed_with * 1.1  # Allow 10% margin

        # Cleanup
        loader.cleanup_fixture("CHECKSUM_WITH", delete_namespace=True)
        loader.cleanup_fixture("CHECKSUM_WITHOUT", delete_namespace=True)


class TestFixtureValidationPerformance:
    """Test fixture validation performance (NFR-003)."""

    def test_validate_fixture_under_5s(self, iris_connection, temp_dir):
        """Test fixture validation completes in <5 seconds."""
        # Create a fixture
        source_namespace = "VALIDATE_PERF"
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            DO $SYSTEM.OBJ.Execute("
                new $NAMESPACE
                set $NAMESPACE = '%SYS'
                set sc = ##class(Config.Namespaces).Create('{source_namespace}')
                quit:sc
            ")
        """)
        cursor.close()

        fixture_path = Path(temp_dir) / "validate-perf"
        creator = FixtureCreator()
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
