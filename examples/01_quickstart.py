"""
Example 1: Quickstart - Zero-config IRIS container.

This example demonstrates the simplest possible usage:
- No configuration needed
- Automatic container lifecycle
- Automatic connection management

Constitutional Principle #4: Zero Configuration Viable
"""

from iris_devtester.containers import IRISContainer


def main():
    """Run a simple query against IRIS."""
    print("Starting IRIS container...")
    # Expected output: Starting IRIS container...

    # That's it! No configuration needed.
    with IRISContainer.community() as iris:
        print("✓ IRIS container started")
        # Expected output: ✓ IRIS container started
        # ⚠️ Note: First run may take 30-60 seconds to pull IRIS image

        # Get connection (automatic password reset if needed)
        conn = iris.get_connection()
        print("✓ Connection established")
        # Expected output: ✓ Connection established
        # ✅ Success: DBAPI connection (~80ms) or JDBC fallback (~250ms)

        # Run a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]
        print(f"✓ IRIS Version: {version}")
        # Expected output: ✓ IRIS Version: IRIS for UNIX (Ubuntu Server LTS for ARM64 Containers) 2024.1 (Build 267U) Mon Mar 25 2024 17:59:16 EDT

        # Get namespace info
        cursor.execute("SELECT $NAMESPACE")
        namespace = cursor.fetchone()[0]
        print(f"✓ Current Namespace: {namespace}")
        # Expected output: ✓ Current Namespace: USER

        cursor.close()

    print("✓ Container cleaned up automatically")
    # Expected output: ✓ Container cleaned up automatically
    # ✅ Success: Total runtime ~5-10 seconds (after image cached)


if __name__ == "__main__":
    main()
