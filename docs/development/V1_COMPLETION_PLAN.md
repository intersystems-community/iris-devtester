# v1.0.0 Completion Plan

**Goal**: Complete all features and release production-ready v1.0.0 to PyPI
**Decision**: User chose option 2 - complete everything first
**Estimated Time**: 2-3 weeks of focused work

## Current Status Summary

### ✅ Complete (Merged to main)
- **Feature 001**: Project Foundation
- **Feature 003**: Connection Manager (DBAPI/JDBC)

### ✅ Complete (Branch: 002-set-default-stats)
- **Feature 002**: Set Default Stats
  - Code: 100% complete
  - Tests: 190+ tests passing
  - **Missing**: Integration tests never run with real IRIS

### ✅ Complete (Branch: 004-dat-fixtures)
- **Feature 004**: DAT Fixture Management
  - Code: 100% complete (48/48 tasks)
  - Tests: 182 tests (155 passing without IRIS, 27 require IRIS)
  - **Missing**: Integration tests never run with real IRIS

### ❌ Incomplete (Not started)
- **Feature 005**: Schema Management (not started)
- **Feature 006**: Container Enhancements (not started)

## Completion Strategy

### Phase 1: Merge & Integration (Week 1)

**Goal**: Get all completed features onto main and passing

#### 1.1 Merge Feature 002 to main
```bash
git checkout main
git merge 002-set-default-stats
# Resolve conflicts if any
```

**Tasks**:
- [ ] Merge Feature 002 branch
- [ ] Run all Feature 002 unit/contract tests
- [ ] Fix any merge conflicts
- [ ] Verify Feature 003 still works

#### 1.2 Merge Feature 004 to main
```bash
git checkout main
git merge 004-dat-fixtures
# Resolve conflicts if any
```

**Tasks**:
- [ ] Merge Feature 004 branch
- [ ] Run all Feature 004 tests (155 passing)
- [ ] Fix any merge conflicts
- [ ] Verify all features integrate

#### 1.3 Run Integration Tests (Critical!)

**Setup IRIS Container**:
```bash
docker run -d --name iris_integration_test \
  -p 1972:1972 -p 52773:52773 \
  -e ISC_CPF_MERGE_FILE=/tmp/iris.cpf \
  containers.intersystems.com/intersystems/iris-community:latest
```

**Run Feature 002 Integration Tests**:
```bash
pytest tests/integration/test_set_default_stats_integration.py -v
```

**Run Feature 004 Integration Tests**:
```bash
pytest tests/integration/test_dat_fixtures_integration.py -v
pytest tests/integration/test_pytest_integration.py -v
pytest tests/integration/test_fixture_performance.py -v
```

**Expected Results**:
- 26 Feature 002 integration tests pass
- 27 Feature 004 integration tests pass
- **Total**: 53 integration tests passing

**Tasks**:
- [x] Start IRIS container (used existing container on port 31972)
- [x] Run Feature 004 integration tests (27 tests)
- [x] Discovered DBAPI limitation - tests use ObjectScript commands
- [x] Document limitation in `docs/learnings/integration-test-dbapi-limitation.md`
- [⏸️] Defer integration test fixes to Phase 2.1 (when IRISContainer wrapper is built)
- [⏸️] Run Feature 002 integration tests (likely same issue)

**Phase 1.3 Results**:
- **Unit tests**: 160 passing ✅ (67 Feature 002 + 93 Feature 004)
- **Contract tests**: 93 passing ✅ (Feature 004)
- **Integration tests**: 3/9 passing (only ones not using ObjectScript)
- **Blocker discovered**: DBAPI cannot execute ObjectScript through SQL
- **Decision**: Defer to Phase 2.1 when IRISContainer wrapper provides ObjectScript support

### Phase 2: Complete Missing Features (Week 2)

#### 2.1 Fix IRISContainer Wrapper

**Current Status**: Incomplete, referenced in README but not working

**Files to fix**:
- `iris_devtester/containers/iris_container.py`
- `iris_devtester/containers/__init__.py`

**Requirements**:
- Wrap testcontainers for IRIS
- Auto-password reset integration
- Community & Enterprise support
- Wait strategies

**Tests**:
- [ ] Unit tests for IRISContainer
- [ ] Integration tests with real container
- [ ] Enterprise edition test (if license available)

**Estimated**: 8-10 hours

#### 2.2 Complete Testing Utilities

**Current Status**: Incomplete, basic fixtures exist

**Files to complete**:
- `iris_devtester/testing/fixtures.py`
- `iris_devtester/testing/schema_reset.py`

