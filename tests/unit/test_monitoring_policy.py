"""
Unit tests for MonitoringPolicy dataclass.

Tests validation logic, defaults, and ObjectScript generation.
Constitutional Principle #7: Medical-Grade Reliability - All error paths tested.
"""

import pytest
from iris_devtester.containers.monitoring import MonitoringPolicy, CollectionInterval


class TestMonitoringPolicyDefaults:
    """Test default values follow Constitutional Principle #4: Zero Configuration Viable."""

    def test_default_policy_has_sensible_values(self):
        """Test that default policy works without configuration."""
        policy = MonitoringPolicy()

        # FR-002: Default 30-second interval
        assert policy.interval_seconds == 30
        # FR-003: Default 1-hour retention
        assert policy.retention_seconds == 3600
        assert policy.continuous is True
        assert policy.name == "iris-devtester-default"

    def test_default_policy_collects_all_metrics(self):
        """Test that default policy enables comprehensive monitoring."""
        policy = MonitoringPolicy()

        assert policy.collect_globals is True
        assert policy.collect_system is True
        assert policy.collect_processes is True
        assert policy.collect_sql is True
        assert policy.collect_locks is True
        assert policy.collect_vmstat is True
        assert policy.collect_iostat is True
        assert policy.collect_perfmon is True

    def test_default_policy_validates_successfully(self):
        """Test that default policy passes validation."""
        policy = MonitoringPolicy()
        # Should not raise
        policy.validate()


class TestMonitoringPolicyValidation:
    """Test validation logic following Constitutional Principle #5: Fail Fast with Guidance."""

    def test_interval_too_low_raises_helpful_error(self):
        """Test interval < 1 second raises clear error."""
        policy = MonitoringPolicy(interval_seconds=0)

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        error_msg = str(exc_info.value)
        assert "Collection interval 0s invalid" in error_msg
        assert "What went wrong" in error_msg
        assert "How to fix it" in error_msg
        assert "1-300s" in error_msg

    def test_interval_too_high_raises_helpful_error(self):
        """Test interval > 300 seconds raises clear error (FR-021)."""
        policy = MonitoringPolicy(interval_seconds=400)

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        error_msg = str(exc_info.value)
        assert "Collection interval 400s invalid" in error_msg
        assert "1-300s" in error_msg

    def test_retention_too_low_raises_helpful_error(self):
        """Test retention < 5 minutes raises clear error (FR-022)."""
        policy = MonitoringPolicy(retention_seconds=60)  # 1 minute

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        error_msg = str(exc_info.value)
        assert "Retention period 60s invalid" in error_msg
        assert "What went wrong" in error_msg
        assert "How to fix it" in error_msg
        assert "300-86400s" in error_msg

    def test_retention_too_high_raises_helpful_error(self):
        """Test retention > 24 hours raises clear error (FR-022)."""
        policy = MonitoringPolicy(retention_seconds=100000)  # > 24 hours

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        error_msg = str(exc_info.value)
        assert "Retention period 100000s invalid" in error_msg
        assert "300-86400s" in error_msg

    def test_relative_output_path_raises_error(self):
        """Test relative output path raises error."""
        policy = MonitoringPolicy(output_directory="relative/path")

        with pytest.raises(ValueError) as exc_info:
            policy.validate()

        error_msg = str(exc_info.value)
        assert "must be absolute path" in error_msg

    def test_valid_custom_policy_validates(self):
        """Test custom policy with valid values passes validation."""
        policy = MonitoringPolicy(
            interval_seconds=60,  # 1 minute
            retention_seconds=7200,  # 2 hours
            output_directory="/custom/path",
        )

        # Should not raise
        policy.validate()

    def test_boundary_values_validate(self):
        """Test boundary values (1s, 300s, 5min, 24hr) pass validation."""
        # Minimum interval, minimum retention
        policy1 = MonitoringPolicy(interval_seconds=1, retention_seconds=300)
        policy1.validate()

        # Maximum interval, maximum retention
        policy2 = MonitoringPolicy(interval_seconds=300, retention_seconds=86400)
        policy2.validate()


