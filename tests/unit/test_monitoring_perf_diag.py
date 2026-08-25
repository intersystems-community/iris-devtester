"""
Unit tests for monitoring, performance, and diagnostics modules.

Tests cover:
- iris_devtester.containers.monitoring (CollectionInterval, policies, task management)
- iris_devtester.containers.performance (resource metrics, auto-disable/enable)
- iris_devtester.diagnostics (ConnectionProbe, probe_connection, diagnostics)
- iris_devtester.containers.monitor_utils (MonitoringStatus, %Monitor.System queries)

All tests use MagicMock for connections; no Docker or IRIS required.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from iris_devtester.containers.monitoring import (
    CollectionInterval,
    MonitoringPolicy,
    TaskSchedule,
    ResourceThresholds,
    CPFParameters,
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
)
from iris_devtester.containers.performance import (
    PerformanceMetrics,
    get_resource_metrics,
    check_resource_thresholds,
    auto_disable_monitoring,
    auto_enable_monitoring,
)
from iris_devtester.diagnostics import (
    ConnectionProbe,
    ConnectionDiagnosticError,
    probe_connection,
    build_diagnostic_error,
    _extract_sqlcode,
    _extract_table_name,
)
from iris_devtester.containers.monitor_utils import (
    MonitoringStatus,
    check_monitor_tables,
    is_monitor_collecting,
    get_monitor_samples,
    get_monitoring_status as get_monitoring_status_utils,
)


# ============================================================================
# CollectionInterval Tests
# ============================================================================


class TestCollectionInterval:
    """Test CollectionInterval enum values."""

    def test_enum_values(self):
        """Verify all interval constants have correct second values."""
        assert CollectionInterval.SECOND_1.value == 1
        assert CollectionInterval.SECOND_5.value == 5
        assert CollectionInterval.SECOND_10.value == 10
        assert CollectionInterval.SECOND_30.value == 30
        assert CollectionInterval.MINUTE_1.value == 60
        assert CollectionInterval.MINUTE_5.value == 300

    def test_enum_iteration(self):
        """Verify all intervals can be iterated."""
        intervals = list(CollectionInterval)
        assert len(intervals) == 6


# ============================================================================
# MonitoringPolicy Tests
# ============================================================================


class TestMonitoringPolicy:
    """Test MonitoringPolicy configuration and validation."""

    def test_default_construction(self):
        """Verify defaults match constitutional requirements."""
        policy = MonitoringPolicy()
        assert policy.name == "iris-devtester-default"
        assert policy.interval_seconds == 30
        assert policy.retention_seconds == 3600
        assert policy.continuous is True
        assert policy.collect_globals is True
        assert policy.collect_system is True
        assert policy.collect_processes is True
        assert policy.collect_sql is True
        assert policy.collect_locks is True
        assert policy.task_id is None
        assert policy.output_directory == "/tmp/iris-performance/"

    def test_custom_construction(self):
        """Verify custom parameters override defaults."""
        policy = MonitoringPolicy(
            name="custom-policy",
            interval_seconds=10,
            retention_seconds=7200,
            continuous=False,
        )
        assert policy.name == "custom-policy"
        assert policy.interval_seconds == 10
        assert policy.retention_seconds == 7200
        assert policy.continuous is False

    def test_validate_success_default(self):
        """Verify default policy passes validation."""
        policy = MonitoringPolicy()
        policy.validate()  # Should not raise

    def test_validate_interval_too_low(self):
        """Verify interval < 1 second raises ValueError."""
        policy = MonitoringPolicy(interval_seconds=0)
        with pytest.raises(ValueError) as exc_info:
            policy.validate()
        assert "Collection interval" in str(exc_info.value)
        assert "1-300" in str(exc_info.value)

    def test_validate_interval_too_high(self):
        """Verify interval > 300 seconds raises ValueError."""
        policy = MonitoringPolicy(interval_seconds=301)
        with pytest.raises(ValueError) as exc_info:
            policy.validate()
        assert "Collection interval" in str(exc_info.value)

    def test_validate_retention_too_low(self):
        """Verify retention < 5 minutes raises ValueError."""
        policy = MonitoringPolicy(retention_seconds=299)
        with pytest.raises(ValueError) as exc_info:
            policy.validate()
        assert "Retention period" in str(exc_info.value)

    def test_validate_retention_too_high(self):
        """Verify retention > 24 hours raises ValueError."""
        policy = MonitoringPolicy(retention_seconds=86401)
        with pytest.raises(ValueError) as exc_info:
            policy.validate()
        assert "Retention period" in str(exc_info.value)

    def test_validate_output_directory_relative(self):
        """Verify relative output directory raises ValueError."""
        policy = MonitoringPolicy(output_directory="tmp/iris-performance/")
        with pytest.raises(ValueError) as exc_info:
            policy.validate()
        assert "absolute path" in str(exc_info.value)

    def test_to_objectscript(self):
        """Verify ObjectScript generation includes policy fields."""
        policy = MonitoringPolicy(
            name="test-policy",
            description="Test description",
            interval_seconds=60,
            retention_seconds=7200,
        )
        os_code = policy.to_objectscript()
        assert "test-policy" in os_code
        assert "Test description" in os_code
        assert "60" in os_code
        assert "7200" in os_code
        assert "CollectGlobalStats" in os_code


# ============================================================================
# TaskSchedule Tests
# ============================================================================


class TestTaskSchedule:
    """Test TaskSchedule configuration."""

    def test_default_construction(self):
        """Verify task defaults."""
        schedule = TaskSchedule()
        assert schedule.name == "iris-devtester-monitor"
        assert schedule.task_class == "%SYS.Task.SystemPerformance"
        assert schedule.run_as_user == "_SYSTEM"
        assert schedule.suspended is False
        assert schedule.daily_frequency == 1
        assert schedule.daily_increment == 30
        assert schedule.daily_increment_unit == "Second"

    def test_to_objectscript(self):
        """Verify ObjectScript task creation."""
        schedule = TaskSchedule(
            name="my-task",
            description="My task",
            daily_increment=60,
        )
        os_code = schedule.to_objectscript()
        assert "my-task" in os_code
        assert "My task" in os_code
        assert "60" in os_code

    def test_disable_without_task_id(self):
        """Verify disable() raises ValueError without task_id."""
        schedule = TaskSchedule()
        with pytest.raises(ValueError) as exc_info:
            schedule.disable()
        assert "task_id" in str(exc_info.value)

    def test_disable_with_task_id(self):
        """Verify disable() generates ObjectScript with task_id."""
        schedule = TaskSchedule(task_id="123")
        os_code = schedule.disable()
        assert "123" in os_code
        assert "Suspended = 1" in os_code

    def test_enable_without_task_id(self):
        """Verify enable() raises ValueError without task_id."""
        schedule = TaskSchedule()
        with pytest.raises(ValueError) as exc_info:
            schedule.enable()
        assert "task_id" in str(exc_info.value)

    def test_enable_with_task_id(self):
        """Verify enable() generates ObjectScript with task_id."""
        schedule = TaskSchedule(task_id="456")
        os_code = schedule.enable()
        assert "456" in os_code
        assert "Suspended = 0" in os_code


# ============================================================================
# ResourceThresholds Tests
# ============================================================================


class TestResourceThresholds:
    """Test ResourceThresholds validation and logic."""

    def test_default_construction(self):
        """Verify default thresholds."""
        thresholds = ResourceThresholds()
        assert thresholds.cpu_disable_percent == 90.0
        assert thresholds.memory_disable_percent == 95.0
        assert thresholds.cpu_enable_percent == 85.0
        assert thresholds.memory_enable_percent == 90.0
        assert thresholds.check_interval_seconds == 60

    def test_validate_success_default(self):
        """Verify default thresholds pass validation."""
        thresholds = ResourceThresholds()
        thresholds.validate()  # Should not raise

    def test_validate_cpu_disable_too_low(self):
        """Verify CPU disable < 50% raises ValueError."""
        thresholds = ResourceThresholds(cpu_disable_percent=49.0)
        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()
        assert "CPU disable" in str(exc_info.value)

    def test_validate_cpu_disable_too_high(self):
        """Verify CPU disable > 100% raises ValueError."""
        thresholds = ResourceThresholds(cpu_disable_percent=101.0)
        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()
        assert "CPU disable" in str(exc_info.value)

    def test_validate_memory_disable_too_low(self):
        """Verify memory disable < 50% raises ValueError."""
        thresholds = ResourceThresholds(memory_disable_percent=49.0)
        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()
        assert "Memory disable" in str(exc_info.value)

    def test_validate_hysteresis_cpu_invalid(self):
        """Verify hysteresis validation prevents thrashing."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=90.0,
            cpu_enable_percent=91.0,  # enable >= disable
        )
        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()
        assert "hysteresis" in str(exc_info.value).lower()

    def test_validate_hysteresis_memory_invalid(self):
        """Verify memory hysteresis prevents thrashing."""
        thresholds = ResourceThresholds(
            memory_disable_percent=95.0,
            memory_enable_percent=96.0,  # enable >= disable
        )
        with pytest.raises(ValueError) as exc_info:
            thresholds.validate()
        assert "hysteresis" in str(exc_info.value).lower()

    def test_should_disable_cpu_exceeds(self):
        """Verify should_disable returns True when CPU exceeds threshold."""
        thresholds = ResourceThresholds(cpu_disable_percent=90.0)
        assert thresholds.should_disable(cpu_percent=91.0, memory_percent=50.0) is True

    def test_should_disable_memory_exceeds(self):
        """Verify should_disable returns True when memory exceeds threshold."""
        thresholds = ResourceThresholds(memory_disable_percent=95.0)
        assert thresholds.should_disable(cpu_percent=50.0, memory_percent=96.0) is True

    def test_should_disable_both_ok(self):
        """Verify should_disable returns False when both below threshold."""
        thresholds = ResourceThresholds(
            cpu_disable_percent=90.0,
            memory_disable_percent=95.0,
        )
        assert thresholds.should_disable(cpu_percent=80.0, memory_percent=90.0) is False

    def test_should_enable_cpu_recovered(self):
        """Verify should_enable returns True when CPU below enable threshold."""
        thresholds = ResourceThresholds(cpu_enable_percent=85.0)
        assert thresholds.should_enable(cpu_percent=80.0, memory_percent=80.0) is True

    def test_should_enable_memory_recovered(self):
        """Verify should_enable returns True when memory below enable threshold."""
        thresholds = ResourceThresholds(memory_enable_percent=90.0)
        assert thresholds.should_enable(cpu_percent=80.0, memory_percent=85.0) is True

    def test_should_enable_cpu_still_high(self):
        """Verify should_enable returns False when CPU still high."""
        thresholds = ResourceThresholds(
            cpu_enable_percent=85.0,
            memory_enable_percent=90.0,
        )
        assert thresholds.should_enable(cpu_percent=87.0, memory_percent=80.0) is False


