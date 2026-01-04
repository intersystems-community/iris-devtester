# IRIS DevTools Constitution

**Version**: 1.1.0
**Status**: Foundational
**Last Updated**: 2025-11-23

## Preamble

This constitution codifies the hard-won lessons, blind alleys avoided, and battle-tested practices from years of InterSystems IRIS development. Every principle herein represents real production experience, real failures overcome, and real solutions that work.

## CRITICAL: Read This First

### MANDATORY: Use intersystems-irispython Package ONLY

**ABSOLUTE REQUIREMENT**: This project uses `intersystems-irispython` as the ONLY Python package for IRIS connectivity.

**FORBIDDEN PACKAGES**:
- ❌ `intersystems-iris` (old package, deprecated)
- ❌ Any other IRIS Python packages

**Why This Matters**:
- `intersystems-irispython` is the modern, maintained package (v5.3.0+)
- `intersystems-iris` is the legacy package (v3.0.0+) with known issues
- Mixing packages causes import conflicts and mysterious failures
- This is a foundational architectural decision

**The Rule**: ALWAYS use `import intersystems_irispython` in ALL code. NEVER import from `intersystems_iris`.

---

### SQL vs ObjectScript Execution

**Before writing ANY code that interacts with IRIS, read `docs/SQL_VS_OBJECTSCRIPT.md`.**

This single document answers the most critical question in IRIS development: "How do I execute this operation?"

**Why This Matters**:
- Using the wrong execution method causes mysterious failures
- 53 integration tests failed because of this misunderstanding
- DBAPI is 3x faster for SQL but CANNOT execute ObjectScript
- iris.connect() is required for namespace/Task Manager operations
- Getting this wrong wastes hours of debugging

**The Rule**: When you don't know which tool to use, check `docs/SQL_VS_OBJECTSCRIPT.md` FIRST, not after your code fails.

## Core Principles

### 1. AUTOMATIC REMEDIATION OVER MANUAL INTERVENTION

**The Principle**: Infrastructure problems must be automatically detected and remediated without developer intervention.

**Why It Matters**:
- Password expiration errors have wasted hundreds of developer hours
- Manual remediation breaks CI/CD pipelines
- "Works on my machine" scenarios damage team productivity

**Implementation Requirements**:
- ✅ Password change required → automatic reset
- ✅ Container not found → automatic start
- ✅ Port conflicts → automatic port reassignment
- ✅ Stale schema → automatic reset
- ✅ Connection failures → automatic retry with backoff

**Forbidden**:
- ❌ Error messages without remediation steps
- ❌ Requiring manual Docker commands
- ❌ Silent failures without auto-recovery attempts

**Example**:
```python
# WRONG: Manual intervention required
raise ConnectionError("Password change required. Run: docker exec...")

# RIGHT: Automatic remediation
if "Password change required" in str(error):
    reset_password_automatically()
    retry_connection()
```

### 2. CHOOSE THE RIGHT TOOL FOR THE JOB

**The Principle**: Use the appropriate connection method based on what operation you need to perform.

**Why It Matters**:
- IRIS has **two distinct execution paths**: SQL (via DBAPI) and ObjectScript (via iris.connect())
- Using the wrong tool causes mysterious failures
- DBAPI is 3x faster for SQL operations
- ObjectScript operations require iris.connect() or docker exec
- **Getting this wrong breaks everything**

**The Decision Matrix**:

| Operation Type | Use | Speed | Example |
|----------------|-----|-------|---------|
| SQL queries (SELECT, INSERT, UPDATE, DELETE) | **DBAPI** | Fast (3x) | `cursor.execute("SELECT * FROM MyTable")` |
| SQL DDL (CREATE TABLE, DROP TABLE) | **DBAPI** | Fast (3x) | `cursor.execute("CREATE TABLE ...")` |
| Backup/Restore namespace | **DBAPI** + $SYSTEM.OBJ.Execute() | Medium | `cursor.execute("SELECT $SYSTEM.OBJ.Execute('...')")` |
| Create/Delete namespace | **iris.connect()** | Medium | `iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")` |
| Task Manager operations | **iris.connect()** | Medium | `iris_obj.execute("Set task = ##class(%SYS.Task).%New()")` |
| Global variables | **iris.connect()** | Medium | `iris_obj.set("^MyGlobal", "value")` |
| User/password management | **docker exec** | Slow | `docker exec iris_db iris session IRIS ...` |

