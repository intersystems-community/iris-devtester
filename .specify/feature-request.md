# Feature Request: IRIS DevTools - Complete Implementation

## Context

This is a NEW package being extracted from the battle-tested infrastructure in `rag-templates`. We're building a reusable Python package that will be published to PyPI and used across all IRIS projects.

## Source Material

The implementation should be based on proven code from:
- **Source**: `~/ws/rag-templates/`
- **Key files to extract**:
  - `common/iris_connection_manager.py` (~500 lines) → Connection management
  - `tests/utils/iris_password_reset.py` (~200 lines) → Password reset
  - `tests/utils/preflight_checks.py` → Pre-flight validation
  - `tests/utils/schema_validator.py` → Schema validation
  - `tests/fixtures/schema_reset.py` → Schema reset
  - `tests/fixtures/database_cleanup.py` → Test cleanup
  - `tests/fixtures/database_state.py` → Test state tracking
  - `tests/conftest.py` (Feature 028 sections) → pytest fixtures

## What to Build

### 1. Connection Management (`iris_devtools/connections/`)

Extract from `rag-templates/common/iris_connection_manager.py`:

**Files to create**:
- `manager.py` - IRISConnectionManager class
  - DBAPI-first with JDBC fallback
  - Automatic password reset integration
  - Connection pooling
  - Environment detection

- `recovery.py` - Password reset utilities
  - IRISPasswordResetHandler from `tests/utils/iris_password_reset.py`
  - Automatic detection of "Password change required"
  - Docker exec commands for reset
  - Environment variable sync

- `__init__.py` - Convenience exports
  ```python
  from .manager import IRISConnectionManager, get_iris_connection
  from .recovery import IRISPasswordResetHandler, reset_iris_password_if_needed
  ```

### 2. Container Management (`iris_devtools/containers/`)

Build on testcontainers-iris-python:

**Files to create**:
- `iris_container.py` - Enhanced IRISContainer
  - Extend `testcontainers.iris.IRISContainer`
  - Add automatic password remediation
  - Add better wait strategies
  - Add health checks
  - Class methods: `.community()`, `.enterprise()`

- `wait_strategies.py` - Custom wait strategies
  - Wait for actual database readiness (not just logs)
  - Health check verification
  - Schema initialization wait

- `__init__.py` - Convenience exports

### 3. Testing Utilities (`iris_devtools/testing/`)

Extract from `rag-templates/tests/`:

**Files to create**:
- `fixtures.py` - pytest fixtures
  - `iris_test_fixture()` from conftest.py
  - `database_with_clean_schema` fixture
  - `validate_schema_once` fixture

- `preflight.py` - Pre-flight checks
  - Port from `tests/utils/preflight_checks.py`
  - PreflightChecker class
  - Automatic remediation

- `schema_manager.py` - Schema management
  - SchemaValidator from `tests/utils/schema_validator.py`
  - SchemaResetter from `tests/fixtures/schema_reset.py`
  - Auto-reset on mismatch

- `cleanup.py` - Test cleanup
  - DatabaseCleanupHandler from `tests/fixtures/database_cleanup.py`
  - CleanupRegistry

- `state.py` - Test state management
  - TestDatabaseState from `tests/fixtures/database_state.py`
  - TestStateRegistry

- `models.py` - Data models
  - SchemaDefinition, ColumnDefinition
  - SchemaValidationResult, SchemaMismatch
  - From `tests/utils/schema_models.py`

### 4. Configuration (`iris_devtools/config/`)

**Files to create**:
- `discovery.py` - Auto-discovery
  - IRISConfig class
  - Environment variable detection
  - .env file loading
  - Docker container inspection
  - Sensible defaults

- `defaults.py` - Default configurations
  - Default ports, hosts, credentials
  - Default schema definitions
  - Default wait strategies

### 5. Utilities (`iris_devtools/utils/`)

**Files to create**:
- `docker_helpers.py` - Docker utilities
  - Container inspection
  - Port discovery
  - Health checks

- `diagnostics.py` - Diagnostic tools
  - Connection testing
  - Performance profiling
  - Error reporting

## Implementation Requirements

### Constitutional Compliance

All code must follow the 8 principles in `CONSTITUTION.md`:

1. ✅ Automatic Remediation Over Manual Intervention
2. ✅ DBAPI First, JDBC Fallback
3. ✅ Isolation by Default
4. ✅ Zero Configuration Viable
5. ✅ Fail Fast with Guidance
6. ✅ Enterprise Ready, Community Friendly
7. ✅ Medical-Grade Reliability (95%+ coverage)
8. ✅ Document the Blind Alleys

### Testing Requirements

- Unit tests for all modules (95%+ coverage)
- Integration tests with real IRIS containers
- E2E tests validating full workflows
- Performance tests (meet NFR targets)

### Documentation Requirements

- Comprehensive docstrings
- Usage examples in `examples/`
- API documentation
- Migration guide from rag-templates
- Troubleshooting guide in `docs/`

## Success Criteria

✅ **Package Structure**:
- All modules properly organized
- Clean imports (no circular dependencies)
- Type hints throughout
- Proper __all__ exports

✅ **Functionality**:
- Connection management works (DBAPI + JDBC)
- Password reset automatic and transparent
- Testcontainers integration seamless
- pytest fixtures work out of the box
- Schema management robust

✅ **Quality**:
- 95%+ test coverage
- All constitutional principles followed
- No regressions from rag-templates
- Performance targets met

✅ **Usability**:
- Zero-config works: `pip install && pytest`
- Clear error messages with remediation
- Examples for all use cases
- rag-templates can migrate successfully

## Technical Constraints

- **Python**: 3.9+ (match rag-templates)
- **Dependencies**:
  - testcontainers>=4.0.0
  - testcontainers-iris-python>=1.2.2
  - Optional: intersystems-irispython, jaydebeapi
- **Testing**: pytest 8.0+
- **Code Style**: black, isort (already in pyproject.toml)

## Next Steps for Implementation

1. Start with connection manager (most critical)
2. Add password reset integration
3. Build testcontainers wrapper
4. Create pytest fixtures
5. Add configuration discovery
6. Write comprehensive tests
7. Document everything

## Reference Documentation

- Constitution: `CONSTITUTION.md` (8 core principles)
- Package config: `pyproject.toml` (dependencies, tools)
- Source code: `~/ws/rag-templates/` (working directory for extraction)

## Notes for /specify

This is a **code extraction and enhancement** project:
- Extract proven code from rag-templates
- Enhance with testcontainers integration
- Package for PyPI distribution
- Maintain 100% backwards compatibility with rag-templates usage

The goal is **NOT** to rewrite from scratch, but to **organize and enhance** battle-tested code into a reusable package.
