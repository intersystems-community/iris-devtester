# API Contract: reset_password()

**Feature**: 007-fix-reset-password
**Module**: `iris_devtester.utils.password_reset`
**Function**: `reset_password()`
**Date**: 2025-01-09

## Function Signature

```python
def reset_password(
    container_name: str = "iris_db",
    username: str = "_SYSTEM",
    new_password: str = "SYS",
    timeout: int = 30,
) -> Tuple[bool, str]:
```

## Contract Specification

### Preconditions

1. **Docker Available**:
   - Docker command must be in PATH
   - Docker daemon must be running
   - User must have docker execution permissions

2. **Container Running**:
   - Container with `container_name` must exist
   - Container must be in "running" state
   - IRIS must be fully started (not just container running)

3. **User Exists**:
   - `username` must be an existing IRIS user
   - Typically "_SYSTEM" (always exists)

4. **Password Valid**:
   - `new_password` must meet IRIS complexity requirements (validated by IRIS)
   - No explicit validation in our code (Constitutional Principle #4)

### Postconditions (CRITICAL - This is what the bug violates)

#### When `success = True`:

1. **Password MUST Be Set** (FR-001, FR-002, FR-003):
   - Security.Users.Get() was called
   - `prop("Password")` was set to `new_password`
   - Security.Users.Modify() was called
   - ✅ **Verification**: DBAPI connection with `new_password` succeeds

2. **PasswordNeverExpires MUST Be Set** (FR-004):
   - `prop("PasswordNeverExpires")` = 1
   - ✅ **Verification**: Query Security.Users returns PasswordNeverExpires=1

3. **Environment Updated**:
   - `os.environ["IRIS_PASSWORD"]` = `new_password`
   - `os.environ["IRIS_USERNAME"]` = `username`

4. **Idempotent** (FR-005):
   - Calling function multiple times with same password succeeds
   - No errors on re-running with same password

#### When `success = False`:

1. **Password NOT Changed**:
   - Original password still works
   - New password does NOT work

2. **Clear Error Message** (Constitutional Principle #5):
   - Message includes "What went wrong"
   - Message includes "How to fix it"
   - Message includes remediation steps

### Parameters

#### `container_name: str`
- **Type**: string
- **Default**: `"iris_db"`
- **Purpose**: Name of Docker container running IRIS
- **Validation**: None (Docker will error if not found)
- **Example**: `"iris-fhir"`, `"iris_container"`

#### `username: str`
- **Type**: string
- **Default**: `"_SYSTEM"`
- **Purpose**: IRIS username whose password to reset
- **Validation**: None (IRIS will error if user doesn't exist)
- **Example**: `"_SYSTEM"`, `"SuperUser"`, `"Admin"`

#### `new_password: str`
- **Type**: string
- **Default**: `"SYS"`
- **Purpose**: New password to set
- **Validation**: None (IRIS enforces complexity requirements)
- **Security**: Passed to Docker exec, handle with care
- **Example**: `"MyNewPassword123"`, `"ISCDEMO"`

#### `timeout: int`
- **Type**: integer (seconds)
- **Default**: `30`
- **Purpose**: Maximum time to wait for docker commands
- **Validation**: None (subprocess.run will timeout)
- **Example**: `30`, `60`, `120`

### Return Value

#### `Tuple[bool, str]`

**Success Case**:
```python
(True, "Password reset successful for user '_SYSTEM'")
```

**Failure Cases**:
```python
# Container not running
(False, "Container 'iris_db' not running\n...\n[remediation steps]")

# Timeout
(False, "Password reset timed out after 30 seconds\n...\n[remediation steps]")

# Docker not found
(False, "Docker command not found\n...\n[remediation steps]")

# Generic error
(False, "Password reset failed: {error}\n...\n[remediation steps]")
```

## Current Bug vs Fixed Behavior

### Current Broken Behavior

```python
success, msg = reset_password("iris_db", "_SYSTEM", "NEWPWD")
# Returns: (True, "Password reset successful for user '_SYSTEM'")

# BUT password NOT actually changed!
conn = dbapi.connect(password="NEWPWD")  # ❌ RuntimeError: Access Denied
conn = dbapi.connect(password="SYS")      # ✅ Still works with old password
```

**Root Cause**:
- Uses `ExternalPassword` property (wrong)
- Uses `ChangePassword=0` flag (wrong)
- Missing `Get()` call before `Modify()`
- Password not actually set in IRIS

### Fixed Behavior

```python
success, msg = reset_password("iris_db", "_SYSTEM", "NEWPWD")
# Returns: (True, "Password reset successful for user '_SYSTEM'")

# AND password IS changed!
conn = dbapi.connect(password="NEWPWD")  # ✅ Works with new password
conn = dbapi.connect(password="SYS")      # ❌ Fails with old password
```

**Implementation**:
- Uses `Password` property (correct)
- Uses `PasswordNeverExpires=1` flag (correct)
- Calls `Get()` before `Modify()` (correct)
- Password actually set in IRIS

## Integration Test Contract

### Test 1: Password Actually Set

**Contract**: If function returns success, password MUST be set

```python
def test_reset_password_actually_sets_password(iris_db):
    # Arrange
    container_name = iris_db.container.name

    # Act
    success, msg = reset_password(container_name, "_SYSTEM", "TESTPWD123")

    # Assert postconditions
    assert success, f"Function returned failure: {msg}"

    # CRITICAL: Verify password ACTUALLY changed
    conn = iris_db.get_connection(password="TESTPWD123")
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1, "Connection with new password failed"
```

### Test 2: Connection Succeeds

**Contract**: If function returns success, DBAPI connection MUST work

```python
def test_reset_password_connection_succeeds(iris_db):
    # Arrange
    container_name = iris_db.container.name

    # Act
    success, msg = reset_password(container_name, "_SYSTEM", "NEWPASS")

    # Assert postconditions
    assert success

    # Verify DBAPI connection works
    from intersystems_irispython import dbapi
    conn = dbapi.connect(
        hostname="localhost",
        port=iris_db.get_exposed_port(1972),
        namespace="USER",
        username="_SYSTEM",
        password="NEWPASS"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

### Test 3: PasswordNeverExpires Set

**Contract**: If function returns success, PasswordNeverExpires MUST = 1

```python
def test_reset_password_sets_password_never_expires(iris_db):
    # Arrange
    container_name = iris_db.container.name

    # Act
    success, msg = reset_password(container_name, "_SYSTEM", "PWD123")

    # Assert postconditions
    assert success

    # Verify PasswordNeverExpires=1
    # (Note: Cannot easily query via SQL, but can verify via ObjectScript)
    # Integration test will verify this via docker exec
```

### Test 4: Idempotent

**Contract**: Function MUST be idempotent (safe to call multiple times)

```python
def test_reset_password_idempotent(iris_db):
    # Arrange
    container_name = iris_db.container.name

    # Act - call 3 times with same password
    for i in range(3):
        success, msg = reset_password(container_name, "_SYSTEM", "SAMEPWD")

        # Assert each call succeeds
        assert success, f"Call {i+1} failed: {msg}"

    # Verify final password works
    conn = iris_db.get_connection(password="SAMEPWD")
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

## Backward Compatibility

### Function Signature (FR-006)
- ✅ NO CHANGES to function signature
- ✅ Same parameters, same return type
- ✅ Same defaults
- ✅ Existing callers work without modification

### Error Handling (FR-007)
- ✅ Same error message structure (Constitutional format)
- ✅ Same timeout behavior
- ✅ Same subprocess exception handling
- ✅ Same environment variable updates

### Platform Support (FR-008)
- ✅ Works on Linux, macOS, Windows
- ✅ Works with Community edition
- ✅ Works with Enterprise edition
- ✅ Same Docker exec pattern

## Performance

### Expected Performance

- **Success case**: < 10 seconds (no regression from current)
- **Timeout default**: 30 seconds (unchanged)
- **Container check**: < 1 second
- **Password reset**: 2-5 seconds (docker exec + IRIS processing)
- **Verification**: N/A (verification done by caller via connection test)

### Performance Impact of Fix

- **Additional overhead**: ~0.1 seconds for Get() call
- **Get() operation**: Fast (retrieves properties from memory)
- **Total impact**: Negligible (< 2% increase)
- **Benefit**: ACTUALLY WORKS (vs broken)

## Security Considerations

1. **Password in command line**:
   - Passed via docker exec (visible in process list briefly)
   - Same as current implementation (no regression)
   - Alternative (docker exec -i with stdin) more complex

2. **Environment variables**:
   - Password stored in `os.environ` (current behavior)
   - Accessible to process and child processes
   - Documented behavior (unchanged)

3. **Password validation**:
   - Let IRIS enforce complexity (Constitutional Principle #4)
   - No client-side password validation
   - IRIS will reject weak passwords

## Error Contract

All errors MUST follow Constitutional Principle #5 format:

```python
return (
    False,
    "Error summary\n"
    "\n"
    "What went wrong:\n"
    "  Detailed explanation\n"
    "\n"
    "How to fix it:\n"
    "  1. Step one\n"
    "  2. Step two\n"
    "\n"
    "[Optional: Alternative approach]\n"
)
```

## Change Summary

### BEFORE (Lines 120-121):
```python
f'''echo "set props(\\\"ChangePassword\\\")=0 set props(\\\"ExternalPassword\\\")=\\\"{new_password}\\\" write ##class(Security.Users).Modify(\\\"{username}\\\",.props)" | iris session IRIS -U %SYS'''
```

### AFTER (Fixed):
```python
f'''echo "set sc = ##class(Security.Users).Get(\\\"{username}\\\",.props) set props(\\\"Password\\\")=\\\"{new_password}\\\" set props(\\\"PasswordNeverExpires\\\")=1 write ##class(Security.Users).Modify(\\\"{username}\\\",.props)" | iris session IRIS -U %SYS'''
```

**Changes**:
1. ✅ Added `Get()` call before property modification
2. ✅ Changed `ExternalPassword` → `Password`
3. ✅ Changed `ChangePassword=0` → `PasswordNeverExpires=1`

---

**Contract Status**: ✅ DEFINED
**Test Coverage**: 4 integration tests planned
**Backward Compatible**: YES
**Ready for Implementation**: YES
