"""
Example 1: Quickstart - Zero-config IRIS container.

This example demonstrates the simplest possible usage:
- No configuration needed
- Automatic container lifecycle
- Automatic connection management

Constitutional Principle #4: Zero Configuration Viable
"""

from iris_devtools.containers import IRISContainer


def main():
    """Run a simple query against IRIS."""
    print("Starting IRIS container...")

    # That's it! No configuration needed.
    with IRISContainer.community() as iris:
        print("✓ IRIS container started")

        # Get connection (automatic password reset if needed)
        conn = iris.get_connection()
        print("✓ Connection established")

        # Run a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]
        print(f"✓ IRIS Version: {version}")

        # Get namespace info
        cursor.execute("SELECT $NAMESPACE")
        namespace = cursor.fetchone()[0]
        print(f"✓ Current Namespace: {namespace}")

        cursor.close()

    print("✓ Container cleaned up automatically")


if __name__ == "__main__":
    main()
