# Tasks: IRIS Server-Side Performance Monitoring Configuration

**Feature**: 002-set-default-stats
**Input**: Design documents from `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/
**Date**: 2025-10-05

## Overview

This task list implements automatic ^SystemPerformance monitoring configuration for iris-devtools containers. Following TDD principles, all contract tests are written BEFORE implementation, with tasks ordered by dependency and marked [P] for parallel execution where possible.

**Total Tasks**: 40
**Estimated Duration**: 12-16 hours (with parallel execution)

---

## Phase 3.1: Setup & Project Structure (Priority 1)

### T001: Create monitoring module structure

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: setup
**Priority**: P1
**Parallelizable**: No
**Dependencies**: None

**Acceptance Criteria**:
- [ ] File created with module docstring
- [ ] Imports configured (dataclasses, typing, datetime, enum)
- [ ] Module exports defined in `__all__`
- [ ] Constitutional principles documented in file header

**Constitutional Check**:
- Principle 4 (Zero Configuration): Module structure supports defaults
- Principle 8 (Document Blind Alleys): File header references research.md

**Implementation Notes**:
- Reference: `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/data-model.md`
- This is the central module for monitoring configuration
- Will contain: MonitoringPolicy, TaskSchedule, ResourceThresholds dataclasses

---

### T002: Create performance metrics module

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py`
**Type**: setup
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: None

**Acceptance Criteria**:
- [ ] File created with module docstring
- [ ] Imports for ObjectScript execution configured
- [ ] PerformanceMetrics dataclass skeleton defined
- [ ] Module exports in `__all__`

**Constitutional Check**:
- Principle 2 (DBAPI First): Uses existing connection management
- Principle 7 (Medical-Grade): Type hints for all functions

**Implementation Notes**:
- Reference: data-model.md section 5 (PerformanceMetrics)
- Will wrap $SYSTEM.Process.GetSystemPerformance() calls
- ObjectScript patterns from research.md section 5

---

### T003: [P] Create health checks module

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/utils/health_checks.py`
**Type**: setup
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: None

**Acceptance Criteria**:
- [ ] File created with module docstring
- [ ] Import structure for monitoring status checks
- [ ] Placeholder for monitoring health check function
- [ ] Module exports in `__all__`

**Constitutional Check**:
- Principle 5 (Fail Fast): Health checks provide clear status
- Principle 7 (Medical-Grade): Reliable monitoring of monitoring

**Implementation Notes**:
- Will contain health check utilities for monitoring system
- Validates monitoring is running correctly

---

## Phase 3.2: Data Models (Priority 1) ⚠️ CREATE BEFORE TESTS

### T004: [P] Implement MonitoringPolicy dataclass

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T001

**Acceptance Criteria**:
- [ ] MonitoringPolicy dataclass with all fields from data-model.md
- [ ] validate() method implements FR-021, FR-022 constraints
- [ ] to_objectscript() method generates policy creation code
- [ ] Clear error messages follow Constitutional Principle 5

**Constitutional Check**:
- Principle 4 (Zero Configuration): All fields have sensible defaults
- Principle 5 (Fail Fast): Validation errors include "What went wrong" + "How to fix it"

**Implementation Notes**:
- Reference: data-model.md section 1 (MonitoringPolicy)
- Interval range: 1-300 seconds (FR-021)
- Retention range: 300-86400 seconds (FR-022)
- ObjectScript template from research.md section 2

---

### T005: [P] Implement TaskSchedule dataclass

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T001

**Acceptance Criteria**:
- [ ] TaskSchedule dataclass with all fields from data-model.md
- [ ] to_objectscript() generates Task Manager creation code
- [ ] disable() and enable() methods generate ObjectScript
- [ ] Relationship to MonitoringPolicy documented

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Supports auto-disable/enable
- Principle 7 (Medical-Grade): Type-safe ObjectScript generation

**Implementation Notes**:
- Reference: data-model.md section 2 (TaskSchedule)
- ObjectScript patterns from research.md section 1
- Task Manager API documentation in contracts/task_manager_api.md

---

### T006: [P] Implement ResourceThresholds dataclass

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T001

**Acceptance Criteria**:
- [ ] ResourceThresholds dataclass with CPU/memory thresholds
- [ ] validate() enforces hysteresis (enable < disable)
- [ ] should_disable() logic for threshold detection
- [ ] should_enable() logic with hysteresis

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-disable/enable thresholds
- Principle 5 (Fail Fast): Validation prevents thrashing

**Implementation Notes**:
- Reference: data-model.md section 3 (ResourceThresholds)
- FR-017, FR-018, FR-023 requirements
- Hysteresis prevents on/off thrashing

---

### T007: [P] Implement CPFParameters dataclass

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T001

**Acceptance Criteria**:
- [ ] CPFParameters dataclass with startup/memory/misc settings
- [ ] to_objectscript() generates Config.CPF API calls
- [ ] to_dict() method for serialization
- [ ] Defaults match research.md recommendations

**Constitutional Check**:
- Principle 4 (Zero Configuration): Defaults work for most cases
- Principle 6 (Enterprise/Community): Same API both editions

**Implementation Notes**:
- Reference: data-model.md section 4 (CPFParameters)
- Research.md section 3 for CPF parameter values
- Optional feature - defaults usually sufficient

---

### T008: [P] Implement PerformanceMetrics dataclass

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T002

**Acceptance Criteria**:
- [ ] PerformanceMetrics dataclass with all metric fields
- [ ] from_objectscript_result() classmethod parses JSON
- [ ] exceeds_thresholds() method checks against ResourceThresholds
- [ ] below_thresholds() method for re-enable logic

**Constitutional Check**:
- Principle 2 (DBAPI First): Parses ObjectScript results
- Principle 7 (Medical-Grade): Robust JSON parsing with error handling

**Implementation Notes**:
- Reference: data-model.md section 5 (PerformanceMetrics)
- ObjectScript result format from research.md section 5
- JSON parsing from $SYSTEM.Process.GetSystemPerformance()

---

## Phase 3.3: Unit Tests for Data Models (Priority 1) [P]

### T009: [P] Unit test MonitoringPolicy validation

**File**: `/Users/tdyar/ws/iris-devtools/tests/unit/test_monitoring_policy.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T004

