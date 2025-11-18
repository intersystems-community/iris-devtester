# Feature 014: Defensive Container Validation - Implementation Tasks

**Status**: Planning
**Branch**: `014-defensive-container-validation`
**Total Tasks**: 27
**Estimated Duration**: 2-3 days

---

## Phase 1: Setup & Preparation (T001-T003)

### T001: Create feature branch and directory structure
**File**: N/A (git operations)
**Dependencies**: None
**Constitutional**: Principle #4 (Zero Config - prepare for env discovery)

```bash
git checkout -b 014-defensive-container-validation
mkdir -p tests/contract/
mkdir -p tests/integration/containers/
```

**Deliverable**: Branch and test directories ready

---

### T002: [P] Create data model skeletons
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/models.py`
**Dependencies**: None
**Constitutional**: Principle #8 (Document design decisions)

Create empty dataclasses and enums with docstrings:
- `ContainerHealthStatus` enum (6 states)
- `HealthCheckLevel` enum (3 levels)
- `ContainerHealth` dataclass
- `ValidationResult` dataclass with factory methods

**Deliverable**: Type-hinted stubs with comprehensive docstrings

---

### T003: [P] Update package exports
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/__init__.py`
**Dependencies**: T002
**Constitutional**: Principle #4 (Zero Config - clean imports)

Add exports for new validation API:
```python
from .models import (
    ContainerHealthStatus,
    HealthCheckLevel,
    ContainerHealth,
    ValidationResult,
)
from .validation import ContainerValidator, validate_container

__all__ = [
    "IRISContainer",
    "ContainerHealthStatus",
    "HealthCheckLevel",
    "ContainerHealth",
    "ValidationResult",
    "ContainerValidator",
    "validate_container",
]
```

**Deliverable**: Clean public API surface

---

## Phase 2: Contract Tests (TDD - Tests First) (T004-T010)

### T004: Contract test - validate_container() standalone function
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T002, T003
**Constitutional**: Principle #5 (Fail Fast with Guidance)

Test scenarios:
- Valid container returns HEALTHY
- Invalid container ID returns DOES_NOT_EXIST
- Recreated container (stale ID) returns RECREATED
- Docker daemon down returns DOCKER_UNAVAILABLE
- Invalid input raises TypeError with guidance

**Deliverable**: 5+ test cases, all FAILING (Red phase)

---

### T005: [P] Contract test - ContainerValidator class
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T002, T003
**Constitutional**: Principle #7 (Medical-Grade Reliability)

Test scenarios:
- Constructor validation (invalid level raises)
- validate() method with caching
- clear_cache() method
- get_stats() returns validation metrics
- Thread safety (concurrent validations)

**Deliverable**: 8+ test cases, all FAILING (Red phase)

---

### T006: [P] Contract test - IRISContainer.validate() method
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T002, T003
**Constitutional**: Principle #1 (Automatic Remediation)

Test scenarios:
- validate() returns ValidationResult
- validate(level=MINIMAL) fast path
- validate(level=FULL) comprehensive checks
- Validation failure includes remediation steps

**Deliverable**: 6+ test cases, all FAILING (Red phase)

---

### T007: [P] Contract test - IRISContainer.assert_healthy() method
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T002, T003
**Constitutional**: Principle #5 (Fail Fast with Guidance)

Test scenarios:
- Healthy container passes silently
- Unhealthy container raises ContainerValidationError
- Error message includes status, reason, remediation
- Custom message parameter works

**Deliverable**: 5+ test cases, all FAILING (Red phase)

---

### T008: Contract test - ValidationResult factory methods
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T002
**Constitutional**: Principle #8 (Document patterns)

Test scenarios:
- ValidationResult.healthy() factory
- ValidationResult.unhealthy() factory
- ValidationResult.error() factory
- All factories set correct fields

**Deliverable**: 4+ test cases, all FAILING (Red phase)

---

### T009: Contract test - HealthCheckLevel behavior
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T002
**Constitutional**: Principle #4 (Zero Config defaults)

Test scenarios:
- MINIMAL level checks (container exists, running)
- STANDARD level checks (+ ports, basic SQL)
- FULL level checks (+ IRIS health, CallIn service)
- Default level is STANDARD

**Deliverable**: 5+ test cases, all FAILING (Red phase)

---

### T010: Contract test - Error message quality
**File**: `/Users/tdyar/ws/iris-devtester/tests/contract/test_container_validation_api.py`
**Dependencies**: T004-T007
**Constitutional**: Principle #5 (Fail Fast with Guidance)

Validate error messages include:
- What went wrong (clear diagnosis)
- How to fix it (actionable steps)
- Why it matters (context)
- Documentation links

**Deliverable**: Error message validation helper + 3+ test cases

---

## Phase 3: Core Implementation (TDD - Green Phase) (T011-T018)

