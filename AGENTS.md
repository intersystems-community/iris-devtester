# AGENTS.md - AI Agent Configuration

**Version**: 2.0.0
**Project**: iris-devtester (PyPI: `iris-devtester`)
**Python**: 3.9+

> AI-specific operational details. For project context: [README.md](README.md), [CLAUDE.md](CLAUDE.md), [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Build & Test Commands

```bash
# Install (development mode with all extras)
pip install -e ".[all,dev,test]"

# Run ALL tests
pytest

# Run SINGLE test (most common)
pytest tests/unit/test_connection_info.py::test_connection_config_parsing -v
pytest -k "test_basic_connection" -v

# Run by category
pytest tests/unit/                    # Fast, no Docker
pytest tests/integration/             # Requires Docker
pytest tests/contract/                # API contract tests
pytest -m "not slow"                  # Skip slow tests

# Run with coverage
pytest --cov=iris_devtester --cov-report=term-missing

# Lint & Format (run before committing)
black . && isort . && flake8 iris_devtester/ && mypy iris_devtester/
```

## Code Style

### Formatting (pyproject.toml enforced)
- **Line length**: 100 characters
- **Formatter**: black
- **Import sorting**: isort (profile=black)
- **Type checking**: mypy (Python 3.9 target)

### Imports (order matters)
```python
# 1. Standard library
import logging
import os
from typing import Any, Optional

# 2. Third-party
import docker
import pytest

# 3. Local package
from iris_devtester.config import IRISConfig
from iris_devtester.connections.dbapi import create_dbapi_connection
```

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `password_reset.py` |
| Classes | PascalCase | `IRISContainer`, `ConnectionConfig` |
| Functions | snake_case | `get_connection()`, `reset_password()` |
| Constants | UPPER_SNAKE | `HAS_TESTCONTAINERS_IRIS` |
| Private | leading underscore | `_name`, `_container` |
| Test files | `test_*.py` | `test_connection_info.py` |
| Test functions | `test_*` | `test_basic_connection()` |

### Type Hints (required for public APIs)
```python
def get_connection(
    config: Optional[IRISConfig] = None,
    auto_retry: bool = True,
    max_retries: int = 3,
) -> Any:
    """Docstring here."""
```

### Docstrings (Google style)
```python
def reset_password(
    container_name: str,
    username: str,
    new_password: str,
) -> tuple[bool, str]:
    """
    Reset IRIS user password via Docker exec.

    Args:
        container_name: Docker container name or ID
        username: IRIS username to reset
        new_password: New password to set

    Returns:
        Tuple of (success: bool, message: str)

    Raises:
        RuntimeError: If Docker exec fails

    Example:
        >>> success, msg = reset_password("iris_db", "_SYSTEM", "SYS")
        >>> print(msg)
        'Password reset successful'
    """
```

### Error Handling (Constitutional Principle #5)
```python
# WRONG - vague error
raise ConnectionError("Connection failed")

# RIGHT - structured with remediation
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
)
```

### Return Patterns
```python
# Simple success/failure: Tuple[bool, str]
def enable_callin_service(container_name: str) -> tuple[bool, str]:
    return True, "CallIn service enabled"
    return False, "Failed: container not found"

# Rich results: dataclass
@dataclass
class PasswordResetResult:
    success: bool
    message: str
    verification_attempts: int
    elapsed_seconds: float
```

---

## Project Structure

```
iris_devtester/
├── cli/            # Click-based CLI commands
├── config/         # IRISConfig, discovery, YAML loading
├── connections/    # DBAPI connection management
├── containers/     # IRISContainer wrapper, validation
├── fixtures/       # DAT fixture loading/creation
├── integrations/   # LangChain integration
├── ports/          # Port registry for parallel tests
├── testing/        # pytest fixtures, helpers
└── utils/          # password_reset, enable_callin, etc.

tests/
├── unit/           # No Docker, fast (<1s each)
├── integration/    # Real IRIS containers
├── contract/       # API contract tests (TDD)
└── e2e/            # Full workflow tests
```

---

## Test Guidelines

### Test Markers
```python
@pytest.mark.unit           # No external dependencies
@pytest.mark.integration    # Requires Docker/IRIS
@pytest.mark.slow           # >5 seconds
@pytest.mark.contract       # API contract (TDD)
@pytest.mark.enterprise     # Needs IRIS_LICENSE_KEY
```

### Fixtures (from conftest.py)
```python
def test_example(iris_db):           # Function-scoped, fresh container
def test_example(iris_db_shared):    # Module-scoped, shared container
def test_example(iris_container):    # Raw container access
```

### Coverage Requirements
- **Minimum**: 90% (enforced in pyproject.toml)
- **Target**: 95%+ (medical-grade reliability)

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_HOST` | auto-discovered | IRIS hostname |
| `IRIS_PORT` | `1972` | IRIS superserver port |
| `IRIS_NAMESPACE` | `USER` | Default namespace |
| `IRIS_USERNAME` | `_SYSTEM` | Username |
| `IRIS_PASSWORD` | `SYS` | Password |
| `IRIS_LICENSE_KEY` | `~/.iris/iris.key` | Enterprise license path |

---

## Critical Patterns

### DBAPI-First (Constitutional Principle #2)
```python
# Always use DBAPI, no JDBC fallback in modern toolkit
from iris_devtester.connections import get_connection
conn = get_connection()  # DBAPI only, 3x faster
```

### CallIn Service (Required for DBAPI)
```python
# MUST enable before DBAPI connections
from iris_devtester.utils.enable_callin import enable_callin_service
success, msg = enable_callin_service(container_name)
```

### Context Managers (Always use)
```python
# CORRECT
with IRISContainer.community() as iris:
    conn = iris.get_connection()

# WRONG - leaks container
iris = IRISContainer.community()
iris.start()
```

---

## File Editing Restrictions

- **DO NOT** modify `.specify/` directory
- **DO NOT** edit `CHANGELOG.md` without version bump
- **DO NOT** use `as any`, `@ts-ignore` equivalents
- **DO NOT** commit without user request
- **DO NOT** add emoji unless explicitly requested

---

## Agent Skills

The repository exposes core functionality as "Skills" to help AI agents work autonomously.

- **[skill.md](skill.md)** (NEW!) - Hierarchical manifest and operational guidance for all agents.

| Skill | Trigger (Claude) | Trigger (Cursor) | Description |
|-------|------------------|------------------|-------------|
| **Container** | `/container` | `@iris-container` | Start, stop, and check IRIS containers |
| **Connection** | `/connection` | `@iris-connection` | Connect to database, handle auth, retry |
| **Fixture** | `/fixture` | `@iris-fixtures` | Load and manage test data |
| **Troubleshooting** | `/troubleshoot` | `@iris-troubleshooting` | Diagnose and fix common errors |

### Skill Locations
- **Claude Code**: `.claude/commands/*.md`
- **Cursor Rules**: `.cursor/rules/*.mdc`
- **GitHub Copilot**: `.github/copilot-instructions.md`

---

## Operations Requiring Human Approval

- Publishing to PyPI
- Force pushing to main/master
- Deleting IRIS namespaces
- Modifying security/credentials
- Major version bumps

---

## Links

- [README.md](README.md) - Project overview
- [CLAUDE.md](CLAUDE.md) - Claude-specific context
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributor guide
- [CONSTITUTION.md](CONSTITUTION.md) - 8 core principles
- [docs/learnings/](docs/learnings/) - Codified lessons
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues

## Active Technologies
- Markdown (primary), Python 3.9+ (for snippet examples) + None (skills are static documentation) (019-agent-skills)
- File system (git) (019-agent-skills)
- Python 3.9+ + `testcontainers`, `testcontainers-iris`, `docker`, `pydantic` (020-fix-pgwire-issues)
- N/A (Infrastructure layer) (020-fix-pgwire-issues)

## Recent Changes
- 019-agent-skills: Added Markdown (primary), Python 3.9+ (for snippet examples) + None (skills are static documentation)
