# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**iris-devtester** (`idt`) is a Python package providing automatic, reliable infrastructure for
InterSystems IRIS development — testcontainers integration, connection management, password
auto-remediation, and GOF fixture management. It was extracted from production code in `~/ws/rag-templates/`.

**Related files**: `CONSTITUTION.md` (8 non-negotiable principles), `skills/` (agent skill manifests),
`specs/<feature>/` (per-feature spec + plan + contracts).

## Commands

```bash
# Install
pip install -e ".[dev,test,all]"

# Run all tests (includes coverage)
pytest

# Unit tests only (no Docker needed)
pytest tests/unit/ -m "not integration and not e2e"

# Single test
pytest tests/unit/test_iris_container.py::test_community_factory -xvs

# Skip slow tests
pytest -m "not slow"

# Format + lint
black . && isort . && flake8 . && mypy iris_devtester/

# CLI
idt --help
iris-devtester --help
```

## Architecture

```text
iris_devtester/
├── containers/         # IRISContainer — central class (extends testcontainers-iris)
│   ├── iris_container.py   # Factory methods: .community(), .enterprise(), .light(),
│   │                       #   .health(), .ai_hub(), .attach(), .dev()
│   ├── models.py       # ContainerHealth, ContainerHealthStatus, HealthCheckLevel,
│   │                   #   ValidationResult
│   ├── validation.py   # validate_container(), ContainerValidator (Feature 014)
│   ├── cpf_manager.py  # CPF merge file management (Feature 034)
│   └── wait_strategies.py  # Container readiness detection
├── connections/        # Connection layer (Constitutional Principle #2: DBAPI-first)
│   ├── manager.py      # get_connection() — auto-selects DBAPI or JDBC
│   ├── dbapi.py        # intersystems-irispython driver
│   └── jdbc.py         # JayDeBeApi fallback
├── config/             # IRISConfig + auto-discovery (env vars → .env → Docker → defaults)
│   ├── models.py       # IRISConfig dataclass
│   └── discovery.py    # Priority chain: explicit > env > .env > Docker > defaults
├── fixtures/           # GOF fixture management (Feature 004)
│   ├── loader.py       # GOFFixtureLoader — loads .gof files into IRIS
│   ├── creator.py      # FixtureCreator — exports namespace to .gof
│   ├── validator.py    # SHA256 checksum validation
│   └── manifest.py     # FixtureManifest dataclass
├── cli/                # Click CLI (entry point: `idt`)
│   ├── fixture_commands.py  # idt fixture create|load|validate|list|info
│   └── container_commands.py
├── integrations/
│   └── langchain.py    # LangChainIRISContainer (extends IRISContainer)
├── diagnostics.py      # ConnectionProbe, probe_connection() — structured diagnostics
└── utils/              # password.py (reset + exponential-backoff verification)
```

**Key flow**: `IRISContainer.community()` → `start()` → CPF merge (if configured) → password
reset via ObjectScript → `enable_callin_service()` → `get_connection()` → DBAPI (or JDBC).

`get_connection()` calls `connections/manager.py` which tries DBAPI first, falls back to JDBC,
raises `ConnectionError` with structured remediation message on failure.

## Core Principles (NON-NEGOTIABLE — `CONSTITUTION.md`)

1. **Automatic Remediation** — no "run this command" errors; fix it in code
2. **DBAPI First, JDBC Fallback** — DBAPI is 3× faster
3. **Isolation by Default** — each test gets its own namespace
4. **Zero Configuration Viable** — `pip install && pytest` must work
5. **Fail Fast with Guidance** — structured multi-line error messages with fix steps
6. **Enterprise Ready, Community Friendly** — support both editions
7. **Medical-Grade Reliability** — 95%+ coverage required
8. **Document the Blind Alleys** — explain why not X in `docs/learnings/`

## Critical ObjectScript Patterns

Property names are **case-sensitive** and position-based (not keyword-based):

| Correct               | Wrong                       | Notes                         |
| --------------------- | --------------------------- | ----------------------------- |
| `PasswordExternal`    | `Password`                  | Triggers PBKDF2 hashing       |
| `ChangePassword`      | `ChangePasswordAtNextLogin` | Password-change-required flag |
| `AccountNeverExpires` | `AccountNeverExpire`        | Note the trailing 's'         |

`Security.Users.ChangePassword()` was **removed in 2004** — use `Exists()` + `user.PasswordExternal`.

`$SYSTEM.Monitor.State()` returns 0 when container is ready (not just running).

CallIn service **must be enabled** before DBAPI connections work.
`enable_callin_service()` does this automatically.
See `docs/learnings/callin-service-requirement.md`.

## Test Layout

- `tests/unit/` — no Docker; run with `-m "not integration and not e2e"`
- `tests/integration/` — require live IRIS container (`@pytest.mark.integration`)
- `tests/contract/` — TDD contract tests (may fail until implementation complete)
- Coverage threshold: 90% enforced (`--cov-fail-under=90`); target 95%+

## Feature Specs

Each feature in `specs/<NNN>-<name>/` contains `spec.md`, `plan.md`, `data-model.md`,
`contracts/`, `quickstart.md`. Check these before implementing in that feature area.
Implemented: 004 (GOF fixtures), 014 (container validation), 015 (macOS password
reset), 033 (health/ai_hub editions), 034 (CPF-first password strategy).

## Source Reference

`~/ws/rag-templates/` contains original production code this was extracted from. Consult
it when the current implementation is unclear — especially `common/iris_connection_manager.py`.

<!-- codebase-memory-mcp: Code Discovery Protocol -->
## Code Discovery Protocol (codebase-memory-mcp)

**ALWAYS use `codebase-memory-mcp` tools FIRST for any code exploration:**

- `search_graph(name_pattern/label/qn_pattern)` — find functions, classes, routes
- `trace_path(function_name, mode=calls|data_flow|cross_service)` — call chains
- `get_code_snippet(qualified_name)` — exact symbol source with precise line ranges
- `query_graph(query)` — complex Cypher patterns across the codebase graph
- `get_architecture(aspects)` — project structure overview
- `search_code(pattern)` — graph-augmented text search

Use `Grep`/`Glob`/`Read` freely for text, configs, and non-code files, and always
`Read` a file before editing it. If the project is not indexed yet, run
`index_repository` first.
