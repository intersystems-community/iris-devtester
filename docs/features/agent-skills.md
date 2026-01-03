# Agent Skills

**Automatic configuration and guidance for AI coding assistants**

`iris-devtester` includes built-in "Skills" that enable AI agents (Claude, Cursor, GitHub Copilot) to autonomously manage your IRIS development environment. Instead of pasting documentation into your chat window, the library provides structured, executable guidance that agents understand natively.

## What Are Skills?

Skills are specialized markdown files that teach AI agents how to perform specific tasks. They include:
- **Prerequisite checks** (Is Docker running?)
- **CLI command patterns** (How do I start a container?)
- **Python API examples** (How do I connect securely?)
- **Troubleshooting logic** (What does this error mean and how do I fix it?)

## Supported Platforms

| Platform | Mechanism | Location |
|----------|-----------|----------|
| **Claude Code** | Slash Commands | `.claude/commands/*.md` |
| **Cursor IDE** | Project Rules | `.cursor/rules/*.mdc` |
| **GitHub Copilot** | Custom Instructions | `.github/copilot-instructions.md` |

## Available Skills

### 1. Container Management
**Triggers**: `/container` (Claude), `@iris-container` (Cursor)
**Capabilities**:
- Start/Stop IRIS Community containers (zero-config)
- Check health status
- View logs
- Reset passwords automatically

### 2. Connection Management
**Triggers**: `/connection` (Claude), `@iris-connection` (Cursor)
**Capabilities**:
- Verify database connectivity
- Enable CallIn service (required for DBAPI)
- Handle authentication retries

### 3. Fixture Management
**Triggers**: `/fixture` (Claude), `@iris-fixtures` (Cursor)
**Capabilities**:
- Load test data from DAT files
- Export current namespace state to fixtures
- Validate fixture integrity

### 4. Troubleshooting
**Triggers**: `/troubleshoot` (Claude), `@iris-troubleshooting` (Cursor)
**Capabilities**:
- Diagnose "CallIn service not available"
- Fix "Password change required" errors
- Resolve macOS networking issues

## Usage

### In Claude Code
Type `/` to see available commands:
```text
/container up
/troubleshoot
```

### In Cursor
Reference the skill in your chat:
> "Use @iris-container to start a fresh database for testing"

Cursor will automatically load the relevant rule when you open related files (e.g., `docker-compose.yml`, test files).

### In GitHub Copilot
Just ask naturally. Copilot has been pre-prompted with the library's best practices:
> "How do I load the test data?"

## Customization

The skills are installed as part of the repository structure. You can customize them by editing the files in `.claude/commands/` or `.cursor/rules/`, but we recommend keeping them in sync with the library updates.

## Agent Skill Manifest
The primary entry point for AI agents is the **[skill.md](../../skill.md)** file at the repository root. This file provides:
- Hierarchical guidance (Setup to Advanced)
- Copy-paste ready Python snippets
- Constitutional enforcement
- Troubleshooting flowcharts for agents
