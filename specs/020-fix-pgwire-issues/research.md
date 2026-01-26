# Research: Fixes for pgwire-identified bugs

**Feature Branch**: `020-fix-pgwire-issues` | **Date**: 2026-01-02

## 1. Password Reset Parametrization

- **Decision**: Update `reset_password_if_needed` and `reset_password` to accept a `username` parameter.
- **Rationale**: Currently hardcoded to `_SYSTEM`. Enterprise or custom user scenarios (like `iris-pgwire` connecting as `SuperUser`) fail auto-remediation.
- **Alternatives considered**: Automatic detection of the user from the error message.
  - *Rejected because*: Error messages for "password change required" don't always contain the username in a consistent format across IRIS versions.

## 2. Reliable Security Flag Management

- **Decision**: Switch from `%Save()` to `##class(Security.Users).Modify(username, .props)` for clearing security flags.
- **Rationale**: verified that `%Save()` on a `Security.Users` object can be unreliable in Docker environments for certain IRIS versions (2024.1+). `Modify` is the recommended and more robust API.
- **Key Properties**: `ChangePassword=0`, `PasswordExternal` (triggers PBKDF2), `PasswordNeverExpires=1`, `AccountNeverExpires=1`.

## 3. Deterministic Container Readiness

- **Decision**: Enhance `IRISReadyWaitStrategy` to include an application-level check via `docker exec`.
- **Selected Command**: `iris session IRIS -U USER "W 1" Halt`.
- **Rationale**: Port 1972 can be open before the security system or namespaces are fully initialized. A successful `iris session` command verifies that authentication, namespaces, and the Superserver are all functional.
- **Alternatives considered**: `iris list` or `iris qlist`.
  - *Rejected because*: These only confirm the process is running, not that it's accepting authenticated connections.

## 4. Refreshable Test Data

- **Decision**: Add `force_refresh: bool = False` to `DATFixtureLoader.load_fixture`.
- **Behavior**: If `force_refresh` is True and the namespace exists, call `##class(Config.Namespaces).Delete(namespace)` and `##class(Config.Databases).Delete(db_name)` before restoring.
- **Rationale**: Users need to be able to reload fixtures into existing namespaces (like `USER`) without manual cleanup.

## 5. Dogfooding & Infrastructure Optimization

- **Decision**: Refactor `tests/conftest.py` to use `IRISContainer.get_connection()` and remove manual `time.sleep()` calls.
- **Decision**: Ensure `IRISContainer` uses the new `IRISReadyWaitStrategy` by default in its `start()` method.
- **Rationale**: The current tests manually handle connectivity and readiness, masking the issues we are fixing. By dogfooding the fixes in the project's own test suite, we verify the library's higher-level APIs are robust and easy to use.
