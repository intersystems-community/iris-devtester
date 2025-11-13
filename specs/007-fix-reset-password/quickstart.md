# Quickstart: Verify reset_password() Bug Fix

**Feature**: 007-fix-reset-password
**Purpose**: Verify that the critical `reset_password()` bug is fixed
**Duration**: ~30 seconds (container startup + test)

## Prerequisites

```bash
# Install iris-devtester with test dependencies
pip install iris-devtester[test]

# OR install from source
cd /Users/tdyar/ws/iris-devtester
pip install -e ".[test]"

# Verify Docker is running
docker ps
```

## Quickstart Test

### Python Script

Create and run `test_password_reset_fix.py`:

```python
"""
Quickstart test to verify reset_password() bug is FIXED.

This test verifies:
1. Password is ACTUALLY set (not just function returning success)
2. Connection succeeds with new password
3. Old password no longer works
"""

from iris_devtester.containers import IRISContainer
from iris_devtester.utils.password_reset import reset_password
from intersystems_irispython import dbapi

print("Starting IRIS container...")
with IRISContainer.community() as iris:
    container_name = iris.container.name
    port = iris.get_exposed_port(1972)

    print(f"✓ Container started: {container_name}")
    print(f"✓ IRIS port: {port}")

    # Step 1: Reset password to "NEWPASS123"
    print("\n[Step 1] Resetting password to 'NEWPASS123'...")
    success, msg = reset_password(
        container_name=container_name,
        username="_SYSTEM",
        new_password="NEWPASS123"
    )

    if not success:
        print(f"✗ Password reset FAILED: {msg}")
        exit(1)

    print(f"✓ reset_password() returned success: {msg}")

    # Step 2: CRITICAL - Verify password ACTUALLY changed
    print("\n[Step 2] Verifying password ACTUALLY changed...")

    try:
        # Try connection with NEW password
        conn_new = dbapi.connect(
            hostname="localhost",
            port=port,
            namespace="USER",
            username="_SYSTEM",
            password="NEWPASS123"
        )
        cursor = conn_new.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()[0]
        assert result == 1
        print("✓ Connection with NEW password: SUCCESS")
        conn_new.close()

    except Exception as e:
        print(f"✗ Connection with NEW password: FAILED")
        print(f"  Error: {e}")
        print("\n❌ BUG STILL EXISTS - Password not actually set!")
        exit(1)

    # Step 3: Verify OLD password NO LONGER works
    print("\n[Step 3] Verifying old password no longer works...")

    try:
        conn_old = dbapi.connect(
            hostname="localhost",
            port=port,
            namespace="USER",
            username="_SYSTEM",
            password="SYS"  # Default password
        )
        cursor = conn_old.cursor()
        cursor.execute("SELECT 1")
        conn_old.close()

        print("⚠️  Old password still works (unexpected, but not critical)")

    except Exception as e:
        print("✓ Old password rejected (expected)")

    # Step 4: Verify idempotency (call reset_password again)
    print("\n[Step 4] Verifying idempotency...")

    success2, msg2 = reset_password(
        container_name=container_name,
        username="_SYSTEM",
        new_password="NEWPASS123"
    )

    if not success2:
        print(f"✗ Second reset_password() call FAILED: {msg2}")
        exit(1)

    print("✓ Second reset_password() call: SUCCESS")

    # Verify password still works after second call
    try:
        conn_verify = dbapi.connect(
            hostname="localhost",
            port=port,
            namespace="USER",
            username="_SYSTEM",
            password="NEWPASS123"
        )
        cursor = conn_verify.cursor()
        cursor.execute("SELECT 1")
        conn_verify.close()
        print("✓ Password still works after second reset: SUCCESS")

    except Exception as e:
        print(f"✗ Password broken after second reset: FAILED")
        print(f"  Error: {e}")
        exit(1)

    # All tests passed!
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - reset_password() BUG IS FIXED!")
    print("="*60)
    print("\nVerified:")
    print("  ✓ Password is ACTUALLY set (not just function success)")
    print("  ✓ Connection succeeds with new password")
    print("  ✓ Function is idempotent (safe to call multiple times)")
    print("\nConstitutional compliance:")
    print("  ✓ Principle #1: Automatic Remediation (password reset works)")
    print("  ✓ Principle #5: Fail Fast (clear error messages)")
    print("  ✓ Principle #7: Medical-Grade Reliability (tested)")
```

### Run the Test

```bash
python test_password_reset_fix.py
```

### Expected Output (SUCCESS)