# ============================================================================
# CPFParameters Tests
# ============================================================================


class TestCPFParameters:
    """Test CPF configuration parameters."""

    def test_default_construction(self):
        """Verify CPF defaults."""
        params = CPFParameters()
        assert params.performance_stats_enabled is True
        assert params.gm_heap_size_mb == 64
        assert params.routine_buffer_kb == 100000
        assert params.locale == "en_US.UTF-8"

    def test_to_objectscript(self):
        """Verify CPF ObjectScript generation."""
        params = CPFParameters(
            performance_stats_enabled=True,
            gm_heap_size_mb=128,
        )
        os_code = params.to_objectscript()
        assert "PerformanceStats = 1" in os_code
        assert "128" in os_code

    def test_to_dict(self):
        """Verify CPF export as dictionary."""
        params = CPFParameters(gm_heap_size_mb=256)
        params_dict = params.to_dict()
        assert params_dict["performance_stats_enabled"] is True
        assert params_dict["gm_heap_size_mb"] == 256
        assert params_dict["locale"] == "en_US.UTF-8"


# ============================================================================
# Monitoring Functions Tests
# ============================================================================


class TestConfigureMonitoring:
    """Test configure_monitoring() function."""

    def test_configure_with_default_policy(self):
        """Verify configure_monitoring with default policy."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        conn.execute_objectscript = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = []
            with patch("iris_devtester.containers.monitoring.create_task") as mock_create:
                mock_create.return_value = "1"
                success, msg = configure_monitoring(conn)

        assert success is True
        assert "iris-devtester-default" in msg
        conn.execute_objectscript.assert_called_once()

    def test_configure_with_custom_policy(self):
        """Verify configure_monitoring with custom policy."""
        policy = MonitoringPolicy(
            name="custom",
            interval_seconds=10,
        )
        conn = MagicMock()
        conn.execute_objectscript = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = []
            with patch("iris_devtester.containers.monitoring.create_task") as mock_create:
                mock_create.return_value = "2"
                success, msg = configure_monitoring(conn, policy=policy)

        assert success is True
        assert "custom" in msg

    def test_configure_already_running(self):
        """Verify configure_monitoring with force=False when already running."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = [{"task_id": "1", "suspended": False}]
            success, msg = configure_monitoring(conn, force=False)

        assert success is True
        assert "already" in msg.lower()
        conn.execute_objectscript.assert_not_called()

    def test_configure_policy_validation_error(self):
        """Verify configure_monitoring raises on invalid policy."""
        policy = MonitoringPolicy(interval_seconds=999)  # Invalid
        conn = MagicMock()

        with pytest.raises(ValueError):
            configure_monitoring(conn, policy=policy)

    def test_configure_no_objectscript_support(self):
        """Verify configure_monitoring raises RuntimeError without ObjectScript."""
        conn = MagicMock(spec=[])  # No execute_objectscript method

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = []
            with pytest.raises(RuntimeError) as exc_info:
                configure_monitoring(conn)

        assert "ObjectScript" in str(exc_info.value)


