# Data Model: The Dev Instance

## Entities

### 1. DevInstance (Managed Container)
The core persistent engine that runs in the background.

| Field | Type | Description |
|-------|------|-------------|
| container_name | string | "idt-dev-instance" (Fixed) |
| image | string | Default: "intersystemsdc/iris-community:latest" |
| volume_name | string | "idt-dev-data" |
| superserver_port | int | Default: 1972 (with auto-assign fallback) |
| status | enum | CREATED, STARTING, RUNNING, STOPPED, EXITED |

**Validation Rules**:
- Only one instance with this name can exist globally on the host.
- Must use `irisowner` (UID 51773) for all internal operations.

### 2. ProjectContext (Isolation Layer)
Derived context for the current project directory.

| Field | Type | Description |
|-------|------|-------------|
| project_path | string | Absolute path to the current working directory. |
| project_id | string | SHA256 hash of project_path (truncated to 11 chars). |
| namespace | string | "P" + project_id (e.g., "P8F3A2B1C9D"). |

**State Transitions**:
- **Connection**: Check if `namespace` exists on `DevInstance` → Create if missing → Return connection.

## Relationships

- **DevInstance** (1) ↔ (N) **ProjectContext**: A single global engine manages multiple isolated project namespaces.
- **DevInstance** (1) ↔ (1) **DurableVolume**: The engine persists all system and user data into a single managed Docker volume.
