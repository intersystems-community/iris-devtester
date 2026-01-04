# DAT RESTORE Database Isolation Problem

## Summary

IRIS DAT fixture RESTORE fails with `<DIRECTORY>Logon` error when trying to create isolated databases for auto-created containers, but works when using pre-created session containers pointing to the USER database.

## The Problem

When loading DAT fixtures in auto-created containers (`DATFixtureLoader(container=None)`), RESTORE completes successfully but connections fail with:

```
ObjectScript error: <DIRECTORY>Logon+58^%SYS.DBSRV.1 */usr/irissys/mgr/db_namespace/
```

## Root Cause

After extensive investigation, discovered that **IRIS rejects connections to custom database directories** regardless of location (`/tmp/` or `/usr/irissys/mgr/`). The RESTORE sequence executes successfully:

1. ✅ Create directory
2. ✅ Copy IRIS.DAT file
3. ✅ Create Config.Databases entry
4. ✅ Create namespace pointing to database
5. ✅ ObjectScript prints "SUCCESS"
6. ❌ Connection to namespace fails with `<DIRECTORY>Logon` error

## What Works vs What Fails

### Working Pattern (Existing Tests)
- Use session container (`iris_container` pytest fixture)
- Call `iris_container.get_test_namespace(prefix="TEST")`
- This creates namespace pointing to **USER database**
- Load fixture via `loader.load_fixture(container=iris_container)`
- **Result**: All 9/9 DAT fixture tests pass

### Failing Pattern (Auto-Created Containers)
- Create temporary container (`DATFixtureLoader(container=None)`)
- RESTORE tries to create isolated database in `/usr/irissys/mgr/db_namespace/`
- Copy IRIS.DAT, create Config.Databases, create namespace
- **Result**: RESTORE succeeds, connection fails

## Why Existing Tests Don't Catch This

The existing tests use `iris_container.get_test_namespace()` which creates namespaces pointing to the **shared USER database**. This means:

1. **No database isolation** - All test namespaces share one database
2. **Table name collisions possible** - Different fixtures could have same table names
3. **State pollution risk** - Data from one test can affect another

The tests pass because they never try to create custom databases - they just reuse USER.

## Attempted Solutions

### Tried #1: Use `/tmp/` directories ❌
```objectscript
Set dbDir = "/tmp/db_namespace"
```
**Result**: Same `<DIRECTORY>Logon` error

### Tried #2: Use `/usr/irissys/mgr/` directories ❌
```objectscript
Set dbDir = "/usr/irissys/mgr/db_namespace"
```
**Result**: Same `<DIRECTORY>Logon` error

### Tried #3: Create Config.Databases before mounting ❌
```objectscript
Set dbProps("Directory") = dbDir
Set status = ##class(Config.Databases).Create(dbName,.dbProps)
```
**Result**: RESTORE succeeds, connection still fails

### Tried #4: Remove MountDatabase call ✅ (partial)
```objectscript
// Don't call ##class(SYS.Database).MountDatabase(dbDir)
// Config.Databases.Create() handles activation
```
**Result**: RESTORE completes, but connection still fails

## Theory: IRIS Database Validation

The `<DIRECTORY>Logon` error suggests IRIS validates database directories during **connection/login**, not during RESTORE. Possible reasons:

1. **Database metadata mismatch** - Copied IRIS.DAT has wrong internal metadata
2. **Permissions issue** - IRIS.DAT needs specific ownership/permissions
3. **Database activation** - Directory needs additional activation step
4. **Resource limitation** - IRIS Community edition limits custom databases

## Impact on pytest Plugin

The `@pytest.mark.dat_fixture` decorator is **currently broken** for auto-created containers:

```python
@pytest.mark.dat_fixture("./fixtures/test-data")
def test_with_fixture(dat_fixture_connection):
    # This FAILS - auto-created container can't RESTORE
    cursor = dat_fixture_connection.cursor()
```

Tests fail with:
```
ERROR at setup of test_dat_fixture_namespace_fixture
Failed to load DAT fixture: table verification failed
```

## Workarounds

### Option A: Use Session Container (Current)
```python
# In conftest.py
@pytest.fixture(scope="session")
def iris_container():
    with IRISContainer.community() as container:
        yield container

# Tests share one container - no isolation
```
**Pros**: Works
**Cons**: No test isolation, state pollution

### Option B: Pre-create Namespaces
```python
# Don't use RESTORE at all
# Create namespace pointing to USER database
# Load data programmatically via SQL INSERT
```
**Pros**: Avoids RESTORE
**Cons**: Defeats purpose of DAT fixtures (10-100x slower)

### Option C: Fix IRIS Database Permissions (TBD)
```bash
# Inside container after RESTORE
chown irisowner:irisowner /usr/irissys/mgr/db_namespace/IRIS.DAT
chmod 660 /usr/irissys/mgr/db_namespace/IRIS.DAT
```
**Status**: Not yet tested

## Next Steps

1. **Document this blind alley** (Constitutional Principle #8) ✅ Done
2. **Test permissions fix** - Try Option C above
3. **Escalate to InterSystems** - May be Community edition limitation
4. **Redesign pytest plugin** - May need to abandon auto-container approach

## Files Involved

- `iris_devtester/fixtures/loader.py:246-279` - RESTORE implementation
- `iris_devtester/fixtures/pytest_plugin.py:68-77` - Auto-container creation
- `tests/integration/test_pytest_integration.py` - Failing tests
- `/tmp/test_auto_restore.py` - Minimal reproduction

## Constitutional Principles Violated

- **Principle #3: Isolation by Default** - Can't achieve isolation with RESTORE
- **Principle #4: Zero Configuration** - Auto-created containers don't work
- **Principle #7: Medical-Grade Reliability** - RESTORE is unreliable

## Date

2025-01-04

## Final Discovery (2025-01-04 continued)

After extensive debugging:

1. **Permissions fix failed** - `chown irisowner:irisowner` did NOT resolve the error
2. **ObjectScript syntax bugs** - Fixed `{{}}` brace escaping issues in f-strings
3. **Namespace reuse works** - When namespace exists, ObjectScript correctly skips database creation
4. **BUT: Tables not loaded!** - Pre-existing namespaces are empty; RESTORE doesn't load DAT data into them

### The Fundamental Conflict

**DAT fixtures assume complete database takeover:**
- RESTORE creates new database directory + namespace
- Loads entire database snapshot (IRIS.DAT) as a unit
- Cannot extract tables from DAT into existing namespace

**pytest plugin needs shared database:**
- `get_test_namespace()` creates namespaces pointing to USER database
- Enables test isolation by namespace, not by database
- Namespace is empty until tables are created

**These approaches are incompatible.**

### Solutions Forward

**Option A: Accept No Pytest Plugin** (Current)
- Document that `@pytest.mark.dat_fixture` doesn't work
- Users must manually call `loader.load_fixture()` in test code
- Skip the 3 failing pytest plugin tests

**Option B: Extract Tables from DAT** (Complex)
1. Mount DAT file to temporary namespace
2. Copy tables using SQL INSERT INTO ... SELECT FROM
3. Drop temporary namespace
4. Performance would be terrible (defeats DAT fixture purpose)

**Option C: Document Limitation** (Pragmatic)
- Pytest plugin works ONLY if users don't use `get_test_namespace()`
- Tests must let plugin create its own database directories
- Accept that IRIS will reject connections (known limitation)
- Document workaround: Use loader directly instead of plugin

## Status

**DOCUMENTED** - DAT fixtures and `get_test_namespace()` are architecturally incompatible. The pytest plugin cannot work reliably with the current RESTORE-based approach.