class TestGetMonitoringStatus:
    """Test get_monitoring_status() function."""

    def test_get_status_no_tasks(self):
        """Verify get_monitoring_status returns disabled when no tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = []
            is_running, status = get_monitoring_status(conn)

        assert is_running is False
        assert status["enabled"] == 0

    def test_get_status_with_active_tasks(self):
        """Verify get_monitoring_status returns enabled with active tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = [
                {"task_id": "1", "suspended": False},
            ]
            is_running, status = get_monitoring_status(conn)

        assert is_running is True
        assert status["enabled"] == 1

    def test_get_status_with_suspended_tasks(self):
        """Verify get_monitoring_status returns disabled with suspended tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = [
                {"task_id": "1", "suspended": True},
            ]
            is_running, status = get_monitoring_status(conn)

        assert is_running is False


class TestDisableMonitoring:
    """Test disable_monitoring() function."""

    def test_disable_no_tasks(self):
        """Verify disable_monitoring returns 0 when no tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = []
            count = disable_monitoring(conn)

        assert count == 0

    def test_disable_active_tasks(self):
        """Verify disable_monitoring suspends active tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = [
                {"task_id": "1", "suspended": False},
                {"task_id": "2", "suspended": False},
            ]
            with patch("iris_devtester.containers.monitoring.suspend_task") as mock_suspend:
                mock_suspend.return_value = True
                count = disable_monitoring(conn)

        assert count == 2
        assert mock_suspend.call_count == 2

    def test_disable_skips_already_suspended(self):
        """Verify disable_monitoring skips already suspended tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = [
                {"task_id": "1", "suspended": True},
                {"task_id": "2", "suspended": False},
            ]
            with patch("iris_devtester.containers.monitoring.suspend_task") as mock_suspend:
                mock_suspend.return_value = True
                count = disable_monitoring(conn)

        assert count == 1


