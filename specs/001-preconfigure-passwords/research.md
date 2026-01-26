# Research: Pre-configure Passwords at Container Startup

**Feature**: 001-preconfigure-passwords  
**Date**: 2026-01-24  
**Status**: Complete

## Research Questions

### 1. IRIS Container Password Environment Variables

**Question**: What environment variables does IRIS support for password pre-configuration?

**Decision**: Use `IRIS_PASSWORD` and `IRIS_USERNAME` environment variables

**Rationale**:
- Official InterSystems documentation confirms support for these env vars in IRIS container images
- Community Edition on Docker Hub (`intersystemsdc/iris-community`) supports these variables
- Environment variables are processed at container entrypoint before IRIS starts
- Simpler than `--password-file` alternative which requires file mounting

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| `--password-file` flag | Requires file creation and volume mounting; more complex |
| Post-startup ObjectScript | Already implemented; adds 5-10s delay |
| CPF merge file | Doesn't handle password configuration |

**Evidence**:
- InterSystems Docker documentation: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK
- Docker Hub image documentation confirms env var support
- Existing codebase already references these env vars in `config/discovery.py`

### 2. Testcontainers Integration Pattern

**Question**: How to pass environment variables to the underlying testcontainers container?

**Decision**: Use inherited `with_env()` method from BaseIRISContainer

**Rationale**:
- `testcontainers-iris-python` inherits from testcontainers base which provides `with_env()`
- Current codebase already uses `with_env()` for `ISC_CPF_MERGE_FILE` and `ISC_LICENSE_KEY`
- Follows established pattern in `iris_container.py` line 130 and line 280

**Implementation Pattern**:
```python
# In start() method, before calling super().start():
if self._preconfigure_password:
    self.with_env("IRIS_PASSWORD", self._password)
    if self._username != "SuperUser":  # Only if non-default
        self.with_env("IRIS_USERNAME", self._username)
```

### 3. Image Version Detection

**Question**: How to detect if an IRIS image supports password pre-configuration?

**Decision**: Attempt pre-configuration, verify after startup, fallback if needed

**Rationale**:
- No reliable way to detect image capabilities before container starts
- All modern IRIS Community images (2023+) support env var password config
- Verification via connection attempt is fast and reliable
- Fallback to existing password reset is already battle-tested

**Implementation Pattern**:
```python
# After container starts:
try:
    # Quick connection test with pre-configured credentials
    test_connection(timeout=2)
    logger.info("Password pre-configuration succeeded")
    self._password_preconfigured = True
except AuthenticationError:
    logger.warning("Password pre-configuration failed, falling back to reset")
    self._password_preconfigured = False
    reset_password(...)  # Existing mechanism
```

### 4. Backward Compatibility Strategy

**Question**: How to ensure existing code continues to work unchanged?

**Decision**: Auto-detect pre-configuration from environment variables or explicit API

**Rationale**:
- If `IRIS_PASSWORD` env var is set → use pre-configuration
- If `with_preconfigured_password()` called → use pre-configuration
- Otherwise → use existing password reset (current behavior)
- No change required to existing user code

**Activation Matrix**:
| Condition | Behavior |
|-----------|----------|
| No env var, no API call | Existing password reset (unchanged) |
| `IRIS_PASSWORD` env var set | Auto pre-configure |
| `with_preconfigured_password()` called | Explicit pre-configure |
| Both env var and API (conflict) | API takes precedence |

### 5. Logging and Observability

**Question**: How to provide visibility into which password mechanism was used?

**Decision**: Log at INFO level with clear messages

**Rationale**:
- Aligns with Constitution Principle #5: Fail Fast with Guidance
- Developers need to know which path was taken for debugging
- Existing logging patterns in codebase use Python `logging` module

**Log Messages**:
```
INFO: Password pre-configuration enabled via IRIS_PASSWORD environment variable
INFO: Password pre-configuration succeeded - skipping hardening step (saved ~5s)
WARN: Password pre-configuration failed - falling back to password reset
INFO: Using existing password reset mechanism (no pre-configuration detected)
```

## Dependencies Analysis

| Dependency | Version | Purpose | Risk |
|------------|---------|---------|------|
| testcontainers-iris-python | Existing | Base container class | Low - stable API |
| docker | Existing | Container management | Low - env vars are standard |
| pydantic | Existing | Config validation | Low - minor model extension |

## Performance Analysis

| Metric | Current | With Pre-config | Improvement |
|--------|---------|-----------------|-------------|
| Container startup | ~15-20s | ~10-15s | 3-5s faster |
| Time to first connection | ~5-10s after ready | ~1-2s after ready | 4-8s faster |
| Fallback penalty | N/A | ~0.5s (verification) | Acceptable |

## Security Considerations

- Password passed via environment variable to Docker (standard practice)
- Environment variables visible in `docker inspect` (same as current approach)
- No passwords stored in container filesystem
- Follows existing security model in codebase

## Conclusion

All research questions resolved. Ready for Phase 1 design.
