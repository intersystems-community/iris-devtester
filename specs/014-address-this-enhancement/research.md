# Research: Defensive Container Validation

**Feature**: 014-address-this-enhancement
**Date**: 2025-01-17
**Status**: Complete

## Research Questions

### 1. Docker SDK Container Validation Best Practices

**Question**: What are the recommended patterns for validating Docker container state using the Docker SDK for Python?

**Findings**:

The Docker SDK for Python (`docker` package) provides comprehensive container inspection APIs:

1. **Container.attrs** - Full container metadata including:
   - `State.Status` - "running", "exited", "paused", etc.
   - `State.Running` - Boolean flag
   - `State.StartedAt` - Timestamp for staleness detection
   - `Id` - Current container ID (for stale reference detection)

2. **Container.exec_run()** - Execute commands to test accessibility:
   - Returns exit code + output
   - Can detect "container not running" errors
   - Used to verify IRIS is actually responsive

3. **Docker.containers.list()** - List containers by name:
   - Filter by name to find specific containers
   - Returns empty list if not found (not exception)
   - Supports `all=True` to include stopped containers

**Best Practice Pattern**:
```python
# 1. Get container by name (not ID - avoids stale reference)
containers = client.containers.list(filters={"name": container_name})

# 2. Validate existence
if not containers:
    # Container not found - list alternatives

# 3. Validate running state
container = containers[0]
if container.attrs["State"]["Status"] != "running":
    # Container exists but not running

# 4. Validate accessibility (exec test)
try:
    exit_code, output = container.exec_run("echo test")
    if exit_code != 0:
        # Container running but not accessible
except docker.errors.APIError:
    # Docker daemon communication issue
```

**References**:
- Docker SDK Documentation: https://docker-py.readthedocs.io/en/stable/containers.html
- testcontainers-python health checks: Uses similar pattern

---

### 2. Container Health Check Patterns

**Question**: How should we structure health checks for IRIS containers to distinguish between different failure modes?

**Findings**:

Health checks should test multiple layers:

1. **Docker Layer** (container running):
   - Check `State.Running` flag
   - Fast check (<100ms)
   - Detects if container stopped/crashed

2. **Network Layer** (port accessible):
   - Attempt TCP connection to exposed port
   - Detects network configuration issues
   - Medium speed (~500ms with timeout)

3. **Application Layer** (IRIS responsive):
   - Execute ObjectScript command via exec
   - Verify IRIS management portal responds
   - Slower check (~1-2s)

**Recommended Health Check Levels**:

```python
class HealthCheckLevel(Enum):
    MINIMAL = "minimal"      # Just check if running
    STANDARD = "standard"    # Running + network accessible
    FULL = "full"           # Running + network + IRIS responsive
```

**Progressive Validation**:
- Start with minimal (fast fail)
- Only proceed to next level if previous passes
- Stop at first failure to minimize latency

**References**:
- Docker healthcheck: https://docs.docker.com/engine/reference/builder/#healthcheck
- Kubernetes liveness/readiness probes: Similar pattern
- Existing `container_status.py` implementation (progressive checks)

---

### 3. Error Message Formatting for Medical-Grade Reliability

**Question**: What error message structure best aligns with Constitutional Principle #5 (Fail Fast with Guidance)?

**Findings**:

Current `container_status.py` uses excellent pattern:

```
Container Status: my_iris
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running:    ✗ No

How to fix:
  docker start my_iris
  # or
  docker-compose up -d
```

**Recommended Structure** (from constitution):

```python
raise ContainerValidationError(
    "Container validation failed for '{name}'\n"
    "\n"
    "What went wrong:\n"
    "  {specific_issue}\n"
    "\n"
    "How to fix it:\n"
    "  {remediation_steps}\n"
    "\n"
    "Available containers:\n"
    "  {list_of_alternatives}\n"  # Only if not found
)
```

**Key Elements**:
1. **Header** - Clear statement of what failed
2. **What went wrong** - Specific diagnosis
3. **How to fix it** - Actionable remediation (copy-paste commands)
4. **Context** - Additional helpful info (alternatives, documentation links)

