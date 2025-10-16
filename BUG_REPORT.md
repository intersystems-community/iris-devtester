# Critical Bug: Password Reset Doesn't Work with DBAPI Module

**Status**: 🔴 Critical
**Discovered**: 2025-10-16
**Severity**: High - Breaking for automated workflows
**Affects**: All versions of iris-devtools

## Summary

The password reset utilities in iris-devtools execute successfully but **DO NOT fix authentication errors** when using `intersystems_iris.dbapi._DBAPI.connect()`. This violates Constitutional Principle #1 (Automatic Remediation Over Manual Intervention).

## Root Cause

iris-devtools was designed with Constitutional Principle #2: "DBAPI First, JDBC Fallback". However, the DBAPI module **does not support automatic password reset**, requiring manual interactive password change via Management Portal.

**Discovery**: Even rag-templates (the source of this code) uses `iris.connect()` everywhere, **NEVER** `intersystems_iris.dbapi._DBAPI.connect()`.

## Impact

### Broken Workflows
1. ❌ Fresh Docker containers require manual password change
2. ❌ CI/CD pipelines break on first connection
3. ❌ Constitutional Principle #1 violated (no automatic remediation)
4. ❌ Zero-config operation broken (Principle #4)

### What Works
- ✅ `iris.connect()` - Password reset works correctly
- ✅ JDBC connections - Password reset works correctly
- ❌ DBAPI module - Password reset fails silently

## Evidence

### Test Case (DBAPI - FAILS)
```python
import intersystems_iris.dbapi._DBAPI as dbapi
from iris_devtools.utils.password_reset import reset_password

# First connection fails
try:
    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
except Exception as e:
    print(f"Error: {e}")  # "Password change required"

    # Reset password - reports SUCCESS
    success, msg = reset_password(
        container_name='iris_db',
        username='_SYSTEM',
        new_password='SYS'
    )
    print(f"Reset: {success}")  # True

    # Retry - STILL FAILS
    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
    # Still raises "Password change required"
```

### Test Case (iris.connect - WORKS)
```python
import iris
from iris_devtools.utils.password_reset import reset_password

# First connection fails
try:
    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
except Exception as e:
    print(f"Error: {e}")  # "Password change required"

    # Reset password - reports SUCCESS
    success, msg = reset_password(
        container_name='iris_db',
        username='_SYSTEM',
        new_password='SYS'
    )
    print(f"Reset: {success}")  # True

    # Retry - NOW WORKS
    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )  # SUCCESS!
    conn.close()
```

### Evidence from rag-templates

From `rag-templates/common/iris_connection_manager.py` lines 185-196:

```python
if reset_iris_password_if_needed(e, max_retries=1):
    logger.info("✓ Password reset successful. Retrying DBAPI connection...")
    # Even the "DBAPI path" uses iris.connect()!
    import iris
    conn_params_refreshed = self._get_connection_params(config)
    return iris.connect(  # NOT dbapi.connect()
        hostname=conn_params_refreshed["hostname"],
        port=conn_params_refreshed["port"],
        namespace=conn_params_refreshed["namespace"],
        username=conn_params_refreshed["username"],
        password=conn_params_refreshed["password"],
    )
```

**Critical Finding**: rag-templates NEVER uses `intersystems_iris.dbapi._DBAPI.connect()`. It always uses `iris.connect()` after password reset.

## Workaround (Manual)

### Option 1: Management Portal
1. Open `http://localhost:<port>/csp/sys/UtilHome.csp`
2. Login with `_SYSTEM` / `SYS`
3. You'll be prompted to change password - set to `SYS` again
4. Done!

### Option 2: Terminal
```bash
docker exec -it <container_name> iris terminal IRIS
# Login as _SYSTEM / SYS
# Follow password change prompts
```

## Recommended Fix

### 1. Update Constitutional Principle #2

**OLD**: "DBAPI First, JDBC Fallback"

**NEW**: "Embedded Python (`iris.connect()`) First, JDBC Fallback"

**Rationale**:
- Supports automatic password reset (Principle #1)
- Faster than JDBC
- What rag-templates uses successfully
- Compatible with zero-config (Principle #4)

### 2. Rewrite Connection Manager

**Before (BROKEN)**:
```python
try:
    import intersystems_iris.dbapi._DBAPI as dbapi
    return dbapi.connect(...)  # Doesn't support auto-remediation
except ImportError:
    return jaydebeapi.connect(...)
```

**After (FIXED)**:
```python
try:
    import iris
    return iris.connect(  # Supports auto-remediation
        hostname=...,
        port=...,
        namespace=...,
        username=...,
        password=...
    )
except ImportError:
    return jaydebeapi.connect(...)
```

### 3. Add Warnings

Update password reset utilities to warn about DBAPI incompatibility:

```python
def reset_password(...):
    """
    Reset IRIS user password.

    WARNING: This works with iris.connect() and JDBC, but NOT with
             intersystems_iris.dbapi._DBAPI.connect(). The DBAPI module
             requires interactive password change via Management Portal.

    Use iris.connect() for automatic password reset support.
    """
```

## Action Items

- [ ] Update `CONSTITUTION.md` Principle #2
- [ ] Rewrite `iris_devtools/connections/manager.py`
- [ ] Update all documentation
- [ ] Add DBAPI warnings to password utilities
- [ ] Re-run all tests
- [ ] Create migration guide
- [ ] Update README with correct connection method
- [ ] Document this as "Blind Alley" (Principle #8)

## Files Affected

- `CONSTITUTION.md` - Principle #2 update
- `iris_devtools/connections/manager.py` - Connection implementation
- `iris_devtools/utils/password_reset.py` - Add warnings
- `README.md` - Update examples
- `docs/` - All connection examples
- All integration tests - Verify with new connection method

## Related Issues

This explains why:
- Feature 002 integration tests were blocked
- Fresh containers require manual intervention
- CI/CD workflows fail intermittently
- Zero-config doesn't actually work

## Timeline

**Discovered**: 2025-10-16 during benchmark runner development
**Root Cause**: Design assumption that DBAPI would be primary method
**Fix Required**: Change to `iris.connect()` as primary method
**Priority**: Critical - blocks Constitutional compliance

## Additional Context

See `/Users/tdyar/ws/iris-devtools/docs/learnings/dbapi-password-reset-limitation.md` for complete technical analysis.

Original bug report: `/Users/tdyar/ws/arno/benchmarks/iris_comparison/BUG_REPORT_iris-devtools.md`

## Conclusion

**iris-devtools cannot achieve Constitutional Principle #1 (Automatic Remediation) while using DBAPI as primary connection method.**

The fix is to match rag-templates: use `iris.connect()` as primary, with JDBC fallback. This requires updating Constitutional Principle #2 and rewriting the connection manager.
