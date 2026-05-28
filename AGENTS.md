# AGENTS.md - iris-devtester

**Owner:** Thomas Dyar (Tom) — Sr. Manager, AI Platform and Ecosystems, InterSystems Corporation  
> NEVER use "Tim" — that is Tim Leavitt, a colleague. Always use "Tom" in conversation.

**Generated**: 2026-03-28
**Commit**: 417ffee
**Branch**: main
**Version**: 1.14.0 (PyPI: `iris-devtester`)
**Python**: 3.9+

> Hierarchical knowledge base. Subdirectory-specific AGENTS.md files exist for: `containers/`, `connections/`, `utils/`, `config/`, `cli/`, `fixtures/`, `testing/`, `tests/`.

---

## OVERVIEW

Battle-tested Python toolkit for InterSystems IRIS database testing. Manages container lifecycles, DBAPI connections with auto-remediation, GOF fixture loading, and port isolation for parallel test runs.

**Stack**: Python 3.9+ | Docker SDK | testcontainers | Click CLI | Pydantic | intersystems-irispython (DBAPI)

## STRUCTURE

```
iris_devtester/              # 179 .py files, ~39k lines
  cli/                       # Click command groups (container, fixture, dev, connection)
  config/                    # IRISConfig, auto-discovery, YAML presets
  connections/               # DBAPI-first connections, retry, auto-discovery
  containers/                # IRISContainer lifecycle, monitoring, CPF, wait strategies
  fixtures/                  # GOF fixture create/load/validate, $SYSTEM.OBJ export
  integrations/              # LangChain vector store bridge (optional)
  ports/                     # Port registry for parallel test isolation
  testing/                   # pytest fixtures, helpers, schema reset
  utils/                     # password reset, callin, health checks, namespace

tests/                       # 100 test files, ~19k lines
  unit/                      # No Docker, fast (<1s each)
  integration/               # Real IRIS containers required
  contract/                  # API contract tests (TDD-first)
  e2e/                       # Full workflow tests

docs/learnings/              # 27 codified lessons (blind alleys, solutions)
specs/                       # Feature specifications (001-027)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Start/stop containers | `containers/iris_container.py` | `.community()`, `.enterprise()`, `.light()` factory methods |
| Get a connection | `connections/connection.py` | `get_connection()` — auto-discovers, auto-remediates |
| Password issues | `utils/password.py` (677 lines) | Largest util; handles ChangePassword flag |
| Enable CallIn | `utils/enable_callin.py` | MUST call before DBAPI connections work |
| Load test data | `fixtures/loader.py` | GOF format, <1s for most fixtures |
| CLI entry point | `cli/__init__.py` | `main()` Click group; aliases: `iris-devtester`, `idt` |
| pytest fixtures | `testing/fixtures.py` + `tests/conftest.py` | `iris_db`, `iris_db_shared`, `iris_container` |
| Config discovery | `config/discovery.py` + `config/auto_discovery.py` | Env vars > YAML > container probe |
| Port conflicts | `ports/registry.py` | File-lock based, cross-process safe |
| Container health | `containers/monitoring.py` (1185 lines) | Largest file; resource-aware monitoring |
| CPF merge | `containers/cpf_manager.py` | Merge custom CPF into container at startup |
| Dev instance | `containers/dev_instance.py` | Persistent `idt-dev-data` Docker volume |

## CODE MAP (high-centrality symbols)

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `IRISContainer` | class | `containers/iris_container.py` | Core container wrapper; 668 lines |
| `get_connection()` | function | `connections/connection.py` | Primary public API for DB access |
| `IRISConfig` | class | `config/models.py` | Config dataclass (host, port, ns, creds) |
| `FixtureLoader` | class | `fixtures/loader.py` | GOF fixture import |
| `FixtureCreator` | class | `fixtures/creator.py` | GOF fixture export |
| `enable_callin_service()` | function | `utils/enable_callin.py` | Required before DBAPI |
| `reset_password_if_needed()` | function | `utils/password.py` | Auto-remediation |
| `main()` | Click group | `cli/__init__.py` | CLI entry: container, fixture, dev, test-connection |

## COMMANDS

```bash
# Install
pip install -e ".[all,dev,test]"

# Test (by category)
pytest tests/unit/                    # Fast, no Docker
pytest tests/integration/             # Requires Docker
pytest tests/contract/                # API contracts (TDD)
pytest -k "test_name" -v              # Single test

# Lint
black . && isort . && flake8 iris_devtester/ && mypy iris_devtester/

