# Research: Fix IRIS Container Infrastructure Issues

**Feature**: 011-fix-iris-container
**Date**: 2025-01-13
**Status**: Complete

## Research Questions

### 1. Testcontainers Ryuk Cleanup Behavior

**Question**: How does testcontainers ryuk service work and why is it cleaning up CLI-managed containers?

**Findings**:

**What is Ryuk?**
- Ryuk is a container cleanup sidecar used by testcontainers library
- Purpose: Automatically remove containers when the creating process exits
- Runs as separate Docker container (`testcontainers/ryuk:0.5.1` or similar)
- Monitors container labels to detect "orphaned" containers

**How Ryuk Works**:
1. Testcontainers library starts ryuk container when first test container is created
2. Ryuk connects to Docker socket and monitors labels
3. Each testcontainers-managed container gets labels:
   - `org.testcontainers.session-id=<session_id>`
   - `org.testcontainers=true`
4. When Python process exits, ryuk cleanup period starts (default: 10 seconds)
5. Ryuk removes all containers with matching session-id

**Why CLI Containers Are Cleaned Up**:
- `testcontainers-iris` library is used in `IRISContainerManager.create_from_config()`
- This automatically adds testcontainers labels to containers
- When CLI command exits (e.g., `iris-devtester container up`), Python process ends
- Ryuk sees process exit, waits 10 seconds, then removes containers
- This is by design for pytest fixtures, but wrong for CLI usage

**Decision**: Use Docker SDK directly for CLI commands to bypass testcontainers lifecycle

**Rationale**:
- testcontainers-iris is designed for test fixtures (automatic cleanup)
- CLI commands need persistent containers (manual cleanup)
- Docker SDK gives full control over container lifecycle
- Can still use testcontainers-iris for pytest fixtures

**Alternatives Considered**:
1. ❌ Disable ryuk globally → Breaks pytest fixtures that rely on cleanup
2. ❌ Keep container reference in background process → Too complex, fragile
3. ✅ Use Docker SDK for CLI, testcontainers-iris for tests → Clean separation

**Implementation Approach**:
- Add `use_testcontainers` parameter to `IRISContainerManager.create_from_config()`
- Default to `False` for CLI commands (use Docker SDK)
- Default to `True` for pytest fixtures (use testcontainers-iris)
- Docker SDK code path: Create container without testcontainers labels

### 2. Volume Mounting with testcontainers-iris

**Question**: Why is `with_volume_mapping()` not applying volume mounts correctly?

**Findings**:

**Current Implementation** (Feature 010, iris_container_adapter.py:52-58):
```python
for volume in config.volumes:
    parts = volume.split(":")
    host_path = parts[0]
    container_path = parts[1]
    mode = parts[2] if len(parts) > 2 else "rw"
    container.with_volume_mapping(host_path, container_path, mode)
```

**Problem Diagnosis**:
- `testcontainers-iris` version 1.2.2 `with_volume_mapping()` API signature:
  - `with_volume_mapping(host_path: str, container_path: str, mode: str = "rw")`
- This should work, but testcontainers-python has known issues with volumes
- Volume mounts are applied during `container.start()`, not during configuration
- If container is immediately cleaned up by ryuk, volumes never get applied

**Root Cause**:
1. Primary: Ryuk cleanup prevents container from starting properly
2. Secondary: Volume mounting happens after `.start()`, which may not complete

**Decision**: Fix ryuk issue first (root cause), volume mounting will work after that

**Rationale**:
- Volume mounting code from Feature 010 is correct
- Issue is timing: container cleaned up before volumes applied
- Once containers persist, existing volume mounting code should work
- May need to verify volumes after `.start()` completes

**Verification Steps**:
1. Create container with `use_testcontainers=False` (Docker SDK)
2. Apply volumes directly via Docker SDK (not testcontainers)
3. Verify volumes exist in `container.attrs['Mounts']`
4. Test file accessibility via `docker exec`

**Implementation Approach**:
- When using Docker SDK (CLI commands):
  ```python
  container = docker_client.containers.create(
      image=config.get_image_name(),
      name=config.container_name,
      volumes={vol.host_path: {'bind': vol.container_path, 'mode': vol.mode}},
      ports={config.superserver_port: config.superserver_port},
      ...
  )
  container.start()
  ```

### 3. Container Persistence Strategies

**Question**: How should CLI-managed containers differ from pytest-managed containers?

**Findings**:

**Container Lifecycle Patterns**:

1. **Pytest Fixtures** (current, working):
   - Created via `IRISContainer.community()` or `IRISContainer.from_config()`
   - Automatic cleanup when fixture scope ends
   - testcontainers-iris + ryuk manage lifecycle
   - Short-lived (seconds to minutes)

2. **CLI Commands** (current, broken):
   - Created via `iris-devtester container up`
   - Should persist until `iris-devtester container remove`
   - Currently cleaned up by ryuk after CLI process exits
   - Need long-lived (30+ minutes for benchmarks)

3. **Benchmark Infrastructure** (current, broken):
   - Needs persistent container for test suite
   - Container must survive multiple test runs
   - Volume mounts required for workspace
   - Currently falls back to ad-hoc container without workspace

**Decision**: Implement dual-mode container creation

**Modes**:
- **Test Mode** (`use_testcontainers=True`): Uses testcontainers-iris, automatic cleanup
- **CLI Mode** (`use_testcontainers=False`): Uses Docker SDK directly, manual cleanup

