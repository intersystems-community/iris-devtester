# IRIS Container Performance Optimization

**Created**: 2025-12-24
**Status**: Active research
**Impact**: 55+ second startup overhead per test run

## Problem Statement

IRIS container operations are the primary bottleneck in the iris-devtester development cycle:
- Fresh container startup: ~30-45 seconds
- Password reset + verification: ~8 seconds (fixed in v1.5.x, was 55s!)
- Health check stabilization: ~10-15 seconds
- **Total overhead per test session: ~50 seconds**

This makes TDD painful and discourages frequent testing.

## Recent Fixes (Feature 017)

**Password reset regression fixed** - Reduced from 55s to ~8s:
- `settle_delay`: 12s → 2s (correct API doesn't need long waits)
- `initial_backoff_ms`: 3000 → 1000 (faster retries)
- `max_retries`: 5 → 3 (fewer attempts needed)
- `timeout_ms`: 60000 → 10000 (10s hard cap)

## Root Cause Analysis

### 1. Password Expiration Lockout (55s delay)

**The Problem**: IRIS Community images ship with passwords that require change on first login. The current `reset_password()` flow:

1. Execute ObjectScript to set `PasswordExternal` (~2s)
2. Wait for IRIS to propagate changes (~4-6s on macOS due to VM networking)
3. Verify password works via connection test (~3-5 retries × 2s each)

**Proposed Solution**: Environment variable bypass
```bash
# Request to InterSystems: Support this in Community images
docker run -e ISC_PASSWORDS_EXPIRED=0 intersystemsdc/iris-community:latest
```

**Workaround in iris-devtester**: Pre-baked images with passwords already reset
```dockerfile
FROM intersystemsdc/iris-community:latest
# Reset password during image build, not container startup
RUN iris start IRIS && \
    iris session IRIS -U %SYS "Set u=##class(Security.Users).%OpenId(\"_SYSTEM\") Set u.PasswordExternal=\"SYS\" Set u.ChangePassword=0 Do u.%Save()" && \
    iris stop IRIS quietly
```

### 2. CallIn Service Verification

**The Problem**: DBAPI connections require CallIn service enabled. Current flow checks this on every connection.

**Optimization**: Skip verification if container marked as "ready"
```python
# Fast path for known-good containers
if container.is_verified:
    return get_connection_fast(container)  # Skip CallIn check
```

### 3. Health Check Layers

**Current layers** (each adds latency):
1. Docker running check (~50ms)
2. Exec accessibility (~200ms)
3. IRIS process check (~500ms)
4. Database responsiveness (~1-2s)
5. Monitor.State check (~500ms) - NEW in Feature 017

**Optimization**: Parallel checks + caching
```python
# Run layers 1-3 in parallel
# Cache results with 5s TTL
# Skip re-verification for recent checks
```

### 4. Container Reuse

**The Problem**: Each test creates a new container (isolation principle).

**Optimization Options**:

a) **Namespace isolation** (recommended):
```python
# Reuse container, isolate via namespaces
with IRISContainer.reuse("test-pool") as iris:
    ns = iris.create_namespace(f"TEST_{uuid4().hex[:8]}")
    # Run tests in isolated namespace
    iris.drop_namespace(ns)
```

b) **Persistent volume mounting**:
```yaml
# docker-compose.yml for dev
services:
  iris:
    volumes:
      - iris-data:/usr/irissys/mgr/user  # Persist USER database
```

c) **Container pooling**:
```python
# Pre-warm N containers, hand out from pool
pool = IRISContainerPool(size=3)
container = pool.acquire()  # Instant - already running
```

## Benchmarks

| Operation | Current | Optimized | Improvement |
|-----------|---------|-----------|-------------|
| Cold start | 90s | 90s | (unavoidable) |
| Warm start (reuse) | 90s | 5s | 18x |
| Password reset | 55s | 0s (pre-baked) | ∞ |
| Health check | 3s | 0.5s (cached) | 6x |
| Per-test overhead | 90s | 5s | 18x |

## Implementation Priority

1. **P0**: Container reuse via namespace isolation
   - Biggest impact, no upstream changes needed

2. **P1**: Pre-baked development image
   - Create `iris-devtester-dev:latest` with passwords pre-reset

3. **P2**: Health check caching
   - Already partially implemented (5s TTL)

4. **P3**: Request ISC_PASSWORDS_EXPIRED env var
   - File feature request with InterSystems

## Quick Wins for Developers

### Use persistent container during development

```bash
# Start once, reuse forever
docker run -d --name iris-dev \
  -p 1972:1972 -p 52773:52773 \
  -v iris-dev-data:/usr/irissys/mgr \
  intersystemsdc/iris-community:latest

# Reset password once
iris-devtester reset-password iris-dev

# Run tests against existing container
IRIS_HOST=localhost IRIS_PORT=1972 pytest tests/
```

### Skip container tests during fast iteration

```bash
# Unit tests only (no IRIS needed) - runs in <5s
pytest tests/unit/ tests/contract/ --no-cov -q

# Integration tests only when needed
pytest tests/integration/ -k "specific_test"
```

## Related Documentation

- [iris-container-readiness.md](iris-container-readiness.md) - Health check patterns
- [iris-security-users-api.md](iris-security-users-api.md) - Password reset patterns
- Feature 015: Password Reset Reliability (macOS timing issues)

## Action Items

- [ ] Implement namespace-based isolation (Feature 018?)
- [ ] Create pre-baked dev image in CI
- [ ] Add `--reuse-container` flag to pytest plugin
- [ ] File ISC_PASSWORDS_EXPIRED feature request
- [ ] Benchmark container pooling approach
