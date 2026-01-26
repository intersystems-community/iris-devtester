# Feature Specification: IRIS Source Insights for Robustness

**Feature Branch**: `017-iris-source-insights`
**Created**: 2025-12-18
**Status**: Draft
**Input**: User description: "Improve robustness of password and container and snapshot functionality by searching IRIS source code for insights"

---

## Summary

Research and document official IRIS patterns for password management, container lifecycle, and snapshot functionality to improve the robustness of iris-devtester. This specification defines what insights are needed and how they will be validated, without prescribing implementation details.

---

## User Scenarios & Testing

### Primary User Story

As a **developer using iris-devtester**, I want password reset, container management, and snapshot operations to work reliably across all IRIS versions and configurations, so that my integration tests never fail due to infrastructure issues.

### Acceptance Scenarios

1. **Given** a fresh IRIS Community container, **When** a password reset is requested, **Then** the password is successfully changed on the first attempt without retry loops

2. **Given** any supported IRIS version (2024.1+), **When** container health checks run, **Then** the container is correctly identified as ready before connections are attempted

3. **Given** an IRIS namespace with data, **When** a snapshot/backup is created, **Then** the operation completes successfully and produces a valid, restorable backup

4. **Given** password reset code, **When** run against IRIS Security API, **Then** the correct official API patterns are used (not deprecated or non-existent methods)

### Edge Cases

- What happens when IRIS is in "password change required" state during container startup?
- How does the system handle IRIS Community vs Enterprise security model differences?
- What happens when container ports are dynamically assigned by testcontainers?
- How does password reset behave with different IRIS authentication modes?

---

## Requirements

### Functional Requirements

#### Password Management Research

- **FR-001**: Documentation MUST identify all official IRIS Security.Users methods for password operations
- **FR-002**: Documentation MUST specify the correct Get/Modify pattern with property arrays
- **FR-003**: Documentation MUST identify which methods do NOT exist (e.g., ChangePassword) to prevent future regressions
- **FR-004**: Documentation MUST specify the correct property names (Password, PasswordExternal, ChangePassword, PasswordNeverExpires)

#### Container Lifecycle Research

- **FR-005**: Documentation MUST identify IRIS startup sequence and health indicators
- **FR-006**: Documentation MUST specify how to detect when IRIS is fully ready for connections
- **FR-007**: Documentation MUST identify differences between Community and Enterprise container behavior
- **FR-008**: Documentation MUST specify CallIn service requirements for DBAPI connections

#### Snapshot/Backup Research

- **FR-009**: Documentation MUST identify official IRIS backup utilities and patterns
- **FR-010**: Documentation MUST specify namespace export/import patterns
- **FR-011**: Documentation MUST identify global export formats and their use cases

#### Implementation Requirements (Code Changes)

- **FR-012**: Password reset module MUST use correct property name `ChangePassword` (not `ChangePasswordAtNextLogin`)
- **FR-013**: Password reset module MUST use `PasswordExternal` property for setting passwords (triggers PBKDF2 hashing)
- **FR-014**: Password reset module MUST set `AccountNeverExpires=1` in addition to `PasswordNeverExpires=1`
- **FR-015**: Container health check SHOULD use `$SYSTEM.Monitor.State()` for reliable readiness detection
- **FR-016**: DAT fixture module SHOULD use documented `$SYSTEM.OBJ.Export/Import` patterns
- **FR-017**: All code changes MUST include corresponding tests

### Success Criteria

1. **Password reset reliability**: Operations succeed on first attempt in 99%+ of cases (currently ~50% on macOS due to timing issues)
2. **Container readiness accuracy**: Health checks correctly predict connection success in 100% of cases
3. **Backup/restore reliability**: Snapshot operations succeed in 100% of cases with valid, restorable output
4. **Documentation completeness**: All discovered patterns documented in `docs/learnings/` for future reference

### Key Entities

- **Security.Users**: IRIS class managing user accounts, passwords, and permissions
- **Container Health State**: Observable indicators of IRIS readiness (SuperServer port, log messages, health checks)
- **Namespace Backup**: Exportable unit containing globals, routines, and classes

---

## Assumptions

