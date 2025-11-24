#!/usr/bin/env python3
"""
Reproducible test case for iris-devtester password reset bug on macOS.

This script reproduces the password reset failure observed on macOS Darwin 24.5.0
with iris-devtester v1.4.2-v1.4.5.

Bug: Password reset commands execute successfully (exit_code=0) but IRIS doesn't
process the change, resulting in "Access Denied" errors on connection attempts.

Expected behavior: Container starts, password resets, connection succeeds.
Actual behavior: Container starts, password reset executes, connection fails.

System: macOS Darwin 24.5.0, Docker Desktop, Python 3.12
"""

import sys
import time

def main():
    print("=" * 80)
    print("iris-devtester macOS Password Reset Bug Reproduction")
    print("=" * 80)
    print()

    # Step 1: Check iris-devtester version
    print("Step 1: Checking iris-devtester version...")
    try:
        import iris_devtester
        version = getattr(iris_devtester, '__version__', 'unknown')
        print(f"✅ iris-devtester version: {version}")

        # Warn if not using v1.4.5
        if version != '1.4.5':
            print(f"⚠️  WARNING: Using version {version}, recommend testing with v1.4.5")
            print(f"   Install with: pip install iris-devtester==1.4.5 --force-reinstall")
    except ImportError as e:
        print(f"❌ Failed to import iris-devtester: {e}")
        print("   Install with: pip install iris-devtester")
        return 1

    print()

    # Step 2: Import required modules
    print("Step 2: Importing iris-devtester modules...")
    try:
        from iris_devtester.containers import IRISContainer
        from iris_devtester.ports import PortRegistry
        print("✅ Modules imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import modules: {e}")
        return 1

    print()

    # Step 3: Create container with PortRegistry
    print("Step 3: Creating IRIS container with PortRegistry...")
    print("   This should assign a unique port from 1973-2022")
    print()

    registry = PortRegistry()
    iris = None

    try:
        iris = IRISContainer.community(
            username='SuperUser',
            password='SYS',
            namespace='HIPPORAG',
            port_registry=registry
        )
        print("✅ Container created")

        # Step 4: Start container
        print()
        print("Step 4: Starting container...")
        iris.start()
        print("✅ Container started")

        # Get assigned port
        port = iris.get_assigned_port()
        print(f"✅ Assigned port: {port}")

        # Step 5: Wait for ready
        print()
        print("Step 5: Waiting for IRIS to be ready (timeout: 90s)...")
        print("   This is where password reset should occur...")
        start_time = time.time()
        iris.wait_for_ready(timeout=90)
        elapsed = time.time() - start_time
        print(f"✅ Container ready after {elapsed:.1f}s")

        # Step 6: Attempt connection (CRITICAL TEST)
        print()
        print("Step 6: Testing connection (CRITICAL - this is where bug manifests)...")
        print("   Expected: Connection succeeds after password reset")
        print("   Bug behavior: Connection fails with 'Access Denied'")
        print()

        try:
            conn = iris.get_connection()
            print("✅ CONNECTION SUCCESSFUL!")
            print("   Password reset worked correctly!")

            # Verify connection with simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
            print("✅ Query executed successfully")

            cursor.close()
            conn.close()

            print()
            print("=" * 80)
            print("🎉 SUCCESS: Password reset bug NOT reproduced!")
            print("=" * 80)
            print()
            print("iris-devtester is working correctly on this system.")

            return 0

        except Exception as e:
            print("❌ CONNECTION FAILED!")
            print(f"   Error: {e}")
            print()
            print("=" * 80)
            print("🐛 BUG REPRODUCED: Password reset failure on macOS")
            print("=" * 80)
            print()
            print("Symptoms:")
            print("- Container starts successfully")
            print("- wait_for_ready() completes without error")
            print("- Password reset command likely executed (exit_code=0)")
            print("- Connection fails with 'Access Denied' or similar error")
            print()
            print("This indicates the password reset executed but IRIS didn't process it.")
            print()

            # Provide diagnostic information
            print("System Information:")
            import platform
            print(f"  OS: {platform.system()} {platform.release()}")
            print(f"  Python: {platform.python_version()}")
            print(f"  iris-devtester: {version}")
            print(f"  Assigned port: {port}")
            print()

            return 1

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Step 7: Cleanup
        if iris:
            print()
            print("Step 7: Cleaning up container...")
            try:
                iris.stop()
                print("✅ Container stopped and cleaned up")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
