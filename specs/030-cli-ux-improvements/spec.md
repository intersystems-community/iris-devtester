# Feature Specification: CLI UX Improvements

**Feature Branch**: `030-cli-ux-improvements`
**Created**: 2026-03-28
**Status**: Draft
**Input**: Five CLI pain points from downstream consumer (objectscript-coder)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Password-Change Detection in test-connection (Priority: P1)

As a developer running `idt test-connection --container colbert-bench`, I need the command to detect when a DBAPI connection fails because IRIS requires a password change, instead of showing the cryptic message "Unexpected error: 1". It should tell me what went wrong and auto-offer to fix it.

**Why this priority**: Most common frustration. Fresh community containers always hit this. Users waste 15+ minutes debugging a message that says nothing useful.

**Independent Test**: Start a fresh community container without unexpiring passwords, run `idt test-connection`, verify it prints a specific password-change message and suggests `idt container reset-password`.

**Acceptance Scenarios**:

1. **Given** a container where `ChangePassword=1` for `_SYSTEM`, **When** I run `idt test-connection --container <name>`, **Then** the output includes "Password change required" and suggests running `idt container reset-password <name>`.
2. **Given** a container where `ChangePassword=1`, **When** I run `idt test-connection --container <name> --auto-fix`, **Then** the command automatically calls `reset_password()` and retries the connection.
3. **Given** a healthy container with no password issues, **When** I run `idt test-connection`, **Then** behavior is unchanged (no regression).
4. **Given** a container where connection fails for a non-password reason (port closed, container stopped), **When** I run `idt test-connection`, **Then** the existing error messages are preserved.

---

### User Story 2 — reset-password --timeout Flag (Priority: P1)

As a CI pipeline operator, I need `idt container reset-password` to accept a `--timeout` flag so I can fail fast (or wait longer) instead of the command hanging indefinitely when IRIS is unresponsive.

**Why this priority**: Hangs block CI pipelines. The underlying function already has a `timeout` parameter but the CLI doesn't expose it. Simplest fix with highest impact.

**Independent Test**: Run `idt container reset-password <name> --timeout 5` against a stopped container, verify it exits within ~5 seconds with a timeout error.

**Acceptance Scenarios**:

1. **Given** a stopped container, **When** I run `idt container reset-password <name> --timeout 5`, **Then** the command exits with an error within 10 seconds (5s timeout + overhead).
2. **Given** a healthy container, **When** I run `idt container reset-password <name> --timeout 30`, **Then** the password resets successfully as before.
3. **Given** no `--timeout` flag provided, **When** I run `idt container reset-password <name>`, **Then** the default timeout is 30 seconds (backward compatible).

---

### User Story 3 — container up --port (Priority: P2)

As a developer, I need `idt container up --port 1972` to map the IRIS SuperServer to a specific host port, instead of being limited to `--auto-port` which assigns an arbitrary port from the range.

**Why this priority**: Common need for reproducible dev environments. Developers want `idt container up --port 51773` to match their IDE config. The `--auto-port` flag exists but you can't say "use exactly this port".

**Independent Test**: Run `idt container up --port 11972`, verify the container's host-side port mapping is exactly 11972.

**Acceptance Scenarios**:

1. **Given** port 11972 is free, **When** I run `idt container up --port 11972`, **Then** the container maps 1972→11972.
2. **Given** port 11972 is already in use, **When** I run `idt container up --port 11972`, **Then** the command fails with a clear "port in use" error and suggests `--auto-port`.
3. **Given** both `--port` and `--auto-port` are specified, **When** I run the command, **Then** it errors with "cannot use --port and --auto-port together".
4. **Given** no port flags, **When** I run `idt container up`, **Then** behavior is unchanged (defaults to 1972 mapping).

---

### User Story 4 — container exec Command (Priority: P2)

As a developer, I need `idt container exec <name> <command>` to run commands inside a container without falling back to raw `docker exec`. For ObjectScript specifically, I need `idt container exec <name> --objectscript "Write $ZVERSION"`.

