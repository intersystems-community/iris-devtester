# Agent Skills Quickstart

This guide explains how to use the agent skills included in `iris-devtester`. These skills are designed to help AI coding assistants (Claude, Cursor, Copilot) autonomously manage IRIS containers and workflows.

## For Claude Code Users

The skills are automatically available as slash commands if you are in the project root.

1. **Start a Container**:
   ```text
   /container start
   ```

2. **Fix Issues**:
   If you encounter an error, use the troubleshooting skill:
   ```text
   /troubleshoot
   ```

3. **Load Data**:
   ```text
   /fixture load --name test-data
   ```

## For Cursor Users

The skills are defined as Project Rules in `.cursor/rules/`. Cursor will automatically load the relevant skill based on your context.

- Open a file related to containers -> **Container Skill** activates
- Edit a test file -> **Fixture Skill** activates
- Encounter an error in terminal -> **Troubleshooting Skill** activates

You can also explicitly reference them in chat:
> "Use the @container skill to reset the password"

## For GitHub Copilot Users

The skills are embedded in `.github/copilot-instructions.md`. Copilot is aware of them by default.

You can ask:
> "How do I start the IRIS container using the defined skills?"

## Available Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| **Container** | `/container` | Lifecycle management (up, down, status) |
| **Connection** | `/connection` | DBAPI connection and retry logic |
| **Fixture** | `/fixture` | Test data management |
| **Troubleshooting** | `/troubleshoot` | Error diagnosis and remediation |