**Requirements**:
- `iris_test_fixture()` - pytest fixture for IRIS
- Schema reset/validation helpers
- Test isolation helpers

**Tests**:
- [ ] Unit tests for utilities
- [ ] Integration tests with pytest

**Estimated**: 6-8 hours

#### 2.3 Feature 005: Schema Management (Optional for v1.0.0)

**Scope** (from PROGRESS.md):
- Schema discovery and validation
- Schema migration tools
- SQL DDL helpers
- Table/class validation
- Index management

**Decision Point**: Include in v1.0.0 or defer to v1.1.0?

**Recommendation**: **Defer to v1.1.0**
- Not critical for launch
- Can iterate based on user feedback
- Significant additional work (30-40 hours)

#### 2.4 Feature 006: Container Enhancements (Optional for v1.0.0)

**Scope** (from PROGRESS.md):
- Enhanced IRISContainer wrapper
- Wait strategies (health checks)
- Enterprise edition support
- License key management
- Network configuration

**Decision Point**: Include in v1.0.0 or defer to v1.1.0?

**Recommendation**: **Include minimal version in v1.0.0**
- Complete IRISContainer basic wrapper (from 2.1)
- Defer advanced features to v1.1.0

### Phase 3: Package Preparation (Week 2-3)

#### 3.1 Fix Package Metadata

