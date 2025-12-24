# Contributing to IRIS DevTools

Thank you for considering contributing to IRIS DevTools! This project embodies years of production experience with InterSystems IRIS, and we welcome contributions that build on that foundation.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Bug reports are tracked as GitHub Issues. When creating a bug report:
1. Use the bug report template
2. Include iris-devtester version, Python version, IRIS edition
3. Provide minimal reproduction steps
4. Include relevant log output

### Suggesting Enhancements

Feature requests are also tracked as GitHub Issues. When suggesting enhancements:
1. Use the feature request template
2. Explain the problem this feature would solve
3. Describe your proposed solution
4. Consider alternatives and trade-offs

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following our development guidelines (below)
4. Run tests and linters
5. Submit a pull request using the PR template

## Development Setup

### Prerequisites
- Python 3.9+
- Docker Desktop
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/intersystems-community/iris-devtester.git
cd iris-devtester

# Install in development mode with all dependencies
pip install -e ".[all,dev,test]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit/

# Integration tests only (requires Docker)
pytest tests/integration/

# With coverage report
pytest --cov=iris_devtools --cov-report=html
```

### Code Style

This project uses:
- **black** (line length 100)
- **isort** (compatible with black)
- **mypy** (type checking)
- **flake8** (linting)

Run all checks:
```bash
black .
isort .
mypy iris_devtools/
flake8 iris_devtools/
pytest
```

Pre-commit hooks will run these automatically.

## Project Structure

```
iris_devtools/
├── connections/    # DBAPI/JDBC connection management
├── containers/     # Testcontainers wrapper with auto-remediation
├── testing/        # pytest fixtures and utilities
├── config/         # Configuration discovery
└── cli/            # CLI commands

tests/
├── unit/           # Unit tests (no external dependencies)
├── integration/    # Integration tests (require IRIS container)
└── e2e/            # End-to-end workflow tests

docs/
└── learnings/      # Production insights and "why not X?" docs
```

## Testing Guidelines

### Test Coverage Requirements
- Minimum: 95% overall coverage
- All error paths must be tested
- All public APIs must have tests

### Test Organization
- **Unit tests**: Mock external dependencies (IRIS, Docker)
- **Integration tests**: Use real IRIS containers via testcontainers
- **E2E tests**: Full workflow validation

### Writing Tests

Follow these patterns:

```python
# Unit test example
def test_connection_config_parsing():
    """Unit test - no external dependencies"""
    config = ConnectionConfig.from_dict({"host": "localhost"})
    assert config.host == "localhost"

# Integration test example
@pytest.mark.integration
def test_iris_connection(iris_container):
    """Integration test - uses real IRIS"""
    conn = iris_container.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

## Constitutional Compliance

All contributions must follow the [8 Constitutional Principles](CONSTITUTION.md):

1. **Automatic Remediation Over Manual Intervention** - No "run this command" errors
2. **Choose the Right Tool** - DBAPI for SQL, iris.connect() for ObjectScript
3. **Isolation by Default** - Each test gets its own container/namespace
4. **Zero Configuration Viable** - `pip install && pytest` must work
5. **Fail Fast with Guidance** - Errors include "what went wrong" + "how to fix it"
6. **Enterprise Ready, Community Friendly** - Support both editions
7. **Medical-Grade Reliability** - 95%+ coverage, all error paths tested
8. **Document the Blind Alleys** - Add to `docs/learnings/` when you discover "why not X"

**Before submitting a PR**, verify your changes align with these principles.

## Governance

### Maintainers
- Primary maintainers listed in pyproject.toml
- Governance model: Benevolent Dictator For Life (BDFL) with community input

### Decision Process
1. Propose changes via GitHub Issues or Discussions
2. Gather community feedback (1-2 weeks for major changes)
3. Maintainers make final decision based on:
   - Constitutional alignment
   - Production evidence
   - Community consensus
   - Backwards compatibility

### Release Process
- Semantic versioning (MAJOR.MINOR.PATCH)
- CHANGELOG updated for all releases
- Git tags for all versions
- PyPI releases automated via CI

## Documentation Contributions

### Adding to docs/learnings/

When you discover a "blind alley" (something that didn't work), document it:

1. Create `docs/learnings/your-learning.md`
2. Use this template:
```markdown
# Learning: [Title]

## Problem
[What you were trying to solve]

## What We Tried
[Approach that didn't work]

## Why It Didn't Work
[Root cause, with evidence]

## What We Did Instead
[Successful approach]

## Evidence
[Benchmarks, logs, test results]

## Date
[When this was discovered]
```

### Updating API Documentation

- All public APIs need Google-style docstrings
- Include a minimal working example in each docstring
- Document all parameters and return values
- Specify any exceptions raised

## Questions?

- **General questions**: GitHub Discussions
- **Bug reports**: GitHub Issues (use template)
- **Feature requests**: GitHub Issues (use template)
- **Security issues**: See [SECURITY.md](SECURITY.md)

## Thank You!

Your contributions make this project better for everyone. Every principle in our constitution was learned through production debugging—your contribution helps others avoid those same pitfalls.
