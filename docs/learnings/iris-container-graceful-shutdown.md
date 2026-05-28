# IRIS Container Graceful Shutdown

**Severity**: HIGH — silent data loss, no warning, affects all persistent-volume containers
**Fixed in**: iris-devtester 1.18.1 (IRISContainer.__exit__ calls stop_gracefully())

## Root Cause

IRIS uses a WIJ (Write Image Journal) as a write buffer. On normal shutdown, IRIS flushes the WIJ to disk and marks the database clean. On SIGKILL (which `docker stop` eventually sends if SIGTERM is not handled), the WIJ is left dirty.

IRIS's default entrypoint (`/iris-main`) does NOT trap SIGTERM. `docker stop` sends SIGTERM, waits the grace period, then sends SIGKILL. IRIS is killed mid-flight.

On next start, IRIS runs journal recovery (30-300s). Committed data is recovered. Uncommitted in-flight writes are lost.

**Symptom**: After `docker stop` + `docker start`, schema exists but rows are 0.

## Reproduction

1. Insert rows into a persistent-volume IRIS container
2. `docker stop <container>` (no prior `iris stop IRIS quietly`)
3. `docker start <container>`
4. `SELECT COUNT(*) FROM MyTable` → 0

## Fix

```bash
# Always do this before docker stop:
docker exec <container> iris stop IRIS quietly
docker stop <container>
```

## iris-devtester Integration (v1.18.1+)

`IRISContainer.__exit__()` calls `stop_gracefully()` automatically:

```python
with IRISContainer.community() as iris:
    # ... do work ...
# stop_gracefully() runs here before docker stop
```

## docker-compose Pattern

```yaml
services:
  iris:
    stop_grace_period: 60s   # Safety net — but alone is NOT enough
```

Plus a pre-stop script: `docker exec iris iris stop IRIS quietly` before `docker compose down`.

## Why stop_grace_period Alone Is Not Enough

IRIS doesn't trap SIGTERM. `stop_grace_period` gives Docker longer to wait, but IRIS is still killed without flushing the WIJ.

## Full SIGTERM Trap Pattern (optional)

```bash
#!/bin/sh
/iris-main &
IRIS_PID=$!
trap 'iris stop IRIS quietly; wait $IRIS_PID' SIGTERM
wait $IRIS_PID
```

Conflicts with IRIS `-b`/`-a` hooks. Use only on simple images.

## Kubernetes

```yaml
lifecycle:
  preStop:
    exec:
      command: ["iris", "stop", "IRIS", "quietly"]
terminationGracePeriodSeconds: 60
```
