# Changelog

All notable changes to iris-devtester will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.17.0] - 2026-04-25 - Container Health Check and Full Diagnostic API

### Added

- **`IRISContainer.health_check() -> ContainerHealth`**: Probes schema visibility from the container. Returns `ContainerHealth` with `.schemas`, `.tables_visible`, and `.report()`. Eliminates the "works in pytest, fails manually" class of debugging session by making precondition state observable.
- **`ContainerHealth.tables_visible`**: Property returning `True` if at least one schema with tables is visible.
- **`ContainerHealth.report()`**: Human-readable summary of container name, status, schema names, table counts. Includes warning line when no schemas are visible.
- **`ContainerHealth.to_dict()` includes `schemas`**: Serialized schema visibility now included in JSON output.
- **Top-level exports**: `ContainerHealth`, `ConnectionDiagnosticError`, `ConnectionProbe` now importable directly from `iris_devtester`.
- **13 new contract tests**: `TestContainerHealthExtensions`, `TestTopLevelImports`, `TestIRISContainerHealthCheck` — covers empty schema warning, `tables_visible` flag, top-level imports, `probe_connection` round-trip.

### Context

Completes spec 031 (`031-connection-diagnostics`). The full backstory: a 30-minute debugging session traced to "manual `iris.connect()` probe sees empty namespace before `initialize_schema()` runs, pytest fixture connection sees the seeded schema." Zero signal in the error — just `SQLCODE -30`. `ConnectionDiagnosticError` (1.16.0) wraps the error with schema state. `health_check()` (1.17.0) lets you proactively check before queries run.

The pattern this closes: **test infrastructure that creates state should emit observable signals**.

## [1.16.0] - 2026-04-25 - Connection Diagnostics

### Added

- **`probe_connection(conn) -> ConnectionProbe`**: Inspects a live connection in <200ms. Returns namespace, IRIS version, all visible schemas with table counts, and probe latency. Importable directly from `iris_devtester`.
- **`ConnectionDiagnosticError`**: Automatically wraps SQLCODE -30 (Table or view not found) and SQLCODE -23 (CTE label not applicable) with schema visibility context and a suggested fix. Replaces the raw opaque `ProgrammingError` for these two codes — no call-site changes needed.
- **`DiagnosticCursor`**: Transparent cursor proxy injected by `create_dbapi_connection()`. All cursor methods delegate to the underlying DBAPI cursor; only `-30` and `-23` are intercepted.
- **`ContainerHealth.schemas`**: New `Optional[dict[str, int]]` field on `ContainerHealth`. `None` means schema probe was not run; dict maps schema name → table count.
- **`docs/troubleshooting/table-not-found.md`**: Four hard-won scenarios documented: (1) schema not seeded before probing, (2) `_SYSTEM` password expired, (3) schema not in SQL search path, (4) probing outside pytest before fixtures run.
- **14 contract tests**: Full coverage of `ConnectionProbe`, `ConnectionDiagnosticError`, `DiagnosticCursor`, public export, and `ContainerHealth.schemas`.

### Context

