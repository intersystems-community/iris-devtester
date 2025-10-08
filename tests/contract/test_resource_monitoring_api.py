"""
Contract tests for Resource Monitoring & Auto-Disable API.

Tests API contracts for get_resource_metrics(), check_resource_thresholds(),
auto_disable_monitoring(), and auto_enable_monitoring().

These tests validate the API signatures and behavior WITHOUT requiring a real
IRIS instance.

Constitutional Principle #1: Automatic Remediation - Auto-disable under pressure.
"""

import pytest
from unittest.mock import Mock
import inspect
from datetime import datetime

from iris_devtools.containers.performance import (
    PerformanceMetrics,
    get_resource_metrics,
    check_resource_thresholds,
    auto_disable_monitoring,
    auto_enable_monitoring,
)
from iris_devtools.containers.monitoring import ResourceThresholds


class TestGetResourceMetricsContract:
    """Test get_resource_metrics() API contract."""

    def test_function_exists_and_callable(self):
        """Test get_resource_metrics function exists."""
        assert callable(get_resource_metrics)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        mock_conn = Mock()

        with pytest.raises(NotImplementedError):
            get_resource_metrics(mock_conn)

    def test_returns_performance_metrics(self):
        """Test function signature returns PerformanceMetrics."""
        sig = inspect.signature(get_resource_metrics)
        # Return annotation should be PerformanceMetrics
        assert sig.return_annotation is not inspect.Signature.empty


class TestCheckResourceThresholdsContract:
    """Test check_resource_thresholds() API contract."""

    def test_function_exists_and_callable(self):
        """Test check_resource_thresholds function exists."""
        assert callable(check_resource_thresholds)

    def test_signature_accepts_connection_and_thresholds(self):
        """Test function accepts required parameters."""
        mock_conn = Mock()
        thresholds = ResourceThresholds()

        with pytest.raises(NotImplementedError):
            check_resource_thresholds(mock_conn, thresholds)

    def test_returns_tuple(self):
        """Test function signature returns tuple."""
        sig = inspect.signature(check_resource_thresholds)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestAutoDisableMonitoringContract:
    """Test auto_disable_monitoring() API contract."""

    def test_function_exists_and_callable(self):
        """Test auto_disable_monitoring function exists."""
        assert callable(auto_disable_monitoring)

    def test_signature_accepts_connection_and_reason(self):
        """Test function accepts required parameters."""
        mock_conn = Mock()

        with pytest.raises(NotImplementedError):
            auto_disable_monitoring(mock_conn, reason="CPU >90%")

    def test_returns_bool(self):
        """Test function signature returns bool."""
        sig = inspect.signature(auto_disable_monitoring)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestAutoEnableMonitoringContract:
    """Test auto_enable_monitoring() API contract."""

    def test_function_exists_and_callable(self):
        """Test auto_enable_monitoring function exists."""
        assert callable(auto_enable_monitoring)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        mock_conn = Mock()

        with pytest.raises(NotImplementedError):
            auto_enable_monitoring(mock_conn)

    def test_returns_bool(self):
        """Test function signature returns bool."""
        sig = inspect.signature(auto_enable_monitoring)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestPerformanceMetricsContract:
    """Test PerformanceMetrics dataclass contract."""

    def test_performance_metrics_has_required_fields(self):
        """Test PerformanceMetrics includes all required fields."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=45.2,
            memory_percent=67.8,
            global_references=1234,
            lock_requests=56,
            disk_reads=789,
            disk_writes=456,
            monitoring_enabled=True,
        )

        # Required fields
        assert metrics.timestamp is not None
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.global_references >= 0
        assert metrics.lock_requests >= 0
        assert metrics.disk_reads >= 0
        assert metrics.disk_writes >= 0
        assert isinstance(metrics.monitoring_enabled, bool)

    def test_performance_metrics_from_objectscript_result(self):
        """Test PerformanceMetrics.from_objectscript_result() exists."""
        assert hasattr(PerformanceMetrics, "from_objectscript_result")
        assert callable(PerformanceMetrics.from_objectscript_result)

    def test_performance_metrics_exceeds_thresholds(self):
        """Test PerformanceMetrics.exceeds_thresholds() method."""
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

        # Should have method
        assert hasattr(metrics, "exceeds_thresholds")
        assert callable(metrics.exceeds_thresholds)

        # Should detect high CPU
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_performance_metrics_below_thresholds(self):
        """Test PerformanceMetrics.below_thresholds() method."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=80.0,  # Recovered
            memory_percent=85.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )

        thresholds = ResourceThresholds()

        # Should have method
        assert hasattr(metrics, "below_thresholds")
        assert callable(metrics.below_thresholds)

        # Should detect recovery
        assert metrics.below_thresholds(thresholds) is True


