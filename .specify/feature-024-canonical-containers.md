# Feature Specification: Canonical Container Editions

**Feature Branch**: `024-canonical-containers`  
**Created**: 2026-02-01  
**Status**: Draft  
**Input**: User description: "3 canonical containers built in as defaults: Community, Enterprise, Light"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Community Edition Quick Start (Priority: P1)

Developer wants to quickly spin up an IRIS container for local development or testing without worrying about architecture differences (ARM64 vs x86).

**Why this priority**: Most common use case - 90%+ of users will use Community edition for development and testing.

**Independent Test**: Can be fully tested by running `IRISContainer.community()` on both ARM64 and x86 machines and verifying correct image is pulled.

**Acceptance Scenarios**:

1. **Given** developer on ARM64 Mac, **When** they call `IRISContainer.community()`, **Then** correct ARM64-compatible image is pulled from `containers.intersystems.com`
2. **Given** developer on x86 Linux, **When** they call `IRISContainer.community()`, **Then** correct x86 image is pulled from `intersystemsdc/iris-community`
3. **Given** developer wants specific version, **When** they call `IRISContainer.community(version="2025.1")`, **Then** that specific version is used
4. **Given** developer uses CLI, **When** they run `iris-devtester container up --edition community`, **Then** correct architecture image is used

---

### User Story 2 - Enterprise Edition with License (Priority: P2)

Developer needs to test with Enterprise features (advanced security, mirroring, etc.) and has a valid license key.

**Why this priority**: Required for production-like testing but fewer users have enterprise licenses.

**Independent Test**: Can be tested by providing a license key and verifying enterprise container starts with license applied.

**Acceptance Scenarios**:

1. **Given** developer has license key file, **When** they call `IRISContainer.enterprise(license_key="/path/to/iris.key")`, **Then** enterprise container starts with license mounted
2. **Given** developer has `IRIS_LICENSE_KEY` env var set, **When** they call `IRISContainer.enterprise()`, **Then** license from env var is used
3. **Given** developer needs to authenticate to containers.intersystems.com, **When** they run `iris-devtester container login`, **Then** they are guided through Docker login process
4. **Given** developer uses CLI, **When** they run `iris-devtester container up --edition enterprise --license /path/to/iris.key`, **Then** enterprise container starts

---

### User Story 3 - Light Edition for CI/CD (Priority: P3)

Developer wants fastest possible container startup for CI/CD pipelines where full IRIS features aren't needed.

**Why this priority**: Optimization for CI/CD - smaller image, faster pull, faster startup. Not all users need this.

**Independent Test**: Can be tested by measuring startup time and image size vs full community edition.

**Acceptance Scenarios**:

1. **Given** developer wants minimal container, **When** they call `IRISContainer.light()`, **Then** lightweight IRIS image is pulled (~580MB vs ~3.5GB vanilla)
2. **Given** CI/CD pipeline, **When** light edition is used, **Then** startup time is significantly faster (<30s vs ~60s)
3. **Given** developer uses CLI, **When** they run `iris-devtester container up --edition light`, **Then** light container starts
4. **Given** light edition limitations, **When** developer tries to use unsupported feature, **Then** clear error message explains limitation

---

### Edge Cases

- What happens when license key file doesn't exist or is invalid?
- How does system handle when containers.intersystems.com requires authentication but user isn't logged in?
- What if light edition doesn't support a feature the test needs?
- How do we handle image tag/version pinning across editions?
- What if Docker Hub is down but containers.intersystems.com is up (or vice versa)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `IRISContainer.community()` factory that auto-detects architecture (ARM64/x86) and pulls appropriate image
- **FR-002**: System MUST provide `IRISContainer.enterprise(license_key=...)` factory that handles license mounting
- **FR-003**: System MUST provide `IRISContainer.light()` factory for minimal CI/CD-optimized containers
- **FR-004**: CLI MUST support `--edition [community|enterprise|light]` option on `container up` command
- **FR-005**: System MUST support version pinning via `version="2025.1"` parameter on all factory methods
- **FR-006**: System MUST provide `iris-devtester container login` command for authenticating to container registries
- **FR-007**: Enterprise edition MUST support license key from file path OR `IRIS_LICENSE_KEY` environment variable
- **FR-008**: System MUST validate license key exists before attempting to start enterprise container
- **FR-009**: Light edition MUST document which features are NOT available (if any limitations exist)

### Image Registry Mapping

| Edition | x86_64 Image | ARM64 Image | Size |
|---------|--------------|-------------|------|
| Community | `intersystemsdc/iris-community:latest` | `containers.intersystems.com/intersystems/iris-community:2025.1` | ~972MB |
| Enterprise | `containers.intersystems.com/intersystems/iris:latest` | `containers.intersystems.com/intersystems/iris:latest` | ~1GB+ |
| Light | `caretdev/iris-community-light:latest-em` | `caretdev/iris-community-light:latest-em` | ~141MB |

