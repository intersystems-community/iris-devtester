"""
IRIS Performance Monitoring Configuration.

This module provides automatic ^SystemPerformance monitoring configuration for
IRIS containers, following Constitutional Principle #1: Automatic Remediation.

Monitoring is configured to run continuously by default (30-second intervals,
1-hour retention) with automatic disable/enable based on resource pressure.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

__all__ = [
    "CollectionInterval",
    "MonitoringPolicy",
    "TaskSchedule",
    "ResourceThresholds",
    "CPFParameters",
    "configure_monitoring",
    "get_monitoring_status",
    "disable_monitoring",
    "enable_monitoring",
    "create_task",
    "get_task_status",
    "suspend_task",
    "resume_task",
    "delete_task",
    "list_monitoring_tasks",
]

logger = logging.getLogger(__name__)


class CollectionInterval(Enum):
    """Predefined collection intervals with validation."""

    SECOND_1 = 1  # Minimum (high overhead)
    SECOND_5 = 5
    SECOND_10 = 10
    SECOND_30 = 30  # Default (recommended)
    MINUTE_1 = 60
    MINUTE_5 = 300  # Maximum (5 minutes)


@dataclass
class MonitoringPolicy:
    """
    ^SystemPerformance monitoring policy configuration.

    Constitutional Requirement: Zero Configuration Viable (Principle 4)
    - All fields have sensible defaults
    - Validates ranges per constitutional constraints

    Attributes:
        name: Policy name (default: "iris-devtester-default")
        description: Policy description
        interval_seconds: Collection interval 1-300s (default: 30)
        retention_seconds: Data retention 300-86400s (default: 3600)
        continuous: Run indefinitely (default: True)
        collect_*: What metrics to collect (all default: True)
        output_format: Report format (default: "HTML")
        output_directory: Report location (default: "/tmp/iris-performance/")
        task_id: Task Manager task ID (populated after creation)
    """

    name: str = "iris-devtester-default"
    description: str = "Auto-configured performance monitoring"

    # Collection settings
    interval_seconds: int = 30  # Default: 30 seconds (FR-002)
    retention_seconds: int = 3600  # Default: 1 hour (FR-003)
    continuous: bool = True  # Run indefinitely

    # What to collect
    collect_globals: bool = True
    collect_system: bool = True
    collect_processes: bool = True
    collect_sql: bool = True
    collect_locks: bool = True
    collect_vmstat: bool = True  # Linux/Unix
    collect_iostat: bool = True  # Disk I/O
    collect_perfmon: bool = True  # Windows

    # Output settings
    output_format: str = "HTML"
    output_directory: str = "/tmp/iris-performance/"

    # Task Manager integration
    task_id: Optional[str] = None  # Populated after task creation

    def validate(self) -> None:
        """
        Validate policy against constitutional constraints.

        Constitutional Principle #5: Fail Fast with Guidance

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
        if not self.output_directory.startswith("/"):
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


@dataclass
class TaskSchedule:
    """
    IRIS Task Manager task for ^SystemPerformance execution.

    Maps to %SYS.Task class in ObjectScript.

    Attributes:
        task_id: IRIS task ID (populated after creation)
        name: Task name (default: "iris-devtester-monitor")
        description: Task description
        task_class: Task class to execute (default: "%SYS.Task.SystemPerformance")
        run_as_user: User to run as (default: "_SYSTEM" - required for permissions)
        suspended: Whether task is suspended (default: False - active)
        daily_frequency: How often to run (default: 1 - every day)
        daily_increment: Interval in units (default: 30)
        daily_increment_unit: Time unit (default: "Second")
        created_at: When task was created
        last_run: Last execution time
        next_run: Next scheduled execution
    """

    task_id: Optional[str] = None  # Populated after creation
    name: str = "iris-devtester-monitor"
    description: str = "Auto-configured performance monitoring"
    task_class: str = "%SYS.Task.SystemPerformance"
    run_as_user: str = "_SYSTEM"  # Required for monitoring permissions

    # Scheduling
    suspended: bool = False  # Active by default
    daily_frequency: int = 1  # Every day
    daily_increment: int = 30  # Every 30 seconds
    daily_increment_unit: str = "Second"

    # Execution tracking
    created_at: Optional[str] = None
    last_run: Optional[str] = None
    next_run: Optional[str] = None

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
        if self.task_id is None:
            raise ValueError("Cannot disable task without task_id")
        return f"""
            set task = ##class(%SYS.Task).%OpenId("{self.task_id}")
            set task.Suspended = 1
            do task.%Save()
        """

    def enable(self) -> str:
        """Generate ObjectScript to re-enable this task."""
        if self.task_id is None:
            raise ValueError("Cannot enable task without task_id")
        return f"""
            set task = ##class(%SYS.Task).%OpenId("{self.task_id}")
            set task.Suspended = 0
            do task.%Save()
        """


