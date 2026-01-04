# What's New in v1.4.0

**Release Date**: November 18, 2024
**PyPI**: https://pypi.org/project/iris-devtester/1.4.0/

## Overview

Version 1.4.0 introduces two major features that solve common pain points in multi-project IRIS development:

1. **Feature 013: Multi-Project Port Isolation** - Automatic port management for running multiple projects simultaneously
2. **Feature 014: Defensive Container Validation** - Progressive health checks with intelligent caching

Both features are **100% backwards compatible** - existing code continues to work unchanged.

## Feature 013: Multi-Project Port Isolation

### The Problem

When running multiple IRIS projects on the same machine, port conflicts are common:
- Default port 1972 can only be used by one container
- Manual port assignment is error-prone
- Developers waste time debugging "port already in use" errors
- CI/CD pipelines fail with random port conflicts

### The Solution

Automatic port assignment with project-aware persistence:

```python
from iris_devtester.containers import IRISContainer
from iris_devtester.ports import PortRegistry

# Create registry (one per project or shared)
registry = PortRegistry()

# Containers automatically get unique ports
with IRISContainer.community(port_registry=registry) as iris:
    port = iris.get_assigned_port()  # e.g., 1973, 1974, etc.
    print(f"Container running on port {port}")

    # Port persists across container restarts
    conn = iris.get_connection()
    # Connection automatically uses assigned port
```

### How It Works

1. **Port Range**: 1973-2022 (50 available ports)
2. **Project Isolation**: Each project path gets a consistent port
3. **Persistence**: Port assignments survive container restarts
4. **Cleanup**: Stale containers automatically detected and cleaned
5. **Manual Override**: Optional preferred port for specific needs

### Migration Guide

**Before v1.4.0** (still works):
```python
# Uses random Docker port mapping
with IRISContainer.community() as iris:
    conn = iris.get_connection()
```

**After v1.4.0** (recommended for multi-project):
```python
from iris_devtester.ports import PortRegistry

# Shared registry for all tests in project
registry = PortRegistry()

# Each test gets isolated port from project pool
with IRISContainer.community(port_registry=registry) as iris:
    conn = iris.get_connection()
```

**Pytest Integration**:
```python
# conftest.py
import pytest
from iris_devtester.ports import PortRegistry

@pytest.fixture(scope="session")
def port_registry():
    """Shared port registry for all tests."""
    return PortRegistry()

@pytest.fixture
def iris_container(port_registry):
    """IRIS container with automatic port assignment."""
    with IRISContainer.community(port_registry=port_registry) as iris:
        yield iris
```

### Advanced Usage

**Manual Port Preference**:
```python
# Request specific port (e.g., for debugging)
registry = PortRegistry()
with IRISContainer.community(
    port_registry=registry,
    preferred_port=1975
) as iris:
    print(f"Running on preferred port: {iris.get_assigned_port()}")
```

**Check Port Assignment**:
```python
registry = PortRegistry()
assignment = registry.get_assignment(project_path="/path/to/project")
if assignment:
    print(f"Project using port {assignment.port}")
else:
    print("No active port assignment")
```

**Cleanup Stale Assignments**:
```python
# Automatically happens on startup, but can be manual:
registry = PortRegistry()
cleaned = registry.cleanup_stale_assignments()
print(f"Cleaned {len(cleaned)} stale ports")
```

### Benefits

- ✅ **No more port conflicts** between projects
- ✅ **Consistent ports** per project (easier debugging)
- ✅ **CI/CD friendly** (parallel test execution)
- ✅ **Zero configuration** (works out of the box)
- ✅ **Backwards compatible** (opt-in feature)

---

## Feature 014: Defensive Container Validation

### The Problem

Container failures often go undetected until connection attempts:
- "Connection refused" errors are cryptic
- No visibility into why a container isn't healthy
- Manual debugging wastes developer time
- Tests fail with unclear root causes

### The Solution

Progressive health validation with structured error messages:

```python
from iris_devtester.containers import (
    validate_container,
    HealthCheckLevel,
    ContainerHealthStatus
)

# Quick validation (< 500ms)
result = validate_container(
    container_name="iris_db",
    level=HealthCheckLevel.MINIMAL
)

if not result.success:
    print(result.format_message())
    # Output:
    # ❌ Container Health Check Failed
    #
    # What went wrong:
    #   Container 'iris_db' is not running
    #
    # How to fix it:
    #   1. Start the container: docker start iris_db
    #   2. Check container logs: docker logs iris_db
```

### Validation Levels

Three levels with strict performance SLAs:

| Level | Checks | Performance Target | Use Case |
|-------|--------|-------------------|----------|
| **MINIMAL** | Exists + Running | < 500ms | Quick health checks |
| **STANDARD** | MINIMAL + Exec access | < 1000ms | Pre-connection validation |
| **FULL** | STANDARD + IRIS query | < 2000ms | Complete health verification |

### Health Statuses

Six health states with structured diagnostics:

```python
class ContainerHealthStatus:
    HEALTHY              # ✅ Container is fully operational
    RUNNING_NOT_ACCESSIBLE  # ⚠️ Running but exec/IRIS not responding
    NOT_RUNNING          # ❌ Container exists but stopped
    NOT_FOUND            # ❌ Container doesn't exist
    STALE_REFERENCE      # ⚠️ Container name changed (recreated)
    DOCKER_ERROR         # ❌ Docker daemon issue
```

### Usage Patterns

**Standalone Function** (stateless):
```python
from iris_devtester.containers import validate_container, HealthCheckLevel

# MINIMAL: Quick existence check
result = validate_container("iris_db", level=HealthCheckLevel.MINIMAL)
print(f"Healthy: {result.success}, Time: {result.validation_time:.2f}s")

# STANDARD: Check exec accessibility (default)
result = validate_container("iris_db")  # Uses STANDARD by default

# FULL: Complete IRIS health check
result = validate_container("iris_db", level=HealthCheckLevel.FULL)
```

