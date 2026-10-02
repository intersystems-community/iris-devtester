# Implementation Plan: Container Base Hardening

**Branch**: `036-container-base-hardening` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/036-container-base-hardening/spec.md`

## Summary

Make `IRISDockerContainer` (and so `IRISContainer`) safe with arbitrary passwords and strict about namespaces and usernames by passing values through the exec environment of a constant command; check the exit status of both creation steps; make the community licence check log Docker failures and let other errors propagate; delete dead code in two steps (safe deletions, then `HAS_TESTCONTAINERS` with its test rewrite); label containers created by `container up` and the adapter's Docker path; record the decisions. Decisions live in `.scratch/wayfinder/tickets/T9`, `T10`, `R2` and the labelling part of `T4`.

## Technical Context

**Language/Version**: Python 3.9+ (package floor), developed on 3.11/3.12
**Primary Dependencies**: testcontainers (base `DockerContainer`), docker SDK, stdlib `re`
**Storage**: N/A
**Testing**: pytest; unit tests in `tests/unit/test_iris_base_container.py`, `test_iris_container_extra.py`, `test_password_preconfig.py`; one integration test
**Target Platform**: macOS and Linux Docker hosts
**Project Type**: Single project (library plus CLI)
**Performance Goals**: None; validation is constant time
**Constraints**: public behaviour of `IRISContainer` otherwise unchanged; coverage gate 90%; no new dependencies
**Scale/Scope**: about 4 source files, about 34 test references to rewrite in step two

## Constitution Check

| Principle                    | Status | How                                                                    |
| ---------------------------- | ------ | ---------------------------------------------------------------------- |
| 1. Automatic remediation     | Pass   | Failures are detected at start-up with a fix, not later as auth errors |
| 2. Right tool for the job    | Pass   | Values travel by environment; no string-built ObjectScript             |
| 3. Isolation by default      | Pass   | Unchanged                                                              |
| 4. Zero configuration viable | Pass   | No new required settings; opt-in user rule preserved                   |
| 5. Fail fast with guidance   | Pass   | Validation in `__init__`, structured `ValueError`s                     |
| 6. Enterprise ready          | Pass   | Unchanged                                                              |
| 7. Medical-grade reliability | Pass   | Tests first; coverage held at every removal step                       |
| 8. Official IRIS Python API  | N/A    | No change                                                              |
| 9. SQLite-level ergonomics   | Pass   | Any password works                                                     |
| 10. Document blind alleys    | Pass   | CHANGELOG and learnings note                                           |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/036-container-base-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── validation-contract.md
│   └── labels-contract.md
├── checklists/requirements.md
└── tasks.md             # produced by /speckit.tasks
```

### Source Code (repository root)

```text
iris_devtester/
├── containers/
│   ├── _base.py                 # validation, env-based exec, exit checks, licence check policy
│   └── iris_container.py        # stub base, availability flag, driver removed; labels
├── utils/iris_container_adapter.py   # labels in _create_with_docker_sdk
└── cli/container_commands.py    # only if `container up` builds containers outside the adapter

tests/
├── unit/test_iris_base_container.py        # extended
├── unit/test_iris_container_extra.py       # patches rewritten (step two)
├── unit/test_password_preconfig.py         # patches rewritten (step two)
├── unit/test_container_labels.py           # new
├── contract/test_preconfig_contract.py     # rewritten or deleted
└── integration/test_base_quoted_password.py  # new, gated on Docker
docs/learnings/container-base-dead-code-and-env-transfer.md
CHANGELOG.md
```

**Structure Decision**: Single project. No new modules: validators live in `_base.py` beside the class that uses them.

## Risks and gates

- **Environment transfer must work on target images.** The first task group proves it with an integration probe before any other `_base.py` change. If it fails, stop and pick another non-interpolating transfer (recorded in research.md as the fallback: stdin script with values read line by line).
- **Test churn in step two.** About 34 references; coverage checked after each batch.

## Ordering notes for /speckit.tasks

1. Probe task first (environment transfer), then US1 (validation and env transfer), US2 (licence policy), US3 step one, US3 step two with contract test, US4 labels, US5 docs.
2. Tests before implementation in every group; each phase ends with a gate.
