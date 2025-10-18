# Contract: Resource Monitoring & Auto-Disable API

**Feature**: 002-set-default-stats
**Date**: 2025-10-05

## Purpose

Defines the contract for monitoring IRIS resource usage and automatically disabling/re-enabling ^SystemPerformance monitoring based on CPU and memory thresholds (FR-017, FR-018). This implements Constitutional Principle 1 (Automatic Remediation).

---

## API: `get_resource_metrics()`

### Signature

```python
from iris_devtools.containers.monitoring import PerformanceMetrics, get_resource_metrics
from iris_devtools.connections import Connection

def get_resource_metrics(conn: Connection) -> PerformanceMetrics:
    """
    Get current IRIS resource utilization metrics.

    Uses $SYSTEM.Process.GetSystemPerformance() for accurate IRIS-centric metrics.

    Args:
        conn: Active IRIS connection

    Returns:
        PerformanceMetrics with current CPU, memory, and database metrics

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If metrics query fails
    """
```

### Usage

```python
metrics = get_resource_metrics(conn)

assert 0 <= metrics.cpu_percent <= 100
assert 0 <= metrics.memory_percent <= 100
assert metrics.timestamp is not None
print(f"CPU: {metrics.cpu_percent}%, Memory: {metrics.memory_percent}%")
```

---

## API: `check_resource_thresholds()`

### Signature

```python
from iris_devtools.containers.monitoring import ResourceThresholds
from enum import Enum

class ThresholdAction(Enum):
    """Recommended action based on resource thresholds."""
    MAINTAIN = "maintain"          # Keep current state
    DISABLE = "disable"            # Should disable monitoring
    ENABLE = "enable"              # Can re-enable monitoring

def check_resource_thresholds(
    metrics: PerformanceMetrics,
    thresholds: ResourceThresholds
) -> ThresholdAction:
    """
    Determine monitoring action based on current metrics and thresholds.

    Args:
        metrics: Current resource metrics
        thresholds: Configured thresholds for auto-disable

    Returns:
        Recommended action (MAINTAIN, DISABLE, or ENABLE)
    """
```

### Usage

```python
from iris_devtools.containers.monitoring import ResourceThresholds

thresholds = ResourceThresholds(
    cpu_disable_percent=90.0,
    memory_disable_percent=95.0,
    cpu_enable_percent=85.0,
    memory_enable_percent=90.0
)

metrics = get_resource_metrics(conn)
action = check_resource_thresholds(metrics, thresholds)

if action == ThresholdAction.DISABLE:
    print("Resource pressure detected, should disable monitoring")
elif action == ThresholdAction.ENABLE:
    print("Resources recovered, can re-enable monitoring")
```

---

## API: `start_resource_monitor()`

### Signature

```python
from typing import Callable, Optional
import threading

ResourceCallback = Callable[[PerformanceMetrics, ThresholdAction], None]

def start_resource_monitor(
    conn: Connection,
    thresholds: Optional[ResourceThresholds] = None,
    callback: Optional[ResourceCallback] = None,
    check_interval_seconds: int = 60
) -> threading.Thread:
    """
    Start background thread monitoring resources and auto-managing monitoring.

    Automatically disables monitoring when resources exceed thresholds,
    re-enables when resources recover.

    Args:
        conn: Active IRIS connection
        thresholds: Resource thresholds (uses defaults if None)
        callback: Optional callback for threshold events
        check_interval_seconds: How often to check resources (default 60s)

    Returns:
        Background thread (already started, daemon=True)

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If check_interval_seconds < 10 (too frequent)
    """
```

### Usage

```python
# Start auto-monitoring with defaults
monitor_thread = start_resource_monitor(conn)

# Auto-disables when CPU >90% or memory >95%
# Auto-re-enables when CPU <85% and memory <90%
```

### Custom Callback

```python
def on_threshold_event(metrics: PerformanceMetrics, action: ThresholdAction):
    """Custom handler for threshold events."""
    if action == ThresholdAction.DISABLE:
        print(f"WARNING: Disabling monitoring - CPU:{metrics.cpu_percent}% Memory:{metrics.memory_percent}%")
    elif action == ThresholdAction.ENABLE:
        print(f"INFO: Re-enabling monitoring - resources recovered")

# Start with custom callback
monitor_thread = start_resource_monitor(
    conn,
    callback=on_threshold_event,
    check_interval_seconds=30  # Check every 30 seconds
)
```

---

## API: `stop_resource_monitor()`

### Signature

```python
def stop_resource_monitor(monitor_thread: threading.Thread, timeout: float = 5.0) -> None:
    """
    Stop resource monitoring thread gracefully.

    Args:
        monitor_thread: Thread returned by start_resource_monitor()
        timeout: Maximum seconds to wait for thread shutdown

    Raises:
        RuntimeError: If thread doesn't stop within timeout
    """
```

### Usage