**Acceptance Criteria**:
- [ ] Test valid policy with defaults passes
- [ ] Test interval <1s raises ValueError with clear message
- [ ] Test interval >300s raises ValueError with clear message
- [ ] Test retention <300s raises ValueError with clear message
- [ ] Test retention >86400s raises ValueError with clear message
- [ ] Test to_objectscript() generates valid ObjectScript

**Constitutional Check**:
- Principle 5 (Fail Fast): All error messages tested
- Principle 7 (Medical-Grade): All validation paths covered

**Implementation Notes**:
- Use pytest for all tests
- Test error message format (includes "What went wrong", "How to fix it")
- Test boundary conditions (1s, 300s, 300s, 86400s)

---

### T010: [P] Unit test ResourceThresholds validation

**File**: `/Users/tdyar/ws/iris-devtools/tests/unit/test_resource_thresholds.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T006

**Acceptance Criteria**:
- [ ] Test valid thresholds with defaults pass
- [ ] Test should_disable() logic (CPU >90% OR memory >95%)
- [ ] Test should_enable() logic (CPU <85% AND memory <90%)
- [ ] Test hysteresis validation (enable >= disable fails)
- [ ] Test boundary conditions for all thresholds

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-disable logic tested
- Principle 7 (Medical-Grade): All edge cases covered

**Implementation Notes**:
- Test hysteresis prevents thrashing (enable must be < disable)
- Test OR logic for disable, AND logic for enable
- Test boundary values (exactly at threshold)

---

### T011: [P] Unit test PerformanceMetrics parsing

**File**: `/Users/tdyar/ws/iris-devtools/tests/unit/test_performance_metrics.py`
**Type**: unit
**Priority**: P1
**Parallelizable**: Yes [P]
**Dependencies**: T008

**Acceptance Criteria**:
- [ ] Test from_objectscript_result() parses valid JSON
- [ ] Test malformed JSON raises clear error
- [ ] Test exceeds_thresholds() with various metrics
- [ ] Test below_thresholds() with various metrics

**Constitutional Check**:
- Principle 5 (Fail Fast): JSON parsing errors are clear
- Principle 7 (Medical-Grade): All parsing paths tested

**Implementation Notes**:
- Mock ObjectScript JSON responses
- Test error handling for missing fields
- Test numeric range validation (0-100 for percentages)

---

## Phase 3.4: Contract Tests (Priority 2) ⚠️ MUST FAIL BEFORE IMPLEMENTATION

### T012: [P] Contract test monitoring_config_api

**File**: `/Users/tdyar/ws/iris-devtools/tests/contract/test_monitoring_config_api.py`
**Type**: contract
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T004, T006, T009, T010

**Acceptance Criteria**:
- [ ] Test configure_monitoring() with defaults
- [ ] Test configure_monitoring() with custom policy
- [ ] Test configure_monitoring() validation errors
- [ ] Test get_monitoring_status() returns correct state
- [ ] Test disable_monitoring() / enable_monitoring() cycle
- [ ] All tests MUST FAIL initially (TDD)

**Constitutional Check**:
- Principle 4 (Zero Configuration): Test default configuration
- Principle 5 (Fail Fast): Test all error messages

**Implementation Notes**:
- Reference: contracts/monitoring_config_api.md
- Use real IRIS container (testcontainers)
- Test all contract examples from API spec
- Performance: configure <2s, status <100ms, disable/enable <500ms

---

### T013: [P] Contract test task_manager_api

**File**: `/Users/tdyar/ws/iris-devtools/tests/contract/test_task_manager_api.py`
**Type**: contract
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T005, T009

**Acceptance Criteria**:
- [ ] Test create_task() returns task ID
- [ ] Test get_task_status() returns TaskStatus
- [ ] Test suspend_task() / resume_task() cycle
- [ ] Test delete_task() removes task permanently
- [ ] Test list_monitoring_tasks() filters correctly
- [ ] Test permission errors with clear messages
- [ ] All tests MUST FAIL initially (TDD)

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Task lifecycle tested
- Principle 5 (Fail Fast): Permission errors tested

**Implementation Notes**:
- Reference: contracts/task_manager_api.md
- Test Task Manager permissions (requires _SYSTEM)
- Test task execution (wait for actual runs)
- Performance: create <500ms, status <100ms

---

### T014: [P] Contract test resource_monitoring_api

**File**: `/Users/tdyar/ws/iris-devtools/tests/contract/test_resource_monitoring_api.py`
**Type**: contract
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T006, T008, T010, T011

**Acceptance Criteria**:
- [ ] Test get_resource_metrics() returns valid metrics
- [ ] Test check_resource_thresholds() returns correct actions
- [ ] Test start_resource_monitor() creates daemon thread
- [ ] Test stop_resource_monitor() stops gracefully
- [ ] Test auto_disable_monitoring() with tracking
- [ ] Test auto_enable_monitoring() respects state
- [ ] All tests MUST FAIL initially (TDD)

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-disable/enable tested
- Principle 7 (Medical-Grade): Resource monitor reliability tested

**Implementation Notes**:
- Reference: contracts/resource_monitoring_api.md
- Test threshold hysteresis prevents thrashing
- Test callback mechanism for threshold events
- Performance: metrics <100ms, threshold check <10ms

---

## Phase 3.5: API Implementation (Priority 2) - ONLY AFTER CONTRACT TESTS FAIL

### T015: Implement configure_monitoring()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: No
**Dependencies**: T012 (must fail first)

**Acceptance Criteria**:
- [ ] Function signature matches contract
- [ ] Creates MonitoringPolicy with defaults if None
- [ ] Executes ObjectScript to create policy
- [ ] Creates Task Manager task if enable_task_manager=True
- [ ] Returns applied policy with task_id populated
- [ ] Contract test T012 now PASSES

**Constitutional Check**:
- Principle 2 (DBAPI First): Uses existing connection management
- Principle 4 (Zero Configuration): Defaults work immediately

**Implementation Notes**:
- Reference: contracts/monitoring_config_api.md
- Use policy.to_objectscript() for policy creation
- Use TaskSchedule.to_objectscript() for task creation
- Error handling: ConnectionError, ValueError, PermissionError, RuntimeError

---

### T016: Implement get_monitoring_status()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T012 (must fail first)

**Acceptance Criteria**:
- [ ] Function signature matches contract
- [ ] Queries IRIS for current policy state
- [ ] Queries Task Manager for task status
- [ ] Returns MonitoringStatus with all fields
- [ ] Contract test T012 now PASSES for status checks

**Constitutional Check**:
- Principle 5 (Fail Fast): Clear status reporting
- Principle 7 (Medical-Grade): Reliable status queries

**Implementation Notes**:
- Reference: contracts/monitoring_config_api.md
- Query ^SystemPerformance policy via ObjectScript
- Query Task Manager task status
- Populate MonitoringStatus dataclass

---

### T017: [P] Implement disable_monitoring() and enable_monitoring()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T012 (must fail first)

**Acceptance Criteria**:
- [ ] disable_monitoring() signature matches contract
- [ ] enable_monitoring() signature matches contract
- [ ] Calls TaskSchedule.disable() / enable() ObjectScript
- [ ] Logs reason for disable (if provided)
- [ ] Contract test T012 enable/disable cycle PASSES

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Manual control when needed
- Principle 7 (Medical-Grade): Idempotent operations

**Implementation Notes**:
- Reference: contracts/monitoring_config_api.md
- Use TaskSchedule disable/enable methods
- Log all state changes for debugging
- Performance target: <500ms

---

### T018: Implement Task Manager functions (create, status, suspend, resume, delete, list)

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: No
**Dependencies**: T013 (must fail first)

**Acceptance Criteria**:
- [ ] create_task() matches contract signature
- [ ] get_task_status() matches contract signature
- [ ] suspend_task() matches contract signature
- [ ] resume_task() matches contract signature
- [ ] delete_task() matches contract signature
- [ ] list_monitoring_tasks() matches contract signature
- [ ] All contract tests T013 now PASS

**Constitutional Check**:
- Principle 2 (DBAPI First): Uses existing connections
- Principle 5 (Fail Fast): Clear error messages for task not found

**Implementation Notes**:
- Reference: contracts/task_manager_api.md
- Use ObjectScript patterns from research.md section 1
- Parse TaskStatus from ObjectScript results
- Filter tasks by "iris-devtools-" prefix for list operation

---

### T019: Implement get_resource_metrics()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T014 (must fail first)

**Acceptance Criteria**:
- [ ] Function signature matches contract
- [ ] Executes $SYSTEM.Process.GetSystemPerformance() via ObjectScript
- [ ] Parses JSON result using PerformanceMetrics.from_objectscript_result()
- [ ] Returns populated PerformanceMetrics
- [ ] Contract test T014 metrics test PASSES

**Constitutional Check**:
- Principle 2 (DBAPI First): Uses existing connection
- Principle 7 (Medical-Grade): Robust error handling

**Implementation Notes**:
- Reference: contracts/resource_monitoring_api.md
- ObjectScript pattern from research.md section 5
- Performance target: <100ms

---

### T020: [P] Implement check_resource_thresholds()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T014 (must fail first)

**Acceptance Criteria**:
- [ ] Function signature matches contract
- [ ] Returns ThresholdAction.DISABLE if should_disable()
- [ ] Returns ThresholdAction.ENABLE if should_enable()
- [ ] Returns ThresholdAction.MAINTAIN otherwise (hysteresis)
- [ ] Contract test T014 threshold tests PASS

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Decision logic for auto-management
- Principle 7 (Medical-Grade): Hysteresis prevents thrashing

**Implementation Notes**:
- Reference: contracts/resource_monitoring_api.md
- Use ResourceThresholds.should_disable() / should_enable()
- Implement hysteresis logic (maintain state in gap)

---

### T021: Implement start_resource_monitor() and stop_resource_monitor()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: No
**Dependencies**: T014 (must fail first), T019, T020

**Acceptance Criteria**:
- [ ] start_resource_monitor() signature matches contract
- [ ] Creates daemon background thread
- [ ] Thread periodically calls get_resource_metrics()
- [ ] Thread calls check_resource_thresholds()
- [ ] Invokes callback on threshold actions
- [ ] stop_resource_monitor() stops thread gracefully
- [ ] Contract test T014 thread tests PASS

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Background monitoring thread
- Principle 7 (Medical-Grade): Graceful thread shutdown

**Implementation Notes**:
- Reference: contracts/resource_monitoring_api.md
- Use threading.Thread with daemon=True
- Validate check_interval_seconds >= 10 (prevent overhead)
- Performance: thread overhead <0.1% CPU

---

### T022: [P] Implement auto_disable_monitoring() and auto_enable_monitoring()

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py`
**Type**: unit
**Priority**: P2
**Parallelizable**: Yes [P]
**Dependencies**: T014 (must fail first), T017

