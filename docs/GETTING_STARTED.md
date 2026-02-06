# Getting Started with iris-devtester

**Version**: 1.10.1  
**Package**: [iris-devtester on PyPI](https://pypi.org/project/iris-devtester/)

## What Is This?

`iris-devtester` is a Python testing toolkit for InterSystems IRIS databases. It provides:

- **Container Management**: Start/stop IRIS containers with one command
- **Connection Handling**: DBAPI-first connections with automatic retry
- **Fixture Loading**: Load .DAT fixtures for reproducible test data
- **pytest Integration**: Ready-to-use fixtures for test isolation

## Installation

```bash
# Basic installation (DBAPI support)
pip install iris-devtester

# With all features (JDBC, fixtures, testing)
pip install "iris-devtester[all]"
```

## Quick Start

### CLI Usage (Recommended for CI/CD)

```bash
# Start an IRIS container (zero-config)
iris-devtester container up

# Start light edition (85% smaller, ideal for CI/CD)
iris-devtester container up --edition light

# List running containers
iris-devtester container list

# Test database connectivity
iris-devtester test-connection

# View container status
iris-devtester container status

# Stop and remove when done
iris-devtester container stop
iris-devtester container remove
```

### Python API Usage

```python
from iris_devtester.containers import IRISContainer

# Start a container with context manager (auto-cleanup)
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(cursor.fetchone()[0])
```

### pytest Integration

```python
# conftest.py
from iris_devtester.testing import iris_db

# Use the fixture in tests
def test_database_query(iris_db):
    conn = iris_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1+1")
    assert cursor.fetchone()[0] == 2
```

## Container Editions

Choose the right edition for your use case:

| Edition | Size | Use Case | Factory Method |
|---------|------|----------|----------------|
| **Community** | ~3.5GB | Full-featured development | `IRISContainer.community()` |
| **Light** | ~580MB | CI/CD pipelines (6x smaller) | `IRISContainer.light()` |
| **Enterprise** | ~1GB+ | Licensed production features | `IRISContainer.enterprise(license_key=...)` |

### Light Edition Details

The light edition (`caretdev/iris-community-light`) is optimized for CI/CD:

- **85% smaller** than full community edition
- **Removes**: Interoperability, Management Portal, DeepSee/BI, CSP/REST
- **Keeps**: SQL engine, DBAPI, JDBC, ODBC, SQLAlchemy-IRIS
- **Multi-arch**: Supports both ARM64 (Apple Silicon) and x86

```bash
# CLI
iris-devtester container up --edition light

# Python
with IRISContainer.light() as iris:
    conn = iris.get_connection()
```

### Enterprise Edition

For licensed IRIS with enterprise features:

```bash
# CLI
iris-devtester container up --edition enterprise --license ~/.iris/iris.key

# Python
with IRISContainer.enterprise(license_key="/path/to/iris.key") as iris:
    conn = iris.get_connection()
```

## CLI Command Reference

### Container Commands

```bash
iris-devtester container --help

# Available commands:
  up              Create and start container
  list            List IRIS containers
  status          Check container health
  start           Start existing container
  stop            Stop container
  restart         Restart container
  remove          Remove container
  logs            View container logs
  reset-password  Reset IRIS user password
  enable-callin   Enable CallIn service (for DBAPI)
  test-connection Test database connectivity
```

### Common Options

```bash
# Custom container name
iris-devtester container up --name my-project-db

# Specify edition
iris-devtester container up --edition light

# JSON output (for scripting/agents)
iris-devtester container list --format json
iris-devtester container status --format json
```

### Exit Codes

For automation and AI agents:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Not found / Config error |
| 5 | Timeout |

## Configuration

### Environment Variables

```bash
export IRIS_HOST=localhost
export IRIS_PORT=1972
export IRIS_NAMESPACE=USER
export IRIS_USERNAME=_SYSTEM
export IRIS_PASSWORD=SYS
```

### YAML Configuration

Create `iris-config.yml`:

```yaml
container_name: my-iris-db
edition: community
superserver_port: 1972
webserver_port: 52773
namespace: USER
password: SYS
```

Then use:

```bash
iris-devtester container up --config iris-config.yml
```

## Common Workflows

### Local Development

```bash
# Start container once
iris-devtester container up --name dev-iris

# Run your tests
pytest

# Container persists between test runs
# Stop when done for the day
iris-devtester container stop
```

### CI/CD Pipeline

```yaml
# GitHub Actions example
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e ".[test]"
      
      - name: Start IRIS (light edition for speed)
        run: iris-devtester container up --edition light
      
      - name: Run tests
        run: pytest
      
      - name: Cleanup
        if: always()
        run: iris-devtester container remove --force
```

### Fixture-Based Testing

```bash
# Create fixture from existing data
iris-devtester fixture create --namespace USER --output ./fixtures/baseline

# Load fixture into test database
iris-devtester fixture load --fixture ./fixtures/baseline
```

## Troubleshooting

### "Access Denied" Errors

Usually caused by expired passwords. Fix:

```bash
iris-devtester container reset-password
iris-devtester test-connection
```

### Container Won't Start

Check if port is in use:

```bash
# List all IRIS containers
iris-devtester container list --all

# Remove old container
iris-devtester container remove old-container --force
```

### DBAPI Connection Fails

Ensure CallIn service is enabled:

```bash
iris-devtester container enable-callin
```

## For AI Agents

This CLI is designed to be agent-friendly:

1. **Self-documenting**: `iris-devtester --help` shows all options
2. **Structured output**: `--format json` for machine-readable data
3. **Clear exit codes**: 0=success, non-zero=failure
4. **Idempotent operations**: Safe to run commands multiple times

Example agent workflow:

```bash
# Check if container exists
iris-devtester container list --format json

# Start if not running
iris-devtester container up --edition light

# Verify connectivity
iris-devtester test-connection

# Run tests
pytest tests/
```

## When to Use docker-compose Instead

`iris-devtester` manages **single IRIS containers**. For these scenarios, use `docker-compose` directly:

| Scenario | Why docker-compose |
|----------|-------------------|
| **Sharded clusters** | Multiple shards + router require coordinated networking |
| **Mirrored pairs** | Primary + backup with failover configuration |
| **ECP configurations** | Application servers + database servers |
| **Multi-service stacks** | IRIS + web server + cache + queue |
| **Custom networking** | Specific network topologies or bridges |

### Example: Sharded IRIS Cluster

For a sharded HNSW vector search setup with 8 shards:

```yaml
# docker-compose.yaml
services:
  iris-router:
    image: intersystemsdc/iris-community:latest
    ports:
      - "1972:1972"
    # Router configuration...
    
  iris-shard-1:
    image: intersystemsdc/iris-community:latest
    # Shard 1 configuration...
    
  iris-shard-2:
    image: intersystemsdc/iris-community:latest
    # Shard 2 configuration...
    
  # ... more shards
```

Then use:

```bash
docker-compose up -d
# Wait for cluster to be ready
docker-compose logs -f iris-router
```

### Custom Images with iris-devtester

For **single containers** with custom images, use the `--image` option:

```bash
# Custom registry
iris-devtester container up --image myregistry.io/iris:custom

# Specific IRIS version
iris-devtester container up --image intersystemsdc/iris-community:2024.1

# IRIS with ZPM pre-installed
iris-devtester container up --image intersystemsdc/iris-community:2024.1-zpm
```

## Next Steps

- [README.md](../README.md) - Full package documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [CONSTITUTION.md](../CONSTITUTION.md) - Design principles
- [SKILL.md](../SKILL.md) - AI agent skill manifest

---

**Questions?** Open an issue on [GitHub](https://github.com/intersystems-community/iris-devtester/issues)
