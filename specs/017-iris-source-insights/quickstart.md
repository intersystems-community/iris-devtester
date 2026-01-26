# Quickstart: IRIS API Patterns

**Branch**: `017-iris-source-insights`
**Purpose**: Essential patterns derived from IRIS source code analysis

---

## Pattern 1: Password Reset (Correct API)

### ObjectScript Pattern

```objectscript
// CORRECT: Official pattern from Security.Users source
Set username = "_SYSTEM"
Set newPassword = "SYS"

// Get user object
If ##class(Security.Users).Exists(username, .user, .status) {
    // Set password via PasswordExternal (triggers PBKDF2 hashing)
    Set user.PasswordExternal = newPassword

    // Clear password-change-required flag
    // NOTE: Property is "ChangePassword", NOT "ChangePasswordAtNextLogin"
    Set user.ChangePassword = 0

    // Prevent password expiration
    Set user.PasswordNeverExpires = 1

    // Prevent account expiration
    Set user.AccountNeverExpires = 1

    // Save changes
    Set status = user.%Save()

    If $$$ISERR(status) {
        Do $SYSTEM.Status.DisplayError(status)
    } Else {
        Write "Password reset successful", !
    }
}
```

### Python via Docker Exec

```python
def reset_password(container, username: str, password: str) -> bool:
    """Reset IRIS user password using correct API."""

    # CRITICAL: Use ChangePassword, NOT ChangePasswordAtNextLogin
    objectscript = f'''
        Set u="{username}"
        If ##class(Security.Users).Exists(u,.user,.sc) {{
            Set user.PasswordExternal="{password}"
            Set user.ChangePassword=0
            Set user.PasswordNeverExpires=1
            Set user.AccountNeverExpires=1
            Write ##class(Security.Users).Modify(u,.user)
        }}
        Halt
    '''

    result = container.exec_run(
        f'iris session IRIS -U%SYS "{objectscript}"'
    )
    return result.exit_code == 0
```

### Common Mistakes to Avoid

```python
# ❌ WRONG: ChangePassword() method does not exist (removed in 2004!)
"Do ##class(Security.Users).ChangePassword(username, password)"

# ❌ WRONG: Property name is ChangePassword, not ChangePasswordAtNextLogin
"Set properties(\"ChangePasswordAtNextLogin\") = 0"

# ❌ WRONG: Don't set Password directly (it's the hashed value)
"Set user.Password = \"newpassword\""

# ✅ CORRECT: Use PasswordExternal (triggers automatic hashing)
"Set user.PasswordExternal = \"newpassword\""

# ✅ CORRECT: Property name is ChangePassword
"Set user.ChangePassword = 0"
```

---

## Pattern 2: Container Health Check

### ObjectScript Pattern

```objectscript
// Check container health using System Monitor state
Set state = $SYSTEM.Monitor.State()

If state = 0 {
    Write "Container is healthy (OK)", !
} ElseIf state = 1 {
    Write "Container has warnings", !
} ElseIf state = 2 {
    Write "Container has errors", !
} ElseIf state = 3 {
    Write "Container is in fatal state - do not use", !
}
```

### Python Health Check

```python
def check_container_health(container) -> tuple[bool, str]:
    """Check IRIS container health using official API."""

    objectscript = '''
        Write $SYSTEM.Monitor.State()
        Halt
    '''

    result = container.exec_run(
        f'iris session IRIS -U%SYS "{objectscript}"'
    )

    if result.exit_code != 0:
        return False, "Failed to execute health check"

    state = int(result.output.decode().strip())

    states = {
        0: (True, "OK - Container healthy"),
        1: (True, "Warning - Container has minor issues"),
        2: (False, "Error - Container has problems"),
        3: (False, "Fatal - Container unusable"),
    }

    return states.get(state, (False, f"Unknown state: {state}"))
```

---

## Pattern 3: Batch Password Operations

### Clear All Password-Change-Required Flags

```objectscript
// Official pattern: Clear password change requirement for all users
Do ##class(Security.Users).UnExpireUserPasswords("*")
```

### Set Accounts to Never Expire

```objectscript
// Pattern from SYS.Container.SetNeverExpires()
Set usernames = $LB("_SYSTEM", "Admin", "SuperUser", "CSPSystem")

For i = 1:1:$LL(usernames) {
    Set username = $LG(usernames, i)
    Do ##class(Security.Users).Exists(username, .user, .status)
    If $$$ISOK(status) {
        Set user.AccountNeverExpires = 1
        Set user.PasswordNeverExpires = 1
        Do user.%Save()
    }
}
```

---

## Pattern 4: Export/Import Classes

### Export Classes to XML

```objectscript
// Export single class
Do $SYSTEM.OBJ.Export("MyPackage.MyClass.cls", "/tmp/myclass.xml")

// Export entire package
Do $SYSTEM.OBJ.ExportPackage("MyPackage", "/tmp/mypackage.xml")

// Export with wildcards
Do $SYSTEM.OBJ.Export("MyPackage.*.cls", "/tmp/all-classes.xml")
```

### Import Classes

```objectscript
// Import from file
Do $SYSTEM.OBJ.Import("/tmp/myclass.xml", "/compile")

// Import and compile
Do $SYSTEM.OBJ.Import("/tmp/mypackage.xml", "/compile/displaylog")

// List without importing
Do $SYSTEM.OBJ.Import("/tmp/mypackage.xml", "/load=0")
```

---

## Quick Reference Card

### Property Names (Correct vs Wrong)

| Correct | Wrong | Notes |
|---------|-------|-------|
| `ChangePassword` | `ChangePasswordAtNextLogin` | Boolean 0/1 |
| `PasswordExternal` | `Password` | Use External to set |
| `AccountNeverExpires` | `AccountNeverExpire` | Note the 's' |

### Method Availability

| Method | Exists? | Notes |
|--------|---------|-------|
| `Security.Users.Exists()` | ✅ Yes | Returns object handle |
| `Security.Users.Create()` | ✅ Yes | Creates new user |
| `Security.Users.Modify()` | ✅ Yes | Modifies via properties |
| `Security.Users.Get()` | ✅ Yes | Gets properties array |
| `Security.Users.ChangePassword()` | ❌ No | Removed in 2004! |
| `Security.Users.SetPassword()` | ❌ No | Use PasswordExternal |

### Health States

| State | Meaning | Action |
|-------|---------|--------|
| 0 | OK | Safe to connect |
| 1 | Warning | May work, log warning |
| 2 | Error | Likely to fail |
| 3 | Fatal | Do not use |

---
