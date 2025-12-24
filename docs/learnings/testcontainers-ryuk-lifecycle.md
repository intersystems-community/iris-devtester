# Testcontainers Ryuk Lifecycle Management

**Feature**: 011-fix-iris-container
**Date**: 2025-01-13
**Status**: Resolved
**Category**: Container Infrastructure

## Summary

Testcontainers ryuk cleanup service was immediately removing CLI-managed containers, breaking benchmark infrastructure that requires containers to persist for 30+ minutes.

## What is Testcontainers Ryuk?

Ryuk is a cleanup sidecar service that testcontainers-python uses to automatically remove containers when the Python process exits. This is essential for test fixtures but problematic for CLI commands.

**Key Characteristics:**
- Runs as a separate Docker container (`testcontainers/ryuk`)
- Monitors Python process lifecycle
- Removes containers with `org.testcontainers` labels when process exits
- Cleanup happens within 10-60 seconds after process termination

## Why It Interfered with CLI Commands

### The Problem

```bash
# User runs CLI command
$ iris-devtester container up

# Container created successfully with testcontainers-iris
✓ Container 'iris_db' created and started

# CLI exits (normal completion)
$ echo $?
0

# 30 seconds later...
$ docker ps | grep iris_db
# (no output - container was removed by ryuk!)
```

### Root Cause

CLI commands have a **different lifecycle** than pytest fixtures:

| Use Case | Expected Behavior | Cleanup Method |
|----------|------------------|----------------|
| **Pytest fixtures** | Automatic cleanup after test | ✅ Ryuk (perfect fit) |
| **CLI commands** | Manual cleanup when user decides | ❌ Ryuk (removes prematurely) |
| **Benchmark tests** | Persist for 30+ minutes | ❌ Ryuk (removes immediately) |

## The Solution: Dual-Mode Container Creation

### Implementation

We implemented two modes in `IRISContainerManager.create_from_config()`:

```python
# Mode 1: testcontainers-iris (pytest fixtures)
container = IRISContainerManager.create_from_config(
    config,
    use_testcontainers=True  # Automatic cleanup via ryuk
)

# Mode 2: Docker SDK (CLI commands)
container = IRISContainerManager.create_from_config(
    config,
    use_testcontainers=False  # Manual cleanup, no ryuk labels
)
```

### Key Differences

| Aspect | testcontainers Mode | Docker SDK Mode |
|--------|-------------------|-----------------|
| **Cleanup** | Automatic (ryuk) | Manual (user command) |
| **Labels** | `org.testcontainers.*` | None (no ryuk labels) |
| **Use Case** | Pytest fixtures | CLI commands |
| **Container API** | IRISContainer object | Docker SDK Container |
| **Persistence** | Until process exit | Until `docker rm` |

## When to Use Each Mode

### Use testcontainers Mode (`use_testcontainers=True`)

✅ **Pytest fixtures** - Automatic cleanup after tests
✅ **Temporary containers** - Need automatic removal
✅ **CI/CD pipelines** - Don't want orphaned containers
✅ **Unit tests** - Each test gets clean slate

```python
@pytest.fixture
def iris_container():
    config = ContainerConfig.default()
    container = IRISContainerManager.create_from_config(
        config,
        use_testcontainers=True  # Cleanup when fixture scope ends
    )
    yield container
    # Automatic cleanup by ryuk
```

### Use Docker SDK Mode (`use_testcontainers=False`)

✅ **CLI commands** - User controls lifecycle
✅ **Benchmark infrastructure** - Long-running tests (30+ minutes)
✅ **Development containers** - Persist across sessions
✅ **Manual testing** - Inspect container after command

```python
# In CLI command
container = IRISContainerManager.create_from_config(
    config,
    use_testcontainers=False  # Persists until explicit removal
)
```

## Evidence: Benchmark Success Rate

This fix directly solved the benchmark infrastructure failures:

| Metric | Before Fix | After Fix | Improvement |
|--------|-----------|-----------|-------------|
| **Tests Passing** | 0/24 (0.0%) | 22/24 (91.7%) | +91.7% |
| **Container Persistence** | ~30 seconds | Indefinite | ∞ |
| **Root Cause** | Ryuk cleanup | Resolved | Fixed |

## Technical Details

### Ryuk Container Detection

Ryuk identifies containers to clean up via labels:

```bash
# testcontainers mode - HAS ryuk labels
$ docker inspect iris_db --format '{{json .Config.Labels}}' | jq
{
  "org.testcontainers.session-id": "abc123...",
  "org.testcontainers": "true"
}

# Docker SDK mode - NO ryuk labels
$ docker inspect iris_db --format '{{json .Config.Labels}}' | jq
{}
```

### Docker SDK Container Creation

```python
def _create_with_docker_sdk(config: ContainerConfig) -> Container:
    """Create container without testcontainers labels."""
    client = docker.from_env()

    # Parse volumes
    volumes = {}
    for volume_str in config.volumes:
        spec = VolumeMountSpec.parse(volume_str)
        volumes[spec.host_path] = {
            'bind': spec.container_path,
            'mode': spec.mode
        }

    # Create without testcontainers labels (prevents ryuk)
    container = client.containers.create(
        image=config.get_image_name(),
        name=config.container_name,
        volumes=volumes or None,
        ports={
            f'{config.superserver_port}/tcp': config.superserver_port,
            f'{config.webserver_port}/tcp': config.webserver_port
        },
        detach=True
    )

    container.start()
    return container
```

## Troubleshooting

### Symptom: Container disappears after CLI command

**Diagnosis:**
```bash
# Check for testcontainers labels
docker inspect <container_name> --format '{{.Config.Labels}}'

# Check if ryuk is running
docker ps | grep ryuk
```

**Fix:** Ensure CLI uses `use_testcontainers=False`

### Symptom: Containers not cleaned up in tests

**Diagnosis:**
```bash
# Check for orphaned containers
docker ps -a | grep iris
```

**Fix:** Ensure pytest fixtures use `use_testcontainers=True`

### Symptom: "Failed to create container: 0" error

**Cause:** Container created successfully (exit code 0) but immediately removed by ryuk

**Fix:** Use Docker SDK mode for CLI commands

## Related Documentation

- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [testcontainers-python](https://testcontainers-python.readthedocs.io/)
- [testcontainers-iris](https://github.com/intersystems-community/testcontainers-iris)
- Feature 011 specification: `specs/011-fix-iris-container/spec.md`
- Constitutional Principle #3: Isolation by Default

## Lessons Learned

1. **Understand tool lifecycle assumptions** - testcontainers assumes test fixture lifecycle
2. **Choose the right abstraction** - CLI and test fixtures have different needs
3. **Label-based cleanup is powerful** - But can backfire if not controlled
4. **Docker SDK is always available** - When testcontainers doesn't fit, use the SDK directly

## Decision Record

**Date**: 2025-01-13
**Decision**: Dual-mode container creation (testcontainers for tests, Docker SDK for CLI)
**Rationale**: Preserves automatic cleanup benefits for tests while enabling persistent containers for CLI
**Alternatives Considered**:
1. ❌ Disable ryuk globally - Would break pytest fixture cleanup
2. ❌ Only use Docker SDK - Would lose testcontainers-iris convenience for tests
3. ✅ **Dual-mode approach** - Best of both worlds

**Result**: 0% → 92% benchmark pass rate, containers persist as expected
