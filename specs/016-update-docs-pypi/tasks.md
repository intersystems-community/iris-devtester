# Tasks: Update Documentation and PyPI Metadata

**Input**: Design documents from `/specs/016-update-docs-pypi/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No automated tests required - this is a documentation-only feature with manual validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Documentation files at repository root: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`
- Feature docs in: `docs/features/`
- Package config: `pyproject.toml`

---

## Phase 1: Setup

**Purpose**: Create directory structure for new documentation files

- [x] T001 Create docs/features/ directory structure at /docs/features/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking work needed - all user stories can proceed independently

**⚠️ NOTE**: This feature has no blocking prerequisites. User stories can be worked on in any order or in parallel.

**Checkpoint**: Ready to begin user story implementation

---

## Phase 3: User Story 1 - PyPI Page Shows Correct Repository Links (Priority: P1) 🎯 MVP

**Goal**: Fix all 5 project.urls in pyproject.toml to point to correct iris-devtester repository

**Independent Test**: After PyPI publish, visit https://pypi.org/project/iris-devtester/ and click each project link to verify correct repository

### Implementation for User Story 1

- [x] T002 [US1] Update project.urls.Homepage in /pyproject.toml (line 100) from iris-devtools to iris-devtester
- [x] T003 [US1] Update project.urls.Documentation in /pyproject.toml (line 101) from iris-devtools to iris-devtester
- [x] T004 [US1] Update project.urls.Repository in /pyproject.toml (line 102) from iris-devtools to iris-devtester
- [x] T005 [US1] Update project.urls.Issues in /pyproject.toml (line 103) from iris-devtools to iris-devtester
- [x] T006 [US1] Update project.urls.Changelog in /pyproject.toml (line 104) from iris-devtools to iris-devtester
- [x] T007 [US1] Bump version from 1.2.1 to 1.2.2 in /pyproject.toml (line 7)

**Checkpoint**: All pyproject.toml URLs now point to correct repository. SC-001 satisfied.

---

## Phase 4: User Story 2 - README Contains Accurate Links (Priority: P2)

**Goal**: Fix all broken/incorrect links in README.md to point to correct repository resources

**Independent Test**: Click every link in README.md on GitHub and verify all resolve to valid targets (no 404s)

### Implementation for User Story 2

- [x] T008 [US2] Replace all github.com/intersystems-community/iris-devtools URLs with iris-devtester in /README.md
- [x] T009 [US2] Update Constitution link to point to CONSTITUTION.md (relative link) in /README.md
- [x] T010 [US2] Update Troubleshooting Guide link to point to docs/TROUBLESHOOTING.md in /README.md
- [x] T011 [US2] Update CONTRIBUTING.md link to relative path in /README.md
- [x] T012 [US2] Update Examples link to point to examples/ directory in /README.md
- [x] T013 [US2] Update License link to relative LICENSE file in /README.md
- [x] T014 [US2] Verify GitHub Issues link points to iris-devtester/issues in /README.md

**Checkpoint**: All README.md links now resolve correctly. SC-002 satisfied.

---

## Phase 5: User Story 3 - README is Well-Organized and Scannable (Priority: P2)

**Goal**: Reorganize README.md with TOC, condense content to ~145 lines, move detailed docs to docs/features/

**Independent Test**: Count lines in README.md (should be <150), verify TOC anchor links work, verify docs/features/ files exist

### Create Feature Documentation Files

- [x] T015 [P] [US3] Create /docs/features/dat-fixtures.md with DAT Fixture Management content from README
- [x] T016 [P] [US3] Create /docs/features/docker-compose.md with Docker-Compose Integration content from README
- [x] T017 [P] [US3] Create /docs/features/performance-monitoring.md with Performance Monitoring content from README
- [x] T018 [P] [US3] Create /docs/features/testcontainers.md with Testcontainers Integration content from README

### Reorganize README.md

- [x] T019 [US3] Add Table of Contents after badges section in /README.md with anchor links to major sections
- [x] T020 [US3] Condense "The Problem It Solves" section to bullet list (~10 lines) in /README.md
- [x] T021 [US3] Condense "Quick Start" section to minimal examples (~25 lines) in /README.md
- [x] T022 [US3] Replace detailed feature sections with brief descriptions and links to docs/features/ in /README.md
- [x] T023 [US3] Remove "Example: DAT Fixtures" section (moved to docs/features/dat-fixtures.md) from /README.md
- [x] T024 [US3] Remove "Example: Performance Monitoring" section (moved to docs/features/performance-monitoring.md) from /README.md
- [x] T025 [US3] Remove "Example: Docker-Compose Integration" section (moved to docs/features/docker-compose.md) from /README.md
- [x] T026 [US3] Remove "Example: Enterprise Setup" section (moved to docs/features/testcontainers.md) from /README.md
- [x] T027 [US3] Condense "Constitution" section to 5 lines with link to CONSTITUTION.md in /README.md
- [x] T028 [US3] Condense "Real-World Use Cases" to brief list in /README.md
- [x] T029 [US3] Remove "Performance" benchmarks section (moved to docs/features/testcontainers.md) from /README.md
- [x] T030 [US3] Move "AI-Assisted Development" section to /CONTRIBUTING.md
- [x] T031 [US3] Verify final README.md line count is under 150 lines (125 lines achieved)

