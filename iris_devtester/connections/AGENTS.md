# connections/ — DBAPI Connection Management

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

DBAPI-first connection layer with auto-discovery, retry logic, and password remediation. Supports DBAPI (fast, preferred) and JDBC (fallback). 8 files, 1374 lines.

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `connection.py` | — | `get_connection()` — primary public API; `IRISConnection` context manager |
| `dbapi.py` | — | Low-level DBAPI wrapper; `is_dbapi_available()`, `create_dbapi_connection()` |
| `jdbc.py` | — | JDBC fallback; `is_jdbc_available()` |
| `retry.py` | — | `retry_with_backoff()`, `create_connection_with_retry()` |
| `auto_discovery.py` | — | `auto_detect_iris_host_and_port()` — finds running IRIS containers |
| `manager.py` | — | Legacy `get_connection_with_info()` (compatibility layer) |
| `models.py` | — | `ConnectionInfo` dataclass |

## PATTERNS

- **Auto-discovery chain**: env vars > YAML config > Docker container probe
- **Auto-remediation**: password change errors trigger `reset_password_if_needed()` automatically
- **DBAPI > JDBC**: Always try DBAPI first; JDBC only as explicit fallback
- **CallIn prerequisite**: DBAPI requires CallIn service enabled — `get_connection()` handles this

## CRITICAL RULES

- **MUST** enable CallIn before DBAPI: `enable_callin_service(container_name)`
- **MUST** use `127.0.0.1` not `localhost` on macOS (IPv6 resolution bug)
- **MUST** use `intersystems-irispython` package, NEVER `intersystems-iris`

## GOTCHA: "Password change required" on fresh containers

DBAPI connections fail on fresh community containers with an auth error because IRIS sets `ChangePassword=1` for all users at first startup. The DBAPI driver cannot handle the interactive password-change handshake.

**Symptoms**: Connection refused, auth error, or silent hang on `iris.connect()`.

**Fix sequence** (automated by `IRISContainer.start()`):
1. `enable_callin_service(container_name)` — enables the CallIn service
2. `unexpire_all_passwords(container_name)` — clears `ChangePassword=0` via `Security.Users.Modify()`

**If you still hit this** (e.g., `idt container up` started the container but password wasn't cleared):
```bash
idt container reset-password <container-name>
```
Or programmatically: `iris.reset_password(username="_SYSTEM", new_password="SYS")`

See: `docs/learnings/password-reset-changeflag-fix.md`, `containers/AGENTS.md` for full context.

## LEGACY COMPATIBILITY

`__init__.py` exports compatibility wrappers: `get_iris_connection()`, `reset_password_if_needed()`, `test_connection()`, `IRISConnectionManager` — all delegate to modern `get_connection()`.
