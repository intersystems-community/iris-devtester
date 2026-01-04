# Data Model: IRIS Performance Monitoring

**Feature**: 002-set-default-stats
**Date**: 2025-10-05

## Overview

This document defines the key entities and their relationships for the IRIS performance monitoring feature. All entities follow constitutional principles of type safety, validation, and clear error handling.

---

## Entity Definitions

### 1. MonitoringPolicy

**Purpose**: Defines ^SystemPerformance collection policy with validation and defaults.

**Python Model**:
```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class CollectionInterval(Enum):
    """Predefined collection intervals with validation."""
    SECOND_1 = 1      # Minimum (high overhead)
    SECOND_5 = 5
    SECOND_10 = 10
    SECOND_30 = 30    # Default (recommended)
    MINUTE_1 = 60
    MINUTE_5 = 300    # Maximum (5 minutes)

@dataclass
class MonitoringPolicy:
    """
    ^SystemPerformance monitoring policy configuration.

    Constitutional Requirement: Zero Configuration Viable (Principle 4)
    - All fields have sensible defaults
    - Validates ranges per constitutional constraints
    """
    name: str = "iris-devtester-default"
    description: str = "Auto-configured performance monitoring"

    # Collection settings
    interval_seconds: int = 30           # Default: 30 seconds
    retention_seconds: int = 3600        # Default: 1 hour
    continuous: bool = True              # Run indefinitely

    # What to collect
    collect_globals: bool = True
    collect_system: bool = True
    collect_processes: bool = True
    collect_sql: bool = True
    collect_locks: bool = True
    collect_vmstat: bool = True          # Linux/Unix
    collect_iostat: bool = True          # Disk I/O
    collect_perfmon: bool = True         # Windows

    # Output settings
    output_format: str = "HTML"
    output_directory: str = "/tmp/iris-performance/"

    # Task Manager integration
    task_id: Optional[str] = None        # Populated after task creation

    def validate(self) -> None:
        """
        Validate policy against constitutional constraints.

        Raises:
            ValueError: If constraints violated with remediation guidance
        """
        # FR-021: Interval range 1-300 seconds
        if not (1 <= self.interval_seconds <= 300):
            raise ValueError(
                f"Collection interval {self.interval_seconds}s invalid\n"
                "\n"
                "What went wrong:\n"
                "  Collection interval must be between 1 and 300 seconds.\n"
                "\n"
                "How to fix it:\n"
                "  - For high-frequency monitoring: Use 1-10 seconds (high overhead)\n"
                "  - For normal monitoring: Use 30 seconds (recommended)\n"
                "  - For low-overhead monitoring: Use 60-300 seconds\n"
                "\n"
                f"Current value: {self.interval_seconds}s\n"
                f"Valid range: 1-300s\n"
            )

        # FR-022: Retention range 5 minutes - 24 hours
        if not (300 <= self.retention_seconds <= 86400):
            raise ValueError(
                f"Retention period {self.retention_seconds}s invalid\n"
                "\n"
                "What went wrong:\n"
                "  Retention period must be between 5 minutes and 24 hours.\n"
                "\n"
                "How to fix it:\n"
                "  - For recent debugging: Use 300-3600s (5min-1hr)\n"
                "  - For extended debugging: Use 3600-43200s (1hr-12hr)\n"
                "  - For full-day analysis: Use 86400s (24hr max)\n"
                "\n"
                f"Current value: {self.retention_seconds}s ({self.retention_seconds/3600:.1f} hours)\n"
                f"Valid range: 300-86400s (5min-24hr)\n"
            )

        # Validate output directory is absolute path
        if not self.output_directory.startswith('/'):
            raise ValueError(
                f"Output directory must be absolute path: {self.output_directory}"
            )

    def to_objectscript(self) -> str:
        """
        Generate ObjectScript to create this policy in IRIS.

        Returns:
            ObjectScript code to execute via connection
        """
        return f"""
            set policy = ##class(%SYS.PTools.StatsSQL).%New()
            set policy.Name = "{self.name}"
            set policy.Description = "{self.description}"

            // Collection settings
            set policy.Interval = {self.interval_seconds}
            set policy.Duration = {self.retention_seconds}
            set policy.RunTime = "{'continuous' if self.continuous else 'once'}"

            // What to collect
            set policy.CollectGlobalStats = {1 if self.collect_globals else 0}
            set policy.CollectSystemStats = {1 if self.collect_system else 0}
            set policy.CollectProcessStats = {1 if self.collect_processes else 0}
            set policy.CollectSQLStats = {1 if self.collect_sql else 0}
            set policy.CollectLockStats = {1 if self.collect_locks else 0}
            set policy.CollectVMStat = {1 if self.collect_vmstat else 0}
            set policy.CollectIOStat = {1 if self.collect_iostat else 0}
            set policy.CollectPerfMon = {1 if self.collect_perfmon else 0}

            // Output settings
            set policy.OutputFormat = "{self.output_format}"
            set policy.OutputDirectory = "{self.output_directory}"

            do policy.%Save()

            // Start monitoring
            do ##class(%SYS.PTools.StatsSQL).Start(policy.Name)
        """
```