Closes [#14](https://github.com/intersystems-community/iris-devtester/issues/14). A 30-minute debugging session traced SQLCODE -30 to "manual `iris.connect()` probe sees empty namespace before `initialize_schema()` runs." Zero signal in the raw error. `ConnectionDiagnosticError` surfaces schema state at failure time; `probe_connection()` lets you inspect preconditions before running queries.

## [1.15.1] - 2026-04-25 - Docker-in-Docker Port Mapping Fix

### Fixed

- **`get_mapped_port()` raises `ConnectionError` in DinD (BUG-IDT-1)**: When iris-devtester runs inside a container (CI runners, GitHub Actions with mounted Docker socket), testcontainers sets `ConnectionMode.gateway_ip`. `DockerClient.port()` then queries the inner Docker daemon for host-side NAT mappings that don't exist there — returning `None` → `ConnectionError`. Fixed by catching `ConnectionError` in `get_mapped_port()` and falling back to the internal port, which is directly reachable via the container's bridge/gateway IP in DinD. Port 1972 was unaffected (cached); port 52773 and any other non-default port triggered the crash.
- **Narrow `get_config()` exception clause**: `except Exception` narrowed to `except ConnectionError` so real failures (container not started, etc.) still propagate instead of being silently swallowed.
- **Web port overflow**: `idt container up --port 61972` previously calculated web portal port as `52773 + (61972 - 1972) = 112773`, exceeding the 16-bit port limit. Now caps at 65535; ports that would overflow disable the web portal mapping with a clear message.

### Added

- **`_port_cache: dict[int, int]`**: All non-1972 port lookups cached per-container instance, eliminating repeated `DockerClient.port()` calls.
- **`docs/learnings/iris-container-dind-port-mapping.md`**: Full root-cause analysis, diagnosis script, and env-var override reference (`TC_HOST`, `TESTCONTAINERS_CONNECTION_MODE`).
- **8 contract tests**: Full coverage of DinD fallback, port cache, `get_config()` resilience.

## [1.15.0] - 2026-04-25 - CLI UX Improvements + Public Accessors

### Added

- **`IRISContainer.get_password()` / `get_username()`**: Public accessors replacing `iris._password` / `iris._username` private attribute access. Downstream consumers no longer need to reach into private state.
- **`idt test-connection --auto-fix`**: Detects the cryptic "Unexpected error: 1" (IRIS password-change-required error) and auto-remediates by calling `reset_password()` then retrying the connection.
- **`idt test-connection` shows credentials**: Displays masked password by default (`S***`); full password in verbose mode (`-v`).
- **`idt container reset-password --timeout`**: Exposes the existing `timeout` parameter to the CLI (default 30s). Prevents indefinite hangs when IRIS is unresponsive.
- **`idt container up --port`**: Exact host-port mapping for the IRIS SuperServer. Mutually exclusive with `--auto-port`; raises `UsageError` if both provided.
- **`idt container exec`**: Run ObjectScript or shell commands inside a container from the CLI. Options: `--objectscript`, `--namespace` (default `USER`), `--timeout` (default 30s).
- **Hierarchical AGENTS.md knowledge base**: Root + 8 subdirectory AGENTS.md files covering `containers/`, `connections/`, `utils/`, `config/`, `cli/`, `fixtures/`, `testing/`, `tests/`.

### Fixed

- **`intersystems-irispython` v5.x import story**: `connection_commands.py` was importing the legacy `intersystems_iris.dbapi._DBAPI` path (v3.x). Updated to `import iris` and `iris.connect(hostname=, port=, ...)` keyword-argument API.
- **`test_connection_fallback` missing mock**: `test_falls_back_to_jdbc_on_dbapi_failure` was missing `@patch("iris_devtester.connections.jdbc.is_jdbc_available", return_value=True)`, causing the test to raise `ConnectionError` instead of exercising the JDBC fallback.
- **`test_skill_workflow` non-existent user**: `IRISContainer.community(username="skill_user")` referenced a user that doesn't exist in fresh community containers.

### Deprecated

- **`idt container test-connection`**: Deprecated in favour of `idt test-connection --container <name>`. Prints deprecation warning; will be removed in a future major version.



### Fixed

- **Non-Deterministic Auto-Detection**: Fixed `auto_detect_iris_host_and_port()` returning a random container on machines running multiple IRIS containers. It previously picked whichever container appeared first in `docker ps` output.

### Added

- **`container_name` Parameter**: Added optional `container_name` parameter to the entire auto-detection chain, allowing callers to pin detection to a specific Docker container:
  - `get_connection(container_name="my-iris")` - top-level API
  - `IRISConnection(container_name="my-iris")` - context manager
  - `discover_config(container_name="my-iris")` - config discovery
  - `auto_detect_iris_host_and_port(container_name="my-iris")` - host/port detection
  - `auto_detect_iris_port(container_name="my-iris")` - port-only detection
  - `discover_docker_iris(container_name="my-iris")` - Docker-specific discovery
- **Backward Compatible**: All new parameters default to `None`, preserving existing behavior for callers that don't need pinning.
- **10 New Unit Tests**: Comprehensive coverage for multi-container scenarios including pinning, fallback, backward compatibility, and edge cases.

## [1.13.0] - 2026-02-27 - Fix Namespace Lookup for Remote IRIS

### Fixed

- **Namespace Auto-Creation No Longer Requires Docker**: Fixed a bug where `ensure_namespace_exists()` attempted Docker container lookup (hardcoded `iris_db`) even when an explicit `IRISConfig` with host/port was provided. This caused failures for remote/non-Docker IRIS connections.
- **Removed Hardcoded `iris_db` Fallback**: Eliminated the implicit Docker container name assumption from both namespace utilities and the connection password-reset path.

### Added

- **`iris.connect()` Strategy for Namespace Operations**: When no `container_name` is present in config, namespace check/create now uses `iris.connect()` to the `%SYS` namespace directly — no Docker dependency required. This enables namespace auto-creation for remote IRIS instances.
- **`check_namespace_via_iris_connect()`**: New function that verifies namespace existence by connecting to `%SYS` and calling `Config.Namespaces:Exists()`.
- **`create_namespace_via_iris_connect()`**: New function that creates namespaces via `%SYS` using `Config.Namespaces:Create()`.
- **Graceful Degradation**: If `%SYS` access is denied or the `iris` package is unavailable, namespace operations fail gracefully and the connection proceeds anyway.
- **19 New Unit Tests**: Comprehensive coverage for strategy selection logic, `iris.connect()` functions, and edge cases.
- **Blind Alley Documentation**: `docs/learnings/namespace-sql-vs-iris-connect.md` documents why SQL/DBAPI was rejected in favor of `iris.connect()` for namespace operations.

## [1.12.7] - 2026-02-15 - RAG Cleanup Helpers

### Added

- **Deterministic Schema Cleanup**: Added `SchemaResetter.truncate_schema()` for safe, ordered table truncation.
  - Automatically discovers all tables in a schema at runtime.
  - Implements dynamic Foreign Key dependency discovery via `INFORMATION_SCHEMA` to determine safe deletion order (leaf-to-root).
  - Provides configurable safety guards against system schema modification.
- **RAG-Specific Helper**: Added `SchemaResetter.reset_rag_schema()` as an opinionated utility for vector/RAG projects.
  - Pre-configured with optimal deletion order for standard RAG entities.
  - Supports `use_truncate` and `strict` modes for tailored cleanup.

## [1.12.6] - 2026-02-15 - Ultimate Port Reliability Fix

### Fixed

- **Idempotency Remediation**: Fixed "Idempotency Blindness" where `assign_port` would blindly return a cached port assignment even if that port was subsequently occupied by another process. Now performs live verification for every assignment request.
- **Definitive Port Probing**: (Refined from 1.12.5) Replaced weak `connect_ex` probes with definitive `socket.bind()` attempts on `0.0.0.0` and `::` to detect ports that are bound but not actively listening.

### Changed

- **Default Port Range Expansion**: Increased the default auto-assignment pool from `1972-1981` (10 ports) to `1972-2000` (29 ports). This provides significantly more headroom for concurrent projects and reduces collision frequency in congested dev environments.
- **E2E Robustness**: Rewrote `tests/e2e/test_port_registry_e2e.py` to be fully isolated and cover complex remediation scenarios.

## [1.12.5] - 2026-02-15 - Definitive Port Verification

### Fixed

- **Robust Port Detection**: Replaced connection-based port probing with a definitive `socket.bind()` check. This correctly identifies ports that are bound to `0.0.0.0` but not actively listening (a common "silent failure" state for Docker on macOS).
- **CLI Range Support**: Added `--port-range` option to `idt container up` and `idt container start` to allow custom port pools for auto-assignment.
- **Dual-Stack Verification**: Port availability now checks both IPv4 (`0.0.0.0`) and IPv6 (`::`) interfaces where supported.

### Changed

- **E2E Hardening**: Enhanced `tests/e2e/test_port_registry_e2e.py` to simulate the "bound but not listening" state, ensuring long-term reliability of the port fallback mechanism.

## [1.12.4] - 2026-02-15 - Port Management Reliability

### Fixed

- **Host Port Availability**: Enhanced `PortRegistry` to perform live TCP socket checks on the host. This prevents `idt` from assigning ports that are occupied by non-Docker processes.
- **Auto-Port Fallback**: Improved CLI logic to correctly trigger auto-assignment when the default port (1972) is taken, even if it's the configured default.
- **Web Port Scaling**: Fixed logic for proportional adjustment of the WebServer port when the SuperServer port is shifted.

### Added

- **E2E Coverage**: Added full end-to-end coverage for port conflict scenarios in `tests/e2e/test_port_registry_e2e.py`.

## [1.12.3] - 2026-02-15 - Documentation Sync

### Changed

- **Documentation Parity**: Synchronized PyPI source distribution with the latest Troubleshooting Guide and feature documentation.
- **Manifest Enhancement**: Explicitly included `CHANGELOG.md` in the PyPI source distribution (`sdist`).

## [1.12.2] - 2026-02-15 - Smart Port Fallback

### Added

- **Smart Port Fallback**: Added `--auto-port` flag to `idt container up` and `idt container start` commands.
  - Automatically finds and assigns an available port if the default (1972) is taken.
  - Utilizes the `PortRegistry` to maintain stable assignments across project sessions.
  - Automatically adjusts the WebServer port proportionally when the SuperServer port is shifted.

### Fixed

- **Reset Password Support**: Added `IRISContainer.reset_password()` method to support manual password remediation in integration scripts.

## [1.12.1] - 2026-02-15 - Protocol & Discovery Fixes

### Fixed

- **Access Denied (Invalid Message)**: Fixed a critical bug in `get_config()` where discovering `0.0.0.0` as the host caused the IRIS Superserver to reject the connection protocol. Now sanitizes `0.0.0.0` and `::` to `localhost` for reliable client-side connectivity.
- **Attach Validation**: Improved `IRISContainer.attach()` with explicit validation for container names and better error messages when containers are missing or not running.
- **Type Safety**: Resolved LSP type mismatch for `container_name` in `attach()` and `dev()` methods.

## [1.12.0] - 2026-02-10 - The Dev Instance (Warm Start)

### Added

- **The Dev Instance (Warm Start)**: Achieved the project's "North Star" of SQLite-level ergonomics.
  - **Instant Connection**: `get_connection()` now connects in < 100ms by utilizing a persistent background engine.
  - **Managed Lifecycle**: New `idt dev` command group (`up`, `down`, `status`, `logs`) to manage the background engine.
  - **Project Isolation**: Automatic folder-based hashing ensures each project directory gets its own isolated IRIS namespace and database.
  - **Durable Persistence**: Integrated "Durable %SYS" support ensures data survives container restarts and engine upgrades.
  - **Automatic Provisioning**: Calling `get_connection()` will implicitly start the dev engine if it's not running.
  - **Optimized Readiness**: Ultra-fast TCP port probing for immediate connectivity detection.

- **Improved Port Management**: Enhanced auto-discovery logic to prioritize the managed dev instance.

### Fixed

- **Volume Permissions**: Automated `chown` logic for persistent volumes to prevent UID 51773 (irisowner) conflicts on macOS.
- **Readiness Reliability**: Improved `wait_until_ready` logic with more robust ObjectScript-based initialization checks.

## [1.11.1] - 2026-02-08 - Core Container Fixes

### Fixed

- **Superserver Port Mapping**: Fixed critical bug where non-standard superserver ports (e.g., 31972) were incorrectly mapped host-to-host instead of host-to-container (1972). This fixes connection resets on custom ports.
- **Container Name Persistence**: Improved handling of `container_name` in CLI and adapter to ensure user-specified names are respected.

## [1.11.0] - 2026-02-08 - Implicit Namespace Creation (SQLite-Level Ergonomics)

### Added

- **Implicit Namespace Creation**: Achieved "SQLite-level ergonomics" where `get_connection(namespace="NEW")` automatically creates the namespace if it doesn't exist.
  - Automatically creates database directory and `.dat` file.
  - Configures namespace mappings (Globals/Routines) to the new database.
  - Ensures `%Service_CallIn` is enabled for the new namespace.
  - **Hybrid Smart Default**: Enabled by default for `localhost` (zero-friction dev), explicit opt-in required for remote hosts (production safety).
  - Supported via `IRISConfig.auto_create` and `IRIS_AUTO_CREATE` environment variable.

### Fixed

- Improved `get_connection` reliability when connecting to non-existent namespaces.

## [1.10.4] - 2026-02-08 - Critical DBAPI Segfault Fix

### Fixed

- **Critical Segfault**: Resolved `SIGSEGV` crash when using `FETCH FIRST N ROWS ONLY` SQL syntax.
  - Modified `dbapi_compat.py` to prefer the stable `intersystems_iris` connection path over the buggy `iris` (`_elsdk_`) path.
  - Both modules are part of `intersystems-irispython`, but `intersystems_iris` provides the stable `_IRISNative` driver.
  - This fix restores stability for SQL pagination and vector-graph operations.

## [1.10.3] - 2026-02-06 - Docker Exec Ownership Fix

### Fixed

- **Docker Exec Ownership**: Added `-u irisowner` to all `docker exec` calls that interact with IRIS processes.
  - Fixes "Invalid ownership for ./irisdb" errors in containers where root is the default exec user.
  - Affects password reset, service enablement, connection testing, and fixture operations.
  - Standardizes UID 51773 (irisowner) for all IRIS-specific container interactions.

## [1.10.2] - 2026-02-06 - Fixture System & Enterprise Test Fixes

### Fixed

- **Fixture Integration Tests**: All 9 fixture tests now pass
  - Fixed `test_create_validate_load_verify` to properly connect to target namespace
  - Fixed 4 tests that failed due to empty tables validation by adding test data creation

- **Enterprise Edition Tests**: All 5 previously-skipped enterprise tests now run and pass
  - Fixed `conftest.py`: Was reading license key file contents instead of passing file path
  - Fixed `test_cpf_merge.py`: Same license key path bug
  - Added ARM64-compatible enterprise image selection for Apple Silicon

- **Test Infrastructure**:
  - Fixed flaky `test_wait_function_with_timeout` timing assertion (4.0s → 5.0s tolerance)
  - All 342 unit tests pass
  - All 11 enterprise+community edition tests pass (0 skipped)

### Changed

- Enterprise tests now use `containers.intersystems.com/intersystems/iris:2025.1` on ARM64

## [1.10.1] - 2026-02-05 - CLI Documentation & Custom Images

### Added

- **`--image` option for `container up`**: Use any Docker image, overriding edition defaults
  - Example: `iris-devtester container up --image myregistry/iris:2024.1`
  - Example: `iris-devtester container up --image intersystemsdc/iris-community:2024.1-zpm`
  - Useful for custom registries, specific versions, or pre-configured images

### Changed

- **CLI Help Text**: Improved `--help` output for better AI agent and user discoverability
  - Main help now explains what the tool does, container editions, quick start, and common workflows
  - Added "FOR AI AGENTS" section with exit codes and JSON output guidance
  - Container group help now includes edition comparison and quick start commands
  - All help text now properly formatted with `\b` markers (no more broken line wraps)
  - Added note about using docker-compose for multi-container setups

### Documentation

- CLI is now self-documenting enough for AI agents to use without external docs
- All commands support `--help` for detailed options
- `container list --format json` provides machine-readable output
- Added "When to Use docker-compose Instead" section to GETTING_STARTED.md
  - Covers sharding, mirroring, ECP, and multi-service stacks
  - Explains iris-devtester is for single-container management only

## [1.10.0] - 2026-01-31 - Feature 024: Canonical Container Editions

### Added

- **Three Canonical Container Editions**:
  - **Community**: Full IRIS Community Edition (~3.5GB) - `IRISContainer.community()`
  - **Enterprise**: Licensed IRIS - `IRISContainer.enterprise(license_key=...)`
  - **Light**: Minimal for CI/CD (~580MB) - `IRISContainer.light()` - NEW!

- **Light Edition** (`caretdev/iris-community-light`):
  - 85% smaller than full community (580MB vs 3.5GB)
  - Removes: Interoperability, Management Portal, DeepSee/BI, CSP/REST
  - Keeps: SQL engine, DBAPI, JDBC, ODBC, SQLAlchemy-IRIS
  - Multi-arch: ARM64 and x86 supported
  - Ideal for CI/CD pipelines where startup time matters
  - Maintainer: CaretDev (Dmitry Maslennikov)

- **CLI `--edition` option**: `iris-devtester container up --edition light|community|enterprise`
- **CLI `container list` command**: Shows all IRIS containers with status, edition, ports, age
- **Standardized container naming**: All CLI commands accept optional `CONTAINER_NAME` with default `iris_db`

### Changed

- `IRISContainer.community()` now explicitly documents size (~3.5GB)
- `IRISContainer.enterprise()` now includes better license key handling
- Container config now supports `edition` field: `"community"`, `"enterprise"`, `"light"`
- README updated with Container Editions section

### Technical Details

- Light edition image: `caretdev/iris-community-light:latest-em`
- Default tag for light: `latest-em` (production-ready)
- All editions verified for DBAPI connectivity

## [1.9.3] - 2026-01-30 - CLI Container Naming

### Added

- **`--name` option for `container up`**: Specify custom container name
- **Default name warning**: Warns when using default `iris_db` with existing container

### Fixed

- **Pydantic deprecation**: Migrated from `class Config:` to `model_config = ConfigDict(...)`
- **Python 3.9 compatibility**: Fixed `str | Path` → `Union[str, Path]` type hints
- **mypy type errors**: Resolved various type annotation issues

## [1.9.2] - 2026-01-29 - IRIS Session Instance Name Fix

### Fixed

- **CRITICAL**: Fixed IRIS session instance name from `iris` to `IRIS` (uppercase)
  - Affected files: `password.py`, `health_checks.py`
  - Error symptom: "Access Denied" when DBAPI connections failed due to unexpired passwords
  - Root cause: `iris session iris` → `iris session IRIS`
  - All password reset and CallIn enable commands now work correctly

## [1.8.1] - 2026-01-17 - Bug Fixes & API Contract Synchronization

### Fixed

- **CLI `fixture create` Container Support**: Added missing `--container` parameter to specify source IRIS instance.
- **API Contract Synchronization**: Fixed method signatures and return types across `FixtureCreator`, `DATFixtureLoader`, and `IRISContainer` to align with public contract tests.
- **Contract Test Compatibility**: Implemented a robust compatibility layer in `iris_devtester.testing` and `iris_devtester.connections` to support legacy assistant expectations.
- **Test Performance & Stability**: 
  - Optimized `IRISContainer` startup logic to prevent hangs in restricted environments.
  - Improved `wait_for_iris_ready` timing reliability.
  - Added `clean_port_registry` fixture for integration test isolation.

## [1.8.0] - 2026-01-05 - Feature 022: CPF Merge Support 

### Added 

- **Declarative Configuration (`with_cpf_merge`)**: New method for `IRISContainer` to apply CPF snippets during container boot. 
- **Optimization Presets**: Added `CPFPreset.CI_OPTIMIZED` and `CPFPreset.SECURE_DEFAULTS` for instant setup. 
- **2025 Agent Skills Standard**: Standardized on root-level `SKILL.md` and consolidated assistant triggers. 
- **Consolidated CLI & UI**: Unified agent commands into `/idt` (Claude) and `@idt` (Cursor) for zero clutter. 

## [1.5.2] - 2025-12-24 - Performance & Reliability

### Fixed

- **Password Reset Performance Regression** - Reduced from 55s to ~3s
  - `settle_delay`: 12s → 2s (correct API doesn't need long waits)
  - `initial_backoff_ms`: 3000 → 1000 (faster retries)
  - `max_retries`: 5 → 3 (fewer attempts needed)
  - `timeout_ms`: 60000 → 10000 (10s hard cap, NFR-004)

- **Stuck Password State Detection** - New `check_password_state()` function
  - Detects containers with `ChangePassword=1` stuck after failed resets
  - Pre-flight check warns before reset attempt
  - Post-reset verification confirms flag was cleared
  - Fails fast with remediation steps if container needs restart

- **ObjectScript Syntax Fixes** - Fixed `$$ISOK` macro issues
  - Changed to `$Select(sc=1:1,1:0)` for interactive ObjectScript compatibility
  - Affects: `export_classes()`, `import_classes()`, `export_global()`, `import_global()`, `export_package()`

- **Unit Test Fixes** - Fixed `iris_devtester` → `iris_devtester` in 10+ test files

### Added

- **Container Performance Documentation** - `docs/learnings/iris-container-performance.md`
  - Root cause analysis of IRIS container startup bottlenecks
  - Optimization strategies: namespace isolation, container reuse, pre-baked images
  - Quick wins for faster development cycles

## [1.7.5] - 2026-01-04 - PyPI Link & Metadata Finalization

### Fixed

- **Absolute Documentation Links**: Converted all documentation links in `README.md` to absolute GitHub URLs to fix broken navigation on the PyPI project page.
- **PyPI Meta Data**: Removed redundant license metadata fields that were causing distribution validation errors.
- **Metadata Consistency**: Synchronized version strings across `pyproject.toml`, `__init__.py`, and `SKILL.md`.

## [1.7.4] - 2026-01-04 - Metadata & Link Finalization (Internal)

### Fixed

- **Broken Documentation Links**: Fixed all references to the old `iris-devtools` name across README and documentation files.
- **PyPI Meta Data**: Corrected repository and documentation URLs in `pyproject.toml`.
- **Concise README**: Shortened the README for better visibility on PyPI, moving detailed guides to the `docs/` directory.
- **Metadata Consistency**: Synchronized `__init__.py`, `pyproject.toml`, and `SKILL.md` version strings.

## [1.7.1] - 2026-01-04 - Documentation & Metadata Fixes (Internal)

## [1.7.0] - 2026-01-02 - Feature 021: Hierarchical Agent Skills

### Added

- **Hierarchical Agent Skill Manifest (`SKILL.md`)**
  - Root-level guide for AI coding assistants following the "Progressive Disclosure" pattern.
  - **Level 1: Onboarding** - Automated pytest integration and conftest templates.
  - **Level 2: Operations** - Reliable container and connection management patterns.
  - **Level 3: Advanced** - DAT fixtures and resource monitoring guidance.
  - **Level 4: Debugging** - Autonomous troubleshooting for macOS latency and security flags.
- **Project Integration Module**: Specific instructions for agents to incorporate the library into new/existing repositories.
- **Enhanced Distribution**: Added `MANIFEST.in` to ensure AI metadata files (`SKILL.md`, `AGENTS.md`, `CLAUDE.md`) ship with the package.

### Fixed

- **Critical Bug Fixes (Feature 020)**
  - **Parametrized Password Reset**: `reset_password_if_needed` now supports custom users (e.g., `SuperUser`).
  - **Robust Security API**: Switched to `Security.Users.Modify` for clearing `ChangePassword` flags in IRIS 2024.1+.
  - **Deterministic Readiness**: `IRISReadyWaitStrategy` now uses application-level checks via `docker exec`.
  - **Fixture Refresh Support**: `DATFixtureLoader` now supports `force_refresh=True` to clear existing namespaces.
- **CLI Version Reporting**: Fixed CLI reporting stale version (`1.2.0`); now dynamically uses library version.
- **Container Status Validation**: Removed overly strict timestamp validators in `ContainerState` that caused crashes on restarted containers.
- **Architecture Mismatch Detection**: Improved Docker error translation to explicitly detect and report CPU architecture mismatches (e.g., Apple Silicon).
- **Flexible Image Configuration**: Added `image` key to configuration to support custom registries and full image names without forced prefixes.
- **False Negative Reporting**: Fixed CLI `container up` reporting failure after successful creation due to incorrect exception handling.

## [1.6.0] - 2026-01-02 - Feature 019: Agent Skills

### Added

- **Agent Skills (Feature 019)**
  - New "Skills" documentation for AI coding assistants (Claude, Cursor, Copilot)
  - **Claude Code**: `.claude/commands/` support (`/container`, `/connection`, `/fixture`, `/troubleshoot`)
  - **Cursor IDE**: `.cursor/rules/` support (`@iris-container`, `@iris-connection`, etc.)
  - **GitHub Copilot**: `.github/copilot-instructions.md` configuration
  - **Documentation**: New `docs/features/agent-skills.md` guide
  - **Verification**: Contract tests ensuring skill file integrity

## [1.5.3] - Feature 017: IRIS Source Insights

### Added

- **Container Health: $SYSTEM.Monitor.State() Integration (US6)**
  - Added Layer 4 to `wait_for_healthy()`: IRIS-level health check using `$SYSTEM.Monitor.State()`
  - New `check_iris_monitor_state()` function for checking true IRIS readiness
  - New `wait_for_iris_healthy()` function for polling until IRIS is ready
  - New `IrisHealthState` enum matching IRIS API values (0=OK, 1=Warning, 2=Error, 3=Fatal)
  - New `IrisMonitorResult` dataclass for structured health check results
  - Source: `docs/learnings/iris-container-readiness.md`

- **Password Reset: Correct IRIS API Patterns (US5)**
  - Fixed ObjectScript to use `ChangePassword` property (not `ChangePasswordAtNextLogin`)
  - Fixed ObjectScript to use `PasswordExternal` for setting passwords (triggers PBKDF2 hashing)
  - Added `AccountNeverExpires=1` to password reset pattern for reliability
  - Source: `docs/learnings/iris-security-users-api.md`

- **DAT Fixture Export/Import Utilities (US7)**
  - New `export_classes()` function using `$SYSTEM.OBJ.Export`
  - New `import_classes()` function using `$SYSTEM.OBJ.Import`
  - New `export_global()` function using `##class(%Library.Global).Export` (%GOF format)
  - New `import_global()` function using `##class(%Library.Global).Import`
  - New `export_package()` function using `$SYSTEM.OBJ.ExportPackage`
  - New `ExportResult` and `ImportResult` dataclasses for structured results
  - Source: `docs/learnings/iris-backup-patterns.md`

- **Documentation: IRIS Source Code Insights**
  - New `docs/learnings/iris-security-users-api.md` - Password management patterns from Security.Users
  - New `docs/learnings/iris-container-readiness.md` - Container health check patterns from SYS.Container
  - New `docs/learnings/iris-backup-patterns.md` - Export/Import patterns for DAT fixtures
  - Updated `CLAUDE.md` with ObjectScript Patterns section for AI assistant reference

### Changed

- **health_checks.py**: wait_for_healthy() now includes 4 layers (was 3)
  - Layer 1: Container running
  - Layer 2: Docker health check
  - Layer 3: SuperServer port accessible
  - Layer 4: IRIS Monitor.State() = OK (NEW)

### Technical Details

**$SYSTEM.Monitor.State() Return Values**:
- 0: OK - System healthy, ready for connections
- 1: Warning - Minor issues, may still work
- 2: Error - Significant problems, connections may fail
- 3: Fatal - Critical failure, do not use

**Why This Matters**: A container with SuperServer port open is NOT necessarily ready.
The Monitor.State() API checks true IRIS-level health, preventing intermittent
connection failures during container startup.

## [1.5.0] - 2025-11-24

### Fixed

- **CRITICAL FIX (Feature 015): Use Correct IRIS API for Password Reset**
  - **Root Cause**: Code was using `ChangePassword()` method which **DOES NOT EXIST** in IRIS
    - Error: `<METHOD DOES NOT EXIST> *ChangePassword,Security.Users`
    - Password reset would return "success" but password was never actually changed
    - Verification was connecting to wrong port (testcontainers random ports vs hardcoded 1972)
  - **Correct Implementation**: Use official `Get()/Modify()` pattern with property arrays
    - `Get(username, .properties)` - Retrieve user properties (pass by reference)
    - `Set properties("Password") = password` - Set the password field
    - `Set properties("ChangePassword") = 0` - Prevent password change prompt
    - `Set properties("PasswordNeverExpires") = 1` - Prevent future expiration
    - `Modify(username, .properties)` - Commit changes atomically
  - **Performance Improvement**: 840x faster (0.08s vs 67s of failed retries)
  - **Success Rate**: 100% (4/4 integration tests passing)
  - **Location**: `iris_devtester/utils/password_reset.py:82-114`

### Changed

- **password_reset.py**: Replaced two-step approach with single atomic operation
  - Removed non-existent `ChangePassword()` call
  - Used correct `Get() + Modify()` pattern with Password field
  - Added `PasswordNeverExpires=1` for medical-grade reliability
  - Simplified from 2 docker exec calls to 1 atomic operation
- **test_password_reset_integration.py**: Fixed testcontainers port mismatch
  - All `reset_password()` calls now include correct host/port parameters
  - Tests use actual exposed port from testcontainers instead of hardcoded 1972

### Technical Details

**ObjectScript is Position-Based (NOT Keyword-Based)**:
```objectscript
// WRONG - This method does NOT exist!
##class(Security.Users).ChangePassword("_SYSTEM", "password")

// RIGHT - Use Get/Modify pattern
Set u="_SYSTEM"
Do ##class(Security.Users).Get(u,.p)     // .p = pass by reference
Set p("Password")="password"
Set p("ChangePassword")=0
Set p("PasswordNeverExpires")=1
Write ##class(Security.Users).Modify(u,.p)
Halt
```

**Key Learnings**:
- The `.properties` syntax means "pass by reference" (required for Get/Modify)
- Property names are case-sensitive
- `Write` statement outputs the return value (1 = success)
- Always end with `Halt` to exit cleanly

### Documentation

- **CLAUDE.md**: Added new "ObjectScript Patterns" section with critical learnings
- **password_reset.py**: Updated docstrings to reflect correct API usage
- **README.md**: Updated to reflect accurate implementation

### Migration from v1.4.x

No code changes required - v1.5.0 is a drop-in replacement. Just upgrade:
```bash
pip install --upgrade iris-devtester
```

**What Changed Internally**:
- Password reset now actually works (was silently failing in v1.4.x)
- Verification happens on correct port (testcontainers-aware)
- Uses official IRIS API instead of non-existent methods

## [1.4.5] - 2025-11-20

### Fixed

- **CRITICAL HOTFIX (Feature 015): Dual User Hardening - Actually fixes v1.4.2-v1.4.4 bug**
  - **Root Cause of v1.4.2-v1.4.4 Failures**: Only hardening the created user, not SuperUser
    - Tests create a user (e.g., "test") and harden it
    - But connections use SuperUser credentials
    - IRIS greets SuperUser connections with "Password change required"
    - DBAPI clients don't implement password-change handshake → Access Denied
    - Bug persisted through THREE releases (v1.4.2, v1.4.3, v1.4.4)
  - **Actual Fix**: Dual user hardening (harden BOTH target user AND SuperUser)
    - Idempotent user creation (check Exists() before Create())
    - Clear ChangePasswordAtNextLogin=0 for BOTH users
    - Call UnExpireUser() for BOTH users
    - SetPassword() for BOTH users
  - **Impact**: 100% success rate on macOS (v1.4.2-v1.4.4 had ~50% failure rate)
  - **Location**: `iris_devtester/utils/password_reset.py`

### Changed

- **password_reset.py**: Implemented dual user hardening pattern
  - New helper function: `_harden_iris_user()` for idempotent user hardening
  - Hardens target user with provided credentials
  - Also hardens SuperUser (unless target user IS SuperUser)
  - Uses chr(34) for embedded quotes to avoid shell escaping issues
  - Maintains all v1.4.4 fixes (IPv4 forcing, 4s settle delay on macOS)

### Technical Details

**Why v1.4.2-v1.4.4 Failed**:
All three versions only hardened the target user. When tests created a user but connected as SuperUser, the server still had SuperUser flagged with "ChangePasswordAtNextLogin" or expired, causing "Access Denied" errors.

**v1.4.5 Dual Hardening Pattern**:
```python
# Harden the target user
_harden_iris_user(container, username="test", password="TESTPWD")

# Also harden SuperUser (unless it's the same as target)
if username != "SuperUser":
    _harden_iris_user(container, username="SuperUser", password="SYS")
```

**ObjectScript Pattern**:
```objectscript
set u="{username}",
p("ChangePasswordAtNextLogin")=0,
p("PasswordNeverExpires")=1,
if ##class(Security.Users).Exists(u)=0
do ##class(Security.Users).Create(u,"%ALL","{password}")
do ##class(Security.Users).UnExpireUser(u)
do ##class(Security.Users).Modify(u,.p)
do ##class(Security.Users).SetPassword(u,"{password}")
```

### Why This Fix Works

The dual hardening ensures that:
1. The created test user is properly configured (if using that user)
2. SuperUser is ALSO properly configured (if using SuperUser)
3. No matter which user the test connects as, it will work
4. Idempotent creation means it's safe to run multiple times

### Migration from v1.4.2-v1.4.4

No code changes required - v1.4.5 is a drop-in replacement. Just upgrade:
```bash
pip install --upgrade iris-devtester
```

## [1.4.4] - 2025-11-20

### Fixed

- **HOTFIX (Feature 015): Fixed actual root causes of macOS password reset failures**
  - **Root Cause #1**: IRIS flagging account as `ChangePasswordAtNextLogin=1` after password reset
    - DBAPI clients don't implement server-side password-change handshake
    - Clients surface "Invalid Message received; ... Password change required / Access Denied"
    - **Fix**: Explicitly set `ChangePasswordAtNextLogin=0` via `Security.Users.Modify()`
  - **Root Cause #2**: User account expiration not being cleared
    - **Fix**: Call `Security.Users.UnExpireUser()` before setting password
  - **Root Cause #3**: IPv6 localhost resolution on macOS causing auth failures
    - macOS resolves "localhost" to ::1 (IPv6) which can trigger auth issues
    - **Fix**: Force IPv4 (127.0.0.1) on macOS via platform detection
  - **Root Cause #4**: Security metadata propagation delay on Docker Desktop/macOS
    - IRIS security subsystem lags 4-6 seconds after SetPassword/UnExpire on macOS VM
    - **Fix**: Add 4-second settle delay on macOS after password reset
  - **Impact**: These fixes address the actual problem (v1.4.3 only added retry logic which masked symptoms)
  - **Location**: `iris_devtester/utils/password_reset.py`

### Changed

- **password_reset.py**: Updated ObjectScript to properly configure IRIS security state
  - Now calls `UnExpireUser()` to clear expiration
  - Sets `ChangePasswordAtNextLogin=0` to prevent forced password change on next login
  - Uses `SetPassword()` separately from property modification (proper IRIS API pattern)
  - Auto-detects macOS and forces IPv4 (127.0.0.1) instead of localhost
  - Adds 4s settle delay on macOS for security metadata propagation

### Technical Details

**Previous Implementation (v1.4.3)**:
```objectscript
do ##class(Security.Users).Get("{user}",.p)
set p("Password")="{password}"
set p("PasswordNeverExpires")=1
do ##class(Security.Users).Modify("{user}",.p)
```
**Problem**: Didn't clear ChangePasswordAtNextLogin flag or user expiration state.

**New Implementation (v1.4.4)**:
```objectscript
do ##class(Security.Users).UnExpireUser("{user}")
do ##class(Security.Users).Get("{user}",.p)
set p("ChangePasswordAtNextLogin")=0
set p("PasswordNeverExpires")=1
do ##class(Security.Users).Modify("{user}",.p)
do ##class(Security.Users).SetPassword("{user}","{password}")
```
**Fix**: Properly clears all security flags that cause "Password change required" errors.

**IPv4 Forcing (macOS only)**:
```python
hostname = os.getenv("IRIS_DEVTESTER_HOST") or (
    "127.0.0.1" if platform.system() == "Darwin" else "localhost"
)
```

**Settle Delay (macOS only)**:
```python
if platform.system() == "Darwin":
    time.sleep(4.0)  # Wait for security metadata propagation
```

### Why v1.4.3 Didn't Fix It

v1.4.3 added connection-based verification with retry logic, which is valuable for diagnostics but doesn't address the root cause. The retry logic just repeatedly attempted connections to a broken security state. This hotfix actually fixes the security state itself.

## [1.4.3] - 2025-11-20

### Fixed

- **Bug Fix (Feature 015): Password Reset Reliability on macOS**
  - Fixed critical race condition where `reset_password()` returned success but password not yet available for connections
  - Root cause: macOS Docker Desktop VM-based networking has 4-6 second delay vs Linux's <1 second
  - Previous behavior: `time.sleep(2)` insufficient → "Access Denied" errors despite success status
  - New behavior: Connection-based verification with retry logic and exponential backoff
  - **Impact**: 100% success rate on macOS (previously ~50% failure rate)
  - **Performance**: Completes within 10 seconds (NFR-004), typically 3-7 seconds on macOS
  - **Backward Compatible**: Returns `PasswordResetResult` that unpacks to `(bool, str)` tuple

- **New Module**: `iris_devtester/utils/password_verification.py`
  - `PasswordResetResult` dataclass with verification metadata (attempts, elapsed time, error type)
  - `VerificationConfig` dataclass with retry settings (max_retries=3, timeout_ms=10000, exponential backoff)
  - `verify_password_via_connection()` - Verify password via DBAPI connection attempt
  - `classify_error()` - Distinguish retryable vs non-retryable errors
  - Exponential backoff: 100ms → 200ms → 400ms between retries
  - Early exit on success (no unnecessary retries)
  - Fail fast on non-retryable errors (connection refused, network unreachable)

### Changed

- **utils/password_reset.py**: Added connection-based verification
  - `reset_password()` now verifies password via connection before returning success
  - Replaced `time.sleep(2)` with retry loop + exponential backoff
  - Returns `PasswordResetResult` with enhanced metadata (backward compatible with tuple unpacking)
  - Logs verification attempts and timing for diagnostics (Constitutional Principle #7)
  - Respects 10-second hard timeout (NFR-004)
  - Constitutional error messages with structured failure details

### Added

- **Comprehensive Testing** (12 contract tests + 10 integration tests)
  - Contract tests verify FR-002 (password verification before success)
  - Contract tests verify FR-007 (retry with exponential backoff)
  - Contract tests verify NFR-004 (10-second timeout)
  - macOS-specific integration tests for Docker Desktop compatibility
  - Cross-platform timing tests
  - Success rate validation tests (NFR-001: ≥99% success rate)
  - **Location**: `tests/contract/test_reset_verification_contract.py` (5 tests)
  - **Location**: `tests/contract/test_retry_logic_contract.py` (7 tests)
  - **Location**: `tests/integration/test_password_reset_macos.py` (5 tests)
  - **Location**: `tests/integration/test_password_reset_timing.py` (5 tests)

## [1.3.0] - 2025-01-15

### Added

- **Feature 012: DBAPI Package Compatibility**
  - Support for both modern (`intersystems-irispython` v5.3.0+) and legacy (`intersystems-iris` v3.0.0+) IRIS Python packages
  - Automatic package detection with zero configuration (Constitutional Principle #4)
  - Modern package prioritized, legacy package as fallback
  - Version validation ensures minimum compatible versions
  - Constitutional error messages (What/Why/How/Docs format) per Principle #5
  - Package detection logging at INFO level (FR-010) - shows which package and version detected
  - Detection performance <10ms overhead (NFR-001)
  - **Location**: `iris_devtester/utils/dbapi_compat.py` (new compatibility layer)
  - **Impact**: Fixes AttributeError with modern package, maintains backward compatibility with legacy package

- **New Module**: `iris_devtester/utils/dbapi_compat.py`
  - `DBAPIPackageInfo` dataclass for package metadata
  - `detect_dbapi_package()` - Try/except import chain (modern first, legacy fallback)
  - `validate_package_version()` - Semantic version validation
  - `DBAPIConnectionAdapter` - Singleton adapter for zero-overhead connections
  - `get_connection()` - Public API for connections
  - `get_package_info()` - Public API for package metadata
  - `DBAPIPackageNotFoundError` - Constitutional error when no package installed

### Changed

- **connections/dbapi.py**: Updated to use compatibility layer
  - `is_dbapi_available()` now detects both modern and legacy packages
  - `create_dbapi_connection()` uses `get_connection()` from dbapi_compat
  - Logs package name and version when connecting (FR-010)

- **connections/connection.py**: Updated error messages
  - Mentions both modern and legacy packages
  - Provides installation options for both
  - Includes documentation link

- **connections/manager.py**: Enhanced package logging
  - Auto mode logs detected package with version and detection time
  - Example: "✓ Connected using DBAPI - intersystems-irispython v5.3.0 (detected in 2.45ms)"
  - Error messages updated to mention both packages
  - All error messages include documentation links

### Fixed

- **AttributeError with modern package**: Fixed compatibility issue when using `intersystems-irispython`
  - Previous code only supported legacy `intersystems-iris` package
  - Modern package uses different import path (`intersystems_iris.dbapi._DBAPI` vs `iris.irissdk`)
  - Now automatically detects and uses whichever package is installed

### Technical Details

- **Package Detection Strategy**: Try/except import chain
  1. Try modern package: `intersystems_iris.dbapi._DBAPI`
  2. Fall back to legacy: `iris.irissdk`
  3. Raise constitutional error if neither available

- **Version Requirements**:
  - Modern: `intersystems-irispython >= 5.3.0`
  - Legacy: `intersystems-iris >= 3.0.0`

- **Performance**:
  - Detection overhead: <10ms (measured via `time.perf_counter()`)
  - Zero connection overhead: Direct function call via singleton adapter
  - Package info cached at module level

- **Logging**:
  - INFO: Package detected successfully
  - DEBUG: Fallback from modern to legacy
  - ERROR: No package available

### Constitutional Compliance

- **Principle #2**: DBAPI First - Maintains performance, now with both packages
- **Principle #4**: Zero Configuration Viable - Automatic package detection
- **Principle #5**: Fail Fast with Guidance - Constitutional error format throughout
- **Principle #7**: Medical-Grade Reliability - 95%+ test coverage maintained

### Functional Requirements Satisfied

- FR-001: Detect modern package (intersystems-irispython)
- FR-002: Detect legacy package (intersystems-iris) as fallback
- FR-003: Prioritize modern package when both installed
- FR-004: Version validation (modern >= 5.3.0, legacy >= 3.0.0)
- FR-005: Constitutional error when no package installed
- FR-006: Backward compatibility (no breaking changes)
- FR-007: Update connections module
- FR-008: Update fixtures module (via connection delegation)
- FR-009: Update testing utilities (via connection delegation)
- FR-010: Logging - shows package name and version

### Non-Functional Requirements Satisfied

- NFR-001: Performance - <10ms detection, zero connection overhead
- NFR-002: Error Messages - Constitutional format (What/Why/How/Docs)
- NFR-003: Test Coverage - 95%+ maintained
- NFR-004: Documentation - Migration guide and API docs

### Testing

- **Contract Tests**: 27 tests covering all 4 contracts (modern, legacy, no-package, priority)
- **Coverage**: 95%+ maintained across all modules
- **No Regression**: All existing tests pass (100%)

### Migration Notes

- **Zero Breaking Changes**: Existing code continues to work with either package
- **Automatic Migration**: Install modern package, code automatically switches
- **Package Priority**: Modern package automatically used when both installed
- **Error Messages**: Clear guidance when no compatible package installed

### Documentation

- **Specification**: `specs/012-address-enhancement-iris/spec.md`
- **Implementation Plan**: `specs/012-address-enhancement-iris/plan.md`
- **Research**: `specs/012-address-enhancement-iris/research.md`
- **Data Model**: `specs/012-address-enhancement-iris/data-model.md`
- **Contracts**: `specs/012-address-enhancement-iris/contracts/` (4 JSON contracts)
- **Quickstart**: `specs/012-address-enhancement-iris/quickstart.md` (10 usage scenarios)
- **Tasks**: `specs/012-address-enhancement-iris/tasks.md` (30 implementation tasks)

## [1.2.2] - 2025-01-13

### Fixed

- **Bug Fix #1: Prevented ryuk cleanup of CLI-managed containers (Feature 011)**
  - CLI commands now use Docker SDK directly, bypassing testcontainers-iris for container creation
  - Containers created via CLI persist until explicit removal (not cleaned up when CLI exits)
  - Added dual-mode container creation: Docker SDK for CLI, testcontainers for pytest fixtures
  - Resolved testcontainers ryuk sidecar removing containers immediately after CLI process exits
  - **Impact**: Benchmark infrastructure can now run 30+ minute test suites (0% → 92% pass rate)
  - **Location**: `iris_devtester/utils/iris_container_adapter.py` (dual-mode implementation)
  - **Documentation**: New learnings doc at `docs/learnings/testcontainers-ryuk-lifecycle.md`
  - **Technical Details**:
    - CLI mode: `use_testcontainers=False` - No ryuk labels, manual lifecycle
    - Test mode: `use_testcontainers=True` - Automatic cleanup after test scope
    - Benchmark tests improved from 0/24 (0.0%) to 22/24 (91.7%) passing

- **Bug Fix #2: Fixed volume mounting for CLI containers (Feature 011)**
  - Volumes now applied correctly via Docker SDK when using CLI commands
  - Volume mounts verified after container creation with `verify_container_persistence()`
  - Supports multiple volumes with read-only mode (`:ro` suffix)
  - Added volume path validation before container creation
  - **Impact**: Workspace files now accessible in benchmark containers
  - **Location**:
    - `iris_devtester/utils/iris_container_adapter.py` (Docker SDK volume application)
    - `iris_devtester/config/container_config.py` (validate_volume_paths method)
  - **Example**:
    ```yaml
    volumes:
      - ./workspace:/external/workspace     # Read-write
      - ./config:/opt/config:ro             # Read-only
    ```

- **Bug Fix #3: Added container persistence verification (Feature 011)**
  - Post-creation check ensures container actually persists after creation
  - Detects immediate cleanup (ryuk) and reports constitutional error
  - Verifies volume mounts are accessible
  - Wait 2 seconds after creation, then verify container exists and is running
  - **Impact**: No more silent container creation failures ("Failed to create container: 0" errors)
  - **Location**: `iris_devtester/utils/iris_container_adapter.py` (verify_container_persistence function)
  - **Data Model**: `ContainerPersistenceCheck` dataclass with success property

### Added

- **Volume Mount Parsing**: `VolumeMountSpec` dataclass for parsing Docker volume syntax
  - Parses `host:container` or `host:container:mode` format
  - Validates mode is `rw` (read-write) or `ro` (read-only)
  - Defaults to `rw` if mode not specified
  - Constitutional error messages for invalid syntax

- **Volume Path Validation**: `ContainerConfig.validate_volume_paths()` method
  - Checks all host paths exist before container creation
  - Returns list of error messages (empty if all valid)
  - Called automatically by CLI before creating containers

- **Enhanced Error Messages**: Volume mount failures now have constitutional format
  - What went wrong: Specific error details
  - Why this happened: Common causes explained
  - How to fix it: Step-by-step remediation
  - Documentation: Links to Docker volume documentation

### Changed

- **CLI Container Creation**: Updated `container up` and `container start` commands
  - Now use `use_testcontainers=False` for persistent containers
  - Add volume path validation before creation
  - Add persistence verification after creation
  - Report success only after verification passes

### Migration Notes

- **No breaking changes** - All fixes are backwards compatible
- **pytest fixtures** continue to use testcontainers (automatic cleanup)
- **CLI commands** now use Docker SDK (manual cleanup when user decides)
- **Benchmark success rate** improved from 0/24 (0.0%) to 22/24 (91.7%)
- **Container lifecycle**:
  - Before: Container removed within ~60 seconds (ryuk cleanup)
  - After: Container persists indefinitely until explicit removal

### Technical Details

- **Environment Variable Fix**: Removed incorrect `ISC_DATA_DIRECTORY` environment variable
  - Initial implementation set `ISC_DATA_DIRECTORY` to non-existent path
  - Caused containers to exit immediately with "Durable folder does not exist" error
  - Fixed by using empty environment for Community edition (IRIS bootstraps automatically)
  - Only Enterprise edition containers need `ISC_LICENSE_KEY` environment variable
  - **Documentation**: `docs/learnings/iris-docker-sdk-environment-variables.md`

### Quality Assurance

- All 35 existing contract tests passing (100% - no regression)
- 14 new unit tests added (100% passing):
  - 4 tests for volume path validation
  - 5 tests for volume mount parsing (`VolumeMountSpec`)
  - 5 tests for persistence verification (`ContainerPersistenceCheck`)
- 6 new integration tests with real Docker containers (100% passing):
  - 2 tests for ryuk prevention (container persistence, no testcontainers labels)
  - 3 tests for volume mounting (single, multiple, read-only)
  - 1 test for persistence verification
- Constitutional Principle #5 compliance maintained (all error messages follow What/Why/How/Docs format)

### Performance

| Metric | Before (v1.2.1) | After (v1.2.2) | Improvement |
|--------|----------------|----------------|-------------|
| Benchmark pass rate | 0/24 (0.0%) | 22/24 (91.7%) | +91.7% |
| Container persistence | ~30 seconds | Indefinite | ∞ |
| Volume mounting | ❌ Not working | ✅ Working | Fixed |

## [1.2.1] - 2025-01-13

### Fixed

- **Bug Fix #1: Corrected Docker image name for Community edition**
  - Fixed `ContainerConfig.get_image_name()` to use correct Docker Hub organization
  - Community images changed from `intersystems/iris-community` → `intersystemsdc/iris-community`
  - The `intersystems/iris-community` image doesn't exist on Docker Hub
  - Community images use `intersystemsdc/` prefix (Docker Community organization)
  - Enterprise images continue to use `intersystems/` prefix (no change)
  - **Impact**: Community edition containers now start successfully (0 image-not-found errors)
  - **Location**: `iris_devtester/config/container_config.py:266`
  - **Documentation**: New learnings doc at `docs/learnings/docker-hub-image-naming.md`

- **Bug Fix #3: Implemented volume mounting support**
  - Volume mounts specified in `ContainerConfig.volumes` are now applied to containers
  - Supports Docker volume syntax: `host:container` or `host:container:mode`
  - Mode defaults to `rw` (read-write) if not specified, supports `ro` (read-only)
  - Multiple volumes can be mounted simultaneously
  - **Impact**: Configuration-defined volumes now work correctly (previously ignored)
  - **Location**: `iris_devtester/utils/iris_container_adapter.py:52-58`
  - **Example**:
    ```yaml
    volumes:
      - ./data:/external          # Read-write mount
      - ./config:/opt/config:ro   # Read-only mount
    ```

### Migration Notes

No breaking changes - all fixes are backwards compatible:
- Community edition now uses correct image name automatically
- Volume mounting is additive functionality (empty volumes list works as before)
- Existing configurations continue to work without modification

### Quality Assurance

- All 35 existing contract tests passing (100% - no regression)
- 4 new unit tests for image name correction (100% passing)
- 4 new unit tests for volume mounting (100% passing)
- Constitutional Principle #5 compliance maintained (error messages still follow What/Why/How/Docs format)

## [1.2.0] - 2025-01-11

### Changed

#### Refactored CLI to use testcontainers-iris
- **BREAKING**: None - All CLI commands maintain identical interface and behavior
- Replaced custom Docker SDK wrapper (461 lines) with thin adapter layer (247 lines)
- Container lifecycle commands now leverage `testcontainers-iris` for container operations
- **46% code reduction** in container management layer (214 lines removed)
- **Benefits**:
  - Shared bug fixes from testcontainers-iris community
  - Reduced maintenance burden
  - Battle-tested implementation from wider Python ecosystem
  - Automatic improvements as testcontainers-iris evolves

#### Technical Implementation (Feature 009)
- **Added**: `iris_container_adapter.py` (247 lines) - Adapter between CLI and testcontainers-iris
  - `IRISContainerManager.create_from_config()` - Maps ContainerConfig to IRISContainer
  - `IRISContainerManager.get_existing()` - Gets existing containers by name
  - `translate_docker_error()` - Constitutional error translation (4-part format preserved)
- **Moved**: `get_container_state()` → `ContainerState.from_container()` classmethod
  - Better architecture: Logic now lives in the right place (ContainerState class)
  - More intuitive API for querying container state
- **Deleted**: `docker_utils.py` (461 lines) - Replaced by testcontainers-iris + adapter
- **Preserved**: All functionality from v1.1.0
  - 7 CLI commands unchanged (up, start, stop, restart, status, logs, remove)
  - Progress indicators and emoji-based status updates
  - Constitutional error messages (What/Why/How/Docs format)
  - Configuration management (YAML, environment variables, zero-config)
  - Multi-layer health checks
  - Automatic CallIn service enablement

#### Quality Assurance
- **Tests**: All 35 contract tests passing (100%)
- **Tests**: All 20 adapter unit tests passing (100%)
- **Zero breaking changes** verified - Same CLI interface, same exit codes, same behavior
- **Performance**: No regression in container operations
- **Documentation**: Updated examples and docstrings to reflect new API

### Dependencies
- No new dependencies - Leverages existing `testcontainers-iris>=1.2.2` dependency

## [1.1.0] - 2025-01-11

### Added

#### Container Lifecycle CLI Commands
- **NEW**: Complete container lifecycle management via CLI
  - `iris-devtester container up` - Create and start IRIS container with zero-config support
  - `iris-devtester container start` - Start existing container
  - `iris-devtester container stop` - Gracefully stop running container
  - `iris-devtester container restart` - Restart container with health checks
  - `iris-devtester container status` - Display container state (text/JSON output)
  - `iris-devtester container logs` - View container logs (with --follow support)
  - `iris-devtester container remove` - Remove container with optional volume cleanup

#### Configuration Management
- `ContainerConfig` - Pydantic v2 model for container configuration
  - Support for both Community and Enterprise editions
  - YAML configuration file support (`iris-config.yml`)
  - Environment variable configuration (`IRIS_*` variables)
  - Zero-config mode with sensible defaults
  - Configuration hierarchy: explicit config → local file → env → defaults
- `ContainerState` - Runtime container state tracking with health status
- Configuration validation with helpful error messages

#### Multi-Layer Health Checks
- Progressive health validation for containers:
  - Layer 1: Container running (fast fail on crashes)
  - Layer 2: Docker health check (if defined)
  - Layer 3: IRIS SuperServer port accessible
- Automatic CallIn service enablement (required for DBAPI)
- Progress indicators and status updates during container operations

#### Docker SDK Integration
- Comprehensive Docker SDK wrapper with constitutional error messages
- Automatic image pulling with fallback to local images
- Port conflict detection with remediation guidance
- Idempotent operations (safe retries)
- Proper exit codes: 0 (success), 1 (error), 2 (config), 3 (running), 5 (timeout)

#### Examples and Documentation
- Example configurations:
  - `examples/iris-config-community.yml` - Community Edition template
  - `examples/iris-config-enterprise.yml` - Enterprise Edition template with license setup
  - `examples/demo-workflow.sh` - Complete lifecycle demonstration script

### Changed
- Updated package version to 1.1.0
- Fixed CLI prog_name to match package name (iris-devtester)
- Added PyYAML and Pydantic dependencies

### Technical Details
- 33 implementation tasks completed (77% of Feature 008)
- 35 contract tests (all passing)
- 50+ unit tests for configuration and validation
- Constitutional principles compliance:
  - Principle #2: DBAPI First (automatic CallIn enablement)
  - Principle #4: Zero Configuration Viable (works without config files)
  - Principle #5: Fail Fast with Guidance (4-part error messages: What/Why/How/Docs)
  - Principle #6: Enterprise Ready, Community Friendly (both editions supported)

## [1.0.2] - 2025-01-09

### Fixed
- **CRITICAL**: Fixed `reset_password()` bug where function reported success but password was not actually set
  - Now uses correct IRIS Security API property `Password` (not `ExternalPassword`)
  - Now calls `Security.Users.Get()` before `Modify()` per IRIS API requirements
  - Now sets `PasswordNeverExpires=1` to prevent password expiration (not `ChangePassword=0`)
  - Fixes "Access Denied" errors after password reset
  - Verified on AWS EC2, IRIS Community 2025.1
  - Works on both IRIS Community and Enterprise editions
- Issue reported in production user feedback

## [1.0.0] - 2025-10-18

### 🎉 Initial Release

First stable release of iris-devtester, a battle-tested Python package for InterSystems IRIS infrastructure.

### Added

#### Container Management
- `IRISContainer` wrapper with automatic connection management
- `IRISContainer.community()` - Zero-config Community Edition containers
- `IRISContainer.enterprise()` - Enterprise Edition with license support
- `IRISContainer.from_existing()` - Auto-discover existing IRIS instances
- ObjectScript execution support via `get_iris_connection()`
- Namespace management: `create_namespace()`, `delete_namespace()`, `get_test_namespace()`
- Automatic password reset integration
- Wait strategies for container readiness

#### Connection Management
- `get_connection()` - Zero-config connection with auto-discovery
- DBAPI-first approach (3x faster than JDBC)
- Automatic fallback to JDBC when DBAPI unavailable
- Connection pooling support (documented for v1.2.0)
- Retry logic with exponential backoff
- Environment variable configuration support

#### Testing Utilities
- pytest fixtures for IRIS integration tests
  - `iris_container` - Session-scoped container lifecycle
  - `test_namespace` - Function-scoped namespace with auto-cleanup
  - `iris_connection` - DBAPI connection for SQL operations
  - `iris_objectscript_connection` - ObjectScript execution connection
- Schema reset utilities
  - `reset_namespace()` - Drop all user tables
  - `get_namespace_tables()` - Query tables via INFORMATION_SCHEMA
  - `verify_tables_exist()` - Validate expected schema
  - `SchemaResetter` - Context manager for test isolation
- Auto-discovery
  - Docker container inspection
  - Native IRIS detection via `iris list`
  - Multi-port scanning (31972, 1972, 11972, 21972)

#### .DAT Fixture Management
- `FixtureCreator` - Create fixtures from namespaces via BACKUP^DBACK
- `DATFixtureLoader` - Load fixtures via RESTORE (<1s)
- `FixtureValidator` - Validate integrity with SHA256 checksums
- CLI commands: `create`, `load`, `validate`, `list`, `info`
- pytest plugin: `@pytest.mark.dat_fixture` decorator
- Manifest generation with metadata
- Atomic operations with rollback

#### Performance Monitoring
- `MonitoringPolicy` - ^SystemPerformance configuration
- `configure_monitoring()` - Zero-config monitoring setup
- `get_monitoring_status()` - Query monitoring state
- `enable_monitoring()` / `disable_monitoring()` - Control monitoring
- Task Manager integration
  - `create_task()`, `get_task_status()`, `suspend_task()`, `resume_task()`, `delete_task()`
- Resource monitoring
  - `get_resource_metrics()` - CPU, memory, database metrics
  - `check_resource_thresholds()` - Auto-disable/enable logic
  - `auto_disable_monitoring()` / `auto_enable_monitoring()` - Automatic remediation
- `ResourceThresholds` - Configurable thresholds with hysteresis

#### Documentation
- Complete API documentation
- `SQL_VS_OBJECTSCRIPT.md` - Critical execution pattern guide
- `rag-templates-production-patterns.md` - 7 battle-tested patterns
- `CONSTITUTION.md` - 8 core design principles
- `ROADMAP.md` - Future features (v1.1.0+)
- Integration test examples
- Comprehensive docstrings (Google style)

### Quality Metrics
- 224/238 unit tests passing (94%)
- 93 contract tests passing (100%)
- 29 integration tests passing
- 54 integration tests ready (require IRIS container)
- 100% docstring coverage
- 100% type hint coverage
- Medical-grade error messages (Constitutional Principle #5)

### Constitutional Principles
All features follow the [8 core principles](CONSTITUTION.md):
1. ✅ Automatic Remediation Over Manual Intervention
2. ✅ DBAPI First, JDBC Fallback
3. ✅ Isolation by Default
4. ✅ Zero Configuration Viable
5. ✅ Fail Fast with Guidance
6. ✅ Enterprise Ready, Community Friendly
7. ✅ Medical-Grade Reliability
8. ✅ Document the Blind Alleys

### Production Patterns Integrated
Extracted from `rag-templates` production system:
1. Multi-Port Discovery with Fallback
2. Docker Container Port Auto-Detection
3. Connection Pooling (documented for v1.2.0)
4. Automatic Password Reset
5. "Out of the Way" Port Mapping
6. Schema Reset Utilities
7. Retry Logic with Exponential Backoff

### Breaking Changes
N/A - Initial release

### Deprecated
N/A - Initial release

### Fixed
N/A - Initial release

### Security
- SHA256 checksums for .DAT fixture integrity
- Secure password handling in connection strings
- No credentials in logs or error messages

---

## [Unreleased]

### Planned for v1.1.0
- VECTOR datatype introspection via audit trail
- Enhanced schema inspector combining INFORMATION_SCHEMA + audit data
- SQLAlchemy dialect extension with VECTOR type awareness
- Schema reflection with correct VECTOR types

### Planned for v1.2.0
- Production-grade connection pooling implementation
- Query performance tracking
- Advanced testing utilities
- DAT fixture versioning

### Planned for v2.0.0
- Multi-instance support
- Mirror configuration support
- Enterprise features (sharding, ECP, etc.)

---

## Release Notes

### v1.0.0 Highlights

**Zero Configuration**: `pip install iris-devtester && pytest` works out of the box.

**Battle-Tested**: Every feature extracted from production code, representing years of debugging hours saved.

**Constitutional Compliance**: All 8 design principles followed throughout.

**Comprehensive Testing**: 94% test coverage with 224 unit tests, 93 contract tests, and 83 integration tests.

**Production Patterns**: 7 patterns from rag-templates integrated and documented.

**Documentation**: 1,200+ lines of documentation including critical SQL vs ObjectScript guide.

---

**Remember**: Every feature here was paid for with real debugging time. 🚀

[1.10.1]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.10.1
[1.10.0]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.10.0
[1.9.3]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.9.3
[1.9.2]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.9.2
[1.8.1]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.8.1
[1.5.0]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.5.0
[1.4.5]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.4.5
[1.4.4]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.4.4
[1.4.3]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.4.3
[1.3.0]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.3.0
[1.2.2]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.2.2
[1.2.1]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.2.1
[1.2.0]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.2.0
[1.1.0]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.1.0
[1.0.2]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.0.2
[1.0.0]: https://github.com/intersystems-community/iris-devtester/releases/tag/v1.0.0
[Unreleased]: https://github.com/intersystems-community/iris-devtester/compare/v1.10.1...HEAD
