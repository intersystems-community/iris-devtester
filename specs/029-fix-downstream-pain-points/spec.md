# Feature Specification: Fix Downstream Consumer Pain Points

**Feature Branch**: `029-fix-downstream-pain-points`
**Created**: 2026-03-28
**Status**: Draft
**Input**: User description: "Fix three downstream consumer pain points reported by objectscript-coder: (1) no public get_password() on IRISContainer, (2) with_preconfigured_password() doesn't clear ChangePassword flag, (3) Ryuk lifecycle not obvious from API"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Public Password Accessor (Priority: P1)

As a downstream library author, I need to read the password configured on an IRISContainer instance so I can construct my own connections or pass credentials to other tools, without reaching into private attributes.

**Why this priority**: Simplest fix, unblocks the most consumers. Every downstream project currently accesses `iris._password` directly — fragile and violates encapsulation.

**Independent Test**: Call `iris.get_password()` on a configured IRISContainer and verify it returns the configured password string.

**Acceptance Scenarios**:

1. **Given** an IRISContainer created with default credentials, **When** I call `iris.get_password()`, **Then** it returns `"SYS"`.
2. **Given** an IRISContainer created with `.with_credentials("_SYSTEM", "MyPass")`, **When** I call `iris.get_password()`, **Then** it returns `"MyPass"`.
3. **Given** an IRISContainer where `reset_password()` was called with `new_password="Changed"`, **When** I call `iris.get_password()`, **Then** it returns `"Changed"`.
4. **Given** an IRISContainer created with `.with_preconfigured_password("PreConf")`, **When** I call `iris.get_password()`, **Then** it returns `"PreConf"`.

---

### User Story 2 — Preconfigured Password Clears ChangePassword Flag (Priority: P1)

As a developer using iris-devtester in CI/CD, I need `with_preconfigured_password()` to result in a container where DBAPI connections work immediately, without hitting "password change required" errors.

**Why this priority**: Most frequently reported pain point. Causes auth failures in CI pipelines and wastes debugging time.

**Independent Test**: Start a community container with `with_preconfigured_password("SYS")`, then connect via DBAPI without any additional password reset calls. Connection must succeed.

**Acceptance Scenarios**:

1. **Given** a fresh community container started with `.with_preconfigured_password("SYS")`, **When** I call `get_connection()`, **Then** the connection succeeds without any auth error.
2. **Given** a fresh community container started with `.with_preconfigured_password("SYS")`, **When** the container's `start()` method completes, **Then** the `ChangePassword` flag for `_SYSTEM` is `0` in the IRIS security database.
3. **Given** a fresh community container started without `with_preconfigured_password()`, **When** `start()` completes, **Then** `unexpire_all_passwords()` is still called (existing behavior preserved).

---

### User Story 3 — Container Persistence Guidance (Priority: P2)

As a developer who needs containers to persist beyond process exit, I need clear API guidance so I can use the `idt container up` + `IRISContainer.attach()` pattern without discovering it through trial and error.

**Why this priority**: Important for developer experience but doesn't block functionality — the pattern already works, it's just not discoverable.

**Independent Test**: Verify that `IRISContainer.attach()` docstring and class-level docstring explain the Ryuk lifecycle and when to use `attach()` vs context manager.

**Acceptance Scenarios**:

1. **Given** the `IRISContainer` class, **When** I read its class docstring, **Then** it explains that containers created via Python are cleaned up by Ryuk on process exit and directs me to `attach()` + CLI for persistent containers.
2. **Given** the `IRISContainer.attach()` method, **When** I read its docstring, **Then** it explains that this reconnects to a container started by `idt container up` (which is Ryuk-free).
3. **Given** the `IRISContainer.community()` factory, **When** I read its docstring, **Then** it includes a note that the container will be removed when the process exits (Ryuk behavior).

---

### Edge Cases

- `get_password()` called before container start returns configured password (no start required).
- `unexpire_all_passwords()` failure during `start()` is handled by existing retry logic; failure mode documented.
- `attach()` with nonexistent container name raises existing error; docstring mentions this.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `IRISContainer` MUST expose a public `get_password()` method returning the currently configured password as a string.
- **FR-002**: `IRISContainer` MUST expose a public `get_username()` method returning the currently configured username as a string.
- **FR-003**: `IRISContainer.start()` MUST ensure `ChangePassword=0` for all users when `with_preconfigured_password()` was used.
- **FR-004**: `IRISContainer.start()` MUST call `unexpire_all_passwords()` after the container is healthy, regardless of whether `with_preconfigured_password()` was used (preserve existing behavior).
- **FR-005**: `IRISContainer` class docstring MUST document Ryuk lifecycle behavior and the persistent container pattern.
- **FR-006**: `IRISContainer.attach()` docstring MUST explain when and why to use it (reconnect to CLI-managed containers).
- **FR-007**: `IRISContainer.community()`, `.enterprise()`, `.light()` factory docstrings MUST include a note about Ryuk cleanup on process exit.
- **FR-008**: All existing tests MUST continue to pass (no regressions).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Downstream consumers can access password via public API (`get_password()`) instead of private attribute.
- **SC-002**: A fresh community container started with `with_preconfigured_password()` accepts DBAPI connections within 5 seconds of `start()` completing, without additional password reset calls.
- **SC-003**: `help(IRISContainer)` output explains Ryuk lifecycle in the first paragraph of the class docstring.
- **SC-004**: All existing unit, contract, and integration tests pass without modification.
