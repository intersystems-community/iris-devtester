# Feature Specification: Connection Diagnostics and Schema Visibility Probes

**Feature Branch**: `031-connection-diagnostics`
**Created**: 2026-04-25
**Status**: Draft

## Background / Motivation

When an iris-devtester-managed connection fails to find tables (SQLCODE -30), the current experience is:

```
iris.dbapi.ProgrammingError: <SQL ERROR>; Details: [SQLCODE: <-30>:<Table or view not found>]
[%msg: < Table 'GRAPH_KG.NODES' not found>]
```

No context. No hint. The developer spends 30+ minutes ruling out:
- wrong credentials (test/test vs _SYSTEM)
- wrong namespace
- schema not initialized (initialize_schema() not called)
- container fresh (tables don't exist yet)
- schema search path missing Graph_KG
- probing container outside pytest before fixtures seeded it

This spec captures the **hard-won lesson**: a manual `iris.connect()` probe to an iris-devtester container sees a completely different table visibility than the test fixture connection — not because of auth, but because the schema hasn't been seeded yet when you probe before the first test runs. The asymmetry is invisible.

---

## User Scenarios & Testing

### US1 — SQLCODE -30 surfaces actionable diagnostics (P1)

A developer runs a test that fails with "Table 'GRAPH_KG.NODES' not found".
Instead of the raw SQLCODE, they see:

```
ConnectionDiagnosticError: Table 'Graph_KG.nodes' not found (SQLCODE -30)

Diagnostic results:
  ✓ Connected to IRIS at localhost:32870 as test/USER
  ✗ Graph_KG schema: NOT VISIBLE (0 tables found in INFORMATION_SCHEMA)
  ✓ USER namespace accessible
  ? initialize_schema() called: UNKNOWN

Most likely cause: initialize_schema() has not been called on this connection.
Call engine.initialize_schema() or IRISGraphEngine(conn).initialize_schema() before running queries.

If schema should exist: SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='Graph_KG'
```

**Acceptance**: SQLCODE -30 from a DBAPI cursor wraps the error with namespace/schema probe results.

### US2 — `probe_connection()` utility for manual debugging (P1)

```python
from iris_devtester import probe_connection
result = probe_connection(conn)
print(result.report())
```

Returns a `ConnectionProbe` with:
- namespace, current user, IRIS version
- schemas visible (INFORMATION_SCHEMA.SCHEMATA)
- table count per schema
- whether specific schema/tables exist
- latency of the probe round-trip

**Acceptance**: `probe_connection(conn)` takes <200ms and returns a `ConnectionProbe` with a `.report()` string and `.schemas` dict.

### US3 — `IRISContainer.health_check()` exposes schema visibility (P2)

```python
container = IRISContainer.attach("iris_vector_graph")
health = container.health_check()
print(health.schemas)          # {'Graph_KG': 7, 'SQLUser': 0}
print(health.tables_visible)   # True
```

**Acceptance**: `health_check()` returns a structured result including schema names and table counts.

### US4 — Conftest fixture emits schema-seeded confirmation (P2)

After `initialize_schema()` is called in test setup, the fixture logs:

```
[iris-devtester] Schema seeded: Graph_KG (8 tables), USER namespace
```

**Acceptance**: A log line at DEBUG level is emitted by the `iris_connection` fixture after schema init succeeds.

### US5 — Hard-won pattern documented in troubleshooting guide (P1)

The docs include a "Troubleshooting: Table not found" page covering:
1. Connection outside pytest probes an empty container (tables don't exist until initialize_schema() runs)
2. `_SYSTEM` password expires on fresh containers — use `test/test`
3. `Graph_KG` schema not in SQL search path unless fully qualified
4. How to probe manually: `probe_connection(conn).report()`

**Acceptance**: `docs/troubleshooting/table-not-found.md` exists and covers all 4 scenarios.

---

### Edge Cases

- `probe_connection()` called with an already-closed connection → raises `ConnectionClosedError` with clear message
- Container restarted mid-test → SQLCODE -30 on reconnect surfaces "container may have restarted" hint
- `Graph_KG` tables exist but user lacks SELECT privilege → distinct message from "tables don't exist"
- probe_connection called with embedded connection (EmbeddedConnection) → returns "embedded" probe with iris namespace info

---

## Requirements

- **FR-001**: SQLCODE -30 errors from any iris-devtester-managed cursor MUST be wrapped with a `ConnectionDiagnosticError` that includes namespace, schema visibility, and suggested fix
- **FR-002**: `probe_connection(conn) -> ConnectionProbe` MUST be importable from `iris_devtester`; probe takes <200ms; returns `.report() -> str` and `.schemas -> dict[str, int]`
- **FR-003**: `ConnectionProbe.report()` MUST include: IRIS host:port, namespace, current user, list of visible schemas with table counts, most likely cause of failure if probe was triggered by an error
- **FR-004**: `IRISContainer.health_check() -> ContainerHealth` MUST include schema visibility (schema names + table counts)
- **FR-005**: The `iris_connection` pytest fixture MUST emit a DEBUG log line after schema initialization confirming namespace and table count
- **FR-006**: `docs/troubleshooting/table-not-found.md` MUST be created covering the 4 scenarios in US5
- **FR-007**: `ConnectionDiagnosticError` MUST be a subclass of the existing iris-devtester connection error hierarchy, not a raw exception

## Key Entities

- **`ConnectionProbe`**: Result object from `probe_connection()`. Fields: `host`, `port`, `namespace`, `username`, `iris_version`, `schemas: dict[str, int]`, `latency_ms: float`, `error: Optional[str]`
- **`ConnectionDiagnosticError`**: Wraps SQLCODE -30 (and optionally -23 label errors) with enriched context
- **`ContainerHealth`**: Extended health check result including schema probe

## Success Criteria

- **SC-001**: A fresh container where `initialize_schema()` was never called produces a `ConnectionDiagnosticError` with "Graph_KG schema not visible" and suggested fix in the message
- **SC-002**: `probe_connection(conn).report()` runs in <200ms on a live container and includes schema names
- **SC-003**: The 30-minute debugging session described in Background would take <5 minutes with these tools in place
- **SC-004**: Troubleshooting doc covers all 4 hard-won scenarios

## Clarifications

### Session 2026-04-25

- Q: Should `ConnectionDiagnosticError` wrap ALL SQLCODE errors or only -30? → A: At minimum -30 (table not found) and -23 (label not in applicable tables, which is the CTE scoping error). These are the two most confusing IRIS-specific errors for new users.
- Q: Should probe_connection() be synchronous or async? → A: Synchronous — iris-devtester is a sync-first library; async would require a separate interface.
- Q: Should wrapping be opt-in (via config) or always-on? → A: Always-on for -30 and -23; other SQLCODE errors pass through unchanged to avoid obscuring genuine SQL bugs.

### Session 2026-04-25 (implementation)

- Q: Where should SQLCODE -30/-23 interception live? → A: Cursor wrapper always-on — `conn.cursor()` returns a `DiagnosticCursor` for all iris-devtester-managed connections. Zero call-site changes required downstream.
- Q: How should `ContainerHealth.schemas` handle backward compatibility? → A: `Optional[dict[str, int]] = None` — existing construction code unchanged; `None` means schema probe was not run.
