# Data Model Updates: Fixes for pgwire-identified bugs

**Feature Branch**: `020-fix-pgwire-issues` | **Date**: 2026-01-02

## Functions & Methods

### `reset_password_if_needed` (in `iris_devtester/connections/retry.py` or `utils/password_reset.py`)

- **Change**: Add `username: str = "_SYSTEM"` parameter.
- **Impact**: Allows callers to specify which user needs remediation.

### `reset_password` (in `iris_devtester/utils/password_reset.py`)

- **Change**: Internal logic switch to `Security.Users.Modify`.
- **Change**: Signature remains the same but functionality is more robust.

### `IRISReadyWaitStrategy.wait_until_ready` (in `iris_devtester/containers/wait_strategies.py`)

- **Change**: Add a new check step using `docker exec`.
- **Logic**:
  1. Port 1972 is open.
  2. `iris session IRIS -U USER "W 1" Halt` returns 1.

### `DATFixtureLoader.load_fixture` (in `iris_devtester/fixtures/loader.py`)

- **Change**: Add `force_refresh: bool = False` parameter.
- **Logic**:
  - If namespace exists AND `force_refresh` is True:
    - Execute `Config.Namespaces.Delete` via `docker exec`.
    - Execute `Config.Databases.Delete` via `docker exec`.
    - Proceed with normal restore flow.
  - If namespace exists AND `force_refresh` is False:
    - Keep current behavior (skip/SUCCESS).
