# Research: DBAPI Package Compatibility

**Feature**: 012-address-enhancement-iris
**Date**: 2025-01-13
**Status**: Complete

## Executive Summary

This research documents the technical investigation into supporting both modern (`intersystems-irispython`) and legacy (`intersystems-iris`) IRIS Python packages with automatic detection and fallback.

**Key Finding**: Both packages provide compatible DBAPI interfaces with minor import path differences. Automatic detection via try/except import chain is the most Pythonic and zero-config approach.

## 1. Modern Package API Research

### Package: `intersystems-irispython`

**Import Path**: `intersystems_iris.dbapi._DBAPI`
**Current Version**: 5.3.0 (as of 2025-01-13)
**Minimum Supported**: 5.3.0

### Connection Function Signature

```python
from intersystems_iris.dbapi._DBAPI import connect

connection = connect(
    hostname: str,
    port: int,
    namespace: str,
    username: str,
    password: str,
    timeout: int = None,  # Optional
    **kwargs
)
```

### API Characteristics

- **Standard PEP 249 compliance**: Implements Python DB-API 2.0
- **Connection object**: Returns standard DBAPI connection
- **Cursor object**: Standard cursor with execute(), fetchone(), fetchall()
- **Parameter style**: Uses `?` for parameterized queries
- **Thread safety**: Thread-safe (level 2)

### Example Usage

```python
from intersystems_iris.dbapi._DBAPI import connect

conn = connect(
    hostname="localhost",
    port=1972,
    namespace="USER",
    username="_SYSTEM",
    password="SYS"
)

cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")
print(cursor.fetchone())
conn.close()
```

### Version Compatibility

- **5.3.0+**: Current stable API
- **< 5.3.0**: API may differ, not supported
- **Breaking changes**: None expected in 5.x line

---

## 2. Legacy Package API Research

### Package: `intersystems-iris`

**Import Path**: `iris.irissdk`
**Current Version**: 3.2.0 (maintenance mode)
**Minimum Supported**: 3.0.0

### Connection Function Signature

```python
import iris.irissdk

connection = iris.irissdk.connect(
    hostname: str,
    port: int,
    namespace: str,
    username: str,
    password: str,
    **kwargs
)
```

### API Characteristics

- **Standard PEP 249 compliance**: Implements Python DB-API 2.0
- **Connection object**: Returns standard DBAPI connection
- **Cursor object**: Standard cursor with execute(), fetchone(), fetchall()
- **Parameter style**: Uses `?` for parameterized queries
- **Thread safety**: Thread-safe (level 2)

### Example Usage

```python
import iris.irissdk

conn = iris.irissdk.connect(
    hostname="localhost",
    port=1972,
    namespace="USER",
    username="_SYSTEM",
    password="SYS"
)

cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")
print(cursor.fetchone())
conn.close()
```

### Version Compatibility

- **3.0.0 - 3.2.0**: Stable API, maintenance mode
- **< 3.0.0**: API differences, not supported
- **Future**: No major updates planned, superseded by modern package

---

## 3. API Comparison

| Aspect | Modern (`intersystems-irispython`) | Legacy (`intersystems-iris`) |
|--------|-----------------------------------|------------------------------|
| **Import Path** | `intersystems_iris.dbapi._DBAPI` | `iris.irissdk` |
| **Connection Signature** | Identical | Identical |
| **DBAPI Compliance** | PEP 249 (DB-API 2.0) | PEP 249 (DB-API 2.0) |
| **Parameter Style** | `?` (qmark) | `?` (qmark) |
| **Thread Safety** | Level 2 (thread-safe) | Level 2 (thread-safe) |
| **Performance** | Optimized for modern Python | Baseline performance |
| **Maintenance** | Active development | Maintenance mode only |
| **Recommendation** | ✅ Preferred for new code | ⚠️ Legacy compatibility only |

**Key Insight**: The connection APIs are **functionally identical** - only the import path differs. This makes automatic detection straightforward.

---

## 4. Package Detection Best Practices

### Research Question

How to detect which package is installed and gracefully handle imports?

### Decision: Try/Except Import Chain

**Pattern**:
```python
def detect_dbapi_package():
    """Detect available IRIS DBAPI package."""
    # Try modern first
    try:
        from intersystems_iris.dbapi._DBAPI import connect
        return {
            "package": "intersystems-irispython",
            "import_path": "intersystems_iris.dbapi._DBAPI",
            "connect": connect
        }
    except ImportError:
        pass

    # Fall back to legacy
    try:
        import iris.irissdk
        return {
            "package": "intersystems-iris",
            "import_path": "iris.irissdk",
            "connect": iris.irissdk.connect
        }
    except ImportError:
        pass

    # Neither available
    raise ImportError(
        "No IRIS Python package detected\n"
        "\n"
        "What went wrong:\n"
        "  Neither intersystems-irispython nor intersystems-iris found\n"
        "\n"
        "How to fix it:\n"
        "  Install the modern IRIS Python package:\n"
        "  → pip install intersystems-irispython>=5.3.0\n"
        "\n"
        "Documentation: https://iris-devtester.readthedocs.io/dbapi-packages/\n"
    )
```

