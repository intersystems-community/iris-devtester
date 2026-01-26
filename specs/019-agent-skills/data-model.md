# Data Model: Agent Skills

**Feature Branch**: `019-agent-skills` | **Date**: 2026-01-02

## Skill Entity

Each skill is a markdown file representing a discrete capability.

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Unique identifier (e.g., `container`, `connection`) |
| `description` | String | One-line summary for discovery |
| `globs` | List[String] | File patterns that trigger this skill (Cursor specific) |
| `prerequisites` | List[String] | Conditions that must be met before execution |
| `cli_commands` | List[Command] | CLI operations available in this skill |
| `python_api` | List[Snippet] | Python code patterns |
| `troubleshooting` | List[ErrorPattern] | Common errors and fixes |

## File Structure

### Claude Code (`.claude/commands/`)

No frontmatter required, filename is the command trigger.

```markdown
# description: [Description]

[Content]
```

### Cursor Rules (`.cursor/rules/`)

Requires frontmatter for context targeting.

```markdown
---
description: [Description]
globs: [Patterns]
---
[Content]
```

### Copilot Instructions (`.github/copilot-instructions.md`)

Single file embedding summaries.

```markdown
# Skills

## [Name]
[Description]
[Key Instructions]
```