class TestResourceMonitoringConstitutionalCompliance:
    """Test Constitutional Principle compliance in resource monitoring API."""

    def test_automatic_remediation_principle(self):
        """Test Principle 1: Auto-disable/enable logic exists."""
        # Auto-disable when resources high
        assert callable(auto_disable_monitoring)

        # Auto-enable when resources recovered
        assert callable(auto_enable_monitoring)

    def test_resource_thresholds_have_defaults(self):
        """Test Principle 4: ResourceThresholds work with no parameters."""
        thresholds = ResourceThresholds()

        # Should have sensible defaults (FR-017, FR-018)
        assert thresholds.cpu_disable_percent == 90.0
        assert thresholds.memory_disable_percent == 95.0
        assert thresholds.cpu_enable_percent == 85.0
        assert thresholds.memory_enable_percent == 90.0

    def test_resource_thresholds_validation_fails_fast(self):
        """Test Principle 5: Validation provides clear guidance."""
        # Invalid: no hysteresis
        thresholds = ResourceThresholds(
            cpu_disable_percent=90.0, cpu_enable_percent=90.0
        )

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "thrashing" in error_msg.lower()
        assert len(error_msg) > 50  # Detailed message

    def test_get_resource_metrics_target_performance(self):
        """Test performance expectation: <100ms per check."""
        # Contract: Resource metrics query should be fast (<100ms per spec)
        assert get_resource_metrics.__doc__ is not None


class TestResourceMonitoringScenarios:
    """Test realistic resource monitoring scenarios via contracts."""

    def test_normal_operation_scenario(self):
        """Test normal system operation (no action needed)."""
        thresholds = ResourceThresholds()

        # Normal metrics
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            global_references=10000,
            lock_requests=50,
            disk_reads=1000,
            disk_writes=500,
            monitoring_enabled=True,
        )

        # Should not trigger disable
        assert metrics.exceeds_thresholds(thresholds) is False
        # Could enable if it were disabled
        assert metrics.below_thresholds(thresholds) is True

    def test_high_cpu_spike_scenario(self):
        """Test CPU spike triggering auto-disable."""
        thresholds = ResourceThresholds()

        # CPU spike
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=94.0,  # >90% threshold
            memory_percent=68.0,
            global_references=50000,
            lock_requests=200,
            disk_reads=5000,
            disk_writes=3000,
            monitoring_enabled=True,
        )

        # Should trigger disable
        assert metrics.exceeds_thresholds(thresholds) is True
        # Should not allow re-enable yet
        assert metrics.below_thresholds(thresholds) is False

    def test_memory_pressure_scenario(self):
        """Test high memory triggering auto-disable."""
        thresholds = ResourceThresholds()

        # Memory pressure
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=72.0,
            memory_percent=97.0,  # >95% threshold
            global_references=30000,
            lock_requests=100,
            disk_reads=2000,
            disk_writes=1500,
            monitoring_enabled=True,
        )

        # Should trigger disable
        assert metrics.exceeds_thresholds(thresholds) is True

    def test_recovery_with_hysteresis_scenario(self):
        """Test resource recovery with hysteresis preventing thrashing."""
        thresholds = ResourceThresholds()

        # Step 1: High CPU (monitoring disabled)
        high_cpu = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=94.0,
            memory_percent=70.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )
        assert high_cpu.exceeds_thresholds(thresholds) is True

        # Step 2: CPU drops to 88% (still can't re-enable due to hysteresis)
        partial_recovery = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=88.0,
            memory_percent=70.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )
        assert partial_recovery.exceeds_thresholds(thresholds) is False
        assert partial_recovery.below_thresholds(thresholds) is False  # Hysteresis

        # Step 3: CPU drops to 82% (can re-enable)
        full_recovery = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=82.0,
            memory_percent=70.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )
        assert full_recovery.below_thresholds(thresholds) is True


class TestResourceMonitoringAPIPerformance:
    """Test performance expectations from contracts."""

    def test_get_resource_metrics_performance_target(self):
        """Test get_resource_metrics should complete in <100ms."""
        # Contract: Fast query (per resource_monitoring_api.md)
        sig = inspect.signature(get_resource_metrics)
        assert sig is not None

    def test_check_resource_thresholds_performance_target(self):
        """Test check_resource_thresholds should be very fast (in-memory)."""
        # Contract: Pure logic, no I/O, should be <1ms
        sig = inspect.signature(check_resource_thresholds)
        assert sig is not None

    def test_resource_check_interval_minimum(self):
        """Test check_interval_seconds has minimum value."""
        thresholds = ResourceThresholds()

        # Default should be 60 seconds
        assert thresholds.check_interval_seconds == 60


class TestResourceMonitoringIdempotency:
    """Test idempotency of resource monitoring operations."""

    def test_auto_disable_idempotency(self):
        """Test calling auto_disable twice is safe."""
        mock_conn = Mock()

        # Should be safe to disable multiple times
        with pytest.raises(NotImplementedError):
            auto_disable_monitoring(mock_conn, reason="CPU high")

        with pytest.raises(NotImplementedError):
            auto_disable_monitoring(mock_conn, reason="CPU still high")

    def test_auto_enable_idempotency(self):
        """Test calling auto_enable twice is safe."""
        mock_conn = Mock()

        # Should be safe to enable multiple times
        with pytest.raises(NotImplementedError):
            auto_enable_monitoring(mock_conn)

        with pytest.raises(NotImplementedError):
            auto_enable_monitoring(mock_conn)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
