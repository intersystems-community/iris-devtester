# Feature Specification: Fix Critical Container Creation Bugs

**Feature Branch**: `010-fix-critical-bugs`
**Created**: 2025-01-13
**Status**: Draft
**Input**: User description: "Fix critical bugs: incorrect image name, silent container creation failures, and volume mounting issues"

## Execution Flow (main)
```
1. Parse user description from Input
   → Bug 1: Image name hardcoded incorrectly (container_config.py:266)
   → Bug 2: Container creation fails silently with misleading messages
   → Bug 3: Volumes not mounting despite config
2. Extract key concepts from description
   → Actors: Developers using iris-devtester CLI
   → Actions: Creating IRIS containers
   → Data: Container configuration, Docker images, volume mounts
   → Constraints: Must work with Community edition, maintain backwards compatibility
3. Fill User Scenarios & Testing section
   → Three bug fix scenarios identified
4. Generate Functional Requirements
   → Fix image name, improve error handling, implement volume mounting
5. Run Review Checklist
   → No implementation details in spec
   → Requirements are testable
6. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## Problem Statement

The iris-devtester CLI tool currently has three critical bugs that prevent successful IRIS container creation:

1. **Incorrect Docker image name**: The tool uses `intersystems/iris-community` but Docker Hub uses `intersystemsdc/iris-community` (note the 'dc' suffix for Docker Community images)

2. **Silent failure with misleading messages**: When container creation fails, the tool shows "✗ Failed to create container: 0" followed by success messages, then the container gets cleaned up by testcontainers' ryuk cleanup process, leaving users confused

3. **Volume mounts ignored**: Configuration files can specify volume mounts but they are not applied to the container, preventing users from persisting data or mounting external resources

These bugs block all container-dependent workflows including compilation scripts (iris_compile_impl.sh) and test execution scripts (iris_test_impl.sh).

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a developer using iris-devtester, I need to create IRIS containers reliably so that I can run my development and testing workflows without manual Docker intervention.

### Acceptance Scenarios

#### Bug Fix 1: Correct Image Name
1. **Given** a fresh system with no IRIS images pulled, **When** a user runs `iris-devtester container up` with Community edition, **Then** the system MUST pull `intersystemsdc/iris-community:latest` (not `intersystems/iris-community:latest`)

2. **Given** a user has specified `image_tag: "2024.1"` in their config, **When** they create a Community edition container, **Then** the system MUST use `intersystemsdc/iris-community:2024.1`

3. **Given** a user specifies Enterprise edition, **When** they create a container, **Then** the system MUST use `intersystems/iris:latest` (Enterprise images do NOT have the 'dc' suffix)

#### Bug Fix 2: Clear Error Messages
1. **Given** Docker cannot pull the requested image, **When** container creation fails, **Then** the system MUST display a clear error message explaining what went wrong, why, and how to fix it (not "Failed to create container: 0")

2. **Given** a port conflict exists (1972 already in use), **When** container creation fails, **Then** the system MUST identify the specific port conflict and suggest remediation steps

3. **Given** container creation succeeds initially but health checks fail, **When** the container is cleaned up, **Then** the system MUST report the health check failure, not show success messages

#### Bug Fix 3: Volume Mounting
1. **Given** a config file with `volumes: ["./data:/external"]`, **When** a user creates a container, **Then** the system MUST mount the local `./data` directory to `/external` inside the container

2. **Given** multiple volume mounts in config, **When** container starts, **Then** all specified volumes MUST be mounted and accessible from inside the container

3. **Given** a volume mount with invalid path, **When** container creation is attempted, **Then** the system MUST fail with a clear error explaining the invalid path

### Edge Cases

- What happens when Docker image name is correct but image doesn't exist on Docker Hub?
  - System should display clear error about image not found with suggestions

- What happens when user specifies volumes but the source directory doesn't exist?
  - System should either auto-create directory or fail with clear guidance

- What happens when container starts successfully but then crashes immediately?
  - System should detect crash during health check and report actual failure reason

---

## Requirements *(mandatory)*

### Functional Requirements

#### Image Name Correction
- **FR-001**: System MUST use `intersystemsdc/iris-community` for Community edition containers (not `intersystems/iris-community`)
- **FR-002**: System MUST use `intersystems/iris` for Enterprise edition containers (no 'dc' suffix)
- **FR-003**: System MUST append the configured image tag to the correct base image name
- **FR-004**: System MUST validate image names before attempting to pull them

#### Error Handling Improvement
- **FR-005**: System MUST report actual error messages from container creation failures (not generic "Failed to create container: 0")
- **FR-006**: System MUST distinguish between different failure types (image pull failure, port conflict, health check failure, permission error)
- **FR-007**: System MUST follow constitutional error message format (What/Why/How/Docs) for all container creation failures
- **FR-008**: System MUST NOT display success messages when container creation has failed
- **FR-009**: System MUST detect when container gets cleaned up by testcontainers and report this as a failure

#### Volume Mounting
- **FR-010**: System MUST apply all volume mounts specified in configuration to the created container
- **FR-011**: System MUST validate volume mount paths before container creation
- **FR-012**: System MUST support both host-path and named-volume mount types
- **FR-013**: System MUST report clear errors when volume mount source path doesn't exist or is inaccessible
- **FR-014**: System MUST verify that volumes are successfully mounted after container starts

### Non-Functional Requirements
- **NFR-001**: Fixes MUST maintain backwards compatibility with existing config files
- **NFR-002**: Fixes MUST not break existing integration tests
- **NFR-003**: Error messages MUST be clear enough for non-Docker-experts to troubleshoot

### Key Entities *(include if feature involves data)*

- **Container Configuration**: Represents user's desired container setup including edition (community/enterprise), image tag, ports, namespace, password, and volumes
- **Docker Image Reference**: The full image name including registry, repository, and tag (e.g., `intersystemsdc/iris-community:latest`)
- **Volume Mount**: A mapping between host filesystem path and container internal path (e.g., `./data:/external`)
- **Container State**: Current status of container including whether it's created, running, healthy, or failed

---

## Dependencies & Assumptions

### Dependencies
- Docker daemon must be running and accessible
- testcontainers-iris library must support volume mounting
- Docker Hub must host images at both `intersystemsdc/iris-community` and `intersystems/iris`

### Assumptions
- Users have valid Docker setup with appropriate permissions
- Image names on Docker Hub won't change unexpectedly
- testcontainers-iris provides access to underlying container configuration

---

## Success Criteria

1. Community edition containers use `intersystemsdc/iris-community` image (verified by `docker inspect`)
2. Enterprise edition containers use `intersystems/iris` image (verified by `docker inspect`)
3. All container creation failures show clear, actionable error messages (no more "Failed to create container: 0")
4. Volumes specified in config are mounted and accessible inside container (verified by file system checks)
5. All existing integration tests continue to pass
6. New integration tests verify all three bug fixes

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
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (none found)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---

## Out of Scope

- Changing container orchestration strategy (e.g., switching from testcontainers to direct Docker SDK)
- Adding support for docker-compose.yml files
- Implementing container networking features beyond basic port mapping
- Supporting Kubernetes or other container platforms
- Modifying IRIS internal configuration beyond what's needed for basic container operation

---

## Notes

This is a bug fix feature, not a new capability. The three bugs represent gaps between the intended behavior (reliable container creation with volumes) and actual behavior (fails silently with wrong image names and ignored volumes).

The image name bug is particularly critical because `intersystems/iris-community` doesn't exist on Docker Hub - it's `intersystemsdc/iris-community`. This causes immediate failure for all Community edition users.

The silent failure bug makes debugging nearly impossible - users see success messages even though the container is about to be cleaned up, leading to confusion about whether their setup is correct.

The volume mounting bug prevents any persistent data workflows, which is essential for development environments where users need to preserve database state or mount code directories.
