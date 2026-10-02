# Implementation Plan: Image Command Hardening

**Branch**: `035-image-command-hardening` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/035-image-command-hardening/spec.md`

## Summary

Harden `idt image load` and `idt image build`: enforced per-phase timeouts, one structured error renderer with fixed exit codes, masked passwords, a mounted (never baked) license key, label-based container collision handling, and a validated `iris-main` with deterministic sources. The 611-line `cli/image_commands.py` becomes the package `iris_devtester/cli/image/` split by concern, with the old module kept as a shim. Decisions are recorded in `.scratch/wayfinder/tickets/T1..T7`; this plan does not reopen them.

## Technical Context

**Language/Version**: Python 3.9+ (package floor), developed on 3.11/3.12
**Primary Dependencies**: click, docker SDK (`docker`), stdlib `subprocess`, `threading`, `struct`, `tarfile`, `os`/`signal`
**Storage**: Files only (temporary build directory)
**Testing**: pytest, `click.testing.CliRunner`, generated fixtures in `tmp_path`
**Target Platform**: macOS and Linux (process-group kill); Windows falls back to killing the Docker CLI process
**Project Type**: Single project (library plus CLI)
**Performance Goals**: Timeout fires within 5 s of the limit (SC-001)
**Constraints**: No new runtime dependencies; `idt container up` output unchanged; no secrets in build context or layers
**Scale/Scope**: One command group, 2 commands, about 7 modules, no existing tests to preserve

## Constitution Check

_GATE: passed before Phase 0; re-checked after Phase 1._

| Principle                    | Status | How                                                                                                             |
| ---------------------------- | ------ | --------------------------------------------------------------------------------------------------------------- |
| 1. Automatic remediation     | Pass   | Labelled stale containers are removed automatically; destructive cases are gated by `--replace` and labels (T4) |
| 2. Right tool for the job    | Pass   | Docker SDK/CLI only; no IRIS SQL or ObjectScript added                                                          |
| 3. Isolation by default      | Pass   | Each command creates its own named, labelled container                                                          |
| 4. Zero configuration viable | Pass   | Missing key continues with a notice; iris-main works when any IRIS container runs, else one documented command  |
| 5. Fail fast with guidance   | Pass   | `ImageCommandError` three-part message on every failure path                                                    |
| 6. Enterprise ready          | Pass   | License key mounted for enterprise images                                                                       |
| 7. Medical-grade reliability | Pass   | 95% coverage on the package; tests first                                                                        |
| 8. Official IRIS Python API  | N/A    | No IRIS API use                                                                                                 |
| 9. SQLite-level ergonomics   | Pass   | Sensible defaults for every timeout and source                                                                  |
| 10. Document blind alleys    | Pass   | `docs/learnings/` note (FR-037)                                                                                 |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/035-image-command-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-contract.md
│   └── error-format.md
├── checklists/requirements.md
└── tasks.md             # produced by /speckit.tasks
```

### Source Code (repository root)

```text
iris_devtester/
├── cli/
│   ├── image_commands.py        # thin shim: re-exports image_group (import path unchanged)
│   └── image/
│       ├── __init__.py          # image_group, registers load and build
│       ├── errors.py            # ImageCommandError, render_error, exit-code constants
│       ├── options.py           # StartOptions (frozen), timeout constants, label keys
│       ├── license.py           # discover_license_key, LicenseNotice
│       ├── collision.py         # resolve_name_collision (labels, --replace)
│       ├── iris_main.py         # resolve_iris_main, check_elf_arch, extract_from_image
│       ├── runner.py            # run_build (Popen + Timer killpg), run_docker_load, run_docker_run
│       ├── load.py              # `idt image load`
│       ├── build.py             # `idt image build`
│       └── common.py            # run_image_command wrapper, --no-start helper, create_and_start_container
└── utils/progress.py            # print_connection_info gains show_password=True

tests/
├── unit/image/                  # conftest fixtures + one test module per package module
├── integration/test_image_load_docker.py   # gated on Docker
docs/learnings/image-build-installer-kit.md
CHANGELOG.md
```

**Structure Decision**: Single project. The `runner.py` module is the single subprocess seam that tests patch (T7); the Docker SDK is the second seam. `common.py` holds what both commands share so neither command file exceeds one screen of logic.

## Phase 0 and Phase 1 artifacts

- [research.md](research.md): decisions carried from the tickets plus the few implementation facts settled during planning.
- [data-model.md](data-model.md): error, options, resolution and collision models.
- [contracts/cli-contract.md](contracts/cli-contract.md): options, environment variables, exit codes.
- [contracts/error-format.md](contracts/error-format.md): rendered error shape and required messages.
- [quickstart.md](quickstart.md): manual verification walk-through.

## Ordering notes for /speckit.tasks

1. Formatting commit first (black on the existing module), then package scaffolding with the shim and characterisation tests (strict xfail).
2. Shared pieces before commands: errors, options, runner, common.
3. Story order: timeouts (US1), errors and password (US2), license (US3), collision (US4), iris-main (US5); docs and CHANGELOG last.
4. Every task group lists its tests before the implementation it covers; each story ends with a passing phase gate.
