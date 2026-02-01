# IRIS DevTester

**Battle-tested InterSystems IRIS infrastructure utilities for Python development**

[![PyPI version](https://badge.fury.io/py/iris-devtester.svg)](https://pypi.org/project/iris-devtester)
[![Python Versions](https://img.shields.io/pypi/pyversions/iris-devtester.svg)](https://pypi.org/project/iris-devtester/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/intersystems-community/iris-devtester)

## What is This?

IRIS DevTester is a comprehensive Python package that provides **automatic, reliable, production-tested** infrastructure for InterSystems IRIS development. It handles connectivity, container lifecycles, and test data management, codifying years of experience into a reusable toolkit.

## Problems It Solves

- **Auto-Remediation**: Fixes "Password change required" and expired accounts automatically
- **Port Management**: Eliminates conflicts when running tests in parallel
- **Isolation**: Ensures every test gets a clean, isolated database instance
- **Performance**: DBAPI-first connection pooling is 3x faster than traditional JDBC
- **Data Refresh**: High-speed GOF fixture loading (10-100x faster than SQL inserts)

## Quick Start

### 1. Install
```bash
pip install iris-devtester[all]
```

### 2. Start a Container
```bash
iris-devtester container up
```

### 3. Write and Run a Test
```python
from iris_devtester.containers import IRISContainer

def test_connection():
    with IRISContainer.community() as iris:
        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
```

## Container API

### Basic Usage
```python
from iris_devtester.containers import IRISContainer

# Community Edition (auto-detects ARM64 vs x86)
with IRISContainer.community() as iris:
    conn = iris.get_connection()

# Enterprise Edition (requires license)
with IRISContainer.enterprise(license_key="/path/to/iris.key") as iris:
    conn = iris.get_connection()
```

### Builder Methods
```python
# Set a custom container name (for debugging, logs, multiple containers)
iris = IRISContainer.community().with_name("my-test-db")

# Set credentials
iris = IRISContainer.community().with_credentials("_SYSTEM", "MyPassword")

# Pre-configure password (set via IRIS_PASSWORD env var at startup)
iris = IRISContainer.community().with_preconfigured_password("MyPassword")

# Chain multiple options
with IRISContainer.community() \
    .with_name("integration-test-db") \
    .with_credentials("_SYSTEM", "TestPass123") as iris:
    conn = iris.get_connection()
```

### Constructor Parameters
```python
IRISContainer(
    image="intersystemsdc/iris-community:latest",  # Docker image
    username="SuperUser",                           # Default username
    password="SYS",                                 # Default password
    namespace="USER",                               # Default namespace
    name="my-container",                            # Container name (alternative to with_name)
)
```

## Key Features

- **🔐 Automatic Password Management**: Remediates security flags using official system APIs.
- **🐳 Container Lifecycle**: CLI and Python API for IRIS container management (`up`, `start`, `stop`).
- **📦 DAT Fixture Management**: Create and load reproducible test fixtures in seconds.
- **⚡ DBAPI-First Performance**: Automatically selects the fastest available driver.
- **📊 Resource Monitoring**: Resource-aware performance tracking.

## AI-Assisted Development

This project is optimized for AI coding assistants:
- **[Agent Skill Manifest](https://github.com/intersystems-community/iris-devtester/blob/main/SKILL.md)** - Hierarchical guidance for Claude, Cursor, and Copilot.
- **[AGENTS.md](https://github.com/intersystems-community/iris-devtester/blob/main/AGENTS.md)** - Common build and test commands.

## Documentation

- **[Getting Started](https://github.com/intersystems-community/iris-devtester/blob/main/docs/GETTING_STARTED.md)**
- **[Troubleshooting Guide](https://github.com/intersystems-community/iris-devtester/blob/main/docs/TROUBLESHOOTING.md)**
- **[Examples](https://github.com/intersystems-community/iris-devtester/tree/main/examples/)**
- **[Codified Learnings](https://github.com/intersystems-community/iris-devtester/tree/main/docs/learnings/)**

## License

MIT License - See [LICENSE](https://github.com/intersystems-community/iris-devtester/blob/main/LICENSE)
