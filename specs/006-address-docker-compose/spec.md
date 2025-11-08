# Feature Specification: Docker-Compose & Existing Container Support

**Feature Branch**: `006-address-docker-compose`
**Created**: 2025-11-07
**Status**: Draft
**Input**: User feedback from FHIR-AI-Hackathon-Kit production deployment with licensed IRIS 2025.3.0EHAT.127.0

## Context

This specification addresses comprehensive feedback from a real-world production deployment using docker-compose with licensed IRIS. The current iris-devtester v1.0.0 is optimized for testcontainers workflows but lacks support for existing container management, resulting in poor UX for docker-compose and production deployments.

**User Environment**:
- macOS (Darwin 24.5.0)
- Docker Desktop
- Licensed IRIS: 2025.3.0EHAT.127.0-linux-arm64v8
- Container started via docker-compose (not testcontainers)
- Python 3.12, iris-devtester 1.0.0

**Key Pain Points**:
1. "iris-devtester has excellent building blocks, but they're hard to discover and use outside of the testcontainers workflow."
2. **CRITICAL**: User gave up on enterprise/licensed IRIS setup and reverted to Community edition due to UX friction - this represents a complete failure of Principle #6 (Enterprise Ready, Community Friendly)

**Business Impact**: The inability to easily use iris-devtester with docker-compose and licensed IRIS is causing users to abandon enterprise features and revert to Community edition, undermining InterSystems' commercial value proposition.

---

## User Scenarios & Testing

### Primary User Story

**Scenario 1: Developer Using Docker-Compose**

Sarah is developing a FHIR application using docker-compose to run a licensed IRIS instance. She needs to:
1. Reset the _SYSTEM password for DBAPI access
2. Enable CallIn service for embedded Python
3. Test the connection works
4. Check overall container health

Currently, Sarah must:
- Write Python scripts for each operation (no CLI)
- Copy ObjectScript snippets from source code
- Cannot use IRISContainer utilities (they assume lifecycle management)
- Guess which utilities exist (unexpire_passwords is undocumented)

**Desired Experience**:
```bash
# Quick CLI commands
iris-devtester container reset-password iris-fhir-licensed --user _SYSTEM --password ISCDEMO
iris-devtester container enable-callin iris-fhir-licensed
iris-devtester container test-connection iris-fhir-licensed
iris-devtester container status iris-fhir-licensed
```

**Scenario 2: DevOps Engineer Troubleshooting "Access Denied"**

Mark gets "Access Denied" when connecting via DBAPI. The error message doesn't explain:
- CallIn service must be enabled for DBAPI
- How to enable CallIn service
- What AutheEnabled=48 means

**Desired Experience**:
```
RuntimeError: Access Denied

Likely Cause: CallIn service not enabled (required for DBAPI connections)

Quick Fix:
  iris-devtester container enable-callin my-iris-container

Or in Python:
  from iris_devtester.utils import enable_callin_service
  enable_callin_service('my-iris-container')

Documentation: https://github.com/intersystems-community/iris-devtester/blob/main/docs/TROUBLESHOOTING.md#access-denied
```

**Scenario 3: Data Scientist Using Standalone Utilities**

Elena has an existing IRIS instance from her team's infrastructure. She needs to:
- Use iris-devtester utilities without IRISContainer
- Work with containers she didn't create
- Follow the same pattern for all operations (consistency)

**Current State**:
```python
# ✅ Works (standalone)
from iris_devtester.utils.password_reset import reset_password
reset_password("team-iris", "_SYSTEM", "ISCDEMO")

# ✅ Works but undocumented (standalone)
from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords
unexpire_all_passwords("team-iris")

# ❌ Doesn't exist (must use IRISContainer)
from iris_devtester.utils import enable_callin_service  # ModuleNotFoundError
```

**Desired Experience**: All utilities available as standalone functions

### Acceptance Scenarios

#### High Priority Features

1. **Given** an existing docker-compose IRIS container, **When** user runs `iris-devtester container status iris-fhir-licensed`, **Then** system displays: container health, password status, CallIn enabled status, connection test result

