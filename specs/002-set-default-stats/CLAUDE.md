# CLAUDE.md - Feature 002: IRIS Performance Monitoring

**Branch**: `002-set-default-stats`
**For**: Claude Code agents implementing this feature
**Date**: 2025-10-05

## Quick Context

You are implementing automatic ^SystemPerformance monitoring configuration for iris-devtools containers. This feature ensures diagnostic data is always available when debugging IRIS issues.

**Core Requirement**: Auto-configure monitoring on container start (30s intervals, 1-hour retention) with auto-disable protection under resource pressure.

---

## Before You Start

### MUST READ (in order):
1. `/Users/tdyar/ws/iris-devtools/CONSTITUTION.md` - 8 non-negotiable principles
2. `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/spec.md` - Feature requirements
3. `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/research.md` - Technical decisions
4. `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/data-model.md` - Entity definitions
5. `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/contracts/` - API contracts

**DO NOT** start coding until you've read these files.

---

## Constitutional Requirements (NON-NEGOTIABLE)

### Principle 1: Automatic Remediation
- ✅ Auto-configure monitoring on container start (no manual setup)
- ✅ Auto-disable when CPU >90% or memory >95%
- ✅ Auto-re-enable when resources recover
- ❌ NEVER require manual intervention for monitoring setup

### Principle 2: DBAPI First, JDBC Fallback
- ✅ Use existing `iris_devtools.connections` for ObjectScript execution
- ✅ Leverage DBAPI connection when available
- ❌ DO NOT create new connection logic

### Principle 3: Isolation by Default
- ✅ Each container gets its own monitoring instance
- ✅ No shared state between containers
- ✅ Test fixtures must be isolated

### Principle 4: Zero Configuration Viable
- ✅ Defaults: 30s interval, 1-hour retention, all metrics enabled
- ✅ No required configuration
- ✅ Environment variable opt-out: `IRIS_DISABLE_MONITORING=true`

### Principle 5: Fail Fast with Guidance
- ✅ All errors include "What went wrong" + "How to fix it"
- ✅ Validation errors must be clear and actionable
- ✅ Include documentation links in error messages
- ❌ NEVER throw generic errors

### Principle 6: Enterprise Ready, Community Friendly
- ✅ Same code for both editions
- ✅ No license-specific logic
- ✅ Test on Community edition containers

### Principle 7: Medical-Grade Reliability
- ✅ 95%+ test coverage required
- ✅ All error paths must be tested
- ✅ Idempotent operations (safe to retry)
- ✅ Graceful degradation if monitoring setup fails

### Principle 8: Document the Blind Alleys
- ✅ Update `research.md` with any new findings
- ✅ Document why approaches were rejected
- ✅ Add performance benchmarks

---

## Implementation Checklist

### Phase 1: Core Monitoring Configuration (Priority 1)

- [ ] Create `iris_devtools/containers/monitoring.py`:
  - [ ] `MonitoringPolicy` dataclass with validation
  - [ ] `configure_monitoring()` function
  - [ ] `get_monitoring_status()` function
  - [ ] `disable_monitoring()` function
  - [ ] `enable_monitoring()` function

- [ ] Create `iris_devtools/containers/performance.py`:
  - [ ] `PerformanceMetrics` dataclass
  - [ ] `get_resource_metrics()` function
  - [ ] ObjectScript wrapper for `$SYSTEM.Process.GetSystemPerformance()`

- [ ] Extend `iris_devtools/containers/iris_container.py`:
  - [ ] Add `_configure_monitoring()` to container startup
  - [ ] Check `IRIS_DISABLE_MONITORING` environment variable
  - [ ] Log monitoring configuration status

### Phase 2: Task Manager Integration (Priority 1)

