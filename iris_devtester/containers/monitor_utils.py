"""
IRIS %Monitor.System Utilities.

Provides utilities to check and work with IRIS's built-in %Monitor.System.
This monitoring system auto-starts with IRIS but may require configuration
to save sensor readings.

Note: Full auto-configuration of %Monitor.System may require interactive
setup via ^%SYSMONMGR utility or Enterprise Edition features.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

__all__ = [
    "MonitoringStatus",
    "check_monitor_tables",
    "get_monitor_samples",
    "is_monitor_collecting",
]

logger = logging.getLogger(__name__)


@dataclass
class MonitoringStatus:
    """Status of %Monitor.System."""

    tables_exist: bool
    is_collecting: bool
    sample_count: int
    latest_sample: Optional[datetime]
    available_tables: List[str]


def check_monitor_tables(conn) -> Tuple[bool, List[str]]:
    """
    Check if %Monitor.System tables exist.

    Args:
        conn: Database connection

    Returns:
        (tables_exist, list_of_tables)

    Example:
        >>> exists, tables = check_monitor_tables(conn)
        >>> if exists:
        ...     print(f"Monitoring tables available: {len(tables)}")
    """
    try:
        cursor = conn.cursor()

        query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '%Monitor_System_Sample'
            ORDER BY TABLE_NAME
        """

        cursor.execute(query)
        tables = [row[0] for row in cursor.fetchall()]

        logger.info(f"Found {len(tables)} %Monitor.System tables")
        return len(tables) > 0, tables

    except Exception as e:
        logger.error(f"Failed to check monitor tables: {e}")
        return False, []


def is_monitor_collecting(conn) -> Tuple[bool, int]:
    """
    Check if %Monitor.System is actively collecting samples.

    Args:
        conn: Database connection

    Returns:
        (is_collecting, sample_count)

    Example:
        >>> collecting, count = is_monitor_collecting(conn)
        >>> if collecting:
        ...     print(f"Monitoring active with {count} samples")
    """
    try:
        cursor = conn.cursor()

        # Check HistoryPerf table for recent samples
        cursor.execute("SELECT COUNT(*) FROM %Monitor_System_Sample.HistoryPerf")
        count = cursor.fetchone()[0]

        is_active = count > 0
        logger.info(f"Monitor collecting: {is_active} ({count} samples)")

        return is_active, count

    except Exception as e:
        logger.warning(f"Could not check monitoring status: {e}")
        return False, 0


def get_monitor_samples(
    conn, table: str = "HistoryPerf", limit: int = 10
) -> List[Dict]:
    """
    Get recent monitoring samples from %Monitor.System.

    Args:
        conn: Database connection
        table: Sample table name (default: HistoryPerf)
        limit: Maximum number of samples to return

    Returns:
        List of sample dictionaries

    Example:
        >>> samples = get_monitor_samples(conn, "HistoryPerf", limit=5)
        >>> for sample in samples:
        ...     print(f"{sample['DateTime']}: CPU={sample.get('CPUTime', 'N/A')}")
    """
    try:
        cursor = conn.cursor()

        query = f"""
            SELECT TOP {limit} *
            FROM %Monitor_System_Sample.{table}
            ORDER BY DateTime DESC
        """

        cursor.execute(query)

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Convert rows to dictionaries
        samples = []
        for row in cursor.fetchall():
            sample = dict(zip(columns, row))
            samples.append(sample)

        logger.debug(f"Retrieved {len(samples)} samples from {table}")
        return samples

    except Exception as e:
        logger.error(f"Failed to get monitor samples from {table}: {e}")
        return []


def get_monitoring_status(conn) -> MonitoringStatus:
    """
    Get comprehensive %Monitor.System status.

    Args:
        conn: Database connection

    Returns:
        MonitoringStatus object

    Example:
        >>> status = get_monitoring_status(conn)
        >>> if status.is_collecting:
        ...     print(f"Monitoring active: {status.sample_count} samples")
        >>> else:
        ...     print("Monitoring not collecting (may need manual activation)")
    """
    tables_exist, available_tables = check_monitor_tables(conn)
    is_collecting, sample_count = is_monitor_collecting(conn)

    latest_sample = None
    if is_collecting:
        samples = get_monitor_samples(conn, limit=1)
        if samples:
            latest_sample = samples[0].get("DateTime")

    return MonitoringStatus(
        tables_exist=tables_exist,
        is_collecting=is_collecting,
        sample_count=sample_count,
        latest_sample=latest_sample,
        available_tables=available_tables,
    )
