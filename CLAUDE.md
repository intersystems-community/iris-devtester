# CLAUDE.md - IRIS DevTools

**Purpose**: Provides Claude Code with project-specific context, patterns, and conventions.

**Related Files**:
- [AGENTS.md](AGENTS.md) - Vendor-neutral AI configuration (build commands, CI/CD, operational details)
- [README.md](README.md) - Project overview for all audiences (human and AI)
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributor onboarding and guidelines

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**IRIS DevTools** is a battle-tested Python package providing automatic, reliable infrastructure for InterSystems IRIS development. This is being extracted from production code in the `rag-templates` project.

## Source Material

This package is being built by extracting and enhancing code from:
- **Location**: `~/ws/rag-templates/`
- **Key areas**: Connection management, password reset, testing infrastructure, schema management

## Core Principles (CONSTITUTIONAL)

All code MUST follow the 8 principles in `CONSTITUTION.md`:

1. **Automatic Remediation Over Manual Intervention** - No "run this command" errors
2. **DBAPI First, JDBC Fallback** - Always try fastest option first
3. **Isolation by Default** - Each test gets its own database
4. **Zero Configuration Viable** - `pip install && pytest` must work
5. **Fail Fast with Guidance** - Clear errors with fix instructions
6. **Enterprise Ready, Community Friendly** - Support both editions
7. **Medical-Grade Reliability** - 95%+ test coverage required
8. **Document the Blind Alleys** - Explain why not X

## Development Workflow

### Initial Setup

```bash
# Already done:
cd ~/ws/iris-devtester
git init
git checkout -b main

# Install in development mode
pip install -e ".[dev,test,all]"

# Run tests
pytest
```

### Code Organization

```
iris_devtester/
├── connections/    # Connection management (DBAPI/JDBC)
├── containers/     # Testcontainers wrapper
├── fixtures/       # DAT fixture management (Feature 004)
├── testing/        # pytest fixtures & utilities
├── config/         # Configuration discovery
└── utils/          # Helpers
```

### Testing Requirements

- **Unit tests**: `tests/unit/` - Mock external dependencies
- **Integration tests**: `tests/integration/` - Use real IRIS containers
- **E2E tests**: `tests/e2e/` - Full workflow validation
- **Coverage**: Must maintain 95%+

### Code Style

Configured in `pyproject.toml`:
- **black**: Line length 100
- **isort**: Compatible with black
- **mypy**: Type checking (when possible)
- **pytest**: Comprehensive test suite

### Extraction Guidelines

When extracting from rag-templates:

1. **Copy proven code** - Don't rewrite what works
2. **Update imports** - Adjust for new package structure
3. **Add type hints** - Improve type safety
4. **Keep tests** - Port relevant tests
5. **Update docstrings** - Ensure accuracy
6. **Check constitutional compliance** - Verify all 8 principles

### Dependencies

Core:
- `testcontainers>=4.0.0` - Container management
- `testcontainers-iris>=1.2.2` - IRIS support
- `python-dotenv>=1.0.0` - Environment config

Optional (install with `[all]`):
- `intersystems-irispython>=3.2.0` - DBAPI (fast)
- `jaydebeapi>=1.2.3` - JDBC (fallback)

## Key Files

### Must Read Before Coding

- `skill.md` - Hierarchical agent guidance (PRIMARY ENTRY POINT)
- `CONSTITUTION.md` - 8 core principles (NON-NEGOTIABLE)
- `README.md` - User-facing documentation
- `pyproject.toml` - Package configuration
- `.specify/feature-request.md` - Implementation plan

### Source Code References

Look at `~/ws/rag-templates/` for:
- Connection patterns: `common/iris_connection_manager.py`
- Password reset: `tests/utils/iris_password_reset.py`
- Testing utilities: `tests/utils/`, `tests/fixtures/`
- pytest fixtures: `tests/conftest.py` (Feature 028 sections)

## Common Tasks

### Adding a New Module

```bash
# Create module file
touch iris_devtester/new_module/module_name.py

# Add __init__.py
cat > iris_devtester/new_module/__init__.py << 'EOF'
"""New module description."""
from .module_name import MainClass

__all__ = ["MainClass"]
EOF

# Create tests
touch tests/unit/test_module_name.py
touch tests/integration/test_module_name_integration.py
```

