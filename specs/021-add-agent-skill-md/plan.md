# Implementation Plan: AI Agent Skill.md

**Branch**: `021-add-agent-skill-md` | **Date**: 2026-01-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-add-agent-skill-md/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature involves creating a `SKILL.md` file at the repository root that serves as an "Agent Onboarding Manual". It will provide a hierarchical set of skills following the "Progressive Disclosure" pattern, enabling AI coding assistants to autonomously setup, operate, and troubleshoot IRIS-based testing environments using `iris-devtester`.

## Technical Context

**Language/Version**: Markdown (primary), Python 3.9+ (snippets)  
**Primary Dependencies**: None (Static documentation)  
**Storage**: N/A (File system)  
**Testing**: Structural validation of YAML metadata, functional validation of code snippets in Python 3.9+  
**Target Platform**: Claude Code, Cursor IDE, generic AI agents  
**Project Type**: single  
**Performance Goals**: File size < 5000 tokens for context window efficiency  
**Constraints**: MUST follow the "Agent Skills" open standard format; MUST enforce "Constitution" principles in all guidance  
**Scale/Scope**: Single root file indexing multiple logical skill modules  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Automatic Remediation**: Guidance MUST prioritize auto-remediation steps over manual fixes.
- [x] **II. DBAPI First**: All connection snippets MUST use `get_connection()` or `create_dbapi_connection()`.
- [x] **III. Isolation by Default**: Setup snippets MUST use unique container names or namespaces.
- [x] **IV. Zero Configuration**: Basic onboarding MUST work with minimal environment variables.
- [x] **V. Fail Fast with Guidance**: Troubleshooting sections MUST include root cause analysis patterns.
- [x] **VI. Enterprise & Community**: Snippets MUST cover both `IRISContainer.community()` and `IRISContainer.enterprise()`.
- [x] **VII. Medical-Grade Reliability**: Documentation MUST include validation steps for each operation.
- [x] **VIII. Document Blind Alleys**: Troubleshooting SHOULD explain why common pitfalls (like manual delays) are avoided.

## Project Structure

### Documentation (this feature)

```text
specs/021-add-agent-skill-md/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
SKILL.md                 # NEW: Root skill manifest and core instructions
docs/
└── features/
    └── agent-skills.md  # Reference for human-facing agent docs
```

**Structure Decision**: Single project. The primary artifact is `SKILL.md` at the root for maximum discoverability by agents.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
