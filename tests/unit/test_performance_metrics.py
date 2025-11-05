"""
Unit tests for PerformanceMetrics dataclass.

Tests JSON parsing, threshold checking, and metric collection.
Constitutional Principle #7: Medical-Grade Reliability - All parsing paths tested.
"""

import json
import pytest
from datetime import datetime
from iris_devtester.containers.performance import PerformanceMetrics
from iris_devtester.containers.monitoring import ResourceThresholds


class TestPerformanceMetricsCreation:
    """Test PerformanceMetrics dataclass creation."""

    def test_can_create_metrics_directly(self):
        """Test direct instantiation works."""
        now = datetime.now()
        metrics = PerformanceMetrics(
            timestamp=now,
            cpu_percent=45.2,
            memory_percent=67.8,
            global_references=1234,
            lock_requests=56,
            disk_reads=789,
            disk_writes=456,
            monitoring_enabled=True,
        )

        assert metrics.cpu_percent == 45.2
        assert metrics.memory_percent == 67.8
        assert metrics.global_references == 1234
        assert metrics.monitoring_enabled is True

    def test_optional_last_state_change_defaults_to_none(self):
        """Test last_state_change is optional."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=True,
        )

        assert metrics.last_state_change is None


class TestPerformanceMetricsFromObjectScript:
    """Test parsing from ObjectScript JSON results."""

    def test_parses_complete_json_result(self):
        """Test parsing complete ObjectScript response."""
        json_result = json.dumps(
            {
                "cpu": 45.2,
                "memory": 67.8,
                "glorefs": 1234,
                "locks": 56,
                "reads": 789,
                "writes": 456,
            }
        )

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )

        assert metrics.cpu_percent == 45.2
        assert metrics.memory_percent == 67.8
        assert metrics.global_references == 1234
        assert metrics.lock_requests == 56
        assert metrics.disk_reads == 789
        assert metrics.disk_writes == 456
        assert metrics.monitoring_enabled is True
        assert isinstance(metrics.timestamp, datetime)

    def test_parses_minimal_json_result(self):
        """Test parsing with only required fields."""
        json_result = json.dumps({"cpu": 30.0, "memory": 40.0})

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=False
        )

        assert metrics.cpu_percent == 30.0
        assert metrics.memory_percent == 40.0
        # Optional fields default to 0
        assert metrics.global_references == 0
        assert metrics.lock_requests == 0
        assert metrics.disk_reads == 0
        assert metrics.disk_writes == 0
        assert metrics.monitoring_enabled is False

    def test_parses_partial_json_result(self):
        """Test parsing with some optional fields."""
        json_result = json.dumps(
            {"cpu": 55.5, "memory": 72.3, "glorefs": 9999, "locks": 123}
        )

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )

        assert metrics.cpu_percent == 55.5
        assert metrics.memory_percent == 72.3
        assert metrics.global_references == 9999
        assert metrics.lock_requests == 123
        assert metrics.disk_reads == 0  # Missing, defaults to 0
        assert metrics.disk_writes == 0  # Missing, defaults to 0

    def test_parsing_invalid_json_raises_error(self):
        """Test invalid JSON raises helpful error."""
        invalid_json = "not valid json"

        with pytest.raises(json.JSONDecodeError):
            PerformanceMetrics.from_objectscript_result(
                invalid_json, monitoring_enabled=True
            )

    def test_parsing_missing_required_field_raises_error(self):
        """Test missing required fields raise KeyError."""
        # Missing 'memory' field
        json_result = json.dumps({"cpu": 50.0})

        with pytest.raises(KeyError):
            PerformanceMetrics.from_objectscript_result(
                json_result, monitoring_enabled=True
            )


class TestPerformanceMetricsThresholdChecking:
    """Test exceeds_thresholds() and below_thresholds() methods."""

    def test_exceeds_thresholds_when_cpu_high(self):
        """Test CPU > 90% detected as exceeding thresholds."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=95.0,  # High CPU
            memory_percent=60.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=True,
        )

        thresholds = ResourceThresholds()
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_exceeds_thresholds_when_memory_high(self):
        """Test memory > 95% detected as exceeding thresholds."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=60.0,
            memory_percent=98.0,  # High memory
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=True,
        )

        thresholds = ResourceThresholds()
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_exceeds_thresholds_when_both_high(self):
        """Test both CPU and memory high detected."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=92.0,
            memory_percent=97.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=True,
        )

        thresholds = ResourceThresholds()
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_does_not_exceed_thresholds_when_normal(self):
        """Test normal levels don't exceed thresholds."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=True,
        )

        thresholds = ResourceThresholds()
        assert metrics.exceeds_thresholds(thresholds) is False

    def test_below_thresholds_when_resources_recovered(self):
        """Test CPU < 85% AND memory < 90% detected as below thresholds."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=80.0,
            memory_percent=85.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,  # Currently disabled
        )

        thresholds = ResourceThresholds()
        assert metrics.below_thresholds(thresholds) is True

    def test_not_below_thresholds_when_cpu_still_high(self):
        """Test CPU >= 85% prevents re-enable."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=88.0,  # Still above enable threshold
            memory_percent=85.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )

        thresholds = ResourceThresholds()
        assert metrics.below_thresholds(thresholds) is False

    def test_not_below_thresholds_when_memory_still_high(self):
        """Test memory >= 90% prevents re-enable."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=80.0,
            memory_percent=92.0,  # Still above enable threshold
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )

        thresholds = ResourceThresholds()
        assert metrics.below_thresholds(thresholds) is False