```python
monitor_thread = start_resource_monitor(conn)

# Later: stop monitoring
stop_resource_monitor(monitor_thread)
```

---

## API: `auto_disable_monitoring()`

### Signature

```python
def auto_disable_monitoring(
    conn: Connection,
    reason: str,
    metrics: PerformanceMetrics
) -> None:
    """
    Disable monitoring with auto-disable tracking.

    Records that monitoring was auto-disabled due to resource pressure.
    Logs event for debugging.

    Args:
        conn: Active IRIS connection
        reason: Human-readable reason (e.g., "CPU exceeded 90%")
        metrics: Current metrics that triggered disable

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If disable fails
    """
```

### Usage

```python
metrics = get_resource_metrics(conn)

if metrics.cpu_percent > 90:
    auto_disable_monitoring(
        conn,
        reason=f"CPU exceeded threshold: {metrics.cpu_percent}%",
        metrics=metrics
    )
```

---

## API: `auto_enable_monitoring()`

### Signature

```python
def auto_enable_monitoring(
    conn: Connection,
    metrics: PerformanceMetrics
) -> None:
    """
    Re-enable monitoring after auto-disable.

    Only re-enables if monitoring was previously auto-disabled
    (not manually disabled by user).

    Args:
        conn: Active IRIS connection
        metrics: Current metrics showing resources recovered

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If enable fails or monitoring wasn't auto-disabled
    """
```

### Usage

```python
metrics = get_resource_metrics(conn)

if metrics.cpu_percent < 85 and metrics.memory_percent < 90:
    auto_enable_monitoring(conn, metrics)
```

---

## Contract Tests

### Test: Get Resource Metrics

```python
def test_get_resource_metrics(iris_connection):
    """
    GIVEN an active IRIS connection
    WHEN get_resource_metrics() called
    THEN current CPU and memory utilization returned
    AND all metric fields are populated
    AND values are within valid ranges
    """
    metrics = get_resource_metrics(iris_connection)

    assert isinstance(metrics, PerformanceMetrics)
    assert 0 <= metrics.cpu_percent <= 100
    assert 0 <= metrics.memory_percent <= 100
    assert metrics.timestamp is not None
    assert metrics.global_references >= 0
    assert metrics.disk_reads >= 0
```

### Test: Threshold Detection - Should Disable

```python
def test_check_thresholds_should_disable_cpu(iris_connection):
    """
    GIVEN resource metrics with CPU at 95% (above 90% threshold)
    WHEN check_resource_thresholds() called
    THEN ThresholdAction.DISABLE returned
    """
    thresholds = ResourceThresholds(
        cpu_disable_percent=90.0,
        memory_disable_percent=95.0
    )

    # Simulate high CPU
    metrics = PerformanceMetrics(
        timestamp=datetime.now(),
        cpu_percent=95.0,           # Above threshold!
        memory_percent=50.0,         # Normal
        global_references=1000,
        lock_requests=50,
        disk_reads=500,
        disk_writes=200,
        monitoring_enabled=True
    )

    action = check_resource_thresholds(metrics, thresholds)

    assert action == ThresholdAction.DISABLE
```

### Test: Threshold Detection - Should Enable

```python
def test_check_thresholds_should_enable(iris_connection):
    """
    GIVEN resource metrics with CPU at 80% and memory at 85% (both below enable thresholds)
    AND monitoring is currently disabled
    WHEN check_resource_thresholds() called
    THEN ThresholdAction.ENABLE returned
    """
    thresholds = ResourceThresholds(
        cpu_disable_percent=90.0,
        memory_disable_percent=95.0,
        cpu_enable_percent=85.0,
        memory_enable_percent=90.0
    )

    metrics = PerformanceMetrics(
        timestamp=datetime.now(),
        cpu_percent=80.0,            # Below enable threshold
        memory_percent=85.0,          # Below enable threshold
        global_references=1000,
        lock_requests=50,
        disk_reads=500,
        disk_writes=200,
        monitoring_enabled=False      # Currently disabled
    )

    action = check_resource_thresholds(metrics, thresholds)

    assert action == ThresholdAction.ENABLE
```

### Test: Hysteresis Prevents Thrashing

```python
def test_threshold_hysteresis(iris_connection):
    """
    GIVEN thresholds with hysteresis gap (disable=90%, enable=85%)
    WHEN CPU fluctuates between 86-89% (in hysteresis zone)
    THEN action is MAINTAIN (no state change)
    AND monitoring doesn't thrash on/off
    """
    thresholds = ResourceThresholds(
        cpu_disable_percent=90.0,
        cpu_enable_percent=85.0
    )

    # CPU at 87% - in hysteresis zone
    metrics = PerformanceMetrics(
        timestamp=datetime.now(),
        cpu_percent=87.0,             # Between 85% and 90%
        memory_percent=50.0,
        global_references=1000,
        lock_requests=50,
        disk_reads=500,
        disk_writes=200,
        monitoring_enabled=True       # Currently enabled
    )

    action = check_resource_thresholds(metrics, thresholds)

    # Should maintain current state (no change)
    assert action == ThresholdAction.MAINTAIN
```