# CLI
idt container up                      # Start community container
idt container up --edition light      # CI/CD (580MB image)
idt container up --port 11972         # Specific host port
idt container exec iris_db --objectscript "Write \$ZVERSION"  # Run ObjectScript
idt container reset-password iris_db --timeout 10              # With timeout
idt test-connection                   # Verify connectivity
idt test-connection --auto-fix        # Auto-fix password issues
idt fixture load --name my-data       # Load GOF fixture
idt dev up                            # Persistent dev instance
```

## CONVENTIONS

- **Line length**: 100 (black + isort profile=black)
- **Imports**: stdlib > third-party > local (isort enforced)
- **Type hints**: Required on public APIs; Google-style docstrings
- **Return pattern**: `tuple[bool, str]` for simple success/failure; dataclass for rich results
- **Error messages**: MUST include "What went wrong" + "How to fix it" (Constitution #5)
- **Package**: `intersystems-irispython` ONLY. Never `intersystems-iris` (deprecated, causes conflicts)
- **Import story (v5.x)**: Package ships as `iris` and `irisnative` top-level modules. `import iris; iris.connect(hostname=..., port=..., namespace=..., username=..., password=...)`. NOT `intersystems_iris.dbapi._DBAPI` (old v3.x path). `dbapi_compat.py` handles detection automatically.

## ANTI-PATTERNS

- **DO NOT** use JDBC unless specifically testing JDBC — DBAPI is 3x faster
- **DO NOT** connect without enabling CallIn service first
- **DO NOT** use `localhost` on macOS Docker — use `127.0.0.1` (IPv6 resolution bug)
- **DO NOT** hardcode ports — use `IRISContainer.attach().get_exposed_port(1972)`
- **DO NOT** modify `.specify/` directory
- **DO NOT** edit `CHANGELOG.md` without version bump
- **DO NOT** commit `iris.key` or any `*.key` files (caused real incident)
- **DO NOT** use `iris = IRISContainer(); iris.start()` — always use context manager `with`
- **DO NOT** bind-mount host directories into IRIS containers on Linux without fixing uid 51773 permissions — `chown 51773:51773` or `setfacl -R -m u:51773:rwX`. macOS not affected. See `docs/learnings/iris-container-volume-permissions.md`

## KNOWN PAIN POINTS (downstream consumers)

### 1. Ryuk kills containers on process exit
Testcontainers Ryuk removes containers when the Python process exits. For persistent containers, use `idt container up` (Docker SDK mode, no Ryuk) + `IRISContainer.attach(name)` to reconnect. See `docs/learnings/testcontainers-ryuk-lifecycle.md`.

### 2. Password change required on fresh community containers
IRIS community edition forces `ChangePassword=1` on first startup. `with_preconfigured_password()` sets the env var but does NOT clear this flag. `IRISContainer.start()` calls `unexpire_all_passwords()` automatically, but if you hit auth errors: `idt container reset-password <name>` or `iris.reset_password()`. See `docs/learnings/password-reset-changeflag-fix.md`.

**CLI auto-fix (Feature 030)**: `idt test-connection --auto-fix` now detects password-change errors and auto-remediates. The cryptic "Unexpected error: 1" is replaced with an actionable message.

### 3. No public `get_password()` on IRISContainer
**RESOLVED (Feature 029)**: `get_password()` and `get_username()` public methods added. No longer need `iris._password`.

### 4. `docker stop` causes data loss — WIJ not flushed (HIGH)
`docker stop` sends SIGKILL after grace period. IRIS's default entrypoint doesn't trap SIGTERM, so the WIJ (write buffer) is not flushed. Tables exist on restart but rows are 0. **Fixed (v1.18.1+)**: `IRISContainer.__exit__()` calls `stop_gracefully()` automatically. For CLI/compose: run `docker exec <container> iris stop IRIS quietly` before `docker stop`. See `docs/learnings/iris-container-graceful-shutdown.md`.

## ENVIRONMENT

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_HOST` | auto-discovered | IRIS hostname |
| `IRIS_PORT` | `1972` | Superserver port |
| `IRIS_NAMESPACE` | `USER` | Default namespace |
| `IRIS_USERNAME` | `_SYSTEM` | Username |
| `IRIS_PASSWORD` | `SYS` | Password |
| `IRIS_LICENSE_KEY` | `~/.iris/iris.key` | Enterprise license path |

## TEST FIXTURES

```python
def test_example(iris_db):           # Function-scoped, fresh container
def test_example(iris_db_shared):    # Module-scoped, shared container
def test_example(iris_container):    # Raw IRISContainer access
```

Markers: `@pytest.mark.unit`, `integration`, `slow`, `contract`, `enterprise`
Coverage: 90% minimum (pyproject.toml enforced), 95%+ target.

## AGENT SKILLS

| Skill | Trigger | Key Files |
|-------|---------|-----------|
| Container | `/container` | `containers/iris_container.py`, `cli/container.py` |
| Connection | `/connection` | `connections/connection.py`, `utils/enable_callin.py` |
| Fixture | `/fixture` | `fixtures/loader.py`, `cli/fixture_commands.py` |
| Troubleshooting | `/troubleshoot` | `docs/TROUBLESHOOTING.md` |

Skill locations: `.claude/commands/*.md` (Claude), `.cursor/rules/*.mdc` (Cursor), `.github/copilot-instructions.md` (Copilot)

## HUMAN APPROVAL REQUIRED

- Publishing to PyPI
- Force pushing to main/master
- Deleting IRIS namespaces
- Modifying security/credentials
- Major version bumps

## LINKS

- [CONSTITUTION.md](CONSTITUTION.md) — 8 core principles
- [CLAUDE.md](CLAUDE.md) — Claude-specific context
- [SKILL.md](SKILL.md) — Agent skill manifest
- [docs/learnings/](docs/learnings/) — 27 codified lessons
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Common issues
- [docs/SQL_VS_OBJECTSCRIPT.md](docs/SQL_VS_OBJECTSCRIPT.md) — Critical: read before IRIS code

