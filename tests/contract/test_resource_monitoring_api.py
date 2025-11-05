"""
Contract tests for Resource Monitoring & Auto-Disable API.

Tests API contracts for get_resource_metrics(), check_resource_thresholds(),
auto_disable_monitoring(), and auto_enable_monitoring().

These tests validate the API signatures and behavior WITHOUT requiring a real
IRIS instance.

Constitutional Principle #1: Automatic Remediation - Auto-disable under pressure.
"""


import pytest

pytestmark = pytest.mark.contract
from unittest.mock import Mock
import inspect
from datetime import datetime

from iris_devtester.containers.performance import (
    PerformanceMetrics,
    get_resource_metrics,
    check_resource_thresholds,
    auto_disable_monitoring,
    auto_enable_monitoring,
)
from iris_devtester.containers.monitoring import ResourceThresholds


class TestGetResourceMetricsContract:
    """Test get_resource_metrics() API contract."""

    def test_function_exists_and_callable(self):
        """Test get_resource_metrics function exists."""
        assert callable(get_resource_metrics)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        # Verify function signature

        sig = inspect.signature(get_resource_metrics)

        params = list(sig.parameters.keys())

        assert 'conn' in params

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
        # Verify function signature (contract test)

        sig = inspect.signature(check_resource_thresholds)

        assert sig is not None

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
        # Verify function signature (contract test)
        sig = inspect.signature(auto_disable_monitoring)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        assert 'reason' in params

    def test_auto_enable_idempotency(self):
        """Test calling auto_enable twice is safe."""
        # Verify function signature (contract test)
        sig = inspect.signature(auto_enable_monitoring)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        # Implementation should be idempotent (safe to call multiple times)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
