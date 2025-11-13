# Feature 009: Refactor CLI to use testcontainers-iris

## Executive Summary

Refactor the container lifecycle CLI commands (Feature 008) to use `testcontainers-iris` as the underlying implementation layer, reducing code duplication and maintenance burden while preserving all user-facing CLI functionality.

**Status**: Planning
**Target Release**: v1.2.0
**Dependencies**: testcontainers-iris>=1.2.2

---

## Background

Feature 008 implemented 7 CLI commands for container lifecycle management:
- `iris-devtester container up` - Create and start
- `iris-devtester container start` - Start existing
- `iris-devtester container stop` - Stop gracefully
- `iris-devtester container restart` - Restart with health checks
- `iris-devtester container status` - Display state
- `iris-devtester container logs` - View logs
- `iris-devtester container remove` - Remove container

**Current Implementation**: Custom Docker SDK wrapper in `iris_devtester/utils/docker_utils.py` (462 lines)

**Problem**: We're duplicating functionality that already exists in `testcontainers-iris`, a battle-tested package we already depend on.

**Decision**: Keep the CLI interface, replace the implementation layer.

---

## Analysis of testcontainers-iris API

### Available in testcontainers-iris:

```python
from testcontainers.iris import IRISContainer

# Constructor parameters
IRISContainer(
    image: str = "intersystemsdc/iris-community:latest",
    port: int = 1972,
    username: Optional[str] = None,
    password: Optional[str] = None,
    namespace: Optional[str] = None,
    driver: str = "iris",
    license_key: str = None,
    **kwargs
)

# Builder pattern methods (before .start())
.with_name(name: str)
.with_bind_ports(container: int, host: Optional[int] = None)
.with_env(key: str, value: str)
.with_volume_mapping(host: str, container: str, mode: str = 'ro')
.with_command(command: str)

# Lifecycle methods
.start() -> IRISContainer  # Creates and starts container
.stop(force=True, delete_volume=True) -> None
.get_logs() -> tuple[bytes, bytes]
.exec(command: Union[str, list[str]]) -> tuple[int, bytes]

# Access methods
.get_wrapped_container() -> Container  # Docker SDK container object
.get_docker_client() -> DockerClient
.get_connection_url(host=None) -> str
.get_exposed_port(port: int) -> int
```

**Key insight**: `get_wrapped_container()` returns the Docker SDK `Container` object, which has all the lifecycle methods we need:
- `.start()`
- `.stop()`, `.restart()`
- `.reload()` - refresh status
- `.status` - container state
- `.logs(stream=True/False, follow=True/False, tail=N)`
- `.remove()`

---

## What Stays vs What Goes

### ✅ STAYS (Keep as-is)

#### 1. CLI Interface (`iris_devtester/cli/container.py`)
- All 7 click commands and their signatures
- `--config`, `--detach`, `--timeout`, `--format`, `--follow` flags
- Exit codes (0, 1, 2, 3, 5)
- Help text and command descriptions

#### 2. Configuration Management (`iris_devtester/config/`)
- `ContainerConfig` - Pydantic model for YAML config
- `ContainerState` - Runtime state tracking
- `YamlLoader` - YAML file parsing
- Configuration hierarchy (explicit → file → env → defaults)

**Why keep**: These provide CLI-specific features not in testcontainers-iris:
- YAML configuration files
- Environment variable mapping
- Configuration validation
- State persistence

#### 3. Progress Indicators (`iris_devtester/utils/progress.py`)
- `ProgressIndicator` class
- Emoji-based status updates (⚡, ✓, ⏳, ✗)
- Human-friendly output formatting

**Why keep**: testcontainers-iris is designed for programmatic use in tests, not interactive CLI use.

#### 4. Health Checks (`iris_devtester/utils/health_checks.py`)
- Multi-layer health validation
- CallIn service enablement (automatic)
- Constitutional error messages
- Progress callback integration

**Why keep**: Our health checks are more comprehensive than testcontainers-iris:
- Layer 1: Container running
- Layer 2: Docker health check
- Layer 3: SuperServer port accessible
- Layer 4: CallIn service enabled

#### 5. All Contract Tests (`tests/contract/cli/`)
- 35 contract tests ensuring CLI behavior
- Test structure and assertions

**Why keep**: These define the contract that must be preserved.

---

### ❌ REPLACED (Swap with testcontainers-iris)