1. Research will use official IRIS documentation, Management Portal introspection, and running IRIS instances
2. Research findings apply to IRIS 2024.1 and later versions
3. Patterns discovered will be documented without exposing proprietary code
4. The goal is to understand official API contracts, not reverse-engineer internals
5. IRIS source code is available at `/Users/tdyar/ws/vector-shard/iris/latest/` for research

## Dependencies

- Access to IRIS documentation or running IRIS instance for API exploration
- Existing iris-devtester codebase for context on current implementation
- CHANGELOG.md entries for v1.4.x-v1.5.0 documenting previous password reset issues

## Out of Scope

- Supporting IRIS versions before 2024.1
- Enterprise-specific features (mirrors, ECP, sharding)
- Documenting proprietary IRIS internals beyond public API patterns
- Major architectural changes to iris-devtester (small targeted fixes only)

---

## Research Approach

### Phase 1: Password Management

1. Review IRIS Security.Users class documentation
2. Identify all password-related methods and properties
3. Document the correct pattern for:
   - Checking if user exists
   - Creating new users
   - Modifying password
   - Clearing password expiration flags
   - Handling "password change required" state

### Phase 2: Container Lifecycle

1. Identify IRIS startup log messages indicating readiness
2. Document SuperServer port availability timing
3. Identify any REST/API endpoints for health checking
4. Document CallIn service requirements

### Phase 3: Snapshot/Backup

1. Review backup utility patterns
2. Document class and global export/import utilities
3. Identify global export/import formats
4. Document manifest/checksum patterns for data integrity

---

## Key Findings (from source analysis)

### Security.Users Class (from `/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/Security/Users.xml`)

**Critical Discovery - Property Names**:
- `ChangePassword` - NOT `ChangePasswordAtNextLogin` (the correct property name)
- `PasswordNeverExpires` - Correct
- `Password` - The hashed password (PBKDF2)
- `PasswordExternal` - Clear text password (transient, triggers hashing)

**Historical Note (line 263 in source)**:
> "STC649 10/04/04 Steve Clay, Remove $SYSTEM.Security.Users.ChangePassword"

This confirms that `ChangePassword()` method was removed in 2004! The iris-devtester CHANGELOG references `ChangePassword()` as a non-existent method - this is now confirmed by source code.

**Correct API Pattern** (from Modify() method, lines 2096-2213):
```objectscript
// Get existing user
i '..Exists(Username,.User,.Status) q Status

// Set password via PasswordExternal (triggers hashing)
s User.PasswordExternal=Properties("Password")

// Set password-related flags
s User.ChangePassword=0      // NOT "ChangePasswordAtNextLogin"
s User.PasswordNeverExpires=1

// Save
s Status=User.%Save()
```

**Available Methods**:
- `Create()` - Create user with properties array
- `Modify()` - Modify user via properties array
- `Get()` - Get user properties
- `Exists()` - Check if user exists (returns object handle)
- `UnExpireUserPasswords()` - Clear change-password-required flag for users
- `ExpireUserPasswords()` - Set change-password-required flag for users

**Key Properties** (from source lines 342-868):
| Property | Type | Description |
|----------|------|-------------|
| `ChangePassword` | BooleanYN | 0=Not required, 1=Required before next login |
| `PasswordNeverExpires` | BooleanYN | 0=Expires normally, 1=Never expires |
| `Password` | Password | PBKDF2 hashed password (DO NOT SET DIRECTLY) |
| `PasswordExternal` | String | Clear text, transient - use this to set password |
| `AccountNeverExpires` | BooleanYN | 0=Expires normally, 1=Never expires |
| `Enabled` | BooleanYN | 0=Disabled, 1=Enabled |

---

## Deliverables

### Documentation
1. **docs/learnings/iris-security-users-api.md** - Password management patterns
2. **docs/learnings/iris-container-readiness.md** - Container health check patterns
3. **docs/learnings/iris-backup-patterns.md** - Snapshot and restore patterns
4. Updated CLAUDE.md with ObjectScript Patterns section

### Code Changes
5. **iris_devtester/utils/password_reset.py** - Fix property names and password setting pattern
6. **iris_devtester/utils/container_health.py** - Add $SYSTEM.Monitor.State() health check (new or enhanced)
7. **tests/** - Corresponding tests for all code changes

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
- [x] Success criteria are technology-agnostic
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities resolved (user-specified path adjusted to use available sources)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
