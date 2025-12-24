# IRIS Security.Users API: Password Management Patterns

**Source**: Analysis of IRIS source code at `/databases/sys/cls/Security/Users.xml`
**Feature**: 017-iris-source-insights
**Date**: 2025-12-18

---

## Overview

This document captures official IRIS Security.Users API patterns for password management, derived from source code analysis. These patterns resolve the password reset reliability issues documented in CHANGELOG v1.4.x-v1.5.0.

**Key Discovery**: The `ChangePassword()` method does not exist - it was removed in 2004. The correct approach uses the `Exists()` + object property manipulation pattern.

---

## Critical Property Names

### Correct vs Incorrect Property Names

| Correct | Incorrect | Notes |
|---------|-----------|-------|
| `ChangePassword` | `ChangePasswordAtNextLogin` | Property that controls password-change-required flag |
| `PasswordExternal` | `Password` | Use External to set password (triggers hashing) |
| `AccountNeverExpires` | `AccountNeverExpire` | Note the trailing 's' |
| `PasswordNeverExpires` | `PasswordNeverExpire` | Note the trailing 's' |

### Property Details

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Password` | Password | "" | PBKDF2 hashed password. **DO NOT SET DIRECTLY** |
| `PasswordExternal` | String | "" | Clear text password (transient). Set this to change password |
| `ChangePassword` | BooleanYN | 0 | 0=Not required, 1=Change required before next login |
| `PasswordNeverExpires` | BooleanYN | 0 | 0=Expires per policy, 1=Never expires |
| `AccountNeverExpires` | BooleanYN | 0 | 0=Expires per policy, 1=Never expires |
| `Enabled` | BooleanYN | 1 | 0=Disabled, 1=Enabled |

---

## Available Methods

### Method Availability Reference

| Method | Exists? | Signature | Description |
|--------|---------|-----------|-------------|
| `Exists()` | ✅ Yes | `Exists(name, .obj, .status)` | Check if user exists, returns object handle |
| `Create()` | ✅ Yes | `Create(name, roles, password, ...)` | Create new user with properties |
| `Modify()` | ✅ Yes | `Modify(name, .properties)` | Modify user via properties array |
| `Get()` | ✅ Yes | `Get(name, .properties)` | Get user properties into array |
| `Delete()` | ✅ Yes | `Delete(name)` | Delete user account |
| `UnExpireUserPasswords()` | ✅ Yes | `UnExpireUserPasswords(pattern)` | Clear change-password-required flag |
| `ExpireUserPasswords()` | ✅ Yes | `ExpireUserPasswords(pattern)` | Set change-password-required flag |
| `ChangePassword()` | ❌ **NO** | N/A | **Removed in 2004!** |
| `SetPassword()` | ❌ **NO** | N/A | Does not exist - use PasswordExternal |

### Method Usage Patterns

**Exists() - Check and Get Object Handle**
```objectscript
// Returns 1 if exists, 0 if not
// .user receives the object handle if exists
// .status receives any error status
Set exists = ##class(Security.Users).Exists(username, .user, .status)
If exists {
    // user object is now available for manipulation
    Write user.Name, !
}
```

**Get() - Retrieve Properties Array**
```objectscript
// Get user properties into an array
Set status = ##class(Security.Users).Get(username, .properties)
If $$$ISOK(status) {
    Write "Password expires: ", properties("PasswordNeverExpires"), !
}
```

**Modify() - Update Properties**
```objectscript
// Set properties and apply
Set properties("PasswordNeverExpires") = 1
Set properties("ChangePassword") = 0
Set status = ##class(Security.Users).Modify(username, .properties)
```

**UnExpireUserPasswords() - Batch Clear**
```objectscript
// Clear password-change-required for all users
Do ##class(Security.Users).UnExpireUserPasswords("*")

// Or for specific pattern
Do ##class(Security.Users).UnExpireUserPasswords("test*")
```

---

## Password Setting Pattern

### The Correct Pattern

Use `PasswordExternal` property to set passwords - this triggers automatic PBKDF2 hashing:

```objectscript
// CORRECT: Official pattern from Security.Users source
Set username = "_SYSTEM"
Set newPassword = "SYS"

