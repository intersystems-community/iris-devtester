# Feature Specification: Agent Skills for iris-devtester

**Feature Branch**: `019-agent-skills`  
**Created**: 2026-01-02  
**Status**: Draft  
**Input**: User description: "Make this repo more code-assistant and agent friendly by exposing functionality as skills"

## Clarifications

### Session 2026-01-02
- Q: To ensure consistency across Claude, Cursor, and Copilot formats (FR-001), how should the skill content be sourced? → A: Option A (Manual Sync) - Create and maintain separate files for each platform to optimize for their specific format needs.
- Q: For troubleshooting skills (FR-010), should the remediation content be duplicated inline or linked? → A: Option A (Full Remediation) - Include the full error pattern, root cause, and fix instructions inline within the skill file to support "Fail Fast" and 30s resolution target.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI Agent Starts IRIS Container (Priority: P1)

An AI coding assistant (Claude, Cursor, Copilot, etc.) working in a repository that depends on iris-devtester needs to spin up an IRIS database container to run tests or develop features. The agent invokes the container skill, which provides step-by-step instructions for starting, configuring, and verifying an IRIS container is ready for use.

**Why this priority**: Container management is the foundational capability. Without a running IRIS instance, no other database operations are possible. This unblocks all downstream workflows.

**Independent Test**: Can be fully tested by an agent invoking the skill and successfully starting a container that responds to a health check.

**Acceptance Scenarios**:

1. **Given** an AI agent with access to the skill, **When** the agent invokes the container start skill, **Then** the skill provides clear instructions for starting an IRIS Community container with sensible defaults
2. **Given** a container is starting, **When** the agent follows the skill instructions, **Then** the container becomes healthy and accessible within the documented timeout period
3. **Given** the container is running, **When** the agent needs connection details, **Then** the skill provides host, port, namespace, and credential information

---

### User Story 2 - AI Agent Manages Database Connections (Priority: P1)

An AI coding assistant needs to establish a database connection to execute queries or run tests. The agent invokes the connection skill, which provides instructions for creating DBAPI connections with automatic retry, password reset handling, and error recovery.

**Why this priority**: Database connections are required for any meaningful interaction with IRIS. This is a core capability that enables test execution, data manipulation, and feature development.

**Independent Test**: Can be fully tested by an agent successfully establishing a connection and executing a simple query.

**Acceptance Scenarios**:

1. **Given** an AI agent with a running IRIS container, **When** the agent invokes the connection skill, **Then** the skill provides code patterns for establishing a DBAPI connection
2. **Given** a connection attempt fails with "password change required", **When** the agent follows the skill's error handling guidance, **Then** the connection is automatically recovered
3. **Given** a successful connection, **When** the agent needs to execute SQL, **Then** the skill provides cursor usage patterns and common query examples

---

### User Story 3 - AI Agent Loads Test Fixtures (Priority: P2)

An AI coding assistant needs to populate an IRIS database with test data to validate feature implementations. The agent invokes the fixtures skill, which provides instructions for loading DAT fixtures, validating data integrity, and cleaning up after tests.

**Why this priority**: Reproducible test data is essential for reliable testing, but agents can still test with manually created data if fixtures aren't available. This enhances testing efficiency but isn't blocking.

**Independent Test**: Can be fully tested by an agent loading a fixture and verifying the expected tables and row counts exist.

**Acceptance Scenarios**:

1. **Given** an AI agent with a running IRIS container, **When** the agent invokes the fixture load skill, **Then** the skill provides CLI and Python API patterns for loading DAT fixtures
2. **Given** a fixture directory exists, **When** the agent follows the load instructions, **Then** tables are populated with the fixture data
3. **Given** tests are complete, **When** the agent needs to clean up, **Then** the skill provides cleanup and namespace isolation patterns

---

### User Story 4 - AI Agent Troubleshoots Container Issues (Priority: P2)

An AI coding assistant encounters an error when working with IRIS containers (connection refused, container not starting, CallIn service errors). The agent invokes the troubleshooting skill, which provides diagnostic steps and remediation guidance specific to common iris-devtester issues.

**Why this priority**: Troubleshooting is essential for agent autonomy. When things go wrong, agents need structured guidance to self-recover rather than asking users for help.

**Independent Test**: Can be fully tested by simulating a common error condition and verifying the skill provides actionable remediation steps.

**Acceptance Scenarios**:

1. **Given** an AI agent encounters "CallIn service not available" error, **When** the agent invokes the troubleshooting skill, **Then** the skill provides the specific enable-callin command and verification steps
2. **Given** a container appears stuck in starting state, **When** the agent follows diagnostic steps, **Then** the skill guides through health check interpretation and common fixes
3. **Given** a password verification failure on macOS, **When** the agent consults the skill, **Then** the skill explains the timing issue and provides the extended wait workaround

---

### User Story 5 - AI Agent Creates Test Fixtures (Priority: P3)