- [ ] Create task management functions in `monitoring.py`:
  - [ ] `create_task()` - Create Task Manager task
  - [ ] `get_task_status()` - Query task status
  - [ ] `suspend_task()` - Disable task
  - [ ] `resume_task()` - Re-enable task
  - [ ] `delete_task()` - Remove task
  - [ ] `list_monitoring_tasks()` - List all monitoring tasks

- [ ] Implement `TaskSchedule` dataclass
- [ ] ObjectScript templates for Task Manager operations

### Phase 3: Resource Monitoring & Auto-Disable (Priority 2)

- [ ] Create `ResourceThresholds` dataclass with validation
- [ ] Implement `check_resource_thresholds()` logic
- [ ] Create `start_resource_monitor()` background thread
- [ ] Implement `auto_disable_monitoring()` with logging
- [ ] Implement `auto_enable_monitoring()` with logging
- [ ] Add hysteresis logic to prevent thrashing

### Phase 4: CPF Configuration (Priority 3)

- [ ] Create `CPFParameters` dataclass
- [ ] Implement CPF configuration during container init
- [ ] Make CPF configuration optional (defaults work)
- [ ] Test with both Community and Enterprise editions

### Phase 5: Yaspe Integration (Priority 4 - Optional)

- [ ] Add `yaspe` to `pyproject.toml` optional dependencies
- [ ] Create `iris_devtools/utils/yaspe_integration.py`
- [ ] Implement `export_and_visualize()` helper
- [ ] Document installation: `pip install 'iris-devtools[yaspe]'`

### Phase 6: Testing (REQUIRED for all phases)

- [ ] Unit tests (`tests/unit/`):
  - [ ] `test_monitoring_policy.py` - Policy validation
  - [ ] `test_resource_thresholds.py` - Threshold logic
  - [ ] `test_performance_wrapper.py` - Metrics parsing

- [ ] Contract tests (`tests/contract/`):
  - [ ] `test_monitoring_config_api.py` - API contracts
  - [ ] `test_task_manager_api.py` - Task Manager API
  - [ ] `test_resource_monitoring_api.py` - Resource monitoring API

- [ ] Integration tests (`tests/integration/`):
  - [ ] `test_monitoring_lifecycle.py` - Full lifecycle
  - [ ] `test_auto_disable.py` - Resource pressure scenarios
  - [ ] `test_yaspe_integration.py` - Yaspe export (if implemented)

- [ ] E2E tests (`tests/e2e/`):
  - [ ] `test_monitoring_e2e.py` - Container startup to teardown

---

## Critical ObjectScript Patterns

### Pattern 1: Create Monitoring Policy
```objectscript
set policy = ##class(%SYS.PTools.StatsSQL).%New()
set policy.Name = "iris-devtools-default"
set policy.Interval = 30
set policy.Duration = 3600
set policy.RunTime = "continuous"
// ... set other properties ...
do policy.%Save()
do ##class(%SYS.PTools.StatsSQL).Start(policy.Name)
```

### Pattern 2: Create Task Manager Task
```objectscript
set task = ##class(%SYS.Task).%New()
set task.Name = "iris-devtools-monitor"
set task.TaskClass = "%SYS.Task.SystemPerformance"
set task.RunAsUser = "_SYSTEM"
set task.DailyIncrement = 30
set task.DailyIncrementUnit = "Second"
do task.%Save()
write task.%Id()  // Return task ID to Python
```

### Pattern 3: Get Resource Metrics
```objectscript
set metrics = ##class(%SYSTEM.Process).GetSystemPerformance()
set cpu = $LIST(metrics, 1)
set memory = $LIST(metrics, 5)
write "{"
write """cpu"": " _ cpu _ ", "
write """memory"": " _ memory
write "}"
```

### Pattern 4: Execute ObjectScript from Python
```python
# Via existing connection (DBAPI or JDBC)
cursor = conn.cursor()
result = cursor.execute("""
    // ObjectScript code here
    write "result"
""").fetchone()[0]
```

---

## File Locations (ABSOLUTE PATHS)

