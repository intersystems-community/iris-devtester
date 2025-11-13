"""
Example 2: Connection Management - DBAPI vs JDBC.

This example demonstrates:
- DBAPI (fast) vs JDBC (fallback) connections
- Automatic connection type selection
- Connection pooling patterns
- Performance comparison

Constitutional Principle #2: Choose the Right Tool
"""

from iris_devtester.containers import IRISContainer
import time


def example_dbapi_connection():
    """Demonstrate DBAPI connection (fast path)."""
    print("=== DBAPI Connection Example ===\n")
    # Expected output: === DBAPI Connection Example ===

    with IRISContainer.community() as iris:
        # DBAPI is tried first (3x faster)
        start = time.time()
        conn = iris.get_connection()
        elapsed_ms = (time.time() - start) * 1000

        print(f"✓ Connection established in {elapsed_ms:.1f}ms")
        # Expected output: ✓ Connection established in 80.5ms (typical DBAPI)
        # ⚠️ Note: JDBC fallback ~250ms if DBAPI unavailable

        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]
        print(f"  Version: {version[:50]}...")
        # Expected output:   Version: IRIS for UNIX (Ubuntu Server LTS for ARM64 C...
        cursor.close()

        print(f"✓ Connection type: {type(conn).__name__}")
        # Expected output: ✓ Connection type: Connection (DBAPI)
        # ✅ Success: DBAPI connection is ~3x faster than JDBC


def example_connection_context():
    """Demonstrate connection lifecycle with context manager."""
    print("\n=== Connection Context Manager ===\n")
    # Expected output: === Connection Context Manager ===

    with IRISContainer.community() as iris:
        # Connection is automatically managed
        with iris.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM %SYS.Namespace")
            count = cursor.fetchone()[0]
            print(f"✓ Found {count} namespaces")
            # Expected output: ✓ Found 5 namespaces (varies by IRIS installation)
            cursor.close()

        # Connection is automatically closed here
        print("✓ Connection closed automatically")
        # Expected output: ✓ Connection closed automatically
        # ✅ Success: No manual cleanup needed


def example_connection_parameters():
    """Demonstrate explicit connection parameters."""
    print("\n=== Custom Connection Parameters ===\n")
    # Expected output: === Custom Connection Parameters ===

    with IRISContainer.community(namespace="USER") as iris:
        conn = iris.get_connection()
        cursor = conn.cursor()

        # Verify namespace
        cursor.execute("SELECT $NAMESPACE")
        namespace = cursor.fetchone()[0]
        print(f"✓ Connected to namespace: {namespace}")
        # Expected output: ✓ Connected to namespace: USER

        # Check username
        cursor.execute("SELECT $USERNAME")
        username = cursor.fetchone()[0]
        print(f"✓ Authenticated as: {username}")
        # Expected output: ✓ Authenticated as: _SYSTEM (default)

        cursor.close()


def example_multiple_connections():
    """Demonstrate multiple concurrent connections."""
    print("\n=== Multiple Concurrent Connections ===\n")
    # Expected output: === Multiple Concurrent Connections ===

    with IRISContainer.community() as iris:
        # Open multiple connections (connection pooling)
        conn1 = iris.get_connection()
        conn2 = iris.get_connection()

        cursor1 = conn1.cursor()
        cursor2 = conn2.cursor()

        # Both connections work independently
        cursor1.execute("SELECT 1 AS ConnNum")
        cursor2.execute("SELECT 2 AS ConnNum")

        result1 = cursor1.fetchone()[0]
        result2 = cursor2.fetchone()[0]

        print(f"✓ Connection 1 result: {result1}")
        print(f"✓ Connection 2 result: {result2}")
        # Expected output:
        # ✓ Connection 1 result: 1
        # ✓ Connection 2 result: 2
        # ✅ Success: Multiple concurrent connections supported

        cursor1.close()
        cursor2.close()


def example_performance_comparison():
    """Compare connection performance."""
    print("\n=== Performance Comparison ===\n")
    # Expected output: === Performance Comparison ===

    with IRISContainer.community() as iris:
        # Measure connection time
        timings = []
        for i in range(3):
            start = time.time()
            conn = iris.get_connection()
            elapsed = (time.time() - start) * 1000
            timings.append(elapsed)

            # Quick query to verify connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()

        avg_time = sum(timings) / len(timings)
        print(f"✓ Average connection time: {avg_time:.1f}ms")
        print(f"  Min: {min(timings):.1f}ms, Max: {max(timings):.1f}ms")
        # Expected output:
        # ✓ Average connection time: 85.3ms
        #   Min: 78.2ms, Max: 92.4ms
        # ⚠️ Note: DBAPI typically 60-100ms, JDBC 200-300ms


def main():
    """Run all connection management examples."""
    example_dbapi_connection()
    example_connection_context()
    example_connection_parameters()
    example_multiple_connections()
    example_performance_comparison()

    print("\n✓ All connection management examples complete")
    # Expected output: ✓ All connection management examples complete
    # ✅ Success: Demonstrates DBAPI-first principle with automatic fallback
    # ⚠️ Note: Total runtime ~15-20 seconds


if __name__ == "__main__":
    main()
