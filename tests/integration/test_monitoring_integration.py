"""
Integration tests for IRIS Performance Monitoring with real containers.

Tests the full monitoring API stack against actual IRIS instances to verify
ObjectScript execution, Task Manager integration, and resource monitoring.

Constitutional Principle #7: Medical-Grade Reliability - Integration tests required.
"""

import pytest
import time
from datetime import datetime

from iris_devtester.containers.monitoring import (
    MonitoringPolicy,
    ResourceThresholds,
    configure_monitoring,
    get_monitoring_status,
    disable_monitoring,
    enable_monitoring,
    create_task,
    get_task_status,
    suspend_task,
    resume_task,
    delete_task,
    list_monitoring_tasks,
    TaskSchedule,
)
from iris_devtester.containers.performance import (
    get_resource_metrics,
    check_resource_thresholds,
    auto_disable_monitoring,
    auto_enable_monitoring,
)


pytestmark = pytest.mark.integration


# DEDICATED CONTAINER for monitoring tests
# Monitoring tests get their own container to avoid conflicts with DAT fixture tests
# Constitutional Principle #3: Isolation by Default

@pytest.fixture(scope="module")
def monitoring_container():
    """
    Dedicated IRIS container for monitoring tests only.

    Module-scoped so all monitoring tests share one container, but isolated
    from other test files that might pollute the shared session container.

    This prevents DAT fixture operations from breaking monitoring tests.
    """
    from iris_devtester.containers import IRISContainer

    with IRISContainer.community() as container:
        # Wait for IRIS to be ready
        container.wait_for_ready(timeout=60)

        # Enable CallIn service for DBAPI connections
        container.enable_callin_service()

        # Unexpire passwords
        from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords
        container_name = container.get_container_name()
        unexpire_all_passwords(container_name)

        yield container


@pytest.fixture(scope="function")
def iris_conn(monitoring_container):
    """
    IRIS connection for monitoring tests with ObjectScript execution capability.

    Uses dedicated monitoring_container (not shared iris_container) to avoid
    conflicts with DAT fixture tests that can leave the database in a bad state.

    Provides fresh connection AND cleans up monitoring state after each test.

    NOTE: This connection includes an `execute_objectscript()` method for running
    ObjectScript code. This is a TEST-ONLY workaround until Feature 003 implements
    proper ObjectScript execution via JDBC.
    """
    conn = monitoring_container.get_connection()

    # Add ObjectScript execution capability (TEST-ONLY workaround)
    # Uses container.execute_objectscript() under the hood
    def execute_objectscript(code):
        """Execute ObjectScript code via container exec (TEST-ONLY)."""
        return monitoring_container.execute_objectscript(code)

    # Attach method to connection
    conn.execute_objectscript = execute_objectscript

    yield conn

    # Cleanup: Disable monitoring and remove tasks to prevent state pollution
    # NOTE: Don't close connection - container manages connection lifecycle
    try:
        # Try to disable monitoring (may fail if not configured, that's OK)
        try:
            disable_monitoring(conn)
        except:
            pass

        # Delete all monitoring tasks created during test
        try:
            tasks = list_monitoring_tasks(conn)
            for task in tasks:
                if "task_id" in task:
                    try:
                        delete_task(conn, task["task_id"])
                    except:
                        pass
        except:
            pass

        # Don't close connection - let container manage it
        # Closing here breaks the next test because get_connection() caches it
    except:
        pass  # Ignore cleanup errors


