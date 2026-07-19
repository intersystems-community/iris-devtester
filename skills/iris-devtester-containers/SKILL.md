---
name: iris-devtester-containers
description: IRISContainer factory patterns — community/enterprise/light/attach, CPF-first startup, graceful shutdown.
managed_by: iris-devtester
triggers:
  [container, iriscontainer, community, enterprise, attach, cpf, shutdown, testcontainers, ryuk]
prerequisites: [Docker, "Python 3.9+", "pip install iris-devtester[all]"]
related_skills: [iris-devtester, iris-devtester-connections]
metadata:
  version: 1.18.1
  author: InterSystems Community
---

# Skill: IRISContainer Lifecycle

`IRISContainer` (in `iris_devtester.containers`) wraps `testcontainers-iris` with
automatic password remediation, CallIn enablement, CPF merge, and graceful
shutdown. It is the single entry point for starting, attaching to, and stopping
IRIS containers.

## Choosing a factory

| Factory                                             | Use for                             | Cleanup                      | Notes                                                                                                                             |
| --------------------------------------------------- | ----------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `IRISContainer.community()`                         | Local dev, most tests               | Ryuk removes on process exit | Auto-detects ARM64 vs x86 image. ARM64 → `containers.intersystems.com/.../iris-community`; x86 → `intersystemsdc/iris-community`. |
| `IRISContainer.enterprise(license_key=...)`         | License-gated features              | Ryuk                         | Requires `iris.key`; falls back to `IRIS_LICENSE_KEY` env var. Raises `ValueError` if missing.                                    |
| `IRISContainer.light()`                             | CI/CD (smallest image, ~580 MB)     | Ryuk                         | Fastest startup.                                                                                                                  |
| `IRISContainer.health()` / `IRISContainer.ai_hub()` | FHIR / AI Hub editions              | Ryuk                         | No-ZPM editions (Feature 033).                                                                                                    |
| `IRISContainer.attach("name")`                      | Reconnect to a persistent container | **None** — persists          | For `idt container up` / docker-compose containers. Not managed by Ryuk.                                                          |
| `IRISContainer.dev()`                               | Persistent local dev instance       | Docker volume `idt-dev-data` | Survives restarts.                                                                                                                |

### community() vs enterprise() vs attach()

```python
from iris_devtester.containers import IRISContainer

# Community — ephemeral, context-managed (recommended for tests)
with IRISContainer.community() as iris:
    conn = iris.get_connection()

# Enterprise — needs a license key
with IRISContainer.enterprise(license_key="/path/to/iris.key") as iris:
    conn = iris.get_connection()

# Attach — reconnect to a container started outside this process
#   (e.g. `idt container up --name opsreview-iris`)
iris = IRISContainer.attach("opsreview-iris")
conn = iris.get_connection()
```

**Ryuk lifecycle gotcha**: `community()`/`enterprise()`/`light()` containers are
removed by Ryuk when the Python process exits. For a container that must outlive
the process, start it with `idt container up` (Docker SDK mode, no Ryuk) and
reconnect with `attach()`. See
[testcontainers-ryuk-lifecycle.md](../../docs/learnings/testcontainers-ryuk-lifecycle.md).

## Context manager is mandatory

```python
# CORRECT — cleanup + graceful shutdown guaranteed
with IRISContainer.community() as iris:
    ...

# FORBIDDEN — leaks the container, skips graceful shutdown
iris = IRISContainer.community()
iris.start()
```

## CPF-first startup

Merge a custom Configuration Parameter File (CPF) into the container at startup
— the grongierisc pattern used for the CPF-first password strategy (Feature 034).

```python
iris = IRISContainer.community().with_cpf_merge("./merge.cpf")
with iris:
    conn = iris.get_connection()
```

`with_cpf_merge()` accepts a path or inline CPF content and applies it before
IRIS finishes starting, so config (including password strategy) is in place on
first boot rather than patched afterward.

## Graceful shutdown (data integrity)

`docker stop` sends SIGKILL after its grace period; IRIS's default entrypoint
does not trap SIGTERM, so the write-image journal (WIJ) is not flushed and rows
can be lost even though tables survive. `IRISContainer.__exit__()` calls
`stop_gracefully()` automatically (v1.18.1+), which runs
`iris stop IRIS quietly` inside the container first.

```python
# Automatic — the context manager flushes the WIJ on exit
with IRISContainer.community() as iris:
    ...

# Manual (CLI / compose): stop IRIS cleanly BEFORE docker stop
#   docker exec <container> iris stop IRIS quietly
```

See [iris-container-graceful-shutdown.md](../../docs/learnings/iris-container-graceful-shutdown.md).

## Readiness, not just "running"

Port-open is not the same as IRIS-ready. Use the built-in wait strategy or
`$SYSTEM.Monitor.State()` (returns 0 when truly ready).

```python
with IRISContainer.community() as iris:
    iris.wait_for_ready(timeout=60)   # blocks until the Superserver is ready
    iris.enable_callin_service()      # REQUIRED before DBAPI connections
    conn = iris.get_connection()
```

See [iris-container-readiness.md](../../docs/learnings/iris-container-readiness.md).

## Anti-patterns

- **DO NOT** connect before `enable_callin_service()` — DBAPI needs the CallIn service.
- **DO NOT** hardcode ports — use `iris.get_mapped_port(1972)`.
- **DO NOT** use `localhost` on macOS Docker — prefer `127.0.0.1` (IPv6 resolution bug).
- **DO NOT** bind-mount host dirs into IRIS on Linux without fixing uid 51773 perms.

## Related

- **[iris-devtester-connections](../iris-devtester-connections/SKILL.md)** — once a container is up, get a connection, validate it, and emit the iris-agentic-dev handoff.
- **[iris-devtester](../iris-devtester/SKILL.md)** — top-level onboarding.
