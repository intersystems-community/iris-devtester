# Quickstart: Fixes for pgwire-identified bugs

**Feature Branch**: `020-fix-pgwire-issues` | **Date**: 2026-01-02

## 1. Custom User Password Reset

Calling `get_connection` with a custom user will now automatically trigger remediation for that user specifically.

```python
from iris_devtester.connections import get_connection

# Automatically resets password for SuperUser if needed
conn = get_connection(username="SuperUser")
```

## 2. Refreshing Test Data

Use the `force_refresh` parameter to reload fixtures into an existing namespace.

```python
from iris_devtester.fixtures import DATFixtureLoader

loader = DATFixtureLoader(container=my_container)
# Will delete namespace 'USER' if it exists, then reload from fixture
loader.load_fixture("./fixtures/my-data", target_namespace="USER", force_refresh=True)
```

## 3. Advanced Readiness Checks

The `IRISReadyWaitStrategy` is now deterministic. It will wait for the IRIS application to be fully functional before returning.

```python
from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

strategy = IRISReadyWaitStrategy()
# This will now use 'docker exec' to verify application initialization
is_ready = strategy.wait_until_ready(host="localhost", port=1972)
```