### T011: Implement data models
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/models.py`
**Dependencies**: T004-T010 (tests define requirements)
**Constitutional**: Principle #7 (Medical-Grade types)

Implement:
- `ContainerHealthStatus` enum with descriptions
- `HealthCheckLevel` enum
- `ContainerHealth` dataclass with validation
- `ValidationResult` dataclass with factory methods
- Type hints for all fields

**Deliverable**: T008 tests turn GREEN

---

### T012: Implement validate_container() function
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/validation.py`
**Dependencies**: T011
**Constitutional**: Principle #1 (Automatic Remediation)

Implement standalone function:
- Input validation with helpful errors
- Docker client error handling
- Container existence check
- Stale ID detection (name mismatch)
- Returns ValidationResult

**Deliverable**: T004 tests turn GREEN

---

### T013: Implement ContainerValidator class (core logic)
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/validation.py`
**Dependencies**: T011, T012
**Constitutional**: Principle #7 (Medical-Grade caching)

Implement:
- Constructor with level validation
- validate() method routing (MINIMAL/STANDARD/FULL)
- Result caching with TTL (default 5s)
- Thread-safe cache implementation
- Validation statistics tracking

**Deliverable**: T005 tests turn GREEN (core logic)

---

### T014: Implement MINIMAL health checks
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/validation.py`
**Dependencies**: T013
**Constitutional**: Principle #4 (Fast defaults for CI)

Checks:
1. Container exists in Docker
2. Container is running (not paused/stopped)
3. Container name matches expected

**Performance**: <100ms target

**Deliverable**: MINIMAL level tests turn GREEN

---

### T015: Implement STANDARD health checks
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/validation.py`
**Dependencies**: T014
**Constitutional**: Principle #2 (DBAPI First)

Checks (all from MINIMAL plus):
4. Ports are exposed correctly
5. Basic DBAPI connection succeeds
6. Simple SQL query works (`SELECT 1`)

**Performance**: <1s target

**Deliverable**: STANDARD level tests turn GREEN

---

### T016: Implement FULL health checks
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/validation.py`
**Dependencies**: T015
**Constitutional**: Principle #2 (Validate CallIn service)

Checks (all from STANDARD plus):
7. CallIn service is enabled
8. IRIS system health check (`$SYSTEM.Status()`)
9. Namespace accessibility
10. Write permissions test

**Performance**: <3s target

**Deliverable**: FULL level tests turn GREEN

---

### T017: Implement IRISContainer.validate() method
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/iris_container.py`
**Dependencies**: T013-T016
**Constitutional**: Principle #1 (Automatic Remediation)

Add instance method:
```python
def validate(
    self,
    level: HealthCheckLevel = HealthCheckLevel.STANDARD
) -> ValidationResult:
    """Validate container health with optional remediation."""
```

Uses ContainerValidator internally with caching.

**Deliverable**: T006 tests turn GREEN

---

### T018: Implement IRISContainer.assert_healthy() method
**File**: `/Users/tdyar/ws/iris-devtester/iris_devtester/containers/iris_container.py`
**Dependencies**: T017
**Constitutional**: Principle #5 (Fail Fast with Guidance)

Add assertion method:
```python
def assert_healthy(
    self,
    level: HealthCheckLevel = HealthCheckLevel.STANDARD,
    message: Optional[str] = None
) -> None:
    """Assert container is healthy, raise if not."""
```

Raises `ContainerValidationError` with:
- Status and reason
- Remediation steps
- Custom message if provided

**Deliverable**: T007, T010 tests turn GREEN

---

## Phase 4: Integration Tests (T019-T022)

### T019: Integration test - Detect recreated containers
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/containers/test_container_validation_integration.py`
**Dependencies**: T011-T018
**Constitutional**: Principle #5 (Fail Fast detection)

Test scenario from quickstart.md:
1. Start container, save ID
2. Stop and remove container
3. Start new container with same name
4. Validate with old ID
5. Assert status == RECREATED

**Deliverable**: Real Docker container test

---

### T020: [P] Integration test - Health check levels
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/containers/test_container_validation_integration.py`
**Dependencies**: T011-T018
**Constitutional**: Principle #4 (Performance validation)

Test scenarios:
- MINIMAL completes <100ms
- STANDARD completes <1s
- FULL completes <3s
- Each level catches appropriate issues

**Deliverable**: Performance benchmarks validated

---

### T021: [P] Integration test - Cached validation performance
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/containers/test_container_validation_integration.py`
**Dependencies**: T013
**Constitutional**: Principle #7 (Medical-Grade caching)

Test scenarios:
- First validation takes normal time
- Second validation <10ms (cached)
- Cache expires after TTL
- clear_cache() forces revalidation

**Deliverable**: Cache performance validated

---

### T022: [P] Integration test - Docker daemon failure handling
**File**: `/Users/tdyar/ws/iris-devtester/tests/integration/containers/test_container_validation_integration.py`
**Dependencies**: T012-T018
**Constitutional**: Principle #5 (Fail Fast with Guidance)

Test scenario (simulated):
- Mock Docker client to raise ConnectionError
- Validate container
- Assert status == DOCKER_UNAVAILABLE
- Assert error message includes Docker startup steps

