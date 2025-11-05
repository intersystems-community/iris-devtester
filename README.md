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

## Quick Start

### Installation

```bash
# Basic installation
pip install iris-devtester

# With DBAPI support (recommended - 3x faster)
pip install iris-devtester[dbapi]

# With all features
pip install iris-devtester[all]
```

### Zero-Config Usage

```python
from iris_devtools.containers import IRISContainer

# That's it! No configuration needed.
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(cursor.fetchone())
```

### Pytest Integration

```python
# conftest.py
from iris_devtools.testing import iris_test_fixture
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

## Key Features

### 🔐 Automatic Password Management
- Detects "Password change required" errors
- Automatically resets passwords via Docker
- Transparent retry - your code never knows it happened

### 🐳 Testcontainers Integration
- Each test suite gets isolated IRIS instance
- Automatic cleanup (even on crashes)
- No port conflicts
- No test data pollution

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
- **[.cursorrules](.cursorrules)** - Cursor IDE configuration
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
