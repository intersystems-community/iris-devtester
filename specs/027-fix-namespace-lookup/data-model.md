# Data Model: Fix Namespace Auto-Creation Container Lookup

**Feature**: 027-fix-namespace-lookup
**Date**: 2026-02-27

## Overview

This is a bug fix with no new persistent entities. The change modifies the strategy selection logic within existing functions. The "data model" here describes the decision inputs and the strategy abstraction.

## Existing Entities (unchanged)

### IRISConfig

The configuration object that drives `get_connection()`. Relevant fields for this fix:

| Field | Type | Default | Role in Strategy Selection |
|-------|------|---------|---------------------------|
| `host` | `str` | `"localhost"` | Used for auto_create smart default (localhost=True, remote=False) |
| `port` | `int` | `1972` | Passed to `iris.connect()` for %SYS bootstrap |
| `namespace` | `str` | `"USER"` | The target namespace to check/create |
| `username` | `str` | `"_SYSTEM"` | Credentials for %SYS connection |
| `password` | `str` | `"SYS"` | Credentials for %SYS connection |
| `container_name` | `Optional[str]` | `None` | **KEY DECISION POINT**: determines Docker-exec vs iris.connect() strategy |
| `auto_create` | `Optional[bool]` | `None` | Controls whether namespace auto-creation runs at all |

### Strategy Selection State Machine

```
                    ┌──────────────────────────────┐
                    │   ensure_namespace_exists()   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  Resolve auto_create flag     │
                    │  None → localhost? True:False  │
                    └──────────────┬───────────────┘
                                   │
                         ┌─────────▼─────────┐
                         │  auto_create?      │
                         └────┬─────────┬─────┘
                        False │         │ True
                              │         │
                    ┌─────────▼──┐  ┌───▼─────────────────┐
                    │ Skip. Done │  │ container_name set?  │
                    └────────────┘  └───┬─────────────┬────┘
                                    Yes │             │ No (None/"")
                                        │             │
                              ┌─────────▼──┐  ┌──────▼──────────────┐
                              │ Docker exec │  │ iris.connect(%SYS)  │
                              │ strategy    │  │ strategy             │
                              └─────────────┘  └─────────────────────┘
```

### Strategy Behavior

| Strategy | Check Existence | Create Namespace | Failure Mode |
|----------|-----------------|------------------|--------------|
| **Docker exec** | `docker exec <container> iris session IRIS -U %SYS` + `##class(Config.Namespaces).Exists(ns)` | `docker exec` + ObjectScript create script | Log error, proceed with connection |
| **iris.connect()** | `iris.connect(host, port, "%SYS", user, pass)` + `classMethodValue("Config.Namespaces", "Exists", ns)` | `classMethodValue("Config.Namespaces", "Create", ns, props)` | Log warning, proceed with connection |

## No New Entities

This fix does not introduce new data models, tables, or persistent state. It restructures the control flow within existing functions.
