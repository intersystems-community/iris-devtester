# Implementation Plan: Docker-Compose & Existing Container Support

**Branch**: `006-address-docker-compose` | **Date**: 2025-11-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/tdyar/ws/iris-devtester/specs/006-address-docker-compose/spec.md`

## Summary

Implement CLI commands and standalone utilities to make iris-devtester usable with docker-compose and existing IRIS containers. This addresses critical production feedback where a user **gave up on licensed IRIS and reverted to Community edition** due to UX friction.

**Primary Requirement**: Enable developers to use iris-devtester utilities (password reset, CallIn enable, connection test) on existing containers via:
1. CLI commands for quick operations
2. Standalone Python utilities
3. IR

ISContainer.attach() for existing containers

**Technical Approach**: Follow the proven `password_reset.py` pattern - standalone utilities with (success: bool, message: str) returns, CLI wrappers using Click, and IRISContainer integration methods.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- `click>=8.0.0` (CLI framework, already in pyproject.toml)
- `docker>=6.0.0` (Docker operations, already in pyproject.toml)
- `intersystems-irispython>=3.2.0` (DBAPI for iris.connect(), optional)

**Storage**: N/A (stateless utilities)
**Testing**: pytest with testcontainers-iris for integration tests
**Target Platform**: macOS, Linux (Windows future consideration)
**Project Type**: Single Python package

**Performance Goals**:
- CLI commands complete in <3 seconds (docker exec operations)
- Standalone utilities <500ms overhead
- No performance regression on existing code

**Constraints**:
- MUST maintain backward compatibility (all existing tests pass)
- MUST follow password_reset.py pattern (proven success)
- MUST NOT require IRIS to be running for `--help` commands
- CLI commands must be idempotent (safe to run multiple times)

**Scale/Scope**:
- 15 functional requirements (8 HIGH, 4 MEDIUM, 3 LOW)
- Target: HIGH priority items for v1.0.1 (~2 weeks)
- Estimated: 8 new Python modules, 4 CLI commands, 3 utility functions, 1 example

## Constitution Check

**GATE: Initial Check - PASS ✅**

### Principle #1: Automatic Remediation Over Manual Intervention
- ✅ CLI commands automate docker exec operations (no manual commands)
- ✅ Standalone utilities work without IRISContainer setup
- ✅ Follows password_reset.py remediation pattern

### Principle #2: Choose the Right Tool for the Job
- ✅ Uses docker exec for enable_callin_service (admin operation)
- ✅ Uses iris.connect() if available, docker exec otherwise
- ✅ Properly documents which method is used

### Principle #3: Isolation by Default
- ✅ Utilities are stateless (no shared state)
- ✅ Each container operation is independent
- ✅ No impact on test isolation

### Principle #4: Zero Configuration Viable
- ✅ CLI commands work without configuration
- ✅ Auto-discover containers via `docker ps`
- ✅ Sensible defaults for all operations

### Principle #5: Fail Fast with Guidance
- ✅ Error messages follow structured format (what/why/how)
- ✅ FR-009 specifically addresses error message quality
- ✅ Links to TROUBLESHOOTING.md

### Principle #6: Enterprise Ready, Community Friendly
- ✅ **CRITICAL FIX**: Addresses licensed IRIS UX failure
- ✅ Works with docker-compose (production pattern)
- ✅ Works with testcontainers (development pattern)

### Principle #7: Medical-Grade Reliability
- ✅ Idempotent operations (safe to retry)
- ✅ Comprehensive error handling
- ✅ Unit + integration + contract tests
- ✅ 94%+ coverage requirement

### Principle #8: Document the Blind Alleys
- ✅ FR-013: TROUBLESHOOTING.md with top 5 issues
- ✅ Example showing docker-compose integration
- ✅ AutheEnabled=48 explanation (FR-011)

**Complexity Deviations**: None - follows existing patterns

## Project Structure

### Documentation (this feature)
```
specs/006-address-docker-compose/
├── spec.md              # Feature specification ✅
├── plan.md              # This file (/plan output)
├── research.md          # Phase 0 research (technical decisions)
├── data-model.md        # Phase 1 data model (CLI/utility contracts)
├── quickstart.md        # Phase 1 quickstart validation
├── contracts/           # Phase 1 API contracts
│   ├── cli-commands.yaml
│   ├── standalone-utilities.yaml
│   └── iriscontainer-methods.yaml
└── tasks.md             # Phase 2 (/tasks output)
```

### Source Code (repository root)
```
iris_devtester/
├── utils/
│   ├── password_reset.py        # Existing ✅ (model pattern)
│   ├── unexpire_passwords.py    # Existing ✅
│   ├── enable_callin.py         # NEW - FR-006
│   ├── test_connection.py       # NEW - FR-007
│   ├── container_status.py      # NEW - FR-005 (helper)
│   └── __init__.py              # UPDATE - export new utilities
│
├── cli/
│   ├── __init__.py              # Existing ✅
│   ├── fixture_commands.py      # Existing ✅
│   └── container_commands.py    # NEW - FR-002,003,004,005,015
│
├── containers/
│   └── iris_container.py        # UPDATE - add attach() method (FR-001)
│
└── examples/
    └── 10_docker_compose_integration.py  # NEW - FR-008

