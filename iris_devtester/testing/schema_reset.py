"""
Schema reset utilities for test isolation and cleanup.

Provides idempotent schema management for integration tests.
Extracted from rag-templates production patterns.

See:
- docs/learnings/rag-templates-production-patterns.md (Pattern 6)
- docs/PHASE_2_PLAN.md (Phase 2.2)
"""

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def reset_namespace(connection: Any, namespace: str) -> None:
    """
    Reset namespace to clean state by dropping all user tables.

    Drops all tables in the specified namespace for test isolation.
    This is idempotent and safe to call multiple times.

    Args:
        connection: Database connection (DBAPI or iris.connect())
        namespace: Namespace to reset (e.g., "USER", "TEST")

    Returns:
        None

    Example:
        >>> conn = iris_container.get_connection()
        >>> reset_namespace(conn, "USER")
        >>> # All user tables in USER namespace have been dropped

    Warning:
        This permanently deletes all data in user tables.
        Only use for test namespaces, never production!

    See Also:
        - docs/learnings/rag-templates-production-patterns.md (Pattern 6)
    """
    cursor = connection.cursor()

    try:
        # Switch to namespace
        cursor.execute(f"SET NAMESPACE {namespace}")

        # Get all user tables (excluding system tables)
        cursor.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND TABLE_SCHEMA NOT LIKE '%SYS%'
              AND TABLE_SCHEMA NOT LIKE 'INFORMATION_SCHEMA'
            ORDER BY TABLE_NAME
        """
        )

        tables = cursor.fetchall()

        if not tables:
            logger.debug(f"No user tables found in namespace {namespace}")
            return

        # Drop each table
        for schema, table in tables:
            table_name = f"{schema}.{table}" if schema else table
            try:
                cursor.execute(f"DROP TABLE {table_name}")
                logger.debug(f"Dropped table: {table_name}")
            except Exception as e:
                logger.warning(f"Could not drop table {table_name}: {e}")

        logger.info(f"✓ Reset namespace {namespace}: dropped {len(tables)} table(s)")

    finally:
        cursor.close()


def get_namespace_tables(connection: Any, namespace: str) -> List[str]:
    """
    Get list of all user tables in namespace.

    Args:
        connection: Database connection
        namespace: Namespace to query

    Returns:
        List of table names in the namespace

    Example:
        >>> conn = iris_container.get_connection()
        >>> tables = get_namespace_tables(conn, "USER")
        >>> print(f"Found {len(tables)} tables: {tables}")
    """
    cursor = connection.cursor()

    try:
        cursor.execute(f"SET NAMESPACE {namespace}")

        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND TABLE_SCHEMA NOT LIKE '%SYS%'
              AND TABLE_SCHEMA NOT LIKE 'INFORMATION_SCHEMA'
            ORDER BY TABLE_NAME
        """
        )

        tables = [row[0] for row in cursor.fetchall()]
        return tables

    finally:
        cursor.close()


def verify_tables_exist(
    connection: Any, namespace: str, expected_tables: List[str]
) -> tuple[bool, List[str]]:
    """
    Verify expected tables exist in namespace.

    Args:
        connection: Database connection
        namespace: Namespace to check
        expected_tables: List of table names that should exist

    Returns:
        Tuple of (all_exist: bool, missing: List[str])

    Example:
        >>> expected = ["Documents", "Chunks", "Entities"]
        >>> all_exist, missing = verify_tables_exist(conn, "USER", expected)
        >>> if not all_exist:
        ...     print(f"Missing tables: {missing}")

    See Also:
        - docs/learnings/rag-templates-production-patterns.md (Pattern 6)
    """
    actual_tables = get_namespace_tables(connection, namespace)

    # Use set operations to find missing tables
    missing = set(expected_tables) - set(actual_tables)

    if missing:
        logger.warning(
            f"Missing tables in namespace {namespace}: {sorted(missing)}\n"
            f"Expected: {sorted(expected_tables)}\n"
            f"Found: {sorted(actual_tables)}"
        )
        return False, sorted(missing)
    else:
        logger.debug(
            f"✓ All expected tables exist in namespace {namespace}: {sorted(expected_tables)}"
        )
        return True, []