### Running Tests

```bash
# All tests
pytest

# Specific test type
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=iris_devtester --cov-report=html

# Fast (skip slow tests)
pytest -m "not slow"
```

### Code Quality Checks

```bash
# Format code
black .
isort .

# Type check
mypy iris_devtester/

# Lint
flake8 iris_devtester/

# All checks
black . && isort . && flake8 . && mypy iris_devtester/ && pytest
```

## Important Patterns

### Error Messages (Constitutional Requirement)

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
    "  3. Verify: docker logs iris_db\n"
    "\n"
    "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/\n"
)
```

### Connection Management (Constitutional Requirement)

```python
# Always try DBAPI first, fall back to JDBC
try:
    conn = get_dbapi_connection()
except Exception:
    conn = get_jdbc_connection()  # Fallback
```

### Test Isolation (Constitutional Requirement)

```python
# Each test gets own container or unique namespace
@pytest.fixture(scope="function")
def iris_db():
    with IRISContainer.community() as iris:
        yield iris.get_connection()
    # Automatic cleanup
```

### ObjectScript Patterns (CRITICAL)

**CRITICAL**: ObjectScript is **position-based**, NOT keyword-based like Python!

**Full Documentation**: See `docs/learnings/` for comprehensive patterns:
- [iris-security-users-api.md](docs/learnings/iris-security-users-api.md) - Password management
- [iris-container-readiness.md](docs/learnings/iris-container-readiness.md) - Container health checks
- [iris-backup-patterns.md](docs/learnings/iris-backup-patterns.md) - Export/Import for fixtures

#### Password Reset Pattern (Correct)

```objectscript
// CORRECT - Use PasswordExternal property (triggers PBKDF2 hashing)
Set username = "_SYSTEM"
If ##class(Security.Users).Exists(username, .user, .status) {
    Set user.PasswordExternal = "newpassword"  // NOT user.Password!
    Set user.ChangePassword = 0                 // NOT ChangePasswordAtNextLogin!
    Set user.PasswordNeverExpires = 1
    Set user.AccountNeverExpires = 1
    Set status = user.%Save()
}
Halt
```

#### Property Name Reference

| Correct | Incorrect | Notes |
|---------|-----------|-------|
| `ChangePassword` | `ChangePasswordAtNextLogin` | Controls password-change-required flag |
| `PasswordExternal` | `Password` | Use External to set (triggers hashing) |
| `AccountNeverExpires` | `AccountNeverExpire` | Note trailing 's' |

#### Container Health Check Pattern

```objectscript
// Check if container is ready using official API
Set state = $SYSTEM.Monitor.State()
// 0=OK (ready), 1=Warning, 2=Error, 3=Fatal
If state = 0 {
    Write "Container ready", !
}
```

#### Methods That DO NOT Exist

| Method | Status | Alternative |
|--------|--------|-------------|
| `Security.Users.ChangePassword()` | **Removed in 2004!** | Use `Exists()` + `user.PasswordExternal` |
| `Security.Users.SetPassword()` | Does not exist | Use `user.PasswordExternal` property |

**Key Learnings**:
- The `.variable` syntax means "pass by reference" (required for Exists/Get)
- Property names are case-sensitive: `"PasswordExternal"`, `"ChangePassword"`
- `Write` statement outputs the return value (1 = success)
- Always end with `Halt` to exit cleanly
- `$SYSTEM.Monitor.State()` returns 0 when container is truly ready

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/connection-manager

# Commit with descriptive messages (NO CLAUDE ATTRIBUTION per user instructions)
git commit -m "Add DBAPI-first connection manager with automatic recovery"

# Keep commits focused and atomic
```

## Documentation

All public APIs must have:
- Clear docstrings (Google style)
- Type hints
- Usage examples
- Error conditions explained

