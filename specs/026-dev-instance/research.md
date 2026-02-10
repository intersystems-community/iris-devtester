# Research: The Dev Instance (Warm Start)

## Decisions

### 1. Persistence Strategy: Durable %SYS
- **Decision**: Use InterSystems IRIS "Durable %SYS" feature.
- **Rationale**: Standard volumes mapped to `/usr/irissys/mgr` can fail if the volume is initially empty. Durable %SYS bootstraps system files into a clean directory.
- **Technical Detail**: Set `ISC_DATA_DIRECTORY=/iris/data` and mount the `idt-dev-data` volume there.

### 2. Physical Storage: Named Docker Volume
- **Decision**: Use a named Docker volume (`idt-dev-data`) instead of a host folder bind mount.
- **Rationale**: Named volumes are managed by Docker, avoiding UID 51773 (`irisowner`) permission conflicts common on macOS host folders.
- **Alternatives considered**: Host folder bind mount (`~/.idt/data`). Rejected due to permission complexity and cross-platform inconsistencies.

### 3. Project Isolation: Hashed Namespace
- **Decision**: Generate a project-specific namespace name by hashing the absolute directory path.
- **Rationale**: Ensures stable, unique isolation without user input.
- **Format**: `P` + `sha256(abspath)[:11]` (e.g., `P8F3A2B1C9D0`). This satisfies IRIS namespace naming rules (starts with letter, alphanumeric, length limits).

### 4. Readiness Check: Port-First
- **Decision**: Use a 50ms TCP port probe on `1972` as the primary readiness signal for `get_connection()`.
- **Rationale**: `docker exec` is too slow (> 200ms) for the "instant" SQLite-like feel. Port checks are < 50ms.

## Best Practices

- **Resource Stewardship**: Only one global `idt-dev-instance` container to minimize memory usage on the host.
- **Quiet Mode**: Use `detach=True` and avoid streaming logs unless requested via `idt dev logs`.
- **Cleanup**: Provide `idt dev down` to stop and remove the container while preserving the volume.

## Patterns

- **Lazy Initialization**: `get_connection()` checks if `idt-dev-instance` exists/is-running and starts it if missing (Implicit Start).
- **Auto-Discovery Integration**: `discover_config()` prioritizes the `idt-dev-instance` over environment variables or other containers.

## Rejected Alternatives (Principle #10)

### 1. Project-Specific Containers
- **Why rejected**: Creating a new container for every project is resource-intensive (CPU/RAM).
- **Failure mode**: On developer machines with multiple projects, Docker Desktop often hits resource limits or port 1972 conflicts.
- **SQLite comparison**: `sqlite3` doesn't spawn a background process per file; it uses a shared engine logic.

### 2. Host Folder Bind Mounts (~/.idt/data)
- **Why rejected**: macOS file permission synchronization (UID 51773 vs local user) is a frequent source of "Database Mount Failed" errors.
- **Failure mode**: If the host folder is deleted or has incorrect permissions, the IRIS container exits immediately with code 1.