class TestMonitoringPolicyObjectScript:
    """Test ObjectScript generation for IRIS execution."""

    def test_to_objectscript_includes_policy_name(self):
        """Test ObjectScript includes policy name."""
        policy = MonitoringPolicy(name="test-policy")
        script = policy.to_objectscript()

        assert 'policy.Name = "test-policy"' in script

    def test_to_objectscript_includes_interval_and_retention(self):
        """Test ObjectScript includes collection settings."""
        policy = MonitoringPolicy(interval_seconds=60, retention_seconds=7200)
        script = policy.to_objectscript()

        assert "policy.Interval = 60" in script
        assert "policy.Duration = 7200" in script

    def test_to_objectscript_sets_continuous_mode(self):
        """Test ObjectScript sets continuous runtime."""
        policy = MonitoringPolicy(continuous=True)
        script = policy.to_objectscript()

        assert 'policy.RunTime = "continuous"' in script

    def test_to_objectscript_sets_once_mode(self):
        """Test ObjectScript sets once runtime when not continuous."""
        policy = MonitoringPolicy(continuous=False)
        script = policy.to_objectscript()

        assert 'policy.RunTime = "once"' in script

    def test_to_objectscript_includes_collection_flags(self):
        """Test ObjectScript includes all collection enable/disable flags."""
        policy = MonitoringPolicy(
            collect_globals=True,
            collect_system=False,
            collect_vmstat=True,
            collect_iostat=False,
        )
        script = policy.to_objectscript()

        assert "policy.CollectGlobalStats = 1" in script
        assert "policy.CollectSystemStats = 0" in script
        assert "policy.CollectVMStat = 1" in script
        assert "policy.CollectIOStat = 0" in script

    def test_to_objectscript_includes_output_settings(self):
        """Test ObjectScript includes output format and directory."""
        policy = MonitoringPolicy(
            output_format="HTML", output_directory="/tmp/iris-performance/"
        )
        script = policy.to_objectscript()

        assert 'policy.OutputFormat = "HTML"' in script
        assert 'policy.OutputDirectory = "/tmp/iris-performance/"' in script

    def test_to_objectscript_starts_monitoring(self):
        """Test ObjectScript includes Start() call."""
        policy = MonitoringPolicy(name="test-policy")
        script = policy.to_objectscript()

        assert "##class(%SYS.PTools.StatsSQL).Start(policy.Name)" in script


class TestCollectionIntervalEnum:
    """Test CollectionInterval enum for predefined values."""

    def test_predefined_intervals_exist(self):
        """Test all predefined intervals are available."""
        assert CollectionInterval.SECOND_1.value == 1
        assert CollectionInterval.SECOND_5.value == 5
        assert CollectionInterval.SECOND_10.value == 10
        assert CollectionInterval.SECOND_30.value == 30
        assert CollectionInterval.MINUTE_1.value == 60
        assert CollectionInterval.MINUTE_5.value == 300

    def test_can_use_enum_in_policy(self):
        """Test enum values work with MonitoringPolicy."""
        policy = MonitoringPolicy(interval_seconds=CollectionInterval.SECOND_30.value)
        assert policy.interval_seconds == 30
        policy.validate()


class TestMonitoringPolicyCustomization:
    """Test Constitutional Principle #4: Zero Config Viable but customizable."""

    def test_can_disable_specific_metrics(self):
        """Test selective metric collection."""
        policy = MonitoringPolicy(
            collect_vmstat=False,  # Disable OS metrics
            collect_iostat=False,
            collect_perfmon=False,
        )

        assert policy.collect_globals is True  # Still enabled
        assert policy.collect_vmstat is False
        assert policy.collect_iostat is False

    def test_can_customize_all_parameters(self):
        """Test full customization works."""
        policy = MonitoringPolicy(
            name="custom-monitoring",
            description="Custom monitoring policy",
            interval_seconds=120,
            retention_seconds=14400,  # 4 hours
            continuous=True,
            collect_globals=True,
            collect_system=True,
            collect_processes=False,
            collect_sql=True,
            collect_locks=False,
            collect_vmstat=True,
            collect_iostat=True,
            collect_perfmon=False,
            output_format="HTML",
            output_directory="/custom/monitoring/",
        )

        policy.validate()
        assert policy.name == "custom-monitoring"
        assert policy.interval_seconds == 120
        assert policy.collect_processes is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
