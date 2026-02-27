# Implementation Plan: Fix Namespace Auto-Creation Container Lookup

**Branch**: `027-fix-namespace-lookup` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/027-fix-namespace-lookup/spec.md`

## Summary

The namespace auto-creation logic in `ensure_namespace_exists()` unconditionally defaults to Docker container name `iris_db` when no `container_name` is set, even when the user provides an explicit `IRISConfig` with host/port. This causes spurious Docker lookup errors. The fix introduces a two-strategy namespace checking approach: (1) use `iris.connect()` to `%SYS` for SQL/ObjectScript-based namespace verification when no container name is available, and (2) preserve Docker-exec-based checking when a container name is known (auto-discovered configs). The hardcoded `iris_db` fallback is removed from the namespace path.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: `intersystems-irispython` (IRIS DBAPI), `docker` (Docker SDK), `click` (CLI)
**Storage**: N/A (no new storage; queries IRIS `%SYS` namespace metadata)
**Testing**: pytest (unit + integration); `tests/unit/test_namespace_utils.py`, `tests/integration/test_implicit_namespace.py`
**Target Platform**: Linux, macOS, Windows (PyPI package)
**Project Type**: Single Python package (library)
**Performance Goals**: N/A (bug fix; no new perf requirements)
**Constraints**: Must maintain backward compatibility with existing `get_connection()` zero-config flow
**Scale/Scope**: 2 files modified (`namespace.py`, `connection.py`), 1-2 new test files, ~150 LOC delta

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | Automatic Remediation | PASS | FR-007: connection proceeds even if namespace check fails; graceful degradation preserved |
| 2 | Right Tool for the Job | PASS | Uses `iris.connect()` + `classMethodValue` for namespace existence check (ObjectScript operation per constitution). Does NOT use DBAPI for namespace ops. Docker exec preserved when container name is known. |
| 3 | Isolation by Default | PASS | No change to test isolation; existing testcontainers approach untouched |
| 4 | Zero Configuration Viable | PASS | FR-003: auto-discovered config path unchanged. Zero-config still works. |
| 5 | Fail Fast with Guidance | PASS | FR-005: clear log messages distinguishing "no container for Docker exec" from "namespace not found" |
| 6 | Enterprise Ready, Community Friendly | PASS | No edition-specific changes |
| 7 | Medical-Grade Reliability | PASS | FR-007: graceful fallback. All error paths produce actionable logs. Idempotent (safe to retry). |
| 8 | Official IRIS Python API | PASS | Uses `iris.connect()` + `iris.createIRIS()` + `classMethodValue("Config.Namespaces", "Exists", ...)` — official API only |
| 9 | SQLite-Level Ergonomics | PASS | This fix improves ergonomics by removing noisy false errors from explicit config usage |
| 10 | Document the Blind Alleys | PASS | Will document why SQL query approach was rejected in favor of `iris.connect()` ObjectScript |

**GATE RESULT: PASS** — No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/027-fix-namespace-lookup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — no new entities)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
iris_devtester/
├── utils/
│   └── namespace.py          # PRIMARY: Refactor ensure_namespace_exists(), add iris.connect() path
├── connections/
│   └── connection.py         # SECONDARY: Remove iris_db fallback from password reset path

tests/
├── unit/
│   └── test_namespace_utils.py   # UPDATE: Add tests for new strategy selection logic
└── integration/
    └── test_implicit_namespace.py # UPDATE: Add test for explicit config without container_name
```

**Structure Decision**: Single Python package. Changes are confined to 2 production files and 2 test files. No new modules needed — the namespace checking strategy is added within the existing `namespace.py`.

## Complexity Tracking

> No constitution violations to justify. All principles satisfied.
