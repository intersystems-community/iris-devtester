# Implementation Plan: Agent Skills for iris-devtester

**Branch**: `019-agent-skills` | **Date**: 2026-01-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-agent-skills/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature exposes core `iris-devtester` functionality (container management, DB connection, fixtures, troubleshooting) as "Agent Skills" - structured markdown guidance files that enable AI coding assistants (Claude, Cursor, Copilot) to autonomously perform tasks. This transforms the repository from "tool-rich" to "agent-native".

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Markdown (primary), Python 3.9+ (for snippet examples)
**Primary Dependencies**: None (skills are static documentation)
**Storage**: File system (git)
**Testing**: Manual validation of skill instructions, potential for automated doctest-like verification
**Target Platform**: Claude Code, GitHub Copilot, Cursor IDE
**Project Type**: Documentation/Configuration extension to existing Python library
**Performance Goals**: <60s for container start skill execution, <30s for troubleshooting resolution
**Constraints**: Vendor-agnostic content, self-contained files (no external links for critical paths)
**Scale/Scope**: 5 core skills initially, extensible pattern

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Library-First**: Skills are modular, self-contained "libraries" of knowledge.
- [x] **II. CLI Interface**: Skills document and leverage the existing CLI interface.
- [x] **III. Test-First**: Success criteria (SC-001 to SC-005) define the testable outcomes.
- [x] **IV. Integration Testing**: Skills are integration tested by their nature (end-to-end workflows).
- [x] **V. Fail Fast**: FR-014 ensures troubleshooting skills provide immediate inline remediation.

## Project Structure

### Documentation (this feature)

```text
specs/019-agent-skills/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
.claude/
└── commands/               # Claude Code Skills
    ├── container.md
    ├── connection.md
    ├── fixture.md
    └── troubleshooting.md

.github/
└── copilot-instructions.md # GitHub Copilot Instructions (Updated)

.cursor/
└── rules/                  # Cursor Rules (New)
    ├── iris-container.mdc
    ├── iris-connection.mdc
    └── iris-fixtures.mdc

AGENTS.md                   # Central Skill Index (Updated)
```

**Structure Decision**: Hybrid approach (FR-001) using platform-specific directories to maximize compatibility while maintaining core content parity manually (FR-013).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Duplicate Content | Multi-platform support (FR-001) | Single source requires complex build/gen system (rejected per Clarification Q1) |