class TestConfigureMonitoringIntegration:
    """Test configure_monitoring() with real IRIS."""

    def test_configure_with_default_policy(self, iris_conn):
        """Test zero-config monitoring setup."""
        # Configure with defaults (30s interval, 1hr retention)
        success, message = configure_monitoring(iris_conn)

        assert success is True
        assert "configured" in message.lower() or "active" in message.lower()

        # Verify monitoring is now active
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is True
        assert "profile_name" in status

    def test_configure_with_custom_policy(self, iris_conn):
        """Test custom policy configuration."""
        policy = MonitoringPolicy(
            name="test-custom-policy",
            interval_seconds=60,  # 1 minute
            retention_seconds=1800,  # 30 minutes
        )

        success, message = configure_monitoring(iris_conn, policy=policy, force=True)

        assert success is True
        assert "configured" in message.lower()

        # Verify custom policy is active
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is True

    def test_configure_is_idempotent(self, iris_conn):
        """Test calling configure_monitoring twice is safe."""
        # First call
        success1, msg1 = configure_monitoring(iris_conn)
        assert success1 is True

        # Second call (should detect already configured)
        success2, msg2 = configure_monitoring(iris_conn)
        assert success2 is True
        assert "already" in msg2.lower()

        # Force reconfigure
        success3, msg3 = configure_monitoring(iris_conn, force=True)
        assert success3 is True


class TestMonitoringStatusIntegration:
    """Test get_monitoring_status() with real IRIS."""

    def test_status_when_not_configured(self, iris_conn):
        """Test status returns disabled when no monitoring configured."""
        # First ensure monitoring is disabled
        disable_monitoring(iris_conn)

        is_running, status = get_monitoring_status(iris_conn)

        # Should return gracefully even if not configured
        assert isinstance(is_running, bool)
        assert isinstance(status, dict)

    def test_status_after_configuration(self, iris_conn):
        """Test status returns active after configuration."""
        # Configure monitoring
        configure_monitoring(iris_conn)

        is_running, status = get_monitoring_status(iris_conn)

        assert is_running is True
        assert "profile_name" in status
        assert status["profile_name"]  # Non-empty


class TestDisableEnableMonitoringIntegration:
    """Test disable/enable_monitoring() with real IRIS."""

    def test_disable_active_monitoring(self, iris_conn):
        """Test disabling active monitoring."""
        # Ensure monitoring is running
        configure_monitoring(iris_conn)

        # Disable it
        count = disable_monitoring(iris_conn)

        assert count > 0  # At least one task disabled

        # Verify disabled
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is False

    def test_enable_disabled_monitoring(self, iris_conn):
        """Test enabling disabled monitoring."""
        # Ensure monitoring exists but is disabled
        configure_monitoring(iris_conn)
        disable_monitoring(iris_conn)

        # Enable it
        count = enable_monitoring(iris_conn)

        assert count > 0  # At least one task enabled

        # Verify enabled
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is True

    def test_disable_is_idempotent(self, iris_conn):
        """Test calling disable_monitoring twice is safe."""
        configure_monitoring(iris_conn)

        count1 = disable_monitoring(iris_conn)
        assert count1 > 0

        count2 = disable_monitoring(iris_conn)
        # Should still succeed (idempotent)
        assert count2 >= 0

    def test_enable_is_idempotent(self, iris_conn):
        """Test calling enable_monitoring twice is safe."""
        configure_monitoring(iris_conn)

        count1 = enable_monitoring(iris_conn)
        assert count1 >= 0

        count2 = enable_monitoring(iris_conn)
        # Should still succeed (idempotent)
        assert count2 >= 0


