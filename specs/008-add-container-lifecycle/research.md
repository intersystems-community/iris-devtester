# Research: Container Lifecycle CLI Commands

**Feature**: 008-add-container-lifecycle
**Date**: 2025-01-10
**Status**: Phase 0 Complete

## Research Questions

### R1: Configuration File Format - YAML vs JSON vs TOML

**Decision**: YAML (iris-config.yml)

**Rationale**:
- Docker ecosystem standard (docker-compose.yml, kubernetes.yaml)
- Human-readable, supports comments
- Less verbose than JSON for configuration
- Python support via PyYAML library (well-maintained)
- User expectation: docker-compose users familiar with YAML

**Alternatives Considered**:
- **JSON**: More verbose, no comments, harder to hand-edit
  - PRO: Native Python support (no dependency)
  - CON: Not docker-compose compatible, poor UX
- **TOML**: Python standard (pyproject.toml), good readability
  - PRO: Type-safe, clear syntax
  - CON: Less familiar to Docker users, requires tomli dependency
- **Environment variables only**: Simple, no file
  - PRO: 12-factor app pattern
  - CON: Complex configurations unwieldy, no version control

**Evidence**: Survey of similar tools:
- docker-compose: YAML
- testcontainers: YAML for external configs
- kubernetes: YAML
- GitHub Actions: YAML

