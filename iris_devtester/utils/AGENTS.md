# utils/ — Infrastructure Utilities

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Core utilities for IRIS operations: password management, CallIn service, health checks, namespace handling. Second-largest subpackage (3572 lines, 11 files).

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `password.py` | 677 | Password reset, ChangePassword flag handling; largest util file |
| `iris_container_adapter.py` | 636 | Adapts various container objects to unified interface |
| `health_checks.py` | 551 | Container and IRIS health verification |
| `enable_callin.py` | — | `enable_callin_service()` — MUST call before DBAPI connections |
| `namespace.py` | — | Namespace creation, switching, cleanup |
| `container_port.py` | — | Port resolution from container |
| `container_status.py` | — | Container state queries |
| `dbapi_compat.py` | — | DBAPI compatibility layer |
| `progress.py` | — | Progress reporting utilities |
| `test_connection.py` | — | Connection verification |

## CRITICAL SEQUENCES

1. **Before any DBAPI connection**: `enable_callin_service(container_name)` — this is non-negotiable
2. **Password remediation**: `password.py` handles the `ChangePassword=1` flag that IRIS sets on fresh containers
3. **Health check order**: port open > superserver ready > SQL query succeeds

## PATTERNS

- **Return pattern**: `tuple[bool, str]` — `(success, message)` for all utility functions
- **Docker exec**: Password reset and CallIn use `docker exec` to run IRIS terminal commands
- **Error messages**: Always include "What went wrong" + "How to fix it" (Constitution #5)
- **Timeout propagation**: `password.py` `reset_password(timeout=N)` now correctly passes `timeout` to the subprocess call (fixed in Feature 030 — was hardcoded to 15s)
