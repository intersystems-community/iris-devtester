# Contract: Testing Fixtures API

**Feature**: 001-implement-iris-devtester
**Module**: `iris_devtester.testing`
**Date**: 2025-10-05

## Overview

This contract defines pytest fixtures and testing utilities for IRIS database testing, including schema validation, test isolation, and automatic cleanup.

## pytest Fixtures

### iris_db (function-scoped)

**Signature**:
```python
@pytest.fixture(scope="function")
def iris_db() -> Generator[Connection, None, None]:
    """Function-scoped IRIS connection with automatic cleanup"""
```

**Purpose**: Provide isolated IRIS connection for each test with automatic cleanup

**Yields**: Connection object (DBAPI or JDBC)

**Behavior**:
1. Create new IRIS container or unique namespace
2. Establish connection
3. Yield connection to test
4. Automatically clean up (close connection, drop namespace/stop container)
5. Guaranteed cleanup even if test fails

**Scope**: Function (new instance per test)

**Performance**: ~30s per test (container startup), ~5s per test (namespace only)

**Requirements**: FR-009, FR-011, FR-013, FR-030

**Example**:
```python
def test_user_creation(iris_db):
    cursor = iris_db.cursor()
    cursor.execute("INSERT INTO users (username) VALUES ('alice')")
    iris_db.commit()
    # Automatic cleanup after test
```

---

### iris_db_shared (module-scoped)

**Signature**:
```python
@pytest.fixture(scope="module")
def iris_db_shared() -> Generator[Connection, None, None]:
    """Module-scoped IRIS connection shared across tests"""
```

**Purpose**: Provide shared IRIS connection for all tests in module (performance optimization)

**Yields**: Connection object (DBAPI or JDBC)

**Behavior**:
1. Create IRIS container once for entire module
2. Yield connection to all tests in module
3. Clean up after last test in module

**Scope**: Module (shared across all tests in file)

**Performance**: ~30s once per module (amortized ~5s per test if 6+ tests)

**Requirements**: FR-009, FR-030

**Use When**:
- Tests are read-only
- Tests use unique namespaces/tables
- Performance is critical

**Example**:
```python
def test_read_users(iris_db_shared):
    cursor = iris_db_shared.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    assert count >= 0

def test_read_products(iris_db_shared):
    # Shares same container as test_read_users
    cursor = iris_db_shared.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
```

---

### iris_container (function-scoped)

**Signature**:
```python
@pytest.fixture(scope="function")
def iris_container() -> Generator[IRISContainer, None, None]:
    """Function-scoped IRIS container with lifecycle management"""
```

**Purpose**: Provide direct access to IRIS container for advanced use cases

**Yields**: IRISContainer instance

**Behavior**:
1. Start IRIS container
2. Wait for ready (health checks)
3. Yield container to test
4. Stop and remove container after test

**Scope**: Function

**Requirements**: FR-019, FR-020, FR-021, FR-023

**Example**:
```python
def test_container_ports(iris_container):
    assert iris_container.get_exposed_port(1972) is not None
    conn = iris_container.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $NAMESPACE")
```

---

## Public Functions

### validate_schema()

**Signature**:
```python
def validate_schema(
    conn: Connection,
    expected: SchemaDefinition,
    *,
    auto_reset: bool = False,
    cache: bool = True
) -> SchemaValidationResult
```

**Purpose**: Validate database schema matches expected definition

**Parameters**:
- `conn` (Connection): Database connection to validate
- `expected` (SchemaDefinition): Expected schema definition
- `auto_reset` (bool): Automatically reset schema if mismatch (default: False)
- `cache` (bool): Cache validation result (default: True)

**Returns**: SchemaValidationResult with validation outcome

**Raises**:
- `SchemaValidationError`: If validation fails and auto_reset=False

**Behavior**:
1. Query database for actual schema (tables, columns, indexes)
2. Compare actual vs expected
3. If mismatch and auto_reset=True, call reset_schema()
4. If cache=True, cache result for container instance
5. Return validation result

