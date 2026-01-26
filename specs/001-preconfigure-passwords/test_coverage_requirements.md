## Test Coverage Validation Requirements

As QA automation engineer, I want comprehensive performance benchmarks that validate the 3-10 second startup time reduction claim.

### Performance Comparison Tests
1. Measure container ready signal to successful authentication WITH pre-configured password; compare against same workflow WITHOUT (baseline post-startup reset). Require consistent ≥3 second improvement across 10+ sequential runs.

2. Statistical analysis averaging multiple container startups in same Docker daemon session OR across isolation boundaries; report average startup time WITH and WITHOUT pre-configured passwords to prove claimed improvement.

### Edge Case Testing
As security engineer, validate all edge case scenarios for password pre-configuration:
1. Special characters (!@#$%^&*()) successfully authenticate; no errors or connection failures.
2) Unicode passwords (Chinese, Japanese emojis in IRIS_USERNAME/IRI S_PASSWORD environment variables OR programmatic API) successfully authenticate; validates support for international developers.
3. Long passwords beyond 256 characters (IRIS max) either handle gracefully OR raise clear error before startup; document expected behavior.
4. Empty or null passwords "" either handled gracefully with fallback to password reset OR raise descriptive validation error before container starts; document expected behavior.
5. Conflicting credentials: IRIS_PASSWORD env var set AND programmatic API with different values; document priority rules and whether explicit error shown to user.
6. Older or custom-built container images without password pre-config support; system starts successfully with fallback AND logs warning.

### Error Handling Tests
As user experience engineer, ensure invalid inputs handled gracefully:
1. Empty username "" passed to `with_credentials()` raises descriptive error before container starts.
2) Whitespace-only passwords raise clear validation errors indicating valid characters required; do not attempt startup with invalid credentials.
3. Authentication failures after container readiness due to network/database issues trigger specific diagnostic logs AND correct fallback mechanism, not generic authentication errors.

**Unit Tests**: Mock-based tests for implementation logic without Docker.

### Stringent Integration Test Suite
As QA automation engineer, I want **no mocked IRIS** - integration tests MUST run real Docker containers with actual InterSystems servers:

1. **NO Mocking**: All integration tests MUST use `testcontainers-python` to start real InterSystems IRIS Community/Enterprise containers, not mocks or fakes.

2. **Real Credential Validation**: Tests MUST connect to actual IRIS instance using provided credentials (IRI S_PASSWORD env var OR programmatic API) and verify successful authentication via real SQL queries executed against container.

3. **Zero Dependency on Pre-configured Environment**: Each integration test MUST start its own fresh IRIS container instance, validate startup from scratch (no pre-cached Docker images that bypass real credential validation).

4. **Full Lifecycle Verification**: Integration tests MUST verify complete password pre-configuration lifecycle:
   - Container starts → environment variables passed OR programmatic API used
. **IRIS initializes with credentials** (no password change required) → connection established via real DBAPI client
   - Connection verified with actual `SELECT 1` query executed against running IRIS database

5. **Performance Benchmark Execution**: Integration test suite MUST include performance comparison tests that actually measure 10+ container startup cycles with AND WITHOUT pre-configured credentials to validate ≥5 second improvement claim - NOT mocked timing values.

6. **Cross-Container Isolation**: Each integration test MUST run in isolated Docker network AND use unique container names to prevent credential conflicts between sequential tests.

7. **Resource Cleanup Enforcement**: Integration test suite MUST verify ALL containers, volumes AND Docker networks are properly cleaned up after each test (no orphaned resources), with explicit `docker ps -a` validation on teardown.

8. **Error Scenarios Require Real IRIS Failure Modes**: Edge case and error handling tests MUST introduce actual conditions that cause failures (e.g., network unreachable IRIS port, invalid credentials in real container environment) - NOT mocked exception handling.

### CI/CD Test Execution
As DevOps engineer, ensure tests run reliably in pipelines:
1. Fast unit test suite completes within 60 seconds for continuous validation.
2) Integration tests available when `RUN_INTEGRATION_TESTS=1` flag set; performance AND edge case validation runs if enabled (may take 2-3 minutes total for comprehensive coverage).

### Test Coverage Success Criteria
1. SC-T01 (Performance): Statistical analysis shows consistent ≥5 second improvement across 10+ test runs.
2) SC-T02 (Edge Cases): All enumerated edge case scenarios pass or explicitly documented as unsupported.
3. SC-T03 (Unit Coverage): Unit test file `tests/unit/test_password_preconfig_unit.py` achieves ≥90% line coverage.
4. SC-T04 (Error Handling): Invalid inputs raise clear errors within 200ms of API call attempting startup.
5. SC-T05 (CI Validation): Unit tests complete <60s; integration suite completes in ≤3 minutes when flag set.
