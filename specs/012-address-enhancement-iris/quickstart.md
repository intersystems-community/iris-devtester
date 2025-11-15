# Quickstart Guide: DBAPI Package Compatibility

**Feature**: 012-address-enhancement-iris
**Date**: 2025-01-13
**Status**: Design Phase

## Overview

This guide shows how to use iris-devtester with **both** the modern `intersystems-irispython` package and the legacy `intersystems-iris` package. Automatic package detection means **zero code changes** required.

## Scenario 1: Using Modern Package (Recommended)

### Install Modern Package

```bash
# Install the modern IRIS Python package
pip install intersystems-irispython>=5.3.0

# Install iris-devtester
pip install iris-devtester
```

### Use iris-devtester (Zero Config)

```python
from iris_devtester.fixtures import FixtureCreator
from testcontainers_iris import IRISContainer

# Start IRIS container
with IRISContainer.community() as iris:
    # Create DAT fixture - works automatically with modern package
    creator = FixtureCreator(container=iris)

    manifest = creator.create_fixture(
        fixture_id="test-100",
        namespace="USER",
        output_dir="./fixtures/test-100"
    )

    print(f"✅ Created fixture with {len(manifest.tables)} tables")
    # No AttributeError - modern package detected automatically
```

### Verify Package Detection

```python
from iris_devtester.utils.dbapi_compat import get_package_info

# Check which package is being used
info = get_package_info()
print(f"Package: {info.package_name}")
# Output: Package: intersystems-irispython

print(f"Version: {info.version}")
# Output: Version: 5.3.0

print(f"Import path: {info.import_path}")
# Output: Import path: intersystems_iris.dbapi._DBAPI

print(f"Detection time: {info.detection_time_ms:.2f}ms")
# Output: Detection time: 1.23ms
```

**Expected Behavior**:
- ✅ Modern package detected automatically
- ✅ All iris-devtester features work
- ✅ No code changes required
- ✅ Detection completes in <10ms

---

## Scenario 2: Using Legacy Package (Backward Compatibility)

### Install Legacy Package

```bash
# Existing users with legacy package installed
pip install intersystems-iris>=3.0.0

# iris-devtester works without any migration
pip install iris-devtester
```

### Use iris-devtester (Unchanged Code)

```python
from iris_devtester.fixtures import FixtureCreator
from testcontainers_iris import IRISContainer

# Your existing code works exactly as before
with IRISContainer.community() as iris:
    creator = FixtureCreator(container=iris)

    manifest = creator.create_fixture(
        fixture_id="test-100",
        namespace="USER",
        output_dir="./fixtures/test-100"
    )

    print(f"✅ Created fixture with {len(manifest.tables)} tables")
    # Backward compatibility maintained - no changes needed
```

### Verify Package Detection

```python
from iris_devtester.utils.dbapi_compat import get_package_info

info = get_package_info()
print(f"Package: {info.package_name}")
# Output: Package: intersystems-iris

print(f"Version: {info.version}")
# Output: Version: 3.2.0

print(f"Import path: {info.import_path}")
# Output: Import path: iris.irissdk
```

**Expected Behavior**:
- ✅ Legacy package detected automatically
- ✅ Fallback from modern to legacy occurred gracefully
- ✅ Zero breaking changes
- ✅ All existing code works unchanged

---

## Scenario 3: Error Handling - No Package Installed

### What Happens

```python
# No IRIS package installed
from iris_devtester.connections import get_iris_connection

try:
    conn = get_iris_connection()
except ImportError as e:
    print(str(e))
```

### Error Message (Constitutional Format)

```
No IRIS Python package detected

What went wrong:
  Neither intersystems-irispython nor intersystems-iris is installed.
  iris-devtester requires one of these packages for DBAPI connections.

Why this happened:
  iris-devtester uses DBAPI for fast SQL operations (3x faster than JDBC).
  The modern package (intersystems-irispython) or legacy package
  (intersystems-iris) must be installed.

How to fix it:
  Install the modern IRIS Python package:
  → pip install intersystems-irispython>=5.3.0

  Or install the legacy package (backward compatibility):
  → pip install intersystems-iris>=3.0.0

Documentation:
  https://iris-devtester.readthedocs.io/dbapi-packages/
```

