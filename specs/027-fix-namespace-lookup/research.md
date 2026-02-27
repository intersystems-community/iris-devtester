# Research: Fix Namespace Auto-Creation Container Lookup

**Feature**: 027-fix-namespace-lookup
**Date**: 2026-02-27

## Research Questions

### R1: How to check namespace existence without Docker exec?

**Decision**: Use `iris.connect()` to `%SYS` + `iris.createIRIS()` + `classMethodValue("Config.Namespaces", "Exists", namespace_name)`.

**Rationale**:
- The project constitution (Principle 2) explicitly mandates `iris.connect()` for namespace operations — NOT DBAPI/SQL.
- The `docs/SQL_VS_OBJECTSCRIPT.md` decision matrix classifies namespace create/delete as `iris.connect()` operations. Namespace existence checking is the same class of operation.
- The codebase already uses `##class(Config.Namespaces).Exists(...)` via docker exec (in `namespace.py` line 41). The `iris.connect()` equivalent is a direct translation: `classMethodValue("Config.Namespaces", "Exists", name)`.
- SQL query against `%SYS.Namespace` was considered but: (a) column names are not validated, (b) the constitution says namespace ops go through `iris.connect()`, (c) ObjectScript `Config.Namespaces.Exists()` is the canonical API.

**Alternatives considered**:
1. **SQL query `SELECT COUNT(*) FROM %SYS.Namespace WHERE Nsp = ?`**: Rejected. Column name unvalidated, and constitution says namespace ops use `iris.connect()` not DBAPI.
2. **Attempt direct connection to target namespace and catch errors**: Rejected. Some namespaces may exist but be inaccessible, and error messages vary across IRIS versions — fragile.
3. **Skip existence check entirely for explicit configs**: Rejected. Would lose the ergonomic auto-creation capability for users who provide explicit host/port but want auto-namespace-creation.

### R2: What is the strategy selection logic?

**Decision**: The `ensure_namespace_exists()` function should select a strategy based on whether `container_name` is available:

1. If `config.container_name` is set (non-None, non-empty) → use Docker exec (existing path)
2. If `config.container_name` is not set → use `iris.connect()` to `%SYS` (new path)
3. Never fall back to hardcoded `iris_db`

**Rationale**:
- `container_name` being set means the config was either auto-discovered from a running container or explicitly provided by the user — Docker exec is appropriate.
- `container_name` being unset means either: (a) explicit config with host/port only, or (b) env-var-based config without container info — `iris.connect()` is the only viable option.
- This is a clean, deterministic decision point with no ambiguity.

**Alternatives considered**:
1. **Check host value (localhost vs remote)**: Rejected. The current localhost-vs-remote heuristic is orthogonal to the strategy choice. A localhost connection without a container name should still use `iris.connect()`.
2. **Try Docker exec first, fall back to iris.connect()**: Rejected. This is the current buggy behavior (trying `iris_db` as fallback).

### R3: How to handle namespace creation (not just existence check) via iris.connect()?

**Decision**: Use `iris.createIRIS(conn).classMethodValue("Config.Namespaces", "Create", namespace_name, properties)` — same pattern already documented in `docs/SQL_VS_OBJECTSCRIPT.md` and `specs/018-fast-container-startup/research.md`.

**Rationale**:
- This is the established pattern in the codebase (see `docs/SQL_VS_OBJECTSCRIPT.md` lines 115-119).
- The `Config.Namespaces.Create()` method takes a namespace name and a properties object.
- For simple creation, the default properties (inheriting from the `USER` database) are sufficient.

**Alternatives considered**:
1. **Only check existence, never create via iris.connect()**: Partial approach. If we can check via `iris.connect()`, we should also be able to create — otherwise the auto-creation feature only works when Docker exec is available.

### R4: What connection parameters does iris.connect() need for the %SYS bootstrap?

**Decision**: Use `config.host`, `config.port`, `config.username`, `config.password` with `namespace="%SYS"`. These are the same credentials the user provided in their `IRISConfig`.

**Rationale**:
- Per clarification session (2026-02-27): "Use same credentials from user's IRISConfig; fail gracefully if %SYS access denied."
- The `_SYSTEM` user (project default) has `%SYS` access. Most admin users do.
- If access is denied, the check fails gracefully and the connection proceeds (FR-007).

### R5: Where exactly should the iris_db fallback be removed?

**Decision**: Remove `or "iris_db"` from two locations:
1. `iris_devtester/utils/namespace.py` line 162: `container_name = config.container_name or "iris_db"` → `container_name = config.container_name`
2. `iris_devtester/connections/connection.py` line 122: `container_name = getattr(config, "container_name", "iris_db") or "iris_db"` → `container_name = getattr(config, "container_name", None)`

**Rationale**:
- FR-004 explicitly prohibits hardcoded container name fallback.
- Other files that use `iris_db` as a default (e.g., `enable_callin.py`, `password.py`, `container_status.py`) are out of scope per spec assumptions — they are utility functions with their own default parameter signatures.

### R6: Blind Alley — Why not use SQL/DBAPI for namespace existence check?

**Decision**: Document this as a blind alley.

**What was considered**: Using `cursor.execute("SELECT COUNT(*) FROM %SYS.Namespace WHERE ...")` via DBAPI.

**Why it was rejected**:
1. Constitution Principle 2 mandates `iris.connect()` for namespace operations, not DBAPI.
2. The `%SYS.Namespace` table column names are not validated in the codebase.
3. The `Config.Namespaces.Exists()` ObjectScript method is the canonical IRIS API for this check.
4. Using DBAPI would require connecting to `%SYS` via DBAPI, which has different connection semantics than `iris.connect()`.

**What was chosen instead**: `iris.connect()` + `classMethodValue("Config.Namespaces", "Exists", ...)` — direct translation of the existing Docker exec ObjectScript.
