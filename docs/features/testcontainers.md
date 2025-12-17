# Testcontainers Integration

Isolated IRIS instances for testing with automatic lifecycle management.

## Overview

Testcontainers integration provides:
- Each test suite gets its own isolated IRIS instance
- Automatic container cleanup (even on crashes)
- No port conflicts - dynamic port allocation
- No test data pollution
- Works with both Community and Enterprise editions

## Quick Start

### Zero-Config Usage

```python
from iris_devtester.containers import IRISContainer

# That's it! No configuration needed.
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(cursor.fetchone())
```

### pytest Integration

```python
# conftest.py
from iris_devtester.testing import iris_test_fixture
import pytest

@pytest.fixture(scope="module")
def iris_db():
    return iris_test_fixture()

# test_example.py
def test_my_feature(iris_db):
    conn, state = iris_db
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

Run tests:
```bash
pytest  # Just works!
```

## Enterprise Edition

For Enterprise features (mirrors, sharding, etc.):

```python
from iris_devtester.containers import IRISContainer

# Auto-discovers license from ~/.iris/iris.key
with IRISContainer.enterprise(namespace="PRODUCTION") as iris:
    conn = iris.get_connection()
    # Use your enterprise IRIS instance
```

### License Discovery Order

1. Explicit `license_key` parameter
2. `IRIS_LICENSE_KEY` environment variable
3. `~/.iris/iris.key`
4. `./iris.key` in project root
5. Auto-discovered from Docker volume mounts

### Explicit License Path

```python
with IRISContainer.enterprise(
    license_key="/path/to/iris.key",
    image="containers.intersystems.com/intersystems/iris:latest"
) as iris:
    # Test mirrors, sharding, etc.
```

## Test Isolation

### Fixture Scopes

```python
# Module scope: Fast, shared state acceptable
@pytest.fixture(scope="module")
def iris_db_fast():
    """One container for all tests in module."""
    # Use when: Tests are read-only or properly isolated
    with IRISContainer.community() as iris:
        yield iris

# Function scope: Slower, maximum isolation
@pytest.fixture(scope="function")
def iris_db_isolated():
    """New container for each test."""
    # Use when: Tests modify schema or require clean state
    with IRISContainer.community() as iris:
        yield iris
```

### Namespace Isolation

```python
@pytest.fixture
def test_namespace(iris_container):
    """Function-scoped namespace with auto-cleanup."""
    ns = iris_container.get_test_namespace(prefix="TEST")
    yield ns
    iris_container.delete_namespace(ns)
```

## Performance

Benchmarks on MacBook Pro M1:

| Operation | Time |
|-----------|------|
| Container startup | ~5 seconds |
| DBAPI connection | ~80ms |
| JDBC connection | ~250ms |
| Schema reset | <5 seconds |
| Test isolation overhead | <100ms per test class |

### Performance Tips

1. **Use module scope**: Share containers across tests when safe
2. **Prefer DBAPI**: 3x faster than JDBC connections
3. **Reuse namespaces**: Reset data instead of recreating
4. **Parallel tests**: Each test class gets its own container

## Connection Types

### DBAPI (Recommended)

```python
# 3x faster than JDBC
conn = iris.get_connection()  # Returns DBAPI connection
cursor = conn.cursor()
cursor.execute("SELECT * FROM MyTable")
```

### JDBC (Fallback)

```python
# Automatic fallback if DBAPI unavailable
# Requires: pip install iris-devtester[jdbc]
conn = iris.get_connection(prefer_jdbc=True)
```

### ObjectScript Connection

```python
# For namespace operations, Task Manager, globals
iris_obj = iris.get_iris_connection()
iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
```

## Best Practices

1. **Use module scope by default**: Faster test runs
2. **Isolate via namespaces**: Cheaper than new containers
3. **Clean up on fixture teardown**: Prevent data pollution
4. **Use schema reset utilities**: Fast cleanup between tests
5. **Test both editions**: Verify Community and Enterprise work

## Troubleshooting

### Container won't start
- Check Docker is running: `docker info`
- Pull image manually: `docker pull intersystemsdc/iris-community:latest`
- Check available disk space

### Connection timeout
- Increase timeout: `IRISContainer.community(timeout=120)`
- Check container logs: `docker logs <container_id>`
- Verify port is accessible

### Password change required
- Handled automatically by iris-devtester
- Transparent retry on password reset

## See Also

- [Docker-Compose Integration](docker-compose.md) - For existing containers
- [DAT Fixtures](dat-fixtures.md) - Fast test data loading
- [examples/](../../examples/) - Runnable examples