Example:
```python
def get_iris_connection(config: Optional[dict] = None) -> Connection:
    """
    Get IRIS database connection with automatic remediation.

    Tries DBAPI first (3x faster), falls back to JDBC if unavailable.
    Automatically resets password if "Password change required" detected.

    Args:
        config: Optional connection configuration. If None, auto-discovers
                from environment variables, .env file, or Docker.

    Returns:
        Database connection ready to use.

    Raises:
        ConnectionError: If connection fails after auto-remediation attempts.
                        Error message includes remediation steps.

    Examples:
        >>> # Zero-config (auto-discovers)
        >>> conn = get_iris_connection()

        >>> # Explicit config
        >>> conn = get_iris_connection({
        ...     "host": "localhost",
        ...     "port": 1972,
        ...     "namespace": "USER"
        ... })
    """
```

## Release Process

Not yet - focus on implementation first. But when ready:

```bash
# Version bump in pyproject.toml
# Build package
python -m build

# Upload to PyPI
twine upload dist/*
```

## Getting Help

- **Constitution**: `CONSTITUTION.md` - Answers "why" questions
- **README**: User-facing documentation
- **Source**: `~/ws/rag-templates/` - Working implementation
- **Specification**: `.specify/feature-request.md` - What to build

## Feature 004: DAT Fixture Management

**Status**: Planned (design phase complete)
**Branch**: `004-dat-fixtures`
**Docs**: `specs/004-dat-fixtures/`

### Quick Overview

Provides fast, reproducible test fixtures by exporting IRIS tables to .DAT files with checksum validation.

**Performance**: 10-100x faster than programmatic test data creation
- Load 10K rows in <10s (vs ~50 minutes programmatically)
- SHA256 checksum validation for data integrity
- Atomic loading with transaction rollback
- Version-controlled fixtures for team sharing

### Module Structure

```
iris_devtester/fixtures/
├── __init__.py           # Public API: DATFixtureLoader, FixtureCreator
├── loader.py             # DATFixtureLoader class (loads .DAT files)
├── creator.py            # FixtureCreator class (exports to .DAT)
├── validator.py          # FixtureValidator class (checksum validation)
├── manifest.py           # FixtureManifest dataclass + schema
└── pytest_plugin.py      # pytest integration (@pytest.mark.dat_fixture)
```

### CLI Commands

```bash
# Create fixture from tables
iris-devtester fixture create --name test-100 --tables RAG.Entities --output ./fixtures/test-100

# Validate fixture integrity
iris-devtester fixture validate --fixture ./fixtures/test-100

# Load fixture into IRIS
iris-devtester fixture load --fixture ./fixtures/test-100

# List available fixtures
iris-devtester fixture list ./fixtures/

# Show fixture info
iris-devtester fixture info --fixture ./fixtures/test-100
```

### Python API

```python
from iris_devtester.fixtures import DATFixtureLoader, FixtureCreator

# Create fixture from namespace
creator = FixtureCreator(container=iris_container)
manifest = creator.create_fixture(
    fixture_id="test-100",
    namespace="SOURCE_NS",
    output_dir="./fixtures/test-100"
)

# Load fixture into new namespace
loader = DATFixtureLoader(container=iris_container)
target_ns = iris_container.get_test_namespace(prefix="TARGET")
result = loader.load_fixture(
    fixture_path="./fixtures/test-100",
    target_namespace=target_ns
)
print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")

# Cleanup
loader.cleanup_fixture(target_ns, delete_namespace=True)
```

### pytest Integration

```python
# Use pytest fixtures for DAT fixture management
@pytest.fixture
def loaded_fixture(iris_container):
    """Load DAT fixture for tests."""
    loader = DATFixtureLoader(container=iris_container)
    target_ns = iris_container.get_test_namespace(prefix="TEST")

    result = loader.load_fixture(
        fixture_path="./fixtures/test-100",
        target_namespace=target_ns
    )

    yield result

    # Cleanup
    loader.cleanup_fixture(target_ns, delete_namespace=True)

def test_entity_count(loaded_fixture):
    """Test using loaded DAT fixture."""
    assert loaded_fixture.success
    assert len(loaded_fixture.tables_loaded) > 0
```

### Key Design Decisions

