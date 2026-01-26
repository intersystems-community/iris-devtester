# Implementation Plan: IRIS Source Insights for Robustness

**Branch**: `017-iris-source-insights` | **Date**: 2025-12-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-iris-source-insights/spec.md`

## Summary

Research and document official IRIS patterns for password management, container lifecycle, and snapshot functionality by analyzing IRIS source code at `/Users/tdyar/ws/vector-shard/iris/latest/`. **Then apply these findings to improve iris-devtester code.**

**Deliverables**:
1. **Documentation**: 3 learning documents + CLAUDE.md update
2. **Implementation**: Fix password_reset.py + enhance container health checks

**Key Discovery Already Made**: The spec contains critical findings from Security.Users.xml analysis, including confirmation that `ChangePassword()` method was removed in 2004, and the correct property name is `ChangePassword` (not `ChangePasswordAtNextLogin`).

## Technical Context

**Language/Version**: Python 3.9+ (for iris-devtester), ObjectScript (for IRIS source analysis)
**Primary Dependencies**: IRIS source code (XML class definitions), existing iris-devtester codebase
**Storage**: N/A
**Testing**: Integration tests for password reset and container health
**Target Platform**: iris-devtester package (PyPI)
**Project Type**: Single (documentation + implementation)
**Performance Goals**: Password reset success on first attempt (99%+)
**Constraints**: Must not expose proprietary IRIS internals beyond public API patterns
**Scale/Scope**: 3 learning documents + CLAUDE.md update + 2 code modules fixed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| 1. Automatic Remediation | ✅ PASS | Documentation will enable better auto-remediation |
| 2. Choose the Right Tool | ✅ PASS | Research informs correct tool selection |
| 3. Isolation by Default | N/A | No tests in this feature |
| 4. Zero Configuration | ✅ PASS | Documentation improves zero-config reliability |
| 5. Fail Fast with Guidance | ✅ PASS | Better error messages from research |
| 6. Enterprise Ready, Community Friendly | ✅ PASS | Research covers both editions |
| 7. Medical-Grade Reliability | ✅ PASS | Research improves 99%+ reliability target |
| 8. Use Official IRIS Python API | ✅ PASS | Research documents official patterns |
| 9. Document the Blind Alleys | ✅ PASS | Primary purpose of this feature |

**Initial Constitution Check**: PASS

## Project Structure

### Documentation (this feature)
```
specs/017-iris-source-insights/
├── plan.md              # This file
├── research.md          # Phase 0 output - IRIS source analysis
├── data-model.md        # Phase 1 output - Security.Users properties
├── quickstart.md        # Phase 1 output - API usage patterns
├── contracts/           # N/A for documentation feature
└── tasks.md             # Phase 2 output (/tasks command)
```

### Source Code (deliverables)
```
docs/learnings/
├── iris-security-users-api.md      # Password management patterns
├── iris-container-readiness.md     # Container health check patterns
└── iris-backup-patterns.md         # Snapshot and restore patterns

CLAUDE.md                           # Updated with ObjectScript Patterns section
```

**Structure Decision**: Single project documentation structure. Deliverables are markdown files in `docs/learnings/` directory.

## Phase 0: Outline & Research

### Research Tasks

1. **Security.Users Class Analysis** (COMPLETE - see spec.md)
   - Source: `/Users/tdyar/ws/vector-shard/iris/latest/databases/sys/cls/Security/Users.xml`
   - Findings documented in spec.md Key Findings section

2. **Container Health Check Patterns**
   - Search for startup indicators in IRIS source
   - Identify %SYSTEM classes for health checking
   - Document SuperServer readiness detection

3. **Backup/Snapshot Patterns**
   - Search for BACKUP^DBACK implementation
   - Identify $SYSTEM.OBJ.Export/Load patterns
   - Document global export/import utilities

### Research Agent Dispatch

```
Task 1: "Analyze Security.Users.xml for password-related methods and properties"
  → COMPLETE: ChangePassword property, UnExpireUserPasswords(), Get/Modify pattern

Task 2: "Search IRIS source for container readiness indicators"
  → Pending: Look for %SYSTEM health check classes

Task 3: "Search IRIS source for backup and namespace export patterns"
  → Pending: Look for BACKUP utility, $SYSTEM.OBJ.Export
