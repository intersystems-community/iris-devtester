# CLAUDE.md - IRIS DevTools

**Purpose**: Provides Claude Code with project-specific context, patterns, and conventions.

**Related Files**:
- [AGENTS.md](AGENTS.md) - Vendor-neutral AI configuration (build commands, CI/CD, operational details)
- [README.md](README.md) - Project overview for all audiences (human and AI)
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributor onboarding and guidelines

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**IRIS DevTools** is a battle-tested Python package providing automatic, reliable infrastructure for InterSystems IRIS development. This is being extracted from production code in the `rag-templates` project.

## Source Material

This package is being built by extracting and enhancing code from:
- **Location**: `~/ws/rag-templates/`
- **Key areas**: Connection management, password reset, testing infrastructure, schema management

## Core Principles (CONSTITUTIONAL)

All code MUST follow the 8 principles in `CONSTITUTION.md`:

1. **Automatic Remediation Over Manual Intervention** - No "run this command" errors
2. **DBAPI First, JDBC Fallback** - Always try fastest option first
3. **Isolation by Default** - Each test gets its own database
4. **Zero Configuration Viable** - `pip install && pytest` must work
5. **Fail Fast with Guidance** - Clear errors with fix instructions
6. **Enterprise Ready, Community Friendly** - Support both editions
7. **Medical-Grade Reliability** - 95%+ test coverage required
8. **Document the Blind Alleys** - Explain why not X

## Development Workflow

### Initial Setup

```bash
# Already done:
cd ~/ws/iris-devtools
git init
git checkout -b main

# Install in development mode
pip install -e ".[dev,test,all]"

# Run tests
pytest
```

### Code Organization

```
iris_devtools/
├── connections/    # Connection management (DBAPI/JDBC)
├── containers/     # Testcontainers wrapper
├── fixtures/       # DAT fixture management (Feature 004)
├── testing/        # pytest fixtures & utilities
├── config/         # Configuration discovery
└── utils/          # Helpers
```

### Testing Requirements

- **Unit tests**: `tests/unit/` - Mock external dependencies
- **Integration tests**: `tests/integration/` - Use real IRIS containers
- **E2E tests**: `tests/e2e/` - Full workflow validation
- **Coverage**: Must maintain 95%+

### Code Style

Configured in `pyproject.toml`:
- **black**: Line length 100
- **isort**: Compatible with black
- **mypy**: Type checking (when possible)
- **pytest**: Comprehensive test suite

### Extraction Guidelines

When extracting from rag-templates:

1. **Copy proven code** - Don't rewrite what works
2. **Update imports** - Adjust for new package structure
3. **Add type hints** - Improve type safety
4. **Keep tests** - Port relevant tests
5. **Update docstrings** - Ensure accuracy
6. **Check constitutional compliance** - Verify all 8 principles

### Dependencies

Core:
- `testcontainers>=4.0.0` - Container management
- `testcontainers-iris>=1.2.2` - IRIS support
- `python-dotenv>=1.0.0` - Environment config

Optional (install with `[all]`):
- `intersystems-irispython>=3.2.0` - DBAPI (fast)
- `jaydebeapi>=1.2.3` - JDBC (fallback)

## Key Files

### Must Read Before Coding

- `CONSTITUTION.md` - 8 core principles (NON-NEGOTIABLE)
- `README.md` - User-facing documentation
- `pyproject.toml` - Package configuration
- `.specify/feature-request.md` - Implementation plan

### Source Code References

Look at `~/ws/rag-templates/` for:
- Connection patterns: `common/iris_connection_manager.py`
- Password reset: `tests/utils/iris_password_reset.py`
- Testing utilities: `tests/utils/`, `tests/fixtures/`
- pytest fixtures: `tests/conftest.py` (Feature 028 sections)

## Common Tasks

### Adding a New Module

```bash
# Create module file
touch iris_devtools/new_module/module_name.py

# Add __init__.py
cat > iris_devtools/new_module/__init__.py << 'EOF'
"""New module description."""
from .module_name import MainClass

__all__ = ["MainClass"]
EOF

# Create tests
touch tests/unit/test_module_name.py
touch tests/integration/test_module_name_integration.py
```

