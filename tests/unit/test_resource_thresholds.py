"""
Unit tests for ResourceThresholds dataclass.

Tests validation, hysteresis logic, and auto-disable/enable decisions.
Constitutional Principle #1: Automatic Remediation - Auto-disable under pressure.
"""

import pytest
from iris_devtester.containers.monitoring import ResourceThresholds


class TestResourceThresholdsDefaults:
    """Test default values follow FR-017, FR-018."""

    def test_default_thresholds_match_specification(self):
        """Test defaults match spec (CPU 90%, memory 95%)."""
        thresholds = ResourceThresholds()

        # FR-017: Auto-disable thresholds
        assert thresholds.cpu_disable_percent == 90.0
        assert thresholds.memory_disable_percent == 95.0

        # FR-018: Auto-enable thresholds with hysteresis
        assert thresholds.cpu_enable_percent == 85.0
        assert thresholds.memory_enable_percent == 90.0

        # Check interval
        assert thresholds.check_interval_seconds == 60

    def test_default_thresholds_validate(self):
        """Test default thresholds pass validation."""
        thresholds = ResourceThresholds()
        # Should not raise
        thresholds.validate()


class TestResourceThresholdsValidation:
    """Test validation logic following Constitutional Principle #5: Fail Fast with Guidance."""

    def test_cpu_disable_too_low_raises_error(self):
        """Test CPU disable < 50% raises helpful error."""
        thresholds = ResourceThresholds(cpu_disable_percent=40.0)

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "CPU disable threshold must be 50-100%" in error_msg
        assert "What went wrong" in error_msg
        assert "How to fix it" in error_msg

    def test_cpu_disable_too_high_raises_error(self):
        """Test CPU disable > 100% raises error."""
        thresholds = ResourceThresholds(cpu_disable_percent=105.0)

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "CPU disable threshold must be 50-100%" in error_msg

    def test_memory_disable_too_low_raises_error(self):
        """Test memory disable < 50% raises helpful error."""
        thresholds = ResourceThresholds(memory_disable_percent=30.0)

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "Memory disable threshold must be 50-100%" in error_msg

    def test_memory_disable_too_high_raises_error(self):
        """Test memory disable > 100% raises error."""
        thresholds = ResourceThresholds(memory_disable_percent=110.0)

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "Memory disable threshold must be 50-100%" in error_msg

    def test_cpu_hysteresis_violation_raises_error(self):
        """Test CPU enable >= disable raises thrashing prevention error."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=90.0,
            cpu_enable_percent=90.0,  # Equal (no gap)
        )

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "prevent thrashing" in error_msg
        assert "cpu_enable_percent < cpu_disable_percent" in error_msg

    def test_memory_hysteresis_violation_raises_error(self):
        """Test memory enable >= disable raises thrashing prevention error."""
        thresholds = ResourceThresholds(
            memory_disable_percent=95.0,
            memory_enable_percent=96.0,  # Greater (inverted)
        )

        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()

        error_msg = str(exc_info.value)
        assert "prevent thrashing" in error_msg
        assert "memory_enable_percent < memory_disable_percent" in error_msg

    def test_boundary_values_validate(self):
        """Test boundary values pass validation."""
        # Minimum thresholds with hysteresis
        thresholds1 = ResourceThresholds(
            cpu_disable_percent=50.0,
            cpu_enable_percent=45.0,
            memory_disable_percent=50.0,
            memory_enable_percent=45.0,
        )
        thresholds1.validate()

        # Maximum thresholds with hysteresis
        thresholds2 = ResourceThresholds(
            cpu_disable_percent=100.0,
            cpu_enable_percent=95.0,
            memory_disable_percent=100.0,
            memory_enable_percent=95.0,
        )
        thresholds2.validate()


class TestResourceThresholdsDisableLogic:
    """Test should_disable() logic for FR-017."""

    def test_cpu_exceeds_threshold_triggers_disable(self):
        """Test CPU > 90% triggers disable."""
        thresholds = ResourceThresholds()

        # CPU at 95% (exceeds 90%)
        assert thresholds.should_disable(cpu_percent=95.0, memory_percent=50.0) is True

    def test_memory_exceeds_threshold_triggers_disable(self):
        """Test memory > 95% triggers disable."""
        thresholds = ResourceThresholds()

        # Memory at 98% (exceeds 95%)
        assert thresholds.should_disable(cpu_percent=50.0, memory_percent=98.0) is True

    def test_both_exceed_thresholds_triggers_disable(self):
        """Test both CPU and memory exceeding triggers disable."""
        thresholds = ResourceThresholds()

        assert thresholds.should_disable(cpu_percent=95.0, memory_percent=98.0) is True

    def test_below_thresholds_does_not_trigger_disable(self):
        """Test normal levels don't trigger disable."""
        thresholds = ResourceThresholds()

        # Both below thresholds
        assert thresholds.should_disable(cpu_percent=50.0, memory_percent=60.0) is False

    def test_exactly_at_threshold_does_not_trigger_disable(self):
        """Test exactly at threshold doesn't trigger (> not >=)."""
        thresholds = ResourceThresholds()

        # Exactly at thresholds
        assert thresholds.should_disable(cpu_percent=90.0, memory_percent=95.0) is False

    def test_custom_thresholds_work(self):
        """Test custom disable thresholds."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=80.0, memory_disable_percent=85.0
        )

        # Below custom thresholds
        assert thresholds.should_disable(cpu_percent=75.0, memory_percent=80.0) is False

        # Exceed custom thresholds
        assert thresholds.should_disable(cpu_percent=85.0, memory_percent=90.0) is True


class TestResourceThresholdsEnableLogic:
    """Test should_enable() logic for FR-018 with hysteresis."""

    def test_both_below_enable_thresholds_allows_enable(self):
        """Test CPU < 85% AND memory < 90% allows re-enable."""
        thresholds = ResourceThresholds()

        # Both below enable thresholds
        assert thresholds.should_enable(cpu_percent=80.0, memory_percent=85.0) is True

    def test_cpu_above_enable_threshold_prevents_enable(self):
        """Test CPU >= 85% prevents re-enable."""
        thresholds = ResourceThresholds()

        # CPU at 90%, memory OK
        assert thresholds.should_enable(cpu_percent=90.0, memory_percent=85.0) is False

    def test_memory_above_enable_threshold_prevents_enable(self):
        """Test memory >= 90% prevents re-enable."""
        thresholds = ResourceThresholds()

        # Memory at 92%, CPU OK
        assert thresholds.should_enable(cpu_percent=80.0, memory_percent=92.0) is False

    def test_both_above_enable_thresholds_prevents_enable(self):
        """Test both above prevents re-enable."""
        thresholds = ResourceThresholds()

        assert thresholds.should_enable(cpu_percent=88.0, memory_percent=93.0) is False

    def test_exactly_at_enable_threshold_prevents_enable(self):
        """Test exactly at threshold prevents enable (< not <=)."""
        thresholds = ResourceThresholds()

        # Exactly at enable thresholds
        assert thresholds.should_enable(cpu_percent=85.0, memory_percent=90.0) is False

    def test_custom_enable_thresholds_work(self):
        """Test custom enable thresholds."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=80.0,
            cpu_enable_percent=75.0,
            memory_disable_percent=85.0,
            memory_enable_percent=80.0,
        )

        # Below custom enable thresholds
        assert thresholds.should_enable(cpu_percent=70.0, memory_percent=75.0) is True

        # Above custom enable thresholds
        assert thresholds.should_enable(cpu_percent=78.0, memory_percent=83.0) is False


