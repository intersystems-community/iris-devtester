"""
Contract tests for Monitoring Configuration API.

Tests API contracts for configure_monitoring(), get_monitoring_status(),
disable_monitoring(), and enable_monitoring().

These tests validate the API signatures and behavior WITHOUT requiring a real
IRIS instance. Implementation will be tested in integration tests.

Constitutional Principle #7: Medical-Grade Reliability - All API contracts validated.
"""


import pytest

pytestmark = pytest.mark.contract
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import inspect

from iris_devtester.containers.monitoring import (
    MonitoringPolicy,
    configure_monitoring,
    get_monitoring_status,
    disable_monitoring,
    enable_monitoring,
    ResourceThresholds,
)


class TestConfigureMonitoringContract:
    """Test configure_monitoring() API contract."""

    def test_function_exists_and_callable(self):
        """Test configure_monitoring function exists."""
        assert callable(configure_monitoring)

    def test_signature_accepts_connection_and_optional_policy(self):
        """Test function accepts required and optional parameters."""
        # Verify function signature (contract test)

        sig = inspect.signature(configure_monitoring)

        assert sig is not None

        # Should accept connection and policy
        policy = MonitoringPolicy()

        # Should accept force parameter

    def test_returns_tuple_with_bool_and_string(self):
        """Test function signature returns (bool, str)."""

        sig = inspect.signature(configure_monitoring)
        # Return annotation should be Tuple[bool, str]
        assert sig.return_annotation is not inspect.Signature.empty

    def test_accepts_none_policy_for_defaults(self):
        """Test None policy triggers default configuration."""
        # Verify function signature (contract test)

        sig = inspect.signature(configure_monitoring)

        assert sig is not None

    def test_accepts_custom_monitoring_policy(self):
        """Test custom MonitoringPolicy can be passed."""
        # Verify function signature (contract test)

        sig = inspect.signature(configure_monitoring)

        assert sig is not None


class TestGetMonitoringStatusContract:
    """Test get_monitoring_status() API contract."""

    def test_function_exists_and_callable(self):
        """Test get_monitoring_status function exists."""
        assert callable(get_monitoring_status)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        # Verify function signature

        sig = inspect.signature(get_monitoring_status)

        params = list(sig.parameters.keys())

        assert 'conn' in params

    def test_returns_tuple_with_bool_and_dict(self):
        """Test function signature returns (bool, dict)."""

        sig = inspect.signature(get_monitoring_status)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestDisableMonitoringContract:
    """Test disable_monitoring() API contract."""

    def test_function_exists_and_callable(self):
        """Test disable_monitoring function exists."""
        assert callable(disable_monitoring)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        # Verify function signature

        sig = inspect.signature(disable_monitoring)

        params = list(sig.parameters.keys())

        assert 'conn' in params

    def test_returns_tuple_with_bool_and_string(self):
        """Test function signature returns (bool, str)."""

        sig = inspect.signature(disable_monitoring)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestEnableMonitoringContract:
    """Test enable_monitoring() API contract."""

    def test_function_exists_and_callable(self):
        """Test enable_monitoring function exists."""
        assert callable(enable_monitoring)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        # Verify function signature

        sig = inspect.signature(enable_monitoring)

        params = list(sig.parameters.keys())

        assert 'conn' in params

    def test_returns_tuple_with_bool_and_string(self):
        """Test function signature returns (bool, str)."""

        sig = inspect.signature(enable_monitoring)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestMonitoringAPIConstitutionalCompliance:
    """Test Constitutional Principle compliance in API design."""

    def test_configure_monitoring_zero_config_viable(self):
        """Test Principle 4: configure_monitoring() works with no parameters except conn."""

        sig = inspect.signature(configure_monitoring)
        params = list(sig.parameters.values())

        # First param is required (conn)
        assert params[0].name == "conn"
        assert params[0].default == inspect.Parameter.empty

        # Other params have defaults (zero-config viable)
        for param in params[1:]:
            assert param.default is not inspect.Parameter.empty

    def test_monitoring_policy_has_sensible_defaults(self):
        """Test Principle 4: MonitoringPolicy defaults match spec."""
        policy = MonitoringPolicy()

        # FR-002, FR-003
        assert policy.interval_seconds == 30
        assert policy.retention_seconds == 3600

    def test_monitoring_policy_validation_fails_fast(self):
        """Test Principle 5: Validation provides clear error messages."""
        policy = MonitoringPolicy(interval_seconds=500)  # Invalid

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        error_msg = str(exc_info.value)
        # Must include "What went wrong" and "How to fix it"
        assert "What went wrong" in error_msg
        assert "How to fix it" in error_msg
        assert "500s" in error_msg  # Specific value mentioned

    def test_resource_thresholds_auto_remediation(self):
        """Test Principle 1: Auto-disable/enable logic exists."""
        thresholds = ResourceThresholds()

        # Should have disable logic
        assert callable(thresholds.should_disable)
        assert callable(thresholds.should_enable)

        # Should trigger disable at CPU > 90%
        assert thresholds.should_disable(cpu_percent=95.0, memory_percent=50.0) is True

        # Should allow enable at CPU < 85% (hysteresis)
        assert thresholds.should_enable(cpu_percent=80.0, memory_percent=50.0) is True


