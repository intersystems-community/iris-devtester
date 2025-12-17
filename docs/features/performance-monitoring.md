# Performance Monitoring

Auto-configure IRIS ^SystemPerformance monitoring with resource-aware auto-disable.

## Overview

Performance monitoring features:
- Zero-config ^SystemPerformance setup
- Task Manager integration for scheduled monitoring
- Resource-aware auto-disable under high load (CPU > 90%)
- Automatic re-enable when resources recover (CPU < 85%)
- Configurable thresholds with hysteresis

## Quick Start

### Python API

```python
from iris_devtester.containers.monitoring import configure_monitoring
from iris_devtester.containers import IRISContainer

with IRISContainer.community() as iris:
    conn = iris.get_connection()

    # Zero-config monitoring setup
    success, message = configure_monitoring(conn)
    print(f"Monitoring configured: {message}")

    # Automatically disables monitoring if CPU > 90%
    # Automatically re-enables when CPU < 85%
```

### Check Monitoring Status

```python
from iris_devtester.containers.monitoring import get_monitoring_status

status = get_monitoring_status(conn)
print(f"Policy: {status.policy_name}")
print(f"Active: {status.is_active}")
print(f"Interval: {status.interval_seconds}s")
```

### Manual Control

```python
from iris_devtester.containers.monitoring import (
    enable_monitoring,
    disable_monitoring,
)

# Disable during heavy operations
disable_monitoring(conn)
# ... run bulk import ...
enable_monitoring(conn)
```

## Resource-Aware Auto-Disable

Monitoring automatically suspends when system resources are constrained:

```python
from iris_devtester.containers.monitoring import ResourceThresholds

# Default thresholds
thresholds = ResourceThresholds(
    cpu_disable_threshold=90,   # Disable at 90% CPU
    cpu_enable_threshold=85,    # Re-enable at 85% CPU
    memory_disable_threshold=95,
    memory_enable_threshold=90,
)

configure_monitoring(conn, thresholds=thresholds)
```

### Hysteresis

The gap between disable/enable thresholds prevents rapid on/off cycling:
- Disable at 90% CPU
- Must drop to 85% to re-enable
- Prevents monitoring from flapping during variable load

## Task Manager Integration

Scheduled monitoring via IRIS Task Manager:

```python
from iris_devtester.containers.monitoring import (
    create_monitoring_task,
    get_task_status,
    suspend_task,
    resume_task,
    delete_task,
)

# Create scheduled monitoring task
task_id = create_monitoring_task(
    conn,
    name="hourly-perf-snapshot",
    interval_minutes=60,
)

# Check task status
status = get_task_status(conn, task_id)
print(f"Last run: {status.last_run}")
print(f"Next run: {status.next_run}")

# Suspend during maintenance
suspend_task(conn, task_id)

# Resume after maintenance
resume_task(conn, task_id)

# Cleanup
delete_task(conn, task_id)
```

## Metrics Available

```python
from iris_devtester.containers.monitoring import get_resource_metrics

metrics = get_resource_metrics(conn)
print(f"CPU: {metrics.cpu_percent}%")
print(f"Memory: {metrics.memory_percent}%")
print(f"Disk: {metrics.disk_percent}%")
print(f"Global buffers: {metrics.global_buffers_percent}%")
```

## Best Practices

1. **Use auto-disable**: Prevents monitoring from impacting production under load
2. **Set appropriate thresholds**: Tune for your workload characteristics
3. **Monitor the monitor**: Check task status periodically
4. **Suspend during bulk operations**: Disable monitoring during imports/migrations
5. **Review intervals**: Balance granularity vs. overhead

## Configuration

### Monitoring Policy

```python
from iris_devtester.containers.monitoring import MonitoringPolicy

policy = MonitoringPolicy(
    name="custom-policy",
    interval_seconds=300,  # 5 minutes
    metrics=[
        "cpu", "memory", "disk",
        "global_buffers", "routine_buffers",
        "journal", "locks"
    ],
    output_directory="/iris/logs/perf/",
)

configure_monitoring(conn, policy=policy)
```

## Troubleshooting

### Monitoring not starting
- Check IRIS %SYS namespace permissions
- Verify Task Manager is running
- Check for conflicting monitoring tasks

### High overhead
- Increase interval (e.g., 300s instead of 60s)
- Reduce collected metrics
- Enable auto-disable with lower thresholds

### Task not running
- Check Task Manager status in Management Portal
- Verify task is not suspended
- Check IRIS error logs

## See Also

- [Testcontainers Integration](testcontainers.md) - Container setup