**Validation Rules** (from FR-021, FR-022):
- `interval_seconds`: 1 ≤ x ≤ 300
- `retention_seconds`: 300 ≤ x ≤ 86400
- `output_directory`: Must be absolute path, writable by IRIS

**State Transitions**:
```
[Created] --validate()--> [Validated] --to_objectscript()--> [Serialized] --apply()--> [Active]
                                                                                          |
                                                                                     disable()
                                                                                          |
                                                                                          v
                                                                                    [Disabled]
```

---

### 2. TaskSchedule

**Purpose**: Represents IRIS Task Manager scheduled task for ^SystemPerformance.

**Python Model**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TaskSchedule:
    """
    IRIS Task Manager task for ^SystemPerformance execution.

    Maps to %SYS.Task class in ObjectScript.
    """
    task_id: Optional[str] = None        # IRIS task ID (populated after creation)
    name: str = "iris-devtester-monitor"
    description: str = "Auto-configured performance monitoring"
    task_class: str = "%SYS.Task.SystemPerformance"
    run_as_user: str = "_SYSTEM"        # Required for monitoring permissions

    # Scheduling
    suspended: bool = False              # Active by default
    daily_frequency: int = 1             # Every day
    daily_increment: int = 30            # Every 30 seconds
    daily_increment_unit: str = "Second"

    # Execution tracking
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

    def to_objectscript(self) -> str:
        """
        Generate ObjectScript to create this task.

        Returns:
            ObjectScript code to create and start task
        """
        return f"""
            set task = ##class(%SYS.Task).%New()
            set task.Name = "{self.name}"
            set task.Description = "{self.description}"
            set task.TaskClass = "{self.task_class}"
            set task.RunAsUser = "{self.run_as_user}"
            set task.Suspended = {1 if self.suspended else 0}

            // Daily schedule starting now
            set task.DailyFrequency = {self.daily_frequency}
            set task.DailyIncrement = {self.daily_increment}
            set task.DailyIncrementUnit = "{self.daily_increment_unit}"

            // Start immediately
            set task.StartDate = $HOROLOG
            set task.StartTime = $PIECE($HOROLOG,",",2)

            do task.%Save()

            // Return task ID for tracking
            write task.%Id()
        """

    def disable(self) -> str:
        """Generate ObjectScript to disable this task."""
        return f"""
            set task = ##class(%SYS.Task).%OpenId("{self.task_id}")
            set task.Suspended = 1
            do task.%Save()
        """

    def enable(self) -> str:
        """Generate ObjectScript to re-enable this task."""
        return f"""
            set task = ##class(%SYS.Task).%OpenId("{self.task_id}")
            set task.Suspended = 0
            do task.%Save()
        """
