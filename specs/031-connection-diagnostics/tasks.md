# Tasks: 031-connection-diagnostics

**Branch**: `031-connection-diagnostics` | Generated: 2026-04-25

## Wave 1 — Foundation (parallel-safe)

- [ ] **T1** Create `iris_devtester/diagnostics.py`
  - `ConnectionProbe` dataclass: `host`, `port`, `namespace`, `username`, `iris_version`, `schemas: dict[str, int]`, `latency_ms: float`, `error: Optional[str]`
  - `probe_connection(conn) -> ConnectionProbe` — queries `INFORMATION_SCHEMA.TABLES` grouped by `TABLE_SCHEMA`; runs in <200ms
  - `ConnectionDiagnosticError(Exception)` — subclass of existing error hierarchy; carries `probe: ConnectionProbe`, `sqlcode: int`, `original: Exception`; `.message` includes schema visibility + suggested fix

- [ ] **T2** Create `iris_devtester/connections/cursor_wrapper.py`
  - `DiagnosticCursor` proxy: wraps DBAPI cursor, delegates all methods
  - `execute()` / `executemany()`: catch `ProgrammingError` where message contains `SQLCODE: <-30>` or `SQLCODE: <-23>`; run `probe_connection(conn)`; raise `ConnectionDiagnosticError`
  - All other exceptions pass through unchanged

## Wave 2 — Wiring (depends on Wave 1)

- [ ] **T3** Modify `iris_devtester/connections/dbapi.py`
  - After successful `get_connection()`, patch `connection.cursor` to return `DiagnosticCursor(original_cursor_fn(), connection)`
  - Import `DiagnosticCursor` from `cursor_wrapper`

- [ ] **T4** Modify `iris_devtester/__init__.py`
  - Add `from iris_devtester.diagnostics import probe_connection` to public exports

## Wave 3 — Extensions (parallel-safe, independent of Wave 2)

- [ ] **T5** Modify `iris_devtester/containers/models.py`
  - Add `schemas: Optional[dict[str, int]] = None` to `ContainerHealth` dataclass
  - No changes to existing field order — append only

- [ ] **T6** Create `docs/troubleshooting/table-not-found.md`
  - Scenario 1: Connection outside pytest probes empty container (initialize_schema not called)
  - Scenario 2: `_SYSTEM` password expired — use `test/test` or run `idt container reset-password`
  - Scenario 3: `Graph_KG` schema not in SQL search path — must fully qualify table names
  - Scenario 4: How to probe manually: `probe_connection(conn).report()`
  - Each scenario: symptom → cause → fix command

- [ ] **T9** Modify `iris_devtester/testing/fixtures.py` (FR-005)
  - After `initialize_schema()` succeeds in the `iris_connection` fixture, emit: `logger.debug(f"[iris-devtester] Schema seeded: {schema_name} ({table_count} tables), {namespace} namespace")`
  - Use `probe_connection(conn).schemas` to get the count

## Wave 4 — Tests + Regression

- [ ] **T7** Create `tests/contract/test_031_diagnostics.py`
  - `TestConnectionProbe`: `probe_connection()` returns `ConnectionProbe` with `.schemas` dict and `.report()` string
  - `TestConnectionDiagnosticError`: hierarchy check (subclass of `Exception`); carries `sqlcode` and `probe`
  - `TestDiagnosticCursor`: SQLCODE -30 → `ConnectionDiagnosticError`; SQLCODE -23 → `ConnectionDiagnosticError`; other exceptions pass through
  - `TestPublicExport`: `from iris_devtester import probe_connection` works
  - `TestContainerHealthSchemas`: `ContainerHealth` accepts `schemas=None` and `schemas={"USER": 5}`

- [ ] **T8** Verify unit regression: `pytest tests/unit/ --override-ini="addopts=" -q` → 386 pass