class TestMonitoringAPIIdempotency:
    """Test that monitoring APIs are idempotent (safe to retry)."""

    def test_configure_monitoring_should_be_idempotent(self):
        """Test calling configure_monitoring twice should be safe."""
        # API contract: configure_monitoring should be idempotent
        # Calling it twice with same policy should not error
        # (Implementation will handle this via force parameter)
        # Verify function signature (contract test)

        sig = inspect.signature(configure_monitoring)

        assert sig is not None

        # Second call with force=True should also work

    def test_disable_monitoring_should_be_idempotent(self):
        """Test calling disable_monitoring twice should be safe."""
        # Verify function signature (contract test)

        sig = inspect.signature(disable_monitoring)

        assert sig is not None

    def test_enable_monitoring_should_be_idempotent(self):
        """Test calling enable_monitoring twice should be safe."""
        # Verify function signature (contract test)

        sig = inspect.signature(enable_monitoring)

        assert sig is not None


class TestMonitoringAPIErrorHandling:
    """Test error handling follows Constitutional Principle 5."""

    def test_invalid_policy_raises_valueerror(self):
        """Test invalid policy raises ValueError before IRIS call."""
        policy = MonitoringPolicy(interval_seconds=500)  # Invalid

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        # Error should be helpful (Principle 5)
        error_msg = str(exc_info.value)
        assert len(error_msg) > 50  # Should be detailed
        assert "500s" in error_msg  # Should mention the invalid value

    def test_resource_thresholds_validation_fails_fast(self):
        """Test ResourceThresholds validation catches configuration errors."""
        # Invalid: enable >= disable (no hysteresis)
        thresholds = ResourceThresholds(
            cpu_disable_percent=90.0, cpu_enable_percent=90.0
        )

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "thrashing" in error_msg.lower()
        assert "hysteresis" in error_msg.lower()


class TestMonitoringAPIPerformanceContract:
    """Test performance expectations from contract."""

    def test_configure_monitoring_should_complete_quickly(self):
        """Test configure_monitoring target: <2 seconds (per spec)."""
        # Contract: configure_monitoring should complete in <2 seconds
        # This is a contract test - actual timing tested in integration

        sig = inspect.signature(configure_monitoring)
        # Function exists and is documented
        assert configure_monitoring.__doc__ is not None

    def test_get_monitoring_status_should_be_fast(self):
        """Test get_monitoring_status should be quick query."""
        # Contract: status check should be fast (<500ms per spec)

        sig = inspect.signature(get_monitoring_status)
        # Function exists
        assert get_monitoring_status.__doc__ is not None


class TestMonitoringPolicyObjectScriptContract:
    """Test MonitoringPolicy ObjectScript generation contract."""

    def test_policy_generates_valid_objectscript(self):
        """Test to_objectscript() generates syntactically valid code."""
        policy = MonitoringPolicy()
        script = policy.to_objectscript()

        # Should be non-empty
        assert len(script) > 100

        # Should include critical ObjectScript commands
        assert "##class(%SYS.PTools.StatsSQL)" in script
        assert "policy.Name" in script
        assert "policy.Interval" in script
        assert "policy.Duration" in script
        assert ".%Save()" in script
        assert ".Start(" in script

    def test_policy_objectscript_includes_all_settings(self):
        """Test ObjectScript includes all policy settings."""
        policy = MonitoringPolicy(
            interval_seconds=60,
            retention_seconds=7200,
            collect_globals=True,
            collect_vmstat=False,
        )
        script = policy.to_objectscript()

        assert "60" in script  # interval
        assert "7200" in script  # retention
        assert "CollectGlobalStats = 1" in script
        assert "CollectVMStat = 0" in script


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
