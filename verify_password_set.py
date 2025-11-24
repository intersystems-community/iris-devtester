#!/usr/bin/env python3
"""
Verify that password is actually set in IRIS after hardening.

This checks the user properties directly to see if the password change
is taking effect or being silently ignored.
"""

import subprocess
import sys

from iris_devtester.containers import IRISContainer
from iris_devtester.ports import PortRegistry
from iris_devtester.utils.password_reset import _harden_iris_user

print("=" * 80)
print("Verify Password Setting After Hardening")
print("=" * 80)
print()

iris = None

try:
    # Create container with PortRegistry
    registry = PortRegistry()
    iris = IRISContainer.community(
        username='SuperUser',
        password='SYS',
        namespace='HIPPORAG',
        port_registry=registry
    )

    print("Starting container...")
    iris.start()
    container_name = iris.get_container_name()
    print(f"✅ Container: {container_name}")

    # Wait for basic readiness
    print("Waiting for IRIS...")
    import time
    from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy
    strategy = IRISReadyWaitStrategy(port=iris.get_config().port, timeout=60)
    ready = strategy.wait_until_ready(iris.get_config().host, iris.get_config().port, 60)
    if not ready:
        print("❌ IRIS not ready")
        sys.exit(1)
    print("✅ IRIS ready")

    # Check SuperUser properties BEFORE hardening
    print()
    print("Step 1: Checking SuperUser properties BEFORE hardening...")
    objectscript = """Do ##class(Security.Users).Get("SuperUser",.p)
Write "PasswordNeverExpires=",p("PasswordNeverExpires")," "
Write "ChangePasswordAtNextLogin=",p("ChangePasswordAtNextLogin")
Halt"""

    check_cmd = [
        "docker", "exec", container_name,
        "sh", "-c",
        f'iris session IRIS -U %SYS << "EOF"\n{objectscript}\nEOF'
    ]

    result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
    print(f"BEFORE hardening: {result.stdout.strip()}")

    # Harden SuperUser
    print()
    print("Step 2: Hardening SuperUser...")
    success, message = _harden_iris_user(
        container_name=container_name,
        username="SuperUser",
        password="SYS",
        timeout=30
    )
    print(f"{'✅' if success else '❌'} {message}")

    # Check SuperUser properties AFTER hardening
    print()
    print("Step 3: Checking SuperUser properties AFTER hardening...")
    result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
    print(f"AFTER hardening: {result.stdout.strip()}")

    # Wait for propagation
    print()
    print("Step 4: Waiting 8s for propagation...")
    time.sleep(8)

    # Check AGAIN after propagation
    print()
    print("Step 5: Checking SuperUser properties AFTER propagation...")
    result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
    print(f"AFTER propagation: {result.stdout.strip()}")

    # Try to verify the password by checking authentication
    print()
    print("Step 6: Testing if password is accepted...")
    auth_objectscript = """Set sc=##class(Security.Users).Authenticate("SuperUser","SYS")
If $$$ISOK(sc) { Write "AUTH_SUCCESS" } Else { Write "AUTH_FAILED" }
Halt"""

    auth_test_cmd = [
        "docker", "exec", container_name,
        "sh", "-c",
        f'iris session IRIS -U %SYS << "EOF"\n{auth_objectscript}\nEOF'
    ]

    result = subprocess.run(auth_test_cmd, capture_output=True, text=True, timeout=10)
    print(f"Authentication test: {result.stdout.strip()}")

    if "AUTH_SUCCESS" in result.stdout:
        print("✅ Password is SET and VERIFIED inside IRIS!")
        print()
        print("BUT connection from outside still fails...")
        print("This suggests the issue is with EXTERNAL authentication, not internal.")
    else:
        print("❌ Password authentication failed INSIDE IRIS")
        print("This means the password is not actually being set.")

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
            print("✅ Stopped")
        except Exception as e:
            print(f"⚠️  {e}")