**Stateful Validator** (with caching):
```python
from iris_devtester.containers import ContainerValidator

# Create validator with 5-second cache
validator = ContainerValidator("iris_db", cache_ttl=5)

# First call: Full validation
result = validator.validate()  # ~500ms

# Second call within 5s: Cached
result = validator.validate()  # <10ms (instant)

# Force refresh
result = validator.validate(force_refresh=True)

# Get detailed health metadata
health = validator.get_health()
print(f"Container ID: {health.container_id}")
print(f"Running: {health.is_running}")
print(f"Exec accessible: {health.exec_accessible}")
```

**IRISContainer Integration**:
```python
from iris_devtester.containers import IRISContainer, HealthCheckLevel

with IRISContainer.community() as iris:
    # Validate before critical operations
    result = iris.validate(level=HealthCheckLevel.STANDARD)
    if not result.success:
        print(result.format_message())
        return

    # Or assert (raises on failure)
    iris.assert_healthy()  # Raises if not healthy

    # Safe to connect
    conn = iris.get_connection()
```

### Migration Guide

**Before v1.4.0** (manual health checks):
```python
import docker

client = docker.from_env()
try:
    container = client.containers.get("iris_db")
    if container.status != "running":
        raise RuntimeError("Container not running")
except docker.errors.NotFound:
    raise RuntimeError("Container not found")
```

**After v1.4.0** (structured validation):
```python
from iris_devtester.containers import validate_container

result = validate_container("iris_db")
if not result.success:
    # Structured error message with remediation
    print(result.format_message())
    raise RuntimeError(result.message)
```

### Error Message Structure

All error messages follow Constitutional Principle #5 (Fail Fast with Guidance):

```
❌ Container Health Check Failed

What went wrong:
  [Clear description of the issue]

How to fix it:
  1. [First remediation step]
  2. [Second remediation step]
  3. [Third remediation step]
```

**Example - Container Not Found**:
```
❌ Container Health Check Failed

What went wrong:
  Container 'iris_db' not found

How to fix it:
  1. List all containers: docker ps -a
  2. Check container name matches
  3. Create container if missing
```

**Example - Container Not Running**:
```
❌ Container Health Check Failed

What went wrong:
  Container 'iris_db' exists but is not running (status: exited)

How to fix it:
  1. Start container: docker start iris_db
  2. Check logs for startup errors: docker logs iris_db
  3. Verify container health: docker inspect iris_db
```

### Performance Guarantees

All validation levels meet strict SLAs:

```python
import time
from iris_devtester.containers import validate_container, HealthCheckLevel

# MINIMAL: < 500ms
start = time.time()
result = validate_container("iris_db", level=HealthCheckLevel.MINIMAL)
assert time.time() - start < 0.5

# STANDARD: < 1000ms
start = time.time()
result = validate_container("iris_db", level=HealthCheckLevel.STANDARD)
assert time.time() - start < 1.0

# FULL: < 2000ms
start = time.time()
result = validate_container("iris_db", level=HealthCheckLevel.FULL)
assert time.time() - start < 2.0
```

### Benefits

- ✅ **Clear error messages** (no more cryptic failures)
- ✅ **Performance SLAs** (predictable validation time)
- ✅ **Intelligent caching** (5s TTL, minimal overhead)
- ✅ **Progressive validation** (fail fast when possible)
- ✅ **Type-safe API** (factory methods + dataclasses)

---

## Combined Usage Example

Using both features together for robust multi-project development:

```python
from iris_devtester.containers import IRISContainer, HealthCheckLevel
from iris_devtester.ports import PortRegistry

# Setup: Port registry for multi-project isolation
registry = PortRegistry()

# Create container with automatic port assignment
with IRISContainer.community(port_registry=registry) as iris:
    # Validate container health before connection
    result = iris.validate(level=HealthCheckLevel.STANDARD)

    if not result.success:
        print(f"Container validation failed:")
        print(result.format_message())
        raise RuntimeError("Container not healthy")

    # Safe to proceed
    port = iris.get_assigned_port()
    print(f"✓ Container healthy on port {port}")

    # Get connection (automatic remediation if needed)
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(f"✓ IRIS version: {cursor.fetchone()[0]}")
```

---

## Testing

Both features include comprehensive integration tests:

- **Feature 013**: 14 integration tests (84s runtime)
- **Feature 014**: 31 integration tests (5.6s runtime)
- **Total**: 126+ tests across entire package

Run tests:
```bash
# All tests
pytest

# Port isolation tests only
pytest tests/integration/ports/

# Container validation tests only
pytest tests/integration/test_container_validation.py
```

---

## Breaking Changes

**None.** v1.4.0 is 100% backwards compatible.

All new features are opt-in:
- Port isolation requires passing `port_registry` parameter
- Container validation is new API (doesn't affect existing code)

---

## Upgrade Instructions

```bash
# Upgrade to v1.4.0
pip install --upgrade iris-devtester

# Verify version
python -c "import iris_devtester; print(iris_devtester.__version__)"
# Output: 1.4.0
```

---

## Questions or Issues?

- **Documentation**: See `CLAUDE.md` for complete feature documentation
- **Issues**: https://github.com/intersystems-community/iris-devtester/issues
- **PyPI**: https://pypi.org/project/iris-devtester/1.4.0/

---

## Next Steps

1. **Upgrade** to v1.4.0
2. **Try** port isolation if running multiple projects
3. **Add** container validation for better error messages
4. **Report** any issues on GitHub

Happy coding with IRIS! 🎉