docs/
└── TROUBLESHOOTING.md           # NEW - FR-013

README.md                        # UPDATE - FR-010 (document unexpire_passwords)
```

**Structure Decision**: Single Python package with utilities, CLI, and containers modules. Follows existing iris-devtester organization proven in v1.0.0.

## Phase 0: Research & Technical Decisions

**All technical context is clear from existing patterns - no research agents needed.**

### Decision 1: CLI Framework
- **Chosen**: Click (already in dependencies)
- **Rationale**: Already used in `fixture_commands.py`, consistent with existing code
- **Pattern**: Follow `iris-devtester fixture` command structure

### Decision 2: Container Interaction Method
- **Chosen**: Docker exec for admin operations (enable_callin), iris.connect() as fallback
- **Rationale**:
  - Constitutional Principle #2: Choose right tool
  - password_reset.py uses docker exec successfully
  - enable_callin requires ObjectScript admin operations
- **Fallback**: iris.connect() if container name resolves to connection params

### Decision 3: Standalone Utility Pattern
- **Chosen**: Follow password_reset.py exactly
  ```python
  def utility(container_name: str, ...) -> Tuple[bool, str]:
      """Returns (success, message)"""
  ```
- **Rationale**: password_reset.py is documented as "Perfect standalone API model" in feedback
- **Benefits**: Consistent API, easy to wrap in CLI, easy to test

### Decision 4: IRISContainer.attach() Implementation
- **Chosen**: Class method returning IRISContainer instance with limited lifecycle
- **Rationale**:
  - Class method pattern consistent with IRISContainer.community()
  - Returns IRISContainer for method compatibility
  - Internal flag `_attached=True` disables lifecycle management
- **API**:
  ```python
  container = IRISContainer.attach("my-container")
  # Utility methods work, lifecycle methods raise error
  ```

### Decision 5: Error Message Structure
- **Chosen**: Multi-line format from Constitutional Principle #5
- **Format**:
  ```
  [ERROR TYPE]

  What went wrong:
    [explanation]

  Likely cause:
    [reason]

  How to fix:
    1. [step]
    2. [step]

  Documentation: [URL]
  ```
- **Rationale**: Already proven in existing error messages, matches FR-009

### Decision 6: Documentation Approach
- **Chosen**: TROUBLESHOOTING.md for common issues, README for API docs
- **Rationale**:
  - Separation of concerns (troubleshooting vs API reference)
  - README already has utility examples (password_reset)
  - TROUBLESHOOTING.md requested explicitly (FR-013)

**Output**: All research complete, no NEEDS CLARIFICATION remain

## Phase 1: Design & Contracts

### Data Model

**ContainerInfo** (internal data structure):
```python
@dataclass
class ContainerInfo:
    """Information about an IRIS container."""
    container_name: str
    is_running: bool
    health_status: Optional[str]  # "healthy", "unhealthy", "starting", None
    callin_enabled: Optional[bool]  # None if can't determine
    password_ok: Optional[bool]  # None if can't test
    connection_test: Optional[str]  # "success", "failed", "unknown"
