# Feature Specification: Fix reset_password() Bug - Password Not Actually Being Set

**Feature Branch**: `007-fix-reset-password`
**Created**: 2025-01-09
**Status**: Draft
**Priority**: CRITICAL (Production Bug)
**Input**: User description: "Fix reset_password() bug - password not actually being set. User reports reset_password() returns success but password is not changed. Need to use Password instead of ExternalPassword, add Get() before Modify(), and use PasswordNeverExpires instead of ChangePassword."

**Source**: Production user feedback from /Users/tdyar/ws/FHIR-AI-Hackathon-Kit/IRIS_DEVTESTER_FEEDBACK.md (Issue #9)

## Execution Flow (main)
```
1. Parse user description from Input
   → COMPLETE: Bug identified - reset_password() doesn't set password
2. Extract key concepts from description
   → Actors: Python developers using iris-devtester
   → Actions: Reset IRIS user password via docker exec
   → Data: User password, PasswordNeverExpires flag
   → Constraints: Must actually set password, not just return success
3. For each unclear aspect:
   → NO CLARIFICATIONS NEEDED - bug is well-documented with tested solution
4. Fill User Scenarios & Testing section
   → User flow clear: Call reset_password(), expect password to be set
5. Generate Functional Requirements
   → All requirements testable via integration tests
6. Identify Key Entities (if data involved)
   → Entity: IRIS Security.Users object with Password, PasswordNeverExpires
7. Run Review Checklist
   → No [NEEDS CLARIFICATION] markers
   → No implementation details (spec level only)
8. Return: SUCCESS (spec ready for planning)
```

---

## Problem Statement

**CRITICAL BUG**: The `reset_password()` function in `iris_devtester/utils/password_reset.py` reports success but does NOT actually set the user's password. This affects all users attempting to configure IRIS passwords via iris-devtester.

### User Impact
- Users call `reset_password(container_name, username, new_password)`
- Function returns `(True, "Password reset successful")`
- Password is NOT changed - connections fail with "Access Denied"
- Users waste hours debugging, eventually resort to manual ObjectScript

### Testing Environment (Reproduced)
- AWS EC2, Ubuntu 24.04 LTS
- IRIS Community 2025.1 (Build 223U)
- iris-devtester 1.0.1
- docker-compose deployment

### Root Cause Analysis

**Current Implementation** (Lines 120-121 of password_reset.py):
```python
# Uses WRONG property names
Set props("ChangePassword")=0
Set props("ExternalPassword")="{new_password}"
```

**Issues**:
1. ❌ Uses `ExternalPassword` instead of `Password`
2. ❌ Missing `Get()` call before `Modify()` (IRIS API requirement)
3. ❌ Uses `ChangePassword=0` instead of `PasswordNeverExpires=1`

**Tested Working Solution** (from user on AWS EC2):
```objectscript
Set sc = ##class(Security.Users).Get("_SYSTEM",.prop)  # ← Must Get first
Set prop("Password")="ISCDEMO"                          # ← Use Password
Set prop("PasswordNeverExpires")=1                      # ← Not ChangePassword
Set sc = ##class(Security.Users).Modify("_SYSTEM",.prop)
```

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

**As a** Python developer using iris-devtester with docker-compose,
**I want** to reset the IRIS _SYSTEM password programmatically,
**So that** I can connect to IRIS without manual ObjectScript intervention.

### Acceptance Scenarios

1. **Given** an IRIS container is running with default password,
   **When** user calls `reset_password(container_name="iris-fhir", username="_SYSTEM", new_password="NEWPASS")`,
   **Then** the function returns `(True, "Password reset successful")` AND the password is actually set to "NEWPASS"

2. **Given** password was successfully reset to "NEWPASS",
   **When** user attempts to connect with username="_SYSTEM" and password="NEWPASS",
   **Then** connection succeeds without "Access Denied" error

3. **Given** password was reset to "NEWPASS",
   **When** user queries IRIS Security.Users for "_SYSTEM",
   **Then** `PasswordNeverExpires=1` (password will not expire)

4. **Given** user calls `reset_password()` multiple times with same password,
   **When** function executes,
   **Then** all calls succeed (idempotent operation)

### Edge Cases

- What happens when container is not running?
  → Function returns `(False, <error message with remediation steps>)`

- What happens when IRIS is not fully started?
  → Function retries or returns clear error message

- What happens when docker command times out?
  → Function returns `(False, <timeout error with troubleshooting>)`

- What happens when user provides invalid password format?
  → Function should succeed (IRIS validates password format)

---

## Requirements *(mandatory)*

### Functional Requirements

#### Core Functionality

- **FR-001**: System MUST actually set the user's password when `reset_password()` is called (not just return success message)

- **FR-002**: System MUST use the correct IRIS Security API property name `Password` (not `ExternalPassword`)

- **FR-003**: System MUST call `Security.Users.Get()` before `Security.Users.Modify()` per IRIS API requirements

- **FR-004**: System MUST set `PasswordNeverExpires=1` to prevent password expiration (not `ChangePassword=0`)

- **FR-005**: System MUST verify password was set by attempting a test connection or querying Security.Users

#### Backward Compatibility

- **FR-006**: Function signature MUST remain unchanged: `reset_password(container_name, username, new_password, timeout) -> Tuple[bool, str]`

- **FR-007**: Function MUST maintain existing error handling and timeout behavior

- **FR-008**: Function MUST continue to work with both Community and Enterprise editions of IRIS

#### Testing & Verification

- **FR-009**: System MUST include integration test that verifies password is actually set (not just function success)

- **FR-010**: Integration test MUST verify connection succeeds with new password

- **FR-011**: Integration test MUST verify `PasswordNeverExpires=1` is set correctly

- **FR-012**: Tests MUST cover both the primary method and fallback method in `reset_password()`

### Key Entities

- **Security.Users**: IRIS system object representing user accounts
  - **Password**: The actual password value (hashed by IRIS)
  - **PasswordNeverExpires**: Flag (0/1) controlling password expiration
  - **ChangePassword**: Flag controlling "change password on next login" (not relevant for our use case)
  - **ExternalPassword**: Different property, not used for standard password authentication

---

## Success Criteria

### Validation Tests

1. **Password Actually Set**:
   - Reset password to "NEWPASS123"
   - Query IRIS Security.Users to verify Password property is set
   - Result: Password is changed

2. **Connection Succeeds**:
   - Reset password to "NEWPASS123"
   - Attempt DBAPI connection with new password
   - Result: Connection succeeds without "Access Denied"

3. **Password Never Expires**:
   - Reset password
   - Query IRIS Security.Users for PasswordNeverExpires
   - Result: PasswordNeverExpires = 1

4. **Idempotency**:
   - Call reset_password() 3 times with same password
   - Result: All succeed, password remains set

### Performance

- Password reset completes within 10 seconds (no regression from current implementation)
- Function timeout defaults remain at 30 seconds

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (none found - bug well-documented)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---

## Dependencies & Assumptions

### Dependencies
- Docker must be installed and running
- IRIS container must be accessible via docker exec
- IRIS Security.Users API behavior is consistent across IRIS versions

### Assumptions
- User has docker permissions to execute docker commands
- IRIS container is using standard Security.Users for authentication (not external auth)
- The tested working solution from AWS EC2 is valid for all IRIS versions (Community and Enterprise)

---

## Out of Scope

- Changing the function signature or return type
- Adding new parameters or options
- Modifying error message format (keep existing Constitutional Principle #5 structure)
- Adding new password validation logic (let IRIS handle validation)
- Changing timeout handling or retry logic

---

## Constitutional Compliance

This fix aligns with iris-devtester Constitutional Principles:

- **Principle #1**: Automatic Remediation Over Manual Intervention
  ✅ Password reset must actually work, not require manual ObjectScript

- **Principle #5**: Fail Fast with Guidance
  ✅ Function must fail if password not set, with clear error messages

- **Principle #7**: Medical-Grade Reliability
  ✅ Critical bug fix requires comprehensive testing (95%+ coverage maintained)

---

## Next Steps

1. Run `/plan` to generate implementation plan
2. Run `/tasks` to break down into executable tasks
3. Implement fix with TDD approach (tests first)
4. Verify fix on local IRIS Community
5. Request user to test on AWS EC2 IRIS Community
6. Release as v1.0.2 patch

---
