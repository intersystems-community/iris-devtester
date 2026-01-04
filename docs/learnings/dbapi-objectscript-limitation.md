# DBAPI Cannot Execute ObjectScript

**Status**: BLOCKING ISSUE
**Discovered**: 2025-01-05
**Impact**: Feature 002 integration tests blocked
**Priority**: HIGH - Must be resolved in Feature 003

---

## Problem Summary

Feature 002 (Set Default Stats) implementation assumes we can execute ObjectScript from external Python using DBAPI connections. **This is incorrect** - DBAPI is SQL-only and cannot execute ObjectScript.

### What Doesn't Work

```python
# THIS FAILS - DBAPI cursors only accept SQL
cursor = conn.cursor()
objectscript = """
    set policy = ##class(%SYS.PTools.StatsSQL).%New()
    set policy.Name = "test"
    do policy.%Save()
"""
cursor.execute(objectscript)  # ❌ ProgrammingError: Invalid SQL statement
```

### Why This Happened

When Feature 002 was written, we were designing the API but hadn't yet integrated with real IRIS containers. The code was written assuming Object Script execution would "just work" through DBAPI connections.

**Reality**:
- DBAPI (intersystems-irispython) provides SQL interface only
- ObjectScript execution requires either:
  1. Embedded Python (running INSIDE IRIS)
  2. JDBC stored procedure calls
  3. Container exec() to run ObjectScript commands

---

## Impact

### Affected Functions

All Feature 002 functions that try to execute ObjectScript:

1. **`configure_monitoring()`** - Tries to create monitoring policy via ObjectScript
   - Lines 500-535 in `monitoring.py`
   - Calls `policy.to_objectscript()` and tries `cursor.execute()`

2. **`create_task()`** - Tries to create Task Manager task via ObjectScript
   - Lines 721-764 in `monitoring.py`
   - Calls `schedule.to_objectscript()` and tries `cursor.execute()`

3. **`get_monitoring_status()`** - Partially fixed
   - Lines 585-624 in `monitoring.py`
   - Now uses SQL directly (✅ WORKING)

4. **Other Task Manager functions** - All have same issue
   - `get_task_status()`
   - `suspend_task()`
   - `resume_task()`
   - `delete_task()`
   - All try to execute ObjectScript via cursor

### Test Status

**Integration tests BLOCKED**: All 30+ Feature 002 integration tests fail because they require ObjectScript execution.

---

## Solutions

### Option 1: JDBC Connection (RECOMMENDED for Feature 003)

JDBC supports stored procedure calls which can execute ObjectScript:

```python
import jaydebeapi

conn = jaydebeapi.connect(
    "com.intersystems.jdbc.IRISDriver",
    f"jdbc:IRIS://{host}:{port}/{namespace}",
    [username, password],
    driver_path
)

# Can execute ObjectScript via stored procedures
cursor.execute("CALL %SYS.PTools.StatsSQL_CreatePolicy(?)", [policy_name])
```

**Pros**:
- Can execute ObjectScript
- Works from external Python
- Industry standard

**Cons**:
- Requires JDBC driver download
- Slower than DBAPI (3x)
- Needs Java

### Option 2: Hybrid Approach (BEST for iris-devtester)

Use both DBAPI and JDBC as needed:

```python
def configure_monitoring(conn, policy):
    # For SQL queries: use DBAPI (fast)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM %SYS_PTools.StatsProfile")

    # For ObjectScript: use JDBC or container exec
    if hasattr(conn, 'execute_objectscript'):
        conn.execute_objectscript(policy.to_objectscript())
    else:
        # Fallback to container exec or raise helpful error
        raise NotImplementedError(
            "ObjectScript execution requires JDBC connection or container access"
        )
```

**Pros**:
- Best of both worlds
- Fast for SQL, capable for ObjectScript
- Follows Constitutional Principle #2 (DBAPI First, JDBC Fallback)

**Cons**:
- More complex
- Requires both connection types

