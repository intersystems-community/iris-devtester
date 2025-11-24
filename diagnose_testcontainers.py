#!/usr/bin/env python3
"""
Diagnostic script to understand testcontainers-iris behavior.

This mimics the reproduction script but with extensive logging.
"""

import logging
import sys

# Enable DEBUG logging for all iris_devtester modules
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("Diagnostic: testcontainers-iris Password Reset Investigation")
print("=" * 80)
print()

# Step 1: Create container WITHOUT PortRegistry first (simpler case)
print("Step 1: Testing with plain testcontainers-iris (no PortRegistry)...")
print()

from iris_devtester.containers import IRISContainer

iris = None

try:
    # Create container with default configuration
    iris = IRISContainer.community(
        username='SuperUser',
        password='SYS',
        namespace='USER'
    )
    print("✅ Container created")

    # Start container
    print()
    print("Starting container...")
    iris.start()
    print("✅ Container started")

    # Get container details
    container_name = iris.get_container_name()
    config = iris.get_config()
    print(f"Container name: {container_name}")
    print(f"Host: {config.host}")
    print(f"Port: {config.port}")
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
        print("🎉 SUCCESS: testcontainers-iris password reset WORKS!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        print()
        print("=" * 80)
        print("🐛 BUG CONFIRMED: testcontainers-iris password reset fails")
        print("=" * 80)
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
