# Feature Specification: Fix IRIS Container Infrastructure Issues

**Feature Branch**: `011-fix-iris-container`
**Created**: 2025-01-13
**Status**: Draft
**Input**: User description: "Fix IRIS container infrastructure issues: ryuk cleanup, volume mounting failures, and persistent container support for benchmark infrastructure"

## Execution Flow (main)
```
1. Parse user description from Input
   → Critical issues identified: ryuk cleanup, volume mounting, container persistence
2. Extract key concepts from description
   → Actors: benchmark infrastructure, iris-devtester CLI, testcontainers
   → Actions: create persistent containers, mount workspace volumes, prevent premature cleanup
   → Data: workspace files, SimpleTestRunner class, benchmark tests
   → Constraints: testcontainers ryuk service, container lifecycle management
3. For each unclear aspect:
   → [RESOLVED] All issues clearly described with error messages and symptoms
4. Fill User Scenarios & Testing section
   → Benchmark infrastructure needs persistent containers with workspace mounts
5. Generate Functional Requirements
   → Each requirement addresses one of the three identified failures
6. Identify Key Entities (if data involved)
   → Container lifecycle, volume mounts, cleanup policies
7. Run Review Checklist
   → All requirements are testable and unambiguous
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

**As a** benchmark infrastructure developer
**I need** iris-devtester to create persistent IRIS containers with workspace mounts
**So that** benchmark tests can run against containers that have the required test runner code and test files

**Current Problem**: After upgrading to iris-devtester 1.2.1, benchmark infrastructure runs but fails with 0/24 tests passing because:
1. Containers are created but immediately cleaned up by testcontainers ryuk service
2. Volume mounts are not being applied despite correct configuration
3. Benchmark falls back to using a different container without workspace mount
4. SimpleTestRunner class doesn't exist in fallback container

**Impact**: Complete blockage of baseline metrics collection - 0% success rate

### Acceptance Scenarios

1. **Given** iris-devtester 1.2.1 is installed, **When** benchmark infrastructure creates a container with `iris-devtester container up --config benchmark-config.yml`, **Then** container MUST persist for the duration of the benchmark run (not be immediately removed by ryuk)

2. **Given** container configuration specifies `volumes: [./workspace:/external/workspace]`, **When** container is created, **Then** workspace directory MUST be accessible at `/external/workspace` inside the container

3. **Given** workspace contains `SimpleTestRunner.cls` file, **When** benchmark tries to instantiate `User.SimpleTestRunner`, **Then** class MUST exist and be executable

4. **Given** benchmark infrastructure needs container for 30 minutes, **When** container is created, **Then** container MUST remain available until explicitly stopped (not cleaned up prematurely)

5. **Given** container creation command completes successfully, **When** checking container status, **Then** container MUST actually exist and be running (not show "Failed to create container: 0")

### Edge Cases

- What happens when ryuk cleanup service tries to remove a container that should persist?
- How does system handle volume mounting when host path doesn't exist?
- What happens when multiple benchmark runs try to use same container name?
- How does system recover when container creation succeeds but volume mount fails?
- What happens when testcontainers cleanup interferes with CLI-managed containers?

## Requirements *(mandatory)*

### Functional Requirements

**Container Lifecycle Management**
- **FR-001**: System MUST create IRIS containers that persist beyond the creation command lifecycle
- **FR-002**: System MUST prevent testcontainers ryuk service from immediately removing CLI-managed containers
- **FR-003**: System MUST provide explicit container lifecycle control (create, start, stop, remove) independent of testcontainers cleanup
- **FR-004**: System MUST display accurate success/failure messages that reflect actual container state (no "success" when container is immediately removed)

**Volume Mounting**
- **FR-005**: System MUST apply volume mounts specified in configuration to created containers
- **FR-006**: System MUST verify volume mounts are accessible inside the container after creation
- **FR-007**: System MUST support workspace volume mounts required for benchmark infrastructure (e.g., `./workspace:/external/workspace`)
- **FR-008**: System MUST report clear error messages when volume mounting fails (not silent failures)

**Benchmark Infrastructure Support**
- **FR-009**: System MUST create containers that support benchmark test execution for at least 30 minutes
- **FR-010**: System MUST ensure workspace-mounted ObjectScript classes (like SimpleTestRunner) are accessible to IRIS
- **FR-011**: System MUST allow benchmark infrastructure to discover and use created containers by name
- **FR-012**: System MUST maintain container state until explicit cleanup command is issued

**Error Reporting**
- **FR-013**: System MUST NOT report "Failed to create container: 0" error when actual issue is container cleanup or volume mounting
- **FR-014**: System MUST provide actionable error messages following Constitutional Principle #5 (What/Why/How/Docs format)
- **FR-015**: System MUST distinguish between creation failures, volume mount failures, and cleanup issues in error messages

**Configuration Validation**
- **FR-016**: System MUST validate that volume mount paths exist before attempting container creation
- **FR-017**: System MUST verify container actually persists after creation before reporting success
- **FR-018**: System MUST detect conflicts between testcontainers lifecycle management and CLI lifecycle management

### Non-Functional Requirements

- **NFR-001**: Container creation with volume mounts MUST complete within 60 seconds (unless image pull required)
- **NFR-002**: Fixes MUST maintain backward compatibility with existing iris-devtester 1.2.1 configurations
- **NFR-003**: All 35 existing contract tests MUST continue to pass (no regression)
- **NFR-004**: Solution MUST work with both testcontainers-iris library and direct Docker SDK usage

### Key Entities *(include if feature involves data)*

- **Container**: IRIS database container with defined lifecycle (created, running, stopped, removed), identified by name, with associated configuration (ports, volumes, edition)

- **Volume Mount**: Mapping between host filesystem path and container filesystem path, with mode (read-only or read-write), required for workspace access

- **Workspace**: Host directory containing ObjectScript classes and test files that must be accessible inside container for benchmark execution

- **Lifecycle Policy**: Rules governing when containers are created, when they persist, and when they are cleaned up (explicit vs automatic)

- **Benchmark Configuration**: Container configuration specifically for benchmark infrastructure, including workspace mount and persistence requirements

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (0% → >90% benchmark pass rate)
- [x] Scope is clearly bounded (container lifecycle, volume mounting, cleanup prevention)
- [x] Dependencies and assumptions identified (testcontainers ryuk, iris-devtester 1.2.1)

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted (3 core failures identified)
- [x] Ambiguities marked (none - detailed error messages provided)
- [x] User scenarios defined (benchmark infrastructure use case)
- [x] Requirements generated (18 functional + 4 non-functional)
- [x] Entities identified (5 key entities)
- [x] Review checklist passed

---

## Success Metrics

**Before Fix** (iris-devtester 1.2.1):
- Benchmark success rate: 0/24 (0.0%)
- Container persistence: Immediate cleanup by ryuk
- Volume mounts: Not applied despite configuration
- Error clarity: "Failed to create container: 0" (uninformative)

**After Fix** (iris-devtester 1.2.x):
- Benchmark success rate: >22/24 (>90%) - SimpleTestRunner accessible
- Container persistence: Containers remain until explicit cleanup
- Volume mounts: Workspace accessible at configured paths
- Error clarity: Constitutional format with clear remediation steps

**Measurement Method**: Run benchmark infrastructure suite and verify:
1. Container persists for full benchmark duration
2. SimpleTestRunner class exists in container
3. Workspace files accessible via volume mount
4. No "Failed to create container: 0" errors
