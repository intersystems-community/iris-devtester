# Tasks: IRIS Source Insights for Robustness

**Feature Branch**: `017-iris-source-insights`
**Input**: Design documents from `/specs/017-iris-source-insights/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

---

## Overview

This is a **documentation/research feature** - no code implementation. The deliverables are learning documents that capture insights from IRIS source code analysis.

**Deliverables**:
1. `docs/learnings/iris-security-users-api.md` - Password management patterns
2. `docs/learnings/iris-container-readiness.md` - Container health check patterns
3. `docs/learnings/iris-backup-patterns.md` - Snapshot and restore patterns
4. Updated `CLAUDE.md` with ObjectScript Patterns section

---

## Phase 1: Setup

- [x] T001 Verify docs/learnings/ directory exists in /Users/tdyar/ws/iris-devtester/docs/learnings/
- [x] T002 Review existing CLAUDE.md structure in /Users/tdyar/ws/iris-devtester/CLAUDE.md

---

## Phase 2: Foundational (Research Consolidation)

- [x] T003 Consolidate Security.Users findings from research.md into structured format
- [x] T004 Consolidate SYS.Container findings from research.md into structured format
- [x] T005 Consolidate %SYSTEM.OBJ findings from research.md into structured format

---

## Phase 3: User Story 1 - Password Management Documentation (P1)

**Story Goal**: Document official IRIS Security.Users API patterns for password operations.

**Independent Test Criteria**: Document exists, covers all FR-001 to FR-004 requirements, includes code examples.

- [x] T006 [US1] Create docs/learnings/iris-security-users-api.md with header and overview
- [x] T007 [US1] Add "Critical Property Names" section documenting ChangePassword vs ChangePasswordAtNextLogin
- [x] T008 [US1] Add "Available Methods" section with Exists(), Create(), Modify(), Get() patterns
- [x] T009 [US1] Add "Password Setting Pattern" section with PasswordExternal usage
- [x] T010 [US1] Add "Removed Methods" section documenting ChangePassword() removal in 2004
- [x] T011 [US1] Add "Common Mistakes" section with what NOT to do
- [x] T012 [US1] Add "Python Integration Examples" section with docker exec patterns
- [x] T013 [US1] Add cross-references to CHANGELOG v1.4.x-v1.5.0 password fixes

---

## Phase 4: User Story 2 - Container Readiness Documentation (P2)

**Story Goal**: Document IRIS container health check patterns for reliable startup detection.

**Independent Test Criteria**: Document exists, covers FR-005 to FR-008 requirements, includes health check patterns.

- [x] T014 [US2] Create docs/learnings/iris-container-readiness.md with header and overview
- [x] T015 [US2] Add "System Monitor State" section documenting $SYSTEM.Monitor.State() values
- [x] T016 [US2] Add "Container Quiesce Patterns" section from SYS.Container analysis
- [x] T017 [US2] Add "Password Change on Startup" section documenting ForcePasswordChange behavior
- [x] T018 [US2] Add "Community vs Enterprise" section with edition-specific notes
- [x] T019 [US2] Add "Python Health Check Example" section with implementation pattern
- [x] T020 [US2] Add "Troubleshooting" section for common container issues

---

## Phase 5: User Story 3 - Backup/Export Documentation (P3)

**Story Goal**: Document IRIS backup and export patterns for DAT fixture management.

**Independent Test Criteria**: Document exists, covers FR-009 to FR-011 requirements, includes export/import patterns.

- [x] T021 [US3] Create docs/learnings/iris-backup-patterns.md with header and overview
- [x] T022 [US3] Add "$SYSTEM.OBJ.Export" section with method signature and examples
- [x] T023 [US3] Add "$SYSTEM.OBJ.Import" section with format support details
- [x] T024 [US3] Add "Supported Formats" section (XML, UDL, %RO, %GOF, etc.)
- [x] T025 [US3] Add "Wildcard Patterns" section for selective export/import
- [x] T026 [US3] Add "Global Export" section for data-level backup
- [x] T027 [US3] Add "Integration with DAT Fixtures" section linking to iris-devtester usage

---

## Phase 6: User Story 4 - CLAUDE.md Update (P4)

**Story Goal**: Update CLAUDE.md with ObjectScript Patterns section for AI assistant reference.

**Independent Test Criteria**: CLAUDE.md contains ObjectScript Patterns section with correct API patterns.

- [x] T028 [US4] Add "ObjectScript Patterns" section header after Feature 004 section in CLAUDE.md
- [x] T029 [US4] Add "Password Reset Pattern" subsection with correct PasswordExternal usage
- [x] T030 [US4] Add "Property Name Reference" subsection with correct vs incorrect names
- [x] T031 [US4] Add "Container Health Check Pattern" subsection with $SYSTEM.Monitor.State()
- [x] T032 [US4] Add links to docs/learnings/*.md files

---

## Phase 7: User Story 5 - Password Reset Implementation (P1-IMPL)

**Story Goal**: Apply research findings to fix password_reset.py with correct IRIS API patterns.

**Independent Test Criteria**: Password reset succeeds on first attempt without retries, uses correct property names.

- [x] T033 [US5] Read current iris_devtester/utils/password_reset.py to understand existing implementation
- [x] T034 [US5] Create tests/integration/test_password_reset_source_insights.py with test for correct property usage
- [x] T035 [US5] Fix password_reset.py to use `ChangePassword` instead of `ChangePasswordAtNextLogin`
- [x] T036 [US5] Fix password_reset.py to use `PasswordExternal` for setting passwords
- [x] T037 [US5] Add `AccountNeverExpires=1` to password reset pattern
- [x] T038 [US5] Run integration tests to verify password reset reliability improvement
- [x] T039 [US5] Update CHANGELOG.md with password reset fix details

---

## Phase 8: User Story 6 - Container Health Check Enhancement (P2-IMPL)

**Story Goal**: Add $SYSTEM.Monitor.State() based health checking for reliable container readiness detection.

**Independent Test Criteria**: Health check uses Monitor.State(), correctly identifies ready/not-ready states.

- [x] T040 [US6] Explore existing container health check code in iris_devtester/
- [x] T041 [US6] Create tests/integration/test_container_health_monitor.py for Monitor.State() usage
- [x] T042 [US6] Create or enhance iris_devtester/utils/container_health.py with Monitor.State() check
- [x] T043 [US6] Integrate new health check into container startup flow
- [x] T044 [US6] Run integration tests to verify health check accuracy
- [x] T045 [US6] Update CHANGELOG.md with container health enhancement

---

## Phase 9: User Story 7 - DAT Fixture Enhancement (P3-IMPL)

**Story Goal**: Apply $SYSTEM.OBJ.Export/Import patterns to improve DAT fixture reliability.

**Independent Test Criteria**: Fixture operations use documented patterns, export/import succeeds reliably.

- [x] T046 [US7] Explore existing iris_devtester/fixtures/ code to understand current implementation
- [x] T047 [US7] Create tests/integration/test_fixture_export_patterns.py for $SYSTEM.OBJ patterns
- [x] T048 [US7] Update fixture creator to use documented $SYSTEM.OBJ.Export pattern
- [x] T049 [US7] Update fixture loader to use documented $SYSTEM.OBJ.Import pattern
- [x] T050 [US7] Add global export support using documented %GOF format
- [x] T051 [US7] Run integration tests to verify fixture reliability improvement
- [x] T052 [US7] Update CHANGELOG.md with DAT fixture enhancement

---

## Phase 10: Polish & Validation

- [x] T053 Verify all FR requirements (FR-001 to FR-017) are covered
- [x] T054 Review documentation for accuracy against IRIS source code
- [x] T055 Add table of contents or navigation to each learning document
- [x] T056 Verify cross-references between documents are correct
- [ ] T057 Run full test suite to ensure no regressions
- [x] T058 Update spec.md Execution Status to mark deliverables complete

---

## Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational)
         ├── Phase 3 (US1: Password Docs) - Independent
         ├── Phase 4 (US2: Container Docs) - Independent
         ├── Phase 5 (US3: Backup Docs) - Independent
         └── Phase 6 (US4: CLAUDE.md) - Depends on US1-US3
              ├── Phase 7 (US5: Password Impl) - Depends on US1 docs
              ├── Phase 8 (US6: Container Impl) - Depends on US2 docs
              └── Phase 9 (US7: DAT Fixture Impl) - Depends on US3 docs
                   └── Phase 10 (Polish)
```

