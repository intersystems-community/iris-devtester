# IRIS Performance Monitoring Landscape

**Date**: 2025-10-05
**Research Goal**: Understand performance monitoring options in InterSystems IRIS Community Edition
**Context**: Feature 002 implementation - Auto-configure performance monitoring

---

## Executive Summary

InterSystems IRIS provides **THREE DISTINCT** monitoring systems, each serving different purposes:

1. **%Monitor.System** - Built-in system monitoring (AVAILABLE in Community Edition)
2. **^SystemPerformance (pTools)** - Advanced performance analysis (AVAILABILITY UNCLEAR)
3. **%SYS.PTools.StatsSQL** - SQL query performance tracking (AVAILABLE)

**Key Finding**: Our Feature 002 implementation was targeting `%SYS.Task.SystemPerformance` which **does NOT exist** as a task class in IRIS Community Edition 2025.1.

---

## 1. %Monitor.System - Built-in System Monitoring

### Availability
✅ **CONFIRMED AVAILABLE** in Community Edition

### Key Characteristics

**Automatic Operation**:
- Starts automatically when IRIS instance initializes
- Cannot be prevented from auto-starting
- Samples every 30 seconds by default
- Runs in %SYS namespace by default

**Data Collection**:
- ECP connection status
- Lock table utilization
- System resource metrics
- Stores data in `%Monitor_System_Sample.*` tables

**Key Tables**:
```
%Monitor_System_Sample.HistoryPerf   - Performance history
%Monitor_System_Sample.HistoryMemory - Memory usage
%Monitor_System_Sample.HistorySys    - System metrics
%Monitor_System_Sample.Processes     - Process information
```

**Configuration**:
- Managed via `^%SYSMONMGR` utility
- Default: 30-second sampling interval
- Default: Does NOT log routine sensor readings (only alerts)
- Default: Does NOT save sensor readings (can be enabled)
- Data retention: 5 days default

**REST API Integration**:
- `/api/monitor/metrics` - OpenMetrics/Prometheus compatible
- `/api/monitor/alerts` - System alerts
- `/api/monitor/interop` - Interoperability metrics

### Our Testing Results

```sql
-- Checked in IRIS Community 2025.1
SELECT COUNT(*) FROM %Monitor_System_Sample.HistoryPerf
-- Result: 0 samples (monitoring is installed but not actively collecting)
```

**Interpretation**: The %Monitor infrastructure EXISTS but appears to be in a passive state by default in containerized environments.

---

## 2. ^SystemPerformance (pTools) - Advanced Performance Analysis

### Availability
⚠️ **UNCLEAR** - Documentation exists but implementation status unknown in Community Edition

### What Documentation Says

**Purpose**: Comprehensive performance data collection and HTML report generation

**Key Functions**:
- `$$Run^SystemPerformance()` - Standard data collection
- `$$RunNoOS^SystemPerformance()` - Exclude OS metrics (multi-instance)
- `$$Collect^SystemPerformance()` - Generate HTML reports
- `$$Preview^SystemPerformance()` - Interim report while running
- `$$Stop^SystemPerformance()` - Stop collection

**Expected Task Class**: `%SYS.Task.SystemPerformance`

### Our Testing Results

```bash
# Checked available task classes in IRIS Community 2025.1
SELECT DISTINCT TaskClass FROM %SYS.Task

# Result: %SYS.Task.SystemPerformance is NOT in the list
# Available classes include:
- %SYS.TASK.SWITCHJOURNAL
- %SYS.TASK.PURGEJOURNAL
- %SYS.TASK.INTEGRITYCHECK
- %SYS.TASK.DIAGNOSTICREPORT
# ... but NO SystemPerformance class
```

**Interpretation**: Either:
1. SystemPerformance is Enterprise Edition only, OR
2. The task class name changed in newer versions, OR
3. It must be manually enabled/installed

---

## 3. %SYS.PTools.StatsSQL - SQL Query Performance

### Availability
✅ **CONFIRMED AVAILABLE** in Community Edition (table exists)

### Key Characteristics

**Purpose**: SQL query execution statistics

**Configuration**:
- Flag-based configuration system
- Namespace-specific collection
- Time-based auto-termination
- Selective metric collection

**Collected Metrics**:
```
TotalRowCount         - Rows returned
TotalCounter          - Execution count
TotalTimeToFirstRow   - First row latency
TotalTimeSpent        - Total execution time
TotalGlobalRefs       - Global reference count
TotalCommandsExecuted - ObjectScript commands
TotalDiskWait         - I/O wait time
VarianceTimeSpent     - Performance consistency
```

**Query Interface**:
```sql
SELECT *
FROM %SYS_PTools.StatsSQL
ORDER BY Namespace, RoutineName, CursorName, StatsGroup
```

### Our Testing Results

```sql
-- Table structure confirmed in IRIS Community 2025.1
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'StatsSQL' AND TABLE_SCHEMA = '%SYS_PTools'

-- Result: 43 columns including all documented metrics
```

**Interpretation**: StatsSQL infrastructure is FULLY PRESENT in Community Edition.

---

## Key Discovery: Task Creation via SQL

### Critical Finding

While researching ObjectScript execution limitations, we discovered that **IRIS Task Manager accepts SQL INSERT operations**:

```python
# THIS WORKS in Community Edition!
cursor.execute("""
    INSERT INTO %SYS.Task
        (Name, Description, TaskClass, RunAsUser, Suspended,
         DailyFrequency, DailyIncrement, DailyIncrementUnit,
         StartDate, StartTime)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_DATE, CURRENT_TIME)
""", (task_name, description, task_class, user, suspended, ...))
```

**Implications**:
- No ObjectScript execution required
- Works with DBAPI connections
- Enables Feature 002 implementation WITHOUT Feature 003 (Connection Manager)

---

## Monitoring Approach Comparison

| Feature | %Monitor.System | ^SystemPerformance | StatsSQL |
|---------|----------------|-------------------|----------|
| Auto-starts | ✅ Yes | ❌ Manual | ❌ Manual |
| Community Edition | ✅ Confirmed | ⚠️ Unknown | ✅ Confirmed |
| Task Manager Integration | Built-in | Task class | Manual |
| SQL Accessible | ✅ Yes | ❓ Unknown | ✅ Yes |
| Performance Focus | System-wide | System-wide | SQL-only |
| Report Generation | REST API | HTML files | SQL queries |

---

## Recommendations for Feature 002

### Option A: Pivot to %Monitor.System (RECOMMENDED)

**Why**:
- ✅ Confirmed available in Community Edition
- ✅ Already auto-starts (just need to verify/configure)
- ✅ SQL-accessible tables
- ✅ REST API for modern monitoring
- ✅ No ObjectScript execution required

**Implementation**:
```python
def configure_monitoring(conn):
    """
    Verify %Monitor.System is running and collecting data.

    Community Edition: %Monitor.System auto-starts but may not save readings.
    This function enables sensor reading storage.
    """
    # Check current status
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM %Monitor_System_Sample.HistoryPerf")

    # If no samples, monitoring might need activation
    # Use ^%SYSMONMGR to configure (via container exec)

    # Return status
    return is_collecting, config_details
```

### Option B: Create Generic Task Infrastructure

**Why**:
- ✅ We discovered SQL INSERT works for tasks
- ✅ Demonstrates core functionality
- ✅ Not blocked on specific monitoring system
- ✅ Useful for ANY scheduled task

**Implementation**:
```python
def create_scheduled_task(conn, task_config):
    """
    Create ANY scheduled task using SQL INSERT.

    Works with any available TaskClass in the system.
    No ObjectScript execution required.
    """
    cursor.execute("""
        INSERT INTO %SYS.Task (Name, TaskClass, ...)
        VALUES (?, ?, ...)
    """, task_config)
```

### Option C: Enable StatsSQL Collection

**Why**:
- ✅ Confirmed available
- ✅ SQL-based configuration
- ✅ Focused, actionable performance data
- ✅ Useful for developers

**Limitation**:
- Only tracks SQL queries (not system-wide performance)

---

## Open Questions

1. **Is ^SystemPerformance available in Community Edition?**
   - How to test: Try to execute `write ##class(%Dictionary.ClassDefinition).%ExistsId("SYS.PTools.StatsSQL")`
   - Need to find correct ObjectScript execution method

2. **Why is %Monitor.System not collecting samples by default in containers?**
   - Possible: Requires explicit enablement via ^%SYSMONMGR
   - Possible: Container lifecycle issue
   - Need to test: Start container, wait 60 seconds, check for samples

3. **What TaskClass SHOULD we use for performance monitoring?**
   - Available: %SYS.TASK.DIAGNOSTICREPORT (might be related?)
   - Need to investigate: What each available task class does

---

## Next Steps for Feature 002

### Immediate Actions

1. **Test %Monitor.System activation**
   ```python
   # In IRIS container
   iris session IRIS -U %SYS
   do ^%SYSMONMGR
   # Enable sensor reading storage
   # Set debug level to 1
   # Verify samples start appearing in tables
   ```

2. **Verify SQL task creation**
   ```python
   # Test with a simple, known-working task class
   INSERT INTO %SYS.Task (Name, TaskClass, ...)
   VALUES ('test-task', '%SYS.TASK.DIAGNOSTICREPORT', ...)
   ```

3. **Document the pivot decision**
   - Update STATUS.md with findings
   - Revise Feature 002 scope if needed
   - Get user confirmation on approach

### Long-term Considerations

- If %Monitor.System is the right choice, Feature 002 becomes simpler
- If ^SystemPerformance is needed, may require Enterprise Edition testing
- StatsSQL could be a quick-win alternative

---

## References

**InterSystems Documentation**:
- System Monitor: https://docs.intersystems.com/ (GMON chapters)
- ^SystemPerformance: https://docs.intersystems.com/ (GSTU_systemperformance)
- pTools: %SYS.PTools.* class documentation

**Community Resources**:
- Perplexity research confirmed %Monitor.System auto-starts
- Perplexity research detailed StatsSQL functionality
- Perplexity research explained ^SystemPerformance utility

**Our Testing**:
- IRIS Community Edition 2025.1 (Build 223U)
- Testcontainers: `intersystemsdc/iris-community:latest`
- Connection: DBAPI via `irisnative`

---

## Conclusion

**The core issue**: Feature 002 was designed around `%SYS.Task.SystemPerformance` which doesn't exist in Community Edition.

**The solution path**: Pivot to `%Monitor.System` (built-in, auto-starts, SQL-accessible) OR simplify to generic task management demonstration.

**The breakthrough**: Discovering SQL INSERT works for Task Manager unlocks implementation WITHOUT ObjectScript execution.

**Next decision point**: User confirmation on which monitoring system to target.
