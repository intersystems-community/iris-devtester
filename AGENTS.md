# AGENTS.md - AI Agent Configuration

**Version**: 1.0.0
**Standard**: AGENTS.md Specification
**Project**: IRIS DevTools

> **Important**: This file contains ONLY AI-specific operational details. For project overview, architecture, and development practices, see [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [CLAUDE.md](CLAUDE.md).

## Build Commands

```bash
# Install all dependencies (including dev, test, all extras)
pip install -e ".[all,dev,test]"

# Run all tests
pytest

# Run only unit tests (fast, no Docker required)
pytest tests/unit/

# Run integration tests (requires Docker)
pytest tests/integration/

# Run with coverage report
pytest --cov=iris_devtools --cov-report=html --cov-report=term-missing

# Code quality checks (run all before committing)
black . && isort . && flake8 iris_devtools/ && mypy iris_devtools/
```

## Test Execution Notes for AI

- **Integration tests require Docker**: Verify `docker ps` works before running
- **First test run pulls IRIS image**: May take 30-60 seconds
- **Parallel test execution**: Use `pytest -n auto` with pytest-xdist (be aware of resource limits)
- **Non-interactive mode**: All tests run headless, no manual intervention needed

## Environment Variables

Available in runtime (optional, auto-discovered if not set):
- `IRIS_HOST` - IRIS hostname (default: auto-discovered or `localhost`)
- `IRIS_PORT` - IRIS port (default: auto-discovered or `1972`)
- `IRIS_NAMESPACE` - Namespace (default: `USER`)
- `IRIS_USERNAME` - Username (default: `_SYSTEM`)
- `IRIS_PASSWORD` - Password (default: `SYS`, auto-reset if expired)
- `IRIS_LICENSE_KEY` - Path to enterprise license key (default: `~/.iris/iris.key`)

**Note**: iris-devtools auto-discovers IRIS instances and resets passwords automatically. Manual configuration is optional.

## MCP Server Configuration

None currently configured. Future versions may expose:
- IRIS container management MCP server
- Fixture management MCP server
- Schema inspection MCP server

## CI/CD Integration

```yaml
# GitHub Actions: No special configuration needed
# Example:
- name: Run tests
  run: |
    pip install iris-devtester[all]
    pytest tests/

# IRIS container starts automatically via testcontainers
# No Docker-in-Docker or service containers required
```

## Operations Requiring Human Approval

The following operations should NEVER be automated without explicit user approval:
- Publishing to PyPI (`twine upload dist/*`)
- Force pushing to main/master branches
- Deleting IRIS namespaces in production
- Modifying security policies or credentials
- Bumping major version numbers (breaking changes)

## Warnings and Caveats

- **Password reset requires Docker exec access**: Auto-remediation fails if Docker exec is blocked
- **Enterprise edition requires license key**: Examples will skip gracefully if unavailable
- **Container cleanup**: Always use context managers (`with` statements) to ensure cleanup
- **Test isolation**: Each test class should get its own namespace to prevent data pollution

## File Editing Restrictions

- **DO NOT** modify files in `.specify/` directory (Specify.ai managed)
- **DO NOT** edit `CHANGELOG.md` without corresponding version bump
- **DO NOT** modify `pyproject.toml` version without updating `iris_devtools/__init__.py`
- **DO NOT** add emoji to code or documentation unless explicitly requested by user

## Links to Full Documentation

- **Project Overview**: [README.md](README.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Claude-Specific Context**: [CLAUDE.md](CLAUDE.md)
- **Constitutional Principles**: [CONSTITUTION.md](CONSTITUTION.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Codified Learnings**: [docs/learnings/](docs/learnings/)

---

**Reminder**: If information would help a human developer understand the project, it belongs in README.md, not here. This file is for AI operational details only.