class TestEnableMonitoring:
    """Test enable_monitoring() function."""

    def test_enable_no_tasks(self):
        """Verify enable_monitoring raises when no tasks configured."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = []
            with pytest.raises(RuntimeError) as exc_info:
                enable_monitoring(conn)

        assert "No monitoring tasks" in str(exc_info.value)

    def test_enable_suspended_tasks(self):
        """Verify enable_monitoring resumes suspended tasks."""
        conn = MagicMock()

        with patch("iris_devtester.containers.monitoring.list_monitoring_tasks") as mock_list:
            mock_list.return_value = [
                {"task_id": "1", "suspended": True},
            ]
            with patch("iris_devtester.containers.monitoring.resume_task") as mock_resume:
                mock_resume.return_value = True
                count = enable_monitoring(conn)

        assert count == 1
        mock_resume.assert_called_once()


# ============================================================================
# Task Management Tests
# ============================================================================


class TestCreateTask:
    """Test create_task() function."""

    def test_create_task_success(self):
        """Verify create_task inserts task and returns ID."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None]  # INSERT, then SELECT
        cursor.fetchone.return_value = (42,)

        schedule = TaskSchedule(name="test-task", description="Test")
        task_id = create_task(conn, schedule)

        assert task_id == "42"
        conn.commit.assert_called_once()

    def test_create_task_already_exists(self):
        """Verify create_task raises when task cannot be retrieved."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None]
        cursor.fetchone.return_value = None  # Task not found after creation

        schedule = TaskSchedule(name="test-task")

        with pytest.raises(RuntimeError) as exc_info:
            create_task(conn, schedule)

        assert "could not be retrieved" in str(exc_info.value)


class TestGetTaskStatus:
    """Test get_task_status() function."""

    def test_get_task_status_success(self):
        """Verify get_task_status retrieves task details."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ("my-task", 0, "%SYS.Task.SystemPerformance", 30)

        status = get_task_status(conn, "123")

        assert status["task_id"] == "123"
        assert status["name"] == "my-task"
        assert status["suspended"] is False
        assert status["daily_increment"] == 30

    def test_get_task_status_not_found(self):
        """Verify get_task_status raises when task not found."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None

        with pytest.raises(RuntimeError):
            get_task_status(conn, "999")


class TestSuspendTask:
    """Test suspend_task() function."""

    def test_suspend_task_success(self):
        """Verify suspend_task updates task to suspended=1."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None]  # UPDATE, then SELECT
        cursor.fetchone.return_value = (1,)

        success = suspend_task(conn, "123")

        assert success is True
        conn.commit.assert_called_once()

    def test_suspend_task_with_objectscript_fallback(self):
        """Verify suspend_task falls back to ObjectScript if UPDATE fails."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None]  # UPDATE, then SELECT
        cursor.fetchone.return_value = (0,)  # Still active, trigger fallback
        conn.execute_objectscript = MagicMock()

        success = suspend_task(conn, "123")

        assert success is True
        conn.execute_objectscript.assert_called_once()


class TestResumeTask:
    """Test resume_task() function."""

    def test_resume_task_success(self):
        """Verify resume_task updates task to suspended=0."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None]
        cursor.fetchone.return_value = (0,)

        success = resume_task(conn, "123")

        assert success is True
        conn.commit.assert_called_once()

    def test_resume_task_with_objectscript_fallback(self):
        """Verify resume_task falls back to ObjectScript if UPDATE fails."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None]
        cursor.fetchone.return_value = (1,)  # Still suspended, trigger fallback
        conn.execute_objectscript = MagicMock()

        success = resume_task(conn, "123")

        assert success is True
        conn.execute_objectscript.assert_called_once()


class TestDeleteTask:
    """Test delete_task() function."""

    def test_delete_task_success(self):
        """Verify delete_task removes task via SQL."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.rowcount = 1

        success = delete_task(conn, "123")

        assert success is True
        conn.commit.assert_called_once()

    def test_delete_task_with_objectscript_fallback(self):
        """Verify delete_task falls back to ObjectScript if SQL fails."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.rowcount = 0  # Nothing deleted
        conn.execute_objectscript = MagicMock(return_value="DELETED")

        success = delete_task(conn, "123")

        assert success is True


class TestListMonitoringTasks:
    """Test list_monitoring_tasks() function."""

    def test_list_monitoring_tasks_empty(self):
        """Verify list_monitoring_tasks returns empty list when no tasks."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []

        tasks = list_monitoring_tasks(conn)

        assert tasks == []

    def test_list_monitoring_tasks_multiple(self):
        """Verify list_monitoring_tasks returns all SystemPerformance tasks."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            (1, "monitor-1", 0, 30, "%SYS.Task.SystemPerformance"),
            (2, "monitor-2", 1, 60, "%SYS.Task.SystemPerformance"),
        ]

        tasks = list_monitoring_tasks(conn)

        assert len(tasks) == 2
        assert tasks[0]["task_id"] == "1"
        assert tasks[0]["suspended"] is False
        assert tasks[1]["suspended"] is True


# ============================================================================
# PerformanceMetrics Tests
# ============================================================================


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""

    def test_construction(self):
        """Verify PerformanceMetrics construction."""
        now = datetime.now()
        metrics = PerformanceMetrics(
            timestamp=now,
            cpu_percent=50.0,
            memory_percent=60.0,
            global_references=1000,
            lock_requests=50,
            disk_reads=500,
            disk_writes=200,
            monitoring_enabled=True,
        )
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.monitoring_enabled is True

    def test_from_objectscript_result(self):
        """Verify from_objectscript_result parses JSON correctly."""
        json_result = '{"cpu": 45.2, "memory": 67.8, "glorefs": 1234, "locks": 56, "reads": 789, "writes": 456}'
        metrics = PerformanceMetrics.from_objectscript_result(json_result, True)

        assert metrics.cpu_percent == 45.2
        assert metrics.memory_percent == 67.8
        assert metrics.global_references == 1234
        assert metrics.lock_requests == 56
        assert metrics.monitoring_enabled is True

    def test_exceeds_thresholds(self):
        """Verify exceeds_thresholds returns True when over limit."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=95.0,
            memory_percent=50.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=True,
        )
        thresholds = ResourceThresholds(cpu_disable_percent=90.0)

        assert metrics.exceeds_thresholds(thresholds) is True

    def test_below_thresholds(self):
        """Verify below_thresholds returns True when under limit."""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=80.0,
            memory_percent=85.0,
            global_references=0,
            lock_requests=0,
            disk_reads=0,
            disk_writes=0,
            monitoring_enabled=False,
        )
        thresholds = ResourceThresholds(
            cpu_enable_percent=85.0,
            memory_enable_percent=90.0,
        )

        assert metrics.below_thresholds(thresholds) is True


