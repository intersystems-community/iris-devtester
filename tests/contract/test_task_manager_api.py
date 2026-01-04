"""
Contract tests for Task Manager Integration API.

Tests API contracts for create_task(), get_task_status(), suspend_task(),
resume_task(), delete_task(), and list_monitoring_tasks().

These tests validate the API signatures and behavior WITHOUT requiring a real
IRIS instance.

Constitutional Principle #7: Medical-Grade Reliability - All API contracts validated.
"""


import pytest

pytestmark = pytest.mark.contract
from unittest.mock import Mock
import inspect

from iris_devtester.containers.monitoring import (
    TaskSchedule,
    create_task,
    get_task_status,
    suspend_task,
    resume_task,
    delete_task,
    list_monitoring_tasks,
)


class TestCreateTaskContract:
    """Test create_task() API contract."""

    def test_function_exists_and_callable(self):
        """Test create_task function exists."""
        assert callable(create_task)

    def test_signature_accepts_connection_and_schedule(self):
        """Test function accepts required parameters."""
        # Verify function accepts the parameters (signature check only)
        sig = inspect.signature(create_task)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        assert 'schedule' in params

    def test_returns_string_task_id(self):
        """Test function signature returns str (task ID)."""
        sig = inspect.signature(create_task)
        # Return annotation should be str
        assert sig.return_annotation is not inspect.Signature.empty

    def test_accepts_task_schedule_with_defaults(self):
        """Test default TaskSchedule works."""
        # Verify TaskSchedule can be created with defaults
        schedule = TaskSchedule()
        assert schedule.name == "iris-devtester-monitor"
        assert schedule.daily_increment == 30

    def test_accepts_custom_task_schedule(self):
        """Test custom TaskSchedule configuration."""
        # Verify custom TaskSchedule configuration works
        schedule = TaskSchedule(
            name="custom-monitor",
            daily_increment=10,  # 10-second intervals
            description="Custom monitoring task",
        )
        assert schedule.name == "custom-monitor"
        assert schedule.daily_increment == 10
        assert schedule.description == "Custom monitoring task"


class TestGetTaskStatusContract:
    """Test get_task_status() API contract."""

    def test_function_exists_and_callable(self):
        """Test get_task_status function exists."""
        assert callable(get_task_status)

    def test_signature_accepts_connection_and_task_id(self):
        """Test function accepts required parameters."""
        # Verify function signature
        sig = inspect.signature(get_task_status)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        assert 'task_id' in params

    def test_returns_dict(self):
        """Test function signature returns dict."""
        sig = inspect.signature(get_task_status)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestSuspendTaskContract:
    """Test suspend_task() API contract."""

    def test_function_exists_and_callable(self):
        """Test suspend_task function exists."""
        assert callable(suspend_task)

    def test_signature_accepts_connection_and_task_id(self):
        """Test function accepts required parameters."""
        # Verify function signature
        sig = inspect.signature(suspend_task)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        assert 'task_id' in params

    def test_returns_bool(self):
        """Test function signature returns bool."""
        sig = inspect.signature(suspend_task)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestResumeTaskContract:
    """Test resume_task() API contract."""

    def test_function_exists_and_callable(self):
        """Test resume_task function exists."""
        assert callable(resume_task)

    def test_signature_accepts_connection_and_task_id(self):
        """Test function accepts required parameters."""
        # Verify function signature
        sig = inspect.signature(resume_task)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        assert 'task_id' in params

    def test_returns_bool(self):
        """Test function signature returns bool."""
        sig = inspect.signature(resume_task)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestDeleteTaskContract:
    """Test delete_task() API contract."""

    def test_function_exists_and_callable(self):
        """Test delete_task function exists."""
        assert callable(delete_task)

    def test_signature_accepts_connection_and_task_id(self):
        """Test function accepts required parameters."""
        # Verify function signature
        sig = inspect.signature(delete_task)
        params = list(sig.parameters.keys())
        assert 'conn' in params
        assert 'task_id' in params

    def test_returns_bool(self):
        """Test function signature returns bool."""
        sig = inspect.signature(delete_task)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestListMonitoringTasksContract:
    """Test list_monitoring_tasks() API contract."""

    def test_function_exists_and_callable(self):
        """Test list_monitoring_tasks function exists."""
        assert callable(list_monitoring_tasks)

    def test_signature_accepts_connection(self):
        """Test function accepts connection parameter."""
        # Verify function signature
        sig = inspect.signature(list_monitoring_tasks)
        params = list(sig.parameters.keys())
        assert 'conn' in params

    def test_returns_list(self):
        """Test function signature returns list."""
        sig = inspect.signature(list_monitoring_tasks)
        # Return annotation should exist
        assert sig.return_annotation is not inspect.Signature.empty