**Parallel Opportunities**:
- T006-T013 (US1) can run in parallel with T014-T020 (US2) and T021-T027 (US3)
- T033-T039 (US5), T040-T045 (US6), and T046-T052 (US7) can all run in parallel
- Within each user story, tasks are sequential (same file)

---

## Parallel Execution Example

```
# Phase 1: Launch US1, US2, US3 documentation creation in parallel:
Task: "Create docs/learnings/iris-security-users-api.md" (T006-T013)
Task: "Create docs/learnings/iris-container-readiness.md" (T014-T020)
Task: "Create docs/learnings/iris-backup-patterns.md" (T021-T027)

# Phase 2: After docs complete, run US4 (CLAUDE.md update):
Task: "Update CLAUDE.md with ObjectScript Patterns" (T028-T032)

# Phase 3: After CLAUDE.md, launch ALL implementation tasks in parallel:
Task: "Fix password_reset.py with correct API patterns" (T033-T039)
Task: "Add Monitor.State() health check" (T040-T045)
Task: "Enhance DAT fixtures with $SYSTEM.OBJ patterns" (T046-T052)
```

---

## Implementation Strategy

### MVP Scope (User Story 1 Only)
- Complete Phase 1-2 (Setup, Foundational)
- Complete Phase 3 (US1: Password Documentation)
- This delivers the most critical insight: correct password API patterns

### Full Implementation
- Complete all phases in order
- US1-US3 can be parallelized
- US4 depends on US1-US3 for content to reference

### Incremental Delivery
Each user story produces a complete, standalone document that provides value:
- US1: Fixes password reset reliability issues
- US2: Improves container startup detection
- US3: Enhances DAT fixture management
- US4: Updates AI assistant context for future development

---

## Validation Checklist

- [x] All spec.md requirements (FR-001 to FR-017) have corresponding tasks
- [x] All deliverables from spec.md have corresponding tasks (docs + code)
- [x] Tasks specify exact file paths
- [x] User stories are independently testable
- [x] Dependencies clearly documented
- [x] Parallel opportunities identified
- [x] Implementation tasks include tests (FR-017)
- [x] All tasks completed (T057 pending integration test run)

---

## Task Summary

| Phase | Description | Task Count |
|-------|-------------|------------|
| Phase 1 | Setup | 2 |
| Phase 2 | Foundational | 3 |
| Phase 3 | US1: Password Docs | 8 |
| Phase 4 | US2: Container Docs | 7 |
| Phase 5 | US3: Backup Docs | 7 |
| Phase 6 | US4: CLAUDE.md | 5 |
| Phase 7 | US5: Password Impl | 7 |
| Phase 8 | US6: Container Impl | 6 |
| Phase 9 | US7: DAT Fixture Impl | 7 |
| Phase 10 | Polish | 6 |
| **Total** | | **58** |

### Scope Summary
- **Documentation Tasks**: 32 (T001-T032)
- **Implementation Tasks**: 20 (T033-T052)
- **Validation Tasks**: 6 (T053-T058)

---
