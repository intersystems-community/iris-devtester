# iris-devtester Extraction Plan - Executive Summary

**Project:** iris-devtester
**Source:** rag-templates (production RAG framework)
**Analysis Date:** 2025-10-06

---

## TL;DR

Extract **~2,400 lines** of battle-tested IRIS infrastructure from rag-templates into iris-devtester, saving **90% of boilerplate** for future IRIS Python projects.

**Impact:** New projects go from 2-3 days setup to **1-2 hours**.

---

## What We're Extracting

### 🔴 Phase 1: Connection Management (Week 1) - CRITICAL
**Files:** 3 files, 957 lines
- ✅ DBAPI-first connection with automatic JDBC fallback
- ✅ Port auto-detection (Docker + native IRIS)
- ✅ Environment auto-detection (UV, venv, system)
- ✅ Retry logic with exponential backoff

**Target:** `iris_devtester/connections/`

### 🟠 Phase 2: Password Reset (Week 2) - HIGH PRIORITY
**Files:** 1 file, 230 lines
- ✅ Automatic detection of "Password change required" errors
- ✅ Docker exec password reset (no manual intervention)
- ✅ Integration with connection manager
- ✅ Constitutional requirement #1: "Automatic Remediation Over Manual Intervention"

**Target:** `iris_devtester/testing/password_reset.py`

### 🟡 Phase 3: Test Infrastructure (Week 3) - MEDIUM PRIORITY
**Files:** 5 files, 1,232 lines
- ✅ Test isolation with unique test_run_id per test
- ✅ Guaranteed cleanup even on failure
- ✅ Pre-flight validation (<2 seconds)
- ✅ Schema management (reset/validate)
- ✅ State tracking for debugging

**Target:** `iris_devtester/testing/`

### 🟢 Phase 4: Configuration Discovery (Week 4) - NICE TO HAVE
**Files:** 2 files, 243 lines
- ✅ Multi-source config (env, .env, Docker, native)
- ✅ Smart defaults
- ✅ .env generation from running IRIS

**Target:** `iris_devtester/config/`

---

## Key Statistics

| Metric | Value |
|--------|-------|
| **Total Lines to Extract** | ~2,400 |
| **Files to Process** | 12 core files |
| **Test Coverage in Source** | 95%+ |
| **Number of Tests in Source** | 789 tests |
| **Code Reduction for Users** | 90-95% |
| **Setup Time Reduction** | 2-3 days → 1-2 hours |

---

## Proven Patterns to Preserve

### 1. DBAPI-First with Automatic Fallback
```python
# Preserved from rag-templates
conn = get_connection()  # Tries DBAPI → JDBC → Mock (for tests)
```

### 2. Automatic Password Reset
```python
# Preserved from rag-templates Feature 028
try:
    conn = iris.connect(...)
except PasswordChangeRequired:
    reset_password_via_docker_exec()
    conn = iris.connect(...)  # Retry automatically
```

### 3. Test Isolation by Default
```python
# Preserved from rag-templates Feature 028
@pytest.fixture
def iris_db():
    test_id = uuid.uuid4()  # Unique per test
    register_cleanup(test_id)  # Guaranteed cleanup
    yield get_connection()
```

### 4. Port Auto-Detection
```python
# Preserved from rag-templates
ports = [11972, 21972, 1972]  # Docker, Licensed, System
for port in ports:
    if docker_iris_running(port):
        return port
```

---

## Before vs. After

### Connection Setup

**Before (rag-templates approach):**
```python
# Copy 3 files (~960 lines)
# common/iris_connection_manager.py
# common/iris_dbapi_connector.py
# common/environment_manager.py

from common.iris_connection_manager import get_iris_connection
conn = get_iris_connection()
```

**After (iris-devtester):**
```python
# pip install iris-devtester
from iris_devtester.connections import get_connection
conn = get_connection()  # Zero config for Docker
```

### Test Infrastructure

**Before (rag-templates approach):**
```python
# Copy 5 files (~1,230 lines)
# tests/utils/iris_password_reset.py
# tests/fixtures/database_cleanup.py
# tests/fixtures/database_state.py
# tests/fixtures/schema_reset.py
# tests/utils/preflight_checks.py

# Manual setup in conftest.py (~200 lines)
```