**Performance**: ~500ms uncached, ~1ms cached

**Requirements**: FR-014, FR-016, FR-018

**Example**:
```python
schema = SchemaDefinition(
    tables={
        "users": TableDefinition(
            name="users",
            columns={
                "id": ColumnDefinition(name="id", type="INTEGER"),
                "username": ColumnDefinition(name="username", type="VARCHAR", max_length=50)
            }
        )
    }
)

result = validate_schema(conn, schema)
if not result.is_valid:
    print(f"Mismatches: {len(result.mismatches)}")
    for mismatch in result.mismatches:
        print(f"  {mismatch.message}")
```

---

### reset_schema()

**Signature**:
```python
def reset_schema(
    conn: Connection,
    definition: SchemaDefinition,
    *,
    drop_existing: bool = True,
    clear_cache: bool = True
) -> None
```

**Purpose**: Reset database schema to match definition

**Parameters**:
- `conn` (Connection): Database connection
- `definition` (SchemaDefinition): Schema definition to apply
- `drop_existing` (bool): Drop existing tables first (default: True)
- `clear_cache` (bool): Clear validation cache (default: True)

**Returns**: None

**Raises**:
- `SchemaResetError`: If reset fails

**Behavior**:
1. If drop_existing=True, drop all existing tables
2. Create tables from definition
3. Create indexes from definition
4. If clear_cache=True, clear validation cache
5. Log reset actions

**Performance**: ~1s for typical schema (5-10 tables)

**Requirements**: FR-015

**Example**:
```python
schema = SchemaDefinition(tables={...})
reset_schema(conn, schema)
# Database now matches schema definition
```

---

### register_cleanup()

**Signature**:
```python
def register_cleanup(
    test_id: str,
    action: CleanupAction
) -> None
```

**Purpose**: Register cleanup action to perform after test

**Parameters**:
- `test_id` (str): Unique test identifier
- `action` (CleanupAction): Cleanup action to perform

**Returns**: None

**Behavior**:
1. Add action to cleanup registry
2. Sort by priority (higher priority executes first)
3. Actions executed in pytest teardown phase

**Requirements**: FR-011, FR-012

**Example**:
```python
def test_with_temp_table(iris_db):
    cursor = iris_db.cursor()
    cursor.execute("CREATE TABLE temp_data (id INTEGER)")

    # Register cleanup
    register_cleanup(
        test_id=pytest.current_test_id,
        action=CleanupAction(
            action_type="drop_table",
            target="temp_data",
            priority=10
        )
    )
    # Table will be dropped after test
```

---

## Pytest Markers

**Provided markers**:
```python
@pytest.mark.iris  # Requires IRIS database
@pytest.mark.slow  # Slow test (container startup)
@pytest.mark.isolation_required  # Requires function-scoped isolation
@pytest.mark.enterprise_only  # Requires Enterprise edition
```

**Configuration in pytest.ini**:
```ini
[pytest]
markers =
    iris: Tests requiring IRIS database
    slow: Slow tests (may be skipped with -m "not slow")
    isolation_required: Tests requiring function-scoped isolation
    enterprise_only: Tests requiring IRIS Enterprise edition
```

**Usage**:
```python
@pytest.mark.slow
def test_large_data_import(iris_db):
    # Skipped with: pytest -m "not slow"
    ...

@pytest.mark.enterprise_only
def test_mirror_failover(iris_db):
    # Skipped if Community edition
    ...
```

---

## Configuration via conftest.py

**Example conftest.py**:
```python
import pytest
from iris_devtester.testing import *

# Enable all fixtures
pytest_plugins = ["iris_devtester.testing.fixtures"]

def pytest_configure(config):
    """Configure iris-devtester for pytest"""
    config.addinivalue_line("markers", "iris: Tests requiring IRIS database")
    config.addinivalue_line("markers", "slow: Slow tests (container startup)")
```