#### 1. `docker_utils.py` - Docker SDK Operations (462 lines → ~100 lines)

**Current** custom implementation:
```python
def get_docker_client() -> docker.DockerClient
def get_container(container_name: str) -> Optional[Container]
def pull_image(image: str, progress_callback: Optional[Callable] = None) -> Image
def create_container(config: ContainerConfig, progress_callback: Optional[Callable] = None) -> Container
def start_container(container: Container, progress_callback: Optional[Callable] = None) -> None
def stop_container(container: Container, timeout: int = 10, progress_callback: Optional[Callable] = None) -> None
def restart_container(container: Container, timeout: int = 10, progress_callback: Optional[Callable] = None) -> None
def remove_container(container: Container, remove_volumes: bool = False, progress_callback: Optional[Callable] = None) -> None
def get_container_logs(container: Container, tail: Optional[int] = None, follow: bool = False) -> Union[str, Iterator[str]]
```

**New** testcontainers-iris wrapper:
```python
from testcontainers.iris import IRISContainer

class IRISContainerManager:
    """Thin wrapper around testcontainers-iris for CLI use."""

    @staticmethod
    def create_from_config(config: ContainerConfig) -> IRISContainer:
        """Create IRISContainer from ContainerConfig."""
        container = IRISContainer(
            image=config.image,
            port=config.superserver_port,
            username=config.username,
            password=config.password,
            namespace=config.namespace,
            license_key=config.license_key if config.edition == "enterprise" else None
        )

        # Apply configuration
        container.with_name(config.container_name)
        container.with_bind_ports(config.superserver_port, config.superserver_port)
        container.with_bind_ports(config.webserver_port, config.webserver_port)

        # Add volume mappings
        if config.edition == "enterprise" and config.license_key_path:
            container.with_volume_mapping(
                str(config.license_key_path),
                "/usr/irissys/mgr/iris.key",
                mode="ro"
            )

        return container

    @staticmethod
    def get_existing(container_name: str) -> Optional[Container]:
        """Get existing container by name using Docker SDK."""
        client = docker.from_env()
        try:
            return client.containers.get(container_name)
        except docker.errors.NotFound:
            return None

    # Other helpers as needed...
```

**Benefit**: Reduce from 462 lines to ~100 lines of adapter code.

---

#### 2. Image Pulling Logic

**Current**: Custom progress callback for image pulling

**New**: Let testcontainers-iris handle it (it already does image pulling in `.start()`)

**Adaptation**: Wrap testcontainers-iris `.start()` with progress indicator:
```python
def start_with_progress(container: IRISContainer, progress: ProgressIndicator):
    progress.update("⏳ Pulling image (if needed)...")
    progress.update("⏳ Creating container...")
    container.start()  # testcontainers-iris handles pulling
    progress.update("✓ Container started")
```

---

#### 3. Port Conflict Detection

**Current**: Custom port conflict detection in `docker_utils.py`

**New**: testcontainers-iris already handles this (raises exception if port is in use)

**Adaptation**: Catch the exception and translate to constitutional error message:
```python
try:
    container.start()
except Exception as e:
    if "port is already allocated" in str(e):
        raise ValueError(
            f"Port {config.superserver_port} is already in use\n"
            "\n"
            "What went wrong:\n"
            "  Another container or service is using the SuperServer port.\n"
            "\n"
            # ... constitutional error message
        )
    raise
```

---

## Implementation Strategy

### Phase 1: Adapter Layer (Minimal Change)
1. Create `iris_devtester/utils/iris_container_adapter.py`
2. Implement `IRISContainerManager` class
3. Keep all existing CLI code but swap `docker_utils` → `iris_container_adapter`

### Phase 2: Integration
1. Update `container.py` CLI commands to use adapter
2. Preserve progress indicators and error messages
3. Run contract tests - all 35 must pass

### Phase 3: Cleanup
1. Remove `docker_utils.py` (462 lines)
2. Simplify health checks (leverage testcontainers-iris)
3. Update documentation

---

## Adaptation Points for CLI Needs

### 1. Progress Callbacks

**Challenge**: testcontainers-iris doesn't have progress callbacks