**Acceptance Criteria**:
- [ ] auto_disable_monitoring() signature matches contract
- [ ] Calls disable_monitoring() with reason
- [ ] Tracks auto_disabled state
- [ ] Logs disable event with metrics
- [ ] auto_enable_monitoring() only enables if auto-disabled
- [ ] Contract test T014 auto-disable/enable tests PASS

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-management implementation
- Principle 5 (Fail Fast): Clear logging of state changes

**Implementation Notes**:
- Reference: contracts/resource_monitoring_api.md
- Store auto_disabled state (in-memory or IRIS global)
- Don't re-enable if manually disabled
- Performance: <500ms including logging

---

## Phase 3.6: Container Integration (Priority 3)

### T023: Extend IRISContainer with monitoring configuration hook

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/iris_container.py`
**Type**: integration
**Priority**: P3
**Parallelizable**: No
**Dependencies**: T015, T016, T021

**Acceptance Criteria**:
- [ ] Add _configure_monitoring() private method
- [ ] Call _configure_monitoring() in container startup
- [ ] Check IRIS_DISABLE_MONITORING environment variable
- [ ] Log monitoring configuration status
- [ ] Graceful degradation if monitoring setup fails

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-configure on startup
- Principle 4 (Zero Configuration): Enabled by default
- Principle 7 (Medical-Grade): Non-fatal if monitoring fails

**Implementation Notes**:
- Reference: quickstart.md use cases
- Environment variable check: `os.getenv('IRIS_DISABLE_MONITORING') == 'true'`
- Startup overhead target: <2 seconds
- Log at INFO level for success, WARN for failure

---

### T024: [P] Add environment variable handling for monitoring config

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/iris_container.py`
**Type**: integration
**Priority**: P3
**Parallelizable**: Yes [P]
**Dependencies**: T023