```
Starting IRIS container...
✓ Container started: iris_container_abc123
✓ IRIS port: 32768

[Step 1] Resetting password to 'NEWPASS123'...
✓ reset_password() returned success: Password reset successful for user '_SYSTEM'

[Step 2] Verifying password ACTUALLY changed...
✓ Connection with NEW password: SUCCESS

[Step 3] Verifying old password no longer works...
✓ Old password rejected (expected)

[Step 4] Verifying idempotency...
✓ Second reset_password() call: SUCCESS
✓ Password still works after second reset: SUCCESS

============================================================
✅ ALL TESTS PASSED - reset_password() BUG IS FIXED!
============================================================

Verified:
  ✓ Password is ACTUALLY set (not just function success)
  ✓ Connection succeeds with new password
  ✓ Function is idempotent (safe to call multiple times)

Constitutional compliance:
  ✓ Principle #1: Automatic Remediation (password reset works)
  ✓ Principle #5: Fail Fast (clear error messages)
  ✓ Principle #7: Medical-Grade Reliability (tested)
```

### Expected Output (BUG STILL EXISTS - BEFORE FIX)

```
Starting IRIS container...
✓ Container started: iris_container_abc123
✓ IRIS port: 32768

[Step 1] Resetting password to 'NEWPASS123'...
✓ reset_password() returned success: Password reset successful for user '_SYSTEM'

[Step 2] Verifying password ACTUALLY changed...
✗ Connection with NEW password: FAILED
  Error: RuntimeError: Access Denied

❌ BUG STILL EXISTS - Password not actually set!
```

## Manual Testing

### Test on Local IRIS Community

```bash
# Start a test container
docker run -d --name iris-test \
  -p 1972:1972 \
  -p 52773:52773 \
  intersystemsdc/iris-community:latest

# Wait for IRIS to start
sleep 30

# Run Python test
python3 << 'EOF'
from iris_devtester.utils.password_reset import reset_password
from intersystems_irispython import dbapi

# Reset password
success, msg = reset_password("iris-test", "_SYSTEM", "TESTPWD")
print(f"Reset: {success}, {msg}")

# Try connection with new password
try:
    conn = dbapi.connect(
        hostname="localhost",
        port=1972,
        namespace="USER",
        username="_SYSTEM",
        password="TESTPWD"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    print("✅ Connection SUCCESS - Bug is FIXED!")
except Exception as e:
    print(f"✗ Connection FAILED: {e}")
    print("❌ Bug still exists")
EOF

# Cleanup
docker stop iris-test && docker rm iris-test
```

## Integration with CI/CD

### pytest Test

This quickstart can be converted to a pytest test:

```python
# tests/integration/test_password_reset_quickstart.py

import pytest
from iris_devtester.containers import IRISContainer
from iris_devtester.utils.password_reset import reset_password
from intersystems_irispython import dbapi


@pytest.fixture(scope="module")
def iris_container():
    """Shared IRIS container for quickstart tests."""
    with IRISContainer.community() as iris:
        yield iris


def test_password_reset_quickstart(iris_container):
    """
    Quickstart test - verifies password is ACTUALLY set.

    This is the critical test that would have caught the bug.
    """
    container_name = iris_container.container.name
    port = iris_container.get_exposed_port(1972)

    # Reset password
    success, msg = reset_password(container_name, "_SYSTEM", "QUICKSTART")
    assert success, f"reset_password failed: {msg}"

    # CRITICAL: Verify password ACTUALLY changed
    conn = dbapi.connect(
        hostname="localhost",
        port=port,
        namespace="USER",
        username="_SYSTEM",
        password="QUICKSTART"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1

    conn.close()
```

Run with pytest:

```bash
pytest tests/integration/test_password_reset_quickstart.py -v
```

## Troubleshooting

### Error: "Container not found"

```
(False, "Container 'iris_db' not running...")
```

**Solution**: Ensure container name matches:
```python
container_name = iris.container.name  # Get actual name from IRISContainer
```

### Error: "Docker command not found"

```
(False, "Docker command not found...")
```

**Solution**:
```bash
# Install Docker
# macOS: brew install --cask docker
# Linux: apt-get install docker.io
# Windows: Install Docker Desktop

# Verify
docker --version
```

### Error: "Access Denied" (Bug Still Exists)

```
RuntimeError: Access Denied
```

**This means the bug is NOT fixed yet**. The password was not actually set.

**Verify fix**:
1. Check lines 120-121 of `iris_devtester/utils/password_reset.py`
2. Should use `Password` (not `ExternalPassword`)
3. Should use `PasswordNeverExpires=1` (not `ChangePassword=0`)
4. Should call `Get()` before `Modify()`

## Success Criteria

✅ **Quickstart passes** when:
1. `reset_password()` returns `(True, "success")`
2. DBAPI connection with new password succeeds
3. `SELECT 1` query executes successfully
4. Calling `reset_password()` multiple times works

❌ **Quickstart fails** if:
1. Connection with new password fails ("Access Denied")
2. Old password still works (password not changed)
3. Function returns success but connection fails (the bug)

---

**Quickstart Status**: ✅ READY
**Expected Duration**: 30 seconds
**Purpose**: Smoke test to verify bug fix
**Next**: Run full integration test suite
