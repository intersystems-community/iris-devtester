# Feature 003: Connection Manager - Implementation Plan

**Status**: Ready to implement
**Priority**: HIGH (blocks Feature 002 integration tests)
**Source**: Extracted from `~/ws/rag-templates/common/iris_connection_manager.py`

---

## Overview

Implement battle-tested connection manager with DBAPI-first architecture, automatic password reset, and zero-config discovery.

**Constitutional Principles**:
- #1: Automatic Remediation (password reset)
- #2: DBAPI First, JDBC Fallback
- #4: Zero Configuration Viable
- #5: Fail Fast with Guidance

---

## Implementation Tasks

### Phase 1: Connection Infrastructure (4-6 hours)

**T001**: Create `iris_devtools/connections/dbapi.py`
- Extract DBAPI connection logic from rag-templates
- Implement `create_dbapi_connection(config)` function
- Handle intersystems-irispython import gracefully
- Comprehensive error messages
- **Tests**: Unit tests for DBAPI connection creation

**T002**: Create `iris_devtools/connections/jdbc.py`
- Extract JDBC connection logic from rag-templates
- Implement `create_jdbc_connection(config)` function
- JDBC driver path discovery (multiple locations)
- Helpful error if driver missing
- **Tests**: Unit tests for JDBC connection creation

**T003**: Create `iris_devtools/connections/fallback.py`
- Implement connection fallback logic
- Try DBAPI first, fall back to JDBC
- Log which connection type succeeded
- **Tests**: Unit tests for fallback scenarios

**T004**: Create `iris_devtools/config/discovery.py`
- Configuration discovery (env vars, .env file, Docker)
- Priority: explicit config > env vars > .env > Docker defaults
- Validation and helpful errors
- **Tests**: Unit tests for config discovery

---

### Phase 2: Password Reset (3-4 hours)

**T005**: Create `iris_devtools/utils/password_reset.py`
- Extract password reset logic from rag-templates
- Detect "Password change required" errors
- Reset via Docker exec + ObjectScript
- Update environment variables
- **Tests**: Unit tests for detection and reset logic

**T006**: Integrate password reset into connections
- Auto-detect password change errors in DBAPI
- Auto-detect password change errors in JDBC
- Retry connection after reset
- Log remediation steps
- **Tests**: Unit tests for auto-remediation

---

### Phase 3: High-Level API (2-3 hours)

**T007**: Create `iris_devtools/connections/__init__.py`
- Implement `get_iris_connection(config=None)` function
- Zero-config: auto-discover from environment
- DBAPI-first with JDBC fallback
- Automatic password reset
- **Tests**: Contract tests for API

**T008**: Create `IRISConnectionManager` class
- Stateful connection manager
- Connection pooling/reuse
- Context manager support (`with` statement)
- `close_all()` method
- **Tests**: Unit tests for manager class

---

### Phase 4: pytest Integration (2-3 hours)

**T009**: Create `iris_devtools/testing/fixtures.py`
- `iris_db` fixture (function-scoped)
- `iris_db_shared` fixture (module-scoped)
- `iris_container` fixture (raw container access)
- Auto-cleanup on teardown
- **Tests**: Contract tests for fixtures

**T010**: Create `iris_devtools/testing/conftest.py`
- Register fixtures for pytest discovery
- Configure pytest markers
- Integration with testcontainers
- **Tests**: Integration tests

---

### Phase 5: Integration Testing (4-6 hours)

**T011**: Create `tests/integration/test_connections_integration.py`
- Test DBAPI connection with real IRIS
- Test JDBC connection with real IRIS
- Test fallback logic
- Test password reset (simulate password change)
- Test config discovery
- **Estimate**: 20+ tests

**T012**: Run Feature 002 integration tests
- Execute `tests/integration/test_monitoring_integration.py`
- Verify all 30+ tests pass
- Fix any IRIS-specific issues
- **Success Criteria**: All tests passing

---

### Phase 6: Documentation (2-3 hours)

**T013**: Create user documentation
- Connection usage guide
- Configuration examples
- Password reset documentation
- Troubleshooting guide

**T014**: Create API documentation
- Docstrings for all public APIs
- Type hints
- Usage examples

---

## File Structure