An AI coding assistant needs to create a new DAT fixture from existing database state for future test reproducibility. The agent invokes the fixture creation skill, which provides instructions for exporting namespace data to DAT files with manifest generation.

**Why this priority**: Fixture creation is an advanced capability primarily used during test suite setup, not routine development. Agents can work without this by using existing fixtures or manual data creation.

**Independent Test**: Can be fully tested by an agent creating a fixture from a populated namespace and verifying the manifest and DAT files are generated.

**Acceptance Scenarios**:

1. **Given** an AI agent with a populated IRIS namespace, **When** the agent invokes the fixture create skill, **Then** the skill provides CLI and Python API patterns for exporting to DAT
2. **Given** the export completes, **When** the agent needs to verify the fixture, **Then** the skill provides validation commands and checksum verification steps

---

### Edge Cases

- What happens when the skill is invoked but Docker is not running?
- How does the skill guide agents when IRIS image download times out?
- What happens when port conflicts prevent container startup?
- How does the skill handle Enterprise vs Community edition differences?
- What happens when skills are invoked in a non-iris-devtester project?

## Requirements *(mandatory)*

### Functional Requirements

#### Skill Delivery Mechanisms

- **FR-001**: System MUST provide skills using multiple delivery mechanisms to maximize compatibility across AI assistants:
  - **Markdown skill files** in `.claude/commands/` for Claude Code slash commands
  - **AGENTS.md** enhanced with quick-reference skill summaries for vendor-neutral discovery
  - **Copilot instructions** in `.github/copilot-instructions.md` for GitHub Copilot users
  - **Cursor rules** in `.cursor/rules/` for Cursor IDE users (if applicable)
- **FR-002**: Skills MUST be formatted as self-contained, executable guidance that works without requiring agent memory of previous interactions
- **FR-003**: Skills MUST be vendor-agnostic in content (no Claude-specific syntax in the guidance itself)
- **FR-013**: Skill content MUST be maintained manually for each platform to optimize for tool-specific formats (Decision: Manual Sync).

#### Skill Content Requirements

- **FR-004**: Each skill MUST include prerequisite checks (Docker running, package installed, container available)
- **FR-005**: Skills MUST provide both CLI commands and Python API examples for each operation
- **FR-006**: Skills MUST include error scenarios with specific remediation steps following Constitutional Principle #5
- **FR-014**: Remediation content MUST be included inline within skill files (not linked) to ensure self-contained troubleshooting (Decision: Full Remediation).
- **FR-007**: Container skill MUST cover: start, stop, status, attach, and health verification
- **FR-008**: Connection skill MUST cover: DBAPI connection, retry configuration, password reset, and connection testing
- **FR-009**: Fixture skill MUST cover: load, validate, create, and cleanup operations
- **FR-010**: Troubleshooting skill MUST index common errors from `docs/learnings/` and `docs/TROUBLESHOOTING.md`

#### Discoverability

- **FR-011**: Skills MUST be indexed in a central manifest (AGENTS.md or dedicated skills index) listing available skills with one-line descriptions
- **FR-012**: Each skill file MUST include a YAML frontmatter or header section with: name, description, prerequisites, and related skills

### Key Entities

- **Skill File**: A markdown file providing structured guidance for a specific capability. Contains prerequisites, step-by-step instructions, code examples, and error handling guidance. Can live in `.claude/commands/`, `.cursor/rules/`, or other tool-specific locations.
- **Skill Index**: A manifest or listing (in AGENTS.md or separate file) that helps AI assistants discover available skills and their purposes.
- **Prerequisite Check**: A verification step (bash command or Python snippet) that ensures required conditions are met before proceeding with skill instructions.
- **Copilot Instructions**: GitHub Copilot's custom instructions file (`.github/copilot-instructions.md`) that can embed skill summaries.
- **Cursor Rules**: Cursor IDE's project-specific AI configuration files in `.cursor/rules/` directory.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An AI assistant can start an IRIS container and verify connectivity within 60 seconds of invoking the container skill
- **SC-002**: An AI assistant encountering a common error can find and apply the correct remediation within 30 seconds using the troubleshooting skill
- **SC-003**: 100% of CLI commands documented in README are also covered in corresponding skills
- **SC-004**: Each skill can be independently loaded and executed without requiring other skills
- **SC-005**: Skills are accessible from at least 3 major AI assistants (Claude Code, GitHub Copilot, Cursor)

## Assumptions

- AI assistants can read and process markdown files from standard locations (`.claude/commands/`, `.github/`, `.cursor/`)
- The skill format follows patterns already established in this repository (e.g., existing speckit commands)
- Docker Desktop is the assumed container runtime for macOS/Windows; native Docker for Linux
- Skills document the existing CLI and Python API rather than replacing them
- MCP (Model Context Protocol) integration is out of scope for this feature but may be added in future iterations
- The existing AGENTS.md and CLAUDE.md files will be enhanced, not replaced
