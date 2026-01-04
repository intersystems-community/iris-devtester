# Getting Started with IRIS DevTools Development

**Status**: Ready for implementation
**Date**: 2025-10-05

## What Is This?

This is a **NEW** Python package being created to provide battle-tested InterSystems IRIS infrastructure for Python developers. We're extracting proven code from `~/ws/rag-templates/` and packaging it for reuse across all IRIS projects.

## Quick Context

### The Problem We're Solving

Every IRIS + Python project encounters the same issues:
- Password expiration in Docker containers
- Connection management (DBAPI vs JDBC)
- Test isolation and cleanup
- Schema management
- CallIn service configuration

### The Solution

Extract all the working solutions from `rag-templates` into a reusable package that can be `pip install`ed.

## Current Status

✅ **Foundation Complete**:
- Package structure created
- Constitutional principles defined (8 core rules)
- Dependencies configured
- Documentation structure ready
- Git initialized with first commit

🚧 **Ready to Build**:
- Connection management (extract from rag-templates)
- Password reset utilities (extract from rag-templates)
- Testcontainers integration (build on testcontainers-iris)
- Testing utilities (extract from rag-templates)
- Configuration system (new)

## File Structure

```
~/ws/iris-devtester/
├── .specify/
│   └── feature-request.md       # Complete implementation spec
├── iris_devtester/               # Package code (EMPTY - ready to fill)
│   ├── __init__.py             # Entry point
│   ├── connections/            # To extract from rag-templates
│   ├── containers/             # To build
│   ├── testing/                # To extract from rag-templates
│   ├── config/                 # To build
│   └── utils/                  # To build
├── tests/                       # Test suite (EMPTY - ready to fill)
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   └── learnings/
│       └── callin-service-requirement.md  # First documented learning
├── examples/                    # Usage examples (EMPTY)
├── CONSTITUTION.md              # 8 core principles (MANDATORY)
├── CLAUDE.md                    # Development guide
├── README.md                    # User documentation
├── pyproject.toml              # Package configuration
└── LICENSE                     # MIT

Source material: ~/ws/rag-templates/
```

## Key Documents to Read

Before coding, read these **in order**:

1. **CONSTITUTION.md** - The 8 non-negotiable principles
   - Automatic remediation
   - DBAPI-first
   - Isolation by default
   - Zero-config viable
   - Fail fast with guidance
   - Enterprise ready
   - Medical-grade reliability
   - Document blind alleys

2. **.specify/feature-request.md** - What to build
   - Complete module breakdown
   - Files to extract
   - Success criteria

3. **CLAUDE.md** - How to develop
   - Code patterns
   - Testing requirements
   - Common tasks

4. **docs/learnings/callin-service-requirement.md** - Critical IRIS detail
   - DBAPI requires CallIn service enabled
   - How to enable automatically

## Next Steps for Implementation

### Recommended Order

1. **Start with Connection Manager** (most critical)
   - Extract from: `~/ws/rag-templates/common/iris_connection_manager.py`
   - Place in: `iris_devtester/connections/manager.py`
   - Add: DBAPI-first, JDBC fallback, auto-recovery

2. **Add Password Reset** (enables auto-remediation)
   - Extract from: `~/ws/rag-templates/tests/utils/iris_password_reset.py`
   - Place in: `iris_devtester/connections/recovery.py`
   - Add: Automatic detection, Docker exec reset

3. **Build Container Wrapper** (testcontainers integration)
   - Extend: `testcontainers.iris.IRISContainer`
   - Place in: `iris_devtester/containers/iris_container.py`
   - Add: Auto password reset, CallIn enablement, better wait strategies

4. **Extract Testing Utilities** (pytest fixtures)
   - Extract from: `~/ws/rag-templates/tests/` (Feature 028)
   - Place in: `iris_devtester/testing/`
   - Add: fixtures.py, schema_manager.py, cleanup.py, state.py

5. **Add Configuration** (auto-discovery)
   - Build: `iris_devtester/config/discovery.py`
   - Add: Environment detection, .env support, sensible defaults

6. **Write Tests** (95% coverage required)
   - Unit tests: Mock dependencies
   - Integration tests: Real IRIS containers
   - E2E tests: Full workflows

## Using /specify

When ready to implement, run:

```bash
cd ~/ws/iris-devtester
# Start new Claude Code session here

# Then use /specify
/specify "Implement iris-devtester following the feature request in .specify/feature-request.md"
```

The `/specify` workflow will:
1. Read the feature request
2. Create a plan
3. Generate tasks
4. Guide implementation

## Quick Reference

### Source Code Locations (in rag-templates)

Extract from these files:

```
~/ws/rag-templates/
├── common/
│   └── iris_connection_manager.py   # → connections/manager.py
├── tests/
│   ├── utils/
│   │   ├── iris_password_reset.py   # → connections/recovery.py
│   │   ├── preflight_checks.py      # → testing/preflight.py
│   │   ├── schema_validator.py      # → testing/schema_manager.py
│   │   └── schema_models.py         # → testing/models.py
│   ├── fixtures/
│   │   ├── schema_reset.py          # → testing/schema_manager.py
│   │   ├── database_cleanup.py      # → testing/cleanup.py
│   │   └── database_state.py        # → testing/state.py
│   └── conftest.py                  # → testing/fixtures.py (Feature 028 sections)
```

### Testing Commands

```bash
# Install in dev mode
pip install -e ".[dev,test,all]"

# Run tests
pytest

# With coverage
pytest --cov=iris_devtester --cov-report=html

# Format code
black . && isort .
```

### Constitutional Compliance Checklist

Before submitting code:

- [ ] Automatic remediation implemented (no manual steps)
- [ ] DBAPI tried first, JDBC fallback
- [ ] Tests are isolated (containers or unique namespaces)
- [ ] Zero-config works (sensible defaults)
- [ ] Error messages include remediation steps
- [ ] Both Community & Enterprise editions supported
- [ ] 95%+ test coverage
- [ ] Blind alleys documented

## Expected Timeline

- **Week 1**: Connection management + password reset
- **Week 2**: Testcontainers integration + testing utilities
- **Week 3**: Configuration + documentation + tests
- **Week 4**: PyPI publishing + rag-templates migration

## Success Criteria

✅ **Package works**:
```python
from iris_devtester.containers import IRISContainer
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # Just works - no configuration needed!
```

✅ **rag-templates migrates successfully**:
```bash
cd ~/ws/rag-templates
pip uninstall <local-iris-code>
pip install iris-devtester
# All 771 tests still pass
```

✅ **PyPI published**:
```bash
pip install iris-devtester
```

## Questions?

- **What to build?** → `.specify/feature-request.md`
- **How to build it?** → `CLAUDE.md`
- **Why these rules?** → `CONSTITUTION.md`
- **Critical IRIS detail?** → `docs/learnings/callin-service-requirement.md`

---

**You're ready to start a new Claude Code session and use `/specify`!**

Open a new terminal:
```bash
cd ~/ws/iris-devtester
# Start Claude Code here
# Use: /specify "Implement iris-devtester following .specify/feature-request.md"
```
