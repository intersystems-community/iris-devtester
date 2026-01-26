# Implementation Plan: Fix pgwire-identified bugs in iris-devtester

**Branch**: `020-fix-pgwire-issues` | **Date**: 2026-01-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-fix-pgwire-issues/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature addresses 4 critical bugs identified during the integration of `iris-devtester` with `iris-pgwire`. The fixes focus on parametrizing password resets, improving security flag reliability using the `Security.Users.Modify` API, enhancing container readiness verification to prevent race conditions, and allowing fixture re-loading into existing namespaces.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: `testcontainers`, `testcontainers-iris`, `docker`, `pydantic`  
**Storage**: N/A (Infrastructure layer)  
**Testing**: `pytest`  
**Target Platform**: Docker (Linux/macOS/Windows)
**Project Type**: single
**Performance Goals**: <10s for password reset, 100% connection acceptance rate post-readiness signal  
**Constraints**: Support IRIS 2024.1+ while maintaining backward compatibility for older versions.  
**Scale/Scope**: 4 targeted fixes in core infrastructure modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Library-First**: Fixes are implemented in the `iris_devtester` library.
- [x] **II. CLI Interface**: Password reset and fixture loading are already exposed via CLI; signatures will be updated.
- [x] **III. Test-First (NON-NEGOTIABLE)**: TDD mandatory for all 4 fixes.
- [x] **IV. Integration Testing**: All fixes require integration tests with real IRIS containers.
- [x] **V. Fail Fast**: Improvement of error messages and readiness checks ensures faster failure detection.

## Project Structure

### Documentation (this feature)

```text
specs/020-fix-pgwire-issues/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
iris_devtester/
├── cli/
│   ├── container.py     # Update reset-password CLI
│   └── fixture_commands.py # Update fixture load CLI
├── connections/
│   └── retry.py         # Update reset_password_if_needed
├── containers/
│   └── wait_strategies.py # Update IRISReadyWaitStrategy
├── fixtures/
│   └── loader.py        # Update DATFixtureLoader
└── utils/
    └── password_reset.py # Implement Security.Users.Modify
```

**Structure Decision**: Single project. Changes are distributed across core modules to address the specific bug locations.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
