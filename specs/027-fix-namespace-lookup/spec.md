# Feature Specification: Fix Namespace Auto-Creation Container Lookup

**Feature Branch**: `027-fix-namespace-lookup`  
**Created**: 2026-02-27  
**Status**: Draft  
**Input**: User description: "Namespace auto-creation attempts container lookup even when explicit IRISConfig is provided. When get_connection(config=IRISConfig(host=..., port=..., namespace='USER')) is called with an explicit config pointing to a running named container, the namespace auto-creation logic still attempts to find a Docker container named iris_db and logs an error when it doesn't exist."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Connection with Explicit Config (Priority: P1)

As a developer using `iris-devtester`, when I call `get_connection()` with an explicit `IRISConfig` specifying host, port, and namespace, I expect no spurious Docker container lookups or error messages in my logs. The connection should proceed cleanly using only the information I provided.

**Why this priority**: This is the primary reported bug. Noisy error logs erode trust in the toolkit and can mask real failures, especially in CI/CD pipelines where log noise triggers false alarms.

**Independent Test**: Can be fully tested by calling `get_connection(config=IRISConfig(host="localhost", port=1972, namespace="USER"))` when no container named `iris_db` exists, and verifying that no Docker-related errors appear in the log output.

**Acceptance Scenarios**:

1. **Given** an explicit `IRISConfig` with host, port, and namespace pointing to a reachable IRIS instance, **When** `get_connection(config)` is called, **Then** the connection succeeds without any Docker container lookup errors in the logs.
2. **Given** an explicit `IRISConfig` with `host="localhost"` and no `container_name` set, **When** `get_connection(config)` is called, **Then** namespace auto-creation does NOT default to looking up a container named `iris_db`.
3. **Given** an explicit `IRISConfig` with `host="localhost"` and no `container_name` set, **When** the specified namespace already exists on the target IRIS instance, **Then** the connection succeeds silently with no namespace-related log messages at INFO level or above.

---

### User Story 2 - Programmatic Namespace Verification for Explicit Configs (Priority: P2)

As a developer connecting to a known IRIS instance, when the toolkit needs to verify whether a namespace exists, it should use `iris.connect()` to the `%SYS` namespace rather than Docker exec commands. This enables namespace checking on remote hosts and containers with non-default names.

**Why this priority**: Provides a robust alternative to Docker-exec-based namespace checking. Enables the toolkit to work correctly with any reachable IRIS instance, not just locally-named Docker containers.

**Independent Test**: Can be tested by connecting to an IRIS instance via explicit host/port and verifying that namespace existence is checked via `iris.connect()` to `%SYS` rather than `docker exec`.

**Acceptance Scenarios**:

1. **Given** an explicit `IRISConfig` without a `container_name`, **When** namespace auto-creation is triggered, **Then** the system checks namespace existence using `iris.connect()` to `%SYS` rather than Docker exec.
2. **Given** an explicit `IRISConfig` pointing to a remote IRIS host, **When** namespace auto-creation is enabled, **Then** namespace existence is verified via `iris.connect()` without requiring Docker access to the remote host.

---

### User Story 3 - Preserve Docker-Based Auto-Creation for Discovered Configs (Priority: P3)

As a developer using auto-discovered configuration (no explicit config), the existing Docker-exec-based namespace auto-creation behavior should continue to work as it does today, so that the zero-config experience is preserved.

**Why this priority**: Backward compatibility. The existing auto-discovery flow correctly identifies the container name and should continue using Docker exec for namespace operations when it has reliable container information.

**Independent Test**: Can be tested by calling `get_connection()` with no arguments when a Docker container is running, and verifying namespace auto-creation still works via Docker exec as before.

**Acceptance Scenarios**:

1. **Given** no explicit config and a running IRIS Docker container, **When** `get_connection()` is called with a namespace that doesn't exist, **Then** the system auto-discovers the container and creates the namespace via Docker exec (existing behavior preserved).
2. **Given** auto-discovered config with a known `container_name`, **When** namespace auto-creation runs, **Then** Docker exec is used against the correctly discovered container name (not hardcoded `iris_db`).

---

### Edge Cases

- What happens when an explicit config has `host="localhost"` but the IRIS instance is not running? The connection should fail with a clear connection error, not a misleading Docker container error.
- What happens when an explicit config includes a `container_name`? Docker-exec-based namespace operations should use that specific container name.
- What happens when namespace auto-creation via `iris.connect()` fails due to insufficient permissions? The system should log a clear warning and allow the connection attempt to proceed (the namespace may already exist).
- What happens when `auto_create` is explicitly set to `False` in the config? Namespace auto-creation should be skipped entirely regardless of host or container settings.
- What happens when `auto_create` is explicitly set to `True` but no `container_name` is provided and the host is localhost? The system should attempt `iris.connect()`-based namespace verification rather than defaulting to `iris_db`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST NOT perform Docker container lookups when an explicit `IRISConfig` is provided without a `container_name`, regardless of the host value.
- **FR-002**: System MUST support programmatic namespace existence checking via `iris.connect()` as an alternative to Docker exec. The check MUST bootstrap by connecting to the `%SYS` namespace first to query namespace metadata, then reconnect to the target namespace if it exists. The check MUST use the same credentials from the user's `IRISConfig`; if `%SYS` access is denied, the check fails gracefully and the connection attempt proceeds (per FR-007).
- **FR-003**: System MUST preserve existing Docker-exec-based namespace auto-creation when config is auto-discovered with a known container name.
- **FR-004**: System MUST NOT fall back to a hardcoded container name (e.g., `iris_db`) when no `container_name` is available in the config.
- **FR-005**: System MUST log clear, accurate messages when namespace operations fail, distinguishing between "no container available for Docker exec" and "namespace does not exist."
- **FR-006**: System MUST respect the `auto_create` config flag: `False` skips all namespace operations, `True` attempts creation, `None` uses the existing smart default logic (but without hardcoded container fallback).
- **FR-007**: System MUST allow the connection attempt to proceed even if namespace verification/creation fails, since the namespace may already exist on the target instance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Calling `get_connection()` with an explicit config produces zero Docker-related error messages in logs when no `container_name` is specified.
- **SC-002**: All existing unit and integration tests continue to pass without modification (backward compatibility).
- **SC-003**: Namespace existence can be verified programmatically via `iris.connect()` on any reachable IRIS instance, not just local Docker containers.
- **SC-004**: Log output during connection establishment contains only relevant, actionable messages -- no misleading "No such container" errors when the connection subsequently succeeds.

## Clarifications

### Session 2026-02-27

- Q: How should the namespace check bootstrap its connection? → A: Connect to `%SYS` namespace first via `iris.connect()`, check namespace existence via `Config.Namespaces.Exists()`, then reconnect to target namespace.
- Q: What credentials should the namespace check use when connecting to `%SYS`? → A: Use same credentials from user's `IRISConfig`; fail gracefully if `%SYS` access denied.

## Assumptions

- The `iris.connect()` API supports calling `Config.Namespaces.Exists()` and `Config.Namespaces.Create()` via `classMethodValue` when connected to the `%SYS` namespace.
- Users who provide an explicit `IRISConfig` with host/port expect the toolkit to use network-level communication, not Docker exec.
- The existing `auto_create=None` smart default (localhost=True, remote=False) is a reasonable heuristic and should be preserved, but its implementation should not depend on hardcoded container names.
- The `iris_db` default container name is an artifact of early development and should be removed from the namespace auto-creation path (other utility functions that use it are out of scope for this fix).
