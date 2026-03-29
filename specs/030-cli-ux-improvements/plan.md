# Implementation Plan: CLI UX Improvements

**Branch**: `030-cli-ux-improvements` | **Date**: 2026-03-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/030-cli-ux-improvements/spec.md`

## Summary

Five CLI UX fixes targeting the most common pain points: (1) detect password-change errors in `test-connection` instead of "Unexpected error: 1", (2) expose `--timeout` on `reset-password`, (3) add `--port` to `container up`, (4) add `container exec` command, (5) show credentials in `test-connection`. Also deprecate the redundant `container test-connection` subcommand.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: Click (CLI framework), Docker SDK, subprocess
**Storage**: N/A
**Testing**: pytest (unit + contract)
**Target Platform**: macOS/Linux (Docker Desktop)
**Project Type**: Single Python package
**Constraints**: Must not break existing CLI behavior; backward compatible defaults

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| 1. Automatic Remediation | PASS | `--auto-fix` auto-remediates password issues |
| 2. DBAPI First | PASS | test-connection already tries DBAPI first |
| 3. Isolation by Default | PASS | No isolation changes |
| 4. Zero Configuration | PASS | All new flags have sensible defaults |
| 5. Fail Fast with Guidance | PASS | Better error messages, timeout support |
| 6. Enterprise + Community | PASS | All changes edition-agnostic |
| 7. Medical-Grade Reliability | PASS | Tests required for all changes |
| 8. Document Blind Alleys | PASS | Deprecation warning for container test-connection |

No violations.

## Project Structure

### Files to Modify

```text
iris_devtester/
├── cli/
│   ├── connection_commands.py   # US1: password detection, US2: --auto-fix, US5: show creds
│   └── container.py             # US2: --timeout on reset-password
│                                # US3: --port on container up
│                                # US4: new exec command
│                                # US1 (container test-connection deprecation via FR-011)
└── utils/
    └── password.py              # US2: fix hardcoded timeout=15 at line 375

tests/
├── contract/
│   └── test_cli_ux_contract.py  # New: contract tests for all 5 stories
└── unit/
    └── test_connection_commands.py  # Updated: password detection unit tests
```

## Implementation Phases

### Phase 1: P1 Items (password detection + timeout)
- FR-001: Password-change error detection in `connection_commands.py`
- FR-002: `--auto-fix` flag on `test-connection`
- FR-003: `--timeout` on `reset-password` CLI
- FR-004: Fix hardcoded `timeout=15` in `password.py:375`
- FR-009: Show credentials (masked/verbose)
- FR-011: Deprecation warning on `container test-connection`

### Phase 2: P2 Items (--port + exec)
- FR-005: `--port` on `container up`
- FR-006: Mutual exclusion with `--auto-port`
- FR-007: `container exec` command
- FR-008: `--namespace` and `--timeout` on exec

### Phase 3: Verification
- FR-010: Full regression test suite
- Contract tests for all new functionality