**Rationale**:
- Test fixtures benefit from automatic cleanup (principle #3: Isolation by Default)
- CLI users expect manual lifecycle control (create → use → remove)
- Benchmark infrastructure needs CLI-style persistence
- Clean separation of concerns

**Implementation**:
```python
class IRISContainerManager:
    @staticmethod
    def create_from_config(config: ContainerConfig, use_testcontainers: bool = False):
        if use_testcontainers:
            # Use testcontainers-iris (automatic cleanup)
            return _create_with_testcontainers(config)
        else:
            # Use Docker SDK directly (manual cleanup)
            return _create_with_docker_sdk(config)
```

**Default Values**:
- CLI commands: `use_testcontainers=False`
- Pytest fixtures: `use_testcontainers=True`
- User can override via config parameter

### 4. Error "Failed to create container: 0" Root Cause

**Question**: What causes this cryptic error message and how do we fix it?

**Findings**:

**Error Message Analysis**:
- Message: "Failed to create container: 0"
- Exit code: 0 (success!)
- Contradiction: Reports failure with success exit code

**Investigation**:
- Traced to `translate_docker_error()` function in iris_container_adapter.py
- Current implementation catches generic `Exception` and reports exit code
- Exit code 0 likely means:
  1. Container creation succeeded
  2. Container started
  3. Container was immediately removed (ryuk)
  4. Verification step fails (container not found)
  5. Error handler sees exit code 0 from successful creation

**Root Cause**:
1. Container creation succeeds (exit code 0)
2. Ryuk cleanup removes container
3. Subsequent verification finds no container
4. Error reporting shows original exit code (0) instead of actual problem

**Decision**: Add post-creation verification step

**Implementation**:
```python
def create_from_config(config, use_testcontainers=False):
    try:
        if use_testcontainers:
            container = _create_with_testcontainers(config)
        else:
            container = _create_with_docker_sdk(config)

        # Verify container persists
        time.sleep(2)  # Give Docker time to settle
        docker_client = docker.from_env()
        try:
            docker_container = docker_client.containers.get(config.container_name)
            if docker_container.status not in ['running', 'created']:
                raise ValueError(
                    f"Container {config.container_name} exists but status is {docker_container.status}"
                )
        except docker.errors.NotFound:
            raise ValueError(
                f"Container {config.container_name} was created but immediately disappeared.\n"
                "\n"
                "What went wrong:\n"
                "  The container was created successfully but was removed by cleanup service.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check if testcontainers ryuk service is removing containers\n"
                "  2. Use Docker SDK mode for CLI commands (use_testcontainers=False)\n"
                "  3. Verify no conflicting Docker labels\n"
                "\n"
                "This is likely a testcontainers lifecycle issue.\n"
            )

        return container

    except Exception as e:
        raise translate_docker_error(e, config)
```

**Enhanced Error Messages**:
- Distinguish between creation failure, mount failure, cleanup
- Report actual container status when verification fails
- Provide actionable remediation steps
- Follow Constitutional Principle #5 (Fail Fast with Guidance)

## Summary of Decisions

### Primary Implementation Strategy

**Problem 1: Ryuk Cleanup**
- **Solution**: Dual-mode container creation (testcontainers vs Docker SDK)
- **Mode**: CLI commands use Docker SDK (bypass testcontainers labels)
- **Impact**: Containers persist until explicit removal

**Problem 2: Volume Mounting**
- **Solution**: Apply volumes directly via Docker SDK for CLI mode
- **Mode**: Use Docker volumes dict in `containers.create()`
- **Impact**: Volumes properly mounted and accessible

**Problem 3: Container Persistence**
- **Solution**: Post-creation verification with Docker SDK
- **Check**: Container exists and status is 'running' or 'created'
- **Impact**: Accurate error reporting, no "Failed to create container: 0"

### Implementation Priorities

1. **High Priority**: Implement Docker SDK path for CLI commands
   - Bypasses testcontainers lifecycle
   - Fixes ryuk cleanup issue
   - Enables proper volume mounting

2. **High Priority**: Add container persistence verification
   - Detect containers removed by cleanup
   - Provide constitutional error messages
   - Verify volume mounts accessible

3. **Medium Priority**: Enhance error messages
   - Distinguish creation/mount/cleanup failures
   - Include remediation steps
   - Link to documentation

### Testing Strategy

1. **Unit Tests**: Volume parsing, validation, error message formatting
2. **Integration Tests**: Real Docker containers with volume mounts
3. **Persistence Tests**: 30-minute container lifecycle test
4. **Regression Tests**: All 35 existing contract tests must pass

### Documentation Requirements

1. **Learnings Document**: `docs/learnings/testcontainers-ryuk-lifecycle.md`
   - Explain ryuk behavior
   - Document when to use testcontainers vs Docker SDK
   - Provide troubleshooting guide

2. **CHANGELOG**: Update with v1.2.2 release notes
   - Fix ryuk cleanup issue
   - Fix volume mounting
   - Enhanced error messages

3. **CLI Help**: Update command descriptions
   - Clarify container persistence behavior
   - Document volume mount syntax

## References

- [testcontainers-python documentation](https://testcontainers-python.readthedocs.io/)
- [testcontainers-iris source](https://github.com/intersystems-community/testcontainers-python-iris)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [Ryuk cleanup service](https://github.com/testcontainers/moby-ryuk)
- Feature 010 implementation (volume mounting code)
- Constitutional Principle #3 (Isolation by Default)
- Constitutional Principle #5 (Fail Fast with Guidance)
