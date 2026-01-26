# Feature Specification: Fix pgwire-identified bugs in iris-devtester

**Feature Branch**: `020-fix-pgwire-issues`  
**Created**: 2026-01-02  
**Status**: Draft  
**Input**: User description: "Fix bugs found by iris-pgwire research: password reset hardcoding, security flag reliability, wait strategy race condition, and namespace mounting logic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect as non-_SYSTEM user with auto-remediation (Priority: P1)

As a developer using `iris-devtester` to test applications that connect as `SuperUser` or other non-default users, I want the auto-remediation (password reset) to work for the user I'm actually connecting with, so that I don't get "Password change required" errors.

**Why this priority**: Core connectivity is the foundation of the tool. If auto-remediation only works for `_SYSTEM`, the tool fails for any enterprise or specific-user scenarios.

**Independent Test**: Can be fully tested by attempting a connection as `SuperUser` to a fresh IRIS container and verifying that `reset_password_if_needed` correctly identifies and fixes the "Password change required" state for that specific user.

**Acceptance Scenarios**:

1. **Given** a fresh IRIS container where `SuperUser` requires a password change, **When** `get_connection(username="SuperUser")` is called, **Then** it should successfully reset the password for `SuperUser` and establish a connection.
2. **Given** a call to `reset_password_if_needed(username="CustomUser")`, **When** the security flag is set for `CustomUser`, **Then** it should invoke `reset_password` for `CustomUser` specifically.

---

### User Story 2 - Reliable Security Flag Management (Priority: P1)

As a developer, I want my password resets to be permanent and reliable in Docker, so that my test suites don't intermittently fail with "Password change required" after I thought I already fixed it.

**Why this priority**: Intermittent test failures (flakiness) destroy developer trust in the testing infrastructure.

**Independent Test**: Can be tested by running consecutive container starts and password resets using the new `Security.Users.Modify` API and verifying 100% success rate without transient failures.

**Acceptance Scenarios**:

1. **Given** a container requiring password change, **When** the reset logic uses `##class(Security.Users).Modify(username, .props)`, **Then** the `ChangePassword` flag must be cleared immediately and permanently.

---

### User Story 3 - Deterministic Container Readiness (Priority: P1)

As a developer, I want the "Ready" signal from my IRIS container to guarantee that the security system is initialized, so that my first test query doesn't fail with a connection error.

**Why this priority**: Prevents race conditions at startup which cause confusing initial test failures.

**Independent Test**: Can be tested by attempting a connection immediately after the `WaitStrategy` signals success and verifying the connection is accepted and authenticated.

**Acceptance Scenarios**:

1. **Given** an IRIS container starting up, **When** port 1972 is open but IRIS internal systems are still initializing, **Then** the `IRISReadyWaitStrategy` should continue waiting.
2. **Given** an IRIS container, **When** `iris list` or a simple SQL query inside the container succeeds, **Then** the `IRISReadyWaitStrategy` should signal success.

---

### User Story 4 - Refreshable Test Data (Priority: P2)

As a developer, I want to be able to reload fixtures into an existing namespace (like `USER`), so that I can reset my test data between runs without manually destroying and recreating the entire container or namespace.

**Why this priority**: Essential for iterative development and long-running test environments where container reuse is preferred for speed.

**Independent Test**: Can be tested by loading a fixture twice into the same namespace and verifying that the second load either updates or replaces the existing data.

**Acceptance Scenarios**:

1. **Given** a namespace `USER` already exists, **When** `load_fixture(namespace="USER")` is called, **Then** it should not skip execution but instead refresh the data.

---

### User Story 5 - Project Dogfooding (Priority: P1)

As a maintainer of `iris-devtester`, I want the repository's own test suite to use the high-level APIs provided by the library, so that we validate our own fixes and provide better examples for users.

**Why this priority**: Crucial for validating that the "medical-grade" readiness and connection logic actually works in practice and simplifies test code.

**Independent Test**: Remove all manual `time.sleep()` and `enable_callin_service()` calls from `tests/conftest.py` and verify that the full test suite still passes reliably.

**Acceptance Scenarios**:

1. **Given** the updated `IRISContainer` and `WaitStrategy`, **When** the `iris_db` fixture starts a container, **Then** it should not require manual settle delays to establish a connection.

---

### Edge Cases

- What happens if the `Security.Users.Modify` API is called for a user that doesn't exist? (Should fail gracefully or create user if intended).
- What if `iris list` hangs inside the container during the wait strategy? (Should respect timeout).
- What if the namespace being refreshed is currently in use by an active connection? (Should handle or warn).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `reset_password_if_needed` MUST accept an optional `username` parameter (defaulting to `_SYSTEM`).
- **FR-002**: Password reset logic MUST use `##class(Security.Users).Modify(username, .props)` instead of `%Save()` for IRIS 2024.1+ (or as a general improvement).
- **FR-003**: `IRISReadyWaitStrategy` MUST verify IRIS application readiness (e.g., via `iris list` or internal command) in addition to port 1972.
- **FR-004**: `DATFixtureLoader.load_fixture` MUST support loading into existing namespaces, optionally clearing existing data first.
- **FR-005**: Password reset MUST clear the `ChangePassword` flag reliably using the recommended Security API.
- **FR-006**: System MUST refactor its own test fixtures in `tests/conftest.py` to use high-level library APIs (dogfooding).

### Key Entities *(include if feature involves data)*

- **WaitStrategy**: The logic used to determine when an IRIS container is ready for work.
- **FixtureLoader**: The component responsible for populating namespaces with test data.
- **Auto-Remediation**: The system that detects and fixes common IRIS connectivity issues like expired passwords.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% successful connections as `SuperUser` on fresh containers with auto-remediation enabled.
- **SC-002**: Zero "Password change required" errors encountered after a successful `reset_password` call.
- **SC-003**: `WaitStrategy` success signal correlates with 100% connection acceptance rate.
- **SC-004**: Fixtures can be re-loaded into existing `USER` namespace without manual intervention.

## Assumptions

- We are targeting IRIS 2024.1+ compatibility while maintaining backward compatibility.
- `iris list` is available in the target container images.
- We have the necessary permissions to execute `Security.Users` methods.