```

**Utility Result** (return type):
```python
# All utilities return: Tuple[bool, str]
# success: True if operation succeeded, False otherwise
# message: Human-readable result/error message
```

**CLI Command Result** (exit codes):
```python
# Exit codes for CLI commands
SUCCESS = 0
ERROR = 1
CONTAINER_NOT_FOUND = 2
OPERATION_FAILED = 3
```

### API Contracts

**Standalone Utilities** (iris_devtester/utils/):

```python
# enable_callin.py
def enable_callin_service(
    container_name: str = "iris_db",
    timeout: int = 30
) -> Tuple[bool, str]:
    """
    Enable CallIn service for DBAPI and embedded Python.

    Returns:
        (True, "CallIn enabled") or
        (False, "Error message with remediation")
    """

# test_connection.py
def test_connection(
    container_name: str = "iris_db",
    namespace: str = "USER",
    timeout: int = 10
) -> Tuple[bool, str]:
    """
    Test connection to IRIS container.

    Returns:
        (True, "Connection successful") or
        (False, "Error message with remediation")
    """

# container_status.py
def get_container_status(
    container_name: str = "iris_db"
) -> Tuple[bool, str]:
    """
    Get comprehensive status of IRIS container.

    Returns:
        (True, "Status report") or
        (False, "Error message")
    """
```

**CLI Commands** (iris-devtester container):

```bash
# Reset password
iris-devtester container reset-password <container_name> [OPTIONS]
  --user TEXT        Username (default: _SYSTEM)
  --password TEXT    New password (default: SYS)
  --help

# Enable CallIn
iris-devtester container enable-callin <container_name> [OPTIONS]
  --help

# Test connection
iris-devtester container test-connection <container_name> [OPTIONS]
  --namespace TEXT   Namespace to test (default: USER)
  --help

# Show status
iris-devtester container status <container_name> [OPTIONS]
  --help

# List containers (FR-015, LOW priority)
iris-devtester container list [OPTIONS]
  --help
```

**IRISContainer Methods**:

```python
class IRISContainer:
    @classmethod
    def attach(cls, container_name: str) -> "IRISContainer":
        """
        Attach to existing container without lifecycle management.

        Raises:
            ValueError: If container not found or not running
        """

    # Existing methods work on attached containers:
    # - enable_callin_service()
    # - get_connection()
    # - reset_password()

    # Lifecycle methods raise error on attached:
    # - start()
    # - stop()
    # - __enter__/__exit__
```

### Contract Tests (to be written)

**File**: `tests/contract/test_enable_callin_api.py`
```python
def test_enable_callin_signature():
    """Contract: enable_callin_service accepts container_name, returns (bool, str)"""

def test_enable_callin_idempotent():
    """Contract: Calling enable_callin twice succeeds both times"""
```

**File**: `tests/contract/test_cli_container_commands.py`
```python
def test_container_reset_password_command_exists():
    """Contract: iris-devtester container reset-password exists"""

def test_container_enable_callin_command_exists():
    """Contract: iris-devtester container enable-callin exists"""
```

**File**: `tests/contract/test_iriscontainer_attach.py`
```python
def test_attach_class_method_exists():
    """Contract: IRISContainer.attach() method exists"""

def test_attach_returns_iriscontainer():
    """Contract: attach() returns IRISContainer instance"""