2. **Given** an IRIS container without CallIn enabled, **When** user runs `iris-devtester container enable-callin my-container`, **Then** system enables CallIn service and confirms success

3. **Given** a developer with an existing container, **When** they import `from iris_devtester.utils import enable_callin_service`, **Then** the standalone function is available (matching password_reset pattern)

4. **Given** an IRISContainer instance, **When** user calls `IRISContainer.attach("my-existing-container")`, **Then** system attaches to existing container and provides utility methods

5. **Given** a new user reading README, **When** they look for docker-compose examples, **Then** they find example showing integration with existing infrastructure

#### Medium Priority Features

6. **Given** a connection failure, **When** error message is displayed, **Then** message includes: what went wrong, likely cause, step-by-step fix, documentation link

7. **Given** a developer exploring utilities, **When** they read docs, **Then** unexpire_passwords is documented in main README alongside password_reset

8. **Given** a user reading source code, **When** they see `AutheEnabled=48`, **Then** inline comment explains: "48 = Password + Kerberos authentication (0x30 bitmask)"

#### Low Priority Features

9. **Given** a troubleshooting scenario, **When** user checks docs, **Then** TROUBLESHOOTING.md exists with top 5 issues: Access Denied → enable CallIn, Password change required → reset password, Connection refused → check container, etc.

### Edge Cases

- What happens when user tries to attach to non-existent container? → Clear error: "Container 'xyz' not found. Available: [list]. Hint: Check 'docker ps'"
- What happens when CallIn is already enabled? → Idempotent: "CallIn already enabled (AutheEnabled=48)"
- What happens when password reset fails? → Error includes: reason, current permissions, Docker requirements
- How does enable_callin_service work on non-containerized IRIS? → Detect connection type, use appropriate method (docker exec vs SQL)

---

## Requirements

### Functional Requirements

#### High Priority (v1.0.1 Target)

**FR-001**: System MUST provide `IRISContainer.attach(container_name)` class method to reference existing containers without lifecycle management

**FR-002**: System MUST provide CLI command `iris-devtester container reset-password <name> [--user USER] [--password PWD]`

**FR-003**: System MUST provide CLI command `iris-devtester container enable-callin <name>`

**FR-004**: System MUST provide CLI command `iris-devtester container test-connection <name>`

**FR-005**: System MUST provide CLI command `iris-devtester container status <name>` showing: container health, password expiration, CallIn status, connection test

**FR-006**: System MUST provide standalone utility function `iris_devtester.utils.enable_callin_service(container_name)` matching password_reset pattern

**FR-007**: System MUST provide standalone utility function `iris_devtester.utils.test_connection(container_name)` for connectivity validation

**FR-008**: System MUST include example `examples/10_docker_compose_integration.py` showing:
- Using standalone utilities with docker-compose containers
- Best practices for licensed IRIS
- How to integrate with existing infrastructure
- Complete setup workflow (password reset → CallIn → connection test)

#### Medium Priority (v1.0.1 or v1.1.0)

**FR-009**: System MUST enhance error messages with structured format:
```
[ERROR TYPE]

What went wrong:
  [Brief explanation]

Likely cause:
  [Most common reason]

How to fix:
  1. [Step 1]
  2. [Step 2]
  3. [Step 3]

Documentation: [URL]
```

**FR-010**: System MUST document `unexpire_all_passwords()` in main README.md alongside `reset_password()`

**FR-011**: System MUST explain AutheEnabled=48 via:
- Named constant: `AUTHE_PASSWORD_KERBEROS = 48`
- Inline comment: "48 = 0x30 = Password (0x10) + Kerberos (0x20) authentication"
- Documentation in CallIn service docstring

**FR-012**: System MUST raise logging level for automatic password unexpiration from `logger.debug` to `logger.info` for visibility

#### Low Priority (v1.1.0)

**FR-013**: System MUST provide `docs/TROUBLESHOOTING.md` with sections:
- "Access Denied" → enable CallIn service
- "Password change required" → reset password
- "Connection refused" → check container running
- "Container not found" → verify container name
- Performance issues → check Docker resources