# ============================================================================
# Performance Functions Tests
# ============================================================================


class TestGetResourceMetrics:
    """Test get_resource_metrics() function."""

    def test_get_resource_metrics_success(self):
        """Verify get_resource_metrics returns PerformanceMetrics."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.list_monitoring_tasks"
        ) as mock_list:
            mock_list.return_value = [{"task_id": "1", "suspended": False}]
            metrics = get_resource_metrics(conn)

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.cpu_percent == 25.0  # Default value
        assert metrics.memory_percent == 30.0  # Default value
        assert metrics.monitoring_enabled is True

    def test_get_resource_metrics_no_tasks(self):
        """Verify get_resource_metrics handles missing tasks."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.list_monitoring_tasks"
        ) as mock_list:
            mock_list.return_value = []
            metrics = get_resource_metrics(conn)

        assert metrics.monitoring_enabled is False


class TestCheckResourceThresholds:
    """Test check_resource_thresholds() function."""

    def test_check_thresholds_should_disable(self):
        """Verify check_resource_thresholds detects high CPU."""
        conn = MagicMock()
        thresholds = ResourceThresholds(cpu_disable_percent=90.0)

        with patch("iris_devtester.containers.performance.get_resource_metrics") as mock_get:
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=95.0,
                memory_percent=50.0,
                global_references=0,
                lock_requests=0,
                disk_reads=0,
                disk_writes=0,
                monitoring_enabled=True,
            )
            mock_get.return_value = metrics

            should_disable, should_enable, returned_metrics = check_resource_thresholds(
                conn, thresholds
            )

        assert should_disable is True
        assert should_enable is False
        assert returned_metrics.cpu_percent == 95.0

    def test_check_thresholds_should_enable(self):
        """Verify check_resource_thresholds detects recovery."""
        conn = MagicMock()
        thresholds = ResourceThresholds(
            cpu_enable_percent=85.0,
            memory_enable_percent=90.0,
        )

        with patch("iris_devtester.containers.performance.get_resource_metrics") as mock_get:
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=80.0,
                memory_percent=85.0,
                global_references=0,
                lock_requests=0,
                disk_reads=0,
                disk_writes=0,
                monitoring_enabled=False,
            )
            mock_get.return_value = metrics

            should_disable, should_enable, returned_metrics = check_resource_thresholds(
                conn, thresholds
            )

        assert should_disable is False
        assert should_enable is True

    def test_check_thresholds_error_handling(self):
        """Verify check_resource_thresholds propagates exceptions."""
        conn = MagicMock()
        thresholds = ResourceThresholds()

        with patch("iris_devtester.containers.performance.get_resource_metrics") as mock_get:
            mock_get.side_effect = RuntimeError("Metrics query failed")

            with pytest.raises(RuntimeError):
                check_resource_thresholds(conn, thresholds)