**Auto-discovery**: If `iris_devtester` installed, fixtures automatically available

---

## Test Isolation Strategies

### Strategy 1: Container per Test (Maximum Isolation)
```python
# conftest.py
@pytest.fixture(scope="function")
def iris_db():
    # Uses iris_db fixture (container isolation)
    ...
```

**Pros**: Maximum isolation, no test pollution
**Cons**: Slow (~30s per test)
**Use when**: Tests modify schema, concurrent tests, critical tests

### Strategy 2: Namespace per Test (Fast Isolation)
```python
# conftest.py
@pytest.fixture(scope="function")
def iris_db():
    # Same container, unique namespace per test
    ...
```

**Pros**: Fast (~5s per test), good isolation
**Cons**: Shared container, namespace cleanup required
**Use when**: Tests modify data but not schema

### Strategy 3: Shared Container (Fastest)
```python
# conftest.py
@pytest.fixture(scope="module")
def iris_db_shared():
    # One container for entire module
    ...
```

**Pros**: Very fast (~5s amortized), efficient
**Cons**: Test pollution risk, manual cleanup needed
**Use when**: Read-only tests, manual cleanup, performance critical

---

## Schema Validation Patterns

### Pattern 1: Validate Once per Module
```python
# conftest.py
@pytest.fixture(scope="module", autouse=True)
def validate_schema_once(iris_db_shared):
    schema = SchemaDefinition(...)
    validate_schema(iris_db_shared, schema, auto_reset=True)
```

**Use when**: Module tests all use same schema

### Pattern 2: Validate per Test
```python
@pytest.fixture(scope="function")
def validated_db(iris_db):
    schema = SchemaDefinition(...)
    validate_schema(iris_db, schema, auto_reset=True, cache=True)
    return iris_db
```

**Use when**: Tests need different schemas

### Pattern 3: Manual Validation
```python
def test_with_custom_schema(iris_db):
    schema = SchemaDefinition(...)
    result = validate_schema(iris_db, schema)
    assert result.is_valid, result.get_summary()
```

**Use when**: Need fine-grained control

---

## Error Messages

**SchemaValidationError Example**:
```
Schema validation failed: 3 mismatch(es)

Mismatches found:
  1. [missing_table] Expected table 'users' not found
  2. [type_mismatch] Column 'products.price': expected INTEGER, found VARCHAR
  3. [missing_column] Table 'orders' missing column 'created_at'

How to fix:
  1. Review schema definition
  2. Run reset_schema() to apply definition:
     from iris_devtester.testing import reset_schema
     reset_schema(conn, schema_definition)
  3. Or enable auto_reset:
     validate_schema(conn, schema, auto_reset=True)

Documentation: https://iris-devtester.readthedocs.io/testing/schema-validation
```

---

## Performance Targets

| Operation | Target | Cache Hit |
|-----------|--------|-----------|
| Schema validation | <500ms | <1ms |
| Schema reset | <1s | N/A |
| Container startup | <30s | N/A |
| Namespace creation | <5s | N/A |
| Cleanup | <10s | N/A |

---

## Contract Tests

**Location**: `tests/contract/test_testing_fixtures_api.py`

**Test Cases**:
1. `test_iris_db_fixture_isolation()` - Each test gets isolated environment
2. `test_iris_db_shared_fixture()` - Shared fixture works
3. `test_iris_container_fixture()` - Container fixture provides access
4. `test_validate_schema_success()` - Schema validation passes
5. `test_validate_schema_failure()` - Schema validation detects mismatches
6. `test_validate_schema_auto_reset()` - Auto-reset works
7. `test_validate_schema_caching()` - Caching improves performance
8. `test_reset_schema()` - Schema reset works
9. `test_register_cleanup()` - Cleanup registration works
10. `test_cleanup_executes_priority_order()` - Cleanup order correct

---

**Contract Version**: 1.0.0
**Last Updated**: 2025-10-05
**Status**: Ready for implementation
