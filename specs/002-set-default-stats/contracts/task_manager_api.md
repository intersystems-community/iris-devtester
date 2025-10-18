# Contract: Task Manager Integration API

**Feature**: 002-set-default-stats
**Date**: 2025-10-05

## Purpose

Defines the contract for creating, managing, and querying IRIS Task Manager tasks for ^SystemPerformance scheduling. This API wraps ObjectScript Task Manager operations with Python-friendly interfaces.

---

## API: `create_task()`

### Signature

```python
from iris_devtools.containers.monitoring import TaskSchedule, create_task
from iris_devtools.connections import Connection

def create_task(
    conn: Connection,
    schedule: TaskSchedule
) -> str:
    """
    Create an IRIS Task Manager task for ^SystemPerformance.

    Args:
        conn: Active IRIS connection
        schedule: Task schedule configuration

    Returns:
        Task ID (string) for tracking

    Raises:
        ConnectionError: If IRIS connection unavailable
        PermissionError: If insufficient privileges to create tasks
        ValueError: If schedule configuration invalid
        RuntimeError: If task creation fails
    """
```

### Default Usage

```python
from iris_devtools.containers.monitoring import TaskSchedule

# Create task with defaults (30-second intervals)
schedule = TaskSchedule(
    name="iris-devtools-monitor",
    daily_increment=30  # Every 30 seconds
)

task_id = create_task(conn, schedule)

assert task_id is not None
assert isinstance(task_id, str)
```

### Custom Schedule

```python
# High-frequency monitoring (10-second intervals)
schedule = TaskSchedule(
    name="high-freq-monitor",
    description="High-frequency debugging session",
    daily_increment=10,
    daily_increment_unit="Second"
)

task_id = create_task(conn, schedule)
```

---

## API: `get_task_status()`

### Signature

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TaskStatus:
    """Task Manager task status."""
    task_id: str
    name: str
    suspended: bool              # Is task currently disabled?
    last_run: Optional[datetime]   # Last execution time
    next_run: Optional[datetime]   # Next scheduled execution
    last_result: Optional[str]     # Result of last execution
    execution_count: int           # Total executions since creation

def get_task_status(conn: Connection, task_id: str) -> TaskStatus:
    """
    Get current status of Task Manager task.

    Args:
        conn: Active IRIS connection
        task_id: Task ID from create_task()

    Returns:
        TaskStatus with current state

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If task_id not found
    """
```

### Usage

```python
task_id = create_task(conn, schedule)

status = get_task_status(conn, task_id)

assert status.task_id == task_id
assert status.suspended is False
assert status.next_run is not None
```

---

## API: `suspend_task()`

### Signature

```python
def suspend_task(conn: Connection, task_id: str) -> None:
    """
    Suspend (disable) a Task Manager task.

    Args:
        conn: Active IRIS connection
        task_id: Task ID to suspend

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If task_id not found
        RuntimeError: If suspension fails
    """
```

### Usage

```python
# Create and then suspend task
task_id = create_task(conn, schedule)
suspend_task(conn, task_id)

status = get_task_status(conn, task_id)
assert status.suspended is True
```

---

## API: `resume_task()`

### Signature

```python
def resume_task(conn: Connection, task_id: str) -> None:
    """
    Resume (enable) a suspended Task Manager task.

    Args:
        conn: Active IRIS connection
        task_id: Task ID to resume

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If task_id not found
        RuntimeError: If resume fails
    """
```

### Usage

```python
# Resume previously suspended task
resume_task(conn, task_id)

status = get_task_status(conn, task_id)
assert status.suspended is False
```

---

## API: `delete_task()`

### Signature

```python
def delete_task(conn: Connection, task_id: str) -> None:
    """
    Delete a Task Manager task permanently.

    Args:
        conn: Active IRIS connection
        task_id: Task ID to delete

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If task_id not found
        RuntimeError: If deletion fails
    """
```

### Usage

```python
# Clean up task when no longer needed
delete_task(conn, task_id)

# Task no longer exists
with pytest.raises(ValueError):
    get_task_status(conn, task_id)
```

---

## API: `list_monitoring_tasks()`

### Signature

```python
from typing import List

def list_monitoring_tasks(conn: Connection) -> List[TaskStatus]:
    """
    List all iris-devtools monitoring tasks.

    Filters to tasks created by iris-devtools (name prefix "iris-devtools-").

    Args:
        conn: Active IRIS connection

    Returns:
        List of TaskStatus for monitoring tasks

    Raises:
        ConnectionError: If IRIS connection unavailable
    """
```

### Usage

```python
# Create multiple tasks
task1 = create_task(conn, TaskSchedule(name="iris-devtools-monitor-1"))
task2 = create_task(conn, TaskSchedule(name="iris-devtools-monitor-2"))

# List all monitoring tasks
tasks = list_monitoring_tasks(conn)

assert len(tasks) >= 2
assert all(t.name.startswith("iris-devtools-") for t in tasks)
```

---

## Contract Tests

### Test: Create Task Successfully

```python
def test_create_task_success(iris_connection):
    """
    GIVEN an IRIS connection with Task Manager permissions
    WHEN create_task() called with valid TaskSchedule
    THEN task is created in Task Manager
    AND task ID is returned
    AND task is active (not suspended)
    """
    schedule = TaskSchedule(name="test-monitor", daily_increment=30)

    task_id = create_task(iris_connection, schedule)

    assert task_id is not None
    assert isinstance(task_id, str)

    status = get_task_status(iris_connection, task_id)
    assert status.name == "test-monitor"
    assert status.suspended is False