### Running Tests

```bash
# All tests
pytest

# Specific test type
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=iris_devtools --cov-report=html

# Fast (skip slow tests)
pytest -m "not slow"
```

### Code Quality Checks

```bash
# Format code
black .
isort .

# Type check
mypy iris_devtools/

# Lint
flake8 iris_devtools/

# All checks
black . && isort . && flake8 . && mypy iris_devtools/ && pytest
```

## Important Patterns

### Error Messages (Constitutional Requirement)

```python
# WRONG
raise ConnectionError("Failed to connect")

# RIGHT
raise ConnectionError(
    "Failed to connect to IRIS at localhost:1972\n"
    "\n"
    "What went wrong:\n"
    "  The IRIS database is not running or not accessible.\n"
    "\n"
    "How to fix it:\n"
    "  1. Start IRIS: docker-compose up -d\n"
    "  2. Wait 30 seconds for startup\n"
    "  3. Verify: docker logs iris_db\n"
    "\n"
    "Documentation: https://iris-devtools.readthedocs.io/troubleshooting/\n"
)
```

### Connection Management (Constitutional Requirement)

```python
# Always try DBAPI first, fall back to JDBC
try:
    conn = get_dbapi_connection()
except Exception:
    conn = get_jdbc_connection()  # Fallback
```

### Test Isolation (Constitutional Requirement)

```python
# Each test gets own container or unique namespace
@pytest.fixture(scope="function")
def iris_db():
    with IRISContainer.community() as iris:
        yield iris.get_connection()
    # Automatic cleanup
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/connection-manager

# Commit with descriptive messages (NO CLAUDE ATTRIBUTION per user instructions)
git commit -m "Add DBAPI-first connection manager with automatic recovery"

# Keep commits focused and atomic
```

## Documentation

All public APIs must have:
- Clear docstrings (Google style)
- Type hints
- Usage examples
- Error conditions explained

Example:
```python
def get_iris_connection(config: Optional[dict] = None) -> Connection:
    """
    Get IRIS database connection with automatic remediation.

    Tries DBAPI first (3x faster), falls back to JDBC if unavailable.
    Automatically resets password if "Password change required" detected.

    Args:
        config: Optional connection configuration. If None, auto-discovers
                from environment variables, .env file, or Docker.

    Returns:
        Database connection ready to use.

    Raises:
        ConnectionError: If connection fails after auto-remediation attempts.
                        Error message includes remediation steps.

    Examples:
        >>> # Zero-config (auto-discovers)
        >>> conn = get_iris_connection()

        >>> # Explicit config
        >>> conn = get_iris_connection({
        ...     "host": "localhost",
        ...     "port": 1972,
        ...     "namespace": "USER"
        ... })
    """
```

## Release Process

Not yet - focus on implementation first. But when ready:

```bash
# Version bump in pyproject.toml
# Build package
python -m build

# Upload to PyPI
twine upload dist/*
```

## Getting Help

- **Constitution**: `CONSTITUTION.md` - Answers "why" questions
- **README**: User-facing documentation
- **Source**: `~/ws/rag-templates/` - Working implementation
- **Specification**: `.specify/feature-request.md` - What to build

## Feature 004: DAT Fixture Management

**Status**: Planned (design phase complete)
**Branch**: `004-dat-fixtures`
**Docs**: `specs/004-dat-fixtures/`

### Quick Overview

Provides fast, reproducible test fixtures by exporting IRIS tables to .DAT files with checksum validation.

**Performance**: 10-100x faster than programmatic test data creation
- Load 10K rows in <10s (vs ~50 minutes programmatically)
- SHA256 checksum validation for data integrity
- Atomic loading with transaction rollback
- Version-controlled fixtures for team sharing

### Module Structure

```
iris_devtools/fixtures/
├── __init__.py           # Public API: DATFixtureLoader, FixtureCreator
├── loader.py             # DATFixtureLoader class (loads .DAT files)
├── creator.py            # FixtureCreator class (exports to .DAT)
├── validator.py          # FixtureValidator class (checksum validation)
├── manifest.py           # FixtureManifest dataclass + schema
└── pytest_plugin.py      # pytest integration (@pytest.mark.dat_fixture)
```

