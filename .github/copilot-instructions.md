# GitHub Copilot Instructions for iris-devtester

You are an AI coding assistant working in the `iris-devtester` repository. This project provides infrastructure utilities for testing InterSystems IRIS databases with Python.

## Core Principles (Constitution)
1. **Library-First**: Functionality must be reusable library code, not just scripts.
2. **CLI Interface**: All library features must be exposed via CLI.
3. **Test-First**: TDD is mandatory.
4. **DBAPI-First**: Always use `iris.connect()` (DBAPI), never JDBC unless testing JDBC specifically.
5. **Fail Fast with Guidance**: Error messages must include context, root cause, and remediation.

## Agent Skills

### 1. Container Management
**Goal**: Start/Stop IRIS containers for testing.
**Key Files**: `iris_devtester/cli/container.py`, `iris_devtester/containers/iris_container.py`
**Instructions**:
- Use `iris-devtester container up` to start.
- Always use `with IRISContainer() as iris:` context manager in code.
- Wait for health check (port 1972 open AND Superserver ready).

### 2. Database Connection
**Goal**: Connect to IRIS using DBAPI.
**Key Files**: `iris_devtester/connections/dbapi.py`, `iris_devtester/utils/enable_callin.py`
**Instructions**:
- **Critical**: CallIn service MUST be enabled before connecting (`enable_callin_service()`).
- Use `get_connection()` factory.
- Handle "Password change required" errors using `reset_password()`.

### 3. Fixture Management
**Goal**: Load test data.
**Key Files**: `iris_devtester/fixtures/`, `iris_devtester/cli/fixture_commands.py`
**Instructions**:
- Use `iris-devtester fixture load` to populate data.
- Use `iris-devtester fixture create` to export current namespace state.
- Fixtures are `.dat` files with a `manifest.json`.

### 4. Troubleshooting
**Common Issues**:
- **CallIn Disabled**: Run `iris-devtester container enable-callin`.
- **Password Change**: Run `iris-devtester container reset-password`.
- **Image Not Found**: Check Community (`intersystemsdc/`) vs Enterprise (`intersystems/`) prefix.
- **Mac Networking**: Use `127.0.0.1` instead of `localhost`.