**Acceptance Criteria**:
- [ ] Support IRIS_DISABLE_MONITORING=true to opt-out
- [ ] Support IRIS_MONITORING_INTERVAL (default 30)
- [ ] Support IRIS_MONITORING_RETENTION (default 3600)
- [ ] Document environment variables in docstring
- [ ] Validation for environment variable values

**Constitutional Check**:
- Principle 4 (Zero Configuration): Defaults + optional env config
- Principle 5 (Fail Fast): Validate env var values

**Implementation Notes**:
- Parse env vars in _configure_monitoring()
- Create MonitoringPolicy from env vars if present
- Fall back to defaults if env vars missing/invalid

---

### T025: Integrate resource monitoring thread with container lifecycle

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/iris_container.py`
**Type**: integration
**Priority**: P3
**Parallelizable**: No
**Dependencies**: T021, T023

**Acceptance Criteria**:
- [ ] Start resource monitoring thread in container startup
- [ ] Stop resource monitoring thread in container shutdown
- [ ] Handle thread cleanup on container errors
- [ ] Daemon thread doesn't block container exit

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-start monitoring thread
- Principle 7 (Medical-Grade): Reliable cleanup

**Implementation Notes**:
- Call start_resource_monitor() after configure_monitoring()
- Store thread reference for cleanup
- Use try/finally for cleanup in container context manager

---

## Phase 3.7: Integration Tests (Priority 3) [P]

### T026: [P] Integration test full monitoring lifecycle

**File**: `/Users/tdyar/ws/iris-devtools/tests/integration/test_monitoring_lifecycle.py`
**Type**: integration
**Priority**: P3
**Parallelizable**: Yes [P]
**Dependencies**: T023, T024, T025

**Acceptance Criteria**:
- [ ] Test container starts with monitoring enabled
- [ ] Test monitoring collects data over time
- [ ] Test manual disable/enable cycle
- [ ] Test monitoring survives IRIS restart (Task Manager persistence)
- [ ] Test container cleanup removes monitoring tasks

**Constitutional Check**:
- Principle 3 (Isolation): Each test gets own container
- Principle 7 (Medical-Grade): Full lifecycle tested

**Implementation Notes**:
- Use IRISContainer.community() in test fixtures
- Wait for multiple data collection cycles
- Verify Task Manager task exists and is running
- Test cleanup on container teardown

---

### T027: [P] Integration test auto-disable under resource pressure

**File**: `/Users/tdyar/ws/iris-devtools/tests/integration/test_auto_disable.py`
**Type**: integration
**Priority**: P3
**Parallelizable**: Yes [P]
**Dependencies**: T021, T022, T025

**Acceptance Criteria**:
- [ ] Test monitoring auto-disables when CPU >90%
- [ ] Test monitoring auto-disables when memory >95%
- [ ] Test monitoring auto-re-enables when resources recover
- [ ] Test hysteresis prevents thrashing
- [ ] Test callback events are triggered

**Constitutional Check**:
- Principle 1 (Automatic Remediation): Auto-disable tested
- Principle 7 (Medical-Grade): Resource protection tested

**Implementation Notes**:
- Simulate high CPU/memory load in IRIS
- Use lower thresholds for faster tests (e.g., 50%/60%)
- Verify disable event logged
- Verify re-enable after recovery

---

### T028: [P] Integration test environment variable configuration

**File**: `/Users/tdyar/ws/iris-devtools/tests/integration/test_monitoring_env_vars.py`
**Type**: integration
**Priority**: P3
**Parallelizable**: Yes [P]
**Dependencies**: T024

**Acceptance Criteria**:
- [ ] Test IRIS_DISABLE_MONITORING=true prevents monitoring
- [ ] Test IRIS_MONITORING_INTERVAL configures interval
- [ ] Test IRIS_MONITORING_RETENTION configures retention
- [ ] Test invalid env var values fail gracefully

**Constitutional Check**:
- Principle 4 (Zero Configuration): Env vars optional
- Principle 5 (Fail Fast): Invalid values validated

**Implementation Notes**:
- Set environment variables before container start
- Verify monitoring configuration matches env vars
- Test opt-out completely disables monitoring

---

## Phase 3.8: E2E Tests (Priority 4)

### T029: E2E test container startup to teardown with monitoring

**File**: `/Users/tdyar/ws/iris-devtools/tests/e2e/test_monitoring_e2e.py`
**Type**: e2e
**Priority**: P4
**Parallelizable**: No
**Dependencies**: T026, T027, T028

**Acceptance Criteria**:
- [ ] Test full container lifecycle with monitoring
- [ ] Verify monitoring auto-configured on startup
- [ ] Verify data collection throughout container lifetime
- [ ] Verify auto-disable/enable cycle under load
- [ ] Verify cleanup on container exit
- [ ] Test scenario from quickstart.md

**Constitutional Check**:
- Principle 7 (Medical-Grade): Full E2E workflow tested
- Principle 8 (Document Blind Alleys): Tests match documented use cases

**Implementation Notes**:
- Follow quickstart.md use case 1 (Debug a crash)
- Simulate realistic workload
- Verify performance overhead <2% CPU
- Test multiple containers in parallel (isolation)

---

## Phase 3.9: Optional Features (Priority 4) [P]

### T030: [P] Create Yaspe integration utilities (optional)

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/utils/yaspe_integration.py`
**Type**: unit
**Priority**: P4
**Parallelizable**: Yes [P]
**Dependencies**: T023