**Checkpoint**: README.md is ~145 lines with TOC, 4 feature docs created. SC-006, SC-007, SC-008 satisfied.

---

## Phase 6: User Story 4 - Consistent Package Naming in Documentation (Priority: P3)

**Goal**: Ensure all user-facing documentation uses iris-devtester consistently, no iris-devtools references remain

**Independent Test**: Run grep for "iris-devtools" in user-facing docs - should return zero matches

### Implementation for User Story 4

- [x] T032 [P] [US4] Replace iris-devtools with iris-devtester in release links at bottom of /CHANGELOG.md
- [x] T033 [P] [US4] Add v1.2.2 release entry to /CHANGELOG.md documenting documentation fixes
- [x] T034 [P] [US4] Update any iris-devtools references in /CONTRIBUTING.md
- [x] T035 [P] [US4] Update any iris-devtools references in /docs/TROUBLESHOOTING.md
- [x] T036 [US4] Verify zero occurrences of github.com/intersystems-community/iris-devtools in user-facing docs

**Checkpoint**: All user-facing docs use iris-devtester consistently. SC-003 satisfied.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and PyPI publishing

- [x] T037 Verify all TOC anchor links work by clicking each in GitHub preview of /README.md
- [x] T038 Verify all docs/features/*.md files have correct internal links
- [x] T039 Run final grep verification: `grep -r "iris-devtools" README.md pyproject.toml CHANGELOG.md CONTRIBUTING.md`
- [ ] T040 Commit all changes with descriptive message
- [ ] T041 Create PR from 016-update-docs-pypi branch to main
- [ ] T042 After PR merge, build package: `python -m build`
- [ ] T043 Publish to PyPI: `python -m twine upload dist/iris_devtester-1.2.2*`
- [ ] T044 Verify PyPI page links at https://pypi.org/project/iris-devtester/ (SC-004 validation)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: N/A - no blocking prerequisites
- **User Stories (Phase 3-6)**: Can proceed in parallel (different files)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies - can start immediately
- **User Story 2 (P2)**: No dependencies on US1 - can run in parallel
- **User Story 3 (P2)**: No dependencies on US1/US2 - can run in parallel (but T019-T030 depend on T015-T018)
- **User Story 4 (P3)**: No dependencies - can run in parallel with others

### Within Each User Story

- US1: All tasks sequential (same file: pyproject.toml)
- US2: All tasks sequential (same file: README.md)
- US3: Feature docs (T015-T018) can run in parallel, then README tasks sequential
- US4: All tasks can run in parallel (different files)

### Parallel Opportunities

```text
Parallel Group 1 (User Stories can run in parallel):
- US1: T002-T007 (pyproject.toml)
- US4: T032-T035 (CHANGELOG, CONTRIBUTING, TROUBLESHOOTING)

Parallel Group 2 (Within US3):
- T015 docs/features/dat-fixtures.md
- T016 docs/features/docker-compose.md
- T017 docs/features/performance-monitoring.md
- T018 docs/features/testcontainers.md
```

---

## Parallel Example: User Story 3

```bash
# Launch all feature doc creation tasks together:
Task: "Create /docs/features/dat-fixtures.md with DAT Fixture Management content"
Task: "Create /docs/features/docker-compose.md with Docker-Compose Integration content"
Task: "Create /docs/features/performance-monitoring.md with Performance Monitoring content"
Task: "Create /docs/features/testcontainers.md with Testcontainers Integration content"

# Then sequentially reorganize README.md (T019-T031)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (create directory)
2. Complete Phase 3: User Story 1 (fix pyproject.toml URLs)
3. **STOP and VALIDATE**: Verify pyproject.toml has correct URLs
4. Could publish at this point to fix PyPI links immediately

### Incremental Delivery

1. User Story 1 → PyPI links fixed (critical bug fix)
2. User Story 2 → README links fixed (user experience)
3. User Story 3 → README reorganized (major improvement)
4. User Story 4 → Consistency pass (polish)
5. Publish to PyPI → All improvements live

### Recommended Order

Since all user stories affect the same README.md file:

1. US1 (pyproject.toml) - independent, do first
2. US4 (CHANGELOG, CONTRIBUTING) - independent, can parallel with US1
3. US3 (create feature docs) - T015-T018 first
4. US2 + US3 (README reorganization) - combined since both touch README

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- No automated tests needed - manual link verification per quickstart.md
- Version bump (T007) required before PyPI publish
- Commit after each user story completion for clean history
- SC-001 through SC-009 map to success criteria in spec.md

---

## Summary

| Phase | User Story | Tasks | Parallelizable |
|-------|------------|-------|----------------|
| 1 | Setup | 1 | No |
| 2 | Foundational | 0 | N/A |
| 3 | US1 - PyPI Links | 6 | No (same file) |
| 4 | US2 - README Links | 7 | No (same file) |
| 5 | US3 - README Reorg | 17 | Partial (T015-T018) |
| 6 | US4 - Consistency | 5 | Yes (T032-T035) |
| 7 | Polish | 8 | Partial |
| **Total** | | **44** | |
