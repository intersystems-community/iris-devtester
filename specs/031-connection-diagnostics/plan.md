# Implementation Plan: Connection Diagnostics and Schema Visibility

**Branch**: `031-connection-diagnostics` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)

## Summary

Add a diagnostic layer to surface actionable context when IRIS DBAPI queries fail with SQLCODE -30 (table not found) or -23 (label not applicable). Three deliverables: `probe_connection()` utility, `ConnectionDiagnosticError` wrapping, troubleshooting doc.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: intersystems-irispython (iris.dbapi), existing iris-devtester connection stack
**Storage**: N/A — diagnostic-only, no persistence
**Testing**: pytest (unit + contract)
**Constraints**: Must not break existing tests; `probe_connection()` <200ms; always-on (no opt-in required)

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| 5. Fail Fast with Guidance | PASS | Core purpose of this feature |
| 7. Medical-Grade Reliability | PASS | Diagnostic cursor must not swallow non -30/-23 errors |
| 2. DBAPI First | PASS | DiagnosticCursor wraps DBAPI cursor only |
| 4. Zero Configuration | PASS | Always-on, no config needed |
| 8. Document Blind Alleys | PASS | Troubleshooting doc is the explicit deliverable |

## Architecture Decision

**Intercept point**: `DiagnosticCursor` wraps the DBAPI cursor returned by `conn.cursor()`. Implemented as a thin proxy class — delegates all methods to the underlying cursor, intercepts only `execute()` and `executemany()` to catch `ProgrammingError` with SQLCODE -30/-23.

Wrapping happens at `create_dbapi_connection()` return: patch `conn.cursor` with a lambda that calls the original cursor factory and wraps the result in `DiagnosticCursor(original_cursor, conn)`. No call-site changes needed downstream.

## File Map

```
iris_devtester/
├── diagnostics.py                    # NEW: ConnectionProbe, probe_connection(), ConnectionDiagnosticError
├── connections/
│   ├── cursor_wrapper.py             # NEW: DiagnosticCursor proxy class
│   └── dbapi.py                      # MODIFY: wrap returned connection's cursor()
├── containers/
│   └── models.py                     # MODIFY: ContainerHealth.schemas Optional[dict[str,int]] = None
└── __init__.py                       # MODIFY: export probe_connection

docs/troubleshooting/
└── table-not-found.md               # NEW: 4 hard-won scenarios

tests/contract/
└── test_031_diagnostics.py          # NEW: contract tests (TDD)
```

## Implementation Phases

### Phase 1 — Core (P1 FRs: FR-001, FR-002, FR-003, FR-007)
1. `diagnostics.py`: `ConnectionProbe` dataclass + `probe_connection(conn)` + `ConnectionDiagnosticError`
2. `connections/cursor_wrapper.py`: `DiagnosticCursor`
3. Wire into `create_dbapi_connection()`: patch `conn.cursor` to return `DiagnosticCursor(cursor, conn)`
4. Export `probe_connection` from `iris_devtester/__init__.py`

### Phase 2 — Extensions (P2 FRs: FR-004, FR-006)
5. `ContainerHealth.schemas: Optional[dict[str, int]] = None`
6. `docs/troubleshooting/table-not-found.md`

### Phase 3 — Tests + Verify
7. Contract tests (RED → GREEN)
8. Unit regression (386 must stay green)
**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
