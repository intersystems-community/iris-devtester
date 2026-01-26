# Feature Specification: AI Agent Skill.md

**Feature Branch**: `021-add-agent-skill-md`  
**Created**: 2026-01-02  
**Status**: Draft  
**Input**: User description: "implement a SKILL.md that ships with iris-devtester that not only documents how to use it, but provides an optimal set of hiearchical skills that make it simple for coding assistants to incorporate iris-devtester into their projects!"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instant Agent Onboarding (Priority: P1)

As a developer starting a new project, I want my AI coding assistant to quickly understand how to use `iris-devtester` for database testing. I point the assistant to the `SKILL.md` file, and the assistant immediately gains the capability to setup containers, establish connections, and write tests following project conventions.

**Why this priority**: This is the core "agent-friendly" value proposition. Reducing the "knowledge acquisition" time for an agent from minutes of documentation reading to seconds of skill loading.

**Independent Test**: Can be fully tested by providing the `SKILL.md` to a "fresh" agent (no previous context of the library) and asking it to "Setup a fresh IRIS environment for my Python project". Success is measured by the agent correctly generating a `docker-compose.yml` and a basic `get_connection()` test script without human correction.

**Acceptance Scenarios**:

1. **Given** a new project with `iris-devtester` installed, **When** an agent reads `SKILL.md`, **Then** it can correctly identify the three primary methods for container management (CLI, Context Manager, Manual).
2. **Given** an agent with `SKILL.md` context, **When** asked to "load test data", **Then** it proposes using the DAT fixture system and correctly references `FixtureLoader`.

---

### User Story 2 - Hierarchical Skill Discovery (Priority: P1)

As an AI agent, I want to see a clear hierarchy of capabilities so that I can manage my context window efficiently. I should be able to see "high-level" skills (Setup, Test) first, and "deep-dive" into specific implementations (ObjectScript patterns, complex wait strategies) only when needed.

**Why this priority**: Prevents context-window bloat. Agents perform better when they can "drill down" into relevant specifics rather than being forced to ingest the entire library's documentation at once.

**Independent Test**: Can be tested by verifying the `SKILL.md` uses clear section headers and "Progressive Disclosure" patterns (e.g., summaries with links to specialized sub-documents or detailed sections).

**Acceptance Scenarios**:

1. **Given** the `SKILL.md`, **When** the agent parses the YAML metadata, **Then** it finds a list of 4-6 distinct "Skill Modules" with clear activation triggers.
2. **Given** a specific task like "Troubleshooting a connection refused error", **When** the agent looks at `SKILL.md`, **Then** it is directed to the "Autonomous Debugging" section within 1 step.

---

### User Story 3 - "Incorporate into Project" Skill (Priority: P2)

As a developer, I want my agent to know exactly how to "incorporate" `iris-devtester` into my existing codebase (e.g., adding it to `requirements.txt`, configuring `conftest.py`, setting up CI/CD).

**Why this priority**: High value for "Greenfield" or "Migration" scenarios. Ensures the library is integrated correctly from the start according to best practices.

**Independent Test**: An agent is asked to "Integrate iris-devtester into this existing repo". It should correctly add the dependency and create a standard `tests/integration/conftest.py` with the recommended `iris_db` fixture.

**Acceptance Scenarios**:

1. **Given** a repository without `iris-devtester`, **When** the agent follows the "Integration" skill in `SKILL.md`, **Then** it successfully configures a `pytest` environment that can spin up an IRIS container.

---

### User Story 4 - Medical-Grade Reliability Enforcement (Priority: P3)

As a technical lead, I want the `SKILL.md` to enforce the project's "Constitution" (8 principles) on any code the agent generates.

**Why this priority**: Ensures quality and consistency. Agents shouldn't just "make it work"; they should "make it right" (e.g., DBAPI First, Zero Config).

**Acceptance Scenarios**:

1. **Given** an agent using `SKILL.md`, **When** it generates a connection script, **Then** it MUST prioritize `iris.connect()` over JDBC unless explicitly told otherwise.

---

### Edge Cases

- **No Docker**: How does the skill guide the agent when Docker is unavailable?
- **Legacy IRIS**: How does the skill handle differences between 2021.1 and 2024.1 (ChangePassword flag)?
- **Mixed OS**: Does the skill provide different guidance for macOS (port mapping delays) vs Linux?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `SKILL.md` file at the repository root.
- **FR-002**: `SKILL.md` MUST include YAML frontmatter with `name`, `description`, and `triggers` for agent activation.
- **FR-003**: The skill set MUST be hierarchical, following a "Progressive Disclosure" pattern:
    - **L1: Core Essentials** (Installation, Setup)
    - **L2: Operations** (Containers, Connections)
    - **L3: Advanced** (Fixtures, Performance)
    - **L4: Debugging** (Troubleshooting, ObjectScript)
- **FR-004**: System MUST include a "Project Integration" skill module specifically for coding assistants.
- **FR-005**: All code snippets in `SKILL.md` MUST be "Copy-Paste Ready" and valid Python 3.9+.
- **FR-006**: `SKILL.md` MUST explicitly link to `AGENTS.md` and `CLAUDE.md` for shared context.
- **FR-007**: System MUST provide clear activation instructions for at least 3 major AI assistants: Claude Code (Slash commands), Cursor (Project Rules), and generic agents (Context Injection).

### Key Entities

- **Skill.md**: The primary agent-facing documentation and capability manifest.
- **Skill Module**: A discrete section or sub-document representing a specific capability (e.g., "Fixture Management").
- **Activation Trigger**: A keyword or phrase in the YAML metadata that causes an agent to load the skill.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh AI agent can generate a working integration test using `iris-devtester` in under 30 seconds after reading `SKILL.md`.
- **SC-002**: 100% of the 8 Constitutional Principles are explicitly or implicitly enforced by the guidance in `SKILL.md`.
- **SC-003**: `SKILL.md` maintains a high discoverability score (e.g., includes keywords for "IRIS", "Database Testing", "Python", "Docker").
- **SC-004**: The file size of `SKILL.md` stays below 5000 tokens to ensure it fits comfortably in most agent context windows.

## Assumptions

- We are using the "Agent Skills" open standard format (YAML frontmatter + Markdown).
- Agents have the capability to read and parse local markdown files.
- The `SKILL.md` will be bundled with the PyPI package (or at least available in the GitHub repo).
