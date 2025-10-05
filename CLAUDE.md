# CLAUDE.md - IRIS DevTools

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
- `testcontainers-iris-python>=1.2.2` - IRIS support
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

## Important Reminders

1. **Don't rewrite what works** - Extract and enhance proven code
2. **Constitutional compliance is mandatory** - All 8 principles
3. **95% coverage minimum** - This is medical-grade software
4. **No Claude attribution** - Per user's global instructions
5. **Document blind alleys** - Help future developers
6. **ALWAYS enable CallIn service** - DBAPI connections require it (see docs/learnings/callin-service-requirement.md)

---

**Remember**: This package codifies years of production experience. Every feature represents real debugging hours saved. Build on that foundation.
