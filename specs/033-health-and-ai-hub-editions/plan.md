# Implementation Plan: health() and ai_hub() Container Editions

**Branch**: `033-health-and-ai-hub-editions` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)

## Summary

Two new factory methods (`IRISContainer.health()` and `IRISContainer.ai_hub()`), a `FHIRReadyWaitStrategy`, a `FHIRContainerHealth` dataclass, a `fhir_health_check()` method, and documented gotchas for all four hard-won findings from the careconnect probe session.

## Technical Context

**Language/Version**: Python 3.9+
**New dependencies**: None — `urllib.request` for HTTP health check (stdlib)
**Key constraint**: AI Hub container requires `docker.iscinternal.com` registry — factory must fail clearly if image pull fails
**Effort**: Medium — ~150 lines production code, ~80 lines tests

## File Map

```
iris_devtester/
├── containers/
│   ├── iris_container.py     # ADD: health(), ai_hub(), fhir_health_check()
│   ├── wait_strategies.py    # ADD: FHIRReadyWaitStrategy
│   ├── models.py             # ADD: FHIRContainerHealth dataclass
│   └── AGENTS.md             # UPDATE: 4 new gotchas

docs/learnings/
└── irishealth-editions.md    # NEW: full discovery notes

tests/contract/
└── test_033_health_editions.py  # NEW: contract tests
```

## Implementation Order

1. `models.py` — `FHIRContainerHealth` dataclass
2. `wait_strategies.py` — `FHIRReadyWaitStrategy`
3. `iris_container.py` — `health()`, `ai_hub()`, `fhir_health_check()`
4. `containers/AGENTS.md` — 4 new gotchas
5. `docs/learnings/irishealth-editions.md`
6. Contract tests

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