1. **ObjectScript via DBAPI**: Use `$SYSTEM.OBJ.Export()` and `$SYSTEM.OBJ.Load()` for .DAT operations
2. **SHA256 checksums**: Cryptographic validation for medical-grade reliability
3. **Transaction-based loading**: Atomic all-or-nothing with automatic rollback
4. **Dataclasses for manifest**: Zero dependencies, simple validation
5. **Flat directory structure**: Git-friendly, easy to inspect

### Constitutional Compliance

- ✅ Principle #2: DBAPI First (inherits from Feature 003)
- ✅ Principle #4: Zero Configuration (auto-discovers IRIS connection)
- ✅ Principle #5: Fail Fast with Guidance (structured error messages)
- ✅ Principle #7: Medical-Grade Reliability (100% checksum validation)

### Reference Documentation

- Spec: `specs/004-dat-fixtures/spec.md`
- Plan: `specs/004-dat-fixtures/plan.md`
- Research: `specs/004-dat-fixtures/research.md`
- Data Model: `specs/004-dat-fixtures/data-model.md`
- Contracts: `specs/004-dat-fixtures/contracts/`
- Quickstart: `specs/004-dat-fixtures/quickstart.md`

---

## Feature 014: Defensive Container Validation

**Status**: Complete
**Branch**: `014-address-this-enhancement`
**Docs**: `specs/014-address-this-enhancement/`

### Quick Overview

Provides defensive validation for Docker container health with automatic detection of common failure modes like stale container ID references, stopped containers, and network accessibility issues.

**Performance**: Progressive validation with strict SLA targets
- MINIMAL level: <500ms (just running status)
- STANDARD level: <1000ms (running + exec accessibility)
- FULL level: <2000ms (STANDARD + IRIS health check)
- Caching with 5-second TTL for repeated checks

### Module Structure

```
iris_devtester/containers/
├── models.py           # ContainerHealthStatus, HealthCheckLevel, ValidationResult, ContainerHealth
├── validation.py       # validate_container(), ContainerValidator class
└── iris_container.py   # IRISContainer.validate(), assert_healthy() methods
```

### Python API

```python
from iris_devtester.containers import (
    validate_container,
    ContainerValidator,
    HealthCheckLevel,
    IRISContainer
)

# Standalone validation function
result = validate_container(
    container_name="iris_db",
    level=HealthCheckLevel.STANDARD
)

if not result.success:
    print(result.format_message())  # Structured error message

# Stateful validator with caching
validator = ContainerValidator("iris_db", cache_ttl=5)
result = validator.validate(level=HealthCheckLevel.FULL)
health = validator.get_health()  # Detailed metadata

# IRISContainer integration
with IRISContainer.community() as iris:
    # Validate container health
    result = iris.validate(level=HealthCheckLevel.STANDARD)

    # Or assert healthy (raises on failure)
    iris.assert_healthy()
```

### Validation Levels

**MINIMAL** (<500ms target):
- Container exists
- Container running status

**STANDARD** (<1000ms target):
- MINIMAL checks
- Exec accessibility test (can run commands)

**FULL** (<2000ms target):
- STANDARD checks
- IRIS-specific health check (database responsive)

### Health Statuses

- `HEALTHY`: Container running and accessible
- `RUNNING_NOT_ACCESSIBLE`: Running but exec commands fail
- `NOT_RUNNING`: Container exists but stopped
- `NOT_FOUND`: Container doesn't exist
- `STALE_REFERENCE`: Container ID changed (recreated)
- `DOCKER_ERROR`: Docker daemon communication failed

### Error Messages

All error messages follow Constitutional Principle #5 (Fail Fast with Guidance):

```
Container validation failed for 'iris_db'

What went wrong:
  Container 'iris_db' does not exist.

How to fix it:
  1. List all containers:
     docker ps -a
  2. Start container if it exists:
     docker start iris_db
  3. Or create new container:
     docker run -d --name iris_db intersystemsdc/iris-community:latest

Available containers:
  - iris_test (running)
  - iris_prod (exited)
```

### Use Cases

1. **Pre-flight checks**: Validate container before operations
2. **Debugging**: Identify why container operations fail
3. **Monitoring**: Track container health over time
4. **CI/CD**: Ensure test infrastructure is healthy

