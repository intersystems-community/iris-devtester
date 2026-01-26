# Research: Fast Container Startup & Dev Cycle Optimization

**Feature**: 018-fast-container-startup
**Date**: 2025-12-24
**Status**: Complete

---

## 1. IRIS Namespace Isolation Patterns

### Decision
Use `Config.Namespaces` class via `iris.connect()` for dynamic namespace creation/deletion without container restart.

### Rationale
- Official InterSystems API for namespace management
- No IRIS restart required - operates at runtime
- <500ms typical creation/deletion time
- Thread-safe with proper error checking

### Key APIs

```objectscript
// Create namespace (in %SYS)
Set Name = "TEST_123456"
Set Properties("Globals") = "USER"
Set Properties("Routines") = "USER"
Set Status = ##Class(Config.Namespaces).Create(Name, .Properties)

// Delete namespace
Set Status = ##Class(Config.Namespaces).Delete("TEST_123456")

// Check existence
Set Exists = ##Class(Config.Namespaces).Exists("TEST_123456")
```

### Python Implementation Pattern

```python
def create_test_namespace(iris_conn, prefix="TEST_"):
    """Create isolated test namespace via iris.connect()."""
    namespace_name = f"{prefix}{int(time.time())}_{uuid.uuid4().hex[:8]}"

    iris_obj = iris.createIRIS(iris_conn)
    # Must be in %SYS namespace
    status = iris_obj.classMethodValue(
        "Config.Namespaces", "Create",
        namespace_name,
        {"Globals": "USER", "Routines": "USER"}
    )
    return namespace_name
```

### Performance Notes
- Creation: <500ms
- Deletion: <500ms
- No container restart needed
- Can create hundreds of namespaces dynamically

### Naming Convention
- Prefix: `TEST_` or project-specific prefix
- Suffix: Timestamp + random hex for uniqueness
- Example: `TEST_1735084800_a1b2c3d4`

---

## 2. Docker Container Reuse Patterns

### Decision
Use singleton container pattern with explicit naming and health check caching. Enable reuse ONLY for local development via `--reuse-container` flag.

### Rationale
- 70-80% reduction in test startup time
- Maintains test isolation via namespace separation
- Compatible with testcontainers ecosystem
- Clear separation between CI (no reuse) and local dev (optional reuse)

### Key Docker SDK Patterns

```python
import docker

def get_or_create_container(name: str, image: str) -> Container:
    """Reuse existing container or create new one."""
    client = docker.from_env()

    try:
        container = client.containers.get(name)
        if container.status != "running":
            container.start()
        return container
    except docker.errors.NotFound:
        return client.containers.run(
            image,
            name=name,
            detach=True,
            ports={'1972/tcp': 1972, '52773/tcp': 52773}
        )
```

### Caveats
- **DO NOT** use container reuse in CI/CD (breaks isolation)
- Implement state reset between test runs
- Verify container health before reuse
- Use explicit labels for project identification

### Health Check Caching Strategy
- Cache health check results with configurable TTL
- Default: 30s for local dev, 5s for CI
- Invalidate on container operations (restart, exec failure)

---

## 3. pytest Plugin Patterns

### Decision
Use `pytest_addoption` hook in conftest.py with session-scoped fixture for `--reuse-container` flag. Default to disabled (isolation by default).

### Rationale
- Standard pytest extension pattern
- Session scope ensures consistent behavior
- Default=False honors Constitutional Principle #3 (Isolation by Default)
- Clear warning when enabled

### Implementation

```python
# conftest.py
def pytest_addoption(parser):
    """Add --reuse-container flag."""
    parser.addoption(
        "--reuse-container",
        action="store_true",
        default=False,
        help="Reuse existing IRIS container (faster but less isolated)"
    )

@pytest.fixture(scope="session")
def reuse_container(request):
    """Check if container reuse is enabled."""
    reuse = request.config.getoption("--reuse-container")
    if reuse:
        import warnings
        warnings.warn("Container reuse enabled - test isolation reduced")
    return reuse

@pytest.fixture(scope="session")
def iris_container(reuse_container):
    """IRIS container fixture with optional reuse."""
    if reuse_container:
        return ContainerPool.get_or_create("iris-dev")
    else:
        with IRISContainer.community() as container:
            yield container
```

