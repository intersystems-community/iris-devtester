# Quickstart: Fix Namespace Auto-Creation Container Lookup

**Feature**: 027-fix-namespace-lookup
**Date**: 2026-02-27

## What Changed

The namespace auto-creation logic no longer defaults to looking up a Docker container named `iris_db` when you provide an explicit `IRISConfig`. Instead, it uses `iris.connect()` to the `%SYS` namespace to check/create namespaces programmatically.

## Before (Buggy)

```python
from iris_devtester.connections import get_connection
from iris_devtester.config import IRISConfig

# This worked but logged spurious errors:
# ERROR - Failed to create namespace 'USER': No such container: iris_db
config = IRISConfig(host="localhost", port=1972, namespace="USER")
conn = get_connection(config)
```

## After (Fixed)

```python
from iris_devtester.connections import get_connection
from iris_devtester.config import IRISConfig

# Clean connection — no Docker lookup, no spurious errors
config = IRISConfig(host="localhost", port=1972, namespace="USER")
conn = get_connection(config)

# If you WANT Docker-exec-based namespace operations, provide container_name:
config = IRISConfig(host="localhost", port=1972, namespace="USER", container_name="my-iris")
conn = get_connection(config)
```

## Zero-Config Still Works

```python
from iris_devtester.connections import get_connection

# Auto-discovery path is unchanged — if a container is found,
# Docker exec is used for namespace operations as before
conn = get_connection()
```

## Strategy Selection Rules

| Scenario | Strategy Used |
|----------|--------------|
| Explicit config, no `container_name` | `iris.connect()` to `%SYS` |
| Explicit config with `container_name` | Docker exec against that container |
| Auto-discovered config (from Docker) | Docker exec against discovered container |
| `auto_create=False` | Skipped entirely |

## Verification

```bash
# Run existing tests (must all pass — backward compatible)
pytest tests/unit/test_namespace_utils.py -v
pytest tests/integration/test_implicit_namespace.py -v

# Run the new tests
pytest tests/unit/test_namespace_utils.py -k "strategy" -v
```
