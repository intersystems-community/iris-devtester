# Implementation Plan: Fix reset_password() Bug - Password Not Actually Being Set

**Branch**: `007-fix-reset-password` | **Date**: 2025-01-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-fix-reset-password/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ COMPLETE: Spec loaded from /Users/tdyar/ws/iris-devtester/specs/007-fix-reset-password/spec.md
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ COMPLETE: No NEEDS CLARIFICATION - bug well-documented with tested solution
3. Fill the Constitution Check section
   → ✅ COMPLETE: Aligned with Principles #1, #5, #7
4. Evaluate Constitution Check section
   → ✅ COMPLETE: No violations, constitutional compliance confirmed
5. Execute Phase 0 → research.md
   → ✅ COMPLETE: research.md created
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → ✅ COMPLETE: All artifacts created
7. Re-evaluate Constitution Check section
   → ✅ COMPLETE: No new violations
8. Plan Phase 2 → Describe task generation approach
   → ✅ COMPLETE: Task strategy defined
9. STOP - Ready for /tasks command
   → PENDING
```

## Summary

Fix critical bug in `reset_password()` function where it reports success but doesn't actually set the user's password. The function currently uses wrong IRIS Security API property names (`ExternalPassword` instead of `Password`, `ChangePassword=0` instead of `PasswordNeverExpires=1`) and is missing required `Get()` call before `Modify()`. This affects ALL users attempting to configure IRIS passwords via iris-devtester, causing "Access Denied" errors despite function returning success.

**Root Cause**: Lines 120-121 of password_reset.py use incorrect ObjectScript
**Tested Solution**: User verified working fix on AWS EC2 IRIS Community 2025.1
**Impact**: CRITICAL - All password configuration workflows broken

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: docker (subprocess), testcontainers>=4.0.0, intersystems-irispython>=3.2.0
**Storage**: IRIS Security.Users (system object)
**Testing**: pytest with integration tests, IRIS Community container
**Target Platform**: Linux, macOS, Windows (Docker required)
**Project Type**: Single (existing utility function bug fix)
**Performance Goals**: <10 seconds for password reset (no regression from current)
**Constraints**: Maintain backward compatibility (function signature unchanged)
**Scale/Scope**: Bug fix in 1 function, 2 test files (unit + integration)

**Additional Context**:
- Tested working solution from production user on AWS EC2
- Must work with both IRIS Community and Enterprise editions
- Docker exec pattern for ObjectScript execution
- Constitutional Principle #1 (Automatic Remediation) compliance
- Constitutional Principle #5 (Fail Fast with Guidance) compliance
- Constitutional Principle #7 (Medical-Grade Reliability) compliance - 95%+ coverage

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle #1: Automatic Remediation Over Manual Intervention
- ✅ **ALIGNED**: Fix ensures password reset actually works automatically
- ✅ No manual ObjectScript intervention required after fix
- ✅ Maintains existing automatic retry and error handling

### Principle #2: Choose the Right Tool for the Job
- ✅ **ALIGNED**: Uses docker exec for password management (correct tool per constitution)
- ✅ User/password management requires docker exec (see constitution table)
- ✅ Will verify with DBAPI connection test (correct tool for SQL validation)

### Principle #5: Fail Fast with Guidance
- ✅ **ALIGNED**: Maintains existing error message structure with remediation
- ✅ Function returns (bool, str) with clear success/failure indication
- ✅ Existing error messages preserved (Constitutional format)

### Principle #7: Medical-Grade Reliability
- ✅ **ALIGNED**: Will maintain 95%+ test coverage
- ✅ Integration tests will verify password ACTUALLY set (not just function success)
- ✅ Idempotent operation (safe to call multiple times)
- ✅ All error paths tested

**GATE STATUS**: ✅ PASS - All applicable constitutional principles aligned

## Project Structure

### Documentation (this feature)
```
specs/007-fix-reset-password/
├── spec.md              # Feature specification (exists)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (in progress)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
├── contracts/           # Phase 1 output (pending)
│   └── reset_password_contract.md
└── tasks.md             # Phase 2 output (/tasks command)
```

### Source Code (repository root)
```
iris_devtester/
├── utils/
│   ├── __init__.py              # Exports reset_password
│   └── password_reset.py        # BUG HERE (lines 120-121, 170)
│
└── cli/
    └── container.py             # CLI uses reset_password (also affected)

