# Implementation Plan: Fix Downstream Consumer Pain Points

**Branch**: `029-fix-downstream-pain-points` | **Date**: 2026-03-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/029-fix-downstream-pain-points/spec.md`

## Summary

Fix three pain points reported by downstream consumers (objectscript-coder): (1) add public `get_password()` and `get_username()` accessors to `IRISContainer`, (2) ensure `with_preconfigured_password()` results in DBAPI-ready containers by verifying `unexpire_all_passwords()` runs reliably during `start()`, (3) add Ryuk lifecycle documentation to class and method docstrings.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: docker SDK, testcontainers, intersystems-irispython (DBAPI)
**Storage**: N/A (modifying existing container wrapper)
**Testing**: pytest (unit + contract + integration)
**Target Platform**: macOS/Linux (Docker Desktop)
**Project Type**: single (Python package)
**Performance Goals**: N/A (no perf-critical changes)
**Constraints**: Must not break any existing tests; backward compatible
**Scale/Scope**: ~50 lines of code changes, ~100 lines of test additions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| 1. Automatic Remediation | PASS | Password flag clearing is auto-remediation |
| 2. DBAPI First | PASS | Fix ensures DBAPI works out of the box |
| 3. Isolation by Default | PASS | No isolation changes |
| 4. Zero Configuration | PASS | Fix reduces required manual steps |
| 5. Fail Fast with Guidance | PASS | Docstrings add remediation guidance |
| 6. Enterprise + Community | PASS | Fix applies to both editions |
| 7. Medical-Grade Reliability | PASS | Tests required for all changes |
| 8. Document Blind Alleys | PASS | Docstrings document Ryuk gotcha |

No violations. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/029-fix-downstream-pain-points/
├── spec.md              # Feature specification
├── plan.md              # This file
├── checklists/
│   └── requirements.md  # Quality checklist
└── contracts/
    └── test_accessor_contract.py  # Contract tests for get_password/get_username
```

### Source Code (files to modify)

```text
iris_devtester/
└── containers/
    └── iris_container.py    # Add get_password(), get_username(), update docstrings

tests/
├── contract/
│   └── test_accessor_contract.py  # New: contract tests for public accessors
└── unit/
    └── test_iris_container.py     # Add unit tests for accessors + docstring checks
```

**Structure Decision**: Single project, modifying existing files. One new contract test file.

## Complexity Tracking

No violations to justify. This is a minimal, focused change.