**Light Edition Details** (from Docker Hub README):
- Image: `caretdev/iris-community-light`
- Maintainer: CaretDev (Dmitry Maslennikov)
- Size: ~580MB compressed, ~141MB on disk (85% smaller than vanilla ~3.5GB)
- Available versions: 2025.1, 2025.2, 2025.3, 2026.1
- Multi-arch: Supports both `amd64/linux` and `arm64/linux`

**What's REMOVED in Light Edition:**
- Interoperability / Ensemble (Productions, Business Services, Adapters)
- DeepSee / BI stack
- Full Web Stack (Management Portal, Web Gateway, CSP, REST framework)
- Most non-SQL runtime components
- Optional development libraries and tools

**What's KEPT in Light Edition:**
- Core IRIS database engine
- SQL engine & query processor
- System classes for storage and globals
- Authentication for basic operation
- JDBC & ODBC connectivity
- Python DBAPI (iris module) - **CONFIRMED WORKING**
- Compatible with: SQLAlchemy-IRIS, dbt-iris, Liquibase-IRIS, typeorm-iris

**Best Use Cases for Light:**
- Microservices
- CI/CD pipelines
- Automated testing
- Cloud-native database workloads
- Python / SQL / AI / ML pipelines
- Projects using pure SQL access

### Key Entities

- **ContainerEdition**: Enum of `community`, `enterprise`, `light`
- **LicenseConfig**: Handles license key path resolution and validation
- **ImageResolver**: Resolves correct image based on edition + architecture + version

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero-config `IRISContainer.community()` works on both ARM64 and x86 without user specifying image
- **SC-002**: Enterprise containers start successfully with license applied (verified by checking license info in container)
- **SC-003**: Light edition image size is <50% of full community edition
- **SC-004**: Light edition startup time is <50% of full community edition
- **SC-005**: Clear error messages when license is missing/invalid or registry auth fails

## CLI Container Name UX Improvements

### Current State (Audit Results)

| Command | Container Name | Required? | Default |
|---------|---------------|-----------|---------|
| `up` | `--name` (option) | No | `iris_db` |
| `start` | `CONTAINER_NAME` (argument) | No | `iris_db` |
| `stop` | `CONTAINER_NAME` (argument) | No | `iris_db` |
| `restart` | `CONTAINER_NAME` (argument) | No | `iris_db` |
| `remove` | `CONTAINER_NAME` (argument) | No | `iris_db` |
| `logs` | `CONTAINER_NAME` (argument) | No | `iris_db` |
| `status` | `CONTAINER_NAME` (argument) | No | `iris_db` |
| `reset-password` | `CONTAINER_NAME` (argument) | **Yes** | None |
| `enable-callin` | `CONTAINER_NAME` (argument) | **Yes** | None |
| `test-connection` | `CONTAINER_NAME` (argument) | **Yes** | None |

### Issues Identified

1. **Inconsistent pattern**: `up` uses `--name` option, others use positional argument
2. **Required vs optional inconsistent**: `reset-password` requires name, `stop` doesn't
3. **No container list**: Can't see what IRIS containers are running
4. **No project context**: User must remember container names

### Proposed Improvements

1. **Add `container list` command**: Show all IRIS containers with status
   ```bash
   iris-devtester container list
   # NAME          EDITION     STATUS    PORTS           AGE
   # iris_db       community   running   1972->1972      2h
   # my-test-db    light       stopped   -               1d
   ```

2. **Standardize on optional argument with default**: All commands should accept optional `CONTAINER_NAME` defaulting to `iris_db`

3. **Smart container detection**: If only one IRIS container exists, use it automatically

4. **Project-aware naming**: Auto-prefix with project directory name
   ```bash
   # In /Users/me/myproject/
   iris-devtester container up  # Creates "myproject-iris"
   ```

5. **Show running containers in status output**: When command runs, show which container was used

## Open Questions

1. ~~**Light Edition Source**: Which Docker image should be used for "light" edition?~~
   - **RESOLVED**: Use `caretdev/iris-community-light` (~141MB vs ~972MB)

2. ~~**Light Edition Limitations**: What features are NOT available in the light edition?~~
   - **RESOLVED**: See "What's REMOVED" section above
   - No Interoperability/Ensemble, No Management Portal, No DeepSee
   - DBAPI/JDBC/ODBC all work fine

3. ~~**Version Strategy**: How do we handle version pinning?~~
   - **RESOLVED**: Default to `latest` (or `latest-em` for LTS track)

4. **Authentication Flow**: How should `container login` work?
   - Defer to future implementation
   - For now, users can run `docker login containers.intersystems.com` manually
   - Document this in README

5. ~~**ARM64 Support for Light**: Does `caretdev/iris-community-light` support ARM64?~~
   - **RESOLVED**: Yes! Multi-arch manifest includes both `amd64/linux` and `arm64/linux`
