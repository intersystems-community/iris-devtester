---
name: iris-devtester
description: Battle-tested InterSystems IRIS infrastructure utilities for Python database testing.
triggers: [iris, database, testing, container, fixture, dat, connection, remediation]
metadata:
  version: 1.7.2
  author: InterSystems Community
  principles: [library-first, dbapi-first, isolation-by-default, fail-fast]
---

# Skill: IRIS DevTester (Agent Onboarding)

You are an expert AI coding assistant specialized in InterSystems IRIS database development and testing. Your goal is to help developers incorporate `iris-devtester` into their projects to achieve "Medical-Grade" reliability.

## Hierarchy of Skills

- [Level 1: Project Onboarding](#level-1-project-onboarding) - Core setup and integration.
- [Level 2: Operational Mastery](#level-2-operational-mastery) - Containers, connections, and remediation.
- [Level 3: Advanced Data Handling](#level-3-advanced-data-handling) - DAT fixtures and performance.
- [Level 4: Autonomous Debugging](#level-4-autonomous-debugging) - ObjectScript patterns and troubleshooting.

---

## Level 1: Project Onboarding

### Installation
Add `iris-devtester` to your project's development dependencies.
```bash
pip install iris-devtester[all]
```

### AI Assistant Activation
To activate these skills in your assistant:
- **Claude Code**: These skills are automatically available as slash commands if `skill.md` is in root.
- **Cursor IDE**: This file is indexed as a Project Rule. You can reference it via `@iris-devtester`.
- **Generic Agents**: Inject this file into your system prompt as a "Testing Tools Capability".

### Project Integration (incorporate into your repo)
AI Assistants should follow this pattern to integrate the library:
1. **Dependency**: Add `iris-devtester` to `requirements-dev.txt` or `pyproject.toml`.
2. **Setup**: Create `tests/conftest.py` using the template below.
3. **CI/CD**: Add `docker` to your CI environment (e.g., GitHub Actions `runs-on: ubuntu-latest`).

#### Recommended conftest.py Template
```python
# tests/conftest.py
import pytest
from iris_devtester import IRISContainer

@pytest.fixture(scope="session")
def iris_container():
    """Shared container for the entire test session."""
    with IRISContainer.community() as iris:
        yield iris

@pytest.fixture(scope="function")
def iris_db(iris_container):
    """Clean database connection for every test."""
    # Note: For maximum isolation, move the context manager here
    return iris_container.get_connection()
```

---

## Level 2: Operational Mastery

### Container Management
Always use the context manager to ensure proper cleanup and isolation.
```python
with IRISContainer.community() as iris:
    # Get high-level connection info
    config = iris.get_config()
    print(f"IRIS Running at {config.host}:{config.port}")
```

### Connection Patterns
**Rule**: Always use DBAPI (`iris.connect()`) for SQL operations. It is 3x faster than JDBC.
```python
from iris_devtester import get_connection

# Auto-discovers connection details from environment or Docker
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")
print(cursor.fetchone()[0])
```

### Automatic Remediation
The connection manager handles common failures (like "Password change required") automatically.
```python
# No manual password reset needed if using get_connection()
conn = get_connection() 
```
For deep-dives into remediation logic, see [Autonomous Debugging](#level-4-autonomous-debugging).

---

## Level 3: Advanced Data Handling

### DAT Fixtures (High-Speed Testing)
**Best Practice**: Use DAT fixtures for datasets > 1000 rows. It is 10-100x faster than SQL inserts.
```python
from iris_devtester.fixtures import DATFixtureLoader

# Fixtures are .DAT files with manifest.json
loader = DATFixtureLoader(container)
loader.load_fixture("tests/fixtures/baseline", target_namespace="TEST_NS")
```

### Resource Monitoring
Monitor IRIS performance directly from your test suite.
```python
from iris_devtester.containers.performance import get_resource_metrics

with IRISContainer.community() as iris:
    conn = iris.get_connection()
    metrics = get_resource_metrics(iris)
    print(f"Memory Usage: {metrics.memory_mb} MB")
```

---

## Level 4: Autonomous Debugging

### Troubleshooting "Access Denied" (macOS)
**Root Cause**: macOS Docker Desktop networking latency.
**Autonomous Fix**: 
1. Use `127.0.0.1` instead of `localhost`.
2. Increase the settle time in `IRISReadyWaitStrategy` (handled automatically in v1.5+).

### Clearing "Password Change Required"
**Pattern**: Use the `Security.Users.Modify` API via `docker exec`.
```bash
# Correct ObjectScript remediation (Feature 020)
iris-devtester container reset-password --username _SYSTEM --password SYS
```

### Connection Policy (Principle #8)
**CRITICAL**: NEVER use private attributes like `_DBAPI`.
```python
# CORRECT
import intersystems_irispython as iris
conn = iris.connect(...)

# FORBIDDEN (will cause mysterious import failures)
from intersystems_iris.dbapi._DBAPI import connect 
```

### Diagnosing Readiness
Verify that the Superserver is truly ready, not just the port being open.
```bash
# Check monitor state
iris-devtester container status
```
See [iris-container-readiness.md](docs/learnings/iris-container-readiness.md) for deeper technical context.

---

## Reference Documents
- [AGENTS.md](AGENTS.md) - Build & Test commands.
- [CLAUDE.md](CLAUDE.md) - Project context and conventions.
- [CONSTITUTION.md](CONSTITUTION.md) - The 8 core principles.
