---
description: "Task list for Agent Skills implementation"
---

# Tasks: Agent Skills for iris-devtester

**Input**: Design documents from `/specs/019-agent-skills/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/skills.yaml

**Tests**: Manual verification required (SC-001 to SC-005). Automated tests for markdown content are not scoped.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Claude Skills**: `.claude/commands/`
- **Cursor Rules**: `.cursor/rules/`
- **Copilot**: `.github/`
- **Index**: Root `AGENTS.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [ ] T001 Create `.cursor/rules/` directory structure
- [ ] T002 Create `.claude/commands/` directory structure (if missing)
- [ ] T003 Check for existence of `.github/copilot-instructions.md` (create if missing)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be discovered

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Update `AGENTS.md` with new "Agent Skills" section listing available skills (FR-011)
- [ ] T005 Create template/header for Copilot instructions in `.github/copilot-instructions.md`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - AI Agent Starts IRIS Container (Priority: P1) 🎯 MVP

**Goal**: Enable agents to start, stop, and check status of IRIS containers

**Independent Test**: Agent can invoke `/container` or see `@container` rule to start a fresh IRIS instance

### Implementation for User Story 1

- [ ] T006 [P] [US1] Create Claude skill `.claude/commands/container.md` with start/stop/status commands
- [ ] T007 [P] [US1] Create Cursor rule `.cursor/rules/iris-container.mdc` with globs `docker-compose.yml`, `iris_devtester/containers/**`
- [ ] T008 [P] [US1] Add Container Management section to `.github/copilot-instructions.md`
- [ ] T009 [US1] verify container skill instructions match `iris_devtester/cli/container.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - AI Agent Manages Database Connections (Priority: P1)

**Goal**: Enable agents to establish DBAPI connections and handle auth retries

**Independent Test**: Agent can invoke `/connection` to get code snippets for connecting to IRIS

### Implementation for User Story 2

- [ ] T010 [P] [US2] Create Claude skill `.claude/commands/connection.md` with DBAPI snippets and retry logic
- [ ] T011 [P] [US2] Create Cursor rule `.cursor/rules/iris-connection.mdc` with globs `**/*connection*.py`
- [ ] T012 [P] [US2] Add Database Connection section to `.github/copilot-instructions.md`
- [ ] T013 [US2] Verify connection skill instructions match `iris_devtester/cli/connection_commands.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - AI Agent Loads Test Fixtures (Priority: P2)

**Goal**: Enable agents to load DAT fixtures for testing

**Independent Test**: Agent can invoke `/fixture` to load data

### Implementation for User Story 3

- [ ] T014 [P] [US3] Create Claude skill `.claude/commands/fixture.md` with load/list commands
- [ ] T015 [P] [US3] Create Cursor rule `.cursor/rules/iris-fixtures.mdc` with globs `tests/fixtures/**`, `*.dat`
- [ ] T016 [P] [US3] Add Fixture Management section to `.github/copilot-instructions.md`
- [ ] T017 [US3] Verify fixture skill instructions match `iris_devtester/cli/fixture_commands.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - AI Agent Troubleshoots Container Issues (Priority: P2)

**Goal**: Enable agents to self-diagnose and fix common errors

**Independent Test**: Agent invokes `/troubleshoot` when seeing a Docker error

### Implementation for User Story 4

- [ ] T018 [P] [US4] Create Claude skill `.claude/commands/troubleshooting.md` with error patterns and inline remediation
- [ ] T019 [P] [US4] Create Cursor rule `.cursor/rules/iris-troubleshooting.mdc` with globs `logs/**`, `pytest.log`
- [ ] T020 [P] [US4] Add Troubleshooting section to `.github/copilot-instructions.md`
- [ ] T021 [US4] Populate troubleshooting content from `docs/TROUBLESHOOTING.md` and research findings

---

## Phase 7: User Story 5 - AI Agent Creates Test Fixtures (Priority: P3)

**Goal**: Enable agents to create new DAT fixtures from current state

**Independent Test**: Agent can invoke `/fixture create` command

### Implementation for User Story 5

- [ ] T022 [US5] Update `.claude/commands/fixture.md` to include `create` and `validate` commands
- [ ] T023 [US5] Update `.cursor/rules/iris-fixtures.mdc` to include fixture creation guidance
- [ ] T024 [US5] Update `.github/copilot-instructions.md` with fixture creation examples

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Consistency checks and validation

- [ ] T025 Verify all skill files have correct frontmatter (where applicable)
- [ ] T026 Verify all skill files link back to `AGENTS.md` index
- [ ] T027 Run manual validation of `/container` command in Claude Code (if environment allows)
- [ ] T028 Run manual validation of `@iris-container` rule triggering in Cursor (visual check of file)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Stories (Phase 3-6)**: depend on Foundational phase completion
  - Can proceed in parallel
- **US5 (Phase 7)**: Depends on US3 (Phase 5) completion (extends existing files)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Container)**: Independent
- **US2 (Connection)**: Independent
- **US3 (Load Fixture)**: Independent
- **US4 (Trouble)**: Independent
- **US5 (Create Fixture)**: Extends US3 artifacts

### Parallel Opportunities

- Tasks T006, T007, T008 (US1) can run in parallel
- Tasks T010, T011, T012 (US2) can run in parallel
- Entire Phases 3, 4, 5, 6 can run in parallel if multiple developers available

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Container)
4. **STOP and VALIDATE**: Verify agent can start IRIS
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational
2. Add US1 (Container) -> Deploy
3. Add US2 (Connection) -> Deploy
4. Add US3 (Fixtures) -> Deploy
5. Add US4 (Troubleshooting) -> Deploy
