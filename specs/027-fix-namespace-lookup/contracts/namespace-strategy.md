# API Contracts: Fix Namespace Auto-Creation Container Lookup

**Feature**: 027-fix-namespace-lookup
**Date**: 2026-02-27

## Overview

This feature modifies internal functions only — no public API changes. The contracts below define the expected behavior of the modified internal functions for test design.

## Contract 1: `ensure_namespace_exists(config)` — Strategy Selection

**Location**: `iris_devtester/utils/namespace.py`

### Input
- `config`: `IRISConfig` with fields: `host`, `port`, `namespace`, `username`, `password`, `container_name`, `auto_create`

### Behavior Contract

```python
def ensure_namespace_exists(config: IRISConfig) -> bool:
    """
    Returns True if namespace exists or was created.
    Returns True (with warning log) if check failed but connection should proceed.
    
    Strategy selection:
    - auto_create resolves to False → return True immediately (skip)
    - container_name is set (non-None, non-empty) → Docker exec strategy
    - container_name is not set → iris.connect() strategy
    - NEVER falls back to hardcoded container name
    """
```

### Test Scenarios

| # | auto_create | container_name | host | Expected Strategy | Expected Result |
|---|-------------|----------------|------|-------------------|-----------------|
| 1 | `False` | any | any | Skip | `True` (no check) |
| 2 | `True` | `"my-iris"` | any | Docker exec | Check/create via docker exec |
| 3 | `True` | `None` | `"localhost"` | iris.connect() | Check/create via %SYS |
| 4 | `True` | `None` | `"10.0.0.5"` | iris.connect() | Check/create via %SYS |
| 5 | `None` | `None` | `"localhost"` | iris.connect() | Resolves auto_create=True, uses iris.connect() |
| 6 | `None` | `None` | `"10.0.0.5"` | Skip | Resolves auto_create=False, skips |
| 7 | `None` | `"my-iris"` | `"localhost"` | Docker exec | Resolves auto_create=True, uses docker exec |
| 8 | `True` | `""` (empty) | `"localhost"` | iris.connect() | Empty string treated as unset |

## Contract 2: `check_namespace_via_iris_connect(config, namespace)` — New Function

**Location**: `iris_devtester/utils/namespace.py` (new)

### Input
- `config`: `IRISConfig` — provides host, port, username, password
- `namespace`: `str` — namespace to check

### Behavior Contract

```python
def check_namespace_via_iris_connect(config: IRISConfig, namespace: str) -> bool:
    """
    Connect to %SYS via iris.connect(), call Config.Namespaces.Exists(namespace).
    
    Returns True if namespace exists.
    Returns False if namespace does not exist.
    Raises no exceptions — catches all errors and returns False with warning log.
    """
```

### Test Scenarios

| # | Condition | Expected Return | Expected Log |
|---|-----------|-----------------|--------------|
| 1 | Namespace exists | `True` | DEBUG: "Namespace 'X' verified via iris.connect()" |
| 2 | Namespace does not exist | `False` | DEBUG: "Namespace 'X' not found via iris.connect()" |
| 3 | %SYS access denied | `False` | WARNING: "Cannot verify namespace 'X': %SYS access denied" |
| 4 | Connection refused (IRIS down) | `False` | WARNING: "Cannot verify namespace 'X': connection failed" |

## Contract 3: `create_namespace_via_iris_connect(config, namespace)` — New Function

**Location**: `iris_devtester/utils/namespace.py` (new)

### Input
- `config`: `IRISConfig`
- `namespace`: `str`

### Behavior Contract

```python
def create_namespace_via_iris_connect(config: IRISConfig, namespace: str) -> bool:
    """
    Connect to %SYS via iris.connect(), create namespace via Config.Namespaces.Create().
    
    Returns True if namespace was created successfully.
    Returns False on any failure (with warning log).
    """
```

## Contract 4: No Hardcoded `iris_db` in Namespace Path

### Negative Test Contract

```python
def test_no_hardcoded_iris_db_in_namespace_path():
    """
    GIVEN an IRISConfig with container_name=None
    WHEN ensure_namespace_exists() is called
    THEN no subprocess call contains 'iris_db'
    AND no Docker API call references 'iris_db'
    """
```

## Contract 5: `get_connection()` — Password Reset Fallback

**Location**: `iris_devtester/connections/connection.py`

### Change Contract

```python
# BEFORE (line 122):
container_name = getattr(config, "container_name", "iris_db") or "iris_db"

# AFTER:
container_name = getattr(config, "container_name", None)
# If container_name is None, skip Docker-based password reset
```
