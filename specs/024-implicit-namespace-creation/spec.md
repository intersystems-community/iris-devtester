# Feature Specification: Implicit Namespace Creation

**Feature Branch**: `024-implicit-namespace-creation`  
**Created**: 2026-02-08  
**Status**: Draft  
**Input**: User description: "Implicit Namespace Creation: get_connection(namespace='NEW') should auto-create the namespace if it doesn't exist, just like SQLite creates the .db file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Zero-Friction New Namespace (Priority: P1)

As a developer, I want to connect to a new namespace without having to manually create the database and namespace in the IRIS Management Portal or via scripts first, so that my development flow is uninterrupted.

**Why this priority**: This is the core "SQLite-Level Ergonomics" vision. It removes the most significant remaining manual step in the developer experience.

**Independent Test**: Can be fully tested by calling `get_connection(namespace="UNIQUE_NEW_NS")` on a running IRIS instance where the namespace does not yet exist, and verifying that a valid connection object is returned and the namespace now exists.

**Acceptance Scenarios**:

1. **Given** a running IRIS container, **When** I call `get_connection(namespace="AUTO_CREATED")`, **Then** the namespace should be created automatically and I should receive a successful connection to it.
2. **Given** a running IRIS container, **When** I connect to an existing namespace like "USER", **Then** the connection should be established normally without any creation attempts.

---

### User Story 2 - Automated Test Isolation (Priority: P2)

As a test author, I want to use descriptive, unique namespace names for my test suites without managing their lifecycle explicitly, so that my tests are isolated and readable.

**Why this priority**: Facilitates better testing patterns by making isolation "free" and easy to use with descriptive names.

**Independent Test**: Create multiple connections to different non-existent namespaces in a loop and verify that each is created and isolated from the others.

**Acceptance Scenarios**:

1. **Given** no existing namespaces for a suite, **When** multiple tests request unique namespaces via `get_connection()`, **Then** each namespace is created independently and data remains isolated.

---

### Edge Cases

- **Invalid Names**: How does the system handle namespace names with invalid characters or that exceed length limits?
- **Read-Only Connections**: How does the system handle implicit creation if the user has read-only permissions on the IRIS instance?
- **Disk Space**: How does the system handle creation failure due to insufficient disk space on the IRIS instance?
- **Concurrent Creation**: What happens if two processes try to create the same namespace simultaneously?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST check for the existence of the requested namespace before attempting a connection.
- **FR-002**: System MUST automatically create a corresponding database and namespace if the requested one is missing.
- **FR-003**: System MUST configure the new namespace with standard defaults (Global and Routine mappings to the new database).
- **FR-004**: System MUST ensure the `%Service_CallIn` is enabled for the new namespace if required for the driver.
- **FR-005**: System MUST auto-create namespaces by default when connecting to `localhost` or local containers (Smart Default).
- **FR-007**: System MUST require explicit opt-in (`auto_create=True`) for non-local hosts to ensure production safety.
- **FR-008**: System MUST provide a clear, actionable error message if auto-creation fails (e.g., due to insufficient permissions or license limits).

### Key Entities *(include if feature involves data)*

- **Namespace**: A logical container in IRIS that maps to specific databases for globals and routines.
- **Database**: A physical `.dat` file on the IRIS file system where data is stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from "zero" to "connected to a new namespace" in a single function call.
- **SC-002**: Implicit namespace creation adds less than 3 seconds of overhead to the connection process.
- **SC-003**: No manual IRIS Management Portal or ObjectScript interaction is required for basic namespace setup.
- **SC-004**: The toolkit maintains its "Zero Configuration Viable" principle by handling the most common setup task automatically.