**FR-014**: System MUST update all error messages to follow Principle #5 (Fail Fast with Guidance) format

**FR-015**: System MUST provide `iris-devtester container list` command showing all IRIS containers with basic status

### Key Entities

**IRISContainerAdapter**: Represents a reference to an existing IRIS container (vs managed lifecycle)
- container_name: Name of existing Docker container
- connection_config: Discovered connection parameters
- health_status: Container health check results
- capabilities: Available utilities (CallIn enabled, password expired, etc.)

**ContainerUtility**: Represents a standalone utility operation
- operation_type: reset-password, enable-callin, test-connection, status
- target_container: Container name
- parameters: Operation-specific parameters
- result: Success/failure with structured message

**ErrorGuidance**: Structured error information
- error_type: Category of error (ConnectionError, AuthenticationError, etc.)
- what_went_wrong: Brief explanation
- likely_cause: Most common reason
- fix_steps: Ordered remediation steps
- documentation_url: Link to detailed troubleshooting

---

## Design Constraints

### Constitutional Compliance

**Principle #1: Automatic Remediation Over Manual Intervention**
- ✅ CLI commands automate manual docker exec operations
- ✅ Standalone utilities work without IRISContainer setup

**Principle #4: Zero Configuration Viable**
- ✅ Auto-discover container connection parameters
- ✅ Sensible defaults for all operations

**Principle #5: Fail Fast with Guidance**
- ✅ Structured error messages with remediation steps
- ✅ Link to troubleshooting documentation

**Principle #6: Enterprise Ready, Community Friendly**
- ✅ Works with docker-compose (production pattern)
- ✅ Works with testcontainers (development pattern)

### Technical Constraints

- MUST NOT break existing IRISContainer API (backward compatibility)
- MUST NOT require IRIS to be running for CLI help/list commands
- MUST work with both DBAPI and JDBC connection types
- MUST support both containerized and native IRIS installations
- MUST follow existing code patterns (password_reset is the model)

### User Experience Constraints

- CLI commands MUST provide `--help` documentation
- Standalone utilities MUST return (success: bool, message: str) tuple
- Error messages MUST NOT exceed 15 lines (readability)
- All utilities MUST be idempotent (safe to run multiple times)

---

## Success Criteria

### Measurable Outcomes

1. **CLI Completeness**: User can perform all common operations via CLI (reset password, enable CallIn, test connection, check status) without writing Python code

2. **API Consistency**: All utilities available as both:
   - CLI commands: `iris-devtester container <operation> <name>`
   - Standalone functions: `iris_devtester.utils.<operation>(container_name)`
   - IRISContainer methods: `container.<operation>()`

3. **Documentation Coverage**:
   - Docker-compose example exists and is runnable
   - TROUBLESHOOTING.md covers top 5 user issues
   - All utilities documented in main README
   - AutheEnabled constants explained

4. **Error Message Quality**: All connection/authentication errors include:
   - What went wrong (1 line)
   - Likely cause (1-2 lines)
   - Fix steps (3-5 numbered steps)
   - Documentation URL

5. **Backward Compatibility**: All existing tests pass, no breaking API changes

### Quality Gates

- Unit test coverage ≥ 94% (maintain current standard)
- Integration tests for all new CLI commands
- Contract tests for all new standalone utilities
- Documentation updated in README, TROUBLESHOOTING, examples/
- CHANGELOG.md entry for v1.0.1

---

## Out of Scope

### Explicitly Not Included

**Multi-Container Management**: Batch operations across multiple containers (e.g., `iris-devtester container enable-callin --all`) - complexity not justified by user feedback

**GUI/Web Interface**: CLI is sufficient for target users (developers, DevOps)

**Container Lifecycle Management via CLI**: Creating, stopping, removing containers - docker-compose already handles this well

**Advanced Authentication Configuration**: Beyond enable/disable CallIn - users can use native IRIS tools

