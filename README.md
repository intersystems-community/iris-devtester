# IRIS DevTools

**Battle-tested InterSystems IRIS infrastructure utilities for Python development**

[![PyPI version](https://badge.fury.io/py/iris-devtester.svg)](https://badge.fury.io/py/iris-devtester)
[![Python Versions](https://img.shields.io/pypi/pyversions/iris-devtester.svg)](https://pypi.org/project/iris-devtester/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/intersystems-community/iris-devtools)

## What is This?

IRIS DevTools is a comprehensive Python package that provides **automatic, reliable, production-tested** infrastructure for InterSystems IRIS development. Born from years of production experience and hundreds of hours debugging IRIS + Docker + Python integration issues, this library codifies all the hard-won lessons into a reusable package.

## The Problem It Solves

Ever experienced these?
- ❌ "Password change required" errors breaking your tests
- ❌ Port conflicts when running tests in parallel
- ❌ Tests polluting each other's data
- ❌ "Works on my machine" but fails in CI
- ❌ Spending hours debugging IRIS connection issues
- ❌ Copying infrastructure code between projects

**IRIS DevTools fixes all of these automatically.**

## Quick Start Guide

### For Absolute Beginners

**Step 1: Install Docker**
```bash
# macOS: Install Docker Desktop
# Download from https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker ps  # Should show empty list, not an error
```

**Step 2: Install iris-devtester**
```bash
# Recommended: Install with all features
pip install iris-devtester[all]

# This includes:
# - testcontainers (container management)
# - DBAPI support (3x faster connections)
# - All optional features
```

**Step 3: Write Your First Test**
```python
# test_example.py
from iris_devtester.containers import IRISContainer

def test_basic_connection():
    """Your first IRIS test - that's all you need!"""
    with IRISContainer.community() as iris:
        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS result")
        assert cursor.fetchone()[0] == 1
```

**Step 4: Run It**
```bash
pytest test_example.py -v

# First run takes ~30 seconds (downloads IRIS image)
# Subsequent runs take ~5-10 seconds
```

**That's it!** You now have a fully isolated IRIS database for testing.

---

### Platform-Specific Notes

#### 🍎 macOS Users (IMPORTANT)

**Startup Time**: On macOS with Docker Desktop, IRIS containers need **10-15 seconds** for full initialization. This is normal - Docker Desktop runs in a VM which adds overhead.

**What You'll See**:
```
Starting IRIS container...
Waiting for IRIS to be ready...  # Takes 10-15s on macOS
✓ IRIS ready
Hardening user accounts...        # Another 8-10s on macOS
✓ Password verified
```

**Why It's Slower**: macOS Docker Desktop runs containers in a VM, which adds latency to:
- Security metadata propagation (~8-10s)
- Volume mounts
- Network initialization

**Tip**: For development, use `iris-devtester container up` to start a persistent container once, then attach to it:
```python
# Start once (takes 30s)
# $ iris-devtester container up

# Then attach in your code (instant)
from iris_devtester.containers import IRISContainer
iris = IRISContainer.attach("iris_container")
conn = iris.get_connection()
```

#### 🐧 Linux Users

**Faster Startup**: Native Docker on Linux is **2-3x faster** than macOS Docker Desktop. Expect:
- Container startup: 3-5 seconds
- Password verification: <2 seconds

**Permissions**: Add your user to the `docker` group to avoid `sudo`:
```bash
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

#### 🪟 Windows Users

**Use WSL2**: For best performance, install Docker Desktop with WSL2 backend.

**Performance**: Similar to macOS (10-15s startup due to VM overhead).

---

### Common Issues & Quick Fixes

#### ❌ "Password verification failed" (macOS only)

**Symptom**: You see warnings like:
```
⚠️ Password verification failed after 3 attempts
```

**Is This a Problem?** Usually **NO**! As of v1.4.7, this is just a warning during startup. If your tests pass and your code works, ignore it.

**Why It Happens**: macOS Docker Desktop needs 10-15s for security metadata to propagate. The verification runs before that completes.

**Fix**: Already fixed in v1.4.7+ (increased settle delay). Just update:
```bash
pip install --upgrade iris-devtester
```

#### ❌ "Container already exists" or Port Conflicts

**Symptom**:
```
Error: Container name already in use
Error: Bind for 0.0.0.0:1972 failed: port is already allocated
```

**Fix**:
```bash
# Remove old containers
docker ps -a | grep iris | awk '{print $1}' | xargs docker rm -f

# Or clean everything
docker system prune -a
```

#### ❌ DBAPI Connections Fail (IRIS-specific)

**Symptom**:
```
ERROR: Access Denied
ERROR: CallIn service not available
```

**Root Cause**: IRIS requires the CallIn service to be enabled for DBAPI connections.

**Fix**: `get_connection()` automatically enables CallIn for you. But if you're using custom code:
```python
# This is automatic in IRISContainer.get_connection()
iris.enable_callin_service()  # Required for DBAPI!
conn = get_dbapi_connection(config)
```

**Fallback**: The library automatically falls back to JDBC (slower but doesn't need CallIn).

#### ❌ Tests Polluting Each Other

**Symptom**: Test A passes alone, but fails when run with Test B.

**Fix**: Use isolated containers per test class:
```python
import pytest
from iris_devtester.containers import IRISContainer

@pytest.fixture(scope="function")  # New container per test
def iris_db():
    with IRISContainer.community() as iris:
        yield iris.get_connection()
    # Automatic cleanup

def test_a(iris_db):
    # Isolated from test_b
    pass

def test_b(iris_db):
    # Gets its own fresh container
    pass
```

#### ❌ Slow Tests (Container Startup Overhead)

**Symptom**: Each test takes 10-15 seconds.

**Fix**: Use `scope="module"` or `scope="session"` to share containers:
```python
@pytest.fixture(scope="module")  # One container per test file
def iris_db():
    with IRISContainer.community() as iris:
        yield iris.get_connection()
```

**Trade-off**: Faster tests, but tests can pollute each other. Use unique namespaces for isolation:
```python
@pytest.fixture
def test_namespace(iris_container):
    """Each test gets unique namespace in shared container."""
    namespace = iris_container.get_test_namespace(prefix="TEST")
    yield namespace
    iris_container.delete_namespace(namespace)  # Cleanup
```

---

### Best Practices (Production-Proven)

#### ✅ Use Context Managers

```python
# ✅ GOOD - Automatic cleanup
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # Use connection
# Container automatically stopped and removed

# ❌ BAD - Manual cleanup required
iris = IRISContainer.community()
iris.start()
conn = iris.get_connection()
# Forgot to cleanup - container still running!
```

#### ✅ Let the Library Handle Password Reset

```python
# ✅ GOOD - Automatic password management
conn = iris.get_connection()  # Handles password reset automatically

# ❌ BAD - Manual password reset
reset_password(container_name, username, password)
conn = get_dbapi_connection(config)
```

#### ✅ Use DBAPI for SQL, iris.connect() for ObjectScript

```python
# ✅ GOOD - 3x faster for SQL
conn = iris.get_connection()  # DBAPI
cursor = conn.cursor()
cursor.execute("SELECT * FROM MyTable")  # Fast!

# ✅ GOOD - Required for ObjectScript
iris_conn = iris.get_iris_connection()  # iris.connect()
iris_obj = iris.createIRIS(iris_conn)
iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")

# ❌ BAD - Using iris.connect() for SQL
iris_conn = iris.get_iris_connection()
cursor = iris_conn.cursor()  # Slower!
```

#### ✅ Use Fixtures for Test Data (10-100x Faster)

```python
# ✅ GOOD - Load 10K rows in <10 seconds
from iris_devtester.fixtures import DATFixtureLoader
loader = DATFixtureLoader(container=iris)
result = loader.load_fixture("./fixtures/test-data-10k")

# ❌ BAD - Programmatic insert takes 50+ minutes
for i in range(10000):
    cursor.execute("INSERT INTO MyTable VALUES (?, ?)", (i, f"Name {i}"))
```

#### ✅ Check Container Health Before Long Operations

```python
# ✅ GOOD - Defensive validation
with IRISContainer.community() as iris:
    # Validate before expensive operations
    result = iris.validate()
    if not result.success:
        raise RuntimeError(result.format_message())

    # Now safe to proceed with long-running task
    run_benchmark(iris)
```

---

### Quick Installation Reference

```bash
# Minimal (JDBC only, slower)
pip install iris-devtester

# Recommended (DBAPI + JDBC)
pip install iris-devtester[dbapi]

# All features (recommended for new projects)
pip install iris-devtester[all]

# Development (includes test tools)
pip install iris-devtester[dev,test,all]
```

**What's Included**:
- `[dbapi]`: intersystems-irispython (3x faster connections)
- `[jdbc]`: jaydebeapi, JPype1 (fallback connector)
- `[all]`: Both DBAPI and JDBC
- `[test]`: pytest, pytest-cov, pytest-asyncio
- `[dev]`: black, isort, mypy, flake8

---

### Zero-Config Usage Examples

#### Example 1: Simple Script

```python
from iris_devtester.containers import IRISContainer

# That's it! No configuration needed.
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(cursor.fetchone())
```

#### Example 2: Pytest Integration

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
pytest  # Just works! 🎉
```

#### Example 3: Docker-Compose (Existing Container)

```python
# Use existing container (no testcontainers overhead)
from iris_devtester.containers import IRISContainer

iris = IRISContainer.attach("iris_db")  # Your docker-compose service
conn = iris.get_connection()
# Use connection
```

## Key Features

### 🔐 Automatic Password Management
- Detects "Password change required" errors
- Automatically resets passwords using official IRIS API
- Uses correct ObjectScript implementation (Get/Modify pattern)
- Connection verification with exponential backoff retry
- **Performance**: <100ms typical verification
- **Success Rate**: 99.5%+ on all platforms (macOS, Linux)
- Transparent retry - your code never knows it happened

### 🐳 Testcontainers Integration
- Each test suite gets isolated IRIS instance
- Automatic cleanup (even on crashes)
- No port conflicts
- No test data pollution

### 🐋 Container Lifecycle Management (NEW in v1.2.2)
- Complete CLI for IRIS container management (`container up`, `start`, `stop`, `remove`)
- Zero-config defaults work out of the box
- Persistent containers for long-running tests (benchmark infrastructure)
- Volume mounting support with read-only mode
- Automatic health checks and CallIn enablement
- Works with both Community and Enterprise editions

### 🐋 Docker-Compose Support
- Attach to existing IRIS containers without lifecycle management
- Works with licensed IRIS via docker-compose
- CLI commands for quick operations (status, enable-callin, test-connection)
- Standalone utilities for shell scripts and automation
- Auto-discovery of container ports

### ⚡ DBAPI-First Performance
- Automatically uses fastest connection method
- DBAPI (Database API): 3x faster than JDBC (Java Database Connectivity)
- Falls back to JDBC if DBAPI unavailable
- All transparent to your code

### 📦 DAT Fixture Management
- Create reproducible test fixtures from IRIS tables
- 10-100x faster than programmatic data creation
- SHA256 checksum validation for data integrity
- Load 10K rows in <10 seconds
- CLI commands for create, load, validate

### 📊 Performance Monitoring
- Auto-configure ^SystemPerformance monitoring
- Task Manager integration for scheduled monitoring
- Resource-aware auto-disable under high load
- Automatic re-enable when resources recover
- Zero-config monitoring setup

### 🧪 Production-Ready Testing
- Schema validation & auto-reset
- Test data isolation
- Pre-flight checks
- Medical-grade reliability (94%+ coverage)

### 📦 Zero Configuration
- Sensible defaults
- Auto-discovery of IRIS instances
- Environment variable overrides
- Works with both Community & Enterprise editions

## Example: Container Lifecycle Management (NEW in v1.2.2)

Manage IRIS containers like docker-compose, but with zero configuration:

```bash
# Start IRIS container (zero-config, uses Community edition)
iris-devtester container up

# Container persists - perfect for development or benchmarks
# Access at http://localhost:52773/csp/sys/UtilHome.csp

# Check status
iris-devtester container status

# View logs
iris-devtester container logs --follow

# Stop when done
iris-devtester container stop

# Remove completely
iris-devtester container remove
```

### With Custom Configuration

```yaml
# iris-config.yml
edition: community
container_name: my_iris
ports:
  superserver: 1972
  webserver: 52773
namespace: USER
password: SYS
volumes:
  - ./data:/external/data
  - ./config:/opt/config:ro  # read-only
```

```bash
# Use custom config
iris-devtester container up --config iris-config.yml
```

### Python API

```python
from iris_devtester.config import ContainerConfig
from iris_devtester.utils import IRISContainerManager

# Programmatic container management
config = ContainerConfig.from_yaml("iris-config.yml")
container = IRISContainerManager.create_from_config(config)

# Container persists for long-running operations
# Perfect for benchmark infrastructure
```

## Example: Enterprise Setup

```python
from iris_devtools.containers import IRISContainer

# Auto-discovers license from ~/.iris/iris.key
with IRISContainer.enterprise(namespace="PRODUCTION") as iris:
    conn = iris.get_connection()
    # Use your enterprise IRIS instance
```

## Example: DAT Fixtures

Create reproducible test fixtures 10-100x faster than programmatic data creation:

```python
from iris_devtools.fixtures import FixtureCreator, DATFixtureLoader

# Create fixture from existing data
creator = FixtureCreator()
manifest = creator.create_fixture(
    fixture_id="test-users-100",
    namespace="USER",
    output_dir="./fixtures/test-users-100"
)

# Load fixture in tests (10K rows in <10 seconds)
loader = DATFixtureLoader()
result = loader.load_fixture("./fixtures/test-users-100")
print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")
```

### CLI Usage

```bash
# Create fixture
iris-devtester fixture create --name test-100 --namespace USER --output ./fixtures/test-100

# Validate integrity
iris-devtester fixture validate --fixture ./fixtures/test-100

# Load fixture
iris-devtester fixture load --fixture ./fixtures/test-100
```

## Example: Performance Monitoring

Auto-configure IRIS performance monitoring with resource-aware auto-disable:

```python
from iris_devtools.containers.monitoring import configure_monitoring
from iris_devtools.containers import IRISContainer

with IRISContainer.community() as iris:
    conn = iris.get_connection()

    # Zero-config monitoring setup
    success, message = configure_monitoring(conn)
    print(f"Monitoring configured: {message}")

    # Automatically disables monitoring if CPU > 90%
    # Automatically re-enables when CPU < 85%
```

## Example: Docker-Compose Integration (NEW in v1.0.1)

Work with existing IRIS containers (docker-compose, licensed IRIS, external containers):

```python
from iris_devtools.containers import IRISContainer
from iris_devtools.utils import enable_callin_service, test_connection, get_container_status

# Approach 1: Attach to existing container
iris = IRISContainer.attach("iris_db")  # Your docker-compose service name
conn = iris.get_connection()  # Auto-enables CallIn, discovers port
cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")

# Approach 2: Standalone utilities (shell-friendly)
success, msg = enable_callin_service("iris_db")
success, msg = test_connection("iris_db", namespace="USER")
success, report = get_container_status("iris_db")
```

### CLI Usage

```bash
# Check container status (aggregates running, health, connection)
iris-devtester container status iris_db

# Enable CallIn service (required for DBAPI connections)
iris-devtester container enable-callin iris_db

# Test database connection
iris-devtester container test-connection iris_db --namespace USER

# Reset password if needed
iris-devtester container reset-password iris_db --user _SYSTEM --password SYS
```

### Docker-Compose Example

```yaml
# docker-compose.yml
version: '3.8'
services:
  iris_db:
    image: intersystemsdc/iris:latest  # Licensed IRIS
    container_name: iris_db
    ports:
      - "1972:1972"
      - "52773:52773"
```

Then use iris-devtester with your existing container:

```python
# No testcontainers overhead - use existing container
iris = IRISContainer.attach("iris_db")
conn = iris.get_connection()
```

See [examples/10_docker_compose_integration.py](examples/10_docker_compose_integration.py) for complete examples.

## Architecture

Built on proven foundations:
- **testcontainers-python**: Industry-standard container management
- **testcontainers-iris-python** (caretdev): IRIS-specific extensions
- **Battle-tested code**: Extracted from production RAG (Retrieval-Augmented Generation) systems

## Constitution

This library follows [8 core principles](https://github.com/intersystems-community/iris-devtools/blob/main/CONSTITUTION.md) learned through production experience:

1. **Automatic Remediation Over Manual Intervention** - No "run this command" errors
2. **DBAPI First, JDBC Fallback** - Always use the fastest option
3. **Isolation by Default** - Each test gets its own database
4. **Zero Configuration Viable** - `pip install && pytest` just works
5. **Fail Fast with Guidance** - Clear errors with fix instructions
6. **Enterprise Ready, Community Friendly** - Both editions supported
7. **Medical-Grade Reliability** - 95%+ test coverage, all error paths tested
8. **Document the Blind Alleys** - Learn from our mistakes

## Documentation

- [Troubleshooting Guide](https://github.com/intersystems-community/iris-devtools/blob/main/docs/TROUBLESHOOTING.md)
- [Codified Learnings](https://github.com/intersystems-community/iris-devtools/blob/main/docs/learnings/) - Our hard-won knowledge
- [Examples](https://github.com/intersystems-community/iris-devtools/blob/main/examples/) - Runnable code samples

## Real-World Use Cases

### Use Case 1: CI/CD (Continuous Integration/Continuous Deployment) Testing
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pip install iris-devtester[all]
    pytest  # IRIS spins up automatically!
```

### Use Case 2: Local Development
```python
# Start coding immediately - no setup!
from iris_devtools.connections import get_iris_connection

conn = get_iris_connection()  # Auto-discovers or starts container
# Code your features...
```

### Use Case 3: Enterprise Production Testing
```python
# Test against real enterprise features
with IRISContainer.enterprise(
    license_key="/path/to/iris.key",
    image="containers.intersystems.com/intersystems/iris:latest"
) as iris:
    # Test mirrors, sharding, etc.
```

## Performance

Benchmarks on MacBook Pro M1:
- Container startup: ~5 seconds
- DBAPI connection: ~80ms
- JDBC connection: ~250ms
- Schema reset: <5 seconds
- Test isolation overhead: <100ms per test class

## Requirements

- Python 3.9+
- Docker (for testcontainers)
- InterSystems IRIS (Community or Enterprise)

## AI-Assisted Development

This project is optimized for AI coding assistants:

- **[AGENTS.md](AGENTS.md)** - Vendor-neutral AI configuration (build commands, CI/CD)
- **[CLAUDE.md](CLAUDE.md)** - Claude Code-specific context and patterns
- **Comprehensive examples** - All examples include expected outputs
- **Structured documentation** - Clear architecture, conventions, and troubleshooting

## Contributing

We welcome contributions! This library embodies real production experience. If you've solved an IRIS infrastructure problem, please contribute it so others don't repeat the same journey.

See [CONTRIBUTING.md](https://github.com/intersystems-community/iris-devtools/blob/main/CONTRIBUTING.md) for guidelines.

## Credits

Built on the shoulders of giants:
- **caretdev/testcontainers-iris-python** - IRIS testcontainers foundation
- **testcontainers/testcontainers-python** - Container lifecycle management
- **InterSystems** - IRIS database platform

Special thanks to all the developers who debugged these issues so you don't have to.

## License

MIT License - See [LICENSE](https://github.com/intersystems-community/iris-devtools/blob/main/LICENSE)

## Support

- [GitHub Issues](https://github.com/intersystems-community/iris-devtools/issues)
- [Documentation](https://github.com/intersystems-community/iris-devtools#readme)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/intersystems-iris) (tag: intersystems-iris)

---

**Remember**: Every feature here was paid for with real debugging time. Use this library to stand on our shoulders, not repeat our mistakes. 🚀
