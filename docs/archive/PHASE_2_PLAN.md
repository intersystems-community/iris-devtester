# Phase 2: Complete Missing Features - Detailed Plan

**Status**: Ready to Start
**Last Updated**: 2025-10-18
**Dependencies**: Phase 1 complete ✅

---

## Phase 2 Overview

Phase 2 focuses on completing the infrastructure needed to run integration tests and prepare for v1.0.0 release.

**Key Blockers Solved**:
- ✅ SQL vs ObjectScript execution patterns documented
- ✅ Constitutional Principle #2 updated with correct guidance
- ✅ Working examples created

**Remaining Work**:
1. Add iris.connect() support to IRISContainer wrapper
2. Update integration tests to use correct patterns
3. Complete testing utilities
4. Run all tests with real IRIS

---

## Phase 2.1: Add ObjectScript Support to IRISContainer

### Current Status

**Exists** (`iris_devtester/containers/iris_container.py`):
- ✅ Community/Enterprise factory methods
- ✅ DBAPI connection via `get_connection()`
- ✅ CallIn service enablement
- ✅ Password reset integration
- ✅ Wait strategies
- ✅ Container lifecycle management

**Missing**:
- ❌ `get_iris_connection()` - Returns iris.connect() for ObjectScript
- ❌ `execute_objectscript()` - Helper for ObjectScript execution
- ❌ `create_namespace()` - Namespace creation helper
- ❌ `delete_namespace()` - Namespace deletion helper
- ❌ Integration test helpers using these methods

### Implementation Tasks

#### Task 1: Add iris.connect() Support

**File**: `iris_devtester/containers/iris_container.py`

**New Method**: `get_iris_connection()`

```python
def get_iris_connection(self) -> Any:
    """
    Get iris.connect() connection for ObjectScript operations.

    Use this for:
    - Creating/deleting namespaces
    - Task Manager operations
    - Global variable operations
    - Full ObjectScript execution

    Use get_connection() for SQL operations (3x faster).

    Returns:
        iris connection object (embedded Python)

    Example:
        >>> with IRISContainer.community() as container:
        ...     iris_conn = container.get_iris_connection()
        ...     iris_obj = iris.createIRIS(iris_conn)
        ...     iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
    """
    import iris

    config = self.get_config()

    conn = iris.connect(
        hostname=config.host,
        port=config.port,
        namespace=config.namespace,
        username=config.username,
        password=config.password
    )

    return conn
```

**Estimated**: 1 hour

---

#### Task 2: Add ObjectScript Helper Methods

**New Methods**:

```python
def execute_objectscript(self, code: str, namespace: str = None) -> str:
    """
    Execute ObjectScript code and return result.

    Args:
        code: ObjectScript code to execute
        namespace: Optional namespace (default: container's namespace)

    Returns:
        Result from ObjectScript (whatever was Written)

    Example:
        >>> result = container.execute_objectscript('Write "Hello, IRIS!"')
        >>> print(result)  # "Hello, IRIS!"
    """
    import iris

    ns = namespace or self._config.namespace
    conn = iris.connect(
        hostname=self._config.host,
        port=self._config.port,
        namespace=ns,
        username=self._config.username,
        password=self._config.password
    )

    iris_obj = iris.createIRIS(conn)
    result = iris_obj.execute(code)
    conn.close()

    return result


def create_namespace(self, namespace: str) -> bool:
    """
    Create IRIS namespace.

    Args:
        namespace: Name of namespace to create

    Returns:
        True if successful

    Example:
        >>> container.create_namespace("TEST")
    """
    import iris

    conn = iris.connect(
        hostname=self._config.host,
        port=self._config.port,
        namespace="%SYS",
        username=self._config.username,
        password=self._config.password
    )

    iris_obj = iris.createIRIS(conn)
    result = iris_obj.classMethodValue("Config.Namespaces", "Create", namespace)
    conn.close()

    return result == 1


def delete_namespace(self, namespace: str) -> bool:
    """
    Delete IRIS namespace.

    Args:
        namespace: Name of namespace to delete

    Returns:
        True if successful

    Example:
        >>> container.delete_namespace("TEST")
    """
    import iris

    conn = iris.connect(
        hostname=self._config.host,
        port=self._config.port,
        namespace="%SYS",
        username=self._config.username,
        password=self._config.password
    )

    iris_obj = iris.createIRIS(conn)
    result = iris_obj.classMethodValue("Config.Namespaces", "Delete", namespace)
    conn.close()

    return result == 1
```

**Estimated**: 2 hours

---

#### Task 3: Add pytest Fixture Helper

**New Method**:

```python
def get_test_namespace(self, prefix: str = "TEST") -> str:
    """
    Create unique test namespace and return connection.

    Use this in pytest fixtures for isolated testing.

    Args:
        prefix: Namespace prefix (default: "TEST")

    Returns:
        Namespace name (caller must delete when done)

    Example:
        >>> @pytest.fixture
        ... def test_db(iris_container):
        ...     namespace = iris_container.get_test_namespace()
        ...     yield namespace
        ...     iris_container.delete_namespace(namespace)
    """
    import uuid

    namespace = f"{prefix}_{uuid.uuid4().hex[:8].upper()}"
    self.create_namespace(namespace)
    return namespace
```

**Estimated**: 30 minutes

---

#### Task 4: Update Tests

**Files to Update**:
- `tests/integration/test_dat_fixtures_integration.py` - Use create_namespace()
- `tests/integration/test_fixture_performance.py` - Use create_namespace()
- `tests/integration/test_monitoring_integration.py` - Use create_namespace()
- `tests/integration/test_pytest_integration.py` - Update for new patterns

