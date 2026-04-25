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

## Gotcha 1: `/durable` Volume Ownership

Named Docker volumes mount with `root` ownership. `irisowner` (uid 51773) cannot write to them.

```
Error: ISC_DATA_DIRECTORY=/durable — Permission denied
Container exits immediately after IRIS start attempt
```

**Fix — tmpfs (non-persistent, default):**
```yaml
volumes:
  - type: tmpfs
    target: /durable
    tmpfs:
      uid: 51773
      gid: 51773
```

**Fix — bind-mount (persistent):**
```bash
mkdir -p /host/durable && chown 51773:51773 /host/durable
```
```yaml
volumes:
  - /host/durable:/durable
```

`IRISContainer.ai_hub()` defaults to tmpfs. Pass `durable_path="/host/durable"` for persistence.

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