class TestTaskManagerIntegration:
    """Test Task Manager API functions with real IRIS."""

    def test_create_task_with_default_schedule(self, iris_conn):
        """Test creating task with default schedule."""
        schedule = TaskSchedule()

        task_id = create_task(iris_conn, schedule)

        assert task_id
        assert isinstance(task_id, str)
        assert task_id.isdigit()  # Task IDs are numeric strings

    def test_create_task_with_custom_schedule(self, iris_conn):
        """Test creating task with custom settings."""
        schedule = TaskSchedule(
            name="test-custom-task",
            daily_increment=120,  # 2 minutes
            description="Custom test task",
        )

        task_id = create_task(iris_conn, schedule)

        assert task_id
        assert isinstance(task_id, str)

        # Clean up
        delete_task(iris_conn, task_id)

    def test_get_task_status(self, iris_conn):
        """Test retrieving task status."""
        # Create a task
        schedule = TaskSchedule(name="test-status-task")
        task_id = create_task(iris_conn, schedule)

        # Get status
        status = get_task_status(iris_conn, task_id)

        assert status["task_id"] == task_id
        assert status["name"] == "test-status-task"
        assert isinstance(status["suspended"], bool)
        assert status["task_class"] == "%SYS.Task.SystemPerformance"
        assert status["daily_increment"] > 0

        # Clean up
        delete_task(iris_conn, task_id)

    def test_suspend_and_resume_task(self, iris_conn):
        """Test suspending and resuming a task."""
        # Create active task
        schedule = TaskSchedule(name="test-suspend-task", suspended=False)
        task_id = create_task(iris_conn, schedule)

        # Suspend it
        success = suspend_task(iris_conn, task_id)
        assert success is True

        # Verify suspended
        status = get_task_status(iris_conn, task_id)
        assert status["suspended"] is True

        # Resume it
        success = resume_task(iris_conn, task_id)
        assert success is True

        # Verify resumed
        status = get_task_status(iris_conn, task_id)
        assert status["suspended"] is False

        # Clean up
        delete_task(iris_conn, task_id)

    def test_delete_task(self, iris_conn):
        """Test deleting a task."""
        # Create task
        schedule = TaskSchedule(name="test-delete-task")
        task_id = create_task(iris_conn, schedule)

        # Delete it
        success = delete_task(iris_conn, task_id)
        assert success is True

        # Verify deleted (should raise error)
        with pytest.raises(RuntimeError, match="not found"):
            get_task_status(iris_conn, task_id)

    def test_list_monitoring_tasks(self, iris_conn):
        """Test listing all monitoring tasks."""
        # Create a couple tasks
        task_id1 = create_task(iris_conn, TaskSchedule(name="list-test-1"))
        task_id2 = create_task(iris_conn, TaskSchedule(name="list-test-2"))

        # List tasks
        tasks = list_monitoring_tasks(iris_conn)

        assert len(tasks) >= 2
        task_ids = [t["task_id"] for t in tasks]
        assert task_id1 in task_ids
        assert task_id2 in task_ids

        # Verify task details
        for task in tasks:
            assert "task_id" in task
            assert "name" in task
            assert "suspended" in task
            assert "task_class" in task
            assert task["task_class"] == "%SYS.Task.SystemPerformance"

        # Clean up
        delete_task(iris_conn, task_id1)
        delete_task(iris_conn, task_id2)


class TestResourceMonitoringIntegration:
    """Test resource monitoring functions with real IRIS."""

    def test_get_resource_metrics(self, iris_conn):
        """Test getting current resource metrics."""
        metrics = get_resource_metrics(iris_conn)

        assert metrics.timestamp is not None
        assert isinstance(metrics.timestamp, datetime)
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.global_references >= 0
        assert metrics.lock_requests >= 0
        assert metrics.disk_reads >= 0
        assert metrics.disk_writes >= 0
        assert isinstance(metrics.monitoring_enabled, bool)

    def test_check_resource_thresholds_normal(self, iris_conn):
        """Test threshold checking under normal load."""
        thresholds = ResourceThresholds()

        should_disable, should_enable, metrics = check_resource_thresholds(
            iris_conn, thresholds
        )

        # Under normal load, should not trigger disable
        assert isinstance(should_disable, bool)
        assert isinstance(should_enable, bool)
        assert metrics is not None

        # At least one should be False (can't both be True)
        assert not (should_disable and should_enable)

    def test_check_resource_thresholds_aggressive(self, iris_conn):
        """Test with aggressive thresholds (should allow enable)."""
        # Very aggressive thresholds - almost always below
        thresholds = ResourceThresholds(
            cpu_disable_percent=99.0,
            memory_disable_percent=99.0,
            cpu_enable_percent=98.0,
            memory_enable_percent=98.0,
        )

        should_disable, should_enable, metrics = check_resource_thresholds(
            iris_conn, thresholds
        )

        # Should not trigger disable with aggressive thresholds
        assert should_disable is False
        # Should allow enable
        assert should_enable is True

    def test_auto_disable_monitoring(self, iris_conn):
        """Test auto-disable under simulated pressure."""
        # Ensure monitoring is running
        configure_monitoring(iris_conn)

        # Auto-disable
        success = auto_disable_monitoring(iris_conn, reason="Test: Simulated CPU spike")

        assert success is True

        # Verify disabled
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is False

    def test_auto_enable_monitoring(self, iris_conn):
        """Test auto-enable after recovery."""
        # Ensure monitoring exists but is disabled
        configure_monitoring(iris_conn)
        disable_monitoring(iris_conn)

        # Auto-enable
        success = auto_enable_monitoring(iris_conn)

        assert success is True

        # Verify enabled
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is True


