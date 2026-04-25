# Tasks: 032-container-health-check

**Branch**: `032-container-health-check` | Generated: 2026-04-25

## Wave 1 — ContainerHealth extensions (FR-002, FR-003, FR-005)

- [ ] **T1** Modify `iris_devtester/containers/models.py`
  - Add `tables_visible` property: returns `True` if `self.schemas` is not None and `len(self.schemas) > 0`
  - Add `report() -> str` method: formatted summary of container name, status, schema names+counts; warning line if `schemas` is None or empty
  - Update `to_dict()` to include `"schemas": self.schemas`

## Wave 2 — IRISContainer.health_check() (FR-001)

- [ ] **T2** Modify `iris_devtester/containers/iris_container.py`
  - Add `health_check() -> ContainerHealth` method
  - Calls `self.get_connection()` to obtain (or reuse) DBAPI connection
  - Calls `probe_connection(conn)` from `iris_devtester.diagnostics`
  - Constructs and returns `ContainerHealth` with existing fields + `schemas=probe.schemas`

## Wave 3 — Top-level exports (FR-004)

- [ ] **T3** Modify `iris_devtester/__init__.py`
  - Import and export `ContainerHealth` from `iris_devtester.containers.models`
  - Import and export `ConnectionDiagnosticError` from `iris_devtester.diagnostics`
  - Import and export `ConnectionProbe` from `iris_devtester.diagnostics`
  - Add all three to `__all__`

## Wave 4 — Tests + Version

- [ ] **T4** Create `tests/contract/test_032_health_check.py`
  - `test_tables_visible_false_when_schemas_empty`: `ContainerHealth(schemas={}).tables_visible == False`
  - `test_tables_visible_true_when_schemas_populated`: `ContainerHealth(schemas={"G": 7}).tables_visible == True`
  - `test_report_includes_warning_on_empty_schemas`: `"warning"` or `"no schema"` or `"not visible"` in `.report().lower()`
  - `test_report_includes_schema_names_when_present`: schema names + counts appear in `.report()`
  - `test_top_level_imports`: all three new exports importable from `iris_devtester`
  - `test_iris_container_has_health_check`: `hasattr(IRISContainer, "health_check")` and callable

- [ ] **T5** Unit regression: `pytest tests/unit/ --override-ini="addopts=" -q` → 386 pass

- [ ] **T6** Version bump: `pyproject.toml` and `iris_devtester/__init__.py` → `1.17.0`
