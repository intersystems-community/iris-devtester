# Feature Specification: The Dev Instance (Warm Start)

**Feature Branch**: `026-dev-instance`  
**Created**: 2026-02-08  
**Status**: Draft  
**Input**: User description: "The Dev Instance (Warm Start): A persistent IRIS container managed by idt that provides instant 'SQLite-like' connectivity. Includes 'idt dev' CLI commands and automatic detection in get_connection()."

## Clarifications

### Session 2026-02-08
- Q: Port Conflict Strategy → A: Auto-assign next available port
- Q: Project Identity Calculation → A: Hashed directory path
- Q: Data Persistence Implementation → A: Managed Volume (idt-dev-data)
- Q: Auto-Provisioning Behavior → A: Implicit Start (Auto-start engine on connection)
- Q: Default Engine Image → A: Community Edition (latest)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instant Connection (Priority: P1)

As a developer, I want to call `get_connection()` and get an immediate connection without waiting for a container to start, so that my development cycle is as fast as SQLite.

**Why this priority**: This is the core "SQLite Vision". Eliminating the 20-40s startup delay is the biggest remaining hurdle to a frictionless experience.

**Independent Test**:
1. Run `idt dev up` to start the dev instance.
2. In a Python script, call `get_connection()` without starting a container.
3. Verify connection is established in < 1 second.

**Acceptance Scenarios**:

1. **Given** a dev instance is running, **When** I call `get_connection()`, **Then** it should automatically discover and connect to the dev instance instantly.
2. **Given** no dev instance is running, **When** I call `get_connection()`, **Then** it should fallback to standard auto-discovery (existing behavior).

---

### User Story 2 - Managed Dev Instance Lifecycle (Priority: P2)

As a developer, I want a simple CLI to manage my persistent development IRIS instance, so that I don't have to remember complex Docker commands.

**Why this priority**: Provides the "Warm Start" capability via a simple, discoverable interface.

**Independent Test**: Run `idt dev status`, `idt dev up`, and `idt dev down` and verify the container state changes correctly.

**Acceptance Scenarios**:

1. **Given** no container exists, **When** I run `idt dev up`, **Then** a container named `idt-dev-instance` should be started with standard ports (1972, 52773).
2. **Given** the dev instance is running, **When** I run `idt dev status`, **Then** it should show "Running" and the connection details.

---

### User Story 3 - Automatic Readiness Optimization (Priority: P3)

As a user, I want the dev instance to use the absolute physical limit for readiness checks, so that even the first start is as fast as possible.

**Why this priority**: Improves the "Cold Start" experience.

**Acceptance Scenarios**:

1. **Given** a new dev instance starting, **When** it becomes ready, **Then** the toolkit should detect it immediately using optimized checks (e.g., port-first, then minimal ObjectScript).

---

### Edge Cases

- **Port Conflicts**: What happens if port 1972 is taken by another IRIS instance when running `idt dev up`?
  - **Resolution**: Use the toolkit's port management to **Auto-assign** the next available port. Auto-discovery will find the instance on its new port.
- **Instance Scoping**: How does the system handle multiple projects?
  - **Decision**: Use a **Global Engine / Project Data** split. One global `idt-dev-instance` container (the Engine) serves all projects, but each project gets an isolated Namespace and Database (the Data) based on its directory/name.
- **Concurrent Creation**: What happens if two processes try to create the same project namespace simultaneously?
- **Stale Instance**: How does the system handle a dev instance that is "Running" in Docker but the IRIS process inside has crashed?
- **Image Updates**: How does the user update the IRIS version used by the dev instance?
  - **Resolution**: Use **Community Edition (latest)** as the default engine image. Users can update or override via CLI flags (`idt dev up --image`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `idt dev` CLI commands (`up`, `down`, `status`, `logs`).
- **FR-002**: System MUST name the global engine container `idt-dev-instance`.
- **FR-003**: System MUST automatically detect, prefer, and (if necessary) implicitly start the `idt-dev-instance` during `get_connection()` or `discover_config()` to ensure zero-friction connectivity.
- **FR-004**: System MUST derive a unique Project ID by hashing the current absolute directory path to ensure stable, folder-specific isolation.
- **FR-005**: System MUST ensure project isolation by creating a Project-specific Namespace on the global engine.
- **FR-006**: System MUST ensure the dev instance is configured with standard credentials (`_SYSTEM`/`SYS`) and CallIn enabled.
- **FR-007**: System MUST support persistent storage by creating and managing a Docker volume named `idt-dev-data` to ensure data survives container lifecycle events.
- **FR-008**: System MUST provide an `IRISContainer.dev()` method to easily interact with the dev instance from code.

### Key Entities *(include if feature involves data)*

- **Dev Instance**: A persistent Docker container managed by the toolkit.
- **Persistent Volume**: A Docker volume used to store IRIS database files (`IRIS.DAT`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "Warm start" connection time (calling `get_connection()` when dev instance is running) is under 500ms.
- **SC-002**: A developer can start their environment with a single command: `idt dev up`.
- **SC-003**: Dev instance data persists across container restarts.
- **SC-004**: Zero manual Docker configuration required for the development environment.