class TestMonitoringEndToEndScenarios:
    """End-to-end scenarios testing full workflows."""

    def test_complete_monitoring_lifecycle(self, iris_conn):
        """Test complete lifecycle: configure -> monitor -> disable -> enable."""
        # Step 1: Configure monitoring
        success, msg = configure_monitoring(iris_conn)
        assert success is True

        # Step 2: Verify active
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is True

        # Step 3: Get metrics while running
        metrics = get_resource_metrics(iris_conn)
        assert metrics.monitoring_enabled is True

        # Step 4: Disable monitoring
        count = disable_monitoring(iris_conn)
        assert count > 0

        # Step 5: Verify disabled
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is False

        # Step 6: Re-enable
        count = enable_monitoring(iris_conn)
        assert count > 0

        # Step 7: Verify active again
        is_running, status = get_monitoring_status(iris_conn)
        assert is_running is True

    def test_auto_remediation_cycle(self, iris_conn):
        """Test automatic disable/enable cycle (Principle #1)."""
        # Configure monitoring
        configure_monitoring(iris_conn)

        # Simulate high load -> auto-disable
        success = auto_disable_monitoring(iris_conn, reason="CPU >90%")
        assert success is True

        # Verify disabled
        is_running, _ = get_monitoring_status(iris_conn)
        assert is_running is False

        # Wait a moment (simulate recovery time)
        time.sleep(1)

        # Simulate recovery -> auto-enable
        success = auto_enable_monitoring(iris_conn)
        assert success is True

        # Verify enabled
        is_running, _ = get_monitoring_status(iris_conn)
        assert is_running is True

    def test_task_manager_full_workflow(self, iris_conn):
        """Test full Task Manager workflow."""
        # Create task
        schedule = TaskSchedule(name="workflow-test", daily_increment=60)
        task_id = create_task(iris_conn, schedule)
        assert task_id

        # Get status (should be active)
        status = get_task_status(iris_conn, task_id)
        assert status["suspended"] is False

        # Suspend
        suspend_task(iris_conn, task_id)
        status = get_task_status(iris_conn, task_id)
        assert status["suspended"] is True

        # Resume
        resume_task(iris_conn, task_id)
        status = get_task_status(iris_conn, task_id)
        assert status["suspended"] is False

        # Delete
        delete_task(iris_conn, task_id)

        # Verify deleted
        with pytest.raises(RuntimeError):
            get_task_status(iris_conn, task_id)


class TestMonitoringPerformance:
    """Test performance characteristics of monitoring APIs."""

    def test_get_resource_metrics_is_fast(self, iris_conn):
        """Test resource metrics query completes in <100ms."""
        start = time.time()
        metrics = get_resource_metrics(iris_conn)
        elapsed = time.time() - start

        assert metrics is not None
        assert elapsed < 0.1  # <100ms target

    def test_check_thresholds_is_very_fast(self, iris_conn):
        """Test threshold check (mostly in-memory) is very fast."""
        thresholds = ResourceThresholds()

        start = time.time()
        should_disable, should_enable, metrics = check_resource_thresholds(
            iris_conn, thresholds
        )
        elapsed = time.time() - start

        assert metrics is not None
        assert elapsed < 0.2  # <200ms (includes metrics fetch)

    def test_configure_monitoring_completes_quickly(self, iris_conn):
        """Test configure_monitoring completes in <2 seconds."""
        start = time.time()
        success, msg = configure_monitoring(iris_conn, force=True)
        elapsed = time.time() - start

        assert success is True
        assert elapsed < 2.0  # <2s target


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