tests/
├── unit/
│   └── test_password_reset.py   # Unit tests for reset_password
│
└── integration/
    └── test_password_reset_integration.py  # Integration tests (NEW)
```

**Structure Decision**: Single project structure. This is a bug fix in existing `iris_devtester/utils/password_reset.py` module with new integration tests to verify password is actually set.

## Phase 0: Outline & Research

**Status**: ✅ COMPLETE

### Research Tasks

1. **IRIS Security.Users API** ✅
   - **Decision**: Use `Password` property (not `ExternalPassword`)
   - **Rationale**: User verified on AWS EC2 that `Set prop("Password")="value"` works
   - **Evidence**: Production feedback document, tested working solution
   - **Reference**: IRIS Security.Users API documentation

2. **IRIS Security API Pattern** ✅
   - **Decision**: Must call `Get()` before `Modify()`
   - **Rationale**: IRIS API requirement - Get() retrieves all properties, Modify() updates them
   - **Evidence**: User's working solution shows: `Set sc = ##class(Security.Users).Get(...,.prop)`
   - **Pattern**: Get → Set properties → Modify

3. **PasswordNeverExpires vs ChangePassword** ✅
   - **Decision**: Use `PasswordNeverExpires=1` (not `ChangePassword=0`)
   - **Rationale**: PasswordNeverExpires prevents expiration, ChangePassword is for "change on next login"
   - **Evidence**: User's tested solution uses `Set prop("PasswordNeverExpires")=1`
   - **Impact**: Prevents password expiration issues

4. **Docker Exec ObjectScript Pattern** ✅
   - **Decision**: Execute multi-line ObjectScript via bash -c with escaped quotes
   - **Current**: Single-line `set props(...)` without Get()
   - **Fixed**: Multi-line with Get() → Set → Modify pattern
   - **Rationale**: Per Constitution #2, password management requires docker exec

5. **Testing Strategy** ✅
   - **Decision**: Integration test that verifies password ACTUALLY set
   - **Rationale**: Current tests only check function return value, not actual password change
   - **Tests needed**:
     1. Verify password set via Security.Users query
     2. Verify connection succeeds with new password
     3. Verify PasswordNeverExpires=1
     4. Verify idempotency (multiple calls work)
   - **Approach**: Use testcontainers IRIS instance, reset password, verify with DBAPI connection

**Output**: research.md (generated below)

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETE

### Data Model

Entity: Security.Users (IRIS system object)
- **Password** (string, hashed): The actual password value
- **PasswordNeverExpires** (0/1): Flag controlling password expiration
- ~~ExternalPassword~~ (WRONG property, do not use)
- ~~ChangePassword~~ (WRONG flag for our use case)

See: `data-model.md`

### API Contracts

**Function**: `reset_password(container_name: str, username: str, new_password: str, timeout: int) -> Tuple[bool, str]`

**Contract**:
- **Input**: Container name, username, new password, timeout
- **Output**: (success: bool, message: str)
- **Postcondition** (CRITICAL): If success=True, password MUST be set in IRIS
- **Postcondition**: If success=True, PasswordNeverExpires MUST = 1
- **Idempotent**: Safe to call multiple times with same password

**Current Bug**:
- Returns (True, "success") but password NOT set
- Uses wrong ObjectScript properties

**Fixed Behavior**:
- Returns (True, "success") AND password IS set
- Uses correct ObjectScript: Get() → Password → PasswordNeverExpires → Modify()

See: `contracts/reset_password_contract.md`

### Contract Tests

Tests are integration tests (require real IRIS container):