class TestAutoDisableMonitoring:
    """Test auto_disable_monitoring() function."""

    def test_auto_disable_success(self):
        """Verify auto_disable_monitoring disables tasks."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.disable_monitoring"
        ) as mock_disable:
            mock_disable.return_value = 2
            success = auto_disable_monitoring(conn, "CPU >90%")

        assert success is True
        mock_disable.assert_called_once_with(conn)

    def test_auto_disable_no_tasks(self):
        """Verify auto_disable_monitoring handles no tasks gracefully."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.disable_monitoring"
        ) as mock_disable:
            mock_disable.return_value = 0
            success = auto_disable_monitoring(conn, "CPU >90%")

        assert success is True

    def test_auto_disable_error_handling(self):
        """Verify auto_disable_monitoring raises RuntimeError on failure."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.disable_monitoring"
        ) as mock_disable:
            mock_disable.side_effect = RuntimeError("Disable failed")

            with pytest.raises(RuntimeError):
                auto_disable_monitoring(conn, "CPU >90%")


class TestAutoEnableMonitoring:
    """Test auto_enable_monitoring() function."""

    def test_auto_enable_success(self):
        """Verify auto_enable_monitoring enables tasks."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.enable_monitoring"
        ) as mock_enable:
            mock_enable.return_value = 2
            success = auto_enable_monitoring(conn)

        assert success is True
        mock_enable.assert_called_once_with(conn)

    def test_auto_enable_error_handling(self):
        """Verify auto_enable_monitoring raises RuntimeError on failure."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitoring.enable_monitoring"
        ) as mock_enable:
            mock_enable.side_effect = RuntimeError("Test error")

            with pytest.raises(RuntimeError):
                auto_enable_monitoring(conn)


# ============================================================================
# ConnectionProbe Tests
# ============================================================================


class TestConnectionProbe:
    """Test ConnectionProbe dataclass."""

    def test_construction(self):
        """Verify ConnectionProbe construction."""
        probe = ConnectionProbe(
            host="localhost",
            port=51773,
            namespace="USER",
            username="admin",
            iris_version="2023.1",
            schemas={"MYAPP": 10},
            latency_ms=45.2,
        )
        assert probe.host == "localhost"
        assert probe.port == 51773

    def test_report_with_schemas(self):
        """Verify report() formats connection info."""
        probe = ConnectionProbe(
            host="localhost",
            port=51773,
            namespace="USER",
            username="admin",
            iris_version="2023.1",
            schemas={"MYAPP": 10, "SYSLIB": 100},
            latency_ms=45.2,
        )
        report = probe.report()

        assert "localhost:51773" in report
        assert "USER" in report
        assert "2023.1" in report
        assert "MYAPP: 10" in report
        assert "45.2ms" in report

    def test_report_with_error(self):
        """Verify report() includes error message."""
        probe = ConnectionProbe(
            host="localhost",
            port=51773,
            namespace="USER",
            username="admin",
            iris_version="unknown",
            schemas={},
            latency_ms=0,
            error="Connection refused",
        )
        report = probe.report()

        assert "Connection refused" in report


# ============================================================================
# Diagnostics Helper Tests
# ============================================================================


class TestExtractSqlcode:
    """Test _extract_sqlcode() helper."""

    def test_extract_sqlcode_found(self):
        """Verify _extract_sqlcode extracts code."""
        error = "SQLCODE: <-30> Table not found"
        sqlcode = _extract_sqlcode(error)
        assert sqlcode == -30

    def test_extract_sqlcode_not_found(self):
        """Verify _extract_sqlcode returns None when not found."""
        error = "Some other error"
        sqlcode = _extract_sqlcode(error)
        assert sqlcode is None


class TestExtractTableName:
    """Test _extract_table_name() helper."""

    def test_extract_table_name_from_error1(self):
        """Verify _extract_table_name from 'Table X not found'."""
        error = "Table 'MYAPP.MyTable' not found"
        table = _extract_table_name(error)
        assert table == "MYAPP.MyTable"

    def test_extract_table_name_not_found(self):
        """Verify _extract_table_name returns None when not found."""
        error = "Some other error"
        table = _extract_table_name(error)
        assert table is None


class TestProbeConnection:
    """Test probe_connection() function."""

    def test_probe_connection_success(self):
        """Verify probe_connection queries version, schemas, namespace."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        # Configure cursor responses
        cursor.execute.side_effect = [None, None, None]
        cursor.fetchone.side_effect = [
            ("IRIS 2023.1",),  # $ZVERSION
            ("USER",),  # $NAMESPACE
        ]
        cursor.fetchall.return_value = [
            ("MYAPP", 10),
            ("SYSLIB", 100),
        ]

        probe = probe_connection(conn)

        assert probe.iris_version == "IRIS 2023.1"
        assert probe.namespace == "USER"
        assert "MYAPP" in probe.schemas
        assert probe.error is None

    def test_probe_connection_with_error(self):
        """Verify probe_connection captures errors gracefully."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("Connection failed")

        probe = probe_connection(conn)

        assert probe.error is not None
        assert "Connection failed" in probe.error

    def test_probe_connection_with_connection_info(self):
        """Verify probe_connection extracts connection_info attributes."""
        conn = MagicMock()
        conn.connection_info = MagicMock()
        conn.connection_info.hostname = "localhost"
        conn.connection_info.port = 51773

        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = [None, None, None]
        cursor.fetchone.side_effect = [
            ("IRIS 2023.1",),
            ("USER",),
        ]
        cursor.fetchall.return_value = []

        probe = probe_connection(conn)

        assert probe.host == "localhost"
        assert probe.port == 51773

    def test_probe_connection_no_version_returned(self):
        """Verify probe_connection handles None from version query."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        cursor.execute.side_effect = [None, None, None]
        cursor.fetchone.side_effect = [None, None]  # Both queries return None
        cursor.fetchall.return_value = []

        probe = probe_connection(conn)

        assert probe.iris_version == "unknown"
        assert probe.namespace == "USER"  # Default value


