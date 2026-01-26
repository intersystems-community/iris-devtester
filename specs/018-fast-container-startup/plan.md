# Implementation Plan: Fast Container Startup & Dev Cycle Optimization

**Branch**: `018-fast-container-startup` | **Date**: 2025-12-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-fast-container-startup/spec.md`

## Summary

Reduce IRIS container test cycle from ~90s to <15s via container reuse with namespace isolation, pre-baked dev images, health check caching, and AI-friendly output formatting to reduce token waste during assisted development.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: testcontainers-iris, docker, pytest, intersystems-irispython
**Storage**: In-memory cache (HealthCache), Docker volumes for persistence
**Testing**: pytest with contract tests, integration tests
**Target Platform**: Linux, macOS (Docker Desktop)
**Project Type**: single (Python library)
**Performance Goals**: <5s warm start, <100ms cached health check, <2s namespace creation
**Constraints**: Must work with both Community and Enterprise editions
**Scale/Scope**: Single developer workflow, CI/CD pipelines

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation Notes |
|-----------|--------|---------------------|
| 1. Automatic Remediation | ✅ PASS | Container reuse auto-detects and handles stale state |
| 2. Choose Right Tool | ✅ PASS | DBAPI for SQL, iris.connect() for namespace ops |
| 3. Isolation by Default | ✅ PASS | Namespace isolation preserves test independence |
| 4. Zero Configuration | ✅ PASS | Auto-detect `iris-dev` container; sensible defaults |
| 5. Fail Fast with Guidance | ✅ PASS | Clear errors when container unavailable |
| 6. Enterprise & Community | ✅ PASS | Pre-baked images for both editions |
| 7. Medical-Grade Reliability | ✅ PASS | Health check caching with TTL; graceful degradation |
| 8. Official IRIS API | ✅ PASS | Use iris.connect() for namespace operations |
| 9. Document Blind Alleys | ✅ PASS | Document why not container pooling (complexity) |

**Gate Status**: PASS - No violations requiring justification.

## Project Structure

### Documentation (this feature)
```
specs/018-fast-container-startup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/tasks command)
```

### Source Code (repository root)
```
iris_devtester/
├── containers/
│   ├── pool.py          # NEW: ContainerPool for reuse
│   ├── namespace.py     # NEW: TestNamespace management
│   └── health_cache.py  # NEW: HealthCache with TTL
├── testing/
│   └── pytest_plugin.py # MODIFY: Add --reuse-container flag
└── output/
    └── formatter.py     # NEW: AI-friendly output formatting

tests/
├── contract/
│   ├── test_container_pool_contract.py
│   ├── test_namespace_contract.py
│   └── test_health_cache_contract.py
├── integration/
│   ├── test_container_reuse.py
│   └── test_namespace_isolation.py
└── unit/
    ├── test_output_formatter.py
    └── test_health_cache.py

docker/
└── Dockerfile.dev       # NEW: Pre-baked dev image
```

**Structure Decision**: Single project layout (Python library). New modules under `iris_devtester/containers/` and `iris_devtester/output/`. Pre-baked image Dockerfile in `docker/`.

## Phase 0: Outline & Research

### Research Tasks

1. **Namespace isolation patterns**: How to create/cleanup namespaces quickly in IRIS
2. **Docker API for container reuse**: Patterns for detecting and connecting to existing containers
3. **pytest plugin patterns**: How to implement `--reuse-container` flag
4. **Pre-baked image best practices**: Dockerfile patterns for IRIS dev images

### Research Agents

Task 1: "Research IRIS namespace creation/deletion via ObjectScript for test isolation"
Task 2: "Find best practices for Docker container reuse in testcontainers"
Task 3: "Research pytest plugin patterns for custom command-line flags"
Task 4: "Find Dockerfile patterns for pre-configured IRIS images"

**Output**: research.md with all unknowns resolved

## Phase 1: Design & Contracts

*Prerequisites: research.md complete*

### Entity Design → data-model.md

1. **ContainerPool**: Singleton managing reusable containers
   - Fields: containers (dict), default_container_name, health_cache
   - Methods: acquire(), release(), get_or_create()

2. **TestNamespace**: Isolated namespace for test session
   - Fields: name, container_ref, created_at, cleanup_registered
   - Methods: create(), drop(), execute_sql()

3. **HealthCache**: Cached health check results
   - Fields: results (dict), ttl_seconds
   - Methods: get(), set(), invalidate()

4. **OutputFormatter**: Transforms verbose output
   - Fields: max_lines, dedupe_enabled
   - Methods: format_test_output(), summarize_logs()

### Contract Generation → contracts/

1. **ContainerPool API**: acquire/release semantics, health check integration
2. **TestNamespace API**: create/drop with isolation guarantees
3. **HealthCache API**: get/set with TTL semantics
4. **OutputFormatter API**: format with line limits

### Test Scenarios → quickstart.md

1. Developer runs integration tests with reused container
2. Developer sees concise output (<50 lines passing, <100 lines failing)
3. Developer shares failure output with AI assistant

### Agent Context Update

Run: `.specify/scripts/bash/update-agent-context.sh claude`

**Output**: data-model.md, /contracts/*, quickstart.md, CLAUDE.md updated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Contract tests first for each new entity (ContainerPool, TestNamespace, HealthCache, OutputFormatter)
- Implementation tasks to make contract tests pass
- Integration tests for end-to-end container reuse workflow
- Dockerfile creation for pre-baked dev image
- pytest plugin modification for --reuse-container flag

**Ordering Strategy**:
- TDD order: Contract tests → Implementation → Integration tests
- Dependency order: HealthCache → ContainerPool → TestNamespace → OutputFormatter
- Mark [P] for parallel execution where possible

**Estimated Output**: 20-25 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*No violations requiring justification*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none needed)

---
*Based on IRIS DevTools Constitution v1.1.0*