**Acceptance Criteria**:
- [ ] visualize_performance_data() function defined
- [ ] Check for yaspe import, raise ImportError with install instructions
- [ ] Export performance data from IRIS
- [ ] Call yaspe to generate visualizations
- [ ] Return path to generated report

**Constitutional Check**:
- Principle 4 (Zero Configuration): Optional dependency
- Principle 5 (Fail Fast): Clear error if yaspe not installed

**Implementation Notes**:
- Reference: research.md section 4 (Yaspe integration)
- Add to pyproject.toml: `yaspe = ["yaspe>=1.0.0"]`
- Document installation: `pip install 'iris-devtools[yaspe]'`
- Test with yaspe installed and without

---

### T031: [P] Implement CPF configuration (optional)

**File**: `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py`
**Type**: unit
**Priority**: P4
**Parallelizable**: Yes [P]
**Dependencies**: T007, T015

**Acceptance Criteria**:
- [ ] configure_cpf_parameters() function defined
- [ ] Executes CPFParameters.to_objectscript()
- [ ] Applied during container initialization
- [ ] Optional - defaults work without CPF config
- [ ] Document when CPF config needed

**Constitutional Check**:
- Principle 4 (Zero Configuration): Optional, defaults sufficient
- Principle 6 (Enterprise/Community): Works on both editions

