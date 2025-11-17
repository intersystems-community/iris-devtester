# Feature Specification: Multi-Project Port Isolation

**Feature Branch**: `013-add-semantics-to`
**Created**: 2025-01-17
**Status**: Draft
**Input**: User description: "add semantics to support multiple separate projects using iris-devtester to avoid collisions on ports that IRIS needs!"

## Execution Flow (main)
```
1. Parse user description from Input
   → Feature: Enable multiple projects to use iris-devtester simultaneously
   → Problem: IRIS containers need port 1972 (superserver) which causes conflicts
2. Extract key concepts from description
   → Actors: Developers running multiple projects
   → Actions: Start IRIS containers, run tests, develop features
   → Data: Port assignments, project identifiers
   → Constraints: Each IRIS instance needs unique ports
3. Clarified key decisions:
   → Project identification: Absolute directory path
   → Port assignment: Auto-assign by default, manual override supported, persistent
   → Concurrency: 10 containers (ports 1972-1981)
   → Performance: <5 seconds for port assignment
   → Scope: Single-user (multi-user deferred to future)
4. Fill User Scenarios & Testing section
   → Scenario 1: Developer works on Project A while tests run for Project B
   → Scenario 2: Developer switches between projects without conflicts
5. Generate Functional Requirements
   → FR-001: System MUST assign unique ports to each IRIS container
   → FR-002: System MUST detect and avoid port conflicts
   → FR-003: System MUST support concurrent IRIS instances
6. Identify Key Entities (if data involved)
   → Project: Represents a development workspace
   → Container Instance: IRIS container with unique port assignment
7. Run Review Checklist
   → WARN "Spec has uncertainties - needs clarification on port assignment strategy"
8. Return: SUCCESS (spec ready for planning after clarifications)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## Clarifications

### Session 2025-01-17

- Q: How should the system uniquely identify projects to enable port isolation? → A: Directory path (absolute directory path as project identifier)
- Q: Should port assignments be automatic, manual, or hybrid? Should they persist across container restarts? → A: Manual-optional, persistent (auto-assign by default but allow manual override; persist both auto and manual assignments)
- Q: What is the maximum number of concurrent IRIS containers the system should support on a single machine? → A: 10 containers (ports 1972-1981)
- Q: What is acceptable latency for port assignment operations (finding available port and updating registry)? → A: 5 seconds
- Q: Should the system support multiple users on the same machine running separate projects without port conflicts? → A: Not a priority (single-user scenario only, port registry is user-specific, multi-user support deferred to future)

---

## User Scenarios & Testing

### Primary User Story

**As a** developer working with InterSystems IRIS
**I want to** run multiple projects using iris-devtester simultaneously
**So that** I can develop on one project while tests run on another, or work on multiple features in parallel without port conflicts

**Current Pain Point**: When developer tries to start a second IRIS container (e.g., for a different project), the container fails to start because port 1972 is already in use by the first project's IRIS instance. This forces developers to:
- Stop one project's containers before working on another
- Manually manage port assignments across projects
- Risk data loss from interrupted test runs
- Waste time waiting for containers to stop/start

**Desired Outcome**: Developer can seamlessly work on multiple projects, with each project's IRIS containers automatically using unique ports. No manual configuration required.

### Acceptance Scenarios

1. **Given** a developer has Project A running with IRIS on port 1972, **When** they start Project B's IRIS container, **Then** Project B's container automatically uses a different port (e.g., 1973) and both projects work simultaneously

2. **Given** a developer has stopped all IRIS containers, **When** they start Project A again, **Then** the system assigns the same port as before (persistent assignment remembered from previous session)

3. **Given** Project A is using port 1972 and Project B is using port 1973, **When** developer runs tests in both projects concurrently, **Then** both test suites complete successfully without interference

4. **Given** a developer has 10 projects running (ports 1972-1981 all in use), **When** they try to start an 11th project, **Then** the system fails fast with guidance indicating port exhaustion and remediation steps (stop unused containers or manually configure port outside standard range)

5. **Given** a developer manually configured Project A to use port 1975, **When** they start Project A's container, **Then** the system respects the manual port assignment and doesn't auto-assign a different port

### Edge Cases

- **Port exhaustion**: When all 10 ports (1972-1981) are in use, system fails with clear error message listing occupied ports and remediation options
- **Port conflict detection**: System detects if a non-IRIS process is using port 1972 by attempting socket bind before container start
- **Stale port assignments**: System automatically detects crashed containers (Docker status check) and marks assignments as stale, making ports available for reuse
- **Manual port override conflicts**: If user manually specifies port already assigned to another project, validation fails with conflict details
- **Container restart**: Container restart reuses the same persistent port assignment from registry
- **Cross-machine consistency**: Port assignments are machine-local (independent per machine) as they use absolute directory paths which differ across machines

## Requirements

### Scope

**In Scope for v1**:
- Single developer running multiple projects on their development machine
- User-specific port registry (stored in user's home directory)
- Automatic port assignment with manual override option
- Port persistence across container restarts

**Out of Scope for v1** (deferred to future):
- Multi-user support (shared port registry across users on same machine)
- System-wide port coordination between different users
- Enterprise multi-tenant scenarios

### Functional Requirements

**Core Port Management**
- **FR-001**: System MUST assign unique ports to each IRIS container instance from the range 1972-1981
- **FR-002**: System MUST detect when a requested port is already in use
- **FR-003**: System MUST prevent multiple containers from binding to the same port
- **FR-004**: System MUST support up to 10 concurrent IRIS containers on the same machine (using ports 1972-1981)

**Project Identification**
- **FR-005**: System MUST identify projects uniquely using absolute directory path as the project identifier (e.g., `/Users/dev/project-a`)
- **FR-006**: System MUST persist port assignments across container restarts (both auto-assigned and manually-specified ports)

**User Control**
- **FR-007**: Users MUST be able to see which ports are assigned to which projects
- **FR-008**: Users MUST be able to manually specify a port for their project if needed
- **FR-009**: System MUST validate user-specified ports are available before container start
- **FR-010**: Users MUST receive clear error messages when port conflicts occur, including guidance on resolution

**Configuration & Discovery**
- **FR-011**: System MUST auto-assign available ports by default without requiring manual configuration (Constitutional Principle #4: Zero Configuration Viable)
- **FR-012**: System MUST work with existing iris-devtester configurations without breaking changes
- **FR-013**: System MUST allow users to manually override auto-assigned ports when deterministic assignments are needed

**Cleanup & Resource Management**
- **FR-014**: System MUST release port assignments when containers stop
- **FR-015**: System MUST detect and clean up stale port assignments from crashed containers
- **FR-016**: System MUST provide a way to view and clear port assignment state

**Error Handling**
- **FR-017**: System MUST fail fast with guidance when no ports are available (Constitutional Principle #5)
- **FR-018**: Error messages MUST include: current port assignments, which ports are available, and remediation steps

### Non-Functional Requirements

**Performance**
- **NFR-001**: Port assignment MUST complete in under 5 seconds (finding available port and updating registry)
- **NFR-002**: Port conflict detection MUST not significantly delay container startup

**Reliability**
- **NFR-003**: Port assignment MUST be atomic to prevent race conditions when multiple containers start simultaneously
- **NFR-004**: System MUST detect and prevent port conflicts with 100% accuracy under normal operation (Constitutional Principle #7: Medical-Grade Reliability)
  - **Acceptable edge cases** (automatically recovered):
    - Docker daemon crashes during startup → Detected as stale assignment during next cleanup
    - Manual `docker rm` bypassing registry → Detected by `cleanup_stale()`, port released
    - File system corruption → Fail fast with clear error (PortAssignmentTimeoutError)
    - Concurrent assignment race conditions → File locking prevents conflicts
  - **Rationale**: File locking ensures atomic assignment (100% conflict prevention). Edge cases are handled via automatic cleanup and fail-fast error handling.

**Compatibility**
- **NFR-005**: Solution MUST support both Community and Enterprise IRIS editions
- **NFR-006**: Solution MUST work on Linux, macOS, and Windows
- **NFR-007**: Solution MUST not break existing test suites or fixtures

### Key Entities

- **Project**: A development workspace identified by its absolute directory path (e.g., `/Users/dev/my-iris-app`). Contains IRIS containers, test suites, and application code.

- **Container Instance**: A running IRIS container with a unique port assignment. Associated with exactly one Project. Has lifecycle: created → running → stopped → removed.

- **Port Assignment**: Mapping of Project to Port number. Attributes:
  - Project identifier (absolute directory path)
  - Port number (1972-1981 for auto-assignment, or user-specified)
  - Assignment timestamp
  - Assignment type (auto-assigned or user-specified)
  - Status (active, released, stale)

- **Port Registry**: User-specific record of all port assignments (stored in user's home directory, e.g., `~/.iris-devtester/port-registry.json`). Provides conflict detection and assignment history for the current user's projects.

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain - All 5 clarifications completed ✅
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (5 second performance target defined)
- [x] Scope is clearly bounded (v1 single-user, multi-user deferred)
- [x] Dependencies and assumptions identified

### Clarifications Completed (Session 2025-01-17)

All critical ambiguities resolved through 5-question clarification workflow:

1. ✅ **Project Identification**: Absolute directory path (e.g., `/Users/dev/project-a`)
2. ✅ **Port Assignment Strategy**: Auto-assign by default, manual override supported, persistent across restarts
3. ✅ **Concurrency Limits**: 10 concurrent containers (ports 1972-1981)
4. ✅ **Performance Targets**: Port assignment must complete in <5 seconds
5. ✅ **Multi-User Support**: Out of scope for v1 (single-user only, deferred to future)

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities identified and clarified (5/5 questions completed)
- [x] User scenarios defined and refined
- [x] Requirements generated and updated with clarifications
- [x] Entities identified and detailed
- [x] Scope boundaries established (v1 vs future)
- [x] Review checklist passed ✅

**Status**: READY FOR PLANNING ✅

---

## Next Steps

1. ✅ All clarifications complete
2. ✅ Performance targets defined (<5 seconds)
3. ✅ Scope clearly bounded (single-user v1)
4. **→ NEXT: Run `/plan` command** to generate implementation design