**Reference**: [Docker Compose file reference](https://docs.docker.com/compose/compose-file/)

---

### R2: YAML Configuration Schema Design

**Decision**: Flat structure with nested sections, docker-compose inspired

**Schema**:
```yaml
# Edition selection
edition: community  # or: enterprise

# Container identification
container_name: iris_db  # optional, defaults to iris_db

# Network configuration
ports:
  superserver: 1972    # optional, defaults to 1972
  webserver: 52773     # optional, defaults to 52773

# IRIS configuration
namespace: USER        # optional, defaults to USER
password: SYS          # optional, defaults to SYS
license_key: ""        # required for enterprise edition

# Storage configuration
volumes:
  - ./data:/external   # optional, no default

# Docker configuration
image_tag: "latest"    # optional, defaults to latest
```

**Rationale**:
- Mirrors docker-compose.yml familiar structure
- Flat top-level for frequently-used settings
- Nested only where logical grouping exists (ports, volumes)
- Comments explain defaults (self-documenting)
- All fields optional except license_key for enterprise

**Validation Strategy**:
- Pydantic dataclass for type safety and validation
- Custom validators for:
  - Port numbers (1024-65535)
  - Edition enum (community/enterprise)
  - License key format (if enterprise)
  - Namespace naming rules

**Alternatives Considered**:
- **Deeply nested** (services.iris.ports.superserver): Too verbose for simple case
- **Docker Compose compatible**: Would require "services" wrapper, unnecessary complexity
- **Minimal (edition only)**: Insufficient for real-world use

---

### R3: Click Framework Patterns for Container Command Group

**Decision**: Command group with shared options pattern

**Pattern**:
```python
import click

@click.group(name="container")
@click.pass_context
def container_group(ctx):
    """Container lifecycle management commands."""
    pass

@container_group.command(name="up")
@click.option("--config", type=click.Path(exists=True), help="Path to iris-config.yml")
@click.option("--detach/--no-detach", default=True, help="Run in background")
@click.pass_context
def up(ctx, config, detach):
    """Create and start IRIS container from configuration."""
    # Implementation
    pass

# Register with main CLI
from iris_devtester.cli.main import cli
cli.add_command(container_group)
```

**Rationale**:
- Follows existing iris-devtester CLI pattern
- Subcommand structure: `iris-devtester container up`
- Shared validation logic via decorators
- Context object for state passing
- Help text auto-generated

**Best Practices from Click docs**:
- Use `@click.pass_context` for accessing parent command state
- Use `click.Path(exists=True)` for file validation
- Use `--flag/--no-flag` for boolean options
- Provide short help text (one line) and detailed help in docstring

**Reference**: [Click documentation - Commands and Groups](https://click.palletsprojects.com/en/8.1.x/commands/)

**Existing Code**:
- See `iris_devtester/cli/main.py` for current CLI structure
- Uses Click 8.0+ with command groups

---

### R4: Docker SDK vs Subprocess Patterns

**Decision**: Use Python Docker SDK for container operations, subprocess only for Docker validation

**Rationale**:
- **Docker SDK (docker-py)**:
  - Object-oriented, type-safe
  - Better error handling (structured exceptions)
  - No shell injection vulnerabilities
  - Easier testing (mockable)
  - IRISContainer already uses it (consistency)
  - Streaming logs support

- **subprocess + docker CLI**:
  - Already used for validation (docker --version)
  - Simple for one-off commands
  - Shell escaping complexity
  - String parsing of output (brittle)

**Pattern**:
```python
import docker

def container_start(config):
    """Start container using Docker SDK."""
    client = docker.from_env()

    # Pre-flight validation via subprocess
    subprocess.run(["docker", "--version"], check=True)

    # Container operations via SDK
    container = client.containers.run(
        image=config.image,
        name=config.container_name,
        ports=config.ports,
        detach=True
    )

    return container
```

**Alternatives Considered**:
- **subprocess only**: Simpler imports, but string parsing hell
- **docker-compose Python library**: Would enable compose.yml support, but heavy dependency
- **Testcontainers only**: Already integrated, but less control over lifecycle

**Evidence from iris-devtester**:
- IRISContainer uses docker-py extensively (see `iris_devtester/containers/iris_container.py`)
- Already in dependencies (via testcontainers-iris)
- Proven pattern in codebase

---

### R5: Health Check Strategies for Containers

**Decision**: Multi-layer health check with timeout

**Strategy**:
```python
def wait_for_healthy(container, timeout=60):
    """Wait for container to be healthy."""
    start = time.time()

    # Layer 1: Container running
    while time.time() - start < timeout:
        container.reload()
        if container.status != "running":
            time.sleep(1)
            continue
        break

    # Layer 2: Docker health check (if defined)
    if container.attrs.get("State", {}).get("Health"):
        while time.time() - start < timeout:
            container.reload()
            health = container.attrs["State"]["Health"]["Status"]
            if health == "healthy":
                break
            time.sleep(2)

    # Layer 3: IRIS-specific check (SuperServer port)
    while time.time() - start < timeout:
        try:
            sock = socket.create_connection(("localhost", 1972), timeout=2)
            sock.close()
            return True
        except:
            time.sleep(2)

    raise TimeoutError(f"Container not healthy after {timeout}s")
```

**Rationale**:
- Progressive validation (fast fail if container crashes)
- Docker health check honors container's own definition
- IRIS-specific check validates SuperServer availability (critical for connections)
- Timeout prevents infinite hangs
- Informative progress messages

**Alternatives Considered**:
- **Sleep only**: Fast but unreliable (race conditions)
- **Port check only**: Misses Docker-level issues
- **Docker health only**: Not all IRIS images have health checks defined
- **Exec into container**: Slow, requires shell access

**Evidence**:
- IRISContainer already has health check logic (see wait strategies)
- Production experience: 30s typical startup, 60s safe timeout
- Port 1972 check is fastest reliable indicator

**Reference**: [Docker SDK - Container health](https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.health)

---

### R6: Constitutional Error Message Format

**Decision**: Four-part error message structure

**Format**:
```
ConnectionError: Failed to connect to Docker daemon

What went wrong:
  Docker is not running or not accessible by current user.

Why it matters:
  Container lifecycle commands require Docker to create and manage IRIS containers.

How to fix it:
  1. Start Docker Desktop (macOS/Windows):
     → Open Docker Desktop application

  2. Start Docker daemon (Linux):
     → sudo systemctl start docker

  3. Verify Docker is running:
     → docker --version
     → docker ps

  4. Check user permissions (Linux):
     → sudo usermod -aG docker $USER
     → Log out and back in

Documentation:
  https://iris-devtester.readthedocs.io/troubleshooting/docker-not-running/
```

**Rationale**:
- Constitutional Principle #5 requirement
- **What went wrong**: Single sentence, no jargon
- **Why it matters**: Context for urgency/impact
- **How to fix it**: Step-by-step, platform-specific
- **Documentation**: Link for deep-dive

**Implementation Pattern**:
```python
def docker_not_running_error():
    """Generate constitutional error message for Docker not running."""
    return (
        "Failed to connect to Docker daemon\n"
        "\n"
        "What went wrong:\n"
        "  Docker is not running or not accessible by current user.\n"
        "\n"
        "Why it matters:\n"
        "  Container lifecycle commands require Docker to create and manage IRIS containers.\n"
        "\n"
        "How to fix it:\n"
        "  1. Start Docker Desktop (macOS/Windows):\n"
        "     → Open Docker Desktop application\n"
        "  \n"
        "  2. Start Docker daemon (Linux):\n"
        "     → sudo systemctl start docker\n"
        "  \n"
        "  3. Verify Docker is running:\n"
        "     → docker --version\n"
        "     → docker ps\n"
        "  \n"
        "  4. Check user permissions (Linux):\n"
        "     → sudo usermod -aG docker $USER\n"
        "     → Log out and back in\n"
        "\n"
        "Documentation:\n"
        "  https://iris-devtester.readthedocs.io/troubleshooting/docker-not-running/\n"
    )
```

**Common Error Scenarios**:
1. Docker not installed → Installation guide
2. Docker not running → Start commands
3. Port conflict → netstat + kill process steps
4. Disk space → df -h + cleanup guide
5. Invalid license key → Format example + where to get
6. Container already exists → Container name conflict resolution

**Reference**: See CONSTITUTION.md Principle #5 examples

---

### R7: Idempotency Strategy (Constitutional Principle #7)

**Decision**: Check-then-act pattern with explicit state validation

**Pattern**:
```python
def container_up_idempotent(config):
    """Idempotent container up - safe to call multiple times."""
    client = docker.from_env()

    # Check existing state
    try:
        container = client.containers.get(config.container_name)

        # Already running - success!
        if container.status == "running":
            click.echo(f"✓ Container '{config.container_name}' already running")
            return container

        # Exists but stopped - restart
        if container.status in ["exited", "stopped"]:
            click.echo(f"⚡ Restarting existing container '{config.container_name}'")
            container.restart()
            wait_for_healthy(container)
            return container

    except docker.errors.NotFound:
        # Doesn't exist - create new
        click.echo(f"⚡ Creating new container '{config.container_name}'")
        container = client.containers.run(...)
        wait_for_healthy(container)
        return container
```

**Rationale**:
- Multiple `up` calls are safe (no errors)
- User gets clear feedback about what happened
- No data loss or duplicate containers
- Restart preserves volumes and config

**Test Cases for Idempotency**:
```python
def test_up_idempotent():
    # First call - creates container
    result1 = cli_runner.invoke(["container", "up"])
    assert "Creating new container" in result1.output

    # Second call - reports already running
    result2 = cli_runner.invoke(["container", "up"])
    assert "already running" in result2.output
    assert result2.exit_code == 0  # Still success!

    # Stop then up - restarts existing
    cli_runner.invoke(["container", "stop"])
    result3 = cli_runner.invoke(["container", "up"])
    assert "Restarting existing" in result3.output
```

---

## Summary of Decisions

| Question | Decision | Key Rationale |
|----------|----------|---------------|
| Config Format | YAML | Docker ecosystem standard, human-readable |
| Config Schema | Flat with nested sections | docker-compose inspired, self-documenting |
| CLI Framework | Click command groups | Existing pattern, auto-help generation |
| Docker Integration | Docker SDK (docker-py) | Type-safe, already in use, mockable |
| Health Checks | Multi-layer (container/health/port) | Progressive validation, IRIS-specific |
| Error Messages | Four-part format (What/Why/How/Docs) | Constitutional requirement |
| Idempotency | Check-then-act pattern | Safe retries, clear feedback |

---

## Implementation Notes

### Dependencies to Add
```toml
# pyproject.toml additions
dependencies = [
    # ... existing dependencies
    "PyYAML>=6.0",  # YAML config file support
]
```

### File Changes Required
```
NEW:  iris_devtester/cli/container.py
NEW:  iris_devtester/config/yaml_loader.py
NEW:  examples/cli/iris-config.yml
NEW:  tests/unit/cli/test_container_cli.py
NEW:  tests/integration/cli/test_container_lifecycle_integration.py
NEW:  tests/contract/cli/test_container_cli_contract.py

MODIFY:  iris_devtester/cli/main.py  # Register container group
MODIFY:  pyproject.toml  # Add PyYAML dependency
MODIFY:  docs/cli-reference.md  # Document new commands
```

### Testing Strategy
- **Unit tests**: Mock Docker SDK, test CLI logic
- **Integration tests**: Real containers, end-to-end workflows
- **Contract tests**: CLI flags, config schema validation, error messages

---

## Blind Alleys Documented

### Why Not docker-compose Python Library?
**What we tried**: Using docker-compose library to enable compose.yml support

**Why it didn't work**:
- Heavy dependency (compose + its dependencies)
- Requires docker-compose installation (violates zero-config)
- Over-engineered for single container management
- Our use case simpler than full orchestration

**What we use instead**: Direct Docker SDK for container operations, YAML config inspired by compose but not compatible

**Evidence**: docker-compose library designed for multi-container orchestration, our need is single container lifecycle

**Decision**: Use compose-inspired YAML but don't require compose compatibility

---

## Next Phase

Phase 0 research complete. All NEEDS CLARIFICATION resolved. Ready for Phase 1 (Design & Contracts).

**Remaining work**: Generate data model, contracts, and quickstart documentation.
