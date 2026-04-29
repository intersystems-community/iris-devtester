# Implementation Plan: CPF-First Password Strategy

**Branch**: `034-cpf-first-password-strategy` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)

## Summary

Refactor password handling to follow the grongierisc template pattern: CPF merge is the primary strategy (sets `ChangePassword=0` before IRIS starts), `unexpire_all_passwords()` docker exec is the fallback (only on detected password-change error, once per instance).

## Technical Context

**Language/Version**: Python 3.9+
**Files touched**: 4 (`config/presets.py` ✓ already done, `containers/iris_container.py`, `connections/dbapi.py`)
**New files**: 0 (tests only)
**Effort**: Small — ~40 lines production code changes

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| 2. DBAPI First | PASS | Optimistic connect preserves DBAPI-first |
| 4. Zero Configuration | PASS | CPF merge is invisible to callers |
| 5. Fail Fast with Guidance | PASS | Fallback error message names `idt container reset-password` |
| 7. Medical-Grade Reliability | PASS | Fallback tested, double-remediation prevented by flag |

## Architecture Decision

**Two-phase password strategy:**

```
start()
  └─ inject CPFPreset.SECURE_DEFAULTS + optional PasswordHash into temp CPF file
  └─ super().start() → IRIS processes CPF before superserver opens
  └─ _password_handled = True

get_connection()
  └─ attempt iris.connect()
  └─ on ChangePassword error AND NOT _password_handled:
       └─ unexpire_all_passwords()  ← docker exec fallback
       └─ _password_handled = True
       └─ retry iris.connect()
  └─ on ChangePassword error AND _password_handled:
       └─ raise ConnectionError with full diagnostic
```

**CPF merge temp file content for community() with preconfigured password:**
```
[Actions]
ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48
ModifyUser:Name=SuperUser,PasswordHash=<hash>,ChangePassword=0,PasswordNeverExpires=1
ModifyUser:Name=_SYSTEM,ChangePassword=0,PasswordNeverExpires=1
```

**attach() path**: `_password_handled` starts `False`, CPF merge is never injected (no `start()` called). `get_connection()` uses fallback path.

## File Map

```
iris_devtester/
├── config/
│   └── presets.py          # DONE — _SYSTEM added to SECURE_DEFAULTS
├── containers/
│   └── iris_container.py   # MODIFY: start() + get_connection() + __init__
└── connections/
    └── dbapi.py             # MINOR: tighten error message (include container_name hint)

tests/contract/
└── test_034_cpf_password.py  # NEW: contract tests
```

## Implementation Order

1. `iris_container.py` — `__init__` flag, `start()` CPF injection, `get_connection()` refactor
2. `connections/dbapi.py` — tighten error message
3. Contract tests
4. Unit regression

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
