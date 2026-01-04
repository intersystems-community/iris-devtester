# Contract: Monitoring Configuration API

**Feature**: 002-set-default-stats
**Date**: 2025-10-05

## Purpose

Defines the contract for configuring ^SystemPerformance monitoring policies in IRIS containers. This API must be stable and testable via contract tests before implementation.

---

## API: `configure_monitoring()`

### Signature

```python
from iris_devtester.containers.monitoring import MonitoringPolicy, configure_monitoring
from iris_devtester.connections import Connection

def configure_monitoring(
    conn: Connection,
    policy: Optional[MonitoringPolicy] = None,
    enable_task_manager: bool = True,
    auto_disable_thresholds: Optional[ResourceThresholds] = None
) -> MonitoringPolicy:
    """
    Configure ^SystemPerformance monitoring on IRIS instance.

    Args:
        conn: Active IRIS connection (DBAPI or JDBC)
        policy: Monitoring policy (uses defaults if None)
        enable_task_manager: Schedule via Task Manager (default True)
        auto_disable_thresholds: Resource thresholds for auto-disable (uses defaults if None)

    Returns:
        Applied MonitoringPolicy with task_id populated

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If policy validation fails
        PermissionError: If insufficient privileges for Task Manager
        RuntimeError: If monitoring setup fails (non-fatal, logs warning)
    """
```

### Default Behavior (FR-002, FR-003, FR-004)

```python
# Zero-config usage (Constitutional Principle 4)
from iris_devtester.containers import IRISContainer

with IRISContainer.community() as iris:
    conn = iris.get_connection()

    # Auto-configures with defaults:
    # - 30-second interval
    # - 1-hour retention
    # - All metrics enabled
    # - Task Manager scheduling
    policy = configure_monitoring(conn)

    assert policy.interval_seconds == 30
    assert policy.retention_seconds == 3600
    assert policy.task_id is not None  # Task created
```

### Custom Configuration (FR-021, FR-022)

```python
from iris_devtester.containers.monitoring import MonitoringPolicy

# Custom policy
policy = MonitoringPolicy(
    interval_seconds=10,      # 10-second intervals (high frequency)
    retention_seconds=7200,   # 2-hour retention
    collect_sql=True,         # Focus on SQL stats
    collect_vmstat=False      # Disable OS metrics
)

# Apply custom policy
applied = configure_monitoring(conn, policy=policy)

assert applied.interval_seconds == 10
assert applied.retention_seconds == 7200
```

### Opt-Out (FR-020)

```python
import os

# Via environment variable (before container start)
os.environ['IRIS_DISABLE_MONITORING'] = 'true'

with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # Monitoring NOT configured automatically
```

---

## API: `get_monitoring_status()`

### Signature

```python
from iris_devtester.containers.monitoring import MonitoringStatus

def get_monitoring_status(conn: Connection) -> MonitoringStatus:
    """
    Get current monitoring status and metrics.

    Args:
        conn: Active IRIS connection

    Returns:
        MonitoringStatus with current state

    Raises:
        ConnectionError: If IRIS connection unavailable
    """

@dataclass
class MonitoringStatus:
    """Current monitoring system status."""
    enabled: bool                      # Is monitoring active?
    policy_name: Optional[str]         # Active policy name
    task_id: Optional[str]             # Task Manager task ID
    last_collection: Optional[datetime]  # Last data collection timestamp
    data_points_available: int         # Number of data points in retention window
    auto_disabled: bool                # Was monitoring auto-disabled due to resources?
    auto_disabled_reason: Optional[str]  # Why was it disabled?
```

### Usage

```python
status = get_monitoring_status(conn)

assert status.enabled is True
assert status.policy_name == "iris-devtester-default"
assert status.data_points_available > 0
```

---

## API: `disable_monitoring()`

### Signature

```python
def disable_monitoring(
    conn: Connection,
    reason: Optional[str] = None
) -> None:
    """
    Disable monitoring (suspend Task Manager task).

    Args:
        conn: Active IRIS connection
        reason: Optional reason for disabling (for logging)

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If disable fails
    """
```