```

### Test: Create Task Without Permissions

```python
def test_create_task_insufficient_permissions(iris_connection_limited):
    """
    GIVEN an IRIS connection without Task Manager create permissions
    WHEN create_task() called
    THEN PermissionError raised
    AND error message includes remediation steps
    """
    schedule = TaskSchedule(name="test-monitor")

    with pytest.raises(PermissionError) as exc_info:
        create_task(iris_connection_limited, schedule)

    error_msg = str(exc_info.value)
    assert "insufficient privileges" in error_msg.lower()
    assert "How to fix it:" in error_msg
    assert "_SYSTEM" in error_msg or "administrator" in error_msg.lower()
```

### Test: Suspend and Resume Cycle

```python
def test_task_suspend_resume_cycle(iris_connection):
    """
    GIVEN a running Task Manager task
    WHEN suspend_task() called
    THEN task.suspended is True
    AND no new executions occur

    WHEN resume_task() called
    THEN task.suspended is False
    AND executions resume
    """
    schedule = TaskSchedule(name="test-monitor", daily_increment=5)
    task_id = create_task(iris_connection, schedule)

    # Suspend
    suspend_task(iris_connection, task_id)
    status = get_task_status(iris_connection, task_id)
    assert status.suspended is True

    initial_count = status.execution_count
    time.sleep(10)  # Wait longer than interval

    status = get_task_status(iris_connection, task_id)
    assert status.execution_count == initial_count  # No new executions

    # Resume
    resume_task(iris_connection, task_id)
    status = get_task_status(iris_connection, task_id)
    assert status.suspended is False

    time.sleep(10)  # Wait for execution
    status = get_task_status(iris_connection, task_id)
    assert status.execution_count > initial_count  # New executions
```

### Test: Delete Task

```python
def test_delete_task(iris_connection):
    """
    GIVEN a Task Manager task
    WHEN delete_task() called
    THEN task is permanently removed
    AND get_task_status() raises ValueError
    """
    schedule = TaskSchedule(name="test-monitor")
    task_id = create_task(iris_connection, schedule)

    # Verify exists
    status = get_task_status(iris_connection, task_id)
    assert status.task_id == task_id

    # Delete
    delete_task(iris_connection, task_id)

    # Verify deleted
    with pytest.raises(ValueError) as exc_info:
        get_task_status(iris_connection, task_id)

    assert "not found" in str(exc_info.value).lower()
```

### Test: List Monitoring Tasks

```python
def test_list_monitoring_tasks(iris_connection):
    """
    GIVEN multiple iris-devtools monitoring tasks
    WHEN list_monitoring_tasks() called
    THEN all iris-devtools tasks are returned
    AND only iris-devtools tasks are returned (filtered by name prefix)
    """
    # Create test tasks
    task1 = create_task(iris_connection, TaskSchedule(name="iris-devtools-test-1"))
    task2 = create_task(iris_connection, TaskSchedule(name="iris-devtools-test-2"))

    # List tasks
    tasks = list_monitoring_tasks(iris_connection)

    assert len(tasks) >= 2

    # Verify all returned tasks are iris-devtools tasks
    for task in tasks:
        assert task.name.startswith("iris-devtools-")

    # Verify our tasks are included
    task_ids = [t.task_id for t in tasks]
    assert task1 in task_ids
    assert task2 in task_ids
```

### Test: Task Status After Execution

```python
def test_task_status_after_execution(iris_connection):
    """
    GIVEN a Task Manager task scheduled to run every 5 seconds
    WHEN task executes
    THEN last_run timestamp is updated
    AND execution_count increments
    AND next_run is scheduled correctly
    """
    schedule = TaskSchedule(name="test-monitor", daily_increment=5)
    task_id = create_task(iris_connection, schedule)

    # Wait for first execution
    time.sleep(6)

    status = get_task_status(iris_connection, task_id)

    assert status.last_run is not None
    assert status.execution_count > 0
    assert status.next_run is not None
    assert status.next_run > status.last_run
```

---

## Error Handling Contract

All Task Manager errors must follow Constitutional Principle 5:

```python
# Example: Task not found
try:
    get_task_status(conn, "nonexistent-task-id")
except ValueError as e:
    error_msg = str(e)
    assert "What went wrong:" in error_msg
    assert "Task ID 'nonexistent-task-id' not found" in error_msg
    assert "How to fix it:" in error_msg
    assert "list_monitoring_tasks()" in error_msg  # Remediation
```

---

## Performance Contract

| Operation | Max Duration | Notes |
|-----------|-------------|-------|
| `create_task()` | <500ms | One-time setup |
| `get_task_status()` | <100ms | Query only |
| `suspend_task()` | <200ms | Task Manager update |
| `resume_task()` | <200ms | Task Manager update |
| `delete_task()` | <300ms | Task Manager delete + cleanup |
| `list_monitoring_tasks()` | <500ms | Query all tasks |

---

## ObjectScript Implementation Notes

### Task Creation ObjectScript
```objectscript
set task = ##class(%SYS.Task).%New()
set task.Name = {name}
set task.TaskClass = "%SYS.Task.SystemPerformance"
set task.RunAsUser = "_SYSTEM"
set task.DailyIncrement = {interval}
do task.%Save()
write task.%Id()
```

### Task Query ObjectScript
```objectscript
set task = ##class(%SYS.Task).%OpenId({task_id})
if '$IsObject(task) { throw task not found error }
// Return task properties as JSON
```

### Task Suspension ObjectScript
```objectscript
set task = ##class(%SYS.Task).%OpenId({task_id})
set task.Suspended = 1
do task.%Save()
```

---

**Contract Status**: ✅ READY FOR IMPLEMENTATION
