# Research: AI Agent Skill.md

**Feature Branch**: `021-add-agent-skill-md` | **Date**: 2026-01-02

## 1. Skill Delivery & Triggers

### Claude Code
- **Trigger**: Slash commands (`/container`, `/connection`).
- **Format**: `.claude/commands/*.md` files.
- **Progressive Disclosure**: Claude loads descriptions at startup, then full body on activation.

### Cursor IDE
- **Trigger**: Project Rules (`.cursor/rules/*.mdc`).
- **Format**: YAML frontmatter with `globs` and `description`.
- **Hierarchical Support**: Can link multiple rules or use a master rule that imports others.

### Generic Agents (Open Standard)
- **Standard**: `agentskills.io` specification.
- **Triggers**: YAML `name`, `description`, `metadata`.
- **Level Hierarchy**:
    - Level 1: Name/Description (Discovery)
    - Level 2: Body (Instructions)
    - Level 3: External Resources (Detailed references)

## 2. Best Practices for "Skill.md"

- **Command-First**: Put executable CLI commands and Python snippets early in the document.
- **Conciseness**: Keep the main instruction set under 500 lines or 5000 tokens.
- **Validation Workflows**: Provide checklists for agents to verify their own work (e.g., "Step 5: Run `iris-devtester container status`").
- **Persona Alignment**: Guidance should be written for an AI persona (e.g., "You are an expert at IRIS testing").

## 3. Hierarchical Structure Decision

- **L1: Onboarding**: "Project Integration" (How to add to project).
- **L2: Operations**: "Lifecycle & Connectivity" (Containers, connections, remediation).
- **L3: Advanced**: "Testing & Performance" (DAT fixtures, benchmarking).
- **L4: Debugging**: "Autonomous Troubleshooting" (ObjectScript patterns, deep logs).

## 4. Alternatives Considered

- **Multiple Small Files**: Harder to discover for generic agents.
- **One Large AGENTS.md**: Bloats the context window too early.
- **Hybrid (Single root with sections)**: Chosen for balance between discoverability and context management.