```

**Relationships**:
- One TaskSchedule → One MonitoringPolicy (1:1)
- TaskSchedule.daily_increment == MonitoringPolicy.interval_seconds

---

### 3. ResourceThresholds

**Purpose**: Defines CPU/memory thresholds for auto-disable monitoring (FR-017, FR-018).

**Python Model**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ResourceThresholds:
    """
    Resource utilization thresholds for auto-disable monitoring.

    Constitutional Requirement: Automatic Remediation (Principle 1)
    - Auto-disables monitoring under resource pressure
    - Auto-re-enables when resources recover
    """
    # Disable thresholds (FR-017)
    cpu_disable_percent: float = 90.0      # Disable if CPU > 90%
    memory_disable_percent: float = 95.0   # Disable if memory > 95%

    # Re-enable thresholds (FR-018, with hysteresis)
    cpu_enable_percent: float = 85.0       # Re-enable if CPU < 85%
    memory_enable_percent: float = 90.0    # Re-enable if memory < 90%

    # Monitoring frequency
    check_interval_seconds: int = 60       # Check every 60 seconds

    def validate(self) -> None:
        """
        Validate threshold configuration.

        Raises:
            ValueError: If thresholds invalid or create thrashing risk
        """
        # FR-023: Allow customization but validate sanity
        if not (50 <= self.cpu_disable_percent <= 100):
            raise ValueError(f"CPU disable threshold must be 50-100%: {self.cpu_disable_percent}")

        if not (50 <= self.memory_disable_percent <= 100):
            raise ValueError(f"Memory disable threshold must be 50-100%: {self.memory_disable_percent}")

        # Ensure hysteresis (enable < disable)
        if self.cpu_enable_percent >= self.cpu_disable_percent:
            raise ValueError(
                f"CPU enable threshold ({self.cpu_enable_percent}%) must be less than "
                f"disable threshold ({self.cpu_disable_percent}%) to prevent thrashing"
            )

        if self.memory_enable_percent >= self.memory_disable_percent:
            raise ValueError(
                f"Memory enable threshold ({self.memory_enable_percent}%) must be less than "
                f"disable threshold ({self.memory_disable_percent}%) to prevent thrashing"
            )

    def should_disable(self, cpu_percent: float, memory_percent: float) -> bool:
        """
        Determine if monitoring should be disabled based on current metrics.

        Args:
            cpu_percent: Current CPU utilization (0-100)
            memory_percent: Current memory utilization (0-100)

        Returns:
            True if monitoring should be disabled
        """
        return (cpu_percent > self.cpu_disable_percent or
                memory_percent > self.memory_disable_percent)

    def should_enable(self, cpu_percent: float, memory_percent: float) -> bool:
        """
        Determine if monitoring should be re-enabled based on current metrics.

        Args:
            cpu_percent: Current CPU utilization (0-100)
            memory_percent: Current memory utilization (0-100)

        Returns:
            True if monitoring can be safely re-enabled
        """
        return (cpu_percent < self.cpu_enable_percent and
                memory_percent < self.memory_enable_percent)
```

**Validation Rules** (from FR-023):
- `cpu_disable_percent`: 50 ≤ x ≤ 100
- `memory_disable_percent`: 50 ≤ x ≤ 100
- Hysteresis: `enable_percent < disable_percent` (prevents thrashing)

**State Transitions**:
```
[Monitoring Active] --should_disable()==True--> [Auto-Disabled]
                                                       |
                                        should_enable()==True
                                                       |
                                                       v
                                              [Monitoring Active]
```

---

### 4. CPFParameters

**Purpose**: Encapsulates IRIS CPF configuration parameters for monitoring.

**Python Model**:
```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CPFParameters:
    """
    Configuration Parameter File settings for monitoring.

    Maps to Config.* classes in ObjectScript.
    """
    # [Startup] section
    performance_stats_enabled: bool = True

    # [Memory] section
    gm_heap_size_mb: int = 64             # Global metrics heap (MB)
    routine_buffer_kb: int = 100000       # Routine cache (KB)

    # [Miscellaneous] section
    locale: str = "en_US.UTF-8"           # For vmstat/iostat parsing

    def to_objectscript(self) -> str:
        """
        Generate ObjectScript to apply CPF parameters.

        Returns:
            ObjectScript code to configure CPF
        """
        return f"""
            // Enable performance monitoring
            do ##class(Config.Startup).Get(.startup)
            set startup.PerformanceStats = {1 if self.performance_stats_enabled else 0}
            do startup.%Save()

            // Set memory allocation
            do ##class(Config.Memory).Get(.mem)
            set mem.GMHeapSize = {self.gm_heap_size_mb}
            set mem.RoutineBuf = {self.routine_buffer_kb}
            do mem.%Save()

            // Configure locale
            do ##class(Config.Miscellaneous).Get(.misc)
            set misc.Locale = "{self.locale}"
            do misc.%Save()
        """

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary for logging/serialization."""
        return {
            "performance_stats_enabled": self.performance_stats_enabled,
            "gm_heap_size_mb": self.gm_heap_size_mb,
            "routine_buffer_kb": self.routine_buffer_kb,
            "locale": self.locale
        }
```

**Notes**:
- CPF changes typically require IRIS restart in traditional deployments
- In containers, apply during initialization (before first connection)
- Defaults work for most cases - only override if resource-constrained

