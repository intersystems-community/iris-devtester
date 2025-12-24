# The `_DBAPI` Private Module Myth

**Date**: 2025-11-23
**Status**: CRITICAL BUG FIX
**Constitutional Principle**: #8 - Use Official IRIS Python API (No Private Attributes)

---

## Executive Summary

**CRITICAL FINDING**: The `_DBAPI` module does **NOT exist** in intersystems-irispython v5.1.2 or v5.3.0.

Code attempting to import from `intersystems_iris.dbapi._DBAPI` will fail with `ImportError` or `AttributeError`.

**Solution**: Use the official `iris.connect()` API per InterSystems documentation.

---

## The Bug

### What Was Wrong

```python
# ❌ BROKEN CODE (iris-devtester v1.4.7 and earlier)
from intersystems_iris.dbapi._DBAPI import connect

# This import fails because _DBAPI does not exist!
```

### Why It Happened

1. **Assumption without verification**: Code assumed package structure without empirical testing
2. **Private module dependency**: Relied on undocumented internal module (`_DBAPI` starts with underscore)
3. **No InterSystems documentation**: Official docs never mention `_DBAPI`

### Impact

- All DBAPI connections failed with mysterious `ImportError`
- Affected hipporag2-pipeline project (discovered the bug)
- Violated Constitutional Principle #8 (use official APIs only)

---

## Empirical Evidence

### Test Results (hipporag2-pipeline)

```python
# Tested on intersystems-irispython v5.1.2
import iris
hasattr(iris, '_DBAPI')  # → False

# Tested on intersystems-irispython v5.3.0
import iris
hasattr(iris, '_DBAPI')  # → False

# Both versions HAVE the official connect() function
hasattr(iris, 'connect')  # → True (BOTH versions!)
```

**Conclusion**: `_DBAPI` never existed in either version.

---

## The Official API

### InterSystems Documentation

**Source**: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_pyapi

The official DB-API 2.0 interface is `iris.connect()`:

```python
# ✅ CORRECT - Official API
import iris

conn = iris.connect(
    hostname="localhost",
    port=1972,
    namespace="USER",
    username="SuperUser",
    password="SYS"
)
cursor = conn.cursor()
cursor.execute("SELECT 1")
result = cursor.fetchone()
```

### Why This Is Better

1. **Documented**: In official InterSystems Python API documentation
2. **Stable**: Public API, won't change without deprecation notice
3. **Simple**: Direct import, no nested modules
4. **Works**: Tested in v5.1.2 and v5.3.0

---

## The Fix

### Code Changes

**File**: `iris_devtester/utils/dbapi_compat.py`

```python
# BEFORE (v1.4.7 - BROKEN)
try:
    from intersystems_iris.dbapi._DBAPI import connect  # ← ImportError!

    pkg_version = importlib.metadata.version("intersystems-irispython")
    validate_package_version("intersystems-irispython", pkg_version, "5.3.0")

    return DBAPIPackageInfo(
        package_name="intersystems-irispython",
        import_path="intersystems_iris.dbapi._DBAPI",  # ← Wrong!
        version=pkg_version,
        connect_function=connect,
        detection_time_ms=elapsed_ms
    )
except ImportError as e:
    logger.debug(f"Modern package not available, trying legacy: {e}")
```

```python
# AFTER (v1.5.0 - FIXED)
try:
    import iris  # ✅ Official API!

    pkg_version = importlib.metadata.version("intersystems-irispython")
    validate_package_version("intersystems-irispython", pkg_version, "5.1.2")  # ← Lowered to tested version

    return DBAPIPackageInfo(
        package_name="intersystems-irispython",
        import_path="iris",  # ✅ Correct import path!
        version=pkg_version,
        connect_function=iris.connect,  # ✅ Official DB-API 2.0 interface!
        detection_time_ms=elapsed_ms
    )
except ImportError as e:
    logger.debug(f"Modern package not available, trying legacy: {e}")
```

### Test Changes

**File**: `tests/contract/test_modern_package_contract.py`

```python
# BEFORE (v1.4.7 - BROKEN)
with patch.dict('sys.modules', {
    'intersystems_iris': MagicMock(),
    'intersystems_iris.dbapi': MagicMock(),
    'intersystems_iris.dbapi._DBAPI': mock_modern  # ← Mocking non-existent module!
}):
    # ...
    assert info.import_path == "intersystems_iris.dbapi._DBAPI"  # ← Wrong assertion!
```

```python
# AFTER (v1.5.0 - FIXED)
with patch.dict('sys.modules', {
    'iris': mock_iris  # ✅ Mock official module!
}):
    # ...
    assert info.import_path == "iris"  # ✅ Correct assertion!
```

---

## Constitutional Update

### Principle #8: Use Official IRIS Python API (No Private Attributes)

**Added**: CONSTITUTION.md v1.1.0 (2025-11-23)

**Mandates**:
1. ✅ Use `iris.connect()` for DBAPI connections (official DB-API 2.0 interface)
2. ✅ Follow official InterSystems documentation
3. ✅ Never import from private modules (anything starting with `_`)
4. ✅ Test compatibility with both v5.1.2 and v5.3.0

**Forbidden**:
- ❌ `from intersystems_iris.dbapi._DBAPI import connect` - **Module does not exist!**
- ❌ `iris._DBAPI.connect()` - **Attribute does not exist!**
- ❌ Any code relying on undocumented internal APIs

**Empirical Evidence**:
```python
# Tested on intersystems-irispython v5.1.2 and v5.3.0
import iris
hasattr(iris, '_DBAPI')  # False in BOTH versions!
hasattr(iris, 'connect')  # True in BOTH versions!
```

**Official Documentation**:
- InterSystems Python API: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_pyapi
- DB-API 2.0 Specification: https://peps.python.org/pep-0249/

---

## Lessons Learned

### 1. Always Verify Package Structure

**Don't assume**: "The package probably has `_DBAPI`..."
**Do verify**: `python -c "import iris; print(dir(iris))"`

### 2. Trust Official Documentation

**Don't invent**: Custom import paths based on guesswork
**Do follow**: InterSystems official Python API documentation

### 3. Avoid Private Modules

**Red flag**: Any import starting with underscore (`_DBAPI`, `_init_elsdk`, etc.)
**Safe pattern**: Public documented APIs only

### 4. Test Empirically

**Theory**: "v5.3.0 probably works the same as v5.1.2..."
**Practice**: Test BOTH versions explicitly with `hasattr()` checks

---

## Related Documents

- **CONSTITUTION.md**: Principle #8 (Use Official IRIS Python API)
- **hipporag2-pipeline/CONSTITUTION.md**: Principle 9 (same finding, independent verification)
- **InterSystems Python API**: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_pyapi

---

## References

1. **InterSystems Official Documentation**
   https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_pyapi

2. **DB-API 2.0 Specification (PEP 249)**
   https://peps.python.org/pep-0249/

3. **hipporag2-pipeline Empirical Testing**
   ~/ws/hipporag2-pipeline/CONSTITUTION.md Principle 9

4. **iris-devtester Fix Commit**
   Commit: 1fad17b - CRITICAL FIX: Remove non-existent _DBAPI import

---

**Bottom Line**: The `_DBAPI` module never existed. Use `iris.connect()` - it's official, documented, and works in v5.1.2 and v5.3.0.
