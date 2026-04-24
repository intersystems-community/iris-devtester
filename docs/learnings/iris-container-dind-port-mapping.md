# Docker-in-Docker Port Mapping Failure

**Bug**: `BUG-IDT-1`  
**Fixed in**: v1.15.1  
**Symptom**: `IRISContainer.get_mapped_port(52773)` raises `ConnectionError: Port mapping for container <id> and port 52773 is not available` when iris-devtester runs inside a container.

## Root Cause

testcontainers detects DinD via `/.dockerenv`. When inside a container, `get_connection_mode()` returns `ConnectionMode.gateway_ip` (not `docker_host`). In gateway_ip mode, `use_mapped_port=True`, so `_get_exposed_port()` calls `DockerClient.port()`. That API call queries the inner Docker daemon for host-side NAT port mappings — but those mappings live on the **outer** host and are not visible inside the nested container. The API returns `None`, triggering:

```
ConnectionError: Port mapping for container <id> and port 52773 is not available
```

Port 1972 often does not hit this because it's cached as `_mapped_port` during `start()`.

## Fix

`get_mapped_port()` now catches `ConnectionError` and falls back to the internal port. In DinD, the started container is reachable via its bridge/gateway IP at the **internal** port — no NAT needed. The fallback is correct behavior.

```python
# New behavior (v1.15.1+):
iris.get_mapped_port(52773)
# DinD: returns 52773 (internal port, reachable via container IP)
# Normal: returns e.g. 49723 (host-mapped port)
```

`get_config()` also narrowed its `except Exception` to `except ConnectionError` so real errors (container not started, etc.) still propagate.

## Env Var Overrides

testcontainers respects these env vars for DinD scenarios:

| Var | Effect |
|-----|--------|
| `TESTCONTAINERS_CONNECTION_MODE=bridge_ip` | Force bridge IP mode (DooD with shared network) |
| `TESTCONTAINERS_CONNECTION_MODE=gateway_ip` | Force gateway IP mode (true DinD) |
| `TC_HOST=<ip>` | Pin the reachable host IP (overrides all detection) |

## Diagnosis

```bash
# Are you in DinD?
cat /.dockerenv 2>/dev/null && echo "DinD detected" || echo "Not in container"

# What mode does testcontainers choose?
python -c "
from testcontainers.core.docker_client import DockerClient
dc = DockerClient()
print('mode:', dc.get_connection_mode())
print('host:', dc.host())
print('inside_container:', __import__('testcontainers.core.utils', fromlist=['inside_container']).inside_container())
"

# Test port mapping directly
python -c "
from iris_devtester.containers import IRISContainer
with IRISContainer.community() as iris:
    print('superserver port:', iris.get_mapped_port(1972))
    print('web port:', iris.get_mapped_port(52773))
    print('host:', iris.get_container_host_ip())
"
```
