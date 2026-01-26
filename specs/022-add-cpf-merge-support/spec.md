# Feature Specification: CPF Merge Support

**Feature Branch**: `022-add-cpf-merge-support`  
**Created**: 2026-01-05  
**Status**: Draft  
**Input**: User request for CPF tips/tricks and improved configuration.

## Clarifications

### Session 2026-01-05
- Q: How should the system handle multiple calls to with_cpf_merge? → A: Overwrite - each call replaces the previous configuration.
- Q: How should broken documentation links on the PyPI project page be fixed? → A: Absolute GitHub URLs - convert all relative links to absolute GitHub URLs to ensure they work on PyPI.
- Q: What should be the default port for IRIS Superserver in test configurations? → A: 1972.
- Q: Which library should be used for managing environment variables from files? → A: python-dotenv.
- Q: Should the library provide built-in presets for common IRIS optimizations? → A: Yes - provide constants/presets for common scenarios (CI optimization, standard service activation).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declarative Service Activation (Priority: P1)

An AI coding assistant setting up an environment for a project needs to enable the CallIn service automatically on container startup without writing extra Python logic or waiting for post-startup remediation. The agent uses the `with_cpf_merge` capability, which handles the file creation and mounting automatically.

**Why this priority**: Eliminates the "connect-fail-remediate-reconnect" latency cycle. Makes tests faster and more robust.

**Independent Test**:
1. Start a container with `with_cpf_merge("[Security.Services]\n%Service_CallIn=1,1,1,1,1,1,1,1,1,1,1,1,1,1")`.
2. Verify that `iris.connect()` (DBAPI) succeeds immediately without calling `enable_callin_service()`.

**Acceptance Scenarios**:
1. **Given** a CPF merge string, **When** `IRISContainer` starts, **Then** it must be correctly mounted and applied to the IRIS instance.
2. **Given** a path to an existing `.cpf` file, **When** passed to `with_cpf_merge`, **Then** the file must be mounted at the same internal path.

---

### User Story 2 - CI/CD Memory Optimization (Priority: P2)

As a DevOps engineer running IRIS in resource-constrained environments (like GitHub Actions), I want to scale down IRIS memory usage (Global Buffers, Heap) via CPF merge so that I can run more parallel test workers without crashing the host.

**Why this priority**: Enables high-concurrency testing which is essential for medical-grade reliability at scale.

**Acceptance Scenarios**:
1. **Given** a CPF merge setting `globals=0,0,128,0,0,0`, **When** IRIS starts, **Then** the `Config.Namespaces` API should confirm the smaller buffer size is active.

---

### User Story 3 - Pre-hashed Passwords (Priority: P3)

As a security-conscious developer, I want to provide a pre-hashed password in the CPF merge to avoid the "Password change required" state entirely.

**Why this priority**: Maximum "Zero Config" efficiency.

**Acceptance Scenarios**:
1. **Given** a `PasswordHash` entry in the CPF merge, **When** IRIS starts, **Then** the standard `SYS` password should be accepted immediately.

---

### Edge Cases

- **Invalid CPF Syntax**: What happens if the provided CPF content is malformed? (IRIS should still start but maybe log errors; library should probably validate basic section headers).
- **Concurrent Merges**: If `with_cpf_merge` is called multiple times, each call replaces the previous configuration (Overwrite).
- **Host Permissions**: Handling cases where the temporary file cannot be created or mounted due to host OS restrictions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `IRISContainer` MUST provide a `with_cpf_merge(path_or_content: str)` method.
- **FR-002**: System MUST support passing a filesystem path to an existing `.cpf` file.
- **FR-003**: System MUST support passing raw CPF string content (e.g., using triple quotes).
- **FR-004**: System MUST automatically manage temporary file lifecycle if raw content is provided (create before start, cleanup after stop).
- **FR-005**: System MUST automatically set the `ISC_CPF_MERGE_FILE` environment variable using `python-dotenv` for configuration management.
- **FR-006**: System MUST automatically mount the CPF file into the container.
- **FR-007**: System MUST convert all relative documentation links in `README.md` to absolute GitHub URLs for PyPI compatibility.
- **FR-008**: System MUST use 1972 as the default Superserver port unless specified otherwise.
- **FR-009**: System MUST provide built-in presets (e.g., `CPFPreset.CI_OPTIMIZED`, `CPFPreset.ENABLE_CALLIN`) for common InterSystems IRIS configurations.
- **FR-010**: System MUST expose CPF merge capability via the `iris-devtester container up` CLI command using a `--cpf` option.

### Key Entities

- **CPF Merge File**: A partial `.cpf` file containing specific sections (e.g., `[config]`, `[Security.Services]`) to be merged into the primary `iris.cpf`.
- **TempCPFManager**: An internal utility to handle the lifecycle of temporary configuration files.
- **CPFPreset**: A collection of predefined CPF snippets for common use cases.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Container startup time (to "Ready") decreases by ~2 seconds by avoiding post-startup ObjectScript remediation for CallIn.
- **SC-002**: Memory usage of the IRIS container can be reliably reduced to < 512MB using declarative config.
- **SC-003**: Zero "connect -> fail -> reset -> connect" cycles in the primary test loop when CPF is used.
- **SC-004**: 100% of documentation links on the PyPI project page are valid and clickable.

## Assumptions

- We are targeting IRIS 2019.4+ (when CPF Merge was introduced).
- Users have Docker installed and permissions to mount volumes.
- The `testcontainers` volume mounting API remains consistent.
- `python-dotenv` is available for managing environment variables.
