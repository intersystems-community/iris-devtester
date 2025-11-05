"""
Integration tests for monitor_utils - %Monitor.System verification.

Tests verify that %Monitor.System infrastructure exists and can be queried
via SQL, even if data collection is not active by default.
"""

import pytest
from iris_devtester.containers.monitor_utils import (
    check_monitor_tables,
    is_monitor_collecting,
    get_monitoring_status,
    get_monitor_samples,
)


class TestMonitorInfrastructure:
    """Test %Monitor.System infrastructure availability."""

    def test_monitor_tables_exist(self, iris_db):
        """
        Verify %Monitor.System tables exist in Community Edition.

        Expected: At least 10 monitoring tables should be available.
        """
        exists, tables = check_monitor_tables(iris_db)

        assert exists is True, "%Monitor.System tables should exist"
        assert len(tables) >= 10, f"Expected at least 10 tables, found {len(tables)}"

        # Verify key tables are present
        table_names = [t.upper() for t in tables]
        assert "HISTORYPERF" in table_names, "HistoryPerf table should exist"
        assert "HISTORYMEMORY" in table_names, "HistoryMemory table should exist"

    def test_monitoring_status(self, iris_db):
        """
        Get comprehensive monitoring status.

        Expected: Infrastructure exists, may not be actively collecting.
        """
        status = get_monitoring_status(iris_db)

        assert status.tables_exist is True, "Monitoring tables should exist"
        assert len(status.available_tables) >= 10, "Multiple tables should be available"

        # Note: is_collecting may be False in default container configuration
        # This is EXPECTED behavior - monitoring exists but sensor saving not enabled
        assert isinstance(status.is_collecting, bool)
        assert isinstance(status.sample_count, int)

    def test_monitor_tables_queryable(self, iris_db):
        """
        Verify monitoring tables can be queried via SQL.

        Expected: Tables are accessible even if empty.
        """
        # Should be able to query HistoryPerf without errors
        samples = get_monitor_samples(iris_db, "HistoryPerf", limit=5)

        assert isinstance(samples, list)
        # Samples may be empty list if monitoring not collecting
        # This is OK - we just verify the table is queryable

    def test_is_monitor_collecting_check(self, iris_db):
        """
        Check if monitoring is collecting data.

        Expected: Returns tuple (bool, int) indicating status.
        """
        is_collecting, sample_count = is_monitor_collecting(iris_db)

        assert isinstance(is_collecting, bool)
        assert isinstance(sample_count, int)
        assert sample_count >= 0, "Sample count should be non-negative"

        # If collecting, sample count should be > 0
        if is_collecting:
            assert sample_count > 0, "If collecting, should have samples"


class TestMonitorSampleRetrieval:
    """Test retrieving monitoring samples (when available)."""

    def test_get_history_perf_samples(self, iris_db):
        """
        Test retrieving HistoryPerf samples.

        Note: May return empty list if monitoring not collecting.
        """
        samples = get_monitor_samples(iris_db, "HistoryPerf", limit=10)

        assert isinstance(samples, list)
        assert len(samples) <= 10, "Should respect limit parameter"

        # If samples exist, verify structure
        if samples:
            sample = samples[0]
            assert isinstance(sample, dict)
            # HistoryPerf should have DateTime field
            assert "DateTime" in sample or "DATETIME" in sample

    def test_get_samples_different_tables(self, iris_db):
        """
        Test retrieving samples from different monitoring tables.

        Note: All may be empty if monitoring not collecting.
        """
        tables_to_test = ["HistoryPerf", "HistoryMemory", "Processes"]

        for table in tables_to_test:
            samples = get_monitor_samples(iris_db, table, limit=5)
            assert isinstance(samples, list), f"{table} should return list"
            assert len(samples) <= 5, f"{table} should respect limit"


@pytest.mark.parametrize(
    "table_name",
    [
        "HistoryPerf",
        "HistoryMemory",
        "HistorySys",
        "Processes",
        "LockTable",
    ],
)
class TestMonitorTableAccess:
    """Test access to individual monitoring tables."""

    def test_table_is_accessible(self, iris_db, table_name):
        """
        Verify specific monitoring table is accessible.

        Expected: Can query table without errors.
        """
        samples = get_monitor_samples(iris_db, table_name, limit=1)
        assert isinstance(samples, list)
        # Empty is OK - table exists and is queryable


class TestMonitorStatusReporting:
    """Test monitoring status reporting."""

    def test_status_provides_complete_info(self, iris_db):
        """
        Verify MonitoringStatus provides all expected fields.

        Expected: All fields present and correct types.
        """
        status = get_monitoring_status(iris_db)

        # Verify all fields present
        assert hasattr(status, "tables_exist")
        assert hasattr(status, "is_collecting")
        assert hasattr(status, "sample_count")
        assert hasattr(status, "latest_sample")
        assert hasattr(status, "available_tables")

        # Verify types
        assert isinstance(status.tables_exist, bool)
        assert isinstance(status.is_collecting, bool)
        assert isinstance(status.sample_count, int)
        assert isinstance(status.available_tables, list)

        # latest_sample can be None if not collecting
        if status.latest_sample is not None:
            # Should be datetime-like if present
            assert hasattr(status.latest_sample, "__str__")

    def test_status_table_list_accurate(self, iris_db):
        """
        Verify status.available_tables matches actual tables.

        Expected: List matches check_monitor_tables() results.
        """
        # Get tables via utility
        exists, tables_direct = check_monitor_tables(iris_db)

        # Get tables via status
        status = get_monitoring_status(iris_db)

        assert status.tables_exist == exists
        assert set(status.available_tables) == set(tables_direct)


class TestMonitorUtilsErrorHandling:
    """Test error handling in monitor utilities."""

    def test_invalid_table_name_graceful(self, iris_db):
        """
        Test graceful handling of invalid table names.

        Expected: Returns empty list, logs error, doesn't crash.
        """
        # Try to get samples from non-existent table
        samples = get_monitor_samples(iris_db, "NonExistentTable", limit=5)

        # Should return empty list, not raise exception
        assert samples == []

    def test_zero_limit_handled(self, iris_db):
        """
        Test that limit=0 is handled correctly.

        Expected: Returns empty list without errors.
        """
        samples = get_monitor_samples(iris_db, "HistoryPerf", limit=0)
        assert samples == []

    def test_large_limit_handled(self, iris_db):
        """
        Test that large limits are handled safely.

        Expected: Returns available samples, respects limit.
        """
        samples = get_monitor_samples(iris_db, "HistoryPerf", limit=1000)
        assert isinstance(samples, list)
        assert len(samples) <= 1000


# Performance tests (optional - can be marked as slow)
@pytest.mark.slow
class TestMonitorPerformance:
    """Performance tests for monitoring utilities."""

    def test_status_check_fast(self, iris_db):
        """
        Verify status check completes quickly.

        Expected: <200ms for status check.
        """
        import time

        start = time.time()
        get_monitoring_status(iris_db)
        duration = time.time() - start

        assert duration < 0.2, f"Status check took {duration:.3f}s (expected <0.2s)"

    def test_sample_retrieval_reasonable(self, iris_db):
        """
        Verify sample retrieval has reasonable performance.

        Expected: <500ms for 100 samples.
        """
        import time

        start = time.time()
        get_monitor_samples(iris_db, "HistoryPerf", limit=100)
        duration = time.time() - start

        assert duration < 0.5, f"Sample retrieval took {duration:.3f}s (expected <0.5s)"