**Expected Behavior**:
- ✅ Clear error message with What/Why/How/Docs format
- ✅ Actionable remediation steps
- ✅ Suggests modern package first
- ✅ Mentions legacy package for backward compatibility

---

## Scenario 4: Both Packages Installed (Priority)

### Install Both Packages

```bash
# Install both modern and legacy packages
pip install intersystems-irispython>=5.3.0
pip install intersystems-iris>=3.0.0

pip install iris-devtester
```

### Use iris-devtester

```python
from iris_devtester.utils.dbapi_compat import get_package_info

# Modern package prioritized when both installed
info = get_package_info()
print(f"Package: {info.package_name}")
# Output: Package: intersystems-irispython (NOT legacy)
```

**Expected Behavior**:
- ✅ Modern package selected (priority)
- ✅ Legacy package ignored
- ✅ Best performance (modern package)
- ✅ No ambiguity - clear priority order

---

## Scenario 5: DAT Fixtures with Modern Package

### Load Fixture with Modern Package

```python
from iris_devtester.fixtures import DATFixtureLoader
from testcontainers_iris import IRISContainer

with IRISContainer.community() as iris:
    # Load DAT fixture - automatic package detection
    loader = DATFixtureLoader(container=iris)

    target_ns = iris.get_test_namespace(prefix="TEST")

    result = loader.load_fixture(
        fixture_path="./fixtures/test-100",
        target_namespace=target_ns
    )

    print(f"✅ Loaded {len(result.tables_loaded)} tables")
    print(f"⚡ Elapsed: {result.elapsed_seconds:.2f}s")
    print(f"✅ All checksums validated")

    # Cleanup
    loader.cleanup_fixture(target_ns, delete_namespace=True)
```

**Expected Behavior**:
- ✅ DAT fixture loading works with modern package
- ✅ Same performance as legacy package
- ✅ Checksum validation identical
- ✅ No code changes from legacy version

---

## Scenario 6: Connection Management

### Get Connection (Package-Agnostic)

```python
from iris_devtester.utils.dbapi_compat import get_connection

# Package-agnostic connection - works with both packages
conn = get_connection(
    hostname="localhost",
    port=1972,
    namespace="USER",
    username="_SYSTEM",
    password="SYS"
)

cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")
version = cursor.fetchone()[0]
print(f"IRIS Version: {version}")

conn.close()
```

**Expected Behavior**:
- ✅ Connection succeeds with either package
- ✅ Same DBAPI interface regardless of package
- ✅ Zero code changes needed

---

## Scenario 7: pytest Integration

### Test with Automatic Package Detection

```python
import pytest
from iris_devtester.fixtures import DATFixtureLoader
from testcontainers_iris import IRISContainer

@pytest.fixture
def loaded_fixture():
    """Load DAT fixture - works with both packages."""
    with IRISContainer.community() as iris:
        loader = DATFixtureLoader(container=iris)
        target_ns = iris.get_test_namespace(prefix="TEST")

        result = loader.load_fixture(
            fixture_path="./fixtures/test-100",
            target_namespace=target_ns
        )

        yield result

        # Cleanup
        loader.cleanup_fixture(target_ns, delete_namespace=True)

def test_entity_count(loaded_fixture):
    """Test using loaded fixture - package-agnostic."""
    assert loaded_fixture.success
    assert len(loaded_fixture.tables_loaded) > 0
    # Works regardless of which IRIS package is installed
```

**Expected Behavior**:
- ✅ Tests work with modern package
- ✅ Tests work with legacy package
- ✅ No test code changes required
- ✅ CI/CD works with either package

---

## Scenario 8: Migration from Legacy to Modern

### Step 1: Verify Current State

```python
from iris_devtester.utils.dbapi_compat import get_package_info

# Check which package you're currently using
info = get_package_info()
print(f"Current package: {info.package_name}")
# Output: Current package: intersystems-iris (legacy)
```

### Step 2: Install Modern Package

```bash
# Install modern package alongside legacy (safe)
pip install intersystems-irispython>=5.3.0
```

