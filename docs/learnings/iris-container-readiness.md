# IRIS Container Readiness: Health Check Patterns

**Source**: Analysis of IRIS source code at `/databases/sys/cls/SYS/Container.xml`
**Feature**: 017-iris-source-insights
**Date**: 2025-12-18

---

## Overview

This document captures official IRIS container health check patterns derived from analyzing the `SYS.Container` class - the same class InterSystems uses for their official Docker image builds.

**Key Discovery**: Container health checks should use `$SYSTEM.Monitor.State()` to detect readiness. A return value of 0 indicates the container is healthy and ready for connections.

---

## System Monitor State

### $SYSTEM.Monitor.State() Values

The `$SYSTEM.Monitor.State()` method returns the overall health status of the IRIS instance:

| Value | State | Meaning | Container Action |
|-------|-------|---------|------------------|
| -1 | N/A | Monitoring not configured | Treat as healthy (container is running) |
| 0 | OK | System is healthy | Ready for connections |
| 1 | Warning | Minor issues detected | May work, log warning |
| 2 | Error | Significant problems | Likely connection failures |
| 3 | Fatal | Critical failure | Do not use container |

**Note**: Community Edition containers often return `-1` because system monitoring is not configured. This should be treated as healthy since the container is running and accepting connections.

### Usage Pattern

```objectscript
// Check container health using System Monitor state
Set state = $SYSTEM.Monitor.State()

If state = 0 {
    Write "Container is healthy (OK)", !
} ElseIf state = 1 {
    Write "Container has warnings - may have transient issues", !
} ElseIf state = 2 {
    Write "Container has errors - connections may fail", !
} ElseIf state = 3 {
    Write "Container is in fatal state - do not use", !
}
```

### Why This Matters

From the source code (SYS.Container.xml lines 271-289):
> "Container healthchecks are based on the System Monitor state. If this failover message is not suppressed, a new container may spend its first several minutes with the System Monitor in a 'warn' state, which will cause container healthchecks to fail."

This explains why containers can appear "ready" (SuperServer port open) but still fail connections - the System Monitor hasn't reached OK state yet.

---

## Container Quiesce Patterns

### Official Quiesce Sequence

InterSystems uses this sequence when preparing IRIS for Docker image builds (from `QuiesceForBundling()` method):

```objectscript
// 1. Prevent hostname mismatch warnings on new containers
Do ..PreventFailoverMessage()  // Clears ^SYS("NODE")

// 2. Force password change for all users (security best practice)
Do ..ForcePasswordChange()     // Sets ChangePassword=1 for all

// 3. Prevent journal rollover warnings
Do ..PreventJournalRolloverMessage()  // Clears ^%SYS("JOURNAL")

// 4. Remove password for manager user (optional)
Do ..KillPassword(mgruser)     // Enables passwordless login

// 5. Set accounts to never expire (for predefined users)
Do ..SetNeverExpires(username)  // AccountNeverExpires=1

// 6. Enable OS authentication (for automation)
Do ..EnableOSAuthentication()

// 7. Clear system monitor alerts
Do ..SetMonitorStateOK()       // Clears severity 1&2 alerts
```

### SetMonitorStateOK Pattern

This method clears alerts that would cause health checks to fail:

```objectscript
// Clear severity 1 and 2 alerts to allow health checks to pass
Do $SYSTEM.Monitor.SetState(0)  // Set to OK state
```

---

## Password Change on Startup

### ForcePasswordChange Behavior

When a fresh IRIS container starts, the `ForcePasswordChange()` method may have set `ChangePassword=1` for all users. This causes:

1. First connection attempt receives "Password change required"
2. DBAPI clients don't implement password-change handshake
3. Connection fails with "Access Denied"

### How iris-devtester Handles This

From CHANGELOG v1.4.4-v1.5.0, the solution is to:
1. Use `docker exec` to run ObjectScript
2. Set `ChangePassword=0` for the target user
3. Also set for SuperUser (if different from target)

```objectscript
// Pattern from SYS.Container.ForcePasswordChange()
Set tResultSet = ##class(Security.Users).ListFunc()
While tResultSet.%Next() {
    Set tName = tResultSet.%Get("Name")
    Set tExists = ##class(Security.Users).Exists(tName,.tUser,.tSC)
    If $$$ISOK(tSC) && tExists {
        Set tUser.ChangePassword = 1  // This is what causes issues!
        Set tSC = tUser.%Save()
    }
}
```

### Undoing ForcePasswordChange

```objectscript
// Clear password change requirement for all users
Do ##class(Security.Users).UnExpireUserPasswords("*")

// Or for specific user
If ##class(Security.Users).Exists(username, .user, .status) {
    Set user.ChangePassword = 0
    Set user.PasswordNeverExpires = 1
    Set user.AccountNeverExpires = 1
    Do user.%Save()
}
```

---

## Community vs Enterprise

### Edition Detection

```objectscript
// Check IRIS edition
Set edition = $SYSTEM.Version.GetProduct()
// Returns: "IRIS Community" or "IRIS for Health" or similar
```

### Key Differences

| Feature | Community | Enterprise |
|---------|-----------|------------|
| Docker Image | `intersystemsdc/iris-community` | `containers.intersystems.com/intersystems/iris` |
| License Required | No | Yes |
| Default Users | _SYSTEM, SuperUser, Admin, CSPSystem | Same + additional |
| Password Policy | Standard | May be stricter |
| Security Mode | Minimal | May be locked down |
| Health Check | Same | Same |

### Enterprise Container Notes

Enterprise containers may have additional security restrictions:
- Stricter password policies
- More restrictive default roles
- Additional audit logging
- May require license key volume mount

