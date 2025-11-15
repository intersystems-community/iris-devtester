# Test Isolation Investigation - Password Reset Integration Tests

**Date**: 2025-01-15
**Status**: In Progress
**Impact**: 4 tests failing due to test isolation issue

## Problem Summary

Password reset integration tests (`tests/integration/test_password_reset_integration.py`) have a test isolation issue:
- ✅ Each test PASSES when run individually
- ❌ When run together, only the FIRST test passes
- ❌ Tests 2, 3, 4 FAIL during fixture setup with "Access Denied" error

## Investigation Timeline

### Initial Discovery
- Full test suite reported "22 errors" after Feature 012 integration
- Breakdown: 18 coverage errors (not real test failures) + 4 real test failures
- 18 coverage errors from `pytest-cov` when coverage < 90% (misleading "ERROR" status)
- Only 4 real test failures in password reset integration tests

### Attempted Fixes

#### Fix #1: Enable CallIn Service (✅ Partial Success)
- **Change**: Added `enable_callin_service()` to `iris_db` and `iris_container` fixtures
- **Result**: Fixed potential CallIn issues for all integration tests
- **Impact**: Monitor tests now pass (18/18 ✅), but password reset tests still fail

#### Fix #2: Update to DBAPI Compatibility Layer (✅ Success)
- **Change**: Replaced direct `irisnative` imports with `dbapi_compat.get_connection()`
- **Files**: `tests/conftest.py`, `tests/integration/test_password_reset_integration.py`
- **Result**: Successfully integrated Feature 012 into test fixtures
- **Impact**: Tests now use compatibility layer correctly

#### Fix #3: Increase Wait Time (❌ No Effect)
- **Change**: Increased sleep from 2s → 5s after CallIn enablement
- **Result**: No improvement - still 3 failures
- **Conclusion**: NOT a timing/race condition issue

#### Fix #4: Explicit Container Cleanup (❌ Failed - Double Cleanup)
- **Change**: Tried adding explicit `container.stop()` and `container.remove()` in fixture cleanup
- **Result**: Error - testcontainers context manager ALSO tries to cleanup, causing "404 Not Found"
- **Conclusion**: Context manager already handles cleanup, but something is wrong with the cleanup process

### Root Cause Identified

**Key Finding**: testcontainers ryuk cleanup sidecar still running after test 1 completes

```bash
$ docker ps -a --filter "label=org.testcontainers=true"
a21e7aa5d0e4	testcontainers-ryuk-978f3202-1761-4b1f-ad9f-5b1772b4327b	Up 16 seconds
```

The ryuk sidecar is testcontainers' cleanup mechanism. It should:
1. Monitor containers with testcontainers labels
2. Clean them up when the testcontainers session ends
3. Exit after cleanup completes

**But**: Ryuk is still running AFTER test 1 completes, suggesting:
- Containers from test 1 not fully cleaned up before test 2 starts
- Test 2 might be connecting to test 1's container instead of its own
- pytest fixture scope might not be properly isolated

### Evidence

#### Stdout Capture Anomaly
When test 2 fails, pytest shows captured stdout that includes output from test 1:

```
---------------------------- Captured stdout setup -----------------------------
res iris session iris -U %SYS '##class(Security.Users).Create("_SYSTEM","%ALL","TESTPWD123")' ExecResult(exit_code=0, output=b'')
```

This is the `Create("_SYSTEM")` call with password `"TESTPWD123"` from test 1.
It appears in test 2's "Captured stdout setup" section.

**Why**: pytest captures stdout during each test but only displays it when a test fails.
So test 2's failure shows BOTH test 2's stdout AND leftover stdout from test 1.

#### Connection Failure Pattern
- Test 2 fixture tries to connect with `username="test"`, `password="test"`
- Gets "Access Denied" error
- CallIn service IS enabled (confirmed working)
- User creation command runs successfully (visible in stdout)
- But connection still fails

**Hypothesis**: Test 2's fixture might be trying to connect to test 1's container, where the `_SYSTEM` password was changed by test 1.

## Test Fixture Structure

```python
@pytest.fixture(scope="function")
def iris_db():
    """Function-scoped IRIS container and connection."""
    with IRISContainer() as iris:
        # Enable CallIn
        enable_callin_service(container_name, timeout=30)
        time.sleep(5)  # Wait for CallIn + user creation

        # Connect as "test" user
        conn = get_connection(
            hostname=host,
            port=port,
            namespace="USER",
            username="test",  # Created by testcontainers-iris
            password="test",
        )

        yield conn

        # Cleanup
        conn.close()
    # Context manager should cleanup container
```

**Expected Behavior**: Each test gets a completely fresh IRIS container
**Actual Behavior**: Tests appear to be sharing containers or cleanup is incomplete

## Theories

### Theory #1: Ryuk Cleanup Timing
- Ryuk might take time to cleanup containers after context manager exits
- Test 2's fixture might start BEFORE test 1's containers are fully removed
- Solution: Add explicit wait for ryuk to complete cleanup

### Theory #2: pytest-asyncio Interference
- pytest-asyncio might be causing fixture setup/teardown to overlap
- Solution: Disable pytest-asyncio for these specific tests with `-p no:asyncio`
- **Tested**: Disabling asyncio made NO difference

### Theory #3: Container Reuse Bug
- testcontainers might be reusing containers instead of creating new ones
- Solution: Force unique container names per test

### Theory #4: Fixture Scope Issue
- Function scope might not be fully isolated in pytest
- Solution: Try session scope with explicit cleanup between tests

## Next Steps

1. **Verify ryuk cleanup timing** - Add explicit wait for containers to be removed
2. **Force unique container names** - Ensure each test gets truly unique container
3. **Debug container lifecycle** - Add logging to see when containers are created/destroyed
4. **Try alternative cleanup strategy** - Maybe bypass ryuk for these specific tests

## Workaround

Current workaround: Run password reset tests individually
All 4 tests PASS when run alone:

```bash
pytest tests/integration/test_password_reset_integration.py::TestResetPasswordIntegration::test_reset_password_actually_sets_password -xvs --no-cov  # PASSES
pytest tests/integration/test_password_reset_integration.py::TestResetPasswordIntegration::test_reset_password_connection_succeeds -xvs --no-cov  # PASSES
pytest tests/integration/test_password_reset_integration.py::TestResetPasswordIntegration::test_reset_password_sets_password_never_expires -xvs --no-cov  # PASSES
pytest tests/integration/test_password_reset_integration.py::TestResetPasswordIntegration::test_reset_password_idempotent -xvs --no-cov  # PASSES
```

## References

- testcontainers ryuk documentation: https://github.com/testcontainers/moby-ryuk
- pytest fixture scopes: https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session
- testcontainers-iris source: `/opt/homebrew/Caskroom/miniconda/base/lib/python3.12/site-packages/testcontainers/iris/__init__.py`

## Constitutional Compliance

**Principle #3: Isolation by Default** - Currently VIOLATED
Each test should get its own database, but tests are interfering with each other.

**Principle #7: Medical-Grade Reliability** - Currently AT RISK
Test isolation failures undermine test reliability and could mask real bugs.