### Key Design Decisions

1. **Progressive validation**: Fail fast at each level for performance
2. **Factory pattern**: Type-safe ValidationResult creation
3. **Caching strategy**: 5-second TTL balances freshness and performance
4. **Docker SDK**: Native Python library (no shell commands)
5. **Structured error messages**: Following Constitutional Principle #5

### Constitutional Compliance

- ✅ Principle #1: Automatic detection of issues (no manual checks)
- ✅ Principle #5: Fail Fast with Guidance (structured error messages)
- ✅ Principle #7: Medical-Grade Reliability (comprehensive test coverage)

### Test Coverage

- **Contract tests**: 26 tests (data models + API contracts)
- **Integration tests**: 31 tests (real Docker containers)
- **Total**: 57 tests, all passing
- **Performance**: All SLAs verified (<500ms, <1000ms, <2000ms)

### Reference Documentation

- Spec: `specs/014-address-this-enhancement/spec.md`
- Plan: `specs/014-address-this-enhancement/plan.md`
- Quickstart: `specs/014-address-this-enhancement/quickstart.md`
- Contracts: `specs/014-address-this-enhancement/contracts/`
- Data Model: `specs/014-address-this-enhancement/data-model.md`

---

## Important Reminders

1. **Don't rewrite what works** - Extract and enhance proven code
2. **Constitutional compliance is mandatory** - All 8 principles
3. **95% coverage minimum** - This is medical-grade software
4. **No Claude attribution** - Per user's global instructions
5. **Document blind alleys** - Help future developers
6. **ALWAYS enable CallIn service** - DBAPI connections require it (see docs/learnings/callin-service-requirement.md)

---

**Remember**: This package codifies years of production experience. Every feature represents real debugging hours saved. Build on that foundation.

---

## Feature 015: Password Reset Reliability on macOS

**Status**: Planning Complete (Phase 1 complete, ready for /tasks)
**Branch**: `015-fix-iris-devtester`
**Docs**: `specs/015-fix-iris-devtester/`
**Priority**: CRITICAL - Blocks all iris-devtester usage on macOS

### Quick Overview

Fixes critical macOS-specific password reset bug where `reset_password()` returns success (exit code 0) but connections fail with "Access Denied". Root cause is timing race condition - the current `time.sleep(2)` is insufficient for macOS Docker Desktop networking delays (4-6 seconds).

**Solution**: Add connection-based verification with exponential backoff retry logic (adaptive to system speed).

**Performance**: 
- macOS average: 3.2s verification time (99.5% success rate)
- Linux average: 1.1s verification time (100% success rate)
- Timeout: 10s hard limit (NFR-004)

### Module Structure

```
iris_devtester/utils/
├── password_reset.py         # MODIFIED: Add verification + retry logic
└── password_verification.py  # NEW: Connection verification utilities

iris_devtester/containers/
└── iris_container.py          # MODIFIED: Enhanced get_connection() wait logic

tests/
├── contract/
│   ├── test_reset_verification_contract.py   # NEW: 5 verification contract tests
│   └── test_retry_logic_contract.py          # NEW: 7 retry logic contract tests
└── integration/
    ├── test_password_reset_macos.py          # NEW: macOS-specific timing tests
    └── test_password_reset_timing.py         # NEW: Cross-platform benchmarks
```

### Data Entities (from data-model.md)

**PasswordResetResult**:
```python
@dataclass
class PasswordResetResult:
    success: bool
    message: str
    verification_attempts: int
    elapsed_seconds: float
    error_type: Optional[str] = None  # "timeout", "access_denied", "verification_failed"
```

**VerificationConfig**:
```python
@dataclass
class VerificationConfig:
    max_retries: int = 3              # 99.5% success rate on macOS
    initial_wait: float = 1.0         # Minimum IRIS processing time
    retry_interval: float = 2.0       # Base backoff interval (2s, 4s, 5s)
    max_interval: float = 5.0         # Cap exponential growth
    timeout: float = 10.0             # NFR-004 hard limit
    verify_via_dbapi: bool = True     # Constitutional Principle #2
```

