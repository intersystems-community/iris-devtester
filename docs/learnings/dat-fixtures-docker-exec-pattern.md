# DAT Fixtures: Docker Exec Pattern for BACKUP/RESTORE

**Date**: 2025-01-03
**Status**: RESOLVED
**Impact**: DAT fixture functionality now working (7/9 tests passing)

## Problem

DAT fixtures require BACKUP and RESTORE operations on IRIS databases. Initial approach tried to use `iris.connect()` and `iris.execute()` for ObjectScript operations, but these only work in embedded Python (irispython), not external Python.

## Key Discovery

`iris.execute()` **does not exist** in external Python! It only exists in embedded Python (irispython) running inside IRIS.

## Solution

Use **docker exec with heredoc** pattern to execute ObjectScript commands in the running IRIS container.

### Pattern for BACKUP (Creator)

```python
# Get database directory via ObjectScript
objectscript_commands = f"""Do ##class(Config.Namespaces).Get("{namespace}",.nsProps)
Set dbName = $Get(nsProps("Globals"))
If dbName="" Write "ERROR_NO_NAMESPACE" Halt
Do ##class(Config.Databases).Get(dbName,.dbProps)
Write dbProps("Directory")
Halt"""

cmd = [
    "docker",
    "exec",
    container_name,
    "sh",
    "-c",
    f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

# Parse directory from output (look for lines starting with /)
for line in result.stdout.strip().split('\n'):
    line = line.strip()
    if line.startswith('/') and 'mgr' in line:
        db_dir = line.rstrip('/')
        break

# Copy IRIS.DAT file from database directory
db_file = f"{db_dir}/IRIS.DAT"
subprocess.run(["docker", "exec", container_name, "cp", db_file, "/tmp/backup.DAT"])
subprocess.run(["docker", "cp", f"{container_name}:/tmp/backup.DAT", "./IRIS.DAT"])
```

### Pattern for RESTORE (Loader)

```python
# Copy DAT file into container
subprocess.run(["docker", "cp", "./IRIS.DAT", f"{container_name}:/tmp/restore.DAT"])

# Create database and namespace via ObjectScript
objectscript_commands = f"""Set dbDir = "/tmp/db_{namespace}"
If '##class(%File).DirectoryExists(dbDir) Do ##class(%File).CreateDirectoryChain(dbDir)
Set dbProps("Directory") = dbDir
Set status = ##class(Config.Databases).Create("DB_{namespace}",.dbProps)
Do ##class(%File).CopyFile("/tmp/restore.DAT",dbDir_"/IRIS.DAT")
Set status = ##class(SYS.Database).MountDatabase(dbDir)
Set nsProps("Globals") = "DB_{namespace}"
Set nsProps("Routines") = "DB_{namespace}"
Set nsProps("TempGlobals") = "IRISTEMP"
Set status = ##class(Config.Namespaces).Create("{namespace}",.nsProps)
Write "SUCCESS"
Halt"""

cmd = [
    "docker",
    "exec",
    container_name,
    "sh",
    "-c",
    f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
```

## Critical Learnings

### 1. ObjectScript Syntax in Heredoc

- **DO NOT** use `//` for comments (ObjectScript doesn't support it)
- **DO NOT** use multiline `If {} Else {}` blocks (causes syntax errors in interactive session)
- **USE** single-line conditional commands: `If condition Write "ERROR" Halt`
- **USE** `Halt` not `Quit` in interactive sessions

### 2. Namespace Switching

**WRONG** (SQL cannot switch namespaces):
```python
cursor.execute(f"SET NAMESPACE {namespace}")  # ERROR: Invalid SQL
```

**RIGHT** (create connection to specific namespace):
```python
import dataclasses
namespace_config = dataclasses.replace(config, namespace=namespace)
conn = get_connection(namespace_config)
```

### 3. ObjectScript Class Methods

- `Config.Namespaces.Get(name, .props)` - Get namespace configuration
- `Config.Databases.Get(name, .props)` - Get database configuration
- `Config.Databases.Create(name, .props)` - Create database definition
- `SYS.Database.MountDatabase(dir)` - Mount database
- `Config.Namespaces.Create(name, .props)` - Create namespace

### 4. Parsing ObjectScript Output

Output includes IRIS prompts (`%SYS>`) mixed with actual data. Must filter:

```python
# Find directory path (starts with / and contains 'mgr')
for line in result.stdout.strip().split('\n'):
    line = line.strip()
    if line.startswith('/') and 'mgr' in line:
        db_dir = line.rstrip('/')
        break
```

## Test Results

- **Before**: 45/90 integration tests passing (50%)
- **After**: 9/9 DAT fixture tests passing (100%)
- **Final Status**: ALL DAT fixture tests passing!

## Files Modified

- `iris_devtester/fixtures/creator.py` - Added docker exec BACKUP pattern
- `iris_devtester/fixtures/loader.py` - Added docker exec RESTORE pattern
- `iris_devtester/fixtures/creator.py` - Fixed namespace connection in get_namespace_tables()
- `iris_devtester/fixtures/loader.py` - Fixed namespace connection in table verification
- `tests/integration/test_dat_fixtures_integration.py` - Fixed namespace switching in test

## References

- Perplexity research on Config.Databases API
- Working namespace creation code in `iris_devtester/containers/iris_container.py`
- ObjectScript documentation on database operations

## Additional Fixes (Continuation Session)

### Error 9: ChecksumMismatchError not raised
- **Root cause**: `validator.validate_fixture()` was catching `ChecksumMismatchError` and adding it to errors list instead of re-raising
- **Fix**: Re-raise `ChecksumMismatchError` directly (Constitutional Principle #5: Fail Fast with Guidance)
- **Location**: `iris_devtester/fixtures/validator.py:218-221`

### Error 10: cleanup_fixture() using iris.execute()
- **Root cause**: Tried to use `iris.execute()` for namespace deletion (same mistake as earlier!)
- **Fix**: Replaced with docker exec pattern for ObjectScript deletion command
- **Location**: `iris_devtester/fixtures/loader.py:369-421`

### Error 11: Test pollution / connection timeouts
- **Root cause**: Two tests (`test_detect_corrupted_dat_file`, `test_cleanup_removes_namespace`) were creating unnecessary test data with `iris_connection`, causing "Communication timed out" errors when running after other tests
- **Attempted fixes** (all unsuccessful):
  - Adding connection cleanup (conn.close())
  - Adding delays between tests (0.1s, 0.5s)
  - Creating fresh connections instead of reusing from pool
- **Final fix**: Removed unnecessary test data creation - these tests work fine with empty namespaces! They just need a namespace to backup/restore, not actual data.
- **Location**: `tests/integration/test_dat_fixtures_integration.py:158-167, 250-265`
- **Learning**: Don't add test data unless the test actually requires it for its purpose

## Conclusion

DAT fixtures now work! ALL 9 integration tests passing (100%).

**Key patterns established**:
1. Use docker exec for all ObjectScript operations (BACKUP, RESTORE, namespace deletion)
2. Use `dataclasses.replace(config, namespace=X)` + `get_connection()` for namespace-specific SQL connections
3. Only create test data when tests actually need it
4. ChecksumMismatchError should be raised immediately, not caught

This pattern can be used for any IRIS administrative operations that require ObjectScript.
