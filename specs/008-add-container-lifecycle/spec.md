# Feature Specification: Container Lifecycle CLI Commands

**Feature Branch**: `008-add-container-lifecycle`
**Created**: 2025-01-09
**Status**: Draft
**Input**: User description: "Add container lifecycle CLI commands (start, stop, up, logs, remove) to enable zero-config container management from command line"

## Execution Flow (main)
```
1. Parse user description from Input
   → ✅ COMPLETE: Feature adds CLI commands for container lifecycle management
2. Extract key concepts from description
   → ✅ COMPLETE: Actors (CLI users), Actions (start/stop/up/logs/remove), Data (containers, config files)
3. For each unclear aspect:
   → No major ambiguities - user provided clear gap analysis and expected behavior
4. Fill User Scenarios & Testing section
   → ✅ COMPLETE: Clear user flow from configuration file to running container
5. Generate Functional Requirements
   → ✅ COMPLETE: All requirements testable
6. Identify Key Entities (if data involved)
   → ✅ COMPLETE: Container config, running container state
7. Run Review Checklist
   → ✅ COMPLETE: No implementation details, focused on user value
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Problem Statement

**Current State**: iris-devtester CLI provides commands for managing EXISTING containers:
- `iris-devtester container status` - Check container health
- `iris-devtester container test-connection` - Test connectivity
- `iris-devtester container enable-callin` - Enable DBAPI
- `iris-devtester container reset-password` - Reset passwords

**Gap**: CLI has NO commands to START, STOP, or CREATE containers. Users must:
1. Use Python code: `IRISContainer.community()` context manager
2. Use docker-compose separately, then use iris-devtester for management
3. Manually run docker commands

**User Impact**: Violates Constitutional Principle #4 "Zero Configuration Viable" - users should not need to write Python code or use docker-compose for basic container operations.

**Expected Behavior**: CLI should provide complete container lifecycle management, similar to docker-compose, with zero-config defaults.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story

As a developer using iris-devtester, I want to start an IRIS container from my configuration file using a single CLI command, so I don't have to write Python code or use docker-compose.

**Current Workaround**:
```bash
# Must use docker-compose or write Python code
docker-compose up -d
# THEN use iris-devtester for management
iris-devtester container status
```

**Desired Experience**:
```bash
# Single command to start container from config
iris-devtester container up --config iris-config.yml
# Or with zero-config defaults
iris-devtester container up
```

### Acceptance Scenarios

1. **Given** I have an iris-config.yml file in my project directory, **When** I run `iris-devtester container up`, **Then** the system starts an IRIS container using configuration from the file

2. **Given** I have no configuration file, **When** I run `iris-devtester container up`, **Then** the system starts an IRIS Community container with zero-config defaults

3. **Given** I have a running IRIS container, **When** I run `iris-devtester container stop`, **Then** the system stops the container gracefully

4. **Given** I specify `--config iris-config.yml` with a non-existent file, **When** I run `iris-devtester container start`, **Then** the system displays a helpful error message with the file path and example configuration

5. **Given** I have a running container, **When** I run `iris-devtester container logs`, **Then** the system displays recent container logs

6. **Given** I have stopped containers, **When** I run `iris-devtester container remove`, **Then** the system removes the containers and associated volumes

7. **Given** I run `iris-devtester container up` twice, **When** a container is already running, **Then** the system reports that the container is already up (idempotent behavior)

8. **Given** I specify `--detach` flag, **When** I run `iris-devtester container up --detach`, **Then** the system starts the container in background mode and returns immediately

### Edge Cases

- What happens when docker is not installed or not running?
  - System displays error with installation instructions

- What happens when the specified container name already exists?
  - System reports existing container status, offers to restart or use different name

- What happens when configuration file has invalid YAML?
  - System displays specific YAML error with line number

- What happens when insufficient disk space exists?
  - System displays clear error before attempting container start

- What happens when network port is already in use?
  - System displays error identifying the conflicting port and process

- What happens when the license key in config is invalid (Enterprise edition)?
  - System displays validation error before attempting container start

## Requirements *(mandatory)*

### Functional Requirements

#### Core Lifecycle Commands

- **FR-001**: System MUST provide `iris-devtester container start` command to start a new container from configuration file
- **FR-002**: System MUST provide `iris-devtester container stop` command to gracefully stop a running container
- **FR-003**: System MUST provide `iris-devtester container restart` command to stop and start a container
- **FR-004**: System MUST provide `iris-devtester container up` command (docker-compose style) to create or start a container
- **FR-005**: System MUST provide `iris-devtester container logs` command to display container output
- **FR-006**: System MUST provide `iris-devtester container remove` command to delete stopped containers

#### Configuration Support

- **FR-007**: System MUST accept `--config <path>` flag to specify configuration file location
- **FR-008**: System MUST support configuration files in YAML format (iris-config.yml)
- **FR-009**: System MUST use zero-config defaults when no configuration file is specified
- **FR-010**: System MUST validate configuration file syntax before attempting container operations
- **FR-011**: System MUST support both absolute and relative paths for configuration files

#### Configuration File Schema

- **FR-012**: Configuration MUST support specifying IRIS edition (community or enterprise)
- **FR-013**: Configuration MUST support specifying container name
- **FR-014**: Configuration MUST support specifying port mappings
- **FR-015**: Configuration MUST support specifying namespace
- **FR-016**: Configuration MUST support specifying license key (Enterprise edition)
- **FR-017**: Configuration MUST support specifying initial password
- **FR-018**: Configuration MUST support specifying volume mounts

#### Operational Behavior

- **FR-019**: System MUST provide `--detach` flag to run containers in background mode
- **FR-020**: System MUST provide `--follow` flag for logs command to stream continuous output
- **FR-021**: System MUST display container status after start/stop/restart operations
- **FR-022**: System MUST wait for container health check before reporting "started" status
- **FR-023**: System MUST support `--timeout <seconds>` flag for graceful shutdown before force kill
- **FR-024**: System MUST be idempotent (running `up` on an already-running container succeeds)

#### Error Handling & User Guidance

- **FR-025**: System MUST validate docker is installed before executing container commands
- **FR-026**: System MUST validate docker daemon is running before executing container commands
- **FR-027**: System MUST display clear error messages following Constitutional Principle #5 format:
  - What went wrong
  - Why it happened
  - How to fix it
  - Documentation link (if applicable)

- **FR-028**: System MUST detect port conflicts before starting containers
- **FR-029**: System MUST detect disk space issues before starting containers
- **FR-030**: System MUST validate license key format before starting Enterprise containers

#### Integration with Existing Features

- **FR-031**: All lifecycle commands MUST work with containers created via Python API (`IRISContainer.community()`)
- **FR-032**: All lifecycle commands MUST support containers created via docker-compose
- **FR-033**: System MUST preserve existing management commands (status, test-connection, enable-callin, reset-password)
- **FR-034**: System MUST automatically run `enable-callin` after container start if DBAPI is installed

#### Output & Logging

- **FR-035**: System MUST display progress indicators during container pull operations
- **FR-036**: System MUST display container startup progress (waiting for health check)
- **FR-037**: System MUST display container connection information after successful start (host, port, namespace)
- **FR-038**: Logs command MUST support `--tail <number>` to limit output lines
- **FR-039**: Logs command MUST support `--since <timestamp>` to filter by time

### Key Entities *(include if feature involves data)*

- **Container Configuration**: Represents user-specified settings for IRIS container including edition, ports, volumes, license, initial state
  - Attributes: edition (community/enterprise), container_name, ports, namespace, license_key, password, volumes, image_tag
  - Source: iris-config.yml file or zero-config defaults
  - Validation: YAML syntax, port availability, license key format, required fields

- **Running Container State**: Represents operational state of IRIS container
  - Attributes: container_id, status (starting/running/stopped), health (healthy/unhealthy), uptime, port_mappings
  - Relationships: Associated with Container Configuration that created it
  - Lifecycle: Created by `start`/`up`, modified by `restart`, terminated by `stop`, removed by `remove`

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

## Success Criteria

This feature will be considered successful when:

1. Users can start an IRIS container with a single CLI command
2. Zero-config defaults work without any configuration file
3. All container lifecycle operations work from CLI (no Python code required)
4. Error messages follow Constitutional Principle #5 format
5. CLI commands work with containers created via Python API or docker-compose
6. Integration tests verify all lifecycle transitions (start → stop → restart → remove)

## Constitutional Alignment

This feature aligns with:
- **Principle #4: Zero Configuration Viable** - CLI enables container management without writing Python code
- **Principle #5: Fail Fast with Guidance** - Error messages provide clear remediation steps
- **Principle #1: Automatic Remediation** - Automatic callin service enablement, health check waiting

---
