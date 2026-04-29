# IRIS Container Volume Permissions — uid 51773

**Discovered**: 2026-04-25 | **Source**: careconnect probe + READY 2026 hackathon feedback (Anthony Master)

## The Rule

**ALL IRIS containers** (community, enterprise, light, irishealth, AI Hub) run as `irisowner` uid 51773. Any host directory mounted into the container must be writable by that uid or the container will crash.

This is not edition-specific. It applies to every `IRISContainer` factory method.

## Symptoms

```
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unable to find/open file iris-main.log in current directory /home/irisowner/dev
```

Or: container starts, IRIS attempts to write logs/journals/data, permission denied, silent exit with no error in `docker logs`.

Or: `ISC_DATA_DIRECTORY=/durable — Permission denied` (AI Hub specific path).

## When This Hits

| Scenario | Platform | Why |
|---|---|---|
| Bind-mount project dir into container | Linux (Ubuntu, RHEL) | Host dir owned by uid 1000, container runs as uid 51773 |
| Named Docker volume for `/durable` | All | Named volumes mount as root, irisowner can't write |
| docker-compose with `volumes: - ./:/home/irisowner/dev` | Linux | Same uid mismatch |
| Kubernetes PVC | All | PVC default ownership is root |

**macOS Docker Desktop is NOT affected** — VirtioFS/gRPC FUSE translates permissions between the macOS host and the Linux VM. The uid mismatch is invisible.

## Fixes (pick one)

### A. tmpfs — non-persistent, simplest

```yaml
volumes:
  - type: tmpfs
    target: /durable
    tmpfs:
      uid: 51773
      gid: 51773
```

`IRISContainer.ai_hub()` defaults to this for `/durable`.

### B. chown — persistent, requires root once

```bash
mkdir -p /host/path && chown 51773:51773 /host/path
```

### C. POSIX ACLs — no ownership change, Linux only

```bash
setfacl -R -m u:51773:rwX /path/to/project
setfacl -R -d -m u:51773:rwX /path/to/project
```

The `-d` flag sets default ACLs so new files inherit the rule. Must re-run after cloning. Verify with `getfacl /path/to/project`.

### D. Docker user namespace remapping — enterprise

Configure Docker's `userns-remap` so container uid 51773 maps to the host user's uid. Transparent but requires Docker daemon config change.

### E. Init-container pattern — docker-compose (recommended for teams)

Run a one-shot Alpine container that chowns the volume before IRIS starts. Pattern from [grongierisc/iris-fhir-facade-and-repo-template](https://github.com/grongierisc/iris-fhir-facade-and-repo-template/blob/main/docker-compose.yml):

```yaml
services:
  init-permissions:
    image: alpine:latest
    volumes:
      - iris-data:/dur
    command: sh -c "chown -R 51773:51773 /dur && echo 'Permissions fixed'"

  iris:
    depends_on:
      init-permissions:
        condition: service_completed_successfully
    image: intersystemsdc/iris-community:latest
    volumes:
      - iris-data:/dur
    environment:
      - ISC_DATA_DIRECTORY=/dur/iris

volumes:
  iris-data:
```

`depends_on: condition: service_completed_successfully` ensures IRIS only starts after the chown completes. Alpine runs as root inside Docker and can write to named volumes — no host root access needed.

```dockerfile
FROM intersystemsdc/iris-community:latest
USER root
RUN chown -R 51773:51773 /home/irisowner
USER irisowner
```

Not recommended for production. Useful for one-off dev containers.

## iris-devtester integration

iris-devtester does not currently detect or warn about volume permission mismatches. A future enhancement could:
- Check uid of bind-mounted paths before starting the container
- Emit a warning if the path is not writable by uid 51773
- Suggest the appropriate fix for the detected platform (ACL on Linux, chown on all)
