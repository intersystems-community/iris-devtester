# Implementation Plan: The Dev Instance (Warm Start)

**Branch**: `026-dev-instance` | **Date**: 2026-02-08 | **Spec**: [specs/026-dev-instance/spec.md](spec.md)
**Input**: Feature specification from `/specs/026-dev-instance/spec.md`

## Summary

This feature implements a persistent development IRIS instance ("Warm Start") to achieve SQLite-level ergonomics. The toolkit will manage a background container named `idt-dev-instance` using a dedicated Docker volume for persistence. Connections via `get_connection()` will automatically detect and (if necessary) start this instance, ensuring project isolation through folder-specific namespaces within the global engine.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: `docker` (SDK), `testcontainers`, `click`, `packaging`  
**Storage**: Docker Volume (`idt-dev-data`) for physical storage; IRIS Namespaces for project isolation.  
**Testing**: `pytest` (unit and integration)  
**Target Platform**: Docker-enabled environments (macOS, Linux, Windows)
**Project Type**: Python Library with CLI  
**Performance Goals**: < 500ms for warm-start connections; minimized cold-start checks.  
**Constraints**: Zero-manual-config; non-intrusive background management.  
**Scale/Scope**: Local development productivity tool.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Rationale |
|-----------|------------|-----------|
| 1. Automatic Remediation | ✅ Pass | Implicitly starts the engine and ensures CallIn is enabled. |
| 2. DBAPI First | ✅ Pass | All dev instance connections use the stable DBAPI path. |
| 3. Isolation by Default | ✅ Pass | Project isolation via hashed folder-path namespaces. |
| 4. Zero Configuration Viable | ✅ Pass | `get_connection()` finds the dev engine without parameters. |
| 5. Fail Fast with Guidance | ✅ Pass | Informative error messages for Docker/port issues. |
| 6. Enterprise Ready | ✅ Pass | Standard IRIS patterns for DB/Namespace creation. |
| 7. Medical-Grade Reliability | ✅ Pass | 100% test coverage target for new lifecycle logic. |
| 8. Official IRIS Python API | ✅ Pass | Uses `intersystems_iris` connection path. |
| 9. SQLite-Level Ergonomics | ✅ Pass | The core driver for this feature. |
| 10. Document Blind Alleys | ✅ Pass | Architecture decisions (Global Engine / Project Data) recorded. |

## Project Structure

### Documentation (this feature)

```text
specs/026-dev-instance/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
iris_devtester/
├── cli/
│   └── dev_commands.py  # New: idt dev commands
├── containers/
│   └── dev_instance.py  # New: DevInstance manager class
├── config/
│   └── discovery.py     # Updated: detect dev instance
└── connections/
    └── connection.py    # Updated: implicit start logic

tests/
├── integration/
│   └── test_dev_instance.py
└── unit/
    └── test_dev_instance_logic.py
```

**Structure Decision**: Single-project structure. New modules added to `cli/` and `containers/` to handle the specific lifecycle of the persistent dev engine.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(No violations detected)*
