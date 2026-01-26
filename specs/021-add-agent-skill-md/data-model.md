# Data Model: AI Agent Skill.md

**Feature Branch**: `021-add-agent-skill-md` | **Date**: 2026-01-02

## Entities

### `SkillManifest`
Represents the root configuration for all agent skills.

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Unique identifier for the skill set |
| `description` | String | High-level summary used for discovery |
| `triggers` | List[String] | Keywords/Commands that activate the skill |
| `modules` | List[SkillModule] | Hierarchical capabilities |

### `SkillModule`
A discrete capability of the library.

| Field | Type | Description |
|-------|------|-------------|
| `level` | Integer | 1 (Essential) to 4 (Advanced) |
| `title` | String | Module name (e.g., "Container Lifecycle") |
| `prerequisites` | List[String] | What an agent needs to know/have before using |
| `commands` | List[CLICommand] | Relevant CLI operations |
| `snippets` | List[PythonSnippet] | Valid code examples |
| `troubleshooting` | List[ErrorFix] | Specific remediation logic |

## Relationships

- `SkillManifest` HAS-MANY `SkillModule` (Hierarchical)
- `SkillModule` REFERENCES `docs/learnings/*.md` (Level 3 disclosure)
- `SkillModule` CONFORMS-TO `CONSTITUTION.md` (Constraint)