### CLI Commands

```bash
# Create fixture from tables
iris-devtester fixture create --name test-100 --tables RAG.Entities --output ./fixtures/test-100

# Validate fixture integrity
iris-devtester fixture validate --fixture ./fixtures/test-100

# Load fixture into IRIS
iris-devtester fixture load --fixture ./fixtures/test-100

# List available fixtures
iris-devtester fixture list ./fixtures/

# Show fixture info
iris-devtester fixture info --fixture ./fixtures/test-100
```

### Python API

```python
from iris_devtools.fixtures import DATFixtureLoader, FixtureCreator

# Create fixture from namespace
creator = FixtureCreator(container=iris_container)
manifest = creator.create_fixture(
    fixture_id="test-100",
    namespace="SOURCE_NS",
    output_dir="./fixtures/test-100"
)

# Load fixture into new namespace
loader = DATFixtureLoader(container=iris_container)
target_ns = iris_container.get_test_namespace(prefix="TARGET")
result = loader.load_fixture(
    fixture_path="./fixtures/test-100",
    target_namespace=target_ns
)
print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")

# Cleanup
loader.cleanup_fixture(target_ns, delete_namespace=True)
```

### pytest Integration

```python
# Use pytest fixtures for DAT fixture management
@pytest.fixture
def loaded_fixture(iris_container):
    """Load DAT fixture for tests."""
    loader = DATFixtureLoader(container=iris_container)
    target_ns = iris_container.get_test_namespace(prefix="TEST")

    result = loader.load_fixture(
        fixture_path="./fixtures/test-100",
        target_namespace=target_ns
    )

    yield result

    # Cleanup
    loader.cleanup_fixture(target_ns, delete_namespace=True)

def test_entity_count(loaded_fixture):
    """Test using loaded DAT fixture."""
    assert loaded_fixture.success
    assert len(loaded_fixture.tables_loaded) > 0
```

### Key Design Decisions

1. **ObjectScript via DBAPI**: Use `$SYSTEM.OBJ.Export()` and `$SYSTEM.OBJ.Load()` for .DAT operations
2. **SHA256 checksums**: Cryptographic validation for medical-grade reliability
3. **Transaction-based loading**: Atomic all-or-nothing with automatic rollback
4. **Dataclasses for manifest**: Zero dependencies, simple validation
5. **Flat directory structure**: Git-friendly, easy to inspect

### Constitutional Compliance

- ✅ Principle #2: DBAPI First (inherits from Feature 003)
- ✅ Principle #4: Zero Configuration (auto-discovers IRIS connection)
- ✅ Principle #5: Fail Fast with Guidance (structured error messages)
- ✅ Principle #7: Medical-Grade Reliability (100% checksum validation)

### Reference Documentation

- Spec: `specs/004-dat-fixtures/spec.md`
- Plan: `specs/004-dat-fixtures/plan.md`
- Research: `specs/004-dat-fixtures/research.md`
- Data Model: `specs/004-dat-fixtures/data-model.md`
- Contracts: `specs/004-dat-fixtures/contracts/`
- Quickstart: `specs/004-dat-fixtures/quickstart.md`

---

## Feature 014: Defensive Container Validation

**Status**: Complete
**Branch**: `014-address-this-enhancement`
**Docs**: `specs/014-address-this-enhancement/`

### Quick Overview

Provides defensive validation for Docker container health with automatic detection of common failure modes like stale container ID references, stopped containers, and network accessibility issues.

**Performance**: Progressive validation with strict SLA targets
- MINIMAL level: <500ms (just running status)
- STANDARD level: <1000ms (running + exec accessibility)
- FULL level: <2000ms (STANDARD + IRIS health check)
- Caching with 5-second TTL for repeated checks

### Module Structure

