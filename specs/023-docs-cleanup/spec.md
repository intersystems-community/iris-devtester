# Feature Specification: Documentation and Project Cleanup

**Feature Branch**: `023-docs-cleanup`  
**Created**: 2026-01-25  
**Status**: Draft  
**Input**: User description: "Review project top level directory for cleanliness and documentation for accuracy and clarity"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Contributor Onboarding (Priority: P1)

A new developer discovers iris-devtester and wants to understand the project quickly. They should find clear, accurate documentation that explains what the project does, how to install it, and how to contribute.

**Why this priority**: First impressions determine adoption. Confusing or outdated documentation drives users away.

**Independent Test**: Can be tested by having a new developer read only README.md and successfully run the quick start example within 5 minutes.

**Acceptance Scenarios**:

1. **Given** a developer visits the repository, **When** they read README.md, **Then** they understand the project purpose in under 30 seconds
2. **Given** a developer follows the Quick Start, **When** they run the example code, **Then** it works without modification
3. **Given** a developer reads the documentation links, **When** they click any link, **Then** the link is valid and the content matches the description

---

### User Story 2 - AI Agent Configuration (Priority: P1)

An AI coding assistant (Claude, Cursor, Copilot) is used to work on the project. The agent configuration files should provide accurate, non-conflicting guidance that helps the agent work effectively.

**Why this priority**: AI-assisted development is a core feature of this project. Outdated agent configs cause confusion and errors.

**Independent Test**: Can be tested by having an AI agent read AGENTS.md and successfully run the build commands.

**Acceptance Scenarios**:

1. **Given** an AI agent reads AGENTS.md, **When** it runs the listed build commands, **Then** all commands succeed
2. **Given** AGENTS.md references other files, **When** those files are checked, **Then** they exist and are consistent
3. **Given** AGENTS.md lists project structure, **When** compared to actual structure, **Then** they match

---

### User Story 3 - Clean Repository Structure (Priority: P2)

A developer clones the repository and wants a clean, professional project structure without clutter, temp files, or outdated artifacts.

**Why this priority**: Repository cleanliness reflects project quality and professionalism.

**Independent Test**: Can be tested by cloning fresh and verifying no unexpected files exist at top level.

**Acceptance Scenarios**:

1. **Given** a fresh clone, **When** listing the top-level directory, **Then** only expected project files are present
2. **Given** the .gitignore file, **When** compared to common artifacts, **Then** all appropriate files are excluded
3. **Given** the docs/ directory, **When** reviewing contents, **Then** no orphaned or temporary files exist

---

### Edge Cases

- What happens when documentation references deleted files or modules?
- How does the project handle outdated version references in docs?
- What if AI agent configurations conflict with each other?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README.md MUST have working quick start code that executes without errors
- **FR-002**: All documentation links MUST resolve to valid destinations
- **FR-003**: AGENTS.md MUST accurately reflect current project structure and build commands
- **FR-004**: AGENTS.md MUST NOT reference deleted modules (password_reset.py, password_verification.py, unexpire_passwords.py)
- **FR-005**: .gitignore MUST exclude all common development artifacts and temp files
- **FR-006**: Top-level directory MUST contain only standard project files (no temp files, scratch notes, or orphaned artifacts)
- **FR-007**: Documentation in docs/ MUST be organized logically with clear purpose for each file
- **FR-008**: README.md problem list MUST use checkmarks for solved problems, not X marks

### Key Entities

- **README.md**: Primary project introduction and quick start
- **AGENTS.md**: AI agent configuration (build commands, structure, conventions)
- **CLAUDE.md**: Claude-specific context and patterns
- **CONTRIBUTING.md**: Contributor guidelines
- **docs/**: Extended documentation directory
- **.gitignore**: File exclusion rules

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New developer can complete quick start in under 5 minutes with zero errors
- **SC-002**: All internal documentation links (100%) resolve to valid files
- **SC-003**: Fresh repository clone contains zero unexpected files at top level
- **SC-004**: AI agents can successfully execute all build commands listed in AGENTS.md
- **SC-005**: Zero references to deleted/renamed modules in any documentation file
- **SC-006**: README.md accurately describes current feature set with correct symbols
