# Research: IRIS Source Insights for Robustness

**Branch**: `017-iris-source-insights`
**Date**: 2025-12-18
**Source**: `/Users/tdyar/ws/vector-shard/iris/latest/`

---

## Executive Summary

Analysis of IRIS source code has revealed critical API patterns and confirmed historical decisions that directly impact iris-devtester reliability. Key findings include confirmation that `ChangePassword()` method was removed in 2004, the correct property name for password-change-on-next-login is `ChangePassword` (not `ChangePasswordAtNextLogin`), and official container patterns from InterSystems' own build process.

---

## Research Area 1: Security.Users Password Management

### Source File
`/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/Security/Users.xml`

### Decision: Use `PasswordExternal` Property for Setting Passwords

**Rationale**: The source code (lines 639-651) shows `PasswordExternal` is the transient clear-text property that triggers PBKDF2 hashing when saved. The `Password` property stores the hashed value and should never be set directly.

**Alternatives Considered**:
- Direct `Password` property manipulation - REJECTED: This is the hashed value, not cleartext
- Using a non-existent `SetPassword()` method - REJECTED: No such method exists as a simple setter

### Key Findings

#### 1. Property Name Correction (CRITICAL)
- **Correct**: `ChangePassword` (line 369-376)
- **Wrong**: `ChangePasswordAtNextLogin` (referenced in CHANGELOG v1.4.4)

The property description from source:
```xml
<Property name="ChangePassword">
<Description>Change password on next login.
0 - Not required
1 - Required before next login</Description>
<Type>%Boolean</Type>
```

#### 2. Historical Confirmation - ChangePassword() Method Removed
Line 263 in the source code change log:
> "STC649 10/04/04 Steve Clay, Remove $SYSTEM.Security.Users.ChangePassword"

This confirms that `Security.Users.ChangePassword()` method was removed in October 2004 (20 years ago!). The iris-devtester CHANGELOG v1.5.0 correctly identifies this as a non-existent method.

#### 3. Available Methods (from source analysis)

| Method | Signature | Description |
|--------|-----------|-------------|
| `Exists()` | `Exists(name, .obj, .status)` | Check if user exists, returns object handle |
| `Create()` | `Create(name, roles, password, ...)` | Create new user with properties |
| `Modify()` | `Modify(name, .properties)` | Modify user via properties array |
| `Get()` | `Get(name, .properties)` | Get user properties into array |
| `Delete()` | `Delete(name)` | Delete user account |
| `UnExpireUserPasswords()` | `UnExpireUserPasswords(pattern)` | Clear change-password-required flag |
| `ExpireUserPasswords()` | `ExpireUserPasswords(pattern)` | Set change-password-required flag |

#### 4. Key Properties (from source lines 342-868)

| Property | Type | Description | API Notes |
|----------|------|-------------|-----------|
| `Password` | Password | PBKDF2 hashed | DO NOT SET DIRECTLY |
| `PasswordExternal` | String | Clear text, transient | Use this to set password |
| `ChangePassword` | BooleanYN | 0=Not required, 1=Required | Set to 0 to clear |
| `PasswordNeverExpires` | BooleanYN | 0=Expires, 1=Never | Set to 1 for service accounts |
| `AccountNeverExpires` | BooleanYN | 0=Expires, 1=Never | Set to 1 for service accounts |
| `Enabled` | BooleanYN | 0=Disabled, 1=Enabled | Account status |

#### 5. Correct Password Reset Pattern (from Modify() implementation, lines 2096-2213)

```objectscript
// Official pattern derived from source
Set username = "_SYSTEM"

// Check user exists and get object handle
If ##class(Security.Users).Exists(username, .user, .status) {
    // Set password via PasswordExternal (triggers PBKDF2 hashing)
    Set user.PasswordExternal = "newpassword"

    // Clear password-change-required flag
    Set user.ChangePassword = 0

    // Prevent future expiration
    Set user.PasswordNeverExpires = 1

    // Save changes
    Set status = user.%Save()
}
```

---

## Research Area 2: Container Lifecycle & Health

### Source File
`/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/SYS/Container.xml`

### Decision: Use InterSystems' Official Container Patterns

**Rationale**: The SYS.Container class is used by InterSystems' own image build process. These patterns are battle-tested in production.

**Alternatives Considered**:
- Custom health check implementations - REJECTED: Official patterns are more reliable
- Skipping account configuration - REJECTED: Causes auth failures

### Key Findings

#### 1. Official Container Quiesce Process (QuiesceForBundling method)

InterSystems uses this exact sequence when building official IRIS images:

```objectscript
// From QuiesceForBundling() - lines 35-72
1. PreventFailoverMessage()     // Clears ^SYS("NODE") to prevent hostname mismatch warnings
2. ForcePasswordChange()        // Sets ChangePassword=1 for all users
3. PreventJournalRolloverMessage()  // Clears ^%SYS("JOURNAL")
4. KillPassword(mgruser)        // Removes password for manager user
5. SetNeverExpires(username)    // Sets AccountNeverExpires=1 for predefined users
6. EnableOSAuthentication()     // Enables OS-based auth for automation
7. SetMonitorStateOK()          // Clears severity 1&2 alerts
```

#### 2. Container Health Check Insight (lines 271-289)

The `PreventFailoverMessage()` method contains a critical insight:

```xml
<Description>
Container healthchecks are based on the System Monitor state. If this failover
message is not suppressed, a new container may spend its first several minutes
with the System Monitor in a "warn" state, which will cause container
healthchecks to fail.
</Description>
```

**Implication**: Container health checks rely on `$SYSTEM.Monitor.State()`. A return value of:
- 0 = OK
- 1 = Warning
- 2 = Error
- 3 = Fatal (do not use container)

#### 3. Password Change Pattern from SYS.Container (ChangePassword method, lines 75-127)

This shows the official InterSystems pattern for batch password changes:

```objectscript
// From ChangePassword() method
Set tResultSet = ##class(Security.Users).ListFunc()
While tResultSet.%Next() {
    Set tName = tResultSet.%Get("Name")
    Set tExists = ##class(Security.Users).Exists(tName,.tUser,.tSC)
    If $$$ISOK(tSC) && tExists {
        Set tUser.PasswordExternal = tPassword  // <-- Uses PasswordExternal!
        Set tSC = tUser.%Save()
    }
}
```

**Key Insight**: InterSystems uses `PasswordExternal` property for setting passwords, confirming this is the correct API.

#### 4. SetNeverExpires Pattern (lines 342-365)

```objectscript
// Sets AccountNeverExpires for a user
do ##Class(Security.Users).Exists(pUsername,.user,.tSC)
return:$$$ISERR(tSC) ..ErrorHandler(tSC)
set user.AccountNeverExpires=1
return ..ErrorHandler(user.%Save())
```

#### 5. ForcePasswordChange Pattern (lines 221-252)

```objectscript
// Force all users to change password on next login
If ((tEnabled="Yes") && (tRoles'="") && (tName'=$$$CSPSystemUsername)) {
    Set tExists = ##class(Security.Users).Exists(tName,.tUser,.tSC)
    If tSC && tExists {
        Set tUser.ChangePassword = 1  // <-- Uses ChangePassword (NOT ChangePasswordAtNextLogin!)
        Set tSC = tUser.%Save()
    }
}
```

---

## Research Area 3: Export/Import Patterns

### Source File
`/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/SYSTEM/OBJ.xml`

### Decision: Use $SYSTEM.OBJ.Export/Import for Class/Routine Operations

**Rationale**: Official API with comprehensive format support (XML, UDL, %RO, CDL, %GOF, CSR/CSP).

### Key Findings

#### 1. Export Method Signature (lines 666-771)

```objectscript
// Export items as an XML file
ClassMethod Export(items, filename, qspec, errorlog, Charset) As %Status

// Supported item types (by extension):
// CLS - Classes
// CSP - Server Pages
// CSR - Rule files
// MAC - Macro routines
// INT - Non-macro routines
// BAS - Basic routines
// INC - Include files
// GBL - Globals
// PRJ - Projects
// OBJ - Compiled object code
// PKG - Package definitions
```

#### 2. Import Method Signature (lines 2678-2759)

```objectscript
// Import, and optionally compile, contents of file or directory
ClassMethod Import(path, qualifiers, selectedItems, errors, imported) As %Status

// Supported formats:
// - XML format
// - %RO format
// - CDL format
// - UDL format
// - %GOF (global output format)
// - CSR/CSP files
```

#### 3. Wildcard Support

Both Export and Import support wildcards:
- `*.cls` - All classes
- `User.*.cls` - All classes in User package
- `'User.T*.cls` - Exclude classes starting with T in User package

---

## Implications for iris-devtester

### 1. Password Reset Module Updates Needed

**Current Issue in CHANGELOG v1.4.4**:
> "Set `ChangePasswordAtNextLogin=0` via `Security.Users.Modify()`"

**Correct Implementation**:
```python
# The property name is ChangePassword, NOT ChangePasswordAtNextLogin
objectscript_code = '''
    Set user.PasswordExternal = "{password}"
    Set user.ChangePassword = 0
    Set user.PasswordNeverExpires = 1
    Set status = user.%Save()
'''
```

### 2. Container Health Check Enhancement

Use `$SYSTEM.Monitor.State()` to verify container readiness:
- Wait for state = 0 (OK) before attempting connections
- Log warning if state = 1 or 2
- Fail fast if state = 3

### 3. Recommended Password Reset Sequence

Based on SYS.Container patterns:

1. Check if user exists: `Security.Users.Exists(username, .user, .status)`
2. Set password: `user.PasswordExternal = password`
3. Clear change-required: `user.ChangePassword = 0`
4. Prevent expiration: `user.PasswordNeverExpires = 1`
5. Prevent account expiration: `user.AccountNeverExpires = 1`
6. Save: `user.%Save()`

---

## Summary of Corrections Needed

| Current Code | Issue | Correct Pattern |
|--------------|-------|-----------------|
| `ChangePasswordAtNextLogin` | Property doesn't exist with this name | `ChangePassword` |
| `Security.Users.ChangePassword()` | Method removed in 2004 | Use `Exists()` + object manipulation |
| Setting `Password` property | This is hashed value | Use `PasswordExternal` |
| Custom health checks | Inconsistent results | Use `$SYSTEM.Monitor.State()` |

---

## References

- `/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/Security/Users.xml`
- `/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/SYS/Container.xml`
- `/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/SYSTEM/OBJ.xml`
- iris-devtester CHANGELOG.md v1.4.x-v1.5.0

---
