# Feature Specification: Fast Container Startup & Dev Cycle Optimization

**Feature Branch**: `018-fast-container-startup`
**Created**: 2025-12-24
**Status**: Draft
**Input**: User description: "Pursue every known opportunity to speed up dev cycle and IRIS container startup/shutdown, including token-efficient AI-assisted development"

---

## Problem Statement

IRIS container operations create significant development friction:
- **Per-test overhead**: ~50-90 seconds for container spin-up
- **Password reset**: ~8 seconds (recently fixed from 55s)
- **Health checks**: ~3 seconds
- **AI token waste**: Long test output, redundant container logs, verbose error messages

This makes TDD painful, discourages frequent testing, and wastes AI context tokens during assisted development.

## User Scenarios & Testing

### Primary User Story

As a developer using iris-devtester with AI assistance, I want container operations to be fast and AI-friendly so that I can iterate quickly on code changes and get efficient AI guidance without burning through context tokens on repetitive output.

### Acceptance Scenarios

1. **Given** a developer runs integration tests against a pre-existing container, **When** tests complete, **Then** total test run time is under 15 seconds (excluding first cold start)

2. **Given** an AI assistant is helping debug test failures, **When** the test output is displayed, **Then** the output is concise (under 100 lines for a typical test run)

3. **Given** a developer starts their work session, **When** they run `pytest tests/integration/`, **Then** the container reuse kicks in automatically if a compatible container exists

4. **Given** tests fail, **When** the developer shares output with AI, **Then** error messages are structured, deduped, and actionable without scrolling

5. **Given** a fresh development environment, **When** developer runs first test, **Then** a pre-baked dev image is pulled (passwords already reset)

### Edge Cases

- What happens when existing container has stale state? System detects and resets to clean state
- What happens when multiple test sessions run concurrently? Namespace isolation prevents conflicts
- How does system handle container that crashed mid-test? Auto-restart with state verification

---

## Requirements

### Functional Requirements

**Container Reuse**
- **FR-001**: System MUST reuse existing IRIS containers when running tests, avoiding cold starts
- **FR-002**: System MUST provide namespace-based isolation so tests don't pollute each other
- **FR-003**: System MUST detect stale/crashed containers and handle gracefully

**Pre-baked Development Image**
- **FR-004**: Project MUST provide a pre-configured dev image with passwords already reset
- **FR-005**: Pre-baked image MUST have CallIn service enabled by default
- **FR-006**: Pre-baked image MUST be published to a container registry for easy pull

**Health Check Optimization**
- **FR-007**: System MUST cache health check results to avoid redundant verification
- **FR-008**: Cache TTL MUST be configurable (default: 30 seconds for dev, 5 seconds for CI)
- **FR-009**: System MUST support "skip verification" mode for known-good containers

**AI-Friendly Output**
- **FR-010**: Test output MUST be structured and concise by default
- **FR-011**: System MUST deduplicate repeated error messages
- **FR-012**: System MUST provide `--verbose` flag for full output when needed
- **FR-013**: Container logs MUST be summarized, not dumped in full
- **FR-014**: Error messages MUST fit in one screen (under 25 lines)

**Developer Workflow**
- **FR-015**: System MUST support `--reuse-container` pytest flag
- **FR-016**: System MUST auto-detect and use existing `iris-dev` container if present
- **FR-017**: System MUST provide clear guidance when container is unavailable

### Non-Functional Requirements

- **NFR-001**: Warm start (reused container) MUST complete in under 5 seconds
- **NFR-002**: Namespace creation MUST complete in under 2 seconds
- **NFR-003**: Health check with cache hit MUST return in under 100ms
- **NFR-004**: Test output for passing suite MUST be under 50 lines
- **NFR-005**: Test output for failing suite MUST be under 100 lines

### Success Criteria

1. **Test cycle time reduced by 80%**: Developers experience <15 second test runs for integration tests (warm start), down from ~90 seconds
2. **AI context efficiency improved by 70%**: Typical test output fits in ~50 lines vs ~200+ lines currently
3. **Zero-friction container reuse**: Developers don't manually manage containers; system handles automatically
4. **First-time setup under 2 minutes**: New developers can run tests within 2 minutes of cloning repo

---

### Key Entities

- **ContainerPool**: Manages reusable IRIS containers; tracks availability, health state, namespace allocations
- **TestNamespace**: Isolated database namespace for a single test session; auto-cleaned after tests
- **HealthCache**: Stores recent health check results with TTL; avoids redundant verification
- **OutputFormatter**: Transforms verbose test/container output into concise AI-friendly format

---

## Assumptions

1. **Docker Desktop available**: Developers have Docker installed and running
2. **Network connectivity**: Can pull images from container registry
3. **Sufficient resources**: Machine has ~4GB RAM available for IRIS container
4. **pytest as test runner**: Integration focuses on pytest ecosystem
5. **Single container per session**: Most developers run one test session at a time (pool size=1 default)

## Dependencies

- Feature 014 (Container Validation) - health check infrastructure
- Feature 015 (Password Reset) - verification patterns
- Feature 017 (IRIS Source Insights) - container health state detection

## Out of Scope

- Container orchestration for CI/CD (separate feature)
- Multi-node IRIS cluster testing
- Windows container support
- Performance profiling/tracing tools

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (none - all resolved with reasonable defaults)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
