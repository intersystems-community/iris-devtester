# Feature Specification: Pre-configure Passwords at Container Startup

**Feature Branch**: `001-preconfigure-passwords`  
**Created**: 2026-01-24  
**Status**: Draft  
**Input**: User description: "Pre-configure Passwords to Skip Manual Steps: Supply non-default password to IRIS at container startup using environment variables to avoid password change blocks and save 5-10 seconds of startup time"

## Clarifications

### Session 2026-01-24

- Q: Should pre-configuration require an explicit opt-in flag, or activate automatically when credentials are provided? → A: Automatic activation - pre-configure when `IRIS_PASSWORD` or programmatic API is used, no extra flag needed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Container Startup with Pre-configured Credentials (Priority: P1)

As a developer running automated tests, I want IRIS containers to start with my credentials already configured so that I don't have to wait for post-startup password reset operations.

**Why this priority**: This is the core value proposition - eliminating the 5-10 second "Hardening user accounts..." delay on every container startup. This directly impacts developer productivity and CI/CD pipeline speed.

**Independent Test**: Can be fully tested by starting a container with pre-configured credentials and verifying immediate connection without password reset. Delivers immediate value by reducing container startup time.

**Acceptance Scenarios**:

1. **Given** a developer configures `IRIS_PASSWORD=MySecretPass` environment variable, **When** the IRIS container starts, **Then** connections using that password succeed immediately without any password reset step.

2. **Given** a developer configures both `IRIS_USERNAME=dev` and `IRIS_PASSWORD=MySecretPass`, **When** the IRIS container starts, **Then** the specified user can authenticate immediately with the provided password.

3. **Given** pre-configured credentials are provided, **When** the container startup completes, **Then** the total startup time is reduced by at least 3 seconds compared to the current post-startup password reset approach.

---

### User Story 2 - Backward Compatible Default Behavior (Priority: P1)

As an existing user of iris-devtester, I want the library to continue working with my current configuration so that upgrading doesn't break my existing tests.

**Why this priority**: Breaking existing functionality would cause user frustration and adoption barriers. Both P1 stories must be implemented together for a viable release.

**Independent Test**: Can be tested by running existing test suites without any configuration changes and verifying they pass identically to before.

**Acceptance Scenarios**:

1. **Given** no password pre-configuration environment variables are set, **When** IRISContainer starts, **Then** the existing password reset mechanism continues to work as before.

2. **Given** existing code uses `IRISContainer.community()` without any changes, **When** the container starts, **Then** connections succeed using the default credentials (_SYSTEM/SYS).

---

### User Story 3 - Explicit Opt-in for Password Pre-configuration (Priority: P2)

As a developer, I want to explicitly enable password pre-configuration in my container setup so that I have clear control over how credentials are handled.

**Why this priority**: Provides a programmatic API for the feature, complementing the environment variable approach. Less critical than the core functionality but improves developer experience.

**Independent Test**: Can be tested by using the new API method to configure passwords and verifying immediate authentication.

**Acceptance Scenarios**:

1. **Given** a developer uses `IRISContainer.with_preconfigured_password("MyPass")`, **When** the container starts, **Then** the password is pre-configured and connections succeed immediately.

2. **Given** a developer uses `IRISContainer.with_credentials(username="dev", password="MyPass")`, **When** the container starts, **Then** both username and password are pre-configured.

---

### User Story 4 - CI/CD Pipeline Optimization (Priority: P3)

As a CI/CD pipeline maintainer, I want to configure IRIS credentials through pipeline environment variables so that I can standardize container setup across all jobs.

**Why this priority**: Extends the feature to common CI/CD use cases. Lower priority because P1/P2 already enable this via environment variables.

**Independent Test**: Can be tested by setting environment variables in a CI context and verifying container starts with pre-configured credentials.

**Acceptance Scenarios**:

1. **Given** CI/CD environment sets `IRIS_PASSWORD=MySecretPass`, **When** the test container starts, **Then** password pre-configuration is used automatically (no additional opt-in flag required).

---

### Edge Cases

- What happens when the IRIS image version doesn't support password pre-configuration environment variables?
  - System should detect unsupported images and fall back to the existing password reset mechanism with a warning.

- How does the system handle invalid password values (empty, too short, special characters)?
  - IRIS password validation rules should be checked before passing to container; invalid passwords should produce clear error messages before startup.

- What happens if both environment variable and programmatic API are used with conflicting values?
  - Programmatic API takes precedence over environment variables (explicit > implicit).

- What if the container starts but password pre-configuration silently fails?
  - System should verify password works immediately after container readiness and fall back to password reset if needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically use password pre-configuration when `IRIS_PASSWORD` environment variable is set (no additional opt-in flag required).

- **FR-002**: System MUST support `IRIS_USERNAME` environment variable to specify which user receives the pre-configured password.

- **FR-003**: System MUST pass pre-configuration environment variables to the underlying Docker container when starting IRIS.

- **FR-004**: System MUST fall back to the existing password reset mechanism when password pre-configuration is not enabled or fails.

- **FR-005**: System MUST provide a programmatic API (`with_preconfigured_password()` or similar) for explicitly enabling password pre-configuration.

- **FR-006**: System MUST skip the "Hardening user accounts..." step when password pre-configuration succeeds.

- **FR-007**: System MUST verify that pre-configured credentials work immediately after container startup, before returning control to the caller.

- **FR-008**: System MUST log informational messages indicating whether password pre-configuration or traditional reset was used.

- **FR-009**: System MUST maintain backward compatibility - existing code without password pre-configuration must continue to function identically.

- **FR-010**: System MUST detect IRIS image versions that don't support password pre-configuration and automatically fall back to the existing mechanism.

### Key Entities

- **IRISContainer**: Extended with password pre-configuration capability and new configuration options.
- **ContainerConfig**: Extended with fields for pre-configured credentials and pre-configuration enabled flag.
- **Password Pre-configuration State**: Tracks whether pre-configuration was attempted, succeeded, or fell back to reset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Container startup time is reduced by at least 3 seconds when password pre-configuration is enabled compared to the current password reset approach.

- **SC-002**: 100% of existing tests pass without modification when password pre-configuration is not explicitly enabled.

- **SC-003**: Developers can establish a working database connection within 2 seconds of container readiness when using pre-configured passwords.

- **SC-004**: The system correctly falls back to password reset in 100% of cases where pre-configuration fails or is unsupported.

- **SC-005**: Documentation and error messages clearly explain how to enable password pre-configuration and troubleshoot issues.

## Assumptions

- InterSystems IRIS Community Edition containers (from Docker Hub) support `IRIS_PASSWORD` and `IRIS_USERNAME` environment variables for initial credential setup. This is documented in official InterSystems documentation.

- The `--password-file` option exists as an alternative but is more complex; environment variables are the preferred approach for simplicity.

- Older IRIS container images may not support password pre-configuration; the system must gracefully handle this.

- The existing password reset mechanism will remain as a fallback and for users who prefer the current behavior.

## Dependencies

- Docker container environment variable support
- InterSystems IRIS container image with password pre-configuration support (Community Edition on Docker Hub)
- Existing `testcontainers-iris-python` library integration