### Implementation Files
- `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/monitoring.py` - NEW
- `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/performance.py` - NEW
- `/Users/tdyar/ws/iris-devtools/iris_devtools/containers/iris_container.py` - EXTEND
- `/Users/tdyar/ws/iris-devtools/iris_devtools/utils/yaspe_integration.py` - NEW (optional)
- `/Users/tdyar/ws/iris-devtools/iris_devtools/utils/health_checks.py` - NEW

### Test Files
- `/Users/tdyar/ws/iris-devtools/tests/unit/test_monitoring_policy.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/unit/test_resource_thresholds.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/unit/test_performance_wrapper.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/contract/test_monitoring_config_api.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/contract/test_task_manager_api.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/contract/test_resource_monitoring_api.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/integration/test_monitoring_lifecycle.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/integration/test_auto_disable.py` - NEW
- `/Users/tdyar/ws/iris-devtools/tests/e2e/test_monitoring_e2e.py` - NEW

### Documentation Files
- `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/spec.md` - Feature spec
- `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/research.md` - Research
- `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/data-model.md` - Data models
- `/Users/tdyar/ws/iris-devtools/specs/002-set-default-stats/quickstart.md` - User guide
- `/Users/tdyar/ws/iris-devtools/docs/learnings/monitoring-overhead-benchmarks.md` - NEW (add after benchmarking)

---

## Common Pitfalls to Avoid

### ❌ DON'T: Create new connection management code
**Why**: Constitutional Principle 2 - Use existing DBAPI/JDBC connections
**Instead**: Use `iris_devtools.connections.get_connection()`

### ❌ DON'T: Hardcode monitoring intervals
**Why**: Constitutional Principle 4 - Must be configurable
**Instead**: Use `MonitoringPolicy` with validation

### ❌ DON'T: Throw generic errors
**Why**: Constitutional Principle 5 - Fail fast with guidance
**Instead**: Include "What went wrong" and "How to fix it"

### ❌ DON'T: Skip tests for error paths
**Why**: Constitutional Principle 7 - All error paths tested
**Instead**: Test every `raise` statement

### ❌ DON'T: Assume Task Manager always available
**Why**: Permissions may be limited
**Instead**: Graceful degradation with clear error message

### ❌ DON'T: Edit iris.cpf directly
**Why**: Error-prone, requires restart
**Instead**: Use `Config.CPF` API via ObjectScript

### ❌ DON'T: Monitor resources too frequently
**Why**: Overhead adds up
**Instead**: 60-second intervals for resource checks (separate from 30s data collection)

---

## Testing Strategy

### Unit Tests (Fast, No IRIS Required)
- Test `MonitoringPolicy.validate()` with valid/invalid inputs
- Test `ResourceThresholds.should_disable()` logic
- Test `check_resource_thresholds()` hysteresis
- Mock ObjectScript responses for `PerformanceMetrics` parsing

