# irishealth Container Editions

**Discovered**: 2026-04-25 | **Source**: Systematic probe of `irishealth:2026.2.0AI.159.0`

## Two Editions, Two Jobs

| | `irishealth-community` | `irishealth:2026.2.0AI.159` |
|---|---|---|
| Factory | `IRISContainer.health()` | `IRISContainer.ai_hub()` |
| Port 1972 | ✅ SuperServer | ✅ SuperServer |
| Port 52773 | ✅ httpd / FHIR HTTP | ❌ WebServer=0 |
| `%AI.Agent`, `%AI.MCP.Service` | ❌ irislib not present | ✅ |
| `VECTOR`, `EMBEDDING` SQL | ❌ | ✅ |
| `HS.FHIRServer.*` | ✅ | ✅ (but no HTTP) |
| Registry | docker.io | docker.iscinternal.com |
| License key | No | No |

## FHIR Setup (No ZPM, No Network)

The FHIR setup baked into `health()` containers:

```objectscript
set $NAMESPACE = "HSLIB"
do:'##class(%SYS.Namespace).Exists("demo") ##class(HS.Util.Installer.Foundation).Install("demo")
set $NAMESPACE = "demo"
set appKey = "/csp/healthshare/demo/fhir/r4"
set strategyClass = "HS.FHIRServer.Storage.Json.InteractionsStrategy"
set metadataPackages = $LISTBUILD("hl7.fhir.r4.core@4.0.1","hl7.fhir.us.core@3.1.0")
do ##class(HS.FHIRServer.Installer).InstallInstance(appKey, strategyClass, metadataPackages)
```

Total build time: ~30 seconds. Zero network calls. `InstallInstance` generates ~180 search parameter classes and builds FHIR SQL tables.

## Gotcha 1: Volume Ownership — irisowner (uid 51773) Cannot Write Host Volumes

IRIS containers run as `irisowner` (uid 51773). Any host directory mounted into the container must be writable by that uid. This affects:

- **`/durable`** on AI Hub images — named Docker volumes mount as root, irisowner can't write
- **Project bind-mounts** on Linux (Ubuntu, RHEL, etc.) — host directory owned by user uid 1000

The symptom is always the same:
```
terminate called after throwing an instance of 'std::runtime_error'
  what():  Unable to find/open file iris-main.log in current directory /home/irisowner/dev
```
Or: container starts then silently exits.

### Fix A — tmpfs (non-persistent, for `/durable`)

```yaml
volumes:
  - type: tmpfs
    target: /durable
    tmpfs:
      uid: 51773
      gid: 51773
```

`IRISContainer.ai_hub()` defaults to this.

### Fix B — chown (persistent bind-mount)

```bash
mkdir -p /host/path && chown 51773:51773 /host/path
```

### Fix C — POSIX ACLs (Linux project directories, no ownership change)

```bash
setfacl -R -m u:51773:rwX /path/to/project
setfacl -R -d -m u:51773:rwX /path/to/project
```

The `-d` flag sets default ACLs so new files inherit the permission. Verify with `getfacl /path/to/project`. This must be re-run after cloning or on each new developer machine.

### Fix D — Docker user namespace remapping

For enterprise deployments, configure Docker's `userns-remap` so container uid 51773 maps to the host user's uid. This is transparent but requires Docker daemon configuration.

### Note for macOS

macOS Docker Desktop uses a Linux VM with its own filesystem. Bind-mounted volumes go through VirtioFS/gRPC FUSE which translates permissions — so uid 51773 mismatch rarely causes issues on macOS. This is primarily a **Linux host** problem.

## Gotcha 2: Double-Start Bug

The `-a` hook in `/iris-main` runs **after** IRIS is already started. Any script under `-a` that calls `iris start IRIS quietly` fails:

```
Starting IRIS... IRIS is already running. Cannot start.
Exit code 1 → entrypoint fails → container exits
```

**Rule**: Startup scripts under `-a` must assume IRIS is live. Poll port 1972, not `iris start`.

## Gotcha 3: No Web Server in Enterprise Image

`irishealth:2026.2.0AI.*` ships with `WebServer=0` in `iris.cpf` and no `csp/bin/` directory.

```bash
docker exec container ls /usr/irissys/csp/bin/
# ls: cannot access '/usr/irissys/csp/bin/': No such file or directory
```

Port 52773 is not available. FHIR HTTP endpoint not reachable. Port 1972 (SuperServer) works fine for DBAPI, JDBC, ODBC, `%AI.*`.

## Gotcha 4: `%AI.*` Classes in irislib (Read-Only)

`%AI.Agent`, `%AI.MCP.Service`, `%AI.ToolSet`, `%AI.Policy.Authorization` live in `irislib` — a read-only system database.

```
%SYSTEM.OBJ.Export "%AI.Agent.cls" → ERROR: source is read-only
```

Cannot transplant into `irishealth-community`. The two-container split is the correct architecture:
- Community container → FHIR HTTP endpoint, test data loading
- AI Hub container → `%AI.*` methods, `VECTOR`/`EMBEDDING` SQL

## Two-Container docker-compose Pattern

```yaml
services:
  fhir:
    image: intersystemsdc/irishealth-community:latest
    ports:
      - "1972:1972"
      - "52773:52773"
    # FHIR R4 at http://localhost:52773/csp/healthshare/demo/fhir/r4

  ai_hub:
    image: docker.iscinternal.com/docker-intersystems/intersystems/irishealth:2026.2.0AI.159.0
    ports:
      - "11972:1972"
    volumes:
      - type: tmpfs
        target: /durable
        tmpfs:
          uid: 51773
          gid: 51773
    # %AI.Agent at localhost:11972 via DBAPI
```
