# Feature Specification: IRIS DevTools Package Implementation

**Feature Branch**: `001-implement-iris-devtools`
**Created**: 2025-10-05
**Status**: Draft
**Input**: User description: "Implement iris-devtools following the feature request in .specify/feature-request.md"

## Execution Flow (main)
```
1. Parse user description from Input
   → Feature request references .specify/feature-request.md ✓
2. Extract key concepts from description
   → Identified: extraction project, connection management, testing utilities, packaging
3. For each unclear aspect:
   → No critical ambiguities (detailed requirements in feature-request.md)
4. Fill User Scenarios & Testing section
   → Primary user: Python developers needing IRIS connectivity
5. Generate Functional Requirements
   → All requirements testable against source material in rag-templates
6. Identify Key Entities (if data involved)
   → Configuration objects, connection objects, schema definitions
7. Run Review Checklist
   → No implementation HOW (template structure only)
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## User Scenarios & Testing

### Primary User Story

As a Python developer working with InterSystems IRIS databases, I need a reliable, zero-configuration toolkit that automatically handles connection setup, password resets, test isolation, and schema management so that I can focus on building features instead of debugging infrastructure.

The developer should be able to:
1. Install the package via pip
2. Run pytest without any manual configuration
3. Have tests automatically get isolated database environments
4. Have connections work seamlessly without worrying about DBAPI vs JDBC
5. Have password reset issues resolved automatically
6. Get clear, actionable error messages when something goes wrong

### Acceptance Scenarios

1. **Given** a fresh Python environment, **When** developer runs `pip install iris-devtools && pytest`, **Then** all infrastructure is configured automatically and tests run successfully without manual intervention

2. **Given** an IRIS container with expired credentials, **When** developer attempts to connect, **Then** the system automatically detects and resets the password, updating environment variables transparently

3. **Given** a test suite with 50 tests, **When** tests run in parallel, **Then** each test receives an isolated database namespace/container and cleanup happens automatically

4. **Given** an IRIS connection attempt, **When** DBAPI driver is available, **Then** system uses DBAPI (fast) first and only falls back to JDBC if DBAPI fails

5. **Given** a schema mismatch in test database, **When** test starts, **Then** schema is automatically validated and reset if necessary

6. **Given** a connection failure, **When** error occurs, **Then** error message includes specific diagnosis, remediation steps, and documentation links

7. **Given** no explicit configuration, **When** developer requests a connection, **Then** system auto-discovers configuration from environment variables, .env files, or running Docker containers

### Edge Cases

- What happens when both DBAPI and JDBC drivers fail? → System provides diagnostic information about both failures and suggests installation steps
- How does system handle concurrent test runs needing isolation? → Each test gets unique namespace or dedicated container based on isolation level
- What happens when Docker is not available? → System detects absence and provides clear instructions for either installing Docker or using manual IRIS instance
- How does system handle partial configuration (e.g., host provided but not port)? → Missing values filled from sensible defaults, logged for transparency
- What happens when password reset fails? → System falls back to manual instructions with exact commands to run
- How does system handle enterprise vs community IRIS editions? → Auto-detection of edition with appropriate feature adjustments
- What happens when schema validation detects unexpected state? → System provides diff of expected vs actual schema and offers auto-reset or abort options

---

## Requirements

### Functional Requirements

#### Connection Management
- **FR-001**: System MUST attempt connections using DBAPI driver first (performance optimization)
- **FR-002**: System MUST automatically fall back to JDBC driver if DBAPI connection fails
- **FR-003**: System MUST detect "Password change required" errors automatically
- **FR-004**: System MUST automatically reset IRIS passwords when password change is detected
- **FR-005**: System MUST update environment variables after successful password reset
- **FR-006**: System MUST auto-discover connection configuration from multiple sources (environment, .env files, Docker)
- **FR-007**: System MUST provide sensible defaults for all optional configuration values
- **FR-008**: System MUST support connection pooling to reduce connection overhead

#### Test Isolation
- **FR-009**: System MUST provide isolated database environments for each test by default
- **FR-010**: System MUST support both namespace-level and container-level isolation strategies
- **FR-011**: System MUST automatically clean up test databases/namespaces after test completion
- **FR-012**: System MUST track test state across test lifecycle
- **FR-013**: System MUST prevent test pollution by ensuring cleanup even on test failures

#### Schema Management
- **FR-014**: System MUST validate database schema matches expected schema before tests run
- **FR-015**: System MUST automatically reset schema when mismatches are detected
- **FR-016**: System MUST provide detailed diff information when schema validation fails
- **FR-017**: System MUST support custom schema definitions for different test scenarios
- **FR-018**: System MUST cache schema validation results to avoid redundant checks

#### Container Management
- **FR-019**: System MUST extend testcontainers-iris-python with enhanced functionality
- **FR-020**: System MUST provide wait strategies that verify actual database readiness (not just log messages)
- **FR-021**: System MUST perform health checks before marking containers as ready
- **FR-022**: System MUST support both Community and Enterprise IRIS container images
- **FR-023**: System MUST automatically integrate password remediation with container lifecycle

#### Error Handling
- **FR-024**: System MUST provide actionable error messages for all failure modes
- **FR-025**: Error messages MUST include diagnosis, remediation steps, and documentation links
- **FR-026**: System MUST attempt automatic remediation before failing
- **FR-027**: System MUST log remediation attempts for debugging
- **FR-028**: System MUST distinguish between recoverable and unrecoverable errors

#### Developer Experience
- **FR-029**: System MUST work with zero configuration for common development scenarios
- **FR-030**: System MUST provide pytest fixtures that can be imported and used immediately
- **FR-031**: System MUST support explicit configuration for advanced use cases
- **FR-032**: System MUST provide diagnostic utilities for troubleshooting
- **FR-033**: System MUST maintain backwards compatibility with existing rag-templates usage patterns

#### Quality & Reliability
- **FR-034**: System MUST achieve 95% or greater test coverage
- **FR-035**: System MUST support Python 3.9 and newer
- **FR-036**: System MUST be installable via pip from PyPI
- **FR-037**: System MUST have comprehensive documentation including examples
- **FR-038**: System MUST perform as well or better than source code in rag-templates

### Key Entities

- **Connection**: Represents an active database connection with metadata about driver type (DBAPI/JDBC), host, port, namespace, credentials, and connection pool membership

- **Configuration**: Represents discovered or explicit IRIS configuration including connection parameters, schema definitions, isolation strategy, wait strategies, and environment detection results

- **SchemaDefinition**: Represents expected database schema including table definitions, column specifications with types and constraints, and validation rules

- **SchemaValidationResult**: Represents outcome of schema validation including success/failure status, list of mismatches found, suggested remediation actions, and timestamp

- **TestState**: Represents current state of test environment including isolation level, assigned namespace/container, cleanup registry entries, and schema validation cache

- **ContainerConfig**: Represents IRIS container configuration including edition (Community/Enterprise), image version, port mappings, environment variables, wait strategies, and health check definitions

- **PasswordResetResult**: Represents outcome of password reset attempt including success status, new password if generated, updated environment variables, and error details if failed

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs) - focuses on capabilities
- [x] Focused on user value and business needs - developer productivity and reliability
- [x] Written for non-technical stakeholders - uses business language
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain - feature-request.md provides full context
- [x] Requirements are testable and unambiguous - each FR can be validated
- [x] Success criteria are measurable - coverage %, zero-config works, performance targets
- [x] Scope is clearly bounded - extraction and enhancement, not greenfield development
- [x] Dependencies and assumptions identified - rag-templates source, testcontainers, Python 3.9+

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (none requiring clarification)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed
