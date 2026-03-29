# testing/ — pytest Integration

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

pytest fixtures, test helpers, and schema management for IRIS testing. 5 files, 1166 lines.

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `fixtures.py` | — | `iris_db`, `iris_db_shared`, `iris_container` pytest fixture definitions |
| `schema_reset.py` | 580 | Schema cleanup between tests; namespace-level isolation |
| `helpers.py` | — | Test utility functions |
| `models.py` | — | `PasswordResetResult` and other test-specific models |

## PYTEST FIXTURES

| Fixture | Scope | What It Does |
|---------|-------|--------------|
| `iris_db` | function | Fresh IRIS container per test; yields connection |
| `iris_db_shared` | module | Shared container for module; yields connection |
| `iris_container` | function | Raw `IRISContainer` access |
| `iris_db_both_editions` | function | Parameterized: runs test on community AND enterprise |

## PATTERNS

- **Context manager cleanup**: All fixtures use `with IRISContainer.community() as iris:`
- **Connection augmentation**: `conn.execute_objectscript` and `conn._container` added dynamically
- **Container wait**: After context exit, waits up to 10s for container removal before next test
- **Edition skip**: Enterprise tests skip if `IRIS_LICENSE_KEY` not set

## WHERE FIXTURES ARE DEFINED

- `iris_devtester/testing/fixtures.py` — library-provided fixtures
- `tests/conftest.py` — project test fixtures (more detailed, with cleanup waits)