```python
# Enterprise container example
container = IRISContainer(
    image="containers.intersystems.com/intersystems/iris:2024.1",
    license_key="/path/to/iris.key"
)
```

---

## Python Health Check Example

### Basic Health Check

```python
def check_container_health(container) -> tuple[bool, str]:
    """Check IRIS container health using official API.

    Returns:
        (is_healthy, message) tuple
    """
    objectscript = '''
        Write $SYSTEM.Monitor.State()
        Halt
    '''

    result = container.exec_run(
        ['iris', 'session', 'IRIS', '-U', '%SYS'],
        stdin=True,
        input=objectscript.encode()
    )

    if result.exit_code != 0:
        return False, f"Failed to execute health check: {result.output.decode()}"

    try:
        state = int(result.output.decode().strip())
    except ValueError:
        return False, f"Invalid state response: {result.output.decode()}"

    states = {
        0: (True, "OK - Container healthy"),
        1: (True, "Warning - Container has minor issues"),
        2: (False, "Error - Container has problems"),
        3: (False, "Fatal - Container unusable"),
    }

    return states.get(state, (False, f"Unknown state: {state}"))
```

### Wait for Readiness

```python
import time

def wait_for_container_ready(container, timeout: int = 60) -> bool:
    """Wait for container to reach healthy state.

    Args:
        container: Docker container object
        timeout: Maximum seconds to wait

    Returns:
        True if container became ready, False if timeout
    """
    start = time.time()

    while time.time() - start < timeout:
        is_healthy, message = check_container_health(container)

        if is_healthy:
            return True

        # Wait before retry
        time.sleep(2)

    return False
```

### Combined Readiness Check

```python
def ensure_container_ready(container, username: str, password: str) -> bool:
    """Ensure container is ready for connections.

    1. Wait for Monitor.State() = 0
    2. Clear password change requirements
    3. Verify connection works

    Returns:
        True if container is ready
    """
    # Step 1: Wait for system health
    if not wait_for_container_ready(container, timeout=60):
        return False

    # Step 2: Clear password requirements
    clear_password_script = f'''
        If ##class(Security.Users).Exists("{username}", .user, .sc) {{
            Set user.ChangePassword = 0
            Set user.PasswordNeverExpires = 1
            Set user.AccountNeverExpires = 1
            Do user.%Save()
        }}
        Halt
    '''

    container.exec_run(
        ['iris', 'session', 'IRIS', '-U', '%SYS'],
        stdin=True,
        input=clear_password_script.encode()
    )

    # Step 3: Verify connection
    try:
        import iris
        conn = iris.connect(
            hostname=container.get_host(),
            port=container.get_exposed_port(1972),
            namespace="USER",
            username=username,
            password=password
        )
        conn.close()
        return True
    except Exception:
        return False
```

---

## Troubleshooting

### Common Issues

#### 1. "Password change required" Error

**Symptom**:
```
[SQLCODE: <-853>:<User xxx is required to change password before login>]
```

**Cause**: Container's `ForcePasswordChange()` set `ChangePassword=1`

**Fix**: Clear the flag before connecting:
```python
container.exec_run(['iris', 'session', 'IRIS', '-U', '%SYS'],
    stdin=True,
    input=b'Do ##class(Security.Users).UnExpireUserPasswords("*") Halt')
```

#### 2. Connection Refused Despite Port Open

**Symptom**: Port 1972 responds to TCP but connection fails

**Cause**: IRIS SuperServer is up but system not fully initialized

**Fix**: Wait for `$SYSTEM.Monitor.State()` = 0

#### 3. Intermittent Connection Failures

**Symptom**: Connections work sometimes, fail other times

**Cause**: System Monitor in Warning state (1) due to startup alerts

**Fix**: Clear alerts with `$SYSTEM.Monitor.SetState(0)`

#### 4. Container Exits Immediately

**Symptom**: Container starts then stops within seconds

**Cause**: Usually ISC_DATA_DIRECTORY pointing to non-existent path

**Fix**: Don't set ISC_DATA_DIRECTORY for Community edition - IRIS bootstraps automatically

### Diagnostic Commands

```bash
# Check container logs for startup issues
docker logs <container_id> 2>&1 | grep -i error

# Interactive session to debug
docker exec -it <container_id> iris session IRIS -U%SYS

# Check system state
docker exec <container_id> iris session IRIS -U%SYS "Write \$SYSTEM.Monitor.State() Halt"

# List users and their status
docker exec <container_id> iris session IRIS -U%SYS "Do ##class(Security.Users).List()"
```

---

## Cross-References

### Related Learning Documents

- [iris-security-users-api.md](iris-security-users-api.md) - Password management patterns
- [callin-service-requirement.md](callin-service-requirement.md) - CallIn service for DBAPI
- [testcontainers-ryuk-lifecycle.md](testcontainers-ryuk-lifecycle.md) - Container cleanup

### Source Files Analyzed

- `/databases/sys/cls/SYS/Container.xml` - Container management class
- `/databases/sys/cls/Security/Users.xml` - User management class

---

## Summary

| Check | Pattern |
|-------|---------|
| System health | `$SYSTEM.Monitor.State()` returns 0 |
| Clear password flags | `##class(Security.Users).UnExpireUserPasswords("*")` |
| Set user ready | `user.ChangePassword=0, user.PasswordNeverExpires=1` |
| Wait for ready | Poll Monitor.State() until 0, with timeout |

**Remember**: A container with SuperServer port open is NOT necessarily ready - check `$SYSTEM.Monitor.State()` for true readiness.
