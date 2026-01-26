---
description: "Task list for AI Agent Skill.md implementation"
---

# Tasks: AI Agent Skill.md

**Input**: Design documents from `/specs/021-add-agent-skill-md/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/skills.yaml

**Tests**: Verification will be performed through structural validation of YAML and functional testing of snippets in Python 3.9+.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: Repository root (`/`)
- **Documentation**: `docs/features/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 [P] Create directory structure for Agent Skills reference material in `docs/learnings/`
- [x] T002 Verify Python 3.9+ environment for snippet validation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Initialize `SKILL.md` with required YAML frontmatter (FR-002) in `SKILL.md`
- [x] T004 Create skeletal hierarchical structure (L1 to L4) in `SKILL.md` (FR-003)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 & 2 - Instant Onboarding & Hierarchy (Priority: P1) 🎯 MVP

**Goal**: Enable agents to quickly understand and navigate the library's capabilities using progressive disclosure.

**Independent Test**: Provide `SKILL.md` to a fresh agent and verify it can correctly identify the three methods for container management.

### Implementation for User Story 1 & 2

- [x] T005 [US1] Implement Level 1: Core Essentials (Installation, Setup) in `SKILL.md`
- [x] T006 [US1] Implement Level 2: Operations (Containers, Connections) in `SKILL.md`
- [x] T007 [US2] Add progressive disclosure navigation links to detailed sections/modules in `SKILL.md`
- [x] T008 [US1] Verify container management snippets match `iris_devtester/containers/iris_container.py` API

**Checkpoint**: At this point, User Stories 1 and 2 should be fully functional and testable independently

---

## Phase 4: User Story 3 - "Incorporate into Project" Skill (Priority: P2)

**Goal**: Provide specific guidance for agents on how to integrate `iris-devtester` into existing repositories.

**Independent Test**: Ask an agent to "Integrate iris-devtester into this existing repo" and verify it correctly creates a `conftest.py` with the recommended fixture.

### Implementation for User Story 3

- [x] T009 [US3] Implement "Project Integration" skill module in `SKILL.md` (FR-004)
- [x] T010 [US3] Add `conftest.py` template and CI/CD configuration snippets to `SKILL.md`
- [x] T011 [US3] Add activation instructions for Claude Code, Cursor, and generic agents (FR-007)

**Checkpoint**: At this point, User Stories 1, 2, and 3 should work independently

---

## Phase 5: User Story 4 - Medical-Grade Reliability Enforcement (Priority: P3)

**Goal**: Ensure agents generate code that follows the project "Constitution".

**Independent Test**: Verify that connection snippets in `SKILL.md` prioritize `iris.connect()` over JDBC.

### Implementation for User Story 4

- [x] T012 [US4] Embed "Constitution" constraints into connection and setup guidance in `SKILL.md`
- [x] T020 [US4] Verify all connection snippets avoid forbidden `_DBAPI` attributes and use official `intersystems-irispython` patterns (Constitution Principle #8)
- [x] T013 [US4] Implement Level 4: Debugging & Troubleshooting section with root cause analysis patterns in `SKILL.md`
- [x] T014 [US4] Verify all code snippets in `SKILL.md` are valid Python 3.9+ (FR-005)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T015 [P] Update `docs/features/agent-skills.md` to include human-facing reference for the new `SKILL.md`
- [x] T016 [P] Link `SKILL.md` to `AGENTS.md` and `CLAUDE.md` (FR-006)
- [x] T017 Final review of `SKILL.md` token count to ensure it stays below 5000 tokens (SC-004)
- [x] T018 Run manual validation of "Instant Onboarding" scenario with a fresh agent
- [x] T019 [P] Audit referenced documents in `docs/learnings/` for agent-readability and progressive disclosure alignment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 & US2 (P1)**: Foundation for the document structure.
- **US3 (P2)**: Extends US1 with project-level integration.
- **US4 (P3)**: Adds advanced constraints and debugging.

---

## Implementation Strategy

### MVP First (User Story 1 & 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 & US2 (The core hierarchical guidance)
4. **STOP and VALIDATE**: Verify agent onboarding works.

### Incremental Delivery

1. Foundation + US1/2 -> Essential Onboarding (MVP!)
2. Add US3 -> Enhanced Integration guidance
3. Add US4 -> Full Reliability & Troubleshooting suite
