"""
Schema reset utilities for test isolation and cleanup.

Provides idempotent schema management for integration tests.
Extracted from rag-templates production patterns.

See:
- docs/learnings/rag-templates-production-patterns.md (Pattern 6)
- docs/PHASE_2_PLAN.md (Phase 2.2)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Schemas that should NEVER be truncated/reset
SYSTEM_SCHEMAS = {
    "INFORMATION_SCHEMA",
    "%SYS",
    "IRISLIB",
    "IRISLOCAL",
    "IRISSYS",
    "SAMPLES",
}

# Default safe order for RAG tables (leaf to root)
DEFAULT_RAG_ORDER = [
    "EntityRelationships",
    "Entities",
    "DocumentChunks",
    "DocumentTokenEmbeddings",
    "SourceDocuments",
]


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

        try:
            tables = cursor.fetchall()
        except Exception:
            tables = []

        if not tables or not isinstance(tables, (list, tuple)):
            logger.debug(f"No user tables found in namespace {namespace}")
            return

        # Drop each table
        for row in tables:
            schema, table = row[0], row[1]
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
                        logger.debug(f"Deleted {deleted} row(s) from {table} for test_id={test_id}")
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

    def get_table_dependencies(self, schema: str) -> List[Tuple[str, str]]:
        """
        Discover foreign key dependencies in a schema.

        Args:
            schema: Schema name to inspect

        Returns:
            List of (child_table, parent_table) tuples
        """
        cursor = self.connection.cursor()
        try:
            # Query InterSystems IRIS specific system table for FKs
            # This looks at which tables refer to which other tables
            cursor.execute(
                """
                SELECT 
                    f.Relation AS child_table,
                    f.ReferencedRelation AS parent_table
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS r
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS f ON r.CONSTRAINT_NAME = f.CONSTRAINT_NAME
                WHERE f.TABLE_SCHEMA = ?
            """,
                (schema,),
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]
        except Exception as e:
            logger.debug(f"Could not discover dynamic dependencies: {e}")
            return []
        finally:
            cursor.close()

    def _topological_sort(self, tables: List[str], dependencies: List[Tuple[str, str]]) -> List[str]:
        """
        Sort tables so that leaf tables (with FKs) come BEFORE parent tables.
        
        This allows safe DELETE without constraint violations.
        """
        from collections import defaultdict, deque

        # Build graph
        adj = defaultdict(list)
        in_degree = {t: 0 for t in tables}
        
        for child, parent in dependencies:
            if child in in_degree and parent in in_degree:
                # Parent depends on child being deleted first? 
                # No, CHILD depends on PARENT.
                # To DELETE safely, we must delete CHILD before PARENT.
                # So edge is: child -> parent (delete child first)
                adj[child].append(parent)
                in_degree[parent] += 1

        # Kahn's algorithm
        queue = deque([t for t in tables if in_degree[t] == 0])
        sorted_tables = []

        while queue:
            u = queue.popleft()
            sorted_tables.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        # If cycles exist or some tables missing, append them
        remaining = set(tables) - set(sorted_tables)
        return sorted_tables + sorted(list(remaining))

    def truncate_schema(
        self,
        schema: str,
        *,
        order: Optional[List[str]] = None,
        use_truncate: bool = False,
        include_system: bool = False,
        strict: bool = False,
        discover_dependencies: bool = True,
    ) -> Dict[str, Any]:
        """
        Truncate or delete all data from all tables in a specific schema.

        Discovers tables at runtime and attempts to delete/truncate in a safe order.
        Uses dynamic FK discovery where possible, falling back to alphabetical or provided order.

        Args:
            schema: Schema name to clean (e.g. "RAG")
            order: Optional priority list of tables to clean FIRST (leaf tables).
            use_truncate: If True, use TRUNCATE TABLE instead of DELETE FROM.
            include_system: If True, allow cleaning system schemas (DANGEROUS).
            strict: If True, raise exception on first table failure.
            discover_dependencies: If True, query IRIS metadata to find FK order.

        Returns:
            Dictionary with results: {"total": int, "success": int, "failed": int, "errors": list}

        Raises:
            ValueError: If schema is in blocklist and include_system=False.
            RuntimeError: If strict=True and a query fails.
        """
        if not include_system and schema.upper() in SYSTEM_SCHEMAS:
            raise ValueError(f"Schema '{schema}' is a protected system schema.")

        cursor = self.connection.cursor()
        results = {"total": 0, "success": 0, "failed": 0, "errors": []}

        try:
            # 1. Discover all tables in schema
            cursor.execute(
                """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = ?
                  AND TABLE_TYPE = 'BASE TABLE'
            """,
                (schema,),
            )
            all_tables = [row[0] for row in cursor.fetchall()]
            results["total"] = len(all_tables)

            if not all_tables:
                logger.debug(f"No tables found in schema '{schema}'")
                return results

            # 2. Determine deletion order
            final_order = []
            if discover_dependencies:
                deps = self.get_table_dependencies(schema)
                if deps:
                    final_order = self._topological_sort(all_tables, deps)
            
            if not final_order:
                # Fallback to provided order then alphabetical
                clean_order = order or []
                remaining = sorted(list(set(all_tables) - set(clean_order)))
                final_order = clean_order + remaining

            # 3. Execute cleanup
            verb = "TRUNCATE TABLE" if use_truncate else "DELETE FROM"
            for table in final_order:
                # Skip if not in discovery (if order was provided but table missing)
                if table not in all_tables:
                    continue

                full_name = f"{schema}.{table}"
                try:
                    cursor.execute(f"{verb} {full_name}")
                    results["success"] += 1
                    logger.debug(f"Cleaned table {full_name} via {verb}")
                except Exception as e:
                    results["failed"] += 1
                    err_msg = f"Failed to clean {full_name}: {str(e)}"
                    results["errors"].append(err_msg)
                    if strict:
                        raise RuntimeError(err_msg)
                    logger.warning(err_msg)

            if results["failed"] == 0:
                logger.info(f"✓ Successfully cleaned schema '{schema}' ({results['success']} tables)")
            else:
                logger.warning(
                    f"⚠ Cleaned schema '{schema}' with issues: "
                    f"{results['success']} success, {results['failed']} failed"
                )

            return results

        finally:
            cursor.close()

    def reset_rag_schema(self, schema: str = "RAG", **kwargs) -> Dict[str, Any]:
        """
        Opinionated helper to reset the RAG schema.

        Uses DEFAULT_RAG_ORDER to handle FK dependencies common in vector/RAG projects.

        Args:
            schema: RAG schema name (default: "RAG")
            **kwargs: Arguments passed to truncate_schema (use_truncate, strict, etc.)

        Returns:
            Cleanup results summary
        """
        # Merge DEFAULT_RAG_ORDER into kwargs
        kwargs.setdefault("order", DEFAULT_RAG_ORDER)
        return self.truncate_schema(schema, **kwargs)

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