### Test: Start and Stop Resource Monitor

```python
def test_start_stop_resource_monitor(iris_connection):
    """
    GIVEN an IRIS connection
    WHEN start_resource_monitor() called
    THEN background thread is started
    AND thread is daemon (won't block exit)

    WHEN stop_resource_monitor() called
    THEN thread stops within timeout
    """
    monitor_thread = start_resource_monitor(iris_connection, check_interval_seconds=30)

    assert monitor_thread.is_alive()
    assert monitor_thread.daemon is True

    stop_resource_monitor(monitor_thread, timeout=5.0)

    # Thread should be stopped
    time.sleep(1)
    assert not monitor_thread.is_alive()
```

### Test: Auto-Disable Under Load

```python
def test_auto_disable_under_load(iris_connection):
    """
    GIVEN monitoring is running
    AND resource monitor is active
    WHEN CPU exceeds 90% threshold
    THEN monitoring is automatically disabled
    AND disable event is logged
    """
    # Start monitoring
    configure_monitoring(iris_connection)

    events = []

    def track_events(metrics, action):
        events.append((metrics, action))

    # Start resource monitor
    monitor_thread = start_resource_monitor(
        iris_connection,
        callback=track_events,
        check_interval_seconds=10
    )

    # Simulate high CPU (in real test, would actually load IRIS)
    # ... load generation code ...

    # Wait for auto-disable
    time.sleep(15)

    # Verify disable event occurred
    disable_events = [e for e in events if e[1] == ThresholdAction.DISABLE]
    assert len(disable_events) > 0

    # Verify monitoring is disabled
    status = get_monitoring_status(iris_connection)
    assert status.auto_disabled is True

    stop_resource_monitor(monitor_thread)
```

### Test: Auto-Enable After Recovery

```python
def test_auto_enable_after_recovery(iris_connection):
    """
    GIVEN monitoring was auto-disabled due to high CPU
    WHEN CPU drops below enable threshold (85%)
    THEN monitoring is automatically re-enabled
    AND enable event is logged
    """
    # Auto-disable monitoring
    high_metrics = PerformanceMetrics(
        timestamp=datetime.now(),
        cpu_percent=95.0,
        memory_percent=50.0,
        global_references=1000,
        lock_requests=50,
        disk_reads=500,
        disk_writes=200,
        monitoring_enabled=True
    )
    auto_disable_monitoring(iris_connection, "High CPU", high_metrics)

    # Verify disabled
    status = get_monitoring_status(iris_connection)
    assert status.auto_disabled is True

    # Simulate recovery
    low_metrics = PerformanceMetrics(
        timestamp=datetime.now(),
        cpu_percent=80.0,             # Below enable threshold
        memory_percent=50.0,
        global_references=1000,
        lock_requests=50,
        disk_reads=500,
        disk_writes=200,
        monitoring_enabled=False
    )

    auto_enable_monitoring(iris_connection, low_metrics)

    # Verify re-enabled
    status = get_monitoring_status(iris_connection)
    assert status.enabled is True
    assert status.auto_disabled is False
```

---

## Error Handling Contract

All resource monitoring errors must follow Constitutional Principle 5:

```python
# Example: Invalid check interval
try:
    start_resource_monitor(conn, check_interval_seconds=5)  # Too frequent!
except ValueError as e:
    error_msg = str(e)
    assert "What went wrong:" in error_msg
    assert "check_interval_seconds" in error_msg
    assert "How to fix it:" in error_msg
    assert "minimum 10 seconds" in error_msg.lower()
```

---

## Performance Contract

| Operation | Max Duration | Notes |
|-----------|-------------|-------|
| `get_resource_metrics()` | <100ms | Query only |
| `check_resource_thresholds()` | <10ms | Pure computation |
| `start_resource_monitor()` | <100ms | Thread spawn |
| `stop_resource_monitor()` | <5s | Graceful shutdown |
| `auto_disable_monitoring()` | <500ms | Includes logging |
| `auto_enable_monitoring()` | <500ms | Includes logging |

**Resource Monitor Overhead**:
- CPU: <0.1% (60-second check interval)
- Memory: <5MB (metrics history)

---

## ObjectScript Implementation Notes

### Get System Performance Metrics
```objectscript
set metrics = ##class(%SYSTEM.Process).GetSystemPerformance()
set cpu = $LIST(metrics, 1)           // CPU %
set memory = $LIST(metrics, 5)        // Memory %
set glorefs = $LIST(metrics, 8)       // Global references
// Return as JSON for Python parsing
write "{"
write """cpu"": " _ cpu _ ", "
write """memory"": " _ memory _ ", "
write """glorefs"": " _ glorefs
write "}"
```

---

**Contract Status**: ✅ READY FOR IMPLEMENTATION
