# Feature Specification: health() and ai_hub() Container Editions

**Feature Branch**: `033-health-and-ai-hub-editions`
**Created**: 2026-04-25
**Status**: Draft
**Source**: Hard-won findings from a careconnect probe session on irishealth:2026.2.0AI.159

## Background

iris-devtester has three container editions: `community`, `enterprise`, `light`. Two common use cases are unserved:

1. **FHIR testing**: Developers building HL7 FHIR applications need an `irishealth-community` container with the FHIR R4 endpoint set up at build time — no ZPM, no network, no runtime installs. The setup script (`Foundation.Install` + `InstallInstance`) is already written and tested in careconnect.

2. **AI testing**: Developers building `%AI.Agent` / `%AI.MCP.Service` applications need the irishealth enterprise AI Hub build (`irishealth:2026.2.0AI.159`). This image has `%AI.*`, `VECTOR`, `EMBEDDING` — but no web server, no license key required, and a specific `/durable` volume constraint that silently breaks with named Docker volumes.

This spec codifies the discovery of both images, all four gotchas found during probing, and the factory method patterns needed.

## What Is In Each Image

### irishealth-community — FHIR edition

| Class | Present |
|---|---|
| `HS.FHIRServer.Installer` | yes |
| `HS.Util.Installer.Foundation` | yes |
| `HS.FHIR.DTL.*` (SDA3→R4) | yes |
| `HS.FHIRServer.Storage.Json.InteractionsStrategy` | yes |
| `HS.FHIRServer.Tools.DataLoader` | yes |
| Private web server (httpd, port 52773) | yes |
| ZPM | no (not needed) |

FHIR setup via `Foundation.Install("demo")` + `InstallInstance()` baked at build time. Total: ~30 seconds, zero network calls.

### irishealth:2026.2.0AI.159 — AI Hub edition

| Class | Present |
|---|---|
| `%AI.Agent` | yes |
| `%AI.ToolSet` | yes |
| `%AI.Policy.Authorization` | yes |
| `%AI.MCP.Service` | yes |
| Native `VECTOR` / `EMBEDDING` SQL types | yes |
| `HS.FHIRServer.*` | yes |
| Private web server | **NO** — `WebServer=0` in iris.cpf, no `csp/bin/` |
| License key required | **NO** — not the standard enterprise image |
| ISC internal registry required | yes — `docker.iscinternal.com` |

## User Scenarios & Testing

### US1 — FHIR container for testing HL7 R4 apps (Priority: P1)

As a developer building FHIR applications, I need a one-liner to start an irishealth-community container with FHIR R4 pre-installed, so I can run tests against real FHIR endpoints without configuring ZPM or network dependencies.

**Independent Test**: `IRISContainer.health()` starts a container, connects, queries `/metadata` endpoint, gets `200 OK` with `fhirVersion: "4.0.1"`.

**Acceptance Scenarios**:
1. **Given** `with IRISContainer.health() as iris:`, **When** the context is entered, **Then** the container is running and the FHIR endpoint at `/csp/healthshare/demo/fhir/r4/metadata` returns HTTP 200.
2. **Given** `iris.fhir_health_check()`, **When** called on a running health container, **Then** returns `FHIRContainerHealth` with `fhir_version="4.0.1"`, `endpoint`, and `resource_types_count > 100`.
3. **Given** a non-FHIR container, **When** `fhir_health_check()` is called, **Then** raises `RuntimeError` with clear message.

---

### US2 — AI Hub container for testing %AI.* classes (Priority: P1)

As a developer building AI agent applications, I need a container with `%AI.Agent`, `%AI.MCP.Service`, and `VECTOR` SQL support, accessible via SuperServer without needing a web portal.

**Independent Test**: `IRISContainer.ai_hub()` starts, connects via port 1972, executes `SELECT 1` — connection works. `iris.cls("%AI.Agent")` is accessible.

**Acceptance Scenarios**:
1. **Given** `with IRISContainer.ai_hub(build="159") as iris:`, **When** the context is entered, **Then** `iris.get_connection()` succeeds on port 1972.
2. **Given** a running AI Hub container, **When** `iris.health_check()` is called, **Then** returns `ContainerHealth` with `accessible=True`.
3. **Given** `IRISContainer.ai_hub()` without ISC internal registry access, **When** Docker pull fails, **Then** raises `RuntimeError` with message explaining registry requirement.

---

### Edge Cases

- **`/durable` volume ownership**: Named Docker volumes mount with `root` ownership; `irisowner` (uid 51773) cannot write. Must use `tmpfs:/durable:uid=51773,gid=51773` or a bind-mount with correct ownership. Factory must default to tmpfs, with a `durable_path` kwarg for persistent bind-mount.
- **Double-start bug**: The `-a` hook in the AI Hub `/iris-main` entrypoint runs after IRIS is already started. Any entrypoint script that also calls `iris start IRIS quietly` causes IRIS to fail with "database already running" and shut down. Startup scripts under `-a` must assume IRIS is live.
- **Web server split**: `irishealth` enterprise has `WebServer=0`, no httpd, no CSP.ini. Only port 1972 available. `irishealth-community` has `WebServer=1`, port 52773. Factory docstrings must make this explicit.
- **`%AI.*` classes in irislib**: They are compiled system routines in a read-only database. Not exportable as UDL/XML. Cannot be transplanted into the community image — hence two-container architecture is correct for apps needing both FHIR HTTP and `%AI.*`.

## Requirements

- **FR-001**: `IRISContainer.health()` factory method creates an `irishealth-community` container with FHIR R4 endpoint pre-installed at build time.
- **FR-002**: `IRISContainer.ai_hub()` factory method creates an `irishealth:2026.2.0AI.AI.{build}` container with `%AI.*` classes accessible.
- **FR-003**: `ai_hub()` MUST default to `tmpfs:/durable` to avoid volume ownership errors.
- **FR-004**: `ai_hub()` MUST accept `durable_path` kwarg for persistent bind-mount.
- **FR-005**: `IRISContainer` MUST expose `fhir_health_check() -> FHIRContainerHealth` when running as a health edition.
- **FR-006**: `FHIRContainerHealth` dataclass: `fhir_version`, `endpoint`, `resource_types_count`, `accessible`, `report()`.
- **FR-007**: `FHIRReadyWaitStrategy` waits for both port 1972 (SuperServer) AND HTTP 200 from `/metadata` endpoint on port 52773.
- **FR-008**: `ai_hub()` factory docstring MUST document: no web server, no license key, ISC internal registry required, tmpfs durable.
- **FR-009**: All four gotchas (durable volume, double-start, web server split, irislib read-only) MUST be documented in `containers/AGENTS.md`.
- **FR-010**: All existing tests MUST continue to pass.

## Success Criteria

- **SC-001**: `IRISContainer.health()` starts and FHIR `/metadata` returns HTTP 200 in <90 seconds.
- **SC-002**: `IRISContainer.ai_hub()` starts and `get_connection()` succeeds on port 1972 in <60 seconds.
- **SC-003**: `ai_hub()` with no `durable_path` uses `tmpfs` — container starts without volume ownership errors.
- **SC-004**: All existing unit and contract tests pass (386 unit, all contract).