### Step 3: Verify Modern Package Detected

```python
from iris_devtester.utils.dbapi_compat import get_package_info

# Modern package now prioritized
info = get_package_info()
print(f"Current package: {info.package_name}")
# Output: Current package: intersystems-irispython
```

### Step 4: Test Your Code

```bash
# Run your tests with modern package
pytest

# If all tests pass, uninstall legacy package
pip uninstall intersystems-iris
```

**Expected Behavior**:
- ✅ Modern package takes priority immediately
- ✅ No code changes required
- ✅ All tests continue to pass
- ✅ Better performance with modern package

---

## Scenario 9: Debugging Package Detection

### Check Detection Logs

```python
import logging
from iris_devtester.utils.dbapi_compat import get_package_info

# Enable DEBUG logging to see detection process
logging.basicConfig(level=logging.DEBUG)

# Trigger detection
info = get_package_info()

# Logs show:
# DEBUG: Modern package not available, trying legacy
# INFO: Detected IRIS DBAPI package: intersystems-iris v3.2.0 (legacy)
```

**Expected Behavior**:
- ✅ DEBUG logs show fallback attempts
- ✅ INFO logs show final package selected
- ✅ Transparent detection process
- ✅ Easy to diagnose issues

---

## Scenario 10: Version Validation

### Old Version Error

```python
# intersystems-irispython v5.2.0 installed (too old)
from iris_devtester.utils.dbapi_compat import get_connection

try:
    conn = get_connection(hostname="localhost", port=1972, namespace="USER",
                          username="_SYSTEM", password="SYS")
except ImportError as e:
    print(str(e))
```

### Error Message

```
Package intersystems-irispython version 5.2.0 is incompatible

What went wrong:
  Detected package version does not meet minimum requirements.
  Minimum required: 5.3.0

Why this happened:
  iris-devtester requires specific DBAPI features introduced in v5.3.0.
  Older versions may have incompatible APIs or missing functionality.

How to fix it:
  Upgrade the package:
  → pip install --upgrade intersystems-irispython>=5.3.0

Documentation:
  https://iris-devtester.readthedocs.io/dbapi-packages/
```

**Expected Behavior**:
- ✅ Version validation enforced
- ✅ Clear error message with upgrade instructions
- ✅ Constitutional error format (What/Why/How/Docs)

---

## Performance Comparison

### Detection Overhead

```python
import time
from iris_devtester.utils.dbapi_compat import get_package_info

# First detection (includes import)
start = time.perf_counter()
info = get_package_info()
elapsed_ms = (time.perf_counter() - start) * 1000
print(f"First detection: {elapsed_ms:.2f}ms")
# Output: First detection: 1.23ms

# Subsequent calls (cached)
start = time.perf_counter()
info = get_package_info()
elapsed_ms = (time.perf_counter() - start) * 1000
print(f"Cached detection: {elapsed_ms:.2f}ms")
# Output: Cached detection: 0.01ms
```

**Expected Performance**:
- ✅ First detection: <10ms (NFR-001)
- ✅ Cached access: <0.1ms
- ✅ Negligible overhead

---

## Summary

### For New Projects

**Recommendation**: Use modern package
```bash
pip install intersystems-irispython>=5.3.0
pip install iris-devtester
```

### For Existing Projects

**Recommendation**: No changes required - backward compatible
```bash
# Your existing installation works
pip install iris-devtester  # Uses your existing intersystems-iris
```

### Migration Path

**When ready**: Add modern package, test, remove legacy
```bash
pip install intersystems-irispython>=5.3.0  # Add modern
pytest  # Verify tests pass
pip uninstall intersystems-iris  # Remove legacy (optional)
```

---

## Key Takeaways

1. ✅ **Zero Configuration**: Automatic package detection
2. ✅ **Backward Compatible**: Legacy package still works
3. ✅ **Modern Preferred**: Better performance, active development
4. ✅ **Clear Errors**: Constitutional format with remediation
5. ✅ **Fast Detection**: <10ms overhead
6. ✅ **Transparent**: Logging shows which package used
7. ✅ **Easy Migration**: Add modern package, test, done

---

**Status**: Ready for implementation - All scenarios documented
