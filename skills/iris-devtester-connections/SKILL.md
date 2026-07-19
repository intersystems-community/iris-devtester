---
name: iris-devtester-connections
description: ConnectionInfo / IRISConnectionInfo, to_toml_snippet(), the iris-agentic-dev handoff, and connection validation.
managed_by: iris-devtester
source: intersystems-community/iris-devtester
triggers:
  [
    connection,
    connectioninfo,
    irisconnectioninfo,
    toml,
    iris-agentic-dev,
    iad,
    handoff,
    dbapi,
    validate,
    webgateway,
  ]
prerequisites: [Docker, "Python 3.9+", "pip install iris-devtester[all]"]
related_skills: [iris-devtester, iris-devtester-containers]
metadata:
  version: 1.18.1
  author: InterSystems Community
---

# Skill: Connections & the iris-agentic-dev Handoff

Covers how to get a connection, inspect its metadata, validate it, and — the key
capability — emit the authoritative connection description that
[iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev)
(iad) consumes.

## Getting a connection (DBAPI-first)

```python
from iris_devtester import get_connection

# Auto-discovers host/port/creds from env, .env, or a running Docker container.
# Tries DBAPI first (3x faster), falls back to JDBC.
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT $ZVERSION")
print(cur.fetchone()[0])
```

From a container, `get_connection()` also enables the CallIn service and
auto-remediates "Password change required":

```python
with IRISContainer.community() as iris:
    conn = iris.get_connection()   # enables CallIn + unexpires passwords as needed
```

## Two ConnectionInfo types — do not confuse them

| Type                 | Module                              | Purpose                                                                                                          |
| -------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `ConnectionInfo`     | `iris_devtester.connections.models` | Runtime metadata about an **active** connection (driver_type, connection_time, is_pooled). Debugging/monitoring. |
| `IRISConnectionInfo` | `iris_devtester.containers`         | The **handoff contract** describing how to reach a container. Emits `.iris-agentic-dev.toml`.                    |

This skill is about **`IRISConnectionInfo`** — the iad handoff.

## The iris-agentic-dev handoff

iris-devtester owns the container lifecycle; iad compiles and executes
ObjectScript inside it. They share one authoritative connection description so
neither reconstructs it per session — no manual port hunting.

### Workflow

```python
from iris_devtester.containers import IRISContainer

# 1. Attach to a running container (started by `idt container up`, compose, etc.)
container = IRISContainer.attach("opsreview-iris")

# 2. Build the handoff contract (auto-detects a WebGateway sidecar if present)
info = container.connection_info()

# 3. Write the fragment iad hot-reloads
with open(".iris-agentic-dev.toml", "w") as f:
    f.write(info.to_toml_snippet())
```

### Snippet output — Docker-only container (no WebGateway)

```toml
container = "opsreview-iris"
docker_only = true
namespace = "USER"
```

### Snippet output — WebGateway detected on the same Docker network

```toml
container = "opsreview-iris"
web_port = 52774
docker_only = false
namespace = "USER"
```

`web_port` is the host-mapped WebGateway port (container port 80). It is emitted
only when `docker_only = false`; iad never sees `docker_only = false` without a
usable `web_port`.

### WebGateway auto-detection

`connection_info()` scans containers sharing a Docker network with the IRIS
container for an image matching `*webgateway*`, and uses the first match's
host-mapped port 80 as `webgateway_url`. When none is found, pass an explicit
fallback (e.g. from `.iris-dev.toml`):

```python
info = container.connection_info(web_port=52774)  # fallback if auto-detect finds nothing
```

Detection always wins over the `web_port` fallback. If neither yields a port,
the result is `docker_only=True`.

### IRISConnectionInfo fields

| Field                                 | Meaning                                                    |
| ------------------------------------- | ---------------------------------------------------------- |
| `host`                                | Hostname reachable from the session (usually `localhost`). |
| `superserver_port`                    | Host-mapped IRIS SuperServer port (container 1972).        |
| `container`                           | Docker container name of the IRIS instance.                |
| `iris_image`                          | IRIS image reference (`docker inspect .Config.Image`).     |
| `namespace` / `username` / `password` | Connection defaults (`USER` / `_SYSTEM` / `SYS`).          |
| `webgateway_url`                      | `http://host:port` of a detected WebGateway, or `None`.    |
| `webgateway_container`                | Docker name of the WebGateway container, or `None`.        |
| `docker_only`                         | `True` when no WebGateway is reachable.                    |

Install the integration extra: `pip install iris-devtester[iad]`.

**Out of scope for iris-devtester**: capability fingerprinting (NoPWS,
atelier_rest, compile_path) is iad's `check_config` responsibility.

## Validating a connection

Confirm the container is not just running but seeded and responsive before
running queries:

```python
with IRISContainer.community() as iris:
    health = iris.health_check()   # probes visible schemas via a real DBAPI connection
    # or, for progressive container-level checks:
    iris.assert_healthy()          # raises with remediation guidance on failure
```

For standalone diagnostics without a container object, see
`iris_devtester.diagnostics.probe_connection()`.

## Anti-patterns

- **DO NOT** rebuild `.iris-agentic-dev.toml` by hand — call `to_toml_snippet()`.
- **DO NOT** confuse `connections.ConnectionInfo` (active-connection metadata) with `containers.IRISConnectionInfo` (handoff contract).
- **DO NOT** use JDBC unless specifically testing JDBC — DBAPI is 3x faster.

## Related

- **[iris-devtester-containers](../iris-devtester-containers/SKILL.md)** — start or attach to the container this connection targets.
- **[iris-devtester](../iris-devtester/SKILL.md)** — top-level onboarding.
- [AGENTS.md → ECOSYSTEM](../../AGENTS.md#ecosystem) — ecosystem cross-references.