**Implementation Notes**:
- Reference: research.md section 3 (CPF configuration)
- Apply during container init, before first connection
- Document that CPF changes require restart (not needed in containers)

---

### T032: [P] Add performance benchmarking utilities

**File**: `/Users/tdyar/ws/iris-devtools/tests/integration/test_monitoring_performance.py`
**Type**: integration
**Priority**: P4
**Parallelizable**: Yes [P]
**Dependencies**: T026, T029

**Acceptance Criteria**:
- [ ] Benchmark container startup with vs without monitoring
- [ ] Benchmark monitoring overhead at 30s intervals
- [ ] Benchmark resource monitoring thread overhead
- [ ] Document results in research.md or learnings/
- [ ] Verify <2% CPU overhead target met

**Constitutional Check**:
- Principle 7 (Medical-Grade): Performance impact measured
- Principle 8 (Document Blind Alleys): Benchmarks documented

**Implementation Notes**:
- Reference: research.md section 6 (performance benchmarks)
- Use pytest-benchmark or manual timing
- Test 10s, 30s, 60s intervals
- Document overhead at each interval

---

## Phase 3.10: Documentation & Polish (Priority 5) [P]

### T033: [P] Update README.md with monitoring section

**File**: `/Users/tdyar/ws/iris-devtools/README.md`
**Type**: doc
**Priority**: P5
**Parallelizable**: Yes [P]
**Dependencies**: T029

**Acceptance Criteria**:
- [ ] Add "Performance Monitoring" section
- [ ] Document zero-config usage
- [ ] Document environment variables
- [ ] Document opt-out with IRIS_DISABLE_MONITORING
- [ ] Link to quickstart.md for detailed examples

**Constitutional Check**:
- Principle 4 (Zero Configuration): Document defaults clearly
- Principle 8 (Document Blind Alleys): Link to research.md

**Implementation Notes**:
- Keep README section brief (2-3 paragraphs)
- Link to quickstart.md for examples
- Highlight constitutional principles (auto-config, auto-disable)

---

### T034: [P] Create monitoring overhead learnings document

**File**: `/Users/tdyar/ws/iris-devtools/docs/learnings/monitoring-overhead-benchmarks.md`
**Type**: doc
**Priority**: P5
**Parallelizable**: Yes [P]
**Dependencies**: T032

**Acceptance Criteria**:
- [ ] Document benchmark methodology
- [ ] Document results for 10s, 30s, 60s intervals
- [ ] Document CPU/memory overhead measurements
- [ ] Document recommendations for different use cases
- [ ] Link from research.md

**Constitutional Check**:
- Principle 8 (Document Blind Alleys): Document performance findings

**Implementation Notes**:
- Reference: research.md section 6 template
- Include graphs/tables if possible
- Document testing environment (hardware, IRIS edition)
- Recommendations: 30s dev/test, 60s+ production

---

### T035: [P] Add type hints and docstrings to all public APIs

**File**: All `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py` and `performance.py`
**Type**: unit
**Priority**: P5
**Parallelizable**: Yes [P]
**Dependencies**: T015-T022

**Acceptance Criteria**:
- [ ] All public functions have type hints
- [ ] All public functions have Google-style docstrings
- [ ] All classes have docstrings
- [ ] All dataclasses have field documentation
- [ ] mypy type checking passes

**Constitutional Check**:
- Principle 7 (Medical-Grade): Type safety throughout

**Implementation Notes**:
- Follow existing iris_devtools style
- Document all parameters, returns, raises
- Include usage examples in docstrings

---

### T036: [P] Run code quality checks (black, isort, flake8, mypy)

**File**: Repository root
**Type**: unit
**Priority**: P5
**Parallelizable**: Yes [P]
**Dependencies**: T035

**Acceptance Criteria**:
- [ ] black formatting applied to all files
- [ ] isort import sorting applied
- [ ] flake8 linting passes (no warnings)
- [ ] mypy type checking passes (strict mode)
- [ ] All checks pass in CI

**Constitutional Check**:
- Principle 7 (Medical-Grade): Code quality standards

**Implementation Notes**:
- Run: `black . && isort . && flake8 . && mypy iris_devtools/`
- Fix any warnings/errors
- Ensure pyproject.toml config is followed

---

### T037: Add pytest markers for test categorization

