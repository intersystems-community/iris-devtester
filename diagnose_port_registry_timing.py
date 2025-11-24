#!/usr/bin/env python3
"""
Diagnostic to investigate timing issues with PortRegistry + password reset.

This adds explicit wait periods and connection tests to understand why
password reset verification fails with PortRegistry.
"""

import logging
import sys
import time

# Enable DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("Diagnostic: PortRegistry + Password Reset Timing Investigation")
print("=" * 80)
print()

from iris_devtester.containers import IRISContainer
from iris_devtester.ports import PortRegistry
from iris_devtester.utils.password_reset import _harden_iris_user
from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection

iris = None

try:
    # Create PortRegistry
    registry = PortRegistry()
    print("✅ PortRegistry created")

    # Create container WITH PortRegistry
    iris = IRISContainer.community(
        username='SuperUser',
        password='SYS',
        namespace='HIPPORAG',
        port_registry=registry
    )
    print("✅ Container created with PortRegistry")

    # Start container (testcontainers-iris may do its own setup here)
    print()
    print("Step 1: Starting container...")
    iris.start()
    container_name = iris.get_container_name()
    config = iris.get_config()
    print(f"✅ Container started: {container_name}")
    print(f"   Port: {config.port}")

    # Wait for IRIS readiness (WITHOUT password reset)
    print()
    print("Step 2: Waiting for IRIS to be ready (basic healthcheck only)...")
    from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy
    strategy = IRISReadyWaitStrategy(port=config.port, timeout=60)
    ready = strategy.wait_until_ready(config.host, config.port, 60)
    if not ready:
        print("❌ IRIS not ready")
        sys.exit(1)
    print("✅ IRIS is ready (basic health check passed)")

    # Add extra settle time
    print()
    print("Step 3: Waiting 10 seconds for IRIS to fully stabilize...")
    time.sleep(10)
    print("✅ Settle period complete")

    # Manual password reset with detailed logging
    print()
    print("Step 4: Manually hardening users (dual user hardening)...")

    # Harden SuperUser first
    print(f"  4a. Hardening SuperUser...")
    success_super, msg_super = _harden_iris_user(
        container_name=container_name,
        username="SuperUser",
        password="SYS",
        timeout=30
    )
    print(f"  {'✅' if success_super else '❌'} SuperUser: {msg_super}")

    # Also harden the target user (if different)
    if config.username != "SuperUser":
        print(f"  4b. Hardening {config.username}...")
        success_user, msg_user = _harden_iris_user(
            container_name=container_name,
            username=config.username,
            password=config.password,
            timeout=30
        )
        print(f"  {'✅' if success_user else '❌'} {config.username}: {msg_user}")

    # Longer settle time on macOS
    import platform
    if platform.system() == "Darwin":
        settle_delay = 8.0  # Even longer than the 4s in code
        print()
        print(f"Step 5: macOS detected - waiting {settle_delay}s for security metadata propagation...")
        time.sleep(settle_delay)
        print(f"✅ macOS settle period complete")

    # Test connection with explicit IPv4
    print()
    print("Step 6: Testing connection with explicit IPv4 (127.0.0.1)...")
    test_config = IRISConfig(
        host="127.0.0.1",  # Explicit IPv4
        port=config.port,
        namespace=config.namespace,
        username="SuperUser",
        password="SYS"
    )

    try:
        conn = get_connection(test_config)
        print("✅ CONNECTION SUCCESSFUL with explicit IPv4!")

        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"✅ Query result: {result}")

        cursor.close()
        conn.close()

        print()
        print("=" * 80)
        print("🎉 SUCCESS: Manual hardening + extended settle time WORKS!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")

        # Try with even more delay
        print()
        print("Connection failed, trying with additional 10s delay...")
        time.sleep(10)

        try:
            conn = get_connection(test_config)
            print("✅ CONNECTION SUCCESSFUL after extra delay!")
            conn.close()
        except Exception as e2:
            print(f"❌ Still failed: {e2}")

            print()
            print("=" * 80)
            print("🐛 BUG: Password reset not taking effect even with extended delays")
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