1. `test_reset_password_actually_sets_password()`
   - Reset password to "TESTPWD123"
   - Query Security.Users via ObjectScript
   - Assert password property changed

2. `test_reset_password_connection_succeeds()`
   - Reset password to "TESTPWD123"
   - Attempt DBAPI connection with new password
   - Assert connection succeeds (no "Access Denied")

3. `test_reset_password_sets_password_never_expires()`
   - Reset password
   - Query Security.Users for PasswordNeverExpires
   - Assert PasswordNeverExpires = 1

4. `test_reset_password_idempotent()`
   - Call reset_password() 3 times with same password
   - Assert all 3 calls return success
   - Assert password still works

See: `tests/integration/test_password_reset_integration.py`

### Quickstart Test

```python
# Quickstart: Verify password reset bug is fixed
from iris_devtester.containers import IRISContainer
from iris_devtester.utils.password_reset import reset_password

# Start IRIS container
with IRISContainer.community() as iris:
    container_name = iris.container.name

    # Reset password
    success, msg = reset_password(
        container_name=container_name,
        username="_SYSTEM",
        new_password="NEWPASS123"
    )

    # Verify success
    assert success, f"Reset failed: {msg}"

    # CRITICAL: Verify password ACTUALLY changed
    conn = iris.get_connection(password="NEWPASS123")
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1

    print("✅ Password reset bug FIXED - password actually set!")
```

See: `quickstart.md`

### Agent Context Update

Updated CLAUDE.md with:
- Feature 007: reset_password() bug fix
- IRIS Security.Users API pattern (Get → Modify)
- Critical: Test password is ACTUALLY set, not just function success

## Phase 2: Task Planning Approach

**Status**: ✅ COMPLETE (description only - /tasks command will execute)

**Task Generation Strategy**:

1. **TDD Approach** (Constitutional Principle #7):
   - Write integration tests FIRST (red)
   - Implement fix (green)
   - Verify all tests pass (refactor)

2. **Task Ordering**:
   - [P] Create research.md
   - [P] Create data-model.md
   - [P] Create contracts/reset_password_contract.md
   - [P] Create quickstart.md
   - Write integration test: `test_reset_password_actually_sets_password` [MUST FAIL]
   - Write integration test: `test_reset_password_connection_succeeds` [MUST FAIL]
   - Write integration test: `test_reset_password_sets_password_never_expires` [MUST FAIL]
   - Write integration test: `test_reset_password_idempotent` [MUST FAIL]
   - Run integration tests → ALL FAIL (expected)
   - Fix primary method (lines 120-121): Add Get(), use Password, use PasswordNeverExpires
   - Fix fallback method (line 170): Same changes
   - Update unit tests if needed
   - Run integration tests → ALL PASS
   - Update CHANGELOG.md (v1.0.2 - Critical bug fix)
   - Update pyproject.toml version to 1.0.2
   - [P] Manual test on local IRIS Community
   - [P] Request user test on AWS EC2

3. **Parallelization**:
   - [P] = Parallel execution possible (documentation tasks)
   - Sequential: Tests before implementation (TDD)
   - Sequential: Implementation before validation

**Estimated Tasks**: 18 numbered tasks in tasks.md

**IMPORTANT**: The /tasks command will generate the full tasks.md file based on this approach.

## Phase 3+: Future Implementation

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following TDD)
**Phase 5**: Validation (run tests, execute quickstart.md, verify on AWS EC2)

## Complexity Tracking

**No violations** - This fix SIMPLIFIES the codebase by fixing a critical bug with a well-tested solution.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete
- [x] Phase 1: Design complete
- [x] Phase 2: Task planning approach described
- [x] Phase 3: Tasks generated (/tasks command) - 14 tasks created
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---

**Status**: ✅ READY FOR /tasks COMMAND

The planning phase is complete. All research is done, design decisions are made, and the task generation approach is defined. The next step is to run `/tasks` to generate the detailed task list in tasks.md.

---

*Based on IRIS DevTools Constitution v1.0.0 - See `CONSTITUTION.md`*