**File**: `/Users/tdyar/ws/iris-devtools/tests/conftest.py` and test files
**Type**: unit
**Priority**: P5
**Parallelizable**: No
**Dependencies**: T026-T029

**Acceptance Criteria**:
- [ ] Add `@pytest.mark.unit` to unit tests
- [ ] Add `@pytest.mark.contract` to contract tests
- [ ] Add `@pytest.mark.integration` to integration tests
- [ ] Add `@pytest.mark.e2e` to E2E tests
- [ ] Add `@pytest.mark.slow` to tests >5s
- [ ] Document markers in pytest.ini

**Constitutional Check**:
- Principle 7 (Medical-Grade): Test organization

**Implementation Notes**:
- Update pytest.ini with marker definitions
- Allow filtering: `pytest -m "not slow"` for fast tests
- Document in README how to run different test categories

---

### T038: Verify 95%+ test coverage

**File**: Repository root
**Type**: unit
**Priority**: P5
**Parallelizable**: No
**Dependencies**: T009-T014, T026-T029

**Acceptance Criteria**:
- [ ] Run pytest with coverage: `pytest --cov=iris_devtools --cov-report=html`
- [ ] Overall coverage ≥95% (constitutional requirement)
- [ ] monitoring.py coverage ≥95%
- [ ] performance.py coverage ≥95%
- [ ] All error paths covered
- [ ] Coverage report generated in htmlcov/

**Constitutional Check**:
- Principle 7 (Medical-Grade): 95%+ coverage required

**Implementation Notes**:
- Identify uncovered lines with coverage report
- Add tests for uncovered error paths
- Don't skip error handling tests
- Document coverage in CI checks

---

### T039: [P] Test quickstart.md examples manually

**File**: `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/quickstart.md`
**Type**: e2e
**Priority**: P5
**Parallelizable**: Yes [P]
**Dependencies**: T029, T033

**Acceptance Criteria**:
- [ ] Run "Quick Start" example - works as documented
- [ ] Run "Verify Monitoring" example - output matches
- [ ] Run "Custom Policy" example - configures correctly
- [ ] Run "Opt-Out" example - monitoring disabled
- [ ] Run "Resource Utilization" example - metrics displayed
- [ ] All examples execute without errors

**Constitutional Check**:
- Principle 5 (Fail Fast): Documentation is accurate
- Principle 8 (Document Blind Alleys): Examples are realistic

**Implementation Notes**:
- Copy/paste code from quickstart.md
- Run in fresh Python environment
- Verify output matches documented output
- Update quickstart.md if examples fail

---

### T040: [P] Create release checklist and version bump

**File**: `/Users/tdyar/ws/iris-devtools/pyproject.toml` and `CHANGELOG.md`
**Type**: doc
**Priority**: P5
**Parallelizable**: Yes [P]
**Dependencies**: T038, T039

**Acceptance Criteria**:
- [ ] Update version in pyproject.toml (e.g., 0.2.0)
- [ ] Add CHANGELOG.md entry for Feature 002
- [ ] Document new monitoring features
- [ ] Document new environment variables
- [ ] Document Yaspe optional dependency
- [ ] Tag release in git

**Constitutional Check**:
- Principle 8 (Document Blind Alleys): Release notes complete

**Implementation Notes**:
- Follow semantic versioning
- Document breaking changes (if any)
- Link to quickstart.md in CHANGELOG
- Don't push to PyPI yet (pending full iris-devtools release)

---

## Dependencies Graph

```
Phase 1 (Setup): T001, T002, T003 → Parallel
Phase 1 (Models): T004, T005, T006, T007, T008 → Parallel (all depend on T001/T002)
Phase 1 (Unit Tests): T009, T010, T011 → Parallel (depend on models)

Phase 2 (Contract Tests): T012, T013, T014 → Parallel (depend on models + unit tests)
  ↓ GATE: Contract tests MUST FAIL before implementation
Phase 2 (API Impl):
  - T015, T016, T017 → Sequential (monitoring API)
  - T018 → Sequential (task manager API)
  - T019, T020 → Parallel (resource metrics)
  - T021 → Sequential (depends on T019, T020)
  - T022 → Parallel (depends on T017)

Phase 3 (Integration): T023 → T024, T025 → Sequential chain
Phase 3 (Tests): T026, T027, T028 → Parallel (depend on T023-T025)

Phase 4 (E2E): T029 → Sequential (depends on all integration tests)
Phase 4 (Optional): T030, T031, T032 → Parallel

Phase 5 (Docs): T033, T034, T035, T036 → Parallel
Phase 5 (Polish): T037, T038 → Sequential
Phase 5 (Validation): T039, T040 → Parallel (depend on T038)
```

---

## Parallel Execution Examples

### Example 1: Phase 1 Data Models (T004-T008)
```bash
# All models can be created in parallel (different sections of same file)
# Execute after T001, T002 complete

Task: "Implement MonitoringPolicy dataclass in monitoring.py"
Task: "Implement TaskSchedule dataclass in monitoring.py"
Task: "Implement ResourceThresholds dataclass in monitoring.py"
Task: "Implement CPFParameters dataclass in monitoring.py"
Task: "Implement PerformanceMetrics dataclass in performance.py"
```