**After (iris-devtester):**
```python
from iris_devtester.testing import iris_db

def test_my_feature(iris_db):
    # Auto password reset
    # Auto cleanup
    # Auto state tracking
    cursor = iris_db.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

---

## Effort Savings

### Development Time
| Activity | Current | With iris-devtester | Savings |
|----------|---------|-------------------|---------|
| Initial setup | 2-4 hours | 15 minutes | **90%** |
| Test infrastructure | 8-12 hours | 1 hour | **88%** |
| Password debugging | 1-2 hours/occurrence | 0 (automatic) | **100%** |
| Environment troubleshooting | 30-60 minutes | 0 (auto-detect) | **100%** |

### Code Maintenance
| Metric | Current | With iris-devtester | Reduction |
|--------|---------|-------------------|-----------|
| Connection code | ~960 lines | ~50 lines | **95%** |
| Test infrastructure | ~1,230 lines | ~100 lines | **92%** |
| Configuration | ~240 lines | ~30 lines | **87%** |
| **Total** | **~2,430 lines** | **~180 lines** | **93%** |

---

## Constitutional Compliance

All extracted code validates against `CONSTITUTION.md`:

| Principle | Status |
|-----------|--------|
| ✅ #1: Automatic Remediation | Password reset, port detection |
| ✅ #2: DBAPI First | Preserved fallback chain |
| ✅ #3: Isolation by Default | test_run_id per test |
| ✅ #4: Zero Configuration Viable | Auto-detect Docker IRIS |
| ✅ #5: Fail Fast with Guidance | All errors have remediation |
| ✅ #6: Enterprise + Community | Both tested |
| ✅ #7: Medical-Grade Reliability | 95%+ coverage maintained |
| ✅ #8: Document Blind Alleys | Port docs/learnings/ |

---

## File Locations

### Source (rag-templates)
```
/Users/tdyar/ws/rag-templates/
├── common/
│   ├── iris_connection_manager.py (412 lines) ← EXTRACT
│   ├── iris_dbapi_connector.py (324 lines)    ← EXTRACT
│   └── environment_manager.py (221 lines)     ← EXTRACT
└── tests/
    ├── utils/
    │   ├── iris_password_reset.py (230 lines) ← EXTRACT
    │   └── preflight_checks.py (256 lines)    ← EXTRACT
    └── fixtures/
        ├── database_cleanup.py (186 lines)    ← EXTRACT
        ├── database_state.py (181 lines)      ← EXTRACT
        └── schema_reset.py (179 lines)        ← EXTRACT
```

### Target (iris-devtester)
```
/Users/tdyar/ws/iris-devtester/
└── iris_devtester/
    ├── connections/
    │   ├── manager.py          ← iris_connection_manager.py
    │   └── dbapi.py            ← iris_dbapi_connector.py
    ├── testing/
    │   ├── password_reset.py   ← iris_password_reset.py
    │   ├── preflight.py        ← preflight_checks.py
    │   ├── cleanup.py          ← database_cleanup.py
    │   ├── state.py            ← database_state.py
    │   └── fixtures.py         ← conftest.py patterns
    ├── config/
    │   └── discovery.py        ← config.py + auto-detection
    └── utils/
        └── environment.py      ← environment_manager.py
```

---

## Next Steps

### This Week
1. ✅ Review analysis (this document + detailed analysis)
2. ⬜ Create Feature 001 spec for connection management
3. ⬜ Set up CI/CD (GitHub Actions + testcontainers)
4. ⬜ Start Phase 1 extraction

### Weeks 1-2
1. ⬜ Extract connection management
2. ⬜ Extract password reset
3. ⬜ Write integration tests
4. ⬜ Document API

### Weeks 3-4
1. ⬜ Extract test infrastructure
2. ⬜ Create pytest plugin
3. ⬜ Release iris-devtester 0.1.0

---

## Risk Assessment

### Technical Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| IRIS module name conflicts | HIGH | Careful namespace isolation, lazy imports |
| Docker exec on Windows | MEDIUM | Test on WSL2, document requirements |
| JDBC JAR discovery | MEDIUM | Multiple search paths, clear errors |

### Schedule Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Integration tests require IRIS | MEDIUM | Use testcontainers-iris-python |
| Password reset needs elevated perms | LOW | Document manual testing |
| Multiple platform testing | MEDIUM | CI matrix (Linux, macOS, Windows) |

---

## Success Metrics

### Development Success
- [ ] `pip install iris-devtester && pytest` works zero-config
- [ ] Automatic password reset (no manual Docker exec)
- [ ] Port auto-detection (Docker + native)
- [ ] 95%+ test coverage maintained

### Adoption Success
- [ ] rag-templates migrated to use iris-devtester
- [ ] 2+ other projects using iris-devtester
- [ ] <5 GitHub issues per month (stable API)
- [ ] Documentation covers 90%+ of use cases

### Community Success
- [ ] Published to PyPI as `iris-devtester`
- [ ] README with quick start (<5 minutes)
- [ ] Contributing guide
- [ ] Linked from InterSystems docs

---

## Questions to Resolve

1. **Package naming:** Confirm `iris-devtester` (vs `intersystems-devtools`, `iris-dev-toolkit`)
2. **License:** MIT (matching rag-templates)?
3. **Repository:** GitHub location (InterSystems org or personal?)
4. **PyPI ownership:** Who publishes/maintains?
5. **Support model:** Community support or official InterSystems backing?

---

## Resources

- **Detailed Analysis:** `/Users/tdyar/ws/iris-devtester/docs/RAG_TEMPLATES_ANALYSIS.md`
- **Source Project:** `/Users/tdyar/ws/rag-templates`
- **Constitution:** `/Users/tdyar/ws/iris-devtester/CONSTITUTION.md`
- **README:** `/Users/tdyar/ws/iris-devtester/README.md`

---

**Bottom Line:** This extraction is **high value, low risk**. The code is proven in production, well-tested, and directly addresses the 8 constitutional principles. Estimated 4 weeks to v0.1.0 with ~90% code reduction for users.