class TestResourceThresholdsHysteresis:
    """Test hysteresis prevents thrashing (FR-018)."""

    def test_hysteresis_gap_prevents_immediate_re_enable(self):
        """Test 5% gap prevents oscillation."""
        thresholds = ResourceThresholds()

        # CPU at 92% - should disable
        assert thresholds.should_disable(cpu_percent=92.0, memory_percent=80.0) is True

        # CPU drops to 88% - still can't re-enable (needs < 85%)
        assert thresholds.should_enable(cpu_percent=88.0, memory_percent=80.0) is False

        # CPU drops to 82% - now can re-enable
        assert thresholds.should_enable(cpu_percent=82.0, memory_percent=80.0) is True

    def test_scenario_disable_to_enable_cycle(self):
        """Test realistic disable → enable cycle with hysteresis."""
        thresholds = ResourceThresholds()

        # Normal operation (monitoring active)
        assert thresholds.should_disable(cpu_percent=70.0, memory_percent=80.0) is False

        # CPU spikes to 95% → disable monitoring
        assert thresholds.should_disable(cpu_percent=95.0, memory_percent=80.0) is True

        # CPU drops to 89% → still disabled (hysteresis)
        assert thresholds.should_enable(cpu_percent=89.0, memory_percent=80.0) is False

        # CPU drops to 84% → can re-enable
        assert thresholds.should_enable(cpu_percent=84.0, memory_percent=80.0) is True

        # Back to normal
        assert thresholds.should_disable(cpu_percent=84.0, memory_percent=80.0) is False


class TestResourceThresholdsCustomization:
    """Test FR-023: Users can override thresholds."""

    def test_can_customize_all_thresholds(self):
        """Test full threshold customization."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=80.0,
            cpu_enable_percent=70.0,
            memory_disable_percent=90.0,
            memory_enable_percent=80.0,
            check_interval_seconds=30,
        )

        thresholds.validate()
        assert thresholds.cpu_disable_percent == 80.0
        assert thresholds.check_interval_seconds == 30

    def test_aggressive_thresholds_work(self):
        """Test aggressive auto-disable (lower thresholds)."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=70.0,
            cpu_enable_percent=60.0,
            memory_disable_percent=75.0,
            memory_enable_percent=65.0,
        )

        thresholds.validate()

        # Should disable at lower levels
        assert thresholds.should_disable(cpu_percent=72.0, memory_percent=60.0) is True

    def test_conservative_thresholds_work(self):
        """Test conservative auto-disable (higher thresholds)."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=98.0,
            cpu_enable_percent=95.0,
            memory_disable_percent=99.0,
            memory_enable_percent=96.0,
        )

        thresholds.validate()

        # Should only disable at very high levels
        assert thresholds.should_disable(cpu_percent=95.0, memory_percent=92.0) is False
        assert thresholds.should_disable(cpu_percent=99.0, memory_percent=92.0) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
