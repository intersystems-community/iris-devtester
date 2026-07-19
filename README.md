# IRIS DevTester

**Battle-tested InterSystems IRIS infrastructure utilities for Python development**

[![PyPI version](https://badge.fury.io/py/iris-devtester.svg)](https://pypi.org/project/iris-devtester)
[![Python Versions](https://img.shields.io/pypi/pyversions/iris-devtester.svg)](https://pypi.org/project/iris-devtester/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/intersystems-community/iris-devtester)
[![Works with iris-agentic-dev](https://img.shields.io/badge/works%20with-iris--agentic--dev-blue.svg)](https://github.com/intersystems-community/iris-agentic-dev)

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

### 2. SQLite-Level Connectivity (Warm Start)

Use the persistent dev instance for instant connections across projects:

```bash
idt dev up
```

Then in your code:

```python
from iris_devtester.connections import get_connection

# Instant connection to a project-specific namespace
conn = get_connection()
```

### 3. Ephemeral Containers (for CI/CD)

For completely isolated test containers:

```python
from iris_devtester.containers import IRISContainer

def test_connection():
    with IRISContainer.community() as iris:
        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
```

## Container Editions

Three canonical container editions are available:

| Edition        | Size       | Use Case             | Image                                           |
| -------------- | ---------- | -------------------- | ----------------------------------------------- |
| **Community**  | ~972MB     | Development, testing | `intersystemsdc/iris-community`                 |
| **Enterprise** | ~1GB+      | Production testing   | `containers.intersystems.com/intersystems/iris` |
| **Light**      | **~580MB** | CI/CD pipelines      | `caretdev/iris-community-light`                 |

### Python API

```python
from iris_devtester.containers import IRISContainer

# Community Edition (auto-detects ARM64 vs x86)
with IRISContainer.community() as iris:
    conn = iris.get_connection()

# Light Edition (85% smaller, for CI/CD)
with IRISContainer.light() as iris:
    conn = iris.get_connection()

# Enterprise Edition (requires license)
with IRISContainer.enterprise(license_key="/path/to/iris.key") as iris:
    conn = iris.get_connection()

# Specify version
with IRISContainer.community(version="2025.1") as iris:
    conn = iris.get_connection()
```

### CLI Usage

```bash
# Community (default)
iris-devtester container up

# Light edition for CI/CD
iris-devtester container up --edition light

# Enterprise edition with license
iris-devtester container up --edition enterprise --license /path/to/iris.key

# List running IRIS containers
iris-devtester container list
```

### Light Edition Details

The Light edition removes components unnecessary for SQL-only workloads:

- **Removed**: Interoperability/Ensemble, Management Portal, DeepSee/BI, CSP/REST
- **Kept**: SQL engine, DBAPI, JDBC, ODBC, SQLAlchemy-IRIS support

Perfect for microservices, automated testing, and Python/SQL pipelines.

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
    username="_SYSTEM",                             # Default username
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

- **[Agent Skills](https://github.com/intersystems-community/iris-devtester/tree/main/skills/)** - Hierarchical guidance for Claude, Cursor, and Copilot (`iris-devtester`, `-containers`, `-connections`).
- **[AGENTS.md](https://github.com/intersystems-community/iris-devtester/blob/main/AGENTS.md)** - Common build and test commands.

## Works with iris-agentic-dev

iris-devtester owns the **container lifecycle**; [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev) (iad) owns **compiling and executing ObjectScript** inside it. They share one authoritative description of a connection so neither side has to reconstruct it — no manual port hunting.

Once a container is up, emit the handoff fragment iad reads from `.iris-agentic-dev.toml`:

```python
from iris_devtester.containers import IRISContainer

# Attach to a running container (e.g. started by `idt container up`)
container = IRISContainer.attach("opsreview-iris")

# Build the handoff contract (auto-detects a WebGateway sidecar if present)
info = container.connection_info()

# Write the fragment iad hot-reloads
with open(".iris-agentic-dev.toml", "w") as f:
    f.write(info.to_toml_snippet())
```

For a Docker-only container (no WebGateway), `to_toml_snippet()` emits:

```toml
container = "opsreview-iris"
docker_only = true
namespace = "USER"
```

When a WebGateway sidecar is detected on the same Docker network, it emits the
host-mapped web port instead:

```toml
container = "opsreview-iris"
web_port = 52774
docker_only = false
namespace = "USER"
```

Install the optional integration extra with `pip install iris-devtester[iad]`.
See [AGENTS.md → ECOSYSTEM](https://github.com/intersystems-community/iris-devtester/blob/main/AGENTS.md#ecosystem)
and the [iris-devtester-connections skill](https://github.com/intersystems-community/iris-devtester/blob/main/skills/iris-devtester-connections/SKILL.md).

## Documentation

- **[Getting Started](https://github.com/intersystems-community/iris-devtester/blob/main/docs/GETTING_STARTED.md)**
- **[Troubleshooting Guide](https://github.com/intersystems-community/iris-devtester/blob/main/docs/TROUBLESHOOTING.md)**
- **[Examples](https://github.com/intersystems-community/iris-devtester/tree/main/examples/)**
- **[Codified Learnings](https://github.com/intersystems-community/iris-devtester/tree/main/docs/learnings/)**

## License

MIT License - See [LICENSE](https://github.com/intersystems-community/iris-devtester/blob/main/LICENSE)