**Implementation Requirements**:
- ✅ Use DBAPI for all SQL operations (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE)
- ✅ Use iris.connect() for ObjectScript operations (namespaces, Task Manager, globals)
- ✅ Use docker exec only for admin operations (password reset, system config)
- ✅ Never try to execute ObjectScript directly through DBAPI cursor.execute()
- ✅ Log which connection type is used for each operation

**Forbidden**:
- ❌ `cursor.execute("DO ##class(...)...")` - DBAPI cannot execute ObjectScript
- ❌ `cursor.execute("Set ^GlobalData = 'value'")` - DBAPI cannot set globals
- ❌ Using iris.connect() for simple SQL queries (3x slower than DBAPI)
- ❌ Wrapping ObjectScript in SELECT without understanding limitations

**Critical Examples**:

```python
# ✅ RIGHT - SQL via DBAPI
cursor.execute("SELECT COUNT(*) FROM MyTable")
cursor.execute("INSERT INTO MyTable VALUES (1, 'Alice')")
cursor.execute("CREATE TABLE TestData (ID INT, Name VARCHAR(100))")

# ✅ RIGHT - ObjectScript via iris.connect()
import iris
conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                    username="_SYSTEM", password="SYS")
iris_obj = iris.createIRIS(conn)
iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
iris_obj.set("^MyGlobal", "value")

# ✅ RIGHT - Limited ObjectScript via $SYSTEM.OBJ.Execute()
cursor.execute("""
    SELECT $SYSTEM.OBJ.Execute('
        Set sc = ##class(SYS.Database).BackupNamespace("USER", "/tmp/backup.dat")
        If sc { Write "SUCCESS" } Else { Write "FAILED" }
    ')
""")

# ❌ WRONG - ObjectScript through DBAPI (FAILS!)
cursor.execute("DO ##class(Config.Namespaces).Create('TEST')")  # BREAKS!
cursor.execute("Set ^GlobalData = 'value'")  # BREAKS!
cursor.execute("SELECT $SYSTEM.OBJ.Execute('Do ##class(Config.Namespaces).Create(\"TEST\")')")  # SECURITY ERROR!
```

**Performance Evidence**:
```
Benchmark Results (1000 simple queries):
- DBAPI: 2.3 seconds
- iris.connect(): 7.1 seconds
- docker exec: ~600 seconds
- Speedup (DBAPI vs iris.connect()): 3.09x

For SQL operations → Always use DBAPI
For ObjectScript → Use iris.connect() (not DBAPI)
For admin ops → Use docker exec (when iris.connect() unavailable)
```

**Reference**: See `docs/SQL_VS_OBJECTSCRIPT.md` for complete guide

### 3. ISOLATION BY DEFAULT

**The Principle**: Every test suite gets its own isolated IRIS instance unless explicitly shared.

**Why It Matters**:
- Shared databases cause test pollution
- Parallel test execution requires isolation
- Cleanup failures cascade to other tests
- "Works alone but fails in suite" mysteries

**Implementation Requirements**:
- ✅ Testcontainers for test isolation
- ✅ Unique namespaces per test class
- ✅ test_run_id tracking for data cleanup
- ✅ Automatic cleanup even on test failure

**Forbidden**:
- ❌ Shared databases without cleanup
- ❌ Assuming tests run sequentially
- ❌ Leaving test data behind

**Scope Guidelines**:
```python
# Module scope: Fast, shared state acceptable
@pytest.fixture(scope="module")
def iris_db_fast():
    # One container for all tests in module
    # Use when: Tests are read-only or properly isolated

# Function scope: Slower, maximum isolation
@pytest.fixture(scope="function")
def iris_db_isolated():
    # New container for each test
    # Use when: Tests modify schema or require clean state
```

### 4. ZERO CONFIGURATION VIABLE

**The Principle**: `pip install iris-devtester && pytest` must work without configuration.

**Why It Matters**:
- Reduces onboarding friction
- Enables quick experimentation
- Makes examples self-contained
- CI/CD "just works"

**Implementation Requirements**:
- ✅ Sensible defaults for all configuration
- ✅ Auto-discovery of IRIS instances
- ✅ Community edition defaults
- ✅ Environment variable overrides
- ✅ Explicit configuration always possible

**Forbidden**:
- ❌ Required configuration files
- ❌ Mandatory environment variables
- ❌ Undocumented prerequisites

