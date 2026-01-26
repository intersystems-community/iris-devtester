# Data Model: Pre-configure Passwords at Container Startup

**Feature**: 001-preconfigure-passwords  
**Date**: 2026-01-24

## Entity Changes

### IRISContainer (Extended)

**Location**: `iris_devtester/containers/iris_container.py`

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `_preconfigure_password` | `bool` | `False` | Whether to use password pre-configuration |
| `_password_preconfigured` | `bool` | `False` | Whether pre-configuration succeeded |
| `_preconfigure_username` | `Optional[str]` | `None` | Username for pre-configuration (if different from default) |

**New Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `with_preconfigured_password` | `(password: str) -> IRISContainer` | Enable password pre-configuration with specified password |
| `with_credentials` | `(username: str, password: str) -> IRISContainer` | Enable pre-configuration with custom username and password |
| `_should_preconfigure` | `() -> bool` | Check if pre-configuration should be used (env var or explicit) |
| `_apply_password_preconfig` | `() -> None` | Apply env vars to container before start |
| `_verify_preconfig_success` | `() -> bool` | Verify credentials work after container ready |

**Modified Methods**:

| Method | Change |
|--------|--------|
| `__init__` | Add `_preconfigure_password`, `_password_preconfigured`, `_preconfigure_username` attributes |
| `start` | Add pre-configuration logic before `super().start()`, verify after, conditional fallback |

### ContainerConfig (Extended)

**Location**: `iris_devtester/config/container_config.py`

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `preconfigure_password` | `bool` | `False` | Enable password pre-configuration |

**Environment Variable Mapping**:

| Env Var | Config Field | Notes |
|---------|--------------|-------|
| `IRIS_PASSWORD` | `password` | Existing - also triggers pre-configuration when set |
| `IRIS_USERNAME` | N/A | Passed directly to container (not stored in config) |
| `IRIS_PRECONFIGURE_PASSWORD` | `preconfigure_password` | Explicit opt-in (deprecated by clarification - auto-detect instead) |

### PasswordPreconfigState (New - Internal)

**Location**: `iris_devtester/containers/iris_container.py` (inline or as enum)

| State | Description |
|-------|-------------|
| `NOT_ATTEMPTED` | Pre-configuration not enabled |
| `ATTEMPTED` | Pre-configuration was applied to container env |
| `SUCCEEDED` | Credentials verified working |
| `FAILED_FALLBACK` | Pre-configuration failed, used password reset |

## State Transitions

```
Container Created
       │
       ▼
┌──────────────────┐
│ Check if should  │
│ preconfigure     │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  YES        NO
    │         │
    ▼         ▼
┌─────────┐  ┌──────────────┐
│ Apply   │  │ Skip preconfig│
│ env vars│  │ (existing    │
└────┬────┘  │ behavior)    │
     │       └──────┬───────┘
     ▼              │
┌─────────┐         │
│ Start   │◄────────┘
│container│
└────┬────┘
     │
     ▼
┌─────────────┐
│ Verify      │
│ credentials │
└──────┬──────┘
       │
  ┌────┴────┐
  │         │
  ▼         ▼
SUCCESS   FAILURE
  │         │
  ▼         ▼
┌─────────┐ ┌─────────────┐
│ Skip    │ │ Fallback to │
│ reset   │ │ password    │
│ step    │ │ reset       │
└─────────┘ └─────────────┘
```

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| Password not empty | Pydantic `min_length=1` (existing) |
| Password meets IRIS requirements | Warning only (IRIS validates) |
| Username valid format | Regex validation if provided |

## Relationships

```
IRISContainer
     │
     ├── has-a ──► ContainerConfig (optional, via from_config())
     │
     ├── uses ──► PasswordResetResult (fallback)
     │
     └── produces ──► IRISConfig (connection info)
```

## Backward Compatibility

| Existing Usage | New Behavior |
|----------------|--------------|
| `IRISContainer.community()` | Unchanged - uses password reset |
| `IRISContainer.community()` with `IRIS_PASSWORD` env | Auto pre-configures |
| `IRISContainer.from_config(config)` | Unchanged unless `preconfigure_password=True` |
| Direct `IRISContainer(password="X")` | Unchanged - uses password reset |
| Direct `IRISContainer(password="X").with_preconfigured_password("X")` | Uses pre-configuration |