### Usage

```python
# Manual disable
disable_monitoring(conn, reason="User requested")

status = get_monitoring_status(conn)
assert status.enabled is False
```

---

## API: `enable_monitoring()`

### Signature

```python
def enable_monitoring(conn: Connection) -> None:
    """
    Re-enable monitoring (resume Task Manager task).

    Args:
        conn: Active IRIS connection

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If enable fails or no policy configured
    """
```

### Usage

```python
# Re-enable after manual disable
enable_monitoring(conn)

status = get_monitoring_status(conn)
assert status.enabled is True
```

---

## Contract Tests

### Test: Default Configuration

```python
def test_configure_monitoring_defaults(iris_connection):
    """
    GIVEN an IRIS connection
    WHEN configure_monitoring() called with no arguments
    THEN monitoring is configured with 30s interval and 1-hour retention
    AND Task Manager task is created
    AND monitoring is actively collecting data
    """
    policy = configure_monitoring(iris_connection)

    assert policy.interval_seconds == 30
    assert policy.retention_seconds == 3600
    assert policy.task_id is not None

    status = get_monitoring_status(iris_connection)
    assert status.enabled is True
    assert status.policy_name == "iris-devtester-default"
```

### Test: Custom Policy Validation

```python
def test_configure_monitoring_invalid_interval(iris_connection):
    """
    GIVEN a MonitoringPolicy with invalid interval (500s > 300s max)
    WHEN configure_monitoring() called
    THEN ValueError raised with remediation guidance
    """
    policy = MonitoringPolicy(interval_seconds=500)

    with pytest.raises(ValueError) as exc_info:
        configure_monitoring(iris_connection, policy=policy)

    assert "Collection interval 500s invalid" in str(exc_info.value)
    assert "How to fix it:" in str(exc_info.value)
```

### Test: Graceful Degradation

```python
def test_configure_monitoring_non_fatal_failure(iris_connection_with_limited_permissions):
    """
    GIVEN an IRIS connection with limited permissions (can't create Task Manager tasks)
    WHEN configure_monitoring() called
    THEN RuntimeError raised with clear error message
    AND error includes remediation steps
    """
    with pytest.raises(PermissionError) as exc_info:
        configure_monitoring(iris_connection_with_limited_permissions)

    assert "insufficient privileges" in str(exc_info.value).lower()
    assert "How to fix it:" in str(exc_info.value)
```

### Test: Enable/Disable Cycle

```python
def test_monitoring_enable_disable_cycle(iris_connection):
    """
    GIVEN monitoring is configured and running
    WHEN disable_monitoring() called
    THEN monitoring stops collecting data
    AND status.enabled is False

    WHEN enable_monitoring() called
    THEN monitoring resumes collecting data
    AND status.enabled is True
    """
    configure_monitoring(iris_connection)

    # Disable
    disable_monitoring(iris_connection, reason="Test")
    status = get_monitoring_status(iris_connection)
    assert status.enabled is False

    # Re-enable
    enable_monitoring(iris_connection)
    status = get_monitoring_status(iris_connection)
    assert status.enabled is True
```

---

## Error Handling Contract

All errors must follow Constitutional Principle 5 (Fail Fast with Guidance):

```python
# Example: Invalid policy
try:
    policy = MonitoringPolicy(interval_seconds=500)
    configure_monitoring(conn, policy=policy)
except ValueError as e:
    # Error message includes:
    assert "What went wrong:" in str(e)
    assert "How to fix it:" in str(e)
    assert "Current value:" in str(e)
    assert "Valid range:" in str(e)
```

---

## Performance Contract

| Operation | Max Duration | Notes |
|-----------|-------------|-------|
| `configure_monitoring()` | <2 seconds | Initial setup |
| `get_monitoring_status()` | <100ms | Query only |
| `disable_monitoring()` | <500ms | Task Manager update |
| `enable_monitoring()` | <500ms | Task Manager update |

---

**Contract Status**: ✅ READY FOR IMPLEMENTATION
