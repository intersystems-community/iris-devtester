# IRIS DevTools

**Battle-tested InterSystems IRIS infrastructure utilities for Python development**

[![PyPI version](https://badge.fury.io/py/iris-devtester.svg)](https://badge.fury.io/py/iris-devtester)
[![Python Versions](https://img.shields.io/pypi/pyversions/iris-devtester.svg)](https://pypi.org/project/iris-devtester/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/intersystems-community/iris-devtester)

## Table of Contents

- [What is This?](#what-is-this)
- [The Problem It Solves](#the-problem-it-solves)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Documentation](#documentation)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)

## What is This?

IRIS DevTools provides **automatic, reliable, production-tested** infrastructure for InterSystems IRIS development. Born from years of production experience debugging IRIS + Docker + Python integration issues.

## The Problem It Solves

- "Password change required" errors breaking tests
- Port conflicts when running tests in parallel
- Tests polluting each other's data
- "Works on my machine" but fails in CI
- Copying infrastructure code between projects

**IRIS DevTools fixes all of these automatically.**

## Quick Start

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

with IRISContainer.community() as iris:
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(cursor.fetchone())
```

### pytest Integration

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

## Key Features

| Feature | Description | Details |
|---------|-------------|---------|
| **Testcontainers** | Isolated IRIS instances per test suite, automatic cleanup | [docs/features/testcontainers.md](docs/features/testcontainers.md) |
| **Docker-Compose** | Attach to existing containers, CLI commands | [docs/features/docker-compose.md](docs/features/docker-compose.md) |
| **DAT Fixtures** | 10-100x faster test data loading, SHA256 validation | [docs/features/dat-fixtures.md](docs/features/dat-fixtures.md) |
| **Performance Monitoring** | Auto-configure ^SystemPerformance, resource-aware | [docs/features/performance-monitoring.md](docs/features/performance-monitoring.md) |
| **Auto Password Reset** | Transparent "Password change required" handling | Built-in |
| **DBAPI-First** | 3x faster connections with automatic JDBC fallback | Built-in |

## Documentation

- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Constitution](CONSTITUTION.md)** - Our 8 core design principles
- **[Examples](examples/)** - Runnable code samples
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

### Feature Documentation

- [Testcontainers Integration](docs/features/testcontainers.md) - Isolated test containers
- [Docker-Compose Integration](docs/features/docker-compose.md) - Existing container support
- [DAT Fixture Management](docs/features/dat-fixtures.md) - Fast test data loading
- [Performance Monitoring](docs/features/performance-monitoring.md) - IRIS monitoring setup

## Requirements

- Python 3.9+
- Docker (for testcontainers)
- InterSystems IRIS (Community or Enterprise)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Credits

Built on: [testcontainers-iris-python](https://github.com/caretdev/testcontainers-iris-python) by caretdev, [testcontainers-python](https://github.com/testcontainers/testcontainers-python), and InterSystems IRIS.

## License

MIT License - See [LICENSE](LICENSE)

## Support

- [GitHub Issues](https://github.com/intersystems-community/iris-devtester/issues)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/intersystems-iris) (tag: intersystems-iris)
