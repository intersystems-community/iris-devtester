# Data Model: Security.Users (IRIS System Object)

**Feature**: 007-fix-reset-password
**Date**: 2025-01-09

## Overview

The `Security.Users` object is an IRIS system class that manages user accounts, authentication, and password policies. This bug fix modifies how we interact with this object's properties.

## Entity: Security.Users

**Class**: `Security.Users` (IRIS system class)
**Namespace**: `%SYS`
**Purpose**: User account and authentication management

### Properties (Relevant to Bug Fix)

#### Password (string, hashed)
- **Type**: String (stored as hash)
- **Purpose**: The user's authentication password
- **Access**: Read/Write via Get()/Modify() API
- **Validation**: IRIS enforces password complexity rules
- **Storage**: Hashed with IRIS internal algorithm
- **Usage**: `Set prop("Password") = "plaintextpassword"` (IRIS hashes automatically)

**CRITICAL**:
- ✅ **USE THIS** for setting passwords
- ❌ **NOT** `ExternalPassword` (different property for external auth)

#### PasswordNeverExpires (0/1 flag)
- **Type**: Boolean (0 or 1)
- **Purpose**: Controls whether password expires based on system policy
- **Values**:
  - `1` = Password never expires (recommended for automated setups)
  - `0` = Password expires according to system policy (default)
- **Access**: Read/Write via Get()/Modify() API
- **Usage**: `Set prop("PasswordNeverExpires") = 1`

**CRITICAL**:
- ✅ **USE THIS** to prevent password expiration
- ❌ **NOT** `ChangePassword` (different purpose)

#### ChangePassword (0/1 flag) - NOT USED
- **Type**: Boolean (0 or 1)
- **Purpose**: Force user to change password on next login
- **Values**:
  - `1` = User must change password on next login
  - `0` = User can login with current password (default)
- **Usage in our context**: ❌ **DO NOT USE** - Wrong property for preventing expiration

**Why not used**:
- This flag is for forcing password changes, not preventing expiration
- Setting this to 0 doesn't prevent password expiration
- Current bug: Using `ChangePassword=0` instead of `PasswordNeverExpires=1`

#### ExternalPassword (string) - NOT USED
- **Type**: String
- **Purpose**: Password for external authentication systems (LDAP, Kerberos)
- **Usage in our context**: ❌ **DO NOT USE** - Not for standard IRIS authentication

**Why not used**:
- This property is for external auth integration
- Does not work for standard IRIS database authentication
- Current bug: Using `ExternalPassword` instead of `Password`

### API Pattern

#### Correct Pattern (Get → Set → Modify)

```objectscript
// 1. Get current properties
Set sc = ##class(Security.Users).Get("_SYSTEM", .props)

// 2. Modify desired properties
Set props("Password") = "newpassword"
Set props("PasswordNeverExpires") = 1

// 3. Save changes
Set sc = ##class(Security.Users).Modify("_SYSTEM", .props)
```

**Why this pattern**:
- `Get()` retrieves ALL current properties (preserves values)
- Modify specific properties in the array
- `Modify()` saves only changed properties back to IRIS

#### Incorrect Pattern (Modify without Get)

```objectscript
// ❌ WRONG - Missing Get()
Set props("ChangePassword") = 0
Set props("ExternalPassword") = "newpassword"
Write ##class(Security.Users).Modify("_SYSTEM", .props)
```

**Why this fails**:
1. No `Get()` call - other properties may be lost/reset
2. Wrong property names (`ExternalPassword` vs `Password`)
3. Wrong flag (`ChangePassword=0` vs `PasswordNeverExpires=1`)
4. Password not actually set in IRIS

## State Transitions

### Password Reset Flow

```
┌─────────────────────┐
│ Initial State       │
│ - Password: "old"   │
│ - Expired: maybe    │
└──────────┬──────────┘
           │
           │ reset_password(new_password="new")
           ▼
┌─────────────────────────┐
│ Get() Current Properties│ ← CRITICAL STEP
│ - Retrieves all props   │
└──────────┬──────────────┘
           │
           │ Set props("Password") = "new"
           │ Set props("PasswordNeverExpires") = 1
           ▼
┌─────────────────────────┐
│ Modify() Saves Changes  │
│ - Password hashed       │
│ - Never expires set     │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────┐
│ Final State         │
│ - Password: "new"   │
│ - Never expires: 1  │
│ ✅ Connection works │
└─────────────────────┘
```

