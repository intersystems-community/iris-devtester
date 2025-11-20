"""
Integration tests for password reset timing and reliability (Feature 015).

These tests measure verification timing across platforms and validate
that the retry logic performs acceptably in real-world conditions.

Tests verify:
- Verification time measurement on current platform
- Success rate >= 99.5% (NFR-001)
- Retry behavior with simulated delays
- Backward compatibility with existing code

Platform: Cross-platform (macOS and Linux)
"""

import platform
import time
from unittest.mock import MagicMock

import pytest

from iris_devtester.containers import IRISContainer
from iris_devtester.utils.password_reset import reset_password
from iris_devtester.utils.password_verification import VerificationConfig


class TestPasswordResetTiming:
    """Integration tests for password reset timing and reliability."""

    def test_measure_verification_time_current_platform(self):
        """
        Measure verification time on current platform.

        Provides diagnostic data for:
        - macOS: Expected 4-6 seconds (Docker Desktop VM delay)
        - Linux: Expected <2 seconds (native Docker)

        Reports timing statistics for documentation and optimization.
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Measure 5 password resets
            attempts = 5
            timing_data = []

            for i in range(attempts):
                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=f"MEASURE{i}",
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace
                )

                assert result.success, f"Reset {i+1} failed: {result.message}"
                timing_data.append({
                    "elapsed_seconds": result.elapsed_seconds,
                    "verification_attempts": result.verification_attempts
                })

            # Calculate statistics
            avg_time = sum(t["elapsed_seconds"] for t in timing_data) / len(timing_data)
            max_time = max(t["elapsed_seconds"] for t in timing_data)
            min_time = min(t["elapsed_seconds"] for t in timing_data)
            avg_attempts = sum(t["verification_attempts"] for t in timing_data) / len(timing_data)

            # Report platform-specific timing
            platform_name = platform.system()
            print(f"\nVerification Timing ({platform_name}):")
            print(f"  Average: {avg_time:.2f}s ({avg_attempts:.1f} attempts)")
            print(f"  Min: {min_time:.2f}s")
            print(f"  Max: {max_time:.2f}s")
            print(f"  Docker: {'Desktop (VM)' if platform_name == 'Darwin' else 'Native'}")

            # Platform-specific expectations
            if platform_name == "Darwin":
                # macOS: 4-6 seconds expected
                assert 2.0 <= avg_time <= 10.0, (
                    f"macOS average time {avg_time:.2f}s outside expected range 2-10s"
                )
            else:
                # Linux: < 2 seconds expected
                assert avg_time <= 3.0, (
                    f"Linux average time {avg_time:.2f}s exceeds 3s threshold"
                )

            # All platforms: must respect 10s timeout (NFR-004)
            assert max_time <= 10.5, (
                f"Maximum time {max_time:.2f}s exceeds 10.5s hard limit (NFR-004)"
            )

    def test_success_rate_99_5_percent(self):
        """
        Validate success rate >= 99.5% (NFR-001).

        This is a critical reliability requirement: password reset must
        succeed virtually every time to be production-ready.

        Expected: 99.5%+ success rate across 20 attempts
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 20 password resets
            attempts = 20
            successes = 0
            failures = []

            for i in range(attempts):
                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=f"RELIABLE{i}",
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace
                )

                if result.success:
                    successes += 1
                else:
                    failures.append({
                        "attempt": i + 1,
                        "message": result.message,
                        "error_type": result.error_type
                    })

            success_rate = (successes / attempts) * 100

            # Report results
            print(f"\nReliability Test Results:")
            print(f"  Successes: {successes}/{attempts} ({success_rate:.1f}%)")
            if failures:
                print(f"  Failures:")
                for failure in failures:
                    print(f"    Attempt {failure['attempt']}: {failure['error_type']}")

            # Verify NFR-001: >= 99.5% success rate
            assert success_rate >= 99.5, (
                f"Success rate {success_rate:.1f}% below 99.5% target (NFR-001). "
                f"{successes}/{attempts} succeeded"
            )

    def test_retry_behavior_with_simulated_delays(self, monkeypatch):
        """
        Test retry logic with simulated network delays.

        Simulates the macOS Docker Desktop delay pattern:
        - First attempt: fails (password not ready)
        - Second attempt: succeeds (password propagated)

        Validates:
        - Retry loop works correctly
        - Exponential backoff is applied
        - Early exit on success
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Mock DBAPI to simulate delay pattern
            attempt_count = {"value": 0}

            def mock_dbapi_connect(*args, **kwargs):
                attempt_count["value"] += 1
                # Fail first attempt, succeed on second (simulating macOS delay)
                if attempt_count["value"] < 2:
                    raise Exception("Access Denied")
                # Second attempt succeeds
                conn = MagicMock()
                cursor = MagicMock()
                cursor.fetchone.return_value = [1]
                conn.cursor.return_value = cursor
                return conn

            try:
                import iris.dbapi as dbapi
                monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
            except ImportError:
                pytest.skip("DBAPI not available for testing")

            # Reset password (should retry once and succeed)
            start_time = time.time()
            result = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="SIMULATED",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace
            )
            elapsed = time.time() - start_time

            # Verify retry behavior
            assert result.success, f"Reset failed: {result.message}"
            assert result.verification_attempts == 2, (
                f"Expected 2 attempts (1 retry), got {result.verification_attempts}"
            )

            # Verify backoff was applied (should take at least initial_backoff_ms)
            # First failure + 100ms backoff + second success = ~0.1-0.3s minimum
            assert elapsed >= 0.05, (
                f"Elapsed time {elapsed:.2f}s too short, backoff may not have been applied"
            )

            print(f"\nSimulated Delay Test:")
            print(f"  Attempts: {result.verification_attempts}")
            print(f"  Elapsed: {elapsed:.2f}s")
            print(f"  Result: {'SUCCESS' if result.success else 'FAILED'}")

    def test_backward_compatibility_tuple_unpacking(self):
        """
        Verify backward compatibility: PasswordResetResult unpacks to (bool, str).

        Existing code uses:
            success, message = reset_password(...)

        New code returns PasswordResetResult but must still support this pattern.
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # OLD STYLE: Tuple unpacking (backward compatibility)
            success, message = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="COMPAT",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace
            )

            # Verify tuple unpacking works
            assert isinstance(success, bool), "First element should be bool"
            assert isinstance(message, str), "Second element should be str"
            assert success is True, f"Password reset failed: {message}"

            # NEW STYLE: Access full result object
            result = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="NEWSTYLE",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace
            )

            # Verify new metadata is available
            assert hasattr(result, "verification_attempts")
            assert hasattr(result, "elapsed_seconds")
            assert hasattr(result, "error_type")
            assert result.verification_attempts > 0
            assert result.elapsed_seconds > 0.0

            print(f"\nBackward Compatibility Test:")
            print(f"  Old style (tuple): success={success}, message={message[:50]}...")
            print(f"  New style (object): attempts={result.verification_attempts}, elapsed={result.elapsed_seconds:.2f}s")

    def test_verification_config_customization(self):
        """
        Test custom VerificationConfig for edge cases.

        Validates:
        - Custom max_retries setting
        - Custom timeout configuration
        - Custom backoff timing
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Custom config: only 1 retry, fast timeout
            custom_config = VerificationConfig(
                max_retries=1,
                timeout_ms=5000,  # 5 seconds
                initial_backoff_ms=50,
                exponential_backoff=False  # No backoff
            )

            result = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="CUSTOM",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
                verification_config=custom_config
            )

            # Should succeed with custom config
            assert result.success, f"Reset failed with custom config: {result.message}"

            # Verify config was respected
            assert result.verification_attempts <= custom_config.max_retries, (
                f"Exceeded max_retries: {result.verification_attempts} > {custom_config.max_retries}"
            )
            assert result.elapsed_seconds <= (custom_config.timeout_ms / 1000.0) + 1.0, (
                f"Exceeded timeout: {result.elapsed_seconds:.2f}s > {custom_config.timeout_ms/1000.0}s"
            )

            print(f"\nCustom Config Test:")
            print(f"  Max Retries: {custom_config.max_retries}")
            print(f"  Timeout: {custom_config.timeout_ms}ms")
            print(f"  Actual Attempts: {result.verification_attempts}")
            print(f"  Actual Time: {result.elapsed_seconds:.2f}s")
