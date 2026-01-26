# Implementation Plan: CPF Merge Support

**Branch**: `022-add-cpf-merge-support` | **Date**: 2026-01-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/022-add-cpf-merge-support/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a new `with_cpf_merge(path_or_content)` capability for `IRISContainer` to enable declarative configuration of InterSystems IRIS instances during startup. This feature will automate the mounting of configuration snippets and the setting of the `ISC_CPF_MERGE_FILE` environment variable, specifically targeting optimizations for service activation (CallIn), security (pre-hashed passwords), and resource management (CI environments).

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: `testcontainers`, `python-dotenv`, `docker`  
**Storage**: N/A  
**Testing**: `pytest` (unit + integration with real containers, supporting both Community and Enterprise via `iris_db_both_editions` fixture)  
**Target Platform**: InterSystems IRIS 2019.4+ on Docker  
**Project Type**: single  
**Performance Goals**: ~2s reduction in "Ready" signal latency for DBAPI connections.  
**Constraints**: Must support both file paths and raw string content; must manage temporary file lifecycles.  
**Scale/Scope**: Core library enhancement to `IRISContainer` and supporting utilities.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Library-First**: The feature is added to the core `iris_devtester` library.
- [x] **II. CLI Interface**: (To be verified if new CLI commands are needed, spec focuses on API).
- [x] **III. Test-First (NON-NEGOTIABLE)**: Integration tests will be written before implementation.
- [x] **IV. Integration Testing**: Essential to verify CPF actually affects the IRIS instance.
- [x] **V. Fail Fast**: (N/A for this architectural change).

## Project Structure

### Documentation (this feature)

```text
specs/022-add-cpf-merge-support/
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
├── containers/
│   ├── iris_container.py    # Add with_cpf_merge method
│   └── cpf_manager.py       # NEW: Logic for managing temporary CPF files
└── config/
    └── presets.py           # NEW: CPFPreset constants (CI_OPTIMIZED, etc.)

tests/
├── integration/
│   └── test_cpf_merge.py    # Integration tests for CPF application
└── unit/
    └── test_cpf_manager.py  # Unit tests for temp file lifecycle
```

**Structure Decision**: Single project (DEFAULT). Logic is encapsulated in a new `cpf_manager.py` to keep `iris_container.py` focused on lifecycle.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