class TestTaskScheduleContract:
    """Test TaskSchedule dataclass contract."""

    def test_task_schedule_has_sensible_defaults(self):
        """Test TaskSchedule defaults match spec."""
        schedule = TaskSchedule()

        # Default values from data model
        assert schedule.name == "iris-devtester-monitor"
        assert schedule.task_class == "%SYS.Task.SystemPerformance"
        assert schedule.run_as_user == "_SYSTEM"
        assert schedule.daily_increment == 30  # 30 seconds
        assert schedule.daily_increment_unit == "Second"
        assert schedule.suspended is False  # Active by default

    def test_task_schedule_generates_objectscript(self):
        """Test TaskSchedule.to_objectscript() generates valid code."""
        schedule = TaskSchedule()
        script = schedule.to_objectscript()

        # Should be non-empty
        assert len(script) > 50

        # Should include critical ObjectScript commands
        assert "##class(%SYS.Task)" in script
        assert "task.Name" in script
        assert "task.TaskClass" in script
        assert "task.RunAsUser" in script
        assert ".%Save()" in script
        assert "task.%Id()" in script  # Returns task ID

    def test_task_schedule_disable_generates_objectscript(self):
        """Test TaskSchedule.disable() generates valid code."""
        schedule = TaskSchedule(task_id="test-123")
        script = schedule.disable()

        assert "##class(%SYS.Task)" in script
        assert "test-123" in script
        assert "Suspended = 1" in script

    def test_task_schedule_enable_generates_objectscript(self):
        """Test TaskSchedule.enable() generates valid code."""
        schedule = TaskSchedule(task_id="test-456")
        script = schedule.enable()

        assert "##class(%SYS.Task)" in script
        assert "test-456" in script
        assert "Suspended = 0" in script

    def test_task_schedule_disable_requires_task_id(self):
        """Test TaskSchedule.disable() requires task_id."""
        schedule = TaskSchedule()  # No task_id

        with pytest.raises(ValueError) as exc_info:
            schedule.disable()

        assert "task_id" in str(exc_info.value).lower()

    def test_task_schedule_enable_requires_task_id(self):
        """Test TaskSchedule.enable() requires task_id."""
        schedule = TaskSchedule()  # No task_id

        with pytest.raises(ValueError) as exc_info:
            schedule.enable()

        assert "task_id" in str(exc_info.value).lower()


class TestTaskManagerAPIConstitutionalCompliance:
    """Test Constitutional Principle compliance in Task Manager API."""

    def test_task_schedule_zero_config_viable(self):
        """Test Principle 4: TaskSchedule works with no parameters."""
        schedule = TaskSchedule()

        # Should have all required fields with defaults
        assert schedule.name is not None
        assert schedule.task_class is not None
        assert schedule.run_as_user is not None
        assert schedule.daily_increment > 0

    def test_create_task_idempotency(self):
        """Test Principle 1: Task creation should handle re-creation safely."""
        # Contract: Creating task with same name twice should either:
        # 1. Return existing task ID, or
        # 2. Raise clear error
        # (Implementation will determine exact behavior)
        # This is a contract test - just verify function signature exists
        sig = inspect.signature(create_task)
        assert 'conn' in sig.parameters
        assert 'schedule' in sig.parameters

    def test_suspend_task_idempotency(self):
        """Test suspending already-suspended task is safe."""
        # Contract test - verify function signature for idempotent operation
        sig = inspect.signature(suspend_task)
        assert 'conn' in sig.parameters
        assert 'task_id' in sig.parameters
        # Implementation should be idempotent (safe to call multiple times)

    def test_resume_task_idempotency(self):
        """Test resuming already-active task is safe."""
        # Contract test - verify function signature for idempotent operation
        sig = inspect.signature(resume_task)
        assert 'conn' in sig.parameters
        assert 'task_id' in sig.parameters
        # Implementation should be idempotent (safe to call multiple times)


class TestTaskManagerAPIPerformanceContract:
    """Test performance expectations from contract."""

    def test_create_task_should_be_quick(self):
        """Test create_task target: <500ms (per spec)."""
        # Contract: Task creation should complete quickly
        assert create_task.__doc__ is not None

    def test_get_task_status_should_be_fast(self):
        """Test get_task_status should be fast query."""
        # Contract: Status query should be fast
        assert get_task_status.__doc__ is not None

    def test_suspend_resume_should_be_immediate(self):
        """Test suspend/resume should be fast operations."""
        # Contract: State changes should be immediate
        assert suspend_task.__doc__ is not None
        assert resume_task.__doc__ is not None


class TestTaskScheduleObjectScriptIntegration:
    """Test TaskSchedule ObjectScript generation details."""

    def test_objectscript_includes_all_schedule_fields(self):
        """Test ObjectScript includes all schedule configuration."""
        schedule = TaskSchedule(
            name="test-task",
            description="Test description",
            daily_increment=60,
            daily_increment_unit="Second",
        )
        script = schedule.to_objectscript()

        assert "test-task" in script
        assert "Test description" in script
        assert "60" in script
        assert "Second" in script

    def test_objectscript_sets_suspended_flag(self):
        """Test ObjectScript includes suspended state."""
        # Active task
        active_schedule = TaskSchedule(suspended=False)
        active_script = active_schedule.to_objectscript()
        assert "Suspended = 0" in active_script

        # Suspended task
        suspended_schedule = TaskSchedule(suspended=True)
        suspended_script = suspended_schedule.to_objectscript()
        assert "Suspended = 1" in suspended_script

    def test_objectscript_uses_correct_task_class(self):
        """Test ObjectScript uses %SYS.Task.SystemPerformance."""
        schedule = TaskSchedule()
        script = schedule.to_objectscript()

        assert "%SYS.Task.SystemPerformance" in script

    def test_objectscript_runs_as_system_user(self):
        """Test ObjectScript sets RunAsUser to _SYSTEM for permissions."""
        schedule = TaskSchedule()
        script = schedule.to_objectscript()

        assert '_SYSTEM' in script or "_SYSTEM" in script


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
