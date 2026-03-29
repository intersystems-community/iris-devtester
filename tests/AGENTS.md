# tests/ — Test Suite

> Parent: [../AGENTS.md](../AGENTS.md)

## OVERVIEW

100 test files, ~19k lines across 4 categories. TDD-first: contract tests define API before implementation.

## STRUCTURE

| Directory | Files | Lines | Requires Docker | Purpose |
|-----------|-------|-------|-----------------|---------|
| `unit/` | 25 | 6216 | No | Fast tests (<1s each); mocked dependencies |
| `integration/` | 39 | 7046 | Yes | Real IRIS containers; password, monitoring, CPF |
| `contract/` | 33 | 6012 | No | API contract tests (TDD); define public interfaces |
| `e2e/` | 3 | 159 | Yes | Full workflow tests |

## KEY FILES

| File | Role |
|------|------|
| `conftest.py` | Root fixtures: `iris_db`, `iris_db_shared`, `iris_container`, `iris_db_both_editions`; marker registration |
| `integration/conftest.py` | Integration-specific fixtures |
| `contract/cli/` | CLI command contract tests (7 files) |
| `integration/ports/` | Port registry integration tests (6 files) |

## MARKERS

```python
@pytest.mark.unit           # No external dependencies
@pytest.mark.integration    # Requires Docker + IRIS
@pytest.mark.slow           # >5 seconds
@pytest.mark.contract       # API contract (TDD-first)
@pytest.mark.enterprise     # Needs IRIS_LICENSE_KEY
@pytest.mark.dat_fixture    # Uses DAT fixture plugin
```

## RUNNING TESTS

```bash
pytest tests/unit/                    # Fast, no Docker (seconds)
pytest tests/contract/                # API contracts, no Docker
pytest tests/integration/             # Needs Docker (minutes)
pytest tests/e2e/                     # Full workflows
pytest -k "test_password" -v          # By keyword
pytest -m "not slow" tests/           # Skip slow
```

## COVERAGE

- **Minimum**: 90% (enforced via `--cov-fail-under=90` in pyproject.toml)
- **Target**: 95%+
- **Omitted from coverage**: `cli/`, `testing/` (per pyproject.toml `[tool.coverage.run]`)

## PATTERNS

- **Contract-first TDD**: Write contract test defining API → implement → verify
- **Integration cleanup**: Tests wait up to 10s for container removal between tests
- **Edition matrix**: `iris_db_both_editions` parametrizes community + enterprise
- **Subdirectory grouping**: `contract/cli/` and `integration/ports/` for focused test suites
