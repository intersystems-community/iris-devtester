# DBAPI Password Reset Limitation

**Status**: Critical Bug
**Discovered**: 2025-10-16
**Affects**: All iris-devtester password reset utilities
**Impact**: Breaking for automated CI/CD workflows

## The Problem

IRIS requires an interactive password change on first connection to fresh containers. The iris-devtester password reset utilities (`reset_password()`, `unexpire_all_passwords()`) **execute successfully but DO NOT fix the authentication error** when using the DBAPI module.

## Root Cause

There are **TWO different IRIS Python connection modules**:

### 1. `intersystems_iris.dbapi._DBAPI` Module
```python
import intersystems_iris.dbapi._DBAPI as dbapi
conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
```
- ❌ Password reset utilities DON'T work with this
- ❌ Requires interactive password change via Management Portal
- ❌ Breaking for automation

### 2. `iris` Module (Embedded Python)
```python
import iris
conn = iris.connect(
    hostname="localhost",
    port=1972,
    namespace="USER",
    username="_SYSTEM",
    password="SYS"
)
```
- ✅ Password reset utilities WORK with this
- ✅ Automatic password reset via ObjectScript
- ✅ Used by rag-templates successfully

## Why Password Reset Fails with DBAPI

The password reset utilities execute ObjectScript commands successfully:
```objectscript
##class(Security.Users).ChangePassword('_SYSTEM','SYS')
##class(Security.Users).UnExpireUserPasswords("*")
```

However, the DBAPI module's authentication layer **requires an interactive password change flow** that can't be automated via ObjectScript. The `iris` module handles this correctly.

## Evidence from rag-templates

**Critical Finding**: Even rag-templates' "DBAPI connection" code path uses `iris.connect()`, **NOT** `intersystems_iris.dbapi._DBAPI`:

```python
# From rag-templates/common/iris_connection_manager.py:185-196
if reset_iris_password_if_needed(e, max_retries=1):
    logger.info("✓ Password reset successful. Retrying DBAPI connection...")
    import iris  # <-- Uses iris module, not DBAPI!
    conn_params_refreshed = self._get_connection_params(config)
    return iris.connect(  # <-- iris.connect(), not dbapi.connect()
        hostname=conn_params_refreshed["hostname"],
        port=conn_params_refreshed["port"],
        namespace=conn_params_refreshed["namespace"],
        username=conn_params_refreshed["username"],
        password=conn_params_refreshed["password"],
    )
```

**rag-templates NEVER uses `intersystems_iris.dbapi._DBAPI.connect()`**. It always uses `iris.connect()`.

## Impact on iris-devtester

### Current State (BROKEN)
iris-devtester' Constitutional Principle #2 states "DBAPI First, JDBC Fallback" and was designed to use `intersystems_iris.dbapi._DBAPI` as the primary connection method.

**This is fundamentally incompatible with automatic password reset.**

### What Needs to Change

1. **Update Constitutional Principle #2**: Change from "DBAPI First" to "Embedded Python (`iris`) First"
2. **Fix connection manager**: Use `iris.connect()` instead of `intersections_iris.dbapi._DBAPI.connect()`
3. **Update all documentation**: Remove references to DBAPI as primary method
4. **Add warnings**: Document that DBAPI doesn't support auto-remediation

## The Only Manual Solution

When stuck with DBAPI authentication errors, the only fix is manual password change:

### Option 1: Management Portal (Easiest)
1. Open `http://localhost:<port>/csp/sys/UtilHome.csp`
2. Login with `_SYSTEM` / `SYS`
3. You'll be prompted to change password - set it to `SYS` again
4. Done!

### Option 2: Terminal
```bash
docker exec -it <container_name> bash
iris terminal IRIS
# Login as _SYSTEM / SYS
# You'll be prompted to change password
```

## Recommended Fix for iris-devtester

### Change Connection Strategy

**Before (BROKEN)**:
```python
try:
    # Try DBAPI first (doesn't support auto-remediation)
    import intersystems_iris.dbapi._DBAPI as dbapi
    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
except ImportError:
    # Fallback to JDBC
    conn = jaydebeapi.connect(...)
```

**After (FIXED)**:
```python
try:
    # Try embedded Python first (supports auto-remediation)
    import iris
    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
except ImportError:
    # Fallback to JDBC
    conn = jaydebeapi.connect(...)
```

### Update Constitutional Principle #2

**OLD**: "DBAPI First, JDBC Fallback"

**NEW**: "Embedded Python (`iris`) First, JDBC Fallback"

Rationale:
- `iris.connect()` is faster than JDBC
- `iris.connect()` supports automatic password reset (Constitutional Principle #1)
- `iris.connect()` is what rag-templates uses successfully in production
- DBAPI module doesn't support auto-remediation, violating Constitutional Principle #1

## Test Case

```python
import pytest
import intersections_iris.dbapi._DBAPI as dbapi
import iris
from iris_devtester.utils.password_reset import reset_password

def test_password_reset_with_dbapi_EXPECTED_FAILURE():
    """Password reset doesn't work with DBAPI module."""

    # Reset password
    success, msg = reset_password(
        container_name='iris_db',
        username='_SYSTEM',
        new_password='SYS'
    )
    assert success

    # DBAPI connection still fails - this is expected behavior
    with pytest.raises(Exception, match="Password change required"):
        conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")

def test_password_reset_with_iris_connect_SUCCESS():
    """Password reset works with iris.connect()."""

    # Reset password
    success, msg = reset_password(
        container_name='iris_db',
        username='_SYSTEM',
        new_password='SYS'
    )
    assert success

    # iris.connect() works - this is expected behavior
    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    conn.close()
```

## Action Items

- [ ] Update CONSTITUTION.md Principle #2
- [ ] Rewrite `iris_devtester/connections/manager.py` to use `iris.connect()`
- [ ] Update all documentation references
- [ ] Add warnings to password reset utilities about DBAPI incompatibility
- [ ] Create migration guide for existing users
- [ ] Re-run all integration tests with new connection strategy

## Related Files

- `/Users/tdyar/ws/iris-devtester/CONSTITUTION.md` - Principle #2 needs update
- `/Users/tdyar/ws/iris-devtester/iris_devtester/connections/manager.py` - Connection implementation
- `/Users/tdyar/ws/iris-devtester/iris_devtester/utils/password_reset.py` - Works, but needs DBAPI warning
- `/Users/tdyar/ws/rag-templates/common/iris_connection_manager.py` - Reference implementation (uses `iris.connect()`)

## Conclusion

**The iris-devtester package was designed with a fundamentally flawed assumption**: that `intersystems_iris.dbapi._DBAPI` would be the primary connection method. This violates Constitutional Principle #1 (Automatic Remediation) because DBAPI doesn't support automatic password reset.

**The fix**: Change to `iris.connect()` as primary method, matching what rag-templates uses successfully in production.
