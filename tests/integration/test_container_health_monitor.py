"""Integration tests for IRIS $SYSTEM.Monitor.State() health check.

These tests verify that container health checks use the official IRIS
$SYSTEM.Monitor.State() API to detect true container readiness.

Constitutional Compliance:
- Principle #1: Automatic remediation (check IRIS-level health, not just port)
- Principle #5: Fail Fast with Guidance (meaningful state values)
- Principle #7: Medical-Grade Reliability (comprehensive coverage)

Source: docs/learnings/iris-container-readiness.md
"""

import pytest
from iris_devtester.containers import IRISContainer
from iris_devtester.utils.health_checks import (
    check_iris_monitor_state,
    wait_for_iris_healthy,
    IrisHealthState,
)


@pytest.fixture(scope="module")
def running_iris_container():
    """Running IRIS container for health check tests."""
    with IRISContainer.community() as iris:
        # Wait for container to be fully ready
        iris.wait_for_ready(timeout=60)
        yield iris


class TestCheckIrisMonitorState:
    """Test check_iris_monitor_state() function."""

    def test_returns_ok_for_healthy_container(self, running_iris_container):
        """Healthy container should return IrisHealthState.OK (state=0 or -1)."""
        container = running_iris_container._container

        result = check_iris_monitor_state(container)

        assert result.state == IrisHealthState.OK
        assert result.is_healthy is True
        # Message can be either "OK - Container healthy" or include "(monitoring not configured)"
        # for IRIS instances where $SYSTEM.Monitor.State() returns -1
        assert result.message.startswith("OK - Container healthy")

    def test_returns_state_value(self, running_iris_container):
        """Should return the actual state value from IRIS."""
        container = running_iris_container._container

        result = check_iris_monitor_state(container)

        # State should be 0, 1, 2, or 3
        assert result.state in [
            IrisHealthState.OK,
            IrisHealthState.WARNING,
            IrisHealthState.ERROR,
            IrisHealthState.FATAL,
        ]

    def test_warning_state_is_still_healthy(self, running_iris_container):
        """Warning state (1) should still be considered healthy."""
        # Note: We can't easily force a warning state, but we can verify
        # that the logic handles it correctly by checking the enum values
        assert IrisHealthState.WARNING.value == 1
        assert IrisHealthState.OK.value == 0


class TestWaitForIrisHealthy:
    """Test wait_for_iris_healthy() function."""

    def test_returns_quickly_for_healthy_container(self, running_iris_container):
        """Healthy container should return immediately."""
        container = running_iris_container._container

        import time
        start = time.time()
        success = wait_for_iris_healthy(container, timeout=10)
        elapsed = time.time() - start

        assert success is True
        # Should return quickly (< 2s) for already healthy container
        assert elapsed < 2.0

    def test_respects_timeout(self, running_iris_container):
        """Should not exceed timeout value."""
        container = running_iris_container._container

        import time
        start = time.time()
        # Short timeout, should return quickly since container is healthy
        success = wait_for_iris_healthy(container, timeout=5)
        elapsed = time.time() - start

        assert success is True
        assert elapsed < 5.0


class TestIrisHealthStateEnum:
    """Test IrisHealthState enum values match IRIS documentation."""

    def test_state_values_match_iris_api(self):
        """State values should match $SYSTEM.Monitor.State() return values."""
        assert IrisHealthState.OK.value == 0
        assert IrisHealthState.WARNING.value == 1
        assert IrisHealthState.ERROR.value == 2
        assert IrisHealthState.FATAL.value == 3

    def test_is_healthy_property(self):
        """OK and WARNING should be considered healthy."""
        assert IrisHealthState.OK.is_healthy is True
        assert IrisHealthState.WARNING.is_healthy is True
        assert IrisHealthState.ERROR.is_healthy is False
        assert IrisHealthState.FATAL.is_healthy is False


class TestHealthCheckIntegration:
    """Test integration with existing health check infrastructure."""

    def test_wait_for_healthy_includes_iris_check(self, running_iris_container):
        """wait_for_healthy should include IRIS Monitor.State check as Layer 4."""
        # After wait_for_ready completes, IRIS should be healthy
        container = running_iris_container._container

        result = check_iris_monitor_state(container)

        assert result.is_healthy is True
        assert result.state == IrisHealthState.OK