@dataclass
class ResourceThresholds:
    """
    Resource utilization thresholds for auto-disable monitoring.

    Constitutional Requirement: Automatic Remediation (Principle 1)
    - Auto-disables monitoring under resource pressure
    - Auto-re-enables when resources recover

    Attributes:
        cpu_disable_percent: Disable if CPU exceeds this (default: 90.0)
        memory_disable_percent: Disable if memory exceeds this (default: 95.0)
        cpu_enable_percent: Re-enable if CPU drops below this (default: 85.0)
        memory_enable_percent: Re-enable if memory drops below this (default: 90.0)
        check_interval_seconds: How often to check resources (default: 60)
    """

    # Disable thresholds (FR-017)
    cpu_disable_percent: float = 90.0  # Disable if CPU > 90%
    memory_disable_percent: float = 95.0  # Disable if memory > 95%

    # Re-enable thresholds (FR-018, with hysteresis)
    cpu_enable_percent: float = 85.0  # Re-enable if CPU < 85%
    memory_enable_percent: float = 90.0  # Re-enable if memory < 90%

    # Monitoring frequency
    check_interval_seconds: int = 60  # Check every 60 seconds

    def validate(self) -> None:
        """
        Validate threshold configuration.

        Constitutional Principle #5: Fail Fast with Guidance

        Raises:
            ValueError: If thresholds invalid or create thrashing risk
        """
        # FR-023: Allow customization but validate sanity
        if not (50 <= self.cpu_disable_percent <= 100):
            raise ValueError(
                f"CPU disable threshold must be 50-100%: {self.cpu_disable_percent}\n"
                "\n"
                "What went wrong:\n"
                "  CPU disable threshold is outside valid range.\n"
                "\n"
                "How to fix it:\n"
                "  Set cpu_disable_percent between 50.0 and 100.0\n"
                "  Recommended: 90.0 for auto-protection\n"
            )

        if not (50 <= self.memory_disable_percent <= 100):
            raise ValueError(
                f"Memory disable threshold must be 50-100%: {self.memory_disable_percent}\n"
                "\n"
                "What went wrong:\n"
                "  Memory disable threshold is outside valid range.\n"
                "\n"
                "How to fix it:\n"
                "  Set memory_disable_percent between 50.0 and 100.0\n"
                "  Recommended: 95.0 for auto-protection\n"
            )

        # Ensure hysteresis (enable < disable)
        if self.cpu_enable_percent >= self.cpu_disable_percent:
            raise ValueError(
                f"CPU enable threshold ({self.cpu_enable_percent}%) must be less than "
                f"disable threshold ({self.cpu_disable_percent}%) to prevent thrashing\n"
                "\n"
                "What went wrong:\n"
                "  Hysteresis gap is too small or negative.\n"
                "\n"
                "How to fix it:\n"
                "  Ensure cpu_enable_percent < cpu_disable_percent\n"
                "  Recommended gap: 5% (e.g., disable at 90%, enable at 85%)\n"
            )

        if self.memory_enable_percent >= self.memory_disable_percent:
            raise ValueError(
                f"Memory enable threshold ({self.memory_enable_percent}%) must be less than "
                f"disable threshold ({self.memory_disable_percent}%) to prevent thrashing\n"
                "\n"
                "What went wrong:\n"
                "  Hysteresis gap is too small or negative.\n"
                "\n"
                "How to fix it:\n"
                "  Ensure memory_enable_percent < memory_disable_percent\n"
                "  Recommended gap: 5% (e.g., disable at 95%, enable at 90%)\n"
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
        return (
            cpu_percent > self.cpu_disable_percent
            or memory_percent > self.memory_disable_percent
        )

    def should_enable(self, cpu_percent: float, memory_percent: float) -> bool:
        """
        Determine if monitoring should be re-enabled based on current metrics.

        Args:
            cpu_percent: Current CPU utilization (0-100)
            memory_percent: Current memory utilization (0-100)

        Returns:
            True if monitoring can be safely re-enabled
        """
        return (
            cpu_percent < self.cpu_enable_percent
            and memory_percent < self.memory_enable_percent
        )


@dataclass
class CPFParameters:
    """
    Configuration Parameter File settings for monitoring.

    Maps to Config.* classes in ObjectScript.

    Attributes:
        performance_stats_enabled: Enable stats collection in CPF (default: True)
        gm_heap_size_mb: Global metrics heap size in MB (default: 64)
        routine_buffer_kb: Routine cache size in KB (default: 100000)
        locale: System locale for vmstat/iostat parsing (default: "en_US.UTF-8")
    """

    # [Startup] section
    performance_stats_enabled: bool = True

    # [Memory] section
    gm_heap_size_mb: int = 64  # Global metrics heap (MB)
    routine_buffer_kb: int = 100000  # Routine cache (KB)

    # [Miscellaneous] section
    locale: str = "en_US.UTF-8"  # For vmstat/iostat parsing

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

    def to_dict(self) -> dict:
        """Export as dictionary for logging/serialization."""
        return {
            "performance_stats_enabled": self.performance_stats_enabled,
            "gm_heap_size_mb": self.gm_heap_size_mb,
            "routine_buffer_kb": self.routine_buffer_kb,
            "locale": self.locale,
        }


def configure_monitoring(
    conn, policy: Optional[MonitoringPolicy] = None, force: bool = False
) -> Tuple[bool, str]:
    """
    Configure ^SystemPerformance monitoring with policy.

    Constitutional Principle #1: Automatic Remediation
    Constitutional Principle #4: Zero Configuration Viable

    Args:
        conn: Database connection
        policy: Monitoring policy (default: MonitoringPolicy())
        force: Force reconfiguration even if already configured

    Returns:
        (success: bool, message: str)

    Raises:
        ConnectionError: If IRIS connection unavailable
        ValueError: If policy validation fails
        RuntimeError: If monitoring setup fails

    Example:
        >>> # Zero-config (uses defaults: 30s interval, 1hr retention)
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     success, msg = configure_monitoring(conn)
        ...     print(msg)  # "Monitoring configured: iris-devtester-default (task_id=1)"
        ...
        >>> # Custom policy
        >>> policy = MonitoringPolicy(
        ...     name="high-frequency",
        ...     interval_seconds=10,
        ...     retention_seconds=7200
        ... )
        >>> success, msg = configure_monitoring(conn, policy=policy)
    """
    # Use default policy if none provided (Principle #4: Zero-config viable)
    if policy is None:
        policy = MonitoringPolicy()
        logger.info("Using default MonitoringPolicy (30s intervals, 1hr retention)")

    # Validate policy (Principle #5: Fail fast with guidance)
    try:
        policy.validate()
    except ValueError as e:
        logger.error(f"Policy validation failed: {e}")
        raise

    try:
        # Check if monitoring already configured
        is_running, status = get_monitoring_status(conn)

        if is_running and not force:
            logger.info(
                f"Monitoring already configured (policy: {status.get('policy_name')}). "
                f"Use force=True to reconfigure."
            )
            return (
                True,
                f"Monitoring already active with policy '{status.get('policy_name')}'",
            )

        # Execute ObjectScript to create/update policy
        # NOTE: Using conn.execute_objectscript() which is provided by test fixtures
        # This is a temporary workaround until Feature 003 implements JDBC-based ObjectScript execution
        objectscript = policy.to_objectscript()

        logger.debug(f"Executing ObjectScript to configure policy '{policy.name}'")

        # Check if connection has execute_objectscript method (test fixture provides this)
        if hasattr(conn, 'execute_objectscript'):
            conn.execute_objectscript(objectscript)
        else:
            # Fallback error for production (until Feature 003)
            raise NotImplementedError(
                "ObjectScript execution not available\n"
                "\n"
                "What went wrong:\n"
                "  This connection does not support ObjectScript execution.\n"
                "  DBAPI connections are SQL-only.\n"
                "\n"
                "How to fix it:\n"
                "  1. Use a JDBC connection (supports ObjectScript via stored procedures)\n"
                "  2. Or wait for Feature 003 (Connection Manager) which provides\n"
                "     hybrid DBAPI/JDBC connections with ObjectScript support\n"
                "\n"
                "See: docs/learnings/dbapi-objectscript-limitation.md\n"
            )

        # Create Task Manager task for scheduling
        schedule = TaskSchedule(
            name=f"{policy.name}-task",
            description=policy.description,
            daily_increment=policy.interval_seconds,
        )

        task_id = create_task(conn, schedule)
        policy.task_id = task_id

        logger.info(
            f"✓ Monitoring configured successfully: {policy.name} "
            f"(interval={policy.interval_seconds}s, retention={policy.retention_seconds}s, task_id={task_id})"
        )

        return (
            True,
            f"Monitoring configured: {policy.name} (task_id={task_id})",
        )

    except Exception as e:
        error_msg = (
            f"Failed to configure monitoring: {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify IRIS connection is active\n"
            "  2. Ensure user has Task Manager permissions\n"
            "  3. Check IRIS logs for detailed error\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_monitoring_status(conn) -> Tuple[bool, dict]:
    """
    Get current monitoring status.

    Args:
        conn: Database connection

    Returns:
        (is_running: bool, status_dict: dict)

    Raises:
        ConnectionError: If IRIS connection unavailable

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     is_running, status = get_monitoring_status(conn)
        ...     print(f"Monitoring active: {is_running}")
        ...     print(f"Active tasks: {len(status['tasks'])}")
    """
    try:
        # Check if monitoring tasks exist and are active
        # Note: StatsSQL profiles are not directly queryable via SQL tables
        # so we check for active monitoring tasks instead
        tasks = list_monitoring_tasks(conn)

        if not tasks:
            return (False, {"enabled": 0, "tasks": []})

        # Build status from tasks
        status = {
            "enabled": 1,
            "tasks": tasks,
            "policy_name": "iris-devtester-default",  # Default policy name
            "profile_name": "iris-devtester-default",  # Alias for compatibility
        }

        # Check if any task is not suspended
        # Note: task dict has 'suspended' (lowercase) as boolean
        has_active_task = any(not task.get("suspended", True) for task in tasks)

        return (has_active_task, status)

    except Exception as e:
        logger.warning(f"Could not query monitoring status: {e}")
        # Non-fatal - return disabled status
        return (False, {"enabled": 0, "error": str(e)})


def disable_monitoring(conn) -> int:
    """
    Disable monitoring.

    Constitutional Principle #1: Automatic Remediation (can be called by auto-disable)

    Args:
        conn: Database connection

    Returns:
        int: Count of disabled tasks

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If disable fails

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     # Later, under high load:
        ...     count = disable_monitoring(conn)
        ...     print(f"Disabled {count} monitoring tasks")
    """
    try:
        # Find monitoring tasks
        tasks = list_monitoring_tasks(conn)

        if not tasks:
            logger.info("No monitoring tasks found to disable")
            return 0

        # Suspend all monitoring tasks
        disabled_count = 0
        for task in tasks:
            task_id = task.get("task_id")
            if task_id and not task.get("suspended", False):
                success = suspend_task(conn, task_id)
                if success:
                    disabled_count += 1

        logger.info(f"✓ Disabled {disabled_count} monitoring task(s)")
        return disabled_count

    except Exception as e:
        error_msg = f"Failed to disable monitoring: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def enable_monitoring(conn) -> int:
    """
    Enable monitoring.

    Constitutional Principle #1: Automatic Remediation (can be called by auto-enable)

    Args:
        conn: Database connection

    Returns:
        int: Count of enabled tasks

    Raises:
        ConnectionError: If IRIS connection unavailable
        RuntimeError: If enable fails or no policy configured

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     disable_monitoring(conn)
        ...     # Later, when resources recover:
        ...     count = enable_monitoring(conn)
        ...     print(f"Re-enabled {count} monitoring tasks")
    """
    try:
        # Find monitoring tasks
        tasks = list_monitoring_tasks(conn)

        if not tasks:
            error_msg = (
                "No monitoring tasks found\n"
                "\n"
                "What went wrong:\n"
                "  Monitoring has not been configured yet.\n"
                "\n"
                "How to fix it:\n"
                "  Call configure_monitoring() first to set up monitoring.\n"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Resume all suspended monitoring tasks
        enabled_count = 0
        for task in tasks:
            task_id = task.get("task_id")
            if task_id and task.get("suspended", False):
                success = resume_task(conn, task_id)
                if success:
                    enabled_count += 1

        logger.info(f"✓ Enabled {enabled_count} monitoring task(s)")
        return enabled_count

    except Exception as e:
        error_msg = f"Failed to enable monitoring: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def create_task(conn, schedule: TaskSchedule) -> str:
    """
    Create Task Manager task using SQL INSERT.

    Args:
        conn: Database connection
        schedule: Task schedule configuration

    Returns:
        task_id: str (ID of created task)

    Raises:
        ConnectionError: If IRIS connection unavailable
        PermissionError: If insufficient privileges
        RuntimeError: If task creation fails

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     schedule = TaskSchedule(
        ...         name="my-monitoring-task",
        ...         description="Custom monitoring",
        ...         daily_increment=60  # Every 60 seconds
        ...     )
        ...     task_id = create_task(conn, schedule)
        ...     print(f"Created task ID: {task_id}")
    """
    try:
        cursor = conn.cursor()

        logger.debug(f"Creating Task Manager task: {schedule.name}")

        # Create task using SQL INSERT with fields that work
        # Note: TimePeriod has strict validation - omit it and let IRIS set defaults
        # DailyIncrement is VARCHAR(50), store as string like "30"
        insert_sql = """
            INSERT INTO %SYS.Task
                (Name, Description, TaskClass, RunAsUser, Suspended,
                 DailyFrequency, DailyIncrement,
                 StartDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_DATE)
        """

        cursor.execute(
            insert_sql,
            (
                schedule.name,
                schedule.description,
                schedule.task_class,
                schedule.run_as_user,
                1 if schedule.suspended else 0,  # Respect schedule.suspended setting
                schedule.daily_frequency,
                str(schedule.daily_increment),  # Store as string like "30"
            ),
        )
        conn.commit()

        # Get the ID of the created task
        cursor.execute(
            "SELECT ID FROM %SYS.Task WHERE Name = ? ORDER BY ID DESC",
            (schedule.name,),
        )
        result = cursor.fetchone()

        if not result:
            raise RuntimeError(
                f"Task '{schedule.name}' was created but ID could not be retrieved"
            )

        task_id = str(result[0])
        logger.info(f"✓ Created Task Manager task: {schedule.name} (ID: {task_id})")
        return task_id

    except Exception as e:
        error_msg = (
            f"Failed to create Task Manager task: {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Ensure user has Task Manager permissions\n"
            "  2. Verify task name doesn't already exist\n"
            "  3. Check IRIS logs for detailed error\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_task_status(conn, task_id: str) -> dict:
    """
    Get Task Manager task status and details.

    Args:
        conn: Database connection
        task_id: Task ID to query

    Returns:
        dict with task details: {
            "task_id": str,
            "name": str,
            "suspended": bool,
            "task_class": str,
            "daily_increment": int,
            "next_scheduled_time": Optional[str]
        }

    Raises:
        RuntimeError: If task not found or query fails

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     tasks = list_monitoring_tasks(conn)
        ...     task_id = tasks[0]['task_id']
        ...     status = get_task_status(conn, task_id)
        ...     print(f"Task: {status['name']}, Active: {not status['suspended']}")
    """
    try:
        cursor = conn.cursor()

        # Query task details using simple SELECT (works with DBAPI)
        query = """
            SELECT Name, Suspended, TaskClass, DailyIncrement
            FROM %SYS.Task
            WHERE ID = ?
        """

        logger.debug(f"Querying task status: {task_id}")
        cursor.execute(query, (task_id,))
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"Task not found: {task_id}")

        status = {
            "task_id": task_id,
            "name": result[0] if result[0] else "",
            "suspended": bool(result[1]) if result[1] is not None else False,
            "task_class": result[2] if result[2] else "",
            "daily_increment": int(result[3]) if result[3] else 0,
        }

        logger.info(f"✓ Retrieved task status: {status['name']} (ID: {task_id})")
        return status

    except Exception as e:
        error_msg = (
            f"Failed to get task status for ID '{task_id}': {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify task ID is correct\n"
            "  2. Ensure task exists in Task Manager\n"
            "  3. Check user has permission to query tasks\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def suspend_task(conn, task_id: str) -> bool:
    """
    Suspend (pause) a Task Manager task.

    Idempotent - safe to call on already-suspended tasks.

    Args:
        conn: Database connection
        task_id: Task ID to suspend

    Returns:
        True if task suspended successfully

    Raises:
        RuntimeError: If suspension fails

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     tasks = list_monitoring_tasks(conn)
        ...     success = suspend_task(conn, tasks[0]['task_id'])
        ...     print(f"Task suspended: {success}")
    """
    try:
        logger.debug(f"Suspending task: {task_id}")

        # Use SQL UPDATE to suspend the task (works with DBAPI!)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE %SYS.Task SET Suspended = 1 WHERE ID = ?",
            (task_id,)
        )
        conn.commit()

        # Verify it was updated
        cursor.execute("SELECT Suspended FROM %SYS.Task WHERE ID = ?", (task_id,))
        result = cursor.fetchone()

        if not result:
            raise RuntimeError(f"Task {task_id} not found after suspend attempt")

        if result[0] != 1:
            # Fallback to ObjectScript if SQL didn't work
            schedule = TaskSchedule(task_id=task_id)
            objectscript = schedule.disable()

            if hasattr(conn, 'execute_objectscript'):
                conn.execute_objectscript(objectscript)
            else:
                raise NotImplementedError(
                    "ObjectScript execution not available\n"
                    "\n"
                    "What went wrong:\n"
                "  This connection does not support ObjectScript execution.\n"
                "  DBAPI connections are SQL-only.\n"
                "\n"
                "How to fix it:\n"
                "  1. Use a JDBC connection (supports ObjectScript via stored procedures)\n"
                "  2. Or wait for Feature 003 (Connection Manager) which provides\n"
                "     hybrid DBAPI/JDBC connections with ObjectScript support\n"
                "\n"
                "See: docs/learnings/dbapi-objectscript-limitation.md\n"
            )

        logger.info(f"✓ Suspended task: {task_id}")
        return True

    except Exception as e:
        error_msg = (
            f"Failed to suspend task '{task_id}': {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify task ID exists\n"
            "  2. Check user has Task Manager permissions\n"
            "  3. Review IRIS error log for details\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def resume_task(conn, task_id: str) -> bool:
    """
    Resume (unpause) a suspended Task Manager task.

    Idempotent - safe to call on already-active tasks.

    Args:
        conn: Database connection
        task_id: Task ID to resume

    Returns:
        True if task resumed successfully

    Raises:
        RuntimeError: If resume fails

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     tasks = list_monitoring_tasks(conn)
        ...     suspend_task(conn, tasks[0]['task_id'])
        ...     # Later:
        ...     success = resume_task(conn, tasks[0]['task_id'])
        ...     print(f"Task resumed: {success}")
    """
    try:
        logger.debug(f"Resuming task: {task_id}")

        # Use SQL UPDATE to resume the task (works with DBAPI!)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE %SYS.Task SET Suspended = 0 WHERE ID = ?",
            (task_id,)
        )
        conn.commit()

        # Verify it was updated
        cursor.execute("SELECT Suspended FROM %SYS.Task WHERE ID = ?", (task_id,))
        result = cursor.fetchone()

        if not result:
            raise RuntimeError(f"Task {task_id} not found after resume attempt")

        if result[0] != 0:
            # Fallback to ObjectScript if SQL didn't work
            schedule = TaskSchedule(task_id=task_id)
            objectscript = schedule.enable()

            if hasattr(conn, 'execute_objectscript'):
                conn.execute_objectscript(objectscript)
            else:
                raise NotImplementedError(
                    "ObjectScript execution not available\n"
                    "\n"
                    "What went wrong:\n"
                    "  This connection does not support ObjectScript execution.\n"
                    "  DBAPI connections are SQL-only.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Use a JDBC connection (supports ObjectScript via stored procedures)\n"
                    "  2. Or wait for Feature 003 (Connection Manager) which provides\n"
                    "     hybrid DBAPI/JDBC connections with ObjectScript support\n"
                    "\n"
                    "See: docs/learnings/dbapi-objectscript-limitation.md\n"
            )

        logger.info(f"✓ Resumed task: {task_id}")
        return True

    except Exception as e:
        error_msg = (
            f"Failed to resume task '{task_id}': {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify task ID exists\n"
            "  2. Check user has Task Manager permissions\n"
            "  3. Review IRIS error log for details\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def delete_task(conn, task_id: str) -> bool:
    """
    Delete a Task Manager task permanently.

    Args:
        conn: Database connection
        task_id: Task ID to delete

    Returns:
        True if task deleted successfully

    Raises:
        RuntimeError: If deletion fails

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     schedule = TaskSchedule(name="temp-task")
        ...     task_id = create_task(conn, schedule)
        ...     # Later, cleanup:
        ...     success = delete_task(conn, task_id)
        ...     print(f"Task deleted: {success}")
    """
    try:
        logger.debug(f"Deleting task: {task_id}")

        # Use SQL DELETE (works with DBAPI!)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM %SYS.Task WHERE ID = ?",
            (task_id,)
        )
        conn.commit()

        # Check if anything was deleted
        if cursor.rowcount == 0:
            # Fallback to ObjectScript if SQL didn't work
            if hasattr(conn, 'execute_objectscript'):
                objectscript = f"""
                    set task = ##class(%SYS.Task).%OpenId("{task_id}")
                    if $IsObject(task) {{
                        do task.%Delete()
                        write "DELETED"
                    }} else {{
                        write "NOT_FOUND"
                    }}
                """
                output = conn.execute_objectscript(objectscript)
                if "NOT_FOUND" in output:
                    raise ValueError(f"Task not found: {task_id}")
            else:
                raise ValueError(f"Task not found: {task_id}")

        logger.info(f"✓ Deleted task: {task_id}")
        return True

    except Exception as e:
        error_msg = (
            f"Failed to delete task '{task_id}': {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Verify task ID exists\n"
            "  2. Ensure task is suspended before deleting\n"
            "  3. Check user has Task Manager permissions\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def list_monitoring_tasks(conn) -> list:
    """
    List all iris-devtester monitoring tasks.

    Finds tasks created by configure_monitoring() by looking for tasks
    using %SYS.Task.SystemPerformance class.

    Args:
        conn: Database connection

    Returns:
        List of dicts with task info: [{
            "task_id": str,
            "name": str,
            "suspended": bool,
            "daily_increment": int,
            "task_class": str
        }]

    Example:
        >>> with IRISContainer.community() as iris:
        ...     conn = iris.get_connection()
        ...     configure_monitoring(conn)
        ...     tasks = list_monitoring_tasks(conn)
        ...     for task in tasks:
        ...         print(f"{task['name']}: {'active' if not task['suspended'] else 'suspended'}")
    """
    try:
        cursor = conn.cursor()

        # Query all SystemPerformance tasks
        query = """
            SELECT %ID, Name, Suspended, DailyIncrement, TaskClass
            FROM %SYS.Task
            WHERE TaskClass = '%SYS.Task.SystemPerformance'
        """

        logger.debug("Querying monitoring tasks")
        cursor.execute(query)
        results = cursor.fetchall()

        tasks = []
        for row in results:
            tasks.append({
                "task_id": str(row[0]) if row[0] else "",
                "name": row[1] if row[1] else "",
                "suspended": bool(row[2]) if row[2] is not None else False,
                "daily_increment": int(row[3]) if row[3] else 0,
                "task_class": row[4] if row[4] else "",
            })

        logger.info(f"✓ Found {len(tasks)} monitoring task(s)")
        return tasks

    except Exception as e:
        # Non-fatal - return empty list
        logger.warning(f"Failed to list monitoring tasks: {e}")
        return []