**pyproject.toml fixes**:
- [ ] Remove `testcontainers-iris>=1.2.2` (doesn't exist)
- [ ] Update author info
- [ ] Update URLs to intersystems-community
- [ ] Add CLI entry point
- [ ] Verify all dependencies

**iris_devtester/__init__.py fixes**:
- [ ] Uncomment working imports
- [ ] Expose public API
- [ ] Update version to 1.0.0
- [ ] Update docstrings

**Estimated**: 2 hours

#### 3.2 Create Documentation

**README.md** - Complete rewrite:
- [ ] Feature overview (what's actually included)
- [ ] Installation instructions
- [ ] Quick start examples (that work!)
- [ ] CLI documentation
- [ ] pytest plugin usage
- [ ] Connection management
- [ ] Fixture management
- [ ] Troubleshooting

**CHANGELOG.md** - Create:
```markdown
# Changelog

## [1.0.0] - 2025-10-XX

### Added
- Feature 002: IRIS performance monitoring (^SystemPerformance)
- Feature 003: Connection manager (DBAPI-first, JDBC fallback)
- Feature 004: .DAT fixture management
- CLI: `iris-devtester fixture` commands
- pytest plugin: @pytest.mark.dat_fixture
- Automatic password reset utilities
- Zero-config IRIS discovery

### Fixed
- Password reset now properly disables ChangePassword flag
- DBAPI authentication works after password reset

### Documentation
- Complete API documentation
- CLI usage guide
- pytest integration guide
- Troubleshooting guide
```

**CONTRIBUTING.md** - Create:
- [ ] Development setup
- [ ] Running tests
- [ ] Code style
- [ ] PR process
- [ ] Constitutional principles

**examples/** - Create:
- [ ] examples/connections/basic_connection.py
- [ ] examples/fixtures/create_fixture.py
- [ ] examples/fixtures/load_fixture.py
- [ ] examples/pytest/test_with_fixtures.py
- [ ] examples/monitoring/set_default_stats.py

**Estimated**: 8-10 hours

#### 3.3 Burn-In Testing

**Test 1: Fresh Install**
```bash
# Clean environment
python -m venv /tmp/burnin-test
source /tmp/burnin-test/bin/activate

# Build and install
cd /Users/tdyar/ws/iris-devtester
python -m build
pip install dist/iris_devtester-1.0.0-py3-none-any.whl

# Test imports
python -c "from iris_devtester.connections import get_connection"
python -c "from iris_devtester.fixtures import FixtureCreator"

# Test CLI
iris-devtester --help
iris-devtester fixture --help

# Cleanup
deactivate
rm -rf /tmp/burnin-test
```

**Test 2: Zero-Knowledge Developer Workflow**

Create a test script that simulates a developer with no IRIS knowledge:

```python
# test_zero_knowledge.py
"""
Simulates a developer who knows nothing about IRIS
following our README.md to get started.
"""

# Step 1: Import (from README quickstart)
from iris_devtester.containers import IRISContainer

# Step 2: Create container (from README)
with IRISContainer.community() as iris:
    # Step 3: Get connection (from README)
    conn = iris.get_connection()

    # Step 4: Use connection (from README)
    cursor = conn.cursor()
    cursor.execute("SELECT $ZVERSION")
    print(f"✓ IRIS Version: {cursor.fetchone()[0]}")

    # Step 5: Test fixtures (from README)
    from iris_devtester.fixtures import FixtureCreator
    creator = FixtureCreator()
    # ... etc
```

**Tasks**:
- [ ] Create burn-in test suite
- [ ] Run as zero-knowledge developer
- [ ] Document any confusing parts
- [ ] Fix documentation based on findings
- [ ] Iterate until smooth experience

**Estimated**: 4-6 hours

### Phase 4: Release (Week 3)

#### 4.1 Final Testing
- [ ] Run full test suite (all features)
- [ ] Check test coverage (target: 95%+)
- [ ] Run mypy type checking
- [ ] Run code formatters (black, isort)
- [ ] Fix all warnings

#### 4.2 Build Package
```bash
python -m build
```

**Verify**:
- [ ] Check dist/ contains .whl and .tar.gz
- [ ] Inspect wheel contents
- [ ] Verify metadata

#### 4.3 Test on TestPyPI
```bash
python -m twine upload --repository testpypi dist/*
```

**Test install**:
```bash
pip install --index-url https://test.pypi.org/simple/ iris-devtester
```

**Tasks**:
- [ ] Upload to TestPyPI
- [ ] Test installation
- [ ] Verify CLI works
- [ ] Verify imports work
- [ ] Fix any issues

#### 4.4 Release to PyPI
```bash
python -m twine upload dist/*
```

**Tasks**:
- [ ] Upload to PyPI
- [ ] Test installation: `pip install iris-devtester`
- [ ] Create GitHub release
- [ ] Tag version: `git tag v1.0.0`
- [ ] Push tags: `git push --tags`

#### 4.5 Announce
- [ ] Update README with PyPI badge
- [ ] Post to InterSystems Developer Community
- [ ] Tweet (if applicable)
- [ ] LinkedIn post (if applicable)

## Risk Assessment

### High Risks
1. **Integration tests may fail** - Never run with real IRIS
   - Mitigation: Run early, allocate debug time
   - Impact: 1-2 days delay

2. **IRISContainer may need significant work** - Currently incomplete
   - Mitigation: Use testcontainers directly, minimal wrapper
   - Impact: May need to descope for v1.0.0

3. **testcontainers-iris doesn't exist** - Referenced in code
   - Mitigation: Use testcontainers-python directly
   - Impact: 4-6 hours rework

### Medium Risks
1. **Documentation takes longer than expected**
   - Mitigation: Focus on critical paths first
   - Impact: 1-2 days delay

2. **Burn-in test reveals UX issues**
   - Mitigation: Iterate quickly on docs/examples
   - Impact: 1 day delay

## Timeline

**Week 1** (40 hours):
- Day 1-2: Merge features, resolve conflicts
- Day 3-4: Run integration tests, fix issues
- Day 5: Complete IRISContainer wrapper

**Week 2** (40 hours):
- Day 1-2: Complete testing utilities
- Day 3-4: Fix package metadata, documentation
- Day 5: Create examples

**Week 3** (40 hours):
- Day 1-2: Burn-in testing, iterate
- Day 3: Final testing, build
- Day 4: TestPyPI, fixes
- Day 5: PyPI release, announce

**Total**: 120 hours (~3 weeks full-time)

## Success Criteria

### Code Quality
- [ ] All 407+ tests passing
- [ ] 95%+ test coverage
- [ ] mypy clean
- [ ] No flake8 warnings

### Documentation
- [ ] README accurate (no broken examples)
- [ ] All CLI commands documented
- [ ] Examples work out-of-box
- [ ] Troubleshooting guide complete

### Package
- [ ] Installs cleanly: `pip install iris-devtester`
- [ ] CLI works: `iris-devtester --help`
- [ ] Imports work
- [ ] Zero-config viable

### User Experience
- [ ] Zero-knowledge developer can get started in <5 minutes
- [ ] All 8 Constitutional Principles satisfied
- [ ] Error messages helpful
- [ ] Examples run without modification

## Next Steps

1. **User confirmation**: Does this plan look good?
2. **Start with Phase 1.1**: Merge Feature 002 to main
3. **Work through phases sequentially**
4. **Iterate based on findings**

## Notes

- Features 005 & 006 can be deferred to v1.1.0
- Focus on quality over quantity
- Every feature must work perfectly
- Documentation is as important as code