**Performance Monitoring CLI**: Task Manager, resource monitoring - different use case, covered by existing IRISContainer methods

**Windows Container Support**: Feedback from macOS/Linux users only, Windows needs separate validation

### Future Considerations

- **v1.1.0**: Enhanced container discovery (find all IRIS instances on network)
- **v1.2.0**: Connection pooling for standalone utilities
- **v2.0.0**: Full parity between IRISContainer methods and standalone utilities

---

## Dependencies & Assumptions

### Dependencies

- Docker must be installed and running (for container operations)
- User has permissions to run `docker exec` (for ObjectScript operations)
- IRIS container must be accessible (running and network-reachable)

### Assumptions

- Users prefer CLI for quick operations, Python API for automation
- Docker-compose is the primary production deployment pattern
- Users are comfortable with command-line tools
- Error messages should prioritize quick fixes over comprehensive explanations
- Most users work with 1-3 IRIS containers (not dozens)

### Risks

**Risk 1: Docker Permissions**
- Impact: Users without docker exec permissions can't use utilities
- Mitigation: Document sudo requirements, provide clear permission error messages

**Risk 2: Non-Docker IRIS Installations**
- Impact: Docker-specific utilities won't work with native IRIS
- Mitigation: Detect installation type, provide appropriate error/guidance

**Risk 3: Breaking Changes to IRISContainer**
- Impact: Existing code using IRISContainer might break
- Mitigation: Add new methods, don't modify existing. Comprehensive test coverage.

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

### Alignment with Feedback
- [x] Addresses HIGH priority issues (IRISContainer.attach, CLI, standalone utilities)
- [x] Addresses MEDIUM priority issues (examples, errors, docs)
- [x] Addresses LOW priority issues (AutheEnabled, troubleshooting)
- [x] Prioritized based on user impact
- [x] Maintains constitutional compliance

---

## Execution Status

- [x] User description parsed (from feedback file)
- [x] Key concepts extracted (docker-compose, existing containers, CLI, standalone utilities)
- [x] Ambiguities marked (none - feedback is comprehensive and specific)
- [x] User scenarios defined (3 detailed scenarios)
- [x] Requirements generated (15 functional requirements, prioritized)
- [x] Entities identified (3 key entities)
- [x] Review checklist passed

---

## Appendix: Feedback Categorization

### Issues from IRIS_DEVTESTER_FEEDBACK.md

| # | Issue | Priority | FR Reference |
|---|-------|----------|--------------|
| 1 | IRISContainer Cannot Reference Existing Containers | HIGH | FR-001 |
| 2 | Missing Standalone Utility Functions | HIGH | FR-006, FR-007 |
| 3 | Documentation Gap: CallIn Service Required | MEDIUM | FR-009 |
| 4 | Mystery: AutheEnabled=48 Not Explained | LOW | FR-011 |
| 5 | Password Unexpiration Auto-Called But Not User-Visible | MEDIUM | FR-010, FR-012 |
| 6 | No CLI for Common Operations | HIGH | FR-002, FR-003, FR-004, FR-005 |
| 7 | Example Gap: Docker Compose Integration | HIGH | FR-008 |
| 8 | Confusing Error Messages | MEDIUM | FR-009, FR-014 |

### What Worked Well (Preserve These Patterns)

1. **Password Reset Utility** - Perfect standalone API model
   - Clear parameters
   - Returns (success: bool, message: str)
   - Works with docker-compose containers
   - Well documented

2. **Unexpire Passwords Utility** - Good implementation, needs docs
   - Standalone function exists
   - Simple API
   - Just needs visibility in main docs

3. **Well-Structured Source Code** - Maintain quality
   - Readable, well-commented
   - Excellent docstrings
   - Easy to find solutions in source

---

## Next Steps

1. **Clarify specification** with user if needed
2. **Create plan.md** with technical implementation details
3. **Generate tasks.md** with ordered implementation steps
4. **Begin implementation** on branch `006-address-docker-compose`
5. **Target release**: v1.0.1 (high priority items) or v1.1.0 (all items)