```
iris_devtools/
├── connections/
│   ├── __init__.py          # Public API: get_iris_connection()
│   ├── dbapi.py             # DBAPI connection
│   ├── jdbc.py              # JDBC connection
│   ├── fallback.py          # Fallback logic
│   └── manager.py           # IRISConnectionManager class
├── config/
│   ├── __init__.py
│   └── discovery.py         # Config discovery
├── utils/
│   ├── __init__.py
│   └── password_reset.py    # Password reset
└── testing/
    ├── __init__.py
    ├── fixtures.py          # pytest fixtures
    └── conftest.py          # pytest configuration

tests/
├── unit/
│   ├── test_dbapi_connection.py
│   ├── test_jdbc_connection.py
│   ├── test_connection_fallback.py
│   ├── test_config_discovery.py
│   └── test_password_reset.py
├── contract/
│   ├── test_connection_api.py
│   └── test_testing_fixtures_api.py
└── integration/
    └── test_connections_integration.py
```

---

## Key Design Decisions

### 1. DBAPI First (Principle #2)
```python
def get_iris_connection(config=None):
    """Zero-config connection with DBAPI-first."""
    try:
        return create_dbapi_connection(config)  # 3x faster
    except Exception:
        return create_jdbc_connection(config)   # Fallback
```

### 2. Automatic Password Reset (Principle #1)
```python
try:
    conn = iris.connect(...)
except Exception as e:
    if "Password change required" in str(e):
        reset_iris_password()  # Auto-remediate
        conn = iris.connect(...)  # Retry
```

### 3. Zero-Config Discovery (Principle #4)
```python
# Priority order:
# 1. Explicit config parameter
# 2. Environment variables (IRIS_HOST, IRIS_PORT, etc.)
# 3. .env file
# 4. Docker container defaults (localhost:1972, SuperUser/SYS)
```

### 4. Helpful Error Messages (Principle #5)
```python
raise ConnectionError(
    "Failed to connect to IRIS at localhost:1972\n"
    "\n"
    "What went wrong:\n"
    "  intersystems-irispython package not installed.\n"
    "\n"
    "How to fix it:\n"
    "  pip install 'iris-devtools[dbapi]'\n"
    "  # OR\n"
    "  pip install intersystems-irispython\n"
)
```

---

## Testing Strategy

### Unit Tests (60+ tests)
- DBAPI connection creation
- JDBC connection creation
- Fallback logic (DBAPI fails → JDBC)
- Config discovery (env, .env, defaults)
- Password reset detection
- Password reset execution

### Contract Tests (20+ tests)
- API signatures
- Return types
- Constitutional compliance
- Fixture availability

### Integration Tests (25+ tests)
- Real IRIS connections (DBAPI and JDBC)
- Password reset workflow
- Config discovery end-to-end
- Fixture usage
- Feature 002 monitoring tests

---

## Success Criteria

✅ **Code Complete**:
- All connection methods implemented
- Password reset working
- Config discovery functioning
- pytest fixtures available

✅ **Tests Passing**:
- 60+ unit tests
- 20+ contract tests
- 25+ integration tests
- Feature 002 tests (30+ tests)

✅ **Constitutional Compliance**:
- Principle #1: Auto password reset
- Principle #2: DBAPI first
- Principle #4: Zero-config works
- Principle #5: Clear error messages

✅ **Documentation**:
- User guide
- API reference
- Examples
- Troubleshooting

---

## Estimated Timeline

**Optimistic**: 15-20 hours
**Realistic**: 20-25 hours
**Pessimistic**: 25-30 hours

**Critical Path**: T001-T010 (core implementation)
**Parallel Work**: Documentation can be written alongside implementation

---

## Dependencies

**Required Packages**:
- `testcontainers-iris-python>=1.2.2` (already installed)
- `python-dotenv>=1.0.0` (for .env support)

**Optional Packages**:
- `intersystems-irispython>=3.2.0` (DBAPI)
- `jaydebeapi>=1.2.3` (JDBC)

---

## Risks and Mitigations

### Risk 1: JDBC Driver Location
**Risk**: JDBC driver may not be found in expected locations
**Mitigation**: Check multiple paths, provide clear download URL in error
**Impact**: Low (error message guides user)

### Risk 2: Password Reset Docker Dependency
**Risk**: Password reset requires Docker access
**Mitigation**: Graceful fallback with manual instructions
**Impact**: Medium (affects auto-remediation)

### Risk 3: Environment Detection
**Risk**: May not correctly detect IRIS packages
**Mitigation**: Clear error messages with installation instructions
**Impact**: Low (happens at import time)

---

## Next Steps

1. ✅ Create this plan
2. **Start T001**: Implement DBAPI connection
3. Continue through tasks sequentially
4. Run integration tests after T010
5. Execute Feature 002 tests after T012

---

**Ready to implement**: All source code identified, design validated, tests planned.