**Why this priority**: Every user eventually needs to run something inside the container. The infrastructure exists (`execute_objectscript()` on `IRISContainer`) but has no CLI surface.

**Independent Test**: Run `idt container exec <name> --objectscript "Write 1+1"`, verify output includes "2".

**Acceptance Scenarios**:

1. **Given** a running container, **When** I run `idt container exec <name> --objectscript "Write $ZVERSION"`, **Then** the IRIS version string is printed to stdout.
2. **Given** a running container, **When** I run `idt container exec <name> -- ls /`, **Then** the container's root directory listing is printed.
3. **Given** a running container, **When** I run `idt container exec <name> --objectscript "Write 1+1" --namespace MYAPP`, **Then** the command runs in the MYAPP namespace.
4. **Given** a stopped container, **When** I run `idt container exec <name> --objectscript "Write 1"`, **Then** a clear error is printed.
5. **Given** a running container, **When** I run `idt container exec <name> --objectscript "..." --timeout 5`, **Then** the command times out after 5 seconds if IRIS hangs.

---

### User Story 5 — test-connection Shows Credentials (Priority: P3)

As a developer debugging auth failures, I need `idt test-connection` to print which password it's using, so I can verify the right credentials are being attempted.

**Why this priority**: Low effort, helpful for debugging. Both `test-connection` commands already print username but hide the password.

**Independent Test**: Run `idt test-connection --container <name>`, verify output includes "Password: SYS" (or masked version).

**Acceptance Scenarios**:

1. **Given** default credentials, **When** I run `idt test-connection`, **Then** the output includes `Password: S***` (masked by default).
2. **Given** default credentials, **When** I run `idt test-connection -v`, **Then** the output includes `Password: SYS` (full in verbose mode).
3. **Given** explicit credentials `--password MyPass`, **When** I run `idt test-connection --password MyPass`, **Then** the output shows `Password: M*****` (masked).

---

### Edge Cases

- What if IRIS returns error code `1` for a non-password-change reason? Detection should check the full error message string, not just the code.
- What if `--port` conflicts with a port reserved in the port registry? Should consult the registry before binding.
- What if `container exec --objectscript` receives multi-line input? Should handle here-doc style input from stdin.
- What if the password contains special characters? Masking and display should handle any UTF-8 string.

## Clarifications

### Session 2026-03-28

- Q: Two test-connection commands exist — apply fixes to both or one? → A: Deprecate `idt container test-connection`, consolidate into top-level `idt test-connection` which already has `--container` flag.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `idt test-connection` MUST detect password-change-required errors and print a specific remediation message naming the `reset-password` command.
- **FR-002**: `idt test-connection` MUST support an `--auto-fix` flag that automatically calls `reset_password()` and retries on password-change errors.
- **FR-003**: `idt container reset-password` MUST accept `--timeout <seconds>` with a default of 30 seconds.
- **FR-004**: The `timeout` parameter in `reset_password()` MUST control the subprocess timeout for the docker exec call (not be ignored).
- **FR-005**: `idt container up` MUST accept `--port <int>` to set an exact host-side port mapping.
- **FR-006**: `--port` and `--auto-port` MUST be mutually exclusive with a clear error if both are provided.
- **FR-007**: `idt container exec` MUST accept a container name and either `--objectscript <code>` or a raw shell command via `--`.
- **FR-008**: `idt container exec` MUST support `--namespace` (default: USER) and `--timeout` (default: 30).
- **FR-009**: `idt test-connection` MUST print the password being used, masked by default, full in verbose mode.
- **FR-010**: All existing tests MUST continue to pass.
- **FR-011**: `idt container test-connection` MUST be deprecated — print a deprecation warning directing users to `idt test-connection --container <name>`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "Unexpected error: 1" never appears for password-change failures — replaced with actionable message.
- **SC-002**: `reset-password` with `--timeout 5` against a stopped container exits within 10 seconds.
- **SC-003**: `container up --port 11972` creates a container with host port 11972 mapped to container port 1972.
- **SC-004**: `container exec <name> --objectscript "Write 1+1"` prints output containing "2".
- **SC-005**: `test-connection` output includes a "Password:" line in all modes.