**Solution**: Wrap key operations with progress indicators:
```python
def up_command(config: ContainerConfig):
    progress = ProgressIndicator("Creating IRIS container")

    # Create IRISContainer from config
    progress.update("⏳ Configuring container...")
    iris = IRISContainerManager.create_from_config(config)

    # Start (pulls image if needed, creates, starts)
    progress.update("⏳ Pulling image and starting container...")
    iris.start()
    progress.update("✓ Container started")

    # Health checks
    progress.update("⏳ Performing health checks...")
    container = iris.get_wrapped_container()
    health_checks.wait_for_healthy(container, timeout=60, progress_callback=progress.update)
    progress.update("✓ Container healthy")

    # Enable CallIn
    progress.update("⏳ Enabling CallIn service...")
    health_checks.enable_callin_service(container)
    progress.update("✓ CallIn service enabled")

    progress.complete()
```

### 2. Long-Running Containers

**Challenge**: testcontainers-iris is designed for test-scoped containers (context manager pattern)

**Solution**: Don't use context manager, call `.start()` and `.stop()` directly:
```python
# ❌ DON'T do this (auto-cleanup)
with IRISContainer() as iris:
    # Container is removed when exiting context
    pass

# ✅ DO this (persistent container)
iris = IRISContainer().with_name("iris-devtest")
iris.start()
# Container persists until explicitly stopped/removed
```

### 3. Named Containers

**Challenge**: testcontainers-iris defaults to auto-generated names

**Solution**: Use `.with_name()` to set explicit name:
```python
container = IRISContainer().with_name(config.container_name)
```

### 4. Idempotent Operations

**Challenge**: CLI commands should be idempotent (safe retries)

**Solution**: Check container state before operations:
```python
def up_command(config: ContainerConfig):
    # Check if container already exists
    existing = IRISContainerManager.get_existing(config.container_name)

    if existing and existing.status == "running":
        click.echo("Container already running")
        return

    if existing:
        # Start existing container
        existing.start()
    else:
        # Create and start new container
        iris = IRISContainerManager.create_from_config(config)
        iris.start()
```

### 5. Constitutional Error Messages

**Challenge**: testcontainers-iris errors are not constitutional

**Solution**: Wrap exceptions and translate to 4-part format:
```python
try:
    container.start()
except Exception as e:
    # Translate to constitutional error
    raise translate_docker_error(e, config)
```

---

## Migration Checklist

- [ ] Create `iris_container_adapter.py` with `IRISContainerManager`
- [ ] Implement `create_from_config()` method
- [ ] Implement `get_existing()` for idempotency
- [ ] Update `container up` command to use adapter
- [ ] Update `container start` command
- [ ] Update `container stop` command
- [ ] Update `container restart` command
- [ ] Update `container status` command
- [ ] Update `container logs` command
- [ ] Update `container remove` command
- [ ] Run all 35 contract tests - verify 100% pass
- [ ] Remove `docker_utils.py`
- [ ] Update CHANGELOG for v1.2.0
- [ ] Update README with architectural change

---

## Benefits

### Code Reduction
- **Before**: 462 lines in `docker_utils.py`
- **After**: ~100 lines in `iris_container_adapter.py`
- **Reduction**: ~75% less code

### Maintenance
- Leverage battle-tested testcontainers-iris code
- Automatic updates when testcontainers-iris improves
- Shared bug fixes with broader community

### Consistency
- Same container behavior in CLI and Python API
- Unified test infrastructure

---

## Risks and Mitigation

### Risk 1: testcontainers-iris doesn't support all our features
**Mitigation**: Use `get_wrapped_container()` to access Docker SDK directly for anything not supported

### Risk 2: Breaking changes in testcontainers-iris
**Mitigation**: Pin to `testcontainers-iris>=1.2.2,<2.0.0` and test before upgrading

### Risk 3: Performance regression
**Mitigation**: Benchmark before/after and ensure no degradation

---

## Success Criteria

1. ✅ All 35 contract tests pass
2. ✅ Code reduction of >50% in container management
3. ✅ Same CLI interface (no breaking changes)
4. ✅ Same error messages (constitutional format preserved)
5. ✅ Same performance characteristics
6. ✅ Documentation updated

---

## Timeline

**Estimated effort**: 2-3 hours
- Phase 1 (Adapter): 1 hour
- Phase 2 (Integration): 1 hour
- Phase 3 (Cleanup): 30 minutes

**Target completion**: Next development session
**Target release**: v1.2.0

---

## Related Documents

- Feature 008 implementation: v1.1.0 release
- testcontainers-iris docs: https://github.com/caretdev/testcontainers-iris-python
- CONSTITUTION.md - Design principles