// Get user object via Exists()
If ##class(Security.Users).Exists(username, .user, .status) {
    // Set password via PasswordExternal (triggers PBKDF2 hashing)
    Set user.PasswordExternal = newPassword

    // Clear password-change-required flag
    Set user.ChangePassword = 0

    // Prevent password expiration
    Set user.PasswordNeverExpires = 1

    // Prevent account expiration
    Set user.AccountNeverExpires = 1

    // Save changes
    Set status = user.%Save()

    If $$$ISERR(status) {
        Do $SYSTEM.Status.DisplayError(status)
    }
}
```

### Why PasswordExternal?

From the source code (lines 639-651):
- `PasswordExternal` is a **transient** property (not stored directly)
- When set and saved, it triggers the password hashing logic
- The hashed result is stored in the `Password` property
- Setting `Password` directly would require you to hash it yourself

---

## Removed Methods

### ChangePassword() - Removed in 2004

**Historical Note** (from source line 263):
> "STC649 10/04/04 Steve Clay, Remove $SYSTEM.Security.Users.ChangePassword"

This confirms that the `ChangePassword()` method was removed on October 4, 2004 - over 20 years ago!

**Implication**: Any code that attempts to call `Security.Users.ChangePassword()` will fail with:
```
<METHOD DOES NOT EXIST> *ChangePassword,Security.Users
```

This was the root cause of the password reset failures documented in CHANGELOG v1.5.0.

---

## Common Mistakes

### What NOT to Do

```objectscript
// ❌ WRONG: ChangePassword() method does not exist!
Do ##class(Security.Users).ChangePassword(username, password)
// Error: <METHOD DOES NOT EXIST> *ChangePassword,Security.Users

// ❌ WRONG: SetPassword() method does not exist!
Do ##class(Security.Users).SetPassword(username, password)
// Error: <METHOD DOES NOT EXIST> *SetPassword,Security.Users

// ❌ WRONG: Property name is ChangePassword, not ChangePasswordAtNextLogin
Set properties("ChangePasswordAtNextLogin") = 0
// Silently ignored - wrong property name

// ❌ WRONG: Don't set Password directly (it's the hashed value)
Set user.Password = "newpassword"
// Stores literal string, not hashed - login will fail

// ❌ WRONG: Missing AccountNeverExpires causes account lockout
Set user.PasswordNeverExpires = 1
// Account can still expire even if password doesn't!
```

### Correct Alternatives

```objectscript
// ✅ CORRECT: Use PasswordExternal to set password
Set user.PasswordExternal = "newpassword"

// ✅ CORRECT: Property name is ChangePassword
Set user.ChangePassword = 0

// ✅ CORRECT: Set both expiration flags for service accounts
Set user.PasswordNeverExpires = 1
Set user.AccountNeverExpires = 1
```

---

## Python Integration Examples

### Docker Exec Pattern (Recommended)

```python
def reset_password(container, username: str, password: str) -> bool:
    """Reset IRIS user password using correct API patterns."""

    # ObjectScript with correct property names
    objectscript = f'''
        Set u="{username}"
        If ##class(Security.Users).Exists(u,.user,.sc) {{
            Set user.PasswordExternal="{password}"
            Set user.ChangePassword=0
            Set user.PasswordNeverExpires=1
            Set user.AccountNeverExpires=1
            Set sc=user.%Save()
            Write $Select($$$ISOK(sc):1,1:0)
        }} Else {{
            Write 0
        }}
        Halt
    '''

    result = container.exec_run(
        ['iris', 'session', 'IRIS', '-U', '%SYS'],
        stdin=True,
        input=objectscript.encode()
    )

    return result.exit_code == 0 and b'1' in result.output
```

### Batch Password Clear

```python
def clear_all_password_requirements(container) -> bool:
    """Clear password-change-required flag for all users."""

    objectscript = '''
        Do ##class(Security.Users).UnExpireUserPasswords("*")
        Write 1
        Halt
    '''

    result = container.exec_run(
        ['iris', 'session', 'IRIS', '-U', '%SYS'],
        stdin=True,
        input=objectscript.encode()
    )

    return result.exit_code == 0
```

---

## Cross-References

### CHANGELOG Entries

- **v1.5.0**: Fixed root cause - `ChangePassword()` method does not exist
- **v1.4.5**: Added dual user hardening (SuperUser + target user)
- **v1.4.4**: Added `ChangePasswordAtNextLogin=0` (wrong property name!)
- **v1.4.3**: Added connection-based verification with retries

### Related Learning Documents

- [dbapi-password-reset-limitation.md](dbapi-password-reset-limitation.md) - Why DBAPI can't reset passwords
- [password-reset-changeflag-fix.md](password-reset-changeflag-fix.md) - Previous fix attempts

### Source Files Analyzed

- `/databases/sys/cls/Security/Users.xml` - Complete Security.Users class
- `/databases/sys/cls/SYS/Container.xml` - Container password patterns

---

## Summary

| Aspect | Correct Pattern |
|--------|-----------------|
| Set password | `user.PasswordExternal = "password"` |
| Clear change requirement | `user.ChangePassword = 0` |
| Prevent password expiry | `user.PasswordNeverExpires = 1` |
| Prevent account expiry | `user.AccountNeverExpires = 1` |
| Batch clear | `##class(Security.Users).UnExpireUserPasswords("*")` |
| Check user exists | `##class(Security.Users).Exists(name, .user, .status)` |

**Remember**: The `ChangePassword()` method does not exist - it was removed in 2004!
