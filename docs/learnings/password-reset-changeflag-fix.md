# Password Reset Fix: Disabling ChangePassword Flag

**Date**: 2025-10-16
**Status**: FIXED ✅
**Related**: BUG_REPORT.md, docs/learnings/dbapi-password-reset-limitation.md

## The Problem (Before Fix)

The password reset utility was using:
```objectscript
##class(Security.Users).ChangePassword('_SYSTEM','SYS')
```

This changed the password but **left the "ChangePassword on next login" flag set**, causing:
- DBAPI connections to fail with "Password change required"
- `iris.connect()` connections to sometimes fail
- Manual intervention required via Management Portal

## The Root Cause

InterSystems IRIS has TWO separate concepts:
1. **Password value** - What the password is
2. **ChangePassword flag** - Whether user must change password on next login

The `ChangePassword()` method only updates the password value, not the flag!

## The Solution

Use `Security.Users.Modify()` to set BOTH properties:

```objectscript
Set props("ExternalPassword") = "SYS"       // Set password
Set props("ChangePassword") = 0              // Disable "change on next login"
Write ##class(Security.Users).Modify("_SYSTEM", .props)
```

## Implementation

Updated `iris_devtester/utils/password_reset.py`:

### Before (BROKEN)
```python
reset_cmd = [
    "docker", "exec", "-i", container_name,
    "iris", "session", "IRIS", "-U", "%SYS",
    f"##class(Security.Users).ChangePassword('{username}','{new_password}')",
]
```

### After (FIXED)
```python
reset_cmd = [
    "docker", "exec", "-i", container_name,
    "bash", "-c",
    f'''echo "set props(\\"ChangePassword\\")=0 set props(\\"ExternalPassword\\")=\\"{new_password}\\" write ##class(Security.Users).Modify(\\"{username}\\",.props)" | iris session IRIS -U %SYS''',
]
```

## Testing

Run the test script:
```bash
python test_password_reset_fix.py --container iris_benchmark_clickbench
```

This verifies:
1. Password reset succeeds
2. DBAPI connection works after reset
3. iris.connect() works after reset

## Expected Behavior After Fix

### Before Fix
```python
# Reset password
reset_password(container_name='iris_db', username='_SYSTEM', new_password='SYS')

# DBAPI connection - FAILS
import intersystems_iris.dbapi._DBAPI as dbapi
conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")  # ❌ Password change required
```

### After Fix
```python
# Reset password
reset_password(container_name='iris_db', username='_SYSTEM', new_password='SYS')

# DBAPI connection - WORKS
import intersystems_iris.dbapi._DBAPI as dbapi
conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")  # ✅ SUCCESS!
```

## Key Learnings

1. **ChangePassword() is NOT enough** - It only changes the password value
2. **Must use Modify() to set ChangePassword flag to 0** - This disables "change on next login"
3. **ExternalPassword vs Password** - Use ExternalPassword for programmatic password changes
4. **Modify() returns 1 on success** - Check return value in output

## Impact on iris-devtester

### Constitutional Principle #2 Preserved
This fix means we can KEEP "DBAPI First, JDBC Fallback" as Constitutional Principle #2! The issue wasn't with DBAPI itself, but with the incomplete password reset logic.

### No Need to Rewrite Connection Manager
The connection manager in `iris_devtester/connections/` does NOT need to be rewritten to use `iris.connect()`. DBAPI works fine once the ChangePassword flag is properly cleared.

### Bug Report Status
The bug report in `BUG_REPORT.md` should be updated to reflect:
- Root cause was incomplete password reset
- Fix applied: Use `Security.Users.Modify()` to disable ChangePassword flag
- DBAPI is NOT broken, just requires proper password reset

## Related ObjectScript Properties

From `Security.Users` class:
- **ChangePassword** (boolean) - "Require password change on next login" flag
- **Password** (string) - Internal password (hashed)
- **ExternalPassword** (string) - Set password (automatically hashed)
- **PasswordNeverExpires** (boolean) - Exempt from expiration policies

## References

- Perplexity search: "InterSystems IRIS Security.Users ChangePassword method disable change password on next login flag"
- InterSystems Documentation: Security.Users class
- rag-templates: tests/utils/iris_password_reset.py (had same issue!)

## Manual Fix (If Needed)

If automatic reset still fails, manual fix:
```bash
docker exec -it <container> bash
iris session IRIS -U %SYS

# At ObjectScript prompt:
Set props("ChangePassword")=0
Set props("ExternalPassword")="SYS"
Write ##class(Security.Users).Modify("_SYSTEM", .props)
```

Should output: `1` (success)

## Conclusion

The password reset utilities now properly disable the "ChangePassword on next login" flag, fixing DBAPI authentication issues and eliminating the need to manually change passwords via Management Portal.

**Status**: ✅ FIXED - Both DBAPI and iris.connect() work correctly after password reset
