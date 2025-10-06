"""
IRIS Performance Metrics Collection.

This module provides wrappers for IRIS ^SystemPerformance utility and resource
monitoring, supporting automatic disable/enable based on system load.

Constitutional Principle #1: Automatic Remediation - Auto-disable under pressure.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from iris_devtools.containers.monitoring import ResourceThresholds

__all__ = [
    "PerformanceMetrics",
    "get_resource_metrics",
    "check_resource_thresholds",
    "auto_disable_monitoring",
    "auto_enable_monitoring",
]

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Real-time IRIS performance metrics from $SYSTEM.Process.GetSystemPerformance().

    Used for auto-disable threshold monitoring.

    Attributes:
        timestamp: When metrics were collected
        cpu_percent: CPU utilization (0-100)
        memory_percent: Memory utilization (0-100)
        global_references: Global database operations count
        lock_requests: Lock operations count
        disk_reads: Physical disk reads count
        disk_writes: Physical disk writes count
        monitoring_enabled: Current monitoring state
        last_state_change: When monitoring state last changed
    """

    timestamp: datetime
    cpu_percent: float  # CPU utilization (0-100)
    memory_percent: float  # Memory utilization (0-100)
    global_references: int  # Global database operations
    lock_requests: int  # Lock operations
    disk_reads: int  # Physical disk reads
    disk_writes: int  # Physical disk writes

    monitoring_enabled: bool  # Current monitoring state
    last_state_change: Optional[datetime] = None

    @classmethod
    def from_objectscript_result(
        cls, result: str, monitoring_enabled: bool
    ) -> "PerformanceMetrics":
        """
        Parse ObjectScript result from GetSystemPerformance().

        Args:
            result: JSON string from ObjectScript query
            monitoring_enabled: Current monitoring state

        Returns:
            PerformanceMetrics instance

        Example result format:
            {"cpu": 45.2, "memory": 67.8, "glorefs": 1234, "locks": 56,
             "reads": 789, "writes": 456}
        """
        data = json.loads(result)
        return cls(
            timestamp=datetime.now(),
            cpu_percent=data["cpu"],
            memory_percent=data["memory"],
            global_references=data.get("glorefs", 0),
            lock_requests=data.get("locks", 0),
            disk_reads=data.get("reads", 0),
            disk_writes=data.get("writes", 0),
            monitoring_enabled=monitoring_enabled,
        )

    def exceeds_thresholds(self, thresholds: "ResourceThresholds") -> bool:
        """Check if metrics exceed disable thresholds."""
        return thresholds.should_disable(self.cpu_percent, self.memory_percent)

    def below_thresholds(self, thresholds: "ResourceThresholds") -> bool:
        """Check if metrics allow re-enabling."""
        return thresholds.should_enable(self.cpu_percent, self.memory_percent)