**ConnectionVerificationResult** (internal):
```python
@dataclass
class ConnectionVerificationResult:
    success: bool
    error_type: str  # "timeout", "access_denied", "connection_refused", "network_error"
    attempt_number: int
    elapsed_ms: int
    is_retryable: bool  # True for timing issues, False for real failures
```

### Python API

**Basic Usage (Unchanged)**:
```python
from iris_devtester.utils.password_reset import reset_password

# Verification happens automatically
success, message = reset_password(
    container_name="iris_db",
    username="SuperUser",
    new_password="SYS"
)

if success:
    print(f"✓ {message}")  # "Password verified in 3.2s (attempt 2)"
```

**Advanced Usage (With Custom Config)**:
```python
from iris_devtester.utils.password_reset import reset_password_verified
from iris_devtester.utils.password_verification import VerificationConfig

# Custom config for slow systems
config = VerificationConfig(max_retries=5, timeout=15.0)

result = reset_password_verified(
    container_name="iris_db",
    username="SuperUser",
    new_password="SYS",
    config=config
)

print(f"Success: {result.success}")
print(f"Attempts: {result.verification_attempts}")
print(f"Elapsed: {result.elapsed_seconds:.2f}s")
```

**Automatic in IRISContainer**:
```python
from iris_devtester.containers import IRISContainer

# get_connection() now includes verification
with IRISContainer.community() as iris:
    conn = iris.get_connection()  # ✅ Verifies password works before returning
```

### Key Functional Requirements

- **FR-002**: Verify password reset completed successfully (via DBAPI connection test)
- **FR-003**: Wait for IRIS to fully process password changes (retry with backoff)
- **FR-007**: Retry connection attempts if timing fails (exponential backoff, max 3 retries)
- **NFR-001**: 99.9% password reset success rate (99.5% measured with 3 retries)
- **NFR-004**: <10s password verification (hard timeout enforced)

### Retry Strategy

**Exponential Backoff Schedule**:
```
Attempt 1: t=1.0s   (initial wait)
Attempt 2: t=3.0s   (wait 2.0s)
Attempt 3: t=7.0s   (wait 4.0s)
Attempt 4: t=12.0s  (timeout at 10s)
```

**Error Classification**:
- **Retryable** (timing issues): "Access Denied", "Password change required", "Authentication failed"
- **Non-Retryable** (real failures): "Connection refused", "Timeout", "Network error", "Unknown host"

### Performance Benchmarks

| Metric | macOS | Linux | Target (NFR) |
|--------|-------|-------|--------------|
| Average verification | 3.2s | 1.1s | <10s (NFR-004) ✅ |
| 99th percentile | 8.1s | 2.3s | <10s (NFR-004) ✅ |
| Success rate | 99.5% | 100% | 99.9% (NFR-001) ✅ |
| Startup impact | +3s | +1s | <30s (NFR-005) ✅ |

### Root Cause Analysis (from research.md)

**macOS Docker Desktop Architecture**:
- Uses VM-based networking (not native like Linux)
- Networking stack: macOS → Docker Desktop VM → IRIS container
- Password change propagates through IRIS internal caches/services
- **Timing gap**: ObjectScript completion ≠ IRIS service readiness
- Observed delay: 4-6 seconds on macOS vs <1 second on Linux

**Current Bug** (password_reset.py:154-158):
```python
if result.returncode == 0 and "1" in result.stdout:
    time.sleep(2)  # ← INSUFFICIENT on macOS!
    logger.info(f"✓ Password reset successful for user '{username}'")
    return True, f"Password reset successful for user '{username}'"
```

**Fixed Implementation**:
```python
if result.returncode == 0 and "1" in result.stdout:
    # Verify password actually works via connection test
    success, msg = verify_password_change(
        container_name=container_name,
        username=username,
        password=new_password,
        max_retries=3,
        timeout=10.0
    )
    return (success, msg)
```

### Contract Tests (12 total)

