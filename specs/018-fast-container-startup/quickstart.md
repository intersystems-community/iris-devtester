# Quickstart: Fast Container Startup

**Feature**: 018-fast-container-startup
**Time to complete**: 5 minutes

---

## Prerequisites

- Docker installed and running
- Python 3.9+
- iris-devtester installed: `pip install iris-devtester`

---

## Scenario 1: Container Reuse for Fast Test Iteration

**Goal**: Run integration tests in <15 seconds using container reuse.

### Step 1: Start persistent dev container (one-time)

```bash
# Pull pre-baked dev image (passwords already reset)
docker pull ghcr.io/intersystems/iris-devtester-dev:latest

# Start named container
docker run -d --name iris-dev \
  -p 1972:1972 -p 52773:52773 \
  ghcr.io/intersystems/iris-devtester-dev:latest
```

### Step 2: Run tests with container reuse

```bash
# First run - verifies container, ~5 seconds
pytest tests/integration/ --reuse-container

# Subsequent runs - cached health check, ~3 seconds
pytest tests/integration/ --reuse-container
```

### Expected Output

```
================== test session starts ==================
platform darwin -- Python 3.11.0
Using existing container: iris-dev (cached health: OK)
collected 15 items

tests/integration/test_example.py ....               [100%]

=================== 15 passed in 4.23s ==================
```

**Validation**: Total time under 15 seconds after first run.

---

## Scenario 2: Namespace Isolation with Shared Container

**Goal**: Run parallel tests with isolated namespaces.

### Step 1: Use namespace isolation fixture

```python
# conftest.py
import pytest
from iris_devtester.containers import ContainerPool, TestNamespace

@pytest.fixture(scope="function")
def isolated_namespace(reuse_container):
    """Get isolated namespace for each test."""
    pool = ContainerPool.instance()
    container = pool.get_or_create("iris-dev")

    ns = TestNamespace.create_unique(container_ref=container)
    ns.create()
    ns.register_cleanup()

    yield ns

    ns.drop()
```

### Step 2: Use in tests

```python
def test_create_table(isolated_namespace):
    """Test runs in isolated namespace."""
    isolated_namespace.execute_sql("""
        CREATE TABLE TestData (ID INT, Name VARCHAR(100))
    """)

    result = isolated_namespace.execute_sql("SELECT COUNT(*) FROM TestData")
    assert result[0][0] == 0
```

### Expected Behavior

- Each test gets unique namespace (e.g., `TEST_1735084800_a1b2c3d4`)
- Namespace created in <2 seconds
- Namespace automatically cleaned up after test
- Parallel tests don't conflict

---

## Scenario 3: AI-Friendly Output

**Goal**: Test output is concise for AI consumption.

### Step 1: Run tests (default concise mode)

```bash
pytest tests/integration/ --reuse-container
```

### Expected Output (passing)

```
================== test session starts ==================
Using container: iris-dev
15 passed in 4.23s
==================
```

Total: ~10 lines (vs 200+ previously)

### Step 2: Run failing test

```bash
pytest tests/integration/test_fail.py --reuse-container
```

### Expected Output (failing)

```
================== test session starts ==================
FAILED tests/integration/test_fail.py::test_example

test_fail.py:15: AssertionError: assert 1 == 2

Context: Expected database record count
Actual: 1, Expected: 2

... [3 lines omitted] ...

1 failed in 2.34s
==================
```

Total: ~20 lines (vs 100+ previously)

### Step 3: Get verbose output when needed

```bash
pytest tests/integration/ --reuse-container -v
```

---

## Scenario 4: First-Time Setup

**Goal**: New developer runs tests within 2 minutes.

### Step 1: Clone and install

```bash
git clone https://github.com/intersystems/iris-devtester.git
cd iris-devtester
pip install -e ".[dev,test]"
```

### Step 2: Run tests (auto-pulls container)

```bash
pytest tests/unit/ tests/contract/
# Unit tests run immediately (no IRIS needed)

pytest tests/integration/
# First run: pulls image, starts container (~90s)
# Subsequent runs: reuses container (~5s)
```

### Expected Timeline

| Step | Time |
|------|------|
| Clone + install | 30s |
| Unit tests | 5s |
| First integration test | 90s (cold start) |
| Subsequent tests | 5s (warm start) |

**Total first-time**: Under 2 minutes (excluding one-time cold start)

---

## Validation Checklist

- [ ] Container reuse reduces test time to <15 seconds
- [ ] Namespace isolation prevents test pollution
- [ ] Output is under 50 lines for passing tests
- [ ] Output is under 100 lines for failing tests
- [ ] New developer can run tests in <2 minutes

---

## Troubleshooting

### Container not found

```bash
# Check container status
docker ps -a | grep iris-dev

# Restart if needed
docker start iris-dev
```

### Health check failing

```bash
# Force health check refresh
pytest tests/integration/ --reuse-container --no-cache

# Check container logs
docker logs iris-dev --tail 50
```

### Namespace creation fails

```bash
# Verify %SYS access
docker exec iris-dev iris session IRIS -U %SYS "Write ##class(Config.Namespaces).Exists(\"USER\")"
```

---
*Quickstart complete - feature ready for validation*
