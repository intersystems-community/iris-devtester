#!/usr/bin/env python3
"""
Diagnostic script to test testcontainers-iris WITH PortRegistry.

This mimics the exact scenario from reproduce_macos_password_bug.py to see
why password reset fails with PortRegistry but works without it.
"""

import logging
import sys

# Enable DEBUG logging for all iris_devtester modules
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("Diagnostic: testcontainers-iris WITH PortRegistry")
print("=" * 80)
print()

from iris_devtester.containers import IRISContainer
from iris_devtester.ports import PortRegistry

iris = None

try:
    # Create PortRegistry
    registry = PortRegistry()
    print("✅ PortRegistry created")

    # Create container WITH PortRegistry (exactly like reproduction script)
    iris = IRISContainer.community(
        username='SuperUser',
        password='SYS',
        namespace='HIPPORAG',
        port_registry=registry
    )
    print("✅ Container created with PortRegistry")

    # Start container
    print()
    print("Starting container...")
    iris.start()
    print("✅ Container started")

    # Get container details
    container_name = iris.get_container_name()
    config = iris.get_config()
    assigned_port = iris.get_assigned_port()
    print(f"Container name: {container_name}")
    print(f"Host: {config.host}")
    print(f"Port: {config.port}")
    print(f"Assigned port: {assigned_port}")
    print(f"Namespace: {config.namespace}")
    print(f"Username: {config.username}")
    print()

    # Wait for ready (this is where password reset should happen)
    print("Waiting for container to be ready...")
    ready = iris.wait_for_ready(timeout=90)

    if ready:
        print("✅ Container ready")
    else:
        print("❌ Container NOT ready")
        sys.exit(1)

    # Try to connect
    print()
    print("Attempting connection...")
    try:
        conn = iris.get_connection()
        print("✅ CONNECTION SUCCESSFUL!")

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"Query result: {result}")

        cursor.close()
        conn.close()

        print()
        print("=" * 80)
        print("🎉 SUCCESS: testcontainers-iris WITH PortRegistry WORKS!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        print()
        print("=" * 80)
        print("🐛 BUG CONFIRMED: Password reset fails WITH PortRegistry")
        print("=" * 80)

        # Print diagnostic information
        print()
        print("Container Configuration:")
        print(f"  Name: {container_name}")
        print(f"  Port: {assigned_port}")
        print(f"  Config host: {config.host}")
        print(f"  Config port: {config.port}")
        print()

        sys.exit(1)

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    if iris:
        print()
        print("Cleaning up...")
        try:
            iris.stop()
            print("✅ Container stopped")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
