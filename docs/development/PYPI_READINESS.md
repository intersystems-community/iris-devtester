# PyPI Readiness Checklist

**Status**: ❌ NOT READY (As of 2025-10-16)

## Critical Blockers (Must Fix Before Publishing)

### 1. Package Metadata
- [ ] **Author info** - Change from "Your Name" to real name/org
- [ ] **GitHub URLs** - Change "yourusername" to "intersystems-community"
- [ ] **testcontainers-iris dependency** - Package doesn't exist, remove it
- [ ] **Version** - Should be 0.1.0 for first release, not 1.0.0

### 2. Package Functionality
- [ ] **Uncomment imports** in `iris_devtester/__init__.py`
- [ ] **Add CLI entry point** for `iris-devtester` command
- [ ] **Test actual imports** work

### 3. Documentation
- [ ] **Remove broken doc links** from README.md
- [ ] **Create CHANGELOG.md**
- [ ] **Create CONTRIBUTING.md**
- [ ] **Add CLI usage** to README
- [ ] **Create examples/** directory with working examples

### 4. Testing
- [ ] **Run all tests** without IRIS (unit/contract tests)
- [ ] **Document** which tests need IRIS
- [ ] **Create burn-in test** script

## Pre-Release Testing Plan

### Test 1: Fresh Install (Zero-Knowledge Developer)
```bash
# Create clean environment
python -m venv /tmp/test-iris-devtester
source /tmp/test-iris-devtester/bin/activate

# Install from local build
pip install dist/iris_devtester-*.whl

# Try imports
python -c "from iris_devtester.fixtures import FixtureCreator; print('✓ imports work')"

# Try CLI
iris-devtester --help

# Deactivate
deactivate
rm -rf /tmp/test-iris-devtester
```

### Test 2: Fixture Workflow (With IRIS)
```bash
# Assumes IRIS running on localhost:1972

# Create test namespace
python -c "from iris_devtester.connections import get_connection; ..."

# Create fixture
iris-devtester fixture create test-fixture USER ./test-fixture

# Validate fixture
iris-devtester fixture validate ./test-fixture

# Load fixture
iris-devtester fixture load ./test-fixture USER_TEST

# List fixtures
iris-devtester fixture list ./

# Clean up
rm -rf ./test-fixture
```

### Test 3: Connection Auto-Discovery
```python
from iris_devtester.connections import get_connection

# Should auto-discover IRIS on localhost
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")
print(cursor.fetchone())
```

### Test 4: pytest Integration
```python
# test_example.py
import pytest
from iris_devtester.fixtures import DATFixtureLoader

@pytest.mark.dat_fixture("./test-fixture")
def test_with_fixture():
    # Fixture auto-loaded
    from iris_devtester.connections import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM YourTable")
    assert cursor.fetchone()[0] > 0
```

## What's Actually Implemented

✅ **Feature 003**: Connection Manager (DBAPI/JDBC)
✅ **Feature 004**: DAT Fixture Management
✅ **Utilities**: Password reset, unexpire passwords
✅ **CLI**: fixture commands (create/load/validate/list/info)
✅ **pytest plugin**: @pytest.mark.dat_fixture

❌ **Feature 002**: Set Default Stats (not integrated)
❌ **Containers**: IRISContainer wrapper (incomplete)
❌ **Testing**: pytest fixtures (incomplete)

## Recommended First Release Scope

**Version 0.1.0** - DAT Fixture Management Only

Include:
- iris_devtester.fixtures (all classes)
- iris_devtester.connections (basic)
- iris_devtester.utils (password reset)
- CLI: `iris-devtester fixture` commands
- pytest plugin: @pytest.mark.dat_fixture

Exclude (for future releases):
- IRISContainer wrapper
- Feature 002 (performance monitoring)
- Advanced testing utilities

## Pre-Release Steps

1. Fix metadata (author, URLs, dependencies)
2. Set version to 0.1.0
3. Uncomment working imports only
4. Add CLI entry point
5. Create CHANGELOG.md
6. Update README to match actual features
7. Create examples/fixtures/
8. Run burn-in tests
9. Build package: `python -m build`
10. Test on TestPyPI
11. Publish to PyPI

## Post-Release Steps

1. Create GitHub release with tag v0.1.0
2. Update README with PyPI badge
3. Announce on community forums
4. Plan v0.2.0 features

## Timeline Estimate

- Fixes: 2-3 hours
- Testing: 1-2 hours
- Documentation: 1-2 hours
- **Total**: 4-7 hours of focused work

## Decision Needed

**Should we release v0.1.0 with just Feature 004**, or wait to complete all features?

Recommendation: **Release v0.1.0 with Feature 004 only**
- Provides immediate value (.DAT fixtures are unique)
- Gets user feedback early
- Can iterate quickly
- Clear scope, easier to document