class TestPerformanceMetricsRealisticScenarios:
    """Test realistic monitoring scenarios."""

    def test_normal_operation_metrics(self):
        """Test typical healthy system metrics."""
        json_result = json.dumps(
            {
                "cpu": 35.2,
                "memory": 55.8,
                "glorefs": 12345,
                "locks": 42,
                "reads": 1024,
                "writes": 512,
            }
        )

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )
        thresholds = ResourceThresholds()

        # Should not trigger disable
        assert metrics.exceeds_thresholds(thresholds) is False
        # Should allow enable (if it were disabled)
        assert metrics.below_thresholds(thresholds) is True

    def test_high_cpu_spike_scenario(self):
        """Test CPU spike triggering auto-disable."""
        json_result = json.dumps(
            {
                "cpu": 94.5,  # CPU spike
                "memory": 68.0,
                "glorefs": 50000,
                "locks": 200,
                "reads": 5000,
                "writes": 3000,
            }
        )

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )
        thresholds = ResourceThresholds()

        # Should trigger disable
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_memory_pressure_scenario(self):
        """Test high memory triggering auto-disable."""
        json_result = json.dumps(
            {
                "cpu": 72.0,
                "memory": 97.3,  # Memory pressure
                "glorefs": 30000,
                "locks": 100,
                "reads": 2000,
                "writes": 1500,
            }
        )

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )
        thresholds = ResourceThresholds()

        # Should trigger disable
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_recovery_scenario(self):
        """Test resources recovering allowing re-enable."""
        json_result = json.dumps(
            {
                "cpu": 75.0,  # Recovered from 94%
                "memory": 82.0,  # Recovered from 97%
                "glorefs": 15000,
                "locks": 50,
                "reads": 1500,
                "writes": 800,
            }
        )

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=False  # Currently disabled
        )
        thresholds = ResourceThresholds()

        # Should allow re-enable
        assert metrics.below_thresholds(thresholds) is True
        # Should not exceed disable thresholds
        assert metrics.exceeds_thresholds(thresholds) is False


class TestPerformanceMetricsCustomThresholds:
    """Test metrics work with custom thresholds (FR-023)."""

    def test_metrics_with_aggressive_thresholds(self):
        """Test lower disable thresholds."""
        json_result = json.dumps({"cpu": 75.0, "memory": 80.0})

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )

        # Default thresholds (90%, 95%) - should not disable
        default_thresholds = ResourceThresholds()
        assert metrics.exceeds_thresholds(default_thresholds) is False

        # Aggressive thresholds (70%, 75%) - should disable
        aggressive_thresholds = ResourceThresholds(
            cpu_disable_percent=70.0, memory_disable_percent=75.0
        )
        assert metrics.exceeds_thresholds(aggressive_thresholds) is True

    def test_metrics_with_conservative_thresholds(self):
        """Test higher disable thresholds."""
        json_result = json.dumps({"cpu": 93.0, "memory": 96.0})

        metrics = PerformanceMetrics.from_objectscript_result(
            json_result, monitoring_enabled=True
        )

        # Default thresholds (90%, 95%) - should disable
        default_thresholds = ResourceThresholds()
        assert metrics.exceeds_thresholds(default_thresholds) is True

        # Conservative thresholds (98%, 99%) - should not disable
        conservative_thresholds = ResourceThresholds(
            cpu_disable_percent=98.0, memory_disable_percent=99.0
        )
        assert metrics.exceeds_thresholds(conservative_thresholds) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