### Current Bug Flow (BROKEN)

```
┌─────────────────────┐
│ Initial State       │
│ - Password: "old"   │
└──────────┬──────────┘
           │
           │ reset_password(new_password="new")
           ▼
┌─────────────────────────────┐
│ ❌ NO Get() Call            │
│ Set props("ChangePassword")=0     │ ← WRONG PROPERTY
│ Set props("ExternalPassword")="new" │ ← WRONG PROPERTY
└──────────┬────────────────────┘
           │
           │ Modify() attempted
           ▼
┌─────────────────────┐
│ Final State         │
│ - Password: "old"   │ ← NOT CHANGED!
│ - Never expires: 0  │ ← NOT SET!
│ ❌ Connection FAILS │
│ Function returns    │
│ (True, "success")   │ ← LYING!
└─────────────────────┘
```

## Validation Rules

### Password Complexity (enforced by IRIS)
- Minimum length: Varies by IRIS configuration
- May require uppercase, lowercase, numbers, special characters
- IRIS validates and rejects weak passwords
- Our code: Let IRIS handle validation (Constitutional Principle #4)

### PasswordNeverExpires
- Valid values: 0 or 1 only
- Type: Integer (not string)
- Default: 0 (password expires)

## Error Handling

### Possible IRIS Errors

1. **User not found**:
   ```objectscript
   Set sc = ##class(Security.Users).Get("NONEXISTENT", .props)
   // sc = 0 (error)
   ```
   - Our handling: Existing error messages preserved

2. **Invalid password**:
   ```objectscript
   Set props("Password") = "weak"
   Set sc = ##class(Security.Users).Modify("_SYSTEM", .props)
   // sc = 0 (error) - Password doesn't meet complexity requirements
   ```
   - Our handling: Let IRIS validate, existing error handling

3. **Permission denied**:
   ```objectscript
   // If not running as %SYS user
   Set sc = ##class(Security.Users).Modify("_SYSTEM", .props)
   // sc = 0 (error) - Insufficient privileges
   ```
   - Our handling: Use `iris session IRIS -U %SYS` (already correct)

## Data Persistence

### Storage
- Database: IRIS system database
- Namespace: `%SYS`
- Class storage: `Security.Users` class definition
- Password hash algorithm: IRIS internal (SHA-256 based)

### Idempotency
- Setting same password multiple times: ✅ Safe
- Setting PasswordNeverExpires=1 multiple times: ✅ Safe
- Get() → Modify() pattern: ✅ Idempotent

## Testing Considerations

### Integration Test Queries

**Verify password changed**:
```python
# Can't query password hash (security), but can verify connection works
conn = dbapi.connect(password="newpassword")  # Success = password set
```

**Verify PasswordNeverExpires**:
```python
cursor.execute("""
    SELECT $SYSTEM.SQL.Functions.EXECUTE(
        'Set sc = ##class(Security.Users).Get("_SYSTEM",.p) ' ||
        'Write p("PasswordNeverExpires")'
    )
""")
result = cursor.fetchone()[0]
assert result == "1"
```

## Summary

**Critical Properties**:
- ✅ `Password` - The actual password (hashed by IRIS)
- ✅ `PasswordNeverExpires` - Prevents password expiration

**Incorrect Properties** (current bug):
- ❌ `ExternalPassword` - Wrong property for standard auth
- ❌ `ChangePassword` - Wrong flag, doesn't prevent expiration

**Required Pattern**:
1. Get() current properties
2. Set Password and PasswordNeverExpires
3. Modify() to save

**Bug Impact**:
- Password not set → "Access Denied" errors
- PasswordNeverExpires not set → Password expires later
- Function lies about success

---

**Status**: ✅ COMPLETE
**Next**: Create API contracts