**Verification Contracts** (5 tests in `test_reset_verification_contract.py`):
1. ✅ Verify password before returning success (FR-002)
2. ✅ No false positives (ObjectScript success ≠ password ready)
3. ✅ Verification uses actual DBAPI connection
4. ✅ Timeout enforcement (10s hard limit, NFR-004)
5. ✅ Verification attempts logged (Constitutional Principle #7)

**Retry Logic Contracts** (7 tests in `test_retry_logic_contract.py`):
1. ✅ Retry on retryable errors (FR-007)
2. ✅ Exponential backoff between retries
3. ✅ Early exit on success (don't exhaust retries)
4. ✅ Fail fast on non-retryable errors (Constitutional Principle #5)
5. ✅ Respect max_retries limit (bounded retry)
6. ✅ Timeout overrides retry count (NFR-004)
7. ✅ Retry metadata in result (diagnostic data)

### Constitutional Compliance

- ✅ Principle #1: Automatic Remediation - Verification + retry eliminates manual debugging
- ✅ Principle #2: Right Tool - DBAPI for verification (fast), docker exec for password mgmt
- ✅ Principle #5: Fail Fast with Guidance - Timeout prevents hanging, detailed errors
- ✅ Principle #7: Medical-Grade Reliability - 99.5%+ success rate, comprehensive tests

### Migration Path

**Backward Compatible**:
```python
# Old API still works (Tuple[bool, str]):
success, message = reset_password(container, user, pwd)

# New API available (PasswordResetResult):
result = reset_password_verified(container, user, pwd)
```

### Troubleshooting

**Verification Timeout**:
```python
# Use custom config with longer timeout
config = VerificationConfig(timeout=30.0, max_retries=5)
result = reset_password_verified(container, user, pwd, config)
```

**All Retries Exhausted**:
```bash
# Check IRIS logs
docker logs <container_name>

# Manual reset via Management Portal
open http://localhost:<port>/csp/sys/UtilHome.csp
```

### Reference Documentation

- Spec: `specs/015-fix-iris-devtester/spec.md`
- Plan: `specs/015-fix-iris-devtester/plan.md`
- Research: `specs/015-fix-iris-devtester/research.md` (root cause analysis)
- Data Model: `specs/015-fix-iris-devtester/data-model.md` (3 entities)
- Contracts: `specs/015-fix-iris-devtester/contracts/` (12 contract tests)
- Quickstart: `specs/015-fix-iris-devtester/quickstart.md` (5-minute validation)

### Next Steps

**Phase 2**: Create tasks.md via `/tasks` command (not done by /plan)
**Phase 3-4**: Implementation (TDD: contract tests → implementation → integration tests)
**Phase 5**: Validation on macOS + Linux, performance benchmarks, release v1.5.0

---

## Cost Optimization Strategy

This project uses model tiering to minimize costs:

### Model Tiers

| Model | Use For | Cost |
|-------|---------|------|
| **Haiku** | Clarifying specs, small edits, task breakdown, quick Q&A | Lowest |
| **Sonnet** | Planning, validating, coordinating, code review | Moderate |
| **Gemini Flash** (via `gemini_implement` MCP tool) | Code implementation, refactors, multi-file edits | Low |
| **Opus** | Cross-service architecture, complex reasoning | Highest - sparingly |

### MCP Tools

The Gemini MCP server provides cost-effective code generation:

```bash
# Use gemini_implement for code changes
mcp__gemini-impl__gemini_implement({
  instructions: "Add user authentication endpoint",
  target_files: ["api/routes.py"],
  base_dir: "/path/to/project"
})

# Review code without changes
mcp__gemini-impl__gemini_review({
  code: "...",
  focus: "security"
})

# Explain code
mcp__gemini-impl__gemini_explain({
  code: "...",
  question: "What does this function do?"
})

# Health check
mcp__gemini-impl__gemini_health()
```

### Workflow

1. Stay on **Sonnet** (or **opusplan**) for most work
2. Use **Haiku** for simple clarifications
3. Call **`gemini_implement`** for heavy code generation
4. Only use **Opus** for complex architecture decisions

### Configuration

- `.mcp.json` - Gemini MCP server registration
- `.specify/model-routing.yaml` - Phase-specific model routing
- `.claude/agents/spec-implementer.md` - Implementation agent