### Example 2: Phase 1 Unit Tests (T009-T011)
```bash
# All unit tests can run in parallel (different files)
# Execute after T004-T008 complete

Task: "Unit test MonitoringPolicy validation in tests/unit/test_monitoring_policy.py"
Task: "Unit test ResourceThresholds validation in tests/unit/test_resource_thresholds.py"
Task: "Unit test PerformanceMetrics parsing in tests/unit/test_performance_metrics.py"
```

### Example 3: Phase 2 Contract Tests (T012-T014)
```bash
# All contract tests can run in parallel (different files)
# CRITICAL: These MUST FAIL before starting T015+

Task: "Contract test monitoring_config_api in tests/contract/test_monitoring_config_api.py"
Task: "Contract test task_manager_api in tests/contract/test_task_manager_api.py"
Task: "Contract test resource_monitoring_api in tests/contract/test_resource_monitoring_api.py"
```

### Example 4: Phase 3 Integration Tests (T026-T028)
```bash
# All integration tests can run in parallel (different files)
# Execute after T023-T025 complete

Task: "Integration test full monitoring lifecycle in tests/integration/test_monitoring_lifecycle.py"
Task: "Integration test auto-disable under resource pressure in tests/integration/test_auto_disable.py"
Task: "Integration test environment variable configuration in tests/integration/test_monitoring_env_vars.py"
```

### Example 5: Phase 5 Documentation (T033-T036)
```bash
# All documentation tasks can run in parallel (different files)

Task: "Update README.md with monitoring section"
Task: "Create monitoring overhead learnings document in docs/learnings/"
Task: "Add type hints and docstrings to all public APIs"
Task: "Run code quality checks (black, isort, flake8, mypy)"
```

---

## Validation Checklist

**GATE: Verify before marking feature complete**

### Design Coverage
- [x] All 5 entities from data-model.md have implementations (T004-T008)
- [x] All 3 API contracts have contract tests (T012-T014)
- [x] All 3 API contracts have implementations (T015-T022)
- [x] All quickstart.md examples have test coverage (T039)

### Test Coverage
- [ ] All contract tests written BEFORE implementation (T012-T014 before T015+)
- [ ] All contract tests FAILED initially (TDD enforced)
- [ ] Unit tests for all data models (T009-T011)
- [ ] Integration tests for container lifecycle (T026-T028)
- [ ] E2E test for full workflow (T029)
- [ ] Overall coverage ≥95% (T038)

### Constitutional Compliance
- [ ] Principle 1 (Automatic Remediation): Auto-configure, auto-disable/enable tested
- [ ] Principle 2 (DBAPI First): Uses existing connection management
- [ ] Principle 3 (Isolation): Each test gets own container
- [ ] Principle 4 (Zero Configuration): Defaults work, env vars optional
- [ ] Principle 5 (Fail Fast): All error messages include "What went wrong" + "How to fix it"
- [ ] Principle 6 (Enterprise/Community): Tested on both editions
- [ ] Principle 7 (Medical-Grade): 95%+ coverage, all error paths tested
- [ ] Principle 8 (Document Blind Alleys): research.md updated, learnings documented

### Performance Targets
- [ ] Container startup overhead <2s (T029)
- [ ] Monitoring configuration <2s (T012)
- [ ] Resource metrics query <100ms (T014)
- [ ] Auto-disable detection <500ms (T027)
- [ ] CPU overhead <2% at 30s intervals (T032)
- [ ] Resource monitoring thread overhead <0.1% (T032)

### Documentation
- [ ] README.md updated (T033)
- [ ] quickstart.md examples tested (T039)
- [ ] Learnings documented (T034)
- [ ] Type hints on all public APIs (T035)
- [ ] CHANGELOG.md updated (T040)

---

## Notes

- **TDD Enforcement**: Contract tests (T012-T014) MUST be written and MUST FAIL before starting API implementation (T015+)
- **Parallel Execution**: Tasks marked [P] can run in parallel if using parallel task execution tools
- **Error Handling**: All errors must follow Constitutional Principle 5 format
- **Performance**: Benchmark and document actual performance (T032)
- **Coverage**: Must maintain ≥95% coverage per Constitutional Principle 7
- **No Claude Attribution**: Per user's global instructions, no Claude attribution in commits

---

**Task Status**: ✅ READY FOR IMPLEMENTATION

**Generated**: 2025-10-05
**Total Tasks**: 40
**Priority Distribution**:
- P1 (Foundation): 11 tasks (T001-T011)
- P2 (Core APIs): 11 tasks (T012-T022)
- P3 (Integration): 6 tasks (T023-T028)
- P4 (E2E + Optional): 4 tasks (T029-T032)
- P5 (Polish + Docs): 8 tasks (T033-T040)

**Estimated Completion**: 12-16 hours with parallel execution