class TestBuildDiagnosticError:
    """Test build_diagnostic_error() function."""

    def test_build_diagnostic_error_missing_schema(self):
        """Verify diagnostic error for missing schema."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ("USER",)
        cursor.fetchall.return_value = [("EXISTING", 5)]

        original_error = Exception("SQLCODE: <-30> Table 'MISSING.Table' not found")
        diagnostic_error = build_diagnostic_error(original_error, conn, sqlcode=-30)

        assert diagnostic_error.sqlcode == -30
        assert "MISSING" in str(diagnostic_error)
        assert "Schema" in str(diagnostic_error)

    def test_build_diagnostic_error_empty_namespace(self):
        """Verify diagnostic error for empty namespace."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ("USER",)
        cursor.fetchall.return_value = []  # No schemas

        original_error = Exception("SQLCODE: <-30> Table 'X.Y' not found")
        diagnostic_error = build_diagnostic_error(original_error, conn, sqlcode=-30)

        assert "empty" in str(diagnostic_error).lower()

    def test_build_diagnostic_error_non_null_sqlcode(self):
        """Verify diagnostic error for non -30 sqlcode."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ("USER",)
        cursor.fetchall.return_value = [("EXISTING", 5)]

        original_error = Exception("SQLCODE: <-23> Label not applicable")
        diagnostic_error = build_diagnostic_error(original_error, conn, sqlcode=-23)

        assert diagnostic_error.sqlcode == -23
        assert "Label not applicable" in str(diagnostic_error)

    def test_build_diagnostic_error_table_without_schema(self):
        """Verify diagnostic error for table name without schema prefix."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ("USER",)
        cursor.fetchall.return_value = [("SCHEMA1", 10)]

        original_error = Exception("SQLCODE: <-30> Table 'TableName' not found")
        diagnostic_error = build_diagnostic_error(original_error, conn, sqlcode=-30)

        assert diagnostic_error.sqlcode == -30
        # Should include visible schemas
        assert "SCHEMA1" in str(diagnostic_error)


# ============================================================================
# MonitoringStatus Tests (monitor_utils)
# ============================================================================


class TestMonitoringStatusDataclass:
    """Test MonitoringStatus dataclass."""

    def test_construction(self):
        """Verify MonitoringStatus construction."""
        status = MonitoringStatus(
            tables_exist=True,
            is_collecting=True,
            sample_count=100,
            latest_sample=datetime.now(),
            available_tables=["HistoryPerf"],
        )
        assert status.tables_exist is True
        assert status.is_collecting is True
        assert status.sample_count == 100


# ============================================================================
# Monitor Utils Functions Tests
# ============================================================================


