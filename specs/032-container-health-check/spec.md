# Feature Specification: Container Health Check and Full Diagnostic API

**Feature Branch**: `032-container-health-check`
**Created**: 2026-04-25
**Status**: Draft

## Clarifications

### Session 2026-04-25

- Q: When `health_check()` is called with no active connection, how should it obtain one? → A: Reuse `get_connection()` — same path as all other methods (enables CallIn, unexpires passwords). Connection left open on `self._connection`.

## Background

Feature 031 (1.16.0) gave developers `probe_connection(conn)` to inspect schema state after a connection is in hand. But the most common failure mode is connecting to a container, running queries, and getting SQLCODE -30 — at which point the damage is done.

`IRISContainer.health_check()` fills the remaining gap: call it *before* running queries to confirm the container is not just running but has the expected schemas seeded. This turns the "works in pytest, fails manually" class of debugging from reactive to proactive.

The other deliverable is completing the top-level export surface: `ContainerHealth`, `ConnectionDiagnosticError`, and `ConnectionProbe` should all be importable directly from `iris_devtester` so downstream consumers don't need to know internal module paths.

## User Scenarios & Testing

### US1 — Proactive schema visibility check before queries (Priority: P1)

As a developer, I want to call `container.health_check()` to confirm the schema is seeded before I run queries, instead of discovering it at SQLCODE -30 time.

**Independent Test**: Call `health_check()` on a container where `initialize_schema()` has not been called. Verify `result.tables_visible` is `False` and `result.report()` contains a warning.

**Acceptance Scenarios**:

1. **Given** a running container with no schemas seeded, **When** I call `iris.health_check()`, **Then** `result.tables_visible` is `False` and `result.report()` includes "no schemas visible" or equivalent warning.
2. **Given** a running container with `Graph_KG` seeded (7 tables), **When** I call `iris.health_check()`, **Then** `result.schemas == {"Graph_KG": 7}` and `result.tables_visible` is `True`.
3. **Given** any running container, **When** I call `iris.health_check()`, **Then** `result.report()` returns a non-empty string suitable for printing to a developer.

---

### US2 — Top-level imports for diagnostic types (Priority: P1)

As a downstream library author, I want to import `ContainerHealth`, `ConnectionDiagnosticError`, and `ConnectionProbe` from `iris_devtester` directly, without knowing internal module paths.

**Independent Test**: `from iris_devtester import ContainerHealth, ConnectionDiagnosticError, ConnectionProbe` succeeds.

**Acceptance Scenarios**:

1. **Given** `iris_devtester` installed, **When** I run `from iris_devtester import ContainerHealth`, **Then** it succeeds.
2. **Given** `iris_devtester` installed, **When** I run `from iris_devtester import ConnectionDiagnosticError`, **Then** it succeeds.
3. **Given** `iris_devtester` installed, **When** I run `from iris_devtester import ConnectionProbe`, **Then** it succeeds.

---

### US3 — ContainerHealth human-readable report (Priority: P1)

As a developer debugging a container state issue, I want `result.report()` to give me a formatted summary I can print or log — analogous to `ConnectionProbe.report()`.

**Acceptance Scenarios**:

1. **Given** a `ContainerHealth` with `schemas={"Graph_KG": 7}`, **When** I call `.report()`, **Then** it includes "Graph_KG" and "7".
2. **Given** a `ContainerHealth` with `schemas={}` or `schemas=None`, **When** I call `.report()`, **Then** it includes a human-readable warning about no schemas being visible.

---

### Edge Cases

- `health_check()` called on a container that has not been started → raises `RuntimeError` with clear message (container not running).
- `health_check()` called on an `attach()`-ed container (no active DBAPI connection) → opens a temporary connection for the probe, closes it after.
- `ContainerHealth.schemas = None` (probe not run) → `tables_visible` returns `False`, `report()` indicates probe was not run.

## Requirements

- **FR-001**: `IRISContainer` MUST expose a `health_check() -> ContainerHealth` method that calls `get_connection()` (enabling CallIn + password reset if needed), runs `probe_connection()` on the connection, and returns an enriched `ContainerHealth` with `.schemas` populated.
- **FR-002**: `ContainerHealth` MUST expose a `tables_visible` property returning `True` if `schemas` is non-empty, `False` otherwise.
- **FR-003**: `ContainerHealth` MUST expose a `report() -> str` method returning a formatted human-readable summary including schema names, table counts, and a warning if no schemas are visible.
- **FR-004**: `ContainerHealth`, `ConnectionDiagnosticError`, and `ConnectionProbe` MUST be importable directly from `iris_devtester`.
- **FR-005**: `ContainerHealth.to_dict()` MUST include the `schemas` field in its output.
- **FR-006**: All existing tests MUST continue to pass (no regressions).

## Key Entities

- **`ContainerHealth`**: Extended with `tables_visible` property and `report()` method. `schemas` field already exists from 1.16.0.
- **`IRISContainer.health_check()`**: New method. Opens a temporary DBAPI connection if needed, runs `probe_connection()`, closes temporary connection, returns enriched `ContainerHealth`.

## Success Criteria

- **SC-001**: `iris.health_check().tables_visible` is `False` on an unseeded container and `True` on a seeded one.
- **SC-002**: `from iris_devtester import ContainerHealth, ConnectionDiagnosticError, ConnectionProbe` succeeds with no `ImportError`.
- **SC-003**: `health_check().report()` includes schema names and a warning when empty.
- **SC-004**: All existing unit and contract tests pass.
