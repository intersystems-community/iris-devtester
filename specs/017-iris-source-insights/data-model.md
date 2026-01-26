# Data Model: IRIS Security.Users Properties

**Branch**: `017-iris-source-insights`
**Source**: `/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/Security/Users.xml`

---

## Entity: Security.Users

The `Security.Users` class manages IRIS user accounts, passwords, and permissions.

### Password-Related Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Password` | Password | "" | PBKDF2 hashed password. **DO NOT SET DIRECTLY** |
| `PasswordExternal` | String | "" | Clear text password (transient). Set this to change password |
| `ChangePassword` | BooleanYN | 0 | 0=Not required, 1=Change required before next login |
| `PasswordNeverExpires` | BooleanYN | 0 | 0=Expires per policy, 1=Never expires |
| `PasswordChangedDate` | %TimeStamp | "" | When password was last changed |

### Account-Related Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Name` | String | "" | Username (primary key) |
| `Enabled` | BooleanYN | 1 | 0=Disabled, 1=Enabled |
| `AccountNeverExpires` | BooleanYN | 0 | 0=Expires per policy, 1=Never expires |
| `ExpirationDate` | %TimeStamp | "" | When account expires |
| `Roles` | String | "" | Comma-separated list of roles |

### Validation Rules

1. **Username**: Must be non-empty, unique
2. **Password**: When set via `PasswordExternal`, automatically hashed to PBKDF2
3. **ChangePassword**: Must be 0 or 1 (BooleanYN)
4. **PasswordNeverExpires**: Must be 0 or 1 (BooleanYN)

---

## Entity: SYS.Container

The `SYS.Container` class provides methods for container lifecycle management.

### Key Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `QuiesceForBundling()` | %Status | Prepares IRIS for container image creation |
| `ChangePassword(file, predefinedOnly)` | %Status | Changes passwords from file |
| `ForcePasswordChange()` | %Status | Sets ChangePassword=1 for all users |
| `SetNeverExpires(username)` | %Status | Sets AccountNeverExpires=1 |
| `KillPassword(username)` | %Status | Removes password (disables password auth) |
| `SetMonitorStateOK()` | %Status | Clears severity 1&2 alerts |
| `PreventFailoverMessage()` | %Status | Clears ^SYS("NODE") |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ISC_PACKAGE_MGRUSER` | Manager user for container operations |
| `SYS_CONTAINER_QUIET` | Suppress error output |
| `SYS_CONTAINER_CONTINUE_ON_ERROR` | Don't terminate on error |
| `SYS_CONTAINER_LOCKEDDOWN` | Enable locked-down security |

---

## Entity: $SYSTEM.Monitor

Health monitoring for container readiness.

### State Values

| Value | State | Container Action |
|-------|-------|------------------|
| 0 | OK | Ready for connections |
| 1 | Warning | May have transient issues |
| 2 | Error | Connection issues likely |
| 3 | Fatal | Do not use container |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `$SYSTEM.Monitor.State()` | Integer | Current system monitor state (0-3) |
| `$SYSTEM.Monitor.SetState(val)` | void | Set monitor state |

---

## Entity: %SYSTEM.OBJ

Class/routine export and import management.

### Key Methods for Fixtures

| Method | Signature | Description |
|--------|-----------|-------------|
| `Export()` | `Export(items, filename, qspec, errorlog, Charset)` | Export items to XML file |
| `Import()` | `Import(path, qualifiers, selectedItems, errors, imported)` | Import from file/directory |
| `ExportPackage()` | `ExportPackage(package, filename, qspec, errorlog, Charset)` | Export entire package |

### Supported Formats

| Extension | Type | Import | Export |
|-----------|------|--------|--------|
| CLS | Classes | ✅ | ✅ |
| MAC | Macro routines | ✅ | ✅ |
| INT | Non-macro routines | ✅ | ✅ |
| INC | Include files | ✅ | ✅ |
| GBL | Globals | ✅ | ✅ |
| XML | XML format | ✅ | ✅ |
| UDL | UDL format | ✅ | ✅ |
| %RO | Routine output | ✅ | ❌ |
| %GOF | Global output | ✅ | ❌ |

---

## Relationships

```
Security.Users
    └── has many Roles (string list)
    └── has one Password (hashed)
    └── has one PasswordExternal (transient setter)

SYS.Container
    └── uses Security.Users for password operations
    └── uses $SYSTEM.Monitor for health state

%SYSTEM.OBJ
    └── exports/imports Classes, Routines, Globals
    └── supports multiple file formats
```

---
