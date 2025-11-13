# Tasks: Fix reset_password() Bug - Password Not Actually Being Set

**Feature**: 007-fix-reset-password
**Input**: Design documents from `/specs/007-fix-reset-password/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/reset_password_contract.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✅ COMPLETE: Tech stack: Python 3.9+, testcontainers, DBAPI
2. Load optional design documents:
   → ✅ data-model.md: Security.Users entity
   → ✅ contracts/: reset_password() contract
   → ✅ research.md: IRIS API pattern (Get → Modify)
3. Generate tasks by category:
   → Setup: N/A (existing project)
   → Tests: 4 integration tests (TDD red)
   → Core: Fix password_reset.py (TDD green)
   → Integration: N/A (existing function)
   → Polish: Update CHANGELOG, version, validate
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → ✅ All contracts have tests
   → ✅ TDD approach (red → green)
   → ✅ All functional requirements covered
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Project type**: Single (existing Python package)
- **Repository root**: `/Users/tdyar/ws/iris-devtester/`
- **Source**: `iris_devtester/utils/password_reset.py`
- **Tests**: `tests/integration/test_password_reset_integration.py`

---

## Phase 3.1: Setup
*No setup required - existing project with dependencies already configured*

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

These integration tests verify the bug fix works correctly. All tests should FAIL initially (red), then PASS after implementation (green).

- [ ] **T001** [P] Write integration test `test_reset_password_actually_sets_password()` in `tests/integration/test_password_reset_integration.py`
  - **Purpose**: Verify password is ACTUALLY set (not just function returning success)
  - **Contract**: FR-001, FR-002, FR-003 from reset_password_contract.md
  - **Test steps**:
    1. Start IRIS container with IRISContainer.community()
    2. Call reset_password() with new password "TESTPWD123"
    3. Assert function returns (True, "success")
    4. **CRITICAL**: Attempt DBAPI connection with new password
    5. Assert connection succeeds (password was actually set)
  - **Expected**: ❌ MUST FAIL initially (bug exists)
  - **File**: `tests/integration/test_password_reset_integration.py`

- [ ] **T002** [P] Write integration test `test_reset_password_connection_succeeds()` in `tests/integration/test_password_reset_integration.py`
  - **Purpose**: Verify DBAPI connection succeeds with new password
  - **Contract**: FR-010 from reset_password_contract.md
  - **Test steps**:
    1. Reset password to "NEWPASS"
    2. Create DBAPI connection with new password
    3. Execute "SELECT 1" query
    4. Assert query succeeds
  - **Expected**: ❌ MUST FAIL initially (bug exists)
  - **File**: `tests/integration/test_password_reset_integration.py`

- [ ] **T003** [P] Write integration test `test_reset_password_sets_password_never_expires()` in `tests/integration/test_password_reset_integration.py`
  - **Purpose**: Verify PasswordNeverExpires=1 is set
  - **Contract**: FR-004, FR-011 from reset_password_contract.md
  - **Test steps**:
    1. Reset password to "PWD123"
    2. Query Security.Users for PasswordNeverExpires property
    3. Assert PasswordNeverExpires = 1
  - **Expected**: ❌ MUST FAIL initially (current code uses ChangePassword=0)
  - **File**: `tests/integration/test_password_reset_integration.py`

- [ ] **T004** [P] Write integration test `test_reset_password_idempotent()` in `tests/integration/test_password_reset_integration.py`
  - **Purpose**: Verify function is idempotent (safe to call multiple times)
  - **Contract**: FR-005 from reset_password_contract.md
  - **Test steps**:
    1. Call reset_password() 3 times with same password "SAMEPWD"
    2. Assert all 3 calls return success
    3. Verify password still works after 3 calls
  - **Expected**: ❌ MAY FAIL initially (depending on bug behavior)
  - **File**: `tests/integration/test_password_reset_integration.py`

- [ ] **T005** Run integration tests to verify they FAIL (TDD red phase)
  - **Command**: `pytest tests/integration/test_password_reset_integration.py -v`
  - **Expected output**: 4 tests FAILED (T001-T004 all fail)
  - **Purpose**: Verify tests are correctly detecting the bug
  - **CRITICAL**: Do NOT proceed to T006 until tests are failing
  - **Note**: If tests pass, they are not correctly written

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

**GATE**: T001-T005 MUST be complete and failing before starting this phase.

- [ ] **T006** Fix primary method (lines 120-121) in `iris_devtester/utils/password_reset.py`
  - **Purpose**: Implement correct IRIS Security.Users API pattern
  - **Requirements**:
    - Change line 120-121 reset_cmd to use correct ObjectScript
    - Add `Get()` call before `Modify()`
    - Change `ExternalPassword` → `Password`
    - Change `ChangePassword=0` → `PasswordNeverExpires=1`
  - **BEFORE** (broken):
    ```python
    f'''echo "set props(\\\"ChangePassword\\\")=0 set props(\\\"ExternalPassword\\\")=\\\"{new_password}\\\" write ##class(Security.Users).Modify(\\\"{username}\\\",.props)" | iris session IRIS -U %SYS'''
    ```
  - **AFTER** (fixed):
    ```python
    f'''echo "set sc = ##class(Security.Users).Get(\\\"{username}\\\",.props) set props(\\\"Password\\\")=\\\"{new_password}\\\" set props(\\\"PasswordNeverExpires\\\")=1 write ##class(Security.Users).Modify(\\\"{username}\\\",.props)" | iris session IRIS -U %SYS'''
    ```
  - **File**: `iris_devtester/utils/password_reset.py` (lines 120-121)
  - **Constitutional compliance**: Maintains FR-006 (backward compatibility)

- [ ] **T007** Fix fallback method (line 170) in `iris_devtester/utils/password_reset.py`
  - **Purpose**: Apply same fix to fallback method for consistency
  - **Requirements**:
    - Update disable_flag_cmd to use same pattern
    - Add Get() → Password → PasswordNeverExpires → Modify()
  - **BEFORE** (line 170):
    ```python
    f'''echo "set props(\\\"ChangePassword\\\")=0 write ##class(Security.Users).Modify(\\\"{username}\\\",.props)" | iris session IRIS -U %SYS'''
    ```
  - **AFTER** (fixed):
    ```python
    f'''echo "set sc = ##class(Security.Users).Get(\\\"{username}\\\",.props) set props(\\\"Password\\\")=\\\"{new_password}\\\" set props(\\\"PasswordNeverExpires\\\")=1 write ##class(Security.Users).Modify(\\\"{username}\\\",.props)" | iris session IRIS -U %SYS'''
    ```
  - **File**: `iris_devtester/utils/password_reset.py` (line 170)
  - **Depends on**: T006 (same pattern)

- [ ] **T008** Run integration tests to verify they PASS (TDD green phase)
  - **Command**: `pytest tests/integration/test_password_reset_integration.py -v`
  - **Expected output**: 4 tests PASSED (T001-T004 all pass)
  - **Purpose**: Verify bug fix works correctly
  - **CRITICAL**: If tests still fail, implementation is incorrect
  - **Depends on**: T006, T007

- [ ] **T009** [P] Review and update unit tests (if needed) in `tests/unit/test_password_reset.py`
  - **Purpose**: Ensure unit tests are compatible with fix
  - **Check**:
    - Verify unit tests don't hardcode broken behavior
    - Update mocks if needed (unlikely for this bug fix)
    - Ensure unit tests still pass
  - **Command**: `pytest tests/unit/test_password_reset.py -v`
  - **Expected**: All unit tests PASS
  - **File**: `tests/unit/test_password_reset.py`

---

## Phase 3.4: Integration
*No additional integration required - bug fix in existing function*

---

## Phase 3.5: Polish

- [ ] **T010** [P] Update CHANGELOG.md with v1.0.2 release notes
  - **Purpose**: Document critical bug fix for users
  - **Content**:
    ```markdown
    ## [1.0.2] - 2025-01-09

    ### Fixed
    - **CRITICAL**: Fixed `reset_password()` bug where function reported success but password was not actually set
      - Now uses correct IRIS Security API property `Password` (not `ExternalPassword`)
      - Now calls `Security.Users.Get()` before `Modify()` per IRIS API requirements
      - Now sets `PasswordNeverExpires=1` to prevent password expiration (not `ChangePassword=0`)
      - Fixes "Access Denied" errors after password reset
      - Verified on AWS EC2, IRIS Community 2025.1
    - Issue reported in production user feedback (IRIS_DEVTESTER_FEEDBACK.md Issue #9)
    ```
  - **File**: `CHANGELOG.md`
  - **Location**: Repository root

- [ ] **T011** [P] Update version in pyproject.toml to 1.0.2
  - **Purpose**: Bump version for patch release
  - **Change**: Line 7: `version = "1.0.1"` → `version = "1.0.2"`
  - **File**: `pyproject.toml`
  - **Location**: Repository root

- [ ] **T012** [P] Run full test suite to verify no regressions
  - **Command**: `pytest -v`
  - **Expected**: All tests PASS, coverage maintained at 95%+
  - **Purpose**: Verify bug fix doesn't break other functionality
  - **Check**:
    - All integration tests pass
    - All unit tests pass
    - No new failures introduced
  - **Constitutional compliance**: Principle #7 (Medical-Grade Reliability)

- [ ] **T013** [P] Run quickstart validation from `specs/007-fix-reset-password/quickstart.md`
  - **Purpose**: Manual verification that bug is fixed
  - **Steps**:
    1. Copy quickstart Python script
    2. Run with local IRIS container
    3. Verify all 4 steps pass
  - **Expected output**:
    ```
    ✅ ALL TESTS PASSED - reset_password() BUG IS FIXED!
    ```
  - **File**: `specs/007-fix-reset-password/quickstart.md`

- [ ] **T014** Create git commit with bug fix
  - **Purpose**: Record fix in version control
  - **Command**:
    ```bash
    git add iris_devtester/utils/password_reset.py \
            tests/integration/test_password_reset_integration.py \
            tests/unit/test_password_reset.py \
            CHANGELOG.md \
            pyproject.toml
    git commit -m "Fix reset_password() bug - password not actually being set

    CRITICAL BUG FIX:
    - reset_password() reported success but password was NOT changed
    - Users experienced 'Access Denied' errors after reset
    - Affected ALL password configuration workflows

    Changes:
    - Use Password property (not ExternalPassword)
    - Use PasswordNeverExpires=1 (not ChangePassword=0)
    - Add Get() call before Modify() per IRIS API requirements

    Tested:
    - AWS EC2, IRIS Community 2025.1
    - 4 new integration tests verify password actually set
    - All tests pass, 95%+ coverage maintained

    Version: 1.0.2 (patch release)
    Fixes: Issue #9 from IRIS_DEVTESTER_FEEDBACK.md"
    ```
  - **Depends on**: T001-T013 all complete

---

## Dependencies

```
Setup: None (existing project)
  ↓
Tests First (TDD Red):
  T001, T002, T003, T004 [P] → T005
  ↓
Core Implementation (TDD Green):
  T005 → T006 → T007 → T008
         T006 → T009 [P]
  ↓
Polish:
  T008 → T010 [P], T011 [P], T012 [P], T013 [P]
  ↓
  T010, T011, T012, T013 → T014
```

## Parallel Execution Examples

### Phase 3.2: Write Integration Tests (Parallel)
```bash
# Launch T001-T004 together (different test functions, same file but independent):
# Note: Writing different functions in same file can be done in parallel
# Each test is independent and doesn't conflict

# T001: test_reset_password_actually_sets_password
# T002: test_reset_password_connection_succeeds
# T003: test_reset_password_sets_password_never_expires
# T004: test_reset_password_idempotent
```

### Phase 3.5: Polish Tasks (Parallel)
```bash
# Launch T010-T013 together (different files, no dependencies):
# T010: Update CHANGELOG.md
# T011: Update pyproject.toml
# T012: Run pytest
# T013: Run quickstart.md
```

## Task Validation Checklist
*GATE: Verify before marking Phase 3 complete*

- [x] All contracts have corresponding tests (reset_password_contract.md → T001-T004)
- [x] All entities have implementation tasks (Security.Users → T006, T007)
- [x] All tests come before implementation (T001-T005 before T006-T007)
- [x] Parallel tasks truly independent (T001-T004 different functions; T010-T013 different files)
- [x] Each task specifies exact file path (all tasks have file paths)
- [x] No task modifies same file as another [P] task (T010-T013 different files)
- [x] TDD approach enforced (T001-T005 must fail, then T006-T007 fix, then T008 verifies)

## Notes

- **TDD Enforcement**: T005 MUST show failing tests before T006 can start
- **Backward Compatibility**: Function signature unchanged (FR-006)
- **Constitutional Compliance**:
  - Principle #1: Automatic Remediation (password reset works automatically)
  - Principle #5: Fail Fast with Guidance (error messages preserved)
  - Principle #7: Medical-Grade Reliability (integration tests + 95% coverage)
- **Performance**: No regression (<10 seconds, FR-012)
- **Platform Support**: Works on Linux, macOS, Windows (FR-008)
- **Testing Environment**: Use testcontainers IRIS Community edition
- **Commit Strategy**: Single atomic commit (T014) after all tests pass

## Success Criteria

✅ **Feature 007 complete when**:
1. All integration tests (T001-T004) FAIL initially
2. Bug fix implemented (T006-T007)
3. All integration tests PASS (T008)
4. Unit tests still pass (T009)
5. Full test suite passes (T012)
6. Quickstart validation passes (T013)
7. CHANGELOG and version updated (T010-T011)
8. Git commit created (T014)

## Total Tasks: 14

- **Setup**: 0 tasks (existing project)
- **Tests (TDD Red)**: 5 tasks (T001-T005)
- **Implementation (TDD Green)**: 4 tasks (T006-T009)
- **Polish**: 5 tasks (T010-T014)

---

**Status**: ✅ READY FOR EXECUTION
**Next**: Execute T001-T005 (write integration tests, verify they fail)
**Critical**: Do NOT skip TDD red phase (T005) - tests must fail before fix