---

### 5. PerformanceMetrics

**Purpose**: Runtime metrics for resource monitoring and auto-disable logic.

**Python Model**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class PerformanceMetrics:
    """
    Real-time IRIS performance metrics from $SYSTEM.Process.GetSystemPerformance().

    Used for auto-disable threshold monitoring.
    """
    timestamp: datetime
    cpu_percent: float              # CPU utilization (0-100)
    memory_percent: float           # Memory utilization (0-100)
    global_references: int          # Global database operations
    lock_requests: int              # Lock operations
    disk_reads: int                 # Physical disk reads
    disk_writes: int                # Physical disk writes

    monitoring_enabled: bool        # Current monitoring state
    last_state_change: Optional[datetime] = None

    @classmethod
    def from_objectscript_result(cls, result: str, monitoring_enabled: bool) -> "PerformanceMetrics":
        """
        Parse ObjectScript result from GetSystemPerformance().

        Args:
            result: JSON string from ObjectScript query
            monitoring_enabled: Current monitoring state

        Returns:
            PerformanceMetrics instance
        """
        import json
        data = json.loads(result)
        return cls(
            timestamp=datetime.now(),
            cpu_percent=data['cpu'],
            memory_percent=data['memory'],
            global_references=data.get('glorefs', 0),
            lock_requests=data.get('locks', 0),
            disk_reads=data.get('reads', 0),
            disk_writes=data.get('writes', 0),
            monitoring_enabled=monitoring_enabled
        )

    def exceeds_thresholds(self, thresholds: ResourceThresholds) -> bool:
        """Check if metrics exceed disable thresholds."""
        return thresholds.should_disable(self.cpu_percent, self.memory_percent)

    def below_thresholds(self, thresholds: ResourceThresholds) -> bool:
        """Check if metrics allow re-enabling."""
        return thresholds.should_enable(self.cpu_percent, self.memory_percent)
```

**Data Flow**:
```
IRIS ($SYSTEM.Process) --> ObjectScript query --> JSON --> PerformanceMetrics
                                                                    |
                                                                    v
                                                        ResourceThresholds.should_disable()
                                                                    |
                                                                    v
                                                        TaskSchedule.disable()/enable()
```

---

## Entity Relationships

```
MonitoringPolicy (1) ←→ (1) TaskSchedule
       ↓
   validates against
       ↓
ResourceThresholds (1) ←→ (N) PerformanceMetrics
       ↑
   configured via
       ↑
  CPFParameters
```

**Lifecycle**:
1. Create `MonitoringPolicy` with defaults → validate()
2. Create `CPFParameters` → apply to IRIS (if needed)
3. Create `TaskSchedule` → links to MonitoringPolicy
4. Start resource monitoring → periodically create `PerformanceMetrics`
5. Evaluate `PerformanceMetrics` against `ResourceThresholds` → auto-disable/enable

---

## Validation Matrix

| Entity | Validation Method | Constitutional Principle | Requirements |
|--------|------------------|-------------------------|--------------|
| MonitoringPolicy | `.validate()` | Principle 5 (Fail Fast) | FR-021, FR-022 |
| ResourceThresholds | `.validate()` | Principle 1 (Auto-Remediation) | FR-017, FR-018, FR-023 |
| TaskSchedule | Implicit (IRIS validates) | Principle 5 (Fail Fast) | Task Manager API |
| CPFParameters | Implicit (IRIS validates) | Principle 6 (Enterprise/Community) | CPF API |
| PerformanceMetrics | Schema validation | Principle 7 (Reliability) | JSON parsing |

---

## Error Handling Strategy

All entities follow constitutional Principle 5 (Fail Fast with Guidance):

```python
# Example: MonitoringPolicy validation error
try:
    policy = MonitoringPolicy(interval_seconds=500)  # Invalid!
    policy.validate()
except ValueError as e:
    print(e)
    # Output:
    # Collection interval 500s invalid
    #
    # What went wrong:
    #   Collection interval must be between 1 and 300 seconds.
    #
    # How to fix it:
    #   - For high-frequency monitoring: Use 1-10 seconds (high overhead)
    #   - For normal monitoring: Use 30 seconds (recommended)
    #   - For low-overhead monitoring: Use 60-300 seconds
    #
    # Current value: 500s
    # Valid range: 1-300s
```

---

**Data Model Status**: ✅ COMPLETE - All entities defined with validation and relationships.
