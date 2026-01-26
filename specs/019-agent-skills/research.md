# Research: Agent Skills for iris-devtester

**Feature Branch**: `019-agent-skills` | **Date**: 2026-01-02

## 1. Skill Delivery Formats

### Decision: Multi-Platform Support
We will support the three major AI coding assistants through their native configuration mechanisms:

1. **Claude Code**: `.claude/commands/*.md`
   - **Rationale**: Native slash command support (e.g., `/container`).
   - **Format**: Standard markdown with strict structure.
   
2. **Cursor IDE**: `.cursor/rules/*.mdc`
   - **Rationale**: Cursor's new "Rules" feature supports modular, project-specific rules in `.cursor/rules/`. The `.mdc` extension is the standard for these files.
   - **Format**: Markdown with frontmatter glob patterns (`globs`) and description.

3. **GitHub Copilot**: `.github/copilot-instructions.md`
   - **Rationale**: Copilot uses a single instructions file.
   - **Format**: Single file with summarized "Skills" section referencing the markdown files or embedding key instructions.

### Alternatives Considered
- **Single AGENTS.md**: Too generic, doesn't leverage native tool capabilities (slash commands, auto-context).
- **Build System**: Generating tool-specific files from a master source. Rejected for V1 to reduce complexity (manual sync chosen).

## 2. Skill Content Structure

### Template for Skill Files

```markdown
---
description: [One line description]
globs: [Pattern to auto-trigger in Cursor]
---

# Skill: [Name]

## Prerequisites
- [Check 1]
- [Check 2]

## CLI Commands
[Command examples]

## Python API
[Code examples]

## Troubleshooting
[Common errors and fixes]
```

## 3. CLI Command Mapping

| Skill | Commands | Implementation |
|-------|----------|----------------|
| **container** | `up`, `start`, `stop`, `restart`, `status`, `logs`, `remove`, `reset-password`, `enable-callin` | `cli/container.py` |
| **connection** | `test-connection` | `cli/connection_commands.py` |
| **fixture** | `create`, `load`, `validate`, `list`, `info` | `cli/fixture_commands.py` |
| **troubleshooting** | (None - Documentation only) | N/A |

**Note**: `cli/container_commands.py` is unused/redundant and should be ignored in favor of `cli/container.py`.

## 4. Troubleshooting Patterns

Critical patterns identified to include in `troubleshooting.md`:

1. **Authentication**: `[SQLCODE: <-853>...]` (ChangePassword flag), MacOS `Access Denied` (latency/IPv6 issues).
2. **Connectivity**: `CallIn service not available`, `_DBAPI` import errors.
3. **Environment**: `DockerException` (daemon down), `image not found` (Community vs Enterprise prefix).
4. **Health**: Port 1972 open but connection fails (System Monitor state).