**Deliverable**: Graceful Docker failure handling

---

## Phase 5: Documentation & Polish (T023-T027)

### T023: Add docstrings and type hints
**Files**: All implementation files
**Dependencies**: T011-T018
**Constitutional**: Principle #8 (Document patterns)

Requirements:
- Google-style docstrings for all public APIs
- Type hints for all parameters/returns
- Examples in docstrings
- Links to related functions

**Deliverable**: mypy passes, docs build

---

### T024: [P] Create user documentation
**File**: `/Users/tdyar/ws/iris-devtester/docs/guides/container-validation.md`
**Dependencies**: T011-T022
**Constitutional**: Principle #4 (Zero Config examples)

Sections:
1. Quick start (zero config)
2. Health check levels explained
3. Common validation patterns
4. Troubleshooting guide
5. Performance tuning

**Deliverable**: User-facing guide

---

### T025: [P] Update CHANGELOG.md
**File**: `/Users/tdyar/ws/iris-devtester/CHANGELOG.md`
**Dependencies**: T011-T022
**Constitutional**: N/A

Add entry:
```markdown
## [Unreleased]

### Added
- Container validation API with 3 health check levels
- Stale container ID detection
- Cached validation for performance
- Assertion-style validation helper
- Comprehensive error messages with remediation
```

**Deliverable**: CHANGELOG updated

---

### T026: [P] Update README.md with validation example
**File**: `/Users/tdyar/ws/iris-devtester/README.md`
**Dependencies**: T011-T022
**Constitutional**: Principle #4 (Zero Config showcase)

Add example:
```python
from iris_devtester import IRISContainer

iris = IRISContainer.community()

# Quick health check
iris.assert_healthy()  # Raises if unhealthy

# Detailed validation
result = iris.validate(level=HealthCheckLevel.FULL)
if not result.is_healthy:
    print(f"Problem: {result.reason}")
    print(f"Fix: {result.remediation}")
```

**Deliverable**: README has validation example

---

### T027: Run full test suite and coverage report
**File**: N/A (CI validation)
**Dependencies**: T001-T026
**Constitutional**: Principle #7 (Medical-Grade 95%+ coverage)

Commands:
```bash
pytest tests/contract/test_container_validation_api.py -v
pytest tests/integration/containers/test_container_validation_integration.py -v
pytest --cov=iris_devtester.containers.validation --cov-report=html
pytest --cov=iris_devtester.containers.models --cov-report=html
```

**Acceptance Criteria**:
- All contract tests pass (20+ tests)
- All integration tests pass (15+ tests)
- Coverage ≥95% for validation.py
- Coverage ≥95% for models.py
- mypy passes with no errors
- black/isort formatting clean

**Deliverable**: Green CI, coverage report

---

## Execution Strategy

### Parallel Execution Groups

**Group 1** (T002, T003): Data models + exports
**Group 2** (T004-T009): Contract tests (different test classes)
**Group 3** (T020-T022): Integration tests (isolated scenarios)
**Group 4** (T024-T026): Documentation updates

### Critical Path

```
T001 → T002 → T011 → T012 → T013 → T014 → T015 → T016 → T017 → T018 → T027
```

**Estimated Timeline**:
- Phase 1 (Setup): 1 hour
- Phase 2 (Contract Tests): 4 hours
- Phase 3 (Implementation): 8 hours
- Phase 4 (Integration): 3 hours
- Phase 5 (Documentation): 2 hours

**Total**: ~18 hours (2-3 days with breaks)

---

## Constitutional Compliance Checklist

- [T001-T027] **Principle #1**: Automatic remediation in validation logic
- [T012-T018] **Principle #2**: DBAPI first for health checks
- [N/A] **Principle #3**: No database isolation needed (container-level)
- [T024, T026] **Principle #4**: Zero config examples throughout
- [T004, T007, T010, T018] **Principle #5**: Fail fast with guidance
- [N/A] **Principle #6**: Community edition compatible (no enterprise deps)
- [T005, T021, T027] **Principle #7**: Medical-grade reliability (caching, testing)
- [T023, T024] **Principle #8**: Document design decisions

---

## Definition of Done

Feature complete when:
1. ✅ All 27 tasks completed
2. ✅ All contract tests passing (20+ tests)
3. ✅ All integration tests passing (15+ tests)
4. ✅ Coverage ≥95% for new code
5. ✅ mypy type checking passes
6. ✅ Documentation complete (API + guide)
7. ✅ CHANGELOG and README updated
8. ✅ No regressions in existing tests
9. ✅ Performance targets met (MINIMAL <100ms, STANDARD <1s, FULL <3s)
10. ✅ Code review approved

---

## Notes

- **TDD Workflow**: Red (write test) → Green (implement) → Refactor (clean up)
- **Parallel Tasks**: Marked with [P], can run concurrently
- **Dependencies**: Listed explicitly, respect the critical path
- **Constitutional**: Every task links to relevant principle(s)

**Remember**: Tests define the contract, implementation satisfies the contract.
