# Feature Specification: CPF-First Password Strategy

**Feature Branch**: `034-cpf-first-password-strategy`
**Created**: 2026-04-25
**Status**: Draft
**Source**: grongierisc/iris-fhir-facade-and-repo-template pattern + READY 2026 hackathon + objectscript-coder failure trace

## Clarifications

### Session 2026-04-25

- Q: Should `with_preconfigured_password()` use CPF merge or env var? → A: Merge into single CPF file — `PasswordHash` line alongside `ChangePassword=0` in the same temp file, one env var, one mechanism.

## Background

IRIS community containers start with `ChangePassword=1` for all users. iris-devtester currently clears this flag via `unexpire_all_passwords()` — a `docker exec iris session` call that runs **after** IRIS starts. This approach has three failure modes:

1. **Timing**: Runs after IRIS starts but before the superserver is fully ready — can fail silently with no error
2. **Environment**: Requires `docker exec` access — unavailable in some CI/cloud environments  
3. **Incompleteness**: Current `CPFPreset.SECURE_DEFAULTS` patched only `SuperUser`, not `_SYSTEM` (the default connection user) — so the CPF preset was ineffective for the most common case

The [grongierisc/iris-fhir-facade-and-repo-template](https://github.com/grongierisc/iris-fhir-facade-and-repo-template) demonstrates the correct pattern: inject `ChangePassword=0` via `ISC_CPF_MERGE_FILE` **before** IRIS starts — zero `docker exec`, atomic, timing-independent.

## User Scenarios & Testing

### US1 — Container starts, DBAPI connects without password errors (Priority: P1)

As a developer using `IRISContainer.community()`, connections should work immediately after `start()` without any manual password reset, regardless of platform or CI environment.

**Independent Test**: Start a fresh community container — no `with_preconfigured_password()`, no manual setup — call `get_connection()`, verify it succeeds on first attempt.

**Acceptance Scenarios**:

1. **Given** `with IRISContainer.community() as iris:`, **When** `iris.get_connection()` is called, **Then** connection succeeds without `ConnectionError` or password-change error.
2. **Given** a container started without explicit CPF merge, **When** `start()` runs, **Then** `ISC_CPF_MERGE_FILE` is set to a temp file containing `ChangePassword=0` for both `_SYSTEM` and `SuperUser`.
3. **Given** a container where `with_cpf_merge()` was already called before `start()`, **When** `start()` runs, **Then** the existing CPF merge is preserved (not overwritten).

---

### US2 — Fallback works when CPF merge is unavailable (Priority: P1)

As a developer using `IRISContainer.attach()` (connecting to a pre-existing container that wasn't started by iris-devtester), `get_connection()` should detect password-change errors and auto-remediate via docker exec.

**Independent Test**: Attach to a container that has `ChangePassword=1`, call `get_connection()`, verify it succeeds after one fallback.

**Acceptance Scenarios**:

1. **Given** `IRISContainer.attach("existing-container")` where the container has `ChangePassword=1`, **When** `get_connection()` is called, **Then** it detects the password-change error, calls `unexpire_all_passwords()` as fallback, and retries successfully.
2. **Given** a container where `get_connection()` already succeeded, **When** `get_connection()` is called again, **Then** it uses the cached connection — no password check repeated.
3. **Given** a container where both CPF merge AND docker exec fallback fail, **When** `get_connection()` is called, **Then** it raises `ConnectionError` with actionable message including `idt container reset-password`.

---

### US3 — No regression on existing API (Priority: P1)

All existing test patterns continue to work unchanged.

**Acceptance Scenarios**:

1. **Given** `iris.with_preconfigured_password("SYS")`, **When** `start()` runs, **Then** the CPF merge includes the specified password hash alongside `ChangePassword=0`.
2. **Given** 386 existing unit tests, **When** they run, **Then** all pass.

---

### Edge Cases

- `attach()` containers: no `start()` is called, CPF merge doesn't apply — fallback path must work
- `_password_handled` flag: prevents double-remediation (CPF merge + docker exec both running)
- Temp CPF file cleanup: must be deleted after container starts (or on container exit)
- Containers where `docker exec` fails (restricted CI): should raise descriptive `ConnectionError` not a cryptic Docker exception

## Requirements

- **FR-001**: `start()` MUST inject `CPFPreset.SECURE_DEFAULTS` via CPF merge before calling `super().start()`, unless a CPF merge file was already configured. If `with_preconfigured_password()` was used, the password hash MUST be included in the same CPF file as `ChangePassword=0`.
- **FR-002**: `CPFPreset.SECURE_DEFAULTS` MUST include `ChangePassword=0` and `PasswordNeverExpires=1` for BOTH `_SYSTEM` and `SuperUser`.
- **FR-003**: `get_connection()` MUST attempt the connection first (optimistic). If it fails with a password-change error, MUST call `unexpire_all_passwords()` as fallback (once), then retry.
- **FR-004**: `get_connection()` MUST NOT call `unexpire_all_passwords()` proactively — only reactively on detection of a password-change error.
- **FR-005**: `_password_handled: bool` flag MUST prevent the fallback from running more than once per container instance.
- **FR-006**: `attach()` containers MUST use the fallback path only (no CPF merge in `attach()`).
- **FR-007**: All existing tests MUST pass without modification.

## Key Entities

- **`CPFPreset.SECURE_DEFAULTS`** — CPF snippet in `config/presets.py`; patched to include `_SYSTEM`
- **`IRISContainer.start()`** — primary injection point for CPF merge
- **`IRISContainer.get_connection()`** — optimistic connect → detect → fallback
- **`_password_handled: bool`** — instance flag preventing double-remediation

## Success Criteria

- **SC-001**: Fresh `IRISContainer.community()` connects on first `get_connection()` call without any password-change error — no `docker exec` call made during the happy path.
- **SC-002**: `attach()` to a container with `ChangePassword=1` — `get_connection()` succeeds after one fallback.
- **SC-003**: 386 unit tests pass. Contract tests for new flow pass.
- **SC-004**: `unexpire_all_passwords()` is NOT called during `get_connection()` when CPF merge already cleared the flag (verified by mocking).