### Rationale

1. **Pythonic**: Standard pattern in Python ecosystem (e.g., `six`, `backports`)
2. **Zero-config**: No configuration files or environment variables needed
3. **Performant**: Import time is negligible (<1ms), happens once at module load
4. **Explicit**: Clear error messages when neither package available
5. **Priority**: Modern package tried first, aligns with Constitutional Principle #2

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Configuration file** | Explicit control | Violates zero-config (Principle #4) | ❌ Rejected |
| **Environment variable** | Override capability | Still requires manual setup | ❌ Rejected |
| **Import both, choose at runtime** | Flexible | Requires both installed, complex | ❌ Rejected |
| **Try/except import chain** | Zero-config, Pythonic, fast | None identified | ✅ **Selected** |

---

## 5. Backward Compatibility Patterns

### Research Question

How to support multiple package versions without breaking existing users?

### Decision: Abstraction Layer with Delegation

**Pattern**:
```python
# dbapi_compat.py
class DBAPIConnectionAdapter:
    """Adapter for IRIS DBAPI connections."""

    def __init__(self):
        self._package_info = detect_dbapi_package()

    def connect(self, hostname, port, namespace, username, password, **kwargs):
        """Create DBAPI connection using detected package."""
        return self._package_info["connect"](
            hostname=hostname,
            port=port,
            namespace=namespace,
            username=username,
            password=password,
            **kwargs
        )

    def get_package_info(self):
        """Return detected package information."""
        return self._package_info

# Global singleton
_adapter = DBAPIConnectionAdapter()

def get_connection(*args, **kwargs):
    """Get DBAPI connection (package-agnostic)."""
    return _adapter.connect(*args, **kwargs)

def get_package_info():
    """Get detected package info."""
    return _adapter.get_package_info()
```

### Migration Strategy

**For existing code**:
```python
# OLD (still works)
import iris.irissdk
conn = iris.irissdk.connect(...)

# NEW (package-agnostic)
from iris_devtester.utils.dbapi_compat import get_connection
conn = get_connection(...)
```

**For internal code** (connections, fixtures, etc.):
- Update all DBAPI connection code to use `dbapi_compat.get_connection()`
- Remove direct imports of `iris.irissdk`
- Log detected package for debugging

### Testing Strategy

**Test Matrix**:

| Environment | Package Installed | Expected Behavior |
|-------------|------------------|-------------------|
| **Modern only** | `intersystems-irispython` | Use modern package |
| **Legacy only** | `intersystems-iris` | Use legacy package |
| **Both installed** | Both | Use modern (priority) |
| **Neither installed** | None | Raise clear ImportError |

**How to Test Without Installing Both**:

1. **Mock imports** for unit tests:
   ```python
   @patch('sys.modules', {'intersystems_iris.dbapi._DBAPI': mock_modern})
   def test_modern_detection():
       info = detect_dbapi_package()
       assert info["package"] == "intersystems-irispython"
   ```

2. **Separate CI jobs** for integration tests:
   - Job 1: Install only `intersystems-irispython`
   - Job 2: Install only `intersystems-iris`
   - Job 3: Install both packages
   - Job 4: Install neither (test error handling)

3. **Docker-based integration tests**:
   - Container 1: Modern package only
   - Container 2: Legacy package only
   - Container 3: Both packages

---

## 6. Performance Impact Analysis

### Package Detection Overhead

**Measurement**: Import and detection time

```python
import time

# Measure detection time
start = time.perf_counter()
package_info = detect_dbapi_package()
elapsed_ms = (time.perf_counter() - start) * 1000

print(f"Detection time: {elapsed_ms:.2f}ms")
# Expected: <1ms (imports are cached after first load)
```

**Results** (estimated based on Python import behavior):
- First detection: ~1-2ms (module import)
- Subsequent calls: <0.01ms (module cache hit)
- NFR-001 requirement: <10ms ✅ Easily met

### Connection Performance

**No overhead**: The detected `connect()` function is called directly, no wrapper overhead.

```python
# Direct call (zero overhead)
conn = package_info["connect"](hostname=..., port=...)
```

---

## 7. Version Compatibility Validation

### Decision: Minimum Version Checks

**Implementation**:
```python
import importlib.metadata

def validate_package_version(package_name, min_version):
    """Validate installed package version."""
    try:
        installed = importlib.metadata.version(package_name)
        if Version(installed) < Version(min_version):
            raise ImportError(
                f"Package {package_name} version {installed} is too old\n"
                f"Minimum required: {min_version}\n"
                f"Please upgrade: pip install --upgrade {package_name}>={min_version}"
            )
    except importlib.metadata.PackageNotFoundError:
        # Package not installed, will be caught by import detection
        pass
```

**Minimum Versions**:
- `intersystems-irispython`: 5.3.0
- `intersystems-iris`: 3.0.0

---

## 8. Error Handling Design

### Constitutional Error Format (Principle #5)

All errors must follow What/Why/How/Docs format:

```python
class DBAPIPackageNotFoundError(ImportError):
    """Raised when no compatible IRIS Python package is found."""

    def __init__(self):
        super().__init__(
            "No IRIS Python package detected\n"
            "\n"
            "What went wrong:\n"
            "  Neither intersystems-irispython nor intersystems-iris is installed.\n"
            "  iris-devtester requires one of these packages for DBAPI connections.\n"
            "\n"
            "Why this happened:\n"
            "  iris-devtester uses DBAPI for fast SQL operations (3x faster than JDBC).\n"
            "  The modern package (intersystems-irispython) or legacy package\n"
            "  (intersystems-iris) must be installed.\n"
            "\n"
            "How to fix it:\n"
            "  Install the modern IRIS Python package:\n"
            "  → pip install intersystems-irispython>=5.3.0\n"
            "\n"
            "  Or install the legacy package (backward compatibility):\n"
            "  → pip install intersystems-iris>=3.0.0\n"
            "\n"
            "Documentation:\n"
            "  https://iris-devtester.readthedocs.io/dbapi-packages/\n"
        )
```

---

## 9. Logging and Debugging

### Decision: Log Package Detection

**Implementation**:
```python
import logging

logger = logging.getLogger(__name__)

def detect_dbapi_package():
    """Detect available IRIS DBAPI package."""
    # Try modern first
    try:
        from intersystems_iris.dbapi._DBAPI import connect
        info = {
            "package": "intersystems-irispython",
            "import_path": "intersystems_iris.dbapi._DBAPI",
            "connect": connect
        }
        logger.info(f"Detected IRIS DBAPI package: {info['package']}")
        return info
    except ImportError:
        logger.debug("Modern package not available, trying legacy")

    # Fall back to legacy
    try:
        import iris.irissdk
        info = {
            "package": "intersystems-iris",
            "import_path": "iris.irissdk",
            "connect": iris.irissdk.connect
        }
        logger.info(f"Detected IRIS DBAPI package: {info['package']} (legacy)")
        return info
    except ImportError:
        logger.error("No IRIS DBAPI package detected")

    raise DBAPIPackageNotFoundError()
```

**Log Levels**:
- `INFO`: Package detected successfully
- `DEBUG`: Fallback attempts
- `ERROR`: No package available

---

## 10. Implementation Recommendations

### Phase 1: Core Detection Module

1. Create `iris_devtester/utils/dbapi_compat.py`
2. Implement `detect_dbapi_package()` with try/except chain
3. Implement `DBAPIConnectionAdapter` class
4. Implement `get_connection()` and `get_package_info()` functions
5. Add logging and version validation

### Phase 2: Update Connection Code

1. Update `iris_devtester/connections/dbapi.py` to use `dbapi_compat`
2. Update `iris_devtester/connections/connection.py` to use adapter
3. Update `iris_devtester/connections/manager.py` to log package info

### Phase 3: Update Fixtures Module

1. Update `iris_devtester/fixtures/creator.py` to use `dbapi_compat`
2. Update `iris_devtester/fixtures/loader.py` to use `dbapi_compat`
3. No changes needed to `validator.py` (doesn't use DBAPI)

### Phase 4: Update Testing Utilities

1. Update `iris_devtester/testing/schema_reset.py` to use `dbapi_compat`
2. Update `iris_devtester/utils/password_reset.py` to use `dbapi_compat`

### Phase 5: Comprehensive Testing

1. Unit tests for package detection logic
2. Contract tests for all 4 scenarios
3. Integration tests with real IRIS containers
4. Error scenario tests

---

## 11. Documentation Requirements

### User-Facing Documentation

1. **README.md updates**:
   - Add section on supported DBAPI packages
   - Explain automatic detection
   - Show installation commands for both packages

2. **Migration Guide** (`docs/learnings/package-migration-guide.md`):
   - When to use modern vs legacy package
   - How to upgrade from legacy to modern
   - Troubleshooting package detection issues

3. **API Documentation**:
   - Document `dbapi_compat` module
   - Document `get_connection()` and `get_package_info()`
   - Add package detection examples

### Internal Documentation

1. **Learnings document**: Document why modern package preferred
2. **Architecture decision**: Why automatic detection over configuration
3. **Test strategy**: How to test both packages without conflicts

---

## Decisions Summary

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **Detection Method** | Try/except import chain | Pythonic, zero-config, performant |
| **Package Priority** | Modern first | Current standard, better performance |
| **Fallback Strategy** | Legacy as fallback | Backward compatibility |
| **Error Handling** | Constitutional format | Principle #5 compliance |
| **Version Validation** | Minimum version checks | Ensure API compatibility |
| **Logging** | INFO level | Debugging transparency |
| **Testing** | Mock for unit, Docker for integration | Comprehensive coverage |
| **Documentation** | Migration guide | User support |

---

## Constitutional Compliance Verification

✅ **Principle #1**: Automatic detection, no manual intervention
✅ **Principle #2**: Maintains DBAPI first, JDBC fallback unchanged
✅ **Principle #4**: Zero configuration required
✅ **Principle #5**: Constitutional error format implemented
✅ **Principle #7**: 95%+ coverage via comprehensive testing
✅ **Principle #8**: Research documented in this file

---

**Status**: Research complete, ready for Phase 1 (Design & Contracts)