**Configuration Hierarchy** (highest priority first):
1. Explicit constructor arguments
2. Environment variables
3. .env files in project root
4. Docker container inspection
5. Sensible defaults (localhost:1972, etc.)

### 5. FAIL FAST WITH GUIDANCE

**The Principle**: Errors must be detected immediately with clear remediation steps.

**Why It Matters**:
- Debugging time is expensive
- Stack traces without context are useless
- Developers need actionable guidance

**Implementation Requirements**:
- ✅ Detect errors at initialization, not first use
- ✅ Include "What went wrong" explanation
- ✅ Include "How to fix it" remediation
- ✅ Include "Why it matters" context (when helpful)
- ✅ Link to relevant documentation

**Forbidden**:
- ❌ Generic error messages
- ❌ Stack traces without explanation
- ❌ "Contact administrator" without details

**Example**:
```python
# WRONG
raise ConnectionError("Failed to connect")

# RIGHT
raise ConnectionError(
    "Failed to connect to IRIS at localhost:1972\n"
    "\n"
    "What went wrong:\n"
    "  The IRIS database is not running or not accessible.\n"
    "\n"
    "How to fix it:\n"
    "  1. Start IRIS: docker-compose up -d\n"
    "  2. Wait 30 seconds for startup\n"
    "  3. Verify: docker logs iris_db_rag_templates\n"
    "\n"
    "Alternative: Use testcontainers for automatic IRIS management:\n"
    "  from iris_devtester.containers import IRISContainer\n"
    "  with IRISContainer.community() as iris:\n"
    "      conn = iris.get_connection()\n"
    "\n"
    "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/\n"
)
```

### 6. ENTERPRISE READY, COMMUNITY FRIENDLY

**The Principle**: Support both Community and Enterprise editions equally well.

**Why It Matters**:
- Different projects have different needs
- Development often uses Community, production uses Enterprise
- License management is complex
- Mirror configurations are enterprise-only

**Implementation Requirements**:
- ✅ Community edition as default
- ✅ Enterprise edition via license_key parameter
- ✅ Auto-discovery of license files
- ✅ Support for all Enterprise features (Mirrors, Sharding, etc.)
- ✅ Clear documentation of edition differences

**Forbidden**:
- ❌ Hardcoded edition assumptions
- ❌ Enterprise-only code paths without community fallback
- ❌ Obscure license errors

**License Discovery Order**:
1. Explicit `license_key` parameter
2. `IRIS_LICENSE_KEY` environment variable
3. `~/.iris/iris.key`
4. `./iris.key` in project root
5. Auto-discovered from Docker volume mounts

### 7. MEDICAL-GRADE RELIABILITY

**The Principle**: All code must be battle-tested in production scenarios with comprehensive error handling.

**Why It Matters**:
- Healthcare applications require 99.9%+ uptime
- Silent failures are unacceptable
- Diagnostic data saves hours of debugging
- Idempotency prevents cascading failures

**Implementation Requirements**:
- ✅ 95%+ test coverage
- ✅ All error paths tested
- ✅ Idempotent operations (safe to retry)
- ✅ Comprehensive logging
- ✅ Performance monitoring
- ✅ Graceful degradation
- ✅ Health check endpoints

**Forbidden**:
- ❌ Untested error paths
- ❌ Non-idempotent operations
- ❌ Silent failures
- ❌ Assumptions about state

**Reliability Checklist**:
```python
# Every operation must answer:
- [ ] What happens if this fails?
- [ ] Can it be retried safely?
- [ ] How do we detect failure?
- [ ] What diagnostics are logged?
- [ ] How do we recover?
- [ ] What's the user impact?
```

### 8. USE OFFICIAL IRIS PYTHON API (NO PRIVATE ATTRIBUTES)

**The Principle**: MUST use the official `iris.connect()` interface from InterSystems documentation. NEVER use undocumented private attributes like `_DBAPI`.

**Why It Matters**:
- `_DBAPI` does NOT exist in intersystems-irispython (tested in v5.1.2 and v5.3.0)
- Using non-existent attributes causes mysterious import failures
- Official API is `iris.connect()` per InterSystems documentation
- Private attributes are subject to change without warning

**Implementation Requirements**:
- ✅ Use `iris.connect()` for DBAPI connections (official DB-API 2.0 interface)
- ✅ Follow official InterSystems documentation: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_pyapi
- ✅ Never import from private modules (anything starting with `_`)
- ✅ Test compatibility with both v5.1.2 and v5.3.0

