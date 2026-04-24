# containers/ — IRIS Container Lifecycle

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Docker container wrapper for InterSystems IRIS. Manages start/stop, health checks, CPF configuration, resource monitoring, and wait strategies. Largest subpackage (3695 lines, 10 files).

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `iris_container.py` | 668 | Core `IRISContainer` class; `.community()`, `.enterprise()`, `.light()` factories |
| `monitoring.py` | 1185 | Resource-aware health monitoring (CPU, memory, disk); largest file in project |
| `cpf_manager.py` | — | Merge custom CPF (Cache Parameter File) into container at startup |
| `dev_instance.py` | — | Persistent dev container with `idt-dev-data` Docker volume |
| `wait_strategies.py` | — | `IRISReadyWaitStrategy`: port open AND superserver ready |
| `validation.py` | — | `ContainerValidator`, pre-flight checks |
| `models.py` | — | `ContainerHealth`, `ContainerHealthStatus`, `HealthCheckLevel`, `ValidationResult` |
| `performance.py` | — | Performance metric collection |
| `monitor_utils.py` | — | Monitoring helper functions |

## PATTERNS

- **Always context manager**: `with IRISContainer.community() as iris:` — never bare `.start()`
- **Three editions**: `community` (default), `enterprise` (needs license), `light` (CI/CD, 580MB)
- **Builder pattern**: `.with_name()`, `.with_credentials()`, `.with_preconfigured_password()`
- **Factory returns self**: `IRISContainer.community()` returns configured instance, not started
- **Health = port + superserver**: Wait strategy checks both TCP 1972 AND IRIS superserver status

## GOTCHAS (from downstream consumers)

### Ryuk kills CLI containers on process exit
Testcontainers Ryuk registers an atexit handler that removes containers when the Python process exits. This is correct for pytest fixtures but **breaks CLI workflows** where containers must persist.
- **Pytest/library use**: Ryuk cleanup is the right behavior. Use `with IRISContainer.community() as iris:`.
- **CLI / long-running**: `idt container up` uses `use_testcontainers=False` internally (Docker SDK mode, no Ryuk labels). This is the correct pattern for persistent containers.
- **`IRISContainer.attach(name)`**: Reconnects to an existing container without Ryuk. Use this when `idt container up` started it.
- See: `docs/learnings/testcontainers-ryuk-lifecycle.md`

### Password change forced on community edition
Fresh IRIS community containers set `ChangePassword=1` for all users. Even `with_preconfigured_password("SYS")` does not clear this flag — it only sets the env var. DBAPI connections fail because the driver cannot handle the interactive password-change handshake.
- **Fix**: `IRISContainer.start()` calls `unexpire_all_passwords()` automatically after startup (line ~520 of `iris_container.py`). If you still hit this, use `idt test-connection --auto-fix` (auto-detects and remediates) or `idt container reset-password` explicitly.
- **Root cause**: `Security.Users.ChangePassword()` was removed in 2004. Must use `Security.Users.Modify()` with `props("ChangePassword")=0`.
- See: `docs/learnings/password-reset-changeflag-fix.md`, `docs/learnings/iris-security-users-api.md`

### Docker-in-Docker (DinD): get_mapped_port() raises ConnectionError on non-1972 ports
When iris-devtester runs **inside** a container (CI runners, GitHub Actions with Docker socket mounted, nested Docker), testcontainers detects DinD via `/.dockerenv` and sets `ConnectionMode.gateway_ip`. In this mode `DockerClient.port()` queries the Docker API for host-side port mappings — but those mappings are on the **outer** host, invisible to the inner daemon. The call returns `None`, and testcontainers raises `ConnectionError: Port mapping … is not available`.
- **Which calls fail**: `get_mapped_port(52773)` (web portal) and any port other than 1972. Port 1972 is cached as `_mapped_port` during `start()`, so it rarely hits this path.
- **Fix (v1.15.1+)**: `get_mapped_port()` now catches `ConnectionError` and returns the internal port directly. In DinD, the IRIS container is reachable via its bridge/gateway IP + internal port (no NAT needed).
- **Env var override**: Set `TESTCONTAINERS_CONNECTION_MODE=bridge_ip` to force the correct DinD mode, or `TC_HOST=<gateway-ip>` to pin the host.
- **Diagnosis**: `docker exec <runner> cat /.dockerenv` — if the file exists you're in DinD.
- See: `docs/learnings/iris-container-dind-port-mapping.md`

## ANTI-PATTERNS

- **DO NOT** call `iris.start()` without context manager — leaks containers
- **DO NOT** hardcode ports — use `get_exposed_port(1972)` for dynamic mapping
- **DO NOT** assume ARM64/x86 image compatibility — factories handle platform detection

## EXPORTS (`__init__.py`)

`IRISContainer`, `IRISReadyWaitStrategy`, `wait_for_iris_ready`, `ContainerHealthStatus`, `HealthCheckLevel`, `ValidationResult`, `ContainerHealth`, `validate_container`, `ContainerValidator`