```

### Quickstart Validation

**File**: `quickstart.md`

Scenario: Developer using docker-compose with licensed IRIS

```bash
# 1. Start IRIS with docker-compose
docker-compose up -d iris-fhir

# 2. Reset password
iris-devtester container reset-password iris-fhir --user _SYSTEM --password ISCDEMO

# 3. Enable CallIn service
iris-devtester container enable-callin iris-fhir

# 4. Test connection
iris-devtester container test-connection iris-fhir

# 5. Check overall status
iris-devtester container status iris-fhir

# Expected output: All operations successful
```

Python API:
```python
from iris_devtester.utils import enable_callin_service, test_connection
from iris_devtester.containers import IRISContainer

# Standalone utilities
success, msg = enable_callin_service("iris-fhir")
assert success, msg

# IRISContainer.attach()
container = IRISContainer.attach("iris-fhir")
conn = container.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")
print(cursor.fetchone())
```

### Agent Context Update

**IMPORTANT**: Not updating agent files during planning phase - this will be done during implementation when code patterns are established.

**Rationale**: Agent context should reflect actual implementation decisions, not planned ones.

## Phase 2: Task Planning Approach

**This section describes what /tasks will do - NOT executed during /plan**

### Task Generation Strategy

**From Contracts (Phase 1)**:
- Each CLI command contract → 2 tasks (contract test [P], implementation)
- Each utility contract → 2 tasks (contract test [P], implementation)
- Each IRISContainer method → 2 tasks (contract test [P], implementation)

**From Requirements (spec.md)**:
- FR-001: IRISContainer.attach() → 3 tasks (contract, impl, integration test)
- FR-002-005: CLI commands → 8 tasks (4 contract, 4 impl)
- FR-006-007: Standalone utilities → 4 tasks (2 contract, 2 impl)
- FR-008: Docker-compose example → 1 task
- FR-009-012: Documentation updates → 4 tasks
- FR-013-015: LOW priority (v1.1.0) → defer

**Testing Strategy**:
- Contract tests first (TDD)
- Unit tests for utilities
- Integration tests for CLI commands (require Docker)
- Example validation (manual or automated)

### Ordering Strategy

**Dependency Order**:
1. Standalone utilities (foundation, no dependencies)
2. CLI commands (depend on utilities)
3. IRISContainer.attach() (depends on utilities)
4. Documentation updates
5. Examples

**Parallel Execution** [P]:
- All contract tests (independent)
- All utility implementations (independent modules)
- All CLI command implementations (independent subcommands)

### Estimated Output

**Total Tasks**: ~30-35 tasks for HIGH priority items

**Categories**:
- Contract tests: 10 tasks [P]
- Utility implementations: 5 tasks [P]
- CLI implementations: 5 tasks [P]
- IRISContainer.attach(): 3 tasks
- Integration tests: 8 tasks
- Documentation: 4 tasks
- Example: 1 task

**IMPORTANT**: /tasks command will generate detailed tasks.md from Phase 1 artifacts

## Complexity Tracking

**No constitutional violations** - all patterns follow existing code

| Aspect | Approach | Justification |
|--------|----------|---------------|
| Docker dependency | CLI requires docker exec | Existing pattern (password_reset.py), no simpler alternative for admin operations |
| Click dependency | CLI framework | Already in dependencies, proven in fixture_commands.py |
| Tuple returns | (bool, str) pattern | Existing pattern (password_reset.py), simpler than exceptions for utilities |

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete
- [x] Phase 1: Design complete
- [x] Phase 2: Task planning approach described
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

**Requirements Coverage**:
- HIGH Priority (v1.0.1): 8 requirements fully designed
- MEDIUM Priority (v1.0.1/v1.1.0): 4 requirements spec'd
- LOW Priority (v1.1.0): 3 requirements deferred

**Next Step**: Run `/tasks` command to generate tasks.md

---

*Based on IRIS DevTools Constitution v1.0.0 - See `/CONSTITUTION.md`*