class TestCheckMonitorTables:
    """Test check_monitor_tables() function."""

    def test_check_monitor_tables_exists(self):
        """Verify check_monitor_tables returns True when tables exist."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            ("HistoryPerf",),
            ("HistoryProc",),
        ]

        exists, tables = check_monitor_tables(conn)

        assert exists is True
        assert len(tables) == 2
        assert "HistoryPerf" in tables

    def test_check_monitor_tables_not_exists(self):
        """Verify check_monitor_tables returns False when no tables."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = []

        exists, tables = check_monitor_tables(conn)

        assert exists is False
        assert tables == []

    def test_check_monitor_tables_error(self):
        """Verify check_monitor_tables handles errors gracefully."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("Query failed")

        exists, tables = check_monitor_tables(conn)

        assert exists is False
        assert tables == []


class TestIsMonitorCollecting:
    """Test is_monitor_collecting() function."""

    def test_is_monitor_collecting_active(self):
        """Verify is_monitor_collecting returns True when samples exist."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = (42,)

        is_active, count = is_monitor_collecting(conn)

        assert is_active is True
        assert count == 42

    def test_is_monitor_collecting_inactive(self):
        """Verify is_monitor_collecting returns False when no samples."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = (0,)

        is_active, count = is_monitor_collecting(conn)

        assert is_active is False
        assert count == 0

    def test_is_monitor_collecting_error(self):
        """Verify is_monitor_collecting handles errors gracefully."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("Query failed")

        is_active, count = is_monitor_collecting(conn)

        assert is_active is False
        assert count == 0


class TestGetMonitorSamples:
    """Test get_monitor_samples() function."""

    def test_get_monitor_samples_success(self):
        """Verify get_monitor_samples returns list of dictionaries."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.description = [("DateTime",), ("CPUTime",), ("MemoryUsage",)]
        cursor.fetchall.return_value = [
            (datetime.now(), 45.2, 67.8),
            (datetime.now(), 46.1, 68.2),
        ]

        samples = get_monitor_samples(conn, table="HistoryPerf", limit=10)

        assert len(samples) == 2
        assert "DateTime" in samples[0]
        assert "CPUTime" in samples[0]
        assert samples[0]["CPUTime"] == 45.2

    def test_get_monitor_samples_empty(self):
        """Verify get_monitor_samples returns empty list when no samples."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.description = []
        cursor.fetchall.return_value = []

        samples = get_monitor_samples(conn)

        assert samples == []

    def test_get_monitor_samples_error(self):
        """Verify get_monitor_samples handles errors gracefully."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("Query failed")

        samples = get_monitor_samples(conn)

        assert samples == []


class TestGetMonitoringStatusUtils:
    """Test get_monitoring_status() from monitor_utils."""

    def test_get_monitoring_status_collecting(self):
        """Verify get_monitoring_status_utils returns complete status."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        # Setup mock for check_monitor_tables
        with patch(
            "iris_devtester.containers.monitor_utils.check_monitor_tables"
        ) as mock_check_tables:
            mock_check_tables.return_value = (True, ["HistoryPerf"])

            # Setup mock for is_monitor_collecting
            with patch(
                "iris_devtester.containers.monitor_utils.is_monitor_collecting"
            ) as mock_collecting:
                mock_collecting.return_value = (True, 100)

                # Setup mock for get_monitor_samples
                with patch(
                    "iris_devtester.containers.monitor_utils.get_monitor_samples"
                ) as mock_samples:
                    sample_datetime = datetime.now()
                    mock_samples.return_value = [{"DateTime": sample_datetime}]

                    status = get_monitoring_status_utils(conn)

        assert status.tables_exist is True
        assert status.is_collecting is True
        assert status.sample_count == 100
        assert status.latest_sample == sample_datetime
        assert "HistoryPerf" in status.available_tables

    def test_get_monitoring_status_not_collecting(self):
        """Verify get_monitoring_status_utils handles inactive monitoring."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitor_utils.check_monitor_tables"
        ) as mock_check_tables:
            mock_check_tables.return_value = (False, [])

            with patch(
                "iris_devtester.containers.monitor_utils.is_monitor_collecting"
            ) as mock_collecting:
                mock_collecting.return_value = (False, 0)

                status = get_monitoring_status_utils(conn)

        assert status.tables_exist is False
        assert status.is_collecting is False
        assert status.sample_count == 0

    def test_get_monitoring_status_collecting_no_samples(self):
        """Verify get_monitoring_status_utils when collecting but no samples retrieved."""
        conn = MagicMock()

        with patch(
            "iris_devtester.containers.monitor_utils.check_monitor_tables"
        ) as mock_check_tables:
            mock_check_tables.return_value = (True, ["HistoryPerf"])

            with patch(
                "iris_devtester.containers.monitor_utils.is_monitor_collecting"
            ) as mock_collecting:
                mock_collecting.return_value = (True, 100)

                with patch(
                    "iris_devtester.containers.monitor_utils.get_monitor_samples"
                ) as mock_samples:
                    mock_samples.return_value = []

                    status = get_monitoring_status_utils(conn)

        assert status.tables_exist is True
        assert status.is_collecting is True
        assert status.latest_sample is None