### Contract Tests (Real IRIS, Test API Contracts)
- Test each API function signature
- Verify error handling matches contracts
- Validate return types and structures
- Test idempotency (calling twice doesn't break)

### Integration Tests (Real IRIS, Full Workflows)
- Test full monitoring lifecycle (create → run → disable → enable → delete)
- Test auto-disable under simulated load
- Test Task Manager integration
- Test CPF configuration

### E2E Tests (Full Container Lifecycle)
- Test container startup with auto-configured monitoring
- Test monitoring survives IRIS restart
- Test opt-out via environment variable
- Test performance impact benchmarks

---

## Performance Targets

| Metric | Target | Why |
|--------|--------|-----|
| Container startup overhead | <2 seconds | Keep fast feedback loops |
| Monitoring configuration | <2 seconds | One-time setup acceptable |
| Resource check overhead | <100ms | Runs every 60 seconds |
| Query latency impact | <0.1ms p95 | Medical-grade = low overhead |
| CPU overhead (30s intervals) | <2% | Constitutional requirement |
| Memory overhead | <50MB | Reasonable for dev/test |

**IMPORTANT**: Benchmark and document actual performance. Update `research.md` with findings.

---

## Debugging Tips

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('iris_devtools.containers.monitoring')
logger.setLevel(logging.DEBUG)
```

### Check Task Manager in Management Portal
1. Navigate to System Operations → Task Manager
2. Look for tasks with prefix "iris-devtools-"
3. Check Last Run, Next Run, Status

### Query ^SystemPerformance Directly
```python
cursor = conn.cursor()
result = cursor.execute("""
    do ##class(%SYS.PTools.StatsSQL).ListProfiles()
""").fetchall()
print(result)  # Should show "iris-devtools-default" profile
```

### Verify CPF Settings
```python
cursor = conn.cursor()
result = cursor.execute("""
    do ##class(Config.Startup).Get(.startup)
    write startup.PerformanceStats
""").fetchone()[0]
print(f"PerformanceStats enabled: {result}")
```

---

## When You Get Stuck

### Error: "Permission denied" when creating tasks
**Cause**: User doesn't have Task Manager permissions
**Fix**: Tasks must be created as `_SYSTEM` user
**Code**:
```python
# Task creation must specify RunAsUser
schedule = TaskSchedule(run_as_user="_SYSTEM")
```

### Error: "Policy not found" after container restart
**Cause**: Policy not persisted or Task Manager task suspended
**Fix**: Ensure policy is saved and task is not suspended
**Code**:
```python
# Always check policy exists before starting
try:
    do ##class(%SYS.PTools.StatsSQL).Start("iris-devtools-default")
except:
    # Re-create policy if missing
    configure_monitoring(conn)
```

### Error: High CPU usage from monitoring
**Cause**: Collection interval too frequent
**Fix**: Increase interval or disable OS metrics
**Code**:
```python
policy = MonitoringPolicy(
    interval_seconds=60,         # Reduce frequency
    collect_vmstat=False,        # Disable OS metrics
    collect_iostat=False
)
```

---

## Definition of Done

Before marking this feature complete:

- [ ] All contract tests pass (100% of API contracts validated)
- [ ] All integration tests pass (real IRIS containers)
- [ ] All E2E tests pass (full lifecycle)
- [ ] Test coverage ≥95% (constitutional requirement)
- [ ] Performance benchmarks documented in `research.md`
- [ ] All constitutional principles verified
- [ ] Quickstart guide tested by fresh user
- [ ] Documentation updated in README.md
- [ ] No breaking changes to existing APIs
- [ ] Both Community and Enterprise editions tested

---

## Recent Changes & Learnings

### 2025-10-05: Initial Planning
- Decided on ^SystemPerformance over ^PERFMON (better for comprehensive monitoring)
- Decided on Task Manager over cron (container-friendly, IRIS-native)
- Decided on auto-disable at CPU>90% or memory>95% (self-protecting)
- Decided on Yaspe as optional dependency (community tool, proven)

*(Update this section as you implement)*

---

## Questions? Check These First

1. **How do I execute ObjectScript from Python?**
   → See "Critical ObjectScript Patterns" section above

2. **What's the difference between DBAPI and JDBC?**
   → Read `/Users/tdyar/ws/iris-devtools/CONSTITUTION.md` Principle 2

3. **How do I test with real IRIS containers?**
   → See existing tests in `/Users/tdyar/ws/iris-devtools/tests/integration/`

4. **Where do I put new code?**
   → See "File Locations" section above (use absolute paths)

5. **How do I handle errors?**
   → Follow Constitutional Principle 5: "What went wrong" + "How to fix it"

---

**Remember**: This feature codifies InterSystems best practices. Every decision in `research.md` represents real production experience. Build on that foundation.

**Status**: Ready for implementation following constitutional principles.