### Option 3: Pure SQL Rewrite (FALLBACK)

Rewrite all monitoring logic to use only SQL:

```python
# Instead of ObjectScript policy creation:
cursor.execute("""
    INSERT INTO %SYS_PTools.StatsProfile (Name, Description, Interval)
    VALUES (?, ?, ?)
""", [policy.name, policy.description, policy.interval_seconds])
```

**Pros**:
- Works with DBAPI
- Simpler connection management

**Cons**:
- Not all IRIS features accessible via SQL
- Task Manager may not have SQL interface
- Loses power of ObjectScript

---

## Recommended Fix for Feature 003

Implement **Option 2 (Hybrid Approach)**:

1. **Primary connection**: DBAPI for SQL (fast)
2. **Secondary capability**: JDBC for ObjectScript when needed
3. **Connection abstraction**: Hide implementation from users

```python
class IRISConnection:
    def __init__(self, config):
        # Try DBAPI first
        self.dbapi_conn = create_dbapi_connection(config)

        # Create JDBC connection for ObjectScript
        self.jdbc_conn = create_jdbc_connection(config)

    def execute_sql(self, query):
        """Fast SQL via DBAPI."""
        return self.dbapi_conn.cursor().execute(query)

    def execute_objectscript(self, code):
        """ObjectScript via JDBC stored procedure."""
        return self.jdbc_conn.execute_objectscript(code)
```

Users get:
- ✅ Fast SQL queries (DBAPI)
- ✅ Full ObjectScript power (JDBC)
- ✅ Don't need to know which is being used

---

## Workaround for NOW (Unblock Integration Tests)

Until Feature 003 is implemented, we have two options:

### Workaround A: Skip Integration Tests (CURRENT)

Mark integration tests as skipped with clear message:

```python
@pytest.mark.skip(reason="Blocked on Feature 003: DBAPI cannot execute ObjectScript")
def test_configure_monitoring(iris_db):
    ...
```

**Status**: This is what we have now

### Workaround B: Test Fixture Helper (BETTER)

Create a test-only helper that uses container exec:

```python
# In tests/conftest.py
@pytest.fixture
def iris_container_conn(iris_container):
    """Connection with ObjectScript execution via container."""
    conn = get_dbapi_connection(iris_container)

    # Add helper method
    def execute_objectscript(code):
        result = iris_container.exec(
            f"iris session IRIS -U USER '{code}'"
        )
        return result

    conn.execute_objectscript = execute_objectscript
    yield conn
```

**Status**: Could implement this if we want tests running NOW

---

## Timeline

### Immediate (Today)
- [x] Document this limitation
- [ ] Update Feature 002 STATUS.md with blocking issue
- [ ] Create GitHub issue for Feature 003 tracking

### Feature 003 (Next 1-2 weeks)
- [ ] Implement hybrid DBAPI/JDBC connection manager
- [ ] Add `execute_objectscript()` method to connections
- [ ] Update Feature 002 to use new connection API
- [ ] Run Feature 002 integration tests

### Long Term
- [ ] Consider pure SQL implementations where possible
- [ ] Document which features require ObjectScript
- [ ] Provide clear errors when ObjectScript needed but unavailable

---

## Lessons Learned

1. **Test with real connections early** - Don't assume APIs work as expected
2. **DBAPI is SQL-only** - Critical limitation to understand
3. **ObjectScript requires special handling** - Can't be executed like SQL
4. **Hybrid approach is powerful** - DBAPI for speed, JDBC for capability
5. **Constitutional Principle #2 validated** - "DBAPI First, JDBC Fallback" is the right approach

---

## References

- Feature 002 Implementation: `iris_devtester/containers/monitoring.py`
- Integration Tests: `tests/integration/test_monitoring_integration.py`
- DBAPI Documentation: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT
- JDBC Documentation: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BJAVA

---

**Next Action**: Implement Feature 003 (Connection Manager) with hybrid DBAPI/JDBC support to unblock Feature 002 integration tests.