```
iris_devtester/containers/
├── models.py           # ContainerHealthStatus, HealthCheckLevel, ValidationResult, ContainerHealth
├── validation.py       # validate_container(), ContainerValidator class
└── iris_container.py   # IRISContainer.validate(), assert_healthy() methods
```

### Python API

```python
from iris_devtester.containers import (
    validate_container,
    ContainerValidator,
    HealthCheckLevel,
    IRISContainer
)

# Standalone validation function
result = validate_container(
    container_name="iris_db",
    level=HealthCheckLevel.STANDARD
)

if not result.success:
    print(result.format_message())  # Structured error message

# Stateful validator with caching
validator = ContainerValidator("iris_db", cache_ttl=5)
result = validator.validate(level=HealthCheckLevel.FULL)
health = validator.get_health()  # Detailed metadata

# IRISContainer integration
with IRISContainer.community() as iris:
    # Validate container health
    result = iris.validate(level=HealthCheckLevel.STANDARD)

    # Or assert healthy (raises on failure)
    iris.assert_healthy()
```

### Validation Levels

**MINIMAL** (<500ms target):
- Container exists
- Container running status

**STANDARD** (<1000ms target):
- MINIMAL checks
- Exec accessibility test (can run commands)

**FULL** (<2000ms target):
- STANDARD checks
- IRIS-specific health check (database responsive)

### Health Statuses

- `HEALTHY`: Container running and accessible
- `RUNNING_NOT_ACCESSIBLE`: Running but exec commands fail
- `NOT_RUNNING`: Container exists but stopped
- `NOT_FOUND`: Container doesn't exist
- `STALE_REFERENCE`: Container ID changed (recreated)
- `DOCKER_ERROR`: Docker daemon communication failed

### Error Messages

All error messages follow Constitutional Principle #5 (Fail Fast with Guidance):

```
Container validation failed for 'iris_db'

What went wrong:
  Container 'iris_db' does not exist.

How to fix it:
  1. List all containers:
     docker ps -a
  2. Start container if it exists:
     docker start iris_db
  3. Or create new container:
     docker run -d --name iris_db intersystemsdc/iris-community:latest

Available containers:
  - iris_test (running)
  - iris_prod (exited)
```

### Use Cases

1. **Pre-flight checks**: Validate container before operations
2. **Debugging**: Identify why container operations fail
3. **Monitoring**: Track container health over time
4. **CI/CD**: Ensure test infrastructure is healthy

### Key Design Decisions

1. **Progressive validation**: Fail fast at each level for performance
2. **Factory pattern**: Type-safe ValidationResult creation
3. **Caching strategy**: 5-second TTL balances freshness and performance
4. **Docker SDK**: Native Python library (no shell commands)
5. **Structured error messages**: Following Constitutional Principle #5

### Constitutional Compliance

- ✅ Principle #1: Automatic detection of issues (no manual checks)
- ✅ Principle #5: Fail Fast with Guidance (structured error messages)
- ✅ Principle #7: Medical-Grade Reliability (comprehensive test coverage)

### Test Coverage

- **Contract tests**: 26 tests (data models + API contracts)
- **Integration tests**: 31 tests (real Docker containers)
- **Total**: 57 tests, all passing
- **Performance**: All SLAs verified (<500ms, <1000ms, <2000ms)

### Reference Documentation

- Spec: `specs/014-address-this-enhancement/spec.md`
- Plan: `specs/014-address-this-enhancement/plan.md`
- Quickstart: `specs/014-address-this-enhancement/quickstart.md`
- Contracts: `specs/014-address-this-enhancement/contracts/`
- Data Model: `specs/014-address-this-enhancement/data-model.md`

---

## Important Reminders

1. **Don't rewrite what works** - Extract and enhance proven code
2. **Constitutional compliance is mandatory** - All 8 principles
3. **95% coverage minimum** - This is medical-grade software
4. **No Claude attribution** - Per user's global instructions
5. **Document blind alleys** - Help future developers
6. **ALWAYS enable CallIn service** - DBAPI connections require it (see docs/learnings/callin-service-requirement.md)

---

**Remember**: This package codifies years of production experience. Every feature represents real debugging hours saved. Build on that foundation.