**Forbidden**:
- ❌ `from intersystems_iris.dbapi._DBAPI import connect` - **_DBAPI does not exist!**
- ❌ `iris._DBAPI.connect()` - **No such attribute!**
- ❌ Any code relying on undocumented internal APIs
- ❌ Assuming package structure without verification

**Correct API Usage**:
```python
# ✅ CORRECT - Official DB-API 2.0 interface
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

# ❌ WRONG - _DBAPI does not exist!
from intersystems_iris.dbapi._DBAPI import connect  # ImportError!
iris._DBAPI.connect(...)  # AttributeError!
```

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

**Reference**: See hipporag2-pipeline CONSTITUTION.md Principle 9 for detailed empirical testing results.

### 9. DOCUMENT THE BLIND ALLEYS

**The Principle**: Failed approaches must be documented to prevent repetition.

**Why It Matters**:
- Developers waste time rediscovering "why not"
- Institutional knowledge must be preserved
- Context for design decisions is valuable
- Prevents regression to worse solutions

**Implementation Requirements**:
- ✅ `docs/learnings/` directory for deep-dives
- ✅ "Why not X?" sections in documentation
- ✅ ADR (Architecture Decision Records) for major choices
- ✅ Performance comparisons
- ✅ Case studies from production

**Documented Blind Alleys**:
- **Why not JDBC-only?** → DBAPI is 3x faster, see benchmark
- **Why not shared test databases?** → Data pollution, see case study
- **Why not manual password resets?** → CI/CD breaks, see incident report
- **Why not port 1972 hardcoded?** → Conflicts in parallel tests, see issue #42

**Example Documentation**:
```markdown
## Why Not Use Docker Compose for Tests?

**What we tried**: Using docker-compose.yml for test database
**Why it didn't work**:
- Parallel tests conflicted on ports
- Cleanup required manual intervention
- CI/CD required docker-compose installation
- Container lifecycle not tied to test lifecycle

**What we use instead**: Testcontainers
**Evidence**: 287 test failures → 0 after migration
**Date tried**: 2024-09-15
**Decision**: Codified in constitution v1.0
```

## Governance

### Amendment Process

Principles may be amended when:
1. New evidence contradicts existing principle
2. Technology landscape changes materially
3. Production experience reveals gap
4. Community consensus emerges

**Amendment requires**:
- Concrete evidence (benchmarks, case studies, incident reports)
- Backwards compatibility analysis
- Migration guide for existing code
- Updated documentation
- Version bump (major if breaking)

### Enforcement

**Pre-commit hooks** validate:
- [ ] No hardcoded passwords or credentials
- [ ] All database operations are idempotent
- [ ] Error messages include remediation
- [ ] Test isolation via testcontainers or unique namespaces

**CI/CD validates**:
- [ ] 95%+ test coverage
- [ ] All platforms (Linux, Mac, Windows)
- [ ] Both Community and Enterprise editions
- [ ] Performance benchmarks (no regressions)

**Code review checklist**:
- [ ] Follows DBAPI-first principle
- [ ] Automatic remediation implemented
- [ ] Comprehensive error handling
- [ ] Documentation updated
- [ ] Blind alleys documented if applicable

## Version History

### v1.1.0 (2025-11-23)
- Added Principle 8: Use Official IRIS Python API (No Private Attributes)
- Documents empirically tested fact that `_DBAPI` does NOT exist in intersystems-irispython v5.1.2 or v5.3.0
- Mandates use of official `iris.connect()` API per InterSystems documentation
- Renumbered Principle 8 "Document the Blind Alleys" → Principle 9
- Based on critical findings from hipporag2-pipeline project testing

### v1.0.0 (2025-10-05)
- Initial constitution
- 8 core principles established
- Based on rag-templates production experience
- Incorporates learnings from Features 026, 028

## References

- [Testcontainers Best Practices](https://testcontainers.com/guides/)
- [InterSystems IRIS Docker Guide](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK)
- [rag-templates Feature 026](../026-fix-critical-issues/)
- [rag-templates Feature 028](../028-obviously-these-failures/)
- [12 Factor App Methodology](https://12factor.net/)
- [Medical Device Software Standards](https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd)

---

**Remember**: Every principle here was paid for with real debugging time, real production incidents, real developer frustration. Honor these learnings by building on them, not repeating them.