**Pattern to Apply**:

```python
# OLD (broken)
cursor.execute("DO ##class(Config.Namespaces).Create('TEST')")

# NEW (works)
iris_container.create_namespace("TEST")
# or
iris_conn = iris_container.get_iris_connection()
iris_obj = iris.createIRIS(iris_conn)
iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
```

**Estimated**: 4 hours (53 tests to review/update)

---

### Total Phase 2.1 Estimate: 7.5 hours

---

## Phase 2.2: Complete Testing Utilities

### Current Status

**Files Exist**:
- `iris_devtester/testing/__init__.py`
- `iris_devtester/testing/fixtures.py`

**Missing**:
- Complete pytest fixture implementations
- Schema reset utilities
- Test isolation helpers

### Implementation Tasks

#### Task 1: Complete `iris_test_fixture()`

**File**: `iris_devtester/testing/fixtures.py`

```python
import pytest
from iris_devtester.containers import IRISContainer


@pytest.fixture(scope="function")
def iris_test_fixture():
    """
    Pytest fixture for IRIS testing with isolated namespace.

    Provides:
    - IRIS container (community edition)
    - Unique test namespace
    - DBAPI connection for SQL
    - iris.connect() connection for ObjectScript
    - Automatic cleanup

    Usage:
        >>> def test_my_feature(iris_test_fixture):
        ...     db_conn, iris_conn, namespace = iris_test_fixture
        ...     cursor = db_conn.cursor()
        ...     cursor.execute("CREATE TABLE TestData (...)")
    """
    with IRISContainer.community() as container:
        # Create unique namespace
        namespace = container.get_test_namespace()

        # Get both connection types
        db_conn = container.get_connection()  # DBAPI for SQL
        iris_conn = container.get_iris_connection()  # ObjectScript

        yield (db_conn, iris_conn, namespace)

        # Cleanup
        container.delete_namespace(namespace)
```

**Estimated**: 2 hours

---

#### Task 2: Add Schema Reset Utilities

**File**: `iris_devtester/testing/schema_reset.py`

```python
def reset_namespace(connection, namespace: str):
    """
    Reset namespace to clean state.

    Drops all tables in namespace for test isolation.
    """
    import iris

    iris_obj = iris.createIRIS(connection)

    # Get all tables
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """)

    tables = cursor.fetchall()

    # Drop each table
    for schema, table in tables:
        cursor.execute(f"DROP TABLE {schema}.{table}")

    cursor.close()
```

**Estimated**: 2 hours

---

#### Task 3: Add Test Isolation Helpers

**File**: `iris_devtester/testing/isolation.py`

```python
import uuid


def generate_test_id(prefix: str = "TEST") -> str:
    """Generate unique test identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def cleanup_test_data(connection, test_id: str):
    """
    Cleanup test data by test_id.

    Useful when tests share a namespace but need cleanup.
    """
    cursor = connection.cursor()

    # Find all tables
    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """)

    tables = cursor.fetchall()

    # Delete test data from each table (if it has test_id column)
    for (table,) in tables:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE test_id = ?", (test_id,))
        except:
            pass  # Table may not have test_id column

    cursor.close()
```

**Estimated**: 1 hour

---

### Total Phase 2.2 Estimate: 5 hours

---

## Phase 2.3: Run All Tests

### Task: Execute Integration Tests with Real IRIS

**What to Run**:
```bash
# Feature 002 monitoring tests (26 tests)
pytest tests/integration/test_monitoring_integration.py -v

# Feature 004 fixture tests (27 tests)
pytest tests/integration/test_dat_fixtures_integration.py -v
pytest tests/integration/test_fixture_performance.py -v
pytest tests/integration/test_pytest_integration.py -v

# Connection tests
pytest tests/integration/test_connection_integration.py -v

# All integration tests
pytest tests/integration/ -v
```

**Expected Results**:
- Feature 002: 26/26 passing ✅
- Feature 004: 27/27 passing ✅
- **Total**: 53/53 passing ✅

**Estimated**: 2 hours (includes fixing any failures)

---

## Phase 2 Total Estimate: 14.5 hours

**Breakdown**:
- Phase 2.1: IRISContainer ObjectScript support: 7.5 hours
- Phase 2.2: Testing utilities: 5 hours
- Phase 2.3: Run all tests: 2 hours

---

## Success Criteria

### Phase 2.1 Complete When:
- ✅ `get_iris_connection()` method implemented
- ✅ `execute_objectscript()` method implemented
- ✅ `create_namespace()` method implemented
- ✅ `delete_namespace()` method implemented
- ✅ `get_test_namespace()` method implemented
- ✅ All 5 methods have docstrings with examples
- ✅ Integration tests updated to use new methods
- ✅ No more ObjectScript via DBAPI cursor.execute()

### Phase 2.2 Complete When:
- ✅ `iris_test_fixture()` pytest fixture works
- ✅ Schema reset utilities implemented
- ✅ Test isolation helpers implemented
- ✅ Documentation for all utilities

### Phase 2.3 Complete When:
- ✅ 53/53 integration tests passing
- ✅ All features (002-004) validated against real IRIS
- ✅ No test failures or skips

---

## Next Steps After Phase 2

Once Phase 2 is complete:
1. **Phase 3**: Package preparation (pyproject.toml fixes, documentation)
2. **Phase 4**: PyPI release (v1.0.0)

---

## References

- `docs/SQL_VS_OBJECTSCRIPT.md` - Complete execution guide
- `docs/examples/sql_vs_objectscript_examples.py` - Working examples
- `CONSTITUTION.md` Principle #2 - Choose the right tool
- `V1_COMPLETION_PLAN.md` - Overall release plan