**Visual Formatting**:
- Use Unicode box drawing (━, ✓, ✗) for clarity
- Indent remediation steps for readability
- Include comments for context (# or, # for Docker Compose users)

**References**:
- CONSTITUTION.md Principle #5 examples
- Existing `container_status.py` implementation
- Rust error messages: Gold standard for helpful errors

---

### 4. Stale Container ID Detection

**Question**: How do we detect when a Docker container has been recreated with a new ID?

**Findings**:

**The Problem**:
- Container name stays the same: `iris_db`
- Container ID changes: `abc123...` → `def456...`
- Docker daemon may cache old ID in some contexts
- Operations using stale ID fail with "container not running"

**Detection Strategy**:

1. **Always use container NAME** (not ID) for lookups:
   ```python
   # ✅ RIGHT - immune to ID changes
   containers = client.containers.list(filters={"name": "iris_db"})

   # ❌ WRONG - breaks on recreation
   container = client.containers.get(container_id)
   ```

2. **Compare creation timestamp** (if caching ID):
   ```python
   cached_started_at = container_cache.get("started_at")
   current_started_at = container.attrs["State"]["StartedAt"]

   if cached_started_at != current_started_at:
       # Container was recreated
   ```

3. **Error message detection**:
   ```python
   if "is not running" in str(error) and container_exists(name):
       # Likely stale ID reference - suggest refresh
   ```

**Remediation**:
- Clear any cached container objects
- Re-fetch container by name
- Restart IRISContainer context manager
- Include these steps in error message

**References**:
- Issue description: Exactly this scenario
- Docker SDK uses name-based lookup internally
- testcontainers-python: Always fetches fresh by name

---

## Design Decisions

### Decision 1: Use Docker SDK (not subprocess)

**Rationale**:
- Existing code already uses Docker SDK via testcontainers
- More reliable than parsing subprocess output
- Better error handling and type safety
- Consistent with IRISContainer infrastructure

**Alternatives Considered**:
- subprocess + docker CLI: More fragile, parsing issues
- Direct Docker API calls: Over-engineered for this use case

---

### Decision 2: Progressive Validation Strategy

**Rationale**:
- Fast-fail principle (Constitutional #5)
- Don't waste time on slow checks if quick checks fail
- Clear diagnostic trail for debugging

**Implementation**:
```python
def validate_container(name: str, level: HealthCheckLevel) -> ValidationResult:
    # 1. Check existence (fast)
    if not container_exists(name):
        return ValidationResult.not_found(name, list_alternatives())

    # 2. Check running state (fast)
    if not container_running(name):
        return ValidationResult.not_running(name)

    # 3. Check accessibility (if requested)
    if level >= HealthCheckLevel.STANDARD:
        if not container_accessible(name):
            return ValidationResult.not_accessible(name)

    return ValidationResult.healthy(name)
```

---

### Decision 3: Dataclasses for Results (not dicts)

**Rationale**:
- Type safety (mypy checking)
- IDE autocomplete support
- Self-documenting structure
- Follows existing patterns in iris_devtester

**Structure**:
```python
@dataclass
class ValidationResult:
    success: bool
    status: ContainerHealthStatus
    message: str
    remediation_steps: List[str]
    available_containers: List[str] = field(default_factory=list)
```

---

### Decision 4: Integration with Existing container_status.py

**Rationale**:
- Don't duplicate functionality
- Enhance existing tools with new validation
- Maintain backward compatibility

**Migration Path**:
1. Create new `validation.py` module
2. Migrate `container_status.py` to use new validation
3. Keep existing CLI interface working
4. Add new methods to IRISContainer class

---

## Performance Considerations

### Target: <2 seconds for validation

**Breakdown**:
- Container existence check: <100ms (Docker SDK local)
- Running state check: <100ms (metadata only)
- Accessibility check: <1500ms (exec command with timeout)
- Total: ~1700ms < 2000ms target ✅

**Optimization Strategies**:
- Use short timeouts on exec commands (5s max)
- Cache Docker client connection
- Skip accessibility check by default (opt-in via level)
- Run checks in sequence (not parallel) for clear diagnostics

---

## Security Considerations

### Docker Socket Access

**Risk**: Container validation requires Docker socket access

**Mitigation**:
- Read-only operations only (no container modification)
- No privileged operations required
- Standard Docker SDK permissions
- Same security model as testcontainers (battle-tested)

**Best Practice**:
- Document Docker socket requirements
- Fail gracefully if Docker not accessible
- Clear error message about Docker daemon requirement

---

## Summary

**Research Complete**: All technical questions resolved

**Key Findings**:
1. Docker SDK provides robust container inspection APIs
2. Progressive validation (fast → slow) aligns with Constitutional #5
3. Always use container NAME (not ID) to avoid stale references
4. Error message structure from existing code is excellent template
5. Performance target <2s is achievable with timeouts

**Ready for Phase 1**: Design artifacts (data model, contracts, quickstart)

**No Blockers**: All NEEDS CLARIFICATION items resolved
