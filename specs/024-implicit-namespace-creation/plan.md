# Implementation Plan: Implicit Namespace Creation

Implement "SQLite-level ergonomics" for InterSystems IRIS namespaces. When `get_connection(namespace='NEW')` is called, the toolkit should automatically create the namespace if it doesn't exist, provided it's running locally or the user has opted in.

## Phase 1: Configuration & Models
- [ ] **defaults.py**: Add `DEFAULT_AUTO_CREATE = None`.
- [ ] **models.py**: Add `auto_create: Optional[bool] = None` to `IRISConfig`.
- [ ] **discovery.py**: Handle `IRIS_AUTO_CREATE` env var and `.env` variable.
- [ ] **Hybrid Smart Default**: In `IRISConfig.__post_init__` or `get_connection`, if `auto_create` is `None`:
    - `True` if `host` in `['localhost', '127.0.0.1']`.
    - `False` otherwise.

## Phase 2: Namespace Management Utility
- [ ] **Create `iris_devtester/utils/namespace.py`**:
    - `check_namespace_exists(container_name: str, namespace: str) -> bool`: Uses `docker exec` + ObjectScript `##class(Config.Namespaces).Exists(ns)`.
    - `create_namespace(container_name: str, namespace: str) -> bool`: Uses `docker exec` + ObjectScript to:
        1. Create database directory.
        2. Create database file (`SYS.Database`).
        3. Create database configuration (`Config.Databases`).
        4. Create namespace mapping (`Config.Namespaces`).
        5. Enable `%Service_CallIn` (reusing `enable_callin_service`).
    - `ensure_namespace_exists(config: IRISConfig)`: Orchestrates the check and creation.

## Phase 3: Connection Logic Enhancement
- [ ] **`iris_devtester/connections/connection.py`**:
    - Modify `get_connection` to call `ensure_namespace_exists(config)` if `auto_create` evaluates to `True`.
    - Add logging for the creation process.
    - Handle potential errors (e.g., container not found, permission denied) with clear remediation steps.

## Phase 4: Verification & Testing
- [ ] **Unit Tests**:
    - `tests/unit/test_namespace_utils.py`: Test `ensure_namespace_exists` logic with mocked subprocess.
    - `tests/unit/test_config_auto_create.py`: Test smart default logic.
- [ ] **Integration Tests**:
    - `tests/integration/test_implicit_namespace.py`:
        - Test 1: Successful auto-creation of a new namespace on localhost.
        - Test 2: Existing namespace works normally.
        - Test 3: Remote host fails without explicit `auto_create=True`.
        - Test 4: Remote host succeeds with explicit `auto_create=True` (if a test remote is available, or mock it).