def cleanup_test_data(connection: Any, test_id: str) -> int:
    """
    Cleanup test data by test_id.

    Useful when tests share a namespace but need cleanup.
    Deletes rows from all tables that have a test_id column.

    Args:
        connection: Database connection
        test_id: Test identifier to clean up

    Returns:
        Number of tables cleaned

    Example:
        >>> test_id = "TEST_ABC123"
        >>> # Insert test data with test_id
        >>> cursor.execute("INSERT INTO Documents (id, test_id, text) VALUES (1, ?, 'data')", (test_id,))
        >>> # Later, cleanup all data for this test
        >>> cleaned = cleanup_test_data(conn, test_id)
        >>> print(f"Cleaned {cleaned} tables")

    Note:
        Only deletes from tables that have a 'test_id' column.
        Tables without this column are skipped.
    """
    cursor = connection.cursor()
    cleaned_count = 0

    try:
        # Get all tables in current namespace
        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
              AND TABLE_SCHEMA NOT LIKE '%SYS%'
              AND TABLE_SCHEMA NOT LIKE 'INFORMATION_SCHEMA'
        """
        )

        tables = [row[0] for row in cursor.fetchall()]

        # Try to delete from each table
        for table in tables:
            try:
                # Check if table has test_id column
                cursor.execute(
                    """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = ?
                      AND COLUMN_NAME = 'test_id'
                """,
                    (table,),
                )

                if cursor.fetchone():
                    # Table has test_id column, delete matching rows
                    cursor.execute(f"DELETE FROM {table} WHERE test_id = ?", (test_id,))
                    deleted = cursor.rowcount
                    if deleted > 0:
                        logger.debug(
                            f"Deleted {deleted} row(s) from {table} for test_id={test_id}"
                        )
                    cleaned_count += 1

            except Exception as e:
                # Table may not have test_id column or other issue
                logger.debug(f"Could not clean table {table}: {e}")
                continue

        if cleaned_count > 0:
            logger.info(f"✓ Cleaned test data from {cleaned_count} table(s) for test_id={test_id}")
        else:
            logger.debug(f"No tables with test_id column found")

        return cleaned_count

    finally:
        cursor.close()


class SchemaResetter:
    """
    Idempotent schema reset utility for integration tests.

    Provides methods to reset database schema to known state,
    ensuring test isolation.

    Example:
        >>> resetter = SchemaResetter(connection)
        >>> resetter.reset_namespace("TEST")
        >>> # Namespace is now clean

        >>> # Or use context manager
        >>> with SchemaResetter(connection) as resetter:
        ...     resetter.reset_namespace("TEST")

    See Also:
        - docs/learnings/rag-templates-production-patterns.md (Pattern 6)
        - tests/integration/test_schema_reset_integration.py
    """

    def __init__(self, connection: Any):
        """
        Initialize schema resetter.

        Args:
            connection: Database connection
        """
        self.connection = connection

    def reset_namespace(self, namespace: str) -> None:
        """
        Reset namespace to clean state.

        Args:
            namespace: Namespace to reset

        Returns:
            None

        Example:
            >>> with SchemaResetter(conn) as resetter:
            ...     resetter.reset_namespace("TEST")
        """
        reset_namespace(self.connection, namespace)

    def verify_tables(self, namespace: str, expected_tables: List[str]) -> bool:
        """
        Verify expected tables exist.

        Args:
            namespace: Namespace to check
            expected_tables: List of expected table names

        Returns:
            True if all tables exist

        Example:
            >>> with SchemaResetter(conn) as resetter:
            ...     exists = resetter.verify_tables("USER", ["Table1", "Table2"])
            ...     print(f"All tables exist: {exists}")
        """
        all_exist, _ = verify_tables_exist(self.connection, namespace, expected_tables)
        return all_exist

    def get_tables(self, namespace: str) -> List[str]:
        """
        Get list of tables in namespace.

        Args:
            namespace: Namespace to query

        Returns:
            List of table names

        Example:
            >>> with SchemaResetter(conn) as resetter:
            ...     tables = resetter.get_tables("USER")
            ...     print(f"Found {len(tables)} tables: {tables}")
        """
        return get_namespace_tables(self.connection, namespace)

    def cleanup_test_data(self, test_id: str) -> int:
        """
        Cleanup test data by test_id.

        Args:
            test_id: Test identifier

        Returns:
            Number of tables cleaned

        Example:
            >>> with SchemaResetter(conn) as resetter:
            ...     count = resetter.cleanup_test_data("test-run-123")
            ...     print(f"Cleaned {count} tables")
        """
        return cleanup_test_data(self.connection, test_id)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (no cleanup needed)."""
        return False


# For backward compatibility
def reset_schema(connection: Any, namespace: str = "USER") -> None:
    """
    Legacy function - prefer reset_namespace().

    Args:
        connection: Database connection
        namespace: Namespace to reset

    Returns:
        None

    Example:
        >>> conn = iris_container.get_connection()
        >>> reset_schema(conn, "USER")  # Legacy - use reset_namespace() instead
    """
    reset_namespace(connection, namespace)