def get_resource_metrics(conn) -> PerformanceMetrics:
    """
    Get current resource metrics from IRIS.

    Queries IRIS for real-time CPU, memory, and database activity metrics.
    Fast query (<100ms target).

    Args:
        conn: Database connection

    Returns:
        PerformanceMetrics instance with current system state

    Raises:
        RuntimeError: If metrics query fails
    """
    try:
        cursor = conn.cursor()

        # Query current system performance
        # Uses $SYSTEM.Process.GetSystemPerformance() for real-time metrics
        query = """
            SELECT
                $SYSTEM.Process.CPUTime() as cpu,
                $SYSTEM.Process.MemoryUsed() / $SYSTEM.Process.MemoryMax() * 100 as memory,
                ^SYS("PERFMON","GetGloRefs") as glorefs,
                ^SYS("PERFMON","GetLocks") as locks,
                ^SYS("PERFMON","GetReads") as reads,
                ^SYS("PERFMON","GetWrites") as writes
        """

        logger.debug("Querying resource metrics")
        result = cursor.execute(query).fetchone()

        if not result:
            raise RuntimeError("No metrics returned from query")

        # Check if monitoring is currently enabled
        # Query %SYS.PTools.StatsSQL for active profiles
        monitoring_query = """
            SELECT COUNT(*) FROM %SYS.PTools.StatsSQL
            WHERE State = 'Active'
        """
        monitoring_result = cursor.execute(monitoring_query).fetchone()
        monitoring_enabled = bool(monitoring_result and monitoring_result[0] > 0)

        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=float(result[0]) if result[0] else 0.0,
            memory_percent=float(result[1]) if result[1] else 0.0,
            global_references=int(result[2]) if result[2] else 0,
            lock_requests=int(result[3]) if result[3] else 0,
            disk_reads=int(result[4]) if result[4] else 0,
            disk_writes=int(result[5]) if result[5] else 0,
            monitoring_enabled=monitoring_enabled,
        )

        logger.debug(f"✓ Metrics: CPU={metrics.cpu_percent:.1f}% Memory={metrics.memory_percent:.1f}%")
        return metrics

    except Exception as e:
        error_msg = (
            f"Failed to get resource metrics: {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Ensure IRIS connection is active\n"
            "  2. Verify user has %SYS permissions\n"
            "  3. Check IRIS instance is running normally\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def check_resource_thresholds(
    conn, thresholds: "ResourceThresholds"
) -> tuple:
    """
    Check if current resources exceed thresholds.

    Pure logic function - very fast (<1ms), no I/O except initial metrics fetch.

    Args:
        conn: Database connection
        thresholds: Resource thresholds configuration

    Returns:
        Tuple of (should_disable: bool, should_enable: bool, metrics: PerformanceMetrics)
        - should_disable: True if resources exceed disable thresholds
        - should_enable: True if resources below enable thresholds (hysteresis)
        - metrics: Current performance metrics

    Raises:
        RuntimeError: If metrics query fails
    """
    # Get current metrics
    metrics = get_resource_metrics(conn)

    # Check thresholds (pure logic, in-memory)
    should_disable = metrics.exceeds_thresholds(thresholds)
    should_enable = metrics.below_thresholds(thresholds)

    logger.debug(
        f"Resource check: should_disable={should_disable}, "
        f"should_enable={should_enable}, "
        f"CPU={metrics.cpu_percent:.1f}%, "
        f"Memory={metrics.memory_percent:.1f}%"
    )

    return (should_disable, should_enable, metrics)


def auto_disable_monitoring(conn, reason: str) -> bool:
    """
    Auto-disable monitoring under resource pressure.

    Constitutional Principle #1: Automatic Remediation - Disable monitoring
    when system resources are under pressure to reduce overhead.

    Idempotent - safe to call when already disabled.

    Args:
        conn: Database connection
        reason: Human-readable reason for disabling (e.g., "CPU >90%")

    Returns:
        True if monitoring disabled successfully

    Raises:
        RuntimeError: If disable operation fails
    """
    from iris_devtools.containers.monitoring import disable_monitoring

    try:
        logger.warning(f"⚠ Auto-disabling monitoring: {reason}")

        # Call disable_monitoring (imported to avoid circular dependency)
        count = disable_monitoring(conn)

        if count > 0:
            logger.info(f"✓ Auto-disabled {count} monitoring task(s) due to: {reason}")
            return True
        else:
            logger.info("ℹ No active monitoring tasks to disable")
            return True  # Not an error - already disabled

    except Exception as e:
        error_msg = (
            f"Failed to auto-disable monitoring: {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Check IRIS connection is active\n"
            "  2. Verify user has Task Manager permissions\n"
            "  3. Review IRIS error log for details\n"
            "\n"
            f"Trigger reason: {reason}\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def auto_enable_monitoring(conn) -> bool:
    """
    Auto-enable monitoring when resources recover.

    Constitutional Principle #1: Automatic Remediation - Re-enable monitoring
    when system resources have recovered (with hysteresis to prevent thrashing).

    Idempotent - safe to call when already enabled.

    Args:
        conn: Database connection

    Returns:
        True if monitoring enabled successfully

    Raises:
        RuntimeError: If enable operation fails
    """
    from iris_devtools.containers.monitoring import enable_monitoring

    try:
        logger.info("✓ Resources recovered, auto-enabling monitoring")

        # Call enable_monitoring (imported to avoid circular dependency)
        count = enable_monitoring(conn)

        if count > 0:
            logger.info(f"✓ Auto-enabled {count} monitoring task(s)")
            return True
        else:
            logger.info("ℹ No suspended monitoring tasks to enable")
            return True  # Not an error - already enabled

    except Exception as e:
        error_msg = (
            f"Failed to auto-enable monitoring: {e}\n"
            "\n"
            "What went wrong:\n"
            f"  {type(e).__name__}: {e}\n"
            "\n"
            "How to fix it:\n"
            "  1. Check IRIS connection is active\n"
            "  2. Verify monitoring was previously configured\n"
            "  3. Check user has Task Manager permissions\n"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