```

**Output**: research.md with consolidated findings

## Phase 1: Design & Contracts

*Prerequisites: research.md complete*

### 1. Data Model (Security.Users Properties)

Extract from Security.Users.xml:

| Property | Type | API Pattern |
|----------|------|-------------|
| Password | Hashed | DO NOT SET DIRECTLY |
| PasswordExternal | String | Set via Modify() - triggers hashing |
| ChangePassword | BooleanYN | Set to 0 to clear requirement |
| PasswordNeverExpires | BooleanYN | Set to 1 for service accounts |
| AccountNeverExpires | BooleanYN | Set to 1 for service accounts |
| Enabled | BooleanYN | Set to 1 to enable account |

### 2. API Contracts (ObjectScript Patterns)

No REST API contracts for this feature. Instead, document ObjectScript API patterns:

**Password Reset Pattern**:
```objectscript
// Correct pattern (from source analysis)
Set username = "_SYSTEM"
If ##class(Security.Users).Exists(username, .user, .status) {
    Set user.PasswordExternal = "newpassword"
    Set user.ChangePassword = 0
    Set user.PasswordNeverExpires = 1
    Set status = user.%Save()
}
```

**Batch Password Clear Pattern**:
```objectscript
// Clear change-password-required for all users
Do ##class(Security.Users).UnExpireUserPasswords("*")
```

### 3. Quickstart Document

Create `quickstart.md` with:
- 3 essential ObjectScript patterns
- Python code examples using correct patterns
- Common mistakes to avoid

### 4. Agent Context Update

Run: `.specify/scripts/bash/update-agent-context.sh claude`

Add to CLAUDE.md:
- ObjectScript Patterns section
- Security.Users API reference
- Container readiness patterns

**Output**: data-model.md, quickstart.md, updated CLAUDE.md

## Phase 2: Task Planning Approach

*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Research tasks for remaining IRIS source analysis (container, backup)
- Documentation tasks for each learning document
- Update task for CLAUDE.md
- Validation tasks for accuracy checking

**Ordering Strategy**:
- Research before documentation
- Security.Users first (most findings already)
- Container readiness second
- Backup patterns third
- CLAUDE.md update last

**Estimated Output**: 15-20 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3: Documentation Implementation

**Tasks T006-T032**: Create learning documents and update CLAUDE.md

Deliverables:
- `docs/learnings/iris-security-users-api.md`
- `docs/learnings/iris-container-readiness.md`
- `docs/learnings/iris-backup-patterns.md`
- Updated `CLAUDE.md` with ObjectScript Patterns section

## Phase 4: Code Implementation

**Tasks T033-T045**: Apply research findings to fix iris-devtester code

### Password Reset Fix (US5)
- File: `iris_devtester/utils/password_reset.py`
- Changes:
  - Use `ChangePassword` property (not `ChangePasswordAtNextLogin`)
  - Use `PasswordExternal` for setting passwords
  - Add `AccountNeverExpires=1`
- Tests: `tests/integration/test_password_reset_source_insights.py`

### Container Health Enhancement (US6)
- File: `iris_devtester/utils/container_health.py`
- Changes:
  - Add `$SYSTEM.Monitor.State()` health check
  - Integrate into container startup flow
- Tests: `tests/integration/test_container_health_monitor.py`

## Phase 5: Validation

**Tasks T046-T051**: Final validation and release preparation

- Verify all requirements covered
- Run full test suite
- Update CHANGELOG.md

## Complexity Tracking

No constitution violations. This is a documentation + implementation feature with moderate complexity.

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete (research.md created with IRIS source analysis)
- [x] Phase 1: Design complete (data-model.md, quickstart.md created)
- [x] Phase 2: Task planning complete (tasks.md generated with 51 tasks)
- [ ] Phase 3: Documentation implementation (T006-T032)
- [ ] Phase 4: Code implementation (T033-T045)
- [ ] Phase 5: Validation passed (T046-T051)

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)
- [x] Agent context updated (CLAUDE.md)
- [ ] Implementation tests passing
- [ ] Full test suite passing

---
*Based on Constitution v1.1.0 - See `CONSTITUTION.md`*
