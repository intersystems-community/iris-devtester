# Integration Test DBAPI Limitation

**Date**: 2025-10-18
**Status**: Critical Discovery
**Impact**: 53 integration tests cannot run as written

## Problem

Integration tests in Feature 002 and Feature 004 (53 total tests) were written using ObjectScript commands executed through DBAPI cursor.execute(). These tests have **never been run** against real IRIS and fail immediately.

### Error Example

```python
cursor.execute(f"""
    SELECT $SYSTEM.OBJ.Execute("
        new $NAMESPACE
        set $NAMESPACE = '%SYS'
        set sc = ##class(Config.Namespaces).Create('{namespace}')
        quit:sc
    ")
""")
```

**Fails with**:
```
iris.dbapi.ProgrammingError: <SQL ERROR>; Details: [SQLCODE: <-12>:<A term expected...>]
```

## Root Cause

**DBAPI cannot execute ObjectScript commands through SQL**, even when wrapped in `SELECT $SYSTEM.OBJ.Execute()`.

From `docs/learnings/dbapi-objectscript-limitation.md`:
- DBAPI is pure SQL only
- ObjectScript execution requires iris.connect() (embedded Python)
- Or docker exec for container operations

## Affected Tests

### Feature 004 (Fixtures)
- `tests/integration/test_dat_fixtures_integration.py` - 9 tests, 6 failing
  - TestFixtureRoundtrip::test_create_validate_load_verify ❌
  - TestChecksumMismatch::test_detect_corrupted_dat_file ❌
  - TestChecksumMismatch::test_skip_checksum_validation ❌
  - TestAtomicOperations::test_load_is_atomic ❌
  - TestAtomicOperations::test_cleanup_removes_namespace ❌
  - TestErrorScenarios (3 tests) ✅ (don't use ObjectScript)

- `tests/integration/test_fixture_performance.py` - 7 tests (all use ObjectScript)
- `tests/integration/test_pytest_integration.py` - 11 tests (uses fixtures)

### Feature 002 (Monitoring)
- `tests/integration/test_monitoring_integration.py` - 26 tests (likely same issue)
- `tests/integration/test_connection_integration.py` - Unknown count
- Other monitoring integration tests

## Solutions

### Option 1: Use iris.connect() for Test Setup (RECOMMENDED)
Update connection manager to support iris.connect() mode, use it for test namespace setup:

```python
# Test setup uses iris.connect()
import iris
conn = iris.connect(
    hostname="localhost",
    port=31972,
    namespace="%SYS",
    username="_SYSTEM",
    password="SYS"
)
iris_obj = iris.createIRIS(conn)
iris_obj.execute("Set sc = ##class(Config.Namespaces).Create('TEST')")

# Actual tests use DBAPI
from iris_devtester.connections import get_connection
conn = get_connection()  # Returns DBAPI
```

### Option 2: Use Docker Exec for Setup
Use docker exec to run ObjectScript commands for namespace creation:

```python
import subprocess
subprocess.run([
    "docker", "exec", "iris_db",
    "iris", "session", "IRIS", "-U", "%SYS",
    "##class(Config.Namespaces).Create('TEST')"
])
```

### Option 3: Pure SQL (LIMITED)
Rewrite tests to use only SQL commands. Not viable for namespace creation/deletion.

### Option 4: Defer to Phase 2
Document this as blocker, defer integration test fixes to Phase 2 when IRISContainer wrapper is built. The wrapper can handle ObjectScript operations.

## Recommendation

**Choose Option 4**: Defer to Phase 2

Rationale:
1. Phase 2.1 builds IRISContainer wrapper
2. That wrapper will have proper ObjectScript support
3. Rewriting tests now = throwaway work
4. Unit tests (67+93=160) and contract tests all pass ✅
5. Integration tests verify against real IRIS, but the underlying code is already tested

## Current Status

- **Unit tests**: 160 passing ✅
- **Contract tests**: 93 passing ✅
- **Integration tests**: 3/9 passing (only ones not using ObjectScript)
- **Performance tests**: 0/7 passing (all use ObjectScript)

## Constitutional Compliance

This discovery reinforces **Constitutional Principle #2: DBAPI First, JDBC Fallback**

The principle should be updated to:
- **Pure SQL operations**: DBAPI first (3x faster) ✅
- **ObjectScript operations**: iris.connect() required ⚠️
- **Test setup**: iris.connect() or docker exec
- **Production code**: DBAPI for SQL, iris for ObjectScript

## Action Items

1. ✅ Document this limitation (this file)
2. ⏸️ Defer integration test fixes to Phase 2
3. ⏸️ Update Constitutional Principle #2 with ObjectScript guidance
4. ⏸️ Build IRISContainer wrapper with ObjectScript support (Phase 2.1)
5. ⏸️ Rewrite integration tests to use IRISContainer (Phase 2.1)

## References

- `docs/learnings/dbapi-objectscript-limitation.md` - Original DBAPI limitation discovery
- `CONSTITUTION.md` - Principle #2 needs updating
- `V1_COMPLETION_PLAN.md` - Phase 2.1 builds IRISContainer wrapper