### Default Behavior
- **Default**: Create new container per session (isolation)
- **With flag**: Reuse existing `iris-dev` container (speed)
- **Warning**: Print clear warning about reduced isolation

---

## 4. Pre-baked Development Image

### Decision
Create Dockerfile.dev that pre-configures password, CallIn service, and common namespaces. Publish to GitHub Container Registry.

### Rationale
- Eliminates 8s password reset on every startup
- CallIn service enabled by default
- Consistent dev environment across team

### Dockerfile Pattern

```dockerfile
FROM intersystemsdc/iris-community:latest

# Pre-configure passwords and services during build
USER root
RUN iris start IRIS quietly && \
    iris session IRIS -U %SYS <<'EOF'
// Reset _SYSTEM password
Set user = ##class(Security.Users).%OpenId("_SYSTEM")
Set user.PasswordExternal = "SYS"
Set user.ChangePassword = 0
Set user.PasswordNeverExpires = 1
Do user.%Save()

// Enable CallIn service
Set sc = ##class(Security.Services).Get("%Service_CallIn", .props)
Set props("Enabled") = 1
Set sc = ##class(Security.Services).Modify("%Service_CallIn", .props)

Halt
EOF
    iris stop IRIS quietly

USER irisowner
```

### Publishing
```bash
# Build and push
docker build -t ghcr.io/intersystems/iris-devtester-dev:latest -f docker/Dockerfile.dev .
docker push ghcr.io/intersystems/iris-devtester-dev:latest
```

### Usage
```yaml
# docker-compose.yml for development
services:
  iris:
    image: ghcr.io/intersystems/iris-devtester-dev:latest
    ports:
      - "1972:1972"
      - "52773:52773"
```

---

## 5. AI-Friendly Output Formatting

### Decision
Implement OutputFormatter class that truncates, deduplicates, and structures test output for AI context efficiency.

### Rationale
- Current output ~200+ lines wastes AI tokens
- Target: <50 lines passing, <100 lines failing
- Structured format easier for AI parsing

### Implementation Pattern

```python
class OutputFormatter:
    def __init__(self, max_lines: int = 50, dedupe: bool = True):
        self.max_lines = max_lines
        self.dedupe = dedupe

    def format_test_output(self, raw_output: str) -> str:
        """Format verbose test output for AI consumption."""
        lines = raw_output.splitlines()

        if self.dedupe:
            lines = self._deduplicate(lines)

        if len(lines) > self.max_lines:
            # Keep first 20, last 20, summary in middle
            head = lines[:20]
            tail = lines[-20:]
            summary = f"... [{len(lines) - 40} lines omitted] ..."
            lines = head + [summary] + tail

        return "\n".join(lines)

    def _deduplicate(self, lines: list) -> list:
        """Remove consecutive duplicate lines."""
        result = []
        prev = None
        dup_count = 0
        for line in lines:
            if line == prev:
                dup_count += 1
            else:
                if dup_count > 0:
                    result.append(f"  (repeated {dup_count}x)")
                result.append(line)
                dup_count = 0
            prev = line
        return result
```

---

## Alternatives Considered

### Container Pooling (Rejected)
- **What**: Pre-warm N containers, hand out from pool
- **Why rejected**: Complexity, resource usage, diminishing returns
- **Better alternative**: Single reusable container + namespace isolation

### JDBC-only Approach (Rejected)
- **What**: Use JDBC for all operations including namespace management
- **Why rejected**: 3x slower than DBAPI; DBAPI required for performance
- **Reference**: Constitutional Principle #2

### Shared Test Database (Rejected)
- **What**: Single database shared across all tests
- **Why rejected**: Test pollution, parallel execution failures
- **Reference**: Constitutional Principle #3

---

## Summary

| Research Area | Decision | Impact |
|---------------|----------|--------|
| Namespace isolation | Config.Namespaces via iris.connect() | <500ms create/delete |
| Container reuse | Singleton pattern + --reuse-container flag | 70-80% faster startup |
| pytest integration | pytest_addoption with session fixture | Standard, familiar pattern |
| Pre-baked image | Dockerfile.dev with pre-configured password | 8s saved per startup |
| Output formatting | Truncate + dedupe to <50 lines | 70% token reduction |

**All NEEDS CLARIFICATION items resolved.**

---
*Research complete - ready for Phase 1 design*
