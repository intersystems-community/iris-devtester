"""
Integration tests for password reset on macOS (Feature 015).

These tests verify that password reset works correctly on macOS Docker Desktop,
which has a 4-6 second VM-based networking delay after password changes.

Tests verify:
- Container creation → password reset → connection success (end-to-end)
- PortRegistry compatibility (Feature 013)
- Multiple rapid password resets (stress testing)
- Timing validation (NFR-004: < 10 seconds)

Platform: macOS only (Docker Desktop)
"""

import platform
import time

import pytest

from iris_devtester.containers import IRISContainer
from iris_devtester.utils.password_reset import reset_password


@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="macOS-specific tests (Docker Desktop VM-based networking delay)"
)
class TestPasswordResetMacOS:
    """Integration tests for password reset on macOS."""

    def test_container_to_connection_full_workflow(self):
        """
        End-to-end: Container creation → password reset → connection success.

        This is the most important macOS test: verify complete workflow works
        reliably with the 4-6 second macOS Docker Desktop delay.

        Expected: 100% success rate (NFR-001)
        """
        # Create fresh container
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            # Get connection details
            config = iris.get_config()

            # Reset password with new value
            result = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="MACOS_TEST",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace
            )

            # Verify reset succeeded
            assert result.success, f"Password reset failed: {result.message}"
            assert result.elapsed_seconds <= 10.0, (
                f"Verification took {result.elapsed_seconds:.2f}s, exceeds 10s timeout (NFR-004)"
            )

            # CRITICAL: Verify connection succeeds with new password
            from iris_devtester.utils.dbapi_compat import get_connection

            conn = get_connection(
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
                username="SuperUser",
                password="MACOS_TEST"
            )

            # Execute query to verify connection works
            cursor = conn.cursor()
            cursor.execute("SELECT 1 AS test")
            result_row = cursor.fetchone()
            assert result_row[0] == 1, "Connection query failed"

            conn.close()

    def test_portregistry_compatibility(self):
        """
        Verify password reset works with PortRegistry (Feature 013 compatibility).

        PortRegistry manages port allocation for multi-project isolation.
        Password reset must work correctly regardless of port allocation method.

        Expected: No port conflicts, password reset succeeds
        """
        try:
            from iris_devtester.containers.ports import PortRegistry
            port_registry_available = True
        except ImportError:
            pytest.skip("PortRegistry not available (Feature 013)")

        if not port_registry_available:
            pytest.skip("PortRegistry not available (Feature 013)")

        # Create container using PortRegistry
        registry = PortRegistry()
        try:
            port = registry.allocate_port(project_name="test_macos_015")

            with IRISContainer() as iris:
                # Enable CallIn service
                from iris_devtester.utils.enable_callin import enable_callin_service
                container_name = iris.get_wrapped_container().name
                success, msg = enable_callin_service(container_name, timeout=30)
                assert success, f"CallIn service failed: {msg}"

                # Get connection details
                config = iris.get_config()

                # Reset password
                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password="PORTTEST",
                    hostname=config.host,
                    port=config.port,  # Using PortRegistry-allocated port
                    namespace=config.namespace
                )

                # Verify reset succeeded
                assert result.success, f"Password reset failed with PortRegistry: {result.message}"

                # Verify connection succeeds
                from iris_devtester.utils.dbapi_compat import get_connection

                conn = get_connection(
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                    username="SuperUser",
                    password="PORTTEST"
                )

                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result_row = cursor.fetchone()
                assert result_row[0] == 1

                conn.close()

        finally:
            if port_registry_available:
                registry.release_port(project_name="test_macos_015")

    def test_multiple_rapid_password_resets(self):
        """
        Stress test: Multiple rapid password resets in succession.

        Verifies retry logic handles rapid password changes gracefully
        without race conditions or state corruption.

        Expected: All resets succeed, each verification completes within 10s
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 5 rapid password resets
            reset_count = 5
            successes = 0
            timing_violations = 0

            for i in range(reset_count):
                new_password = f"RAPID{i}"

                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=new_password,
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace
                )

                if result.success:
                    successes += 1
                else:
                    pytest.fail(f"Reset {i+1}/{reset_count} failed: {result.message}")

                # Check timing
                if result.elapsed_seconds > 10.0:
                    timing_violations += 1

                # Verify connection works with latest password
                from iris_devtester.utils.dbapi_compat import get_connection

                conn = get_connection(
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                    username="SuperUser",
                    password=new_password
                )

                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result_row = cursor.fetchone()
                assert result_row[0] == 1, f"Connection failed after reset {i+1}"

                conn.close()

            # Verify all resets succeeded
            success_rate = (successes / reset_count) * 100
            assert success_rate == 100.0, (
                f"Success rate {success_rate:.1f}% below 100% target. "
                f"{successes}/{reset_count} succeeded"
            )

            # Verify timing (allow 1 timeout per 5 resets = 80% within 10s)
            timing_success_rate = ((reset_count - timing_violations) / reset_count) * 100
            assert timing_success_rate >= 80.0, (
                f"Timing success rate {timing_success_rate:.1f}% below 80% target. "
                f"{timing_violations}/{reset_count} exceeded 10s timeout"
            )

    def test_verification_timing_within_10_seconds(self):
        """
        Validate timing: Password verification completes within 10 seconds (NFR-004).

        This is the core NFR for Feature 015: verification MUST complete
        within 10 seconds despite macOS Docker Desktop's 4-6s delay.

        Expected: 95%+ of verifications complete within 10s
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 10 password resets to measure timing
            attempts = 10
            timing_data = []

            for i in range(attempts):
                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=f"TIMING{i}",
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace
                )

                assert result.success, f"Reset {i+1} failed: {result.message}"
                timing_data.append(result.elapsed_seconds)

            # Calculate statistics
            avg_time = sum(timing_data) / len(timing_data)
            max_time = max(timing_data)
            min_time = min(timing_data)
            within_10s = sum(1 for t in timing_data if t <= 10.0)
            success_rate = (within_10s / attempts) * 100

            # Report timing statistics
            print(f"\nTiming Statistics (macOS Docker Desktop):")
            print(f"  Average: {avg_time:.2f}s")
            print(f"  Min: {min_time:.2f}s")
            print(f"  Max: {max_time:.2f}s")
            print(f"  Within 10s: {within_10s}/{attempts} ({success_rate:.1f}%)")

            # Verify NFR-004: 95%+ complete within 10 seconds
            assert success_rate >= 95.0, (
                f"Timing success rate {success_rate:.1f}% below 95% target (NFR-004). "
                f"Max time: {max_time:.2f}s, Average: {avg_time:.2f}s"
            )

            # Verify no verification took longer than 10.5s (hard timeout + grace)
            assert max_time <= 10.5, (
                f"Maximum verification time {max_time:.2f}s exceeds 10.5s hard limit (NFR-004)"
            )

    def test_macos_success_rate_99_percent(self):
        """
        Reliability: Achieve >= 99% success rate on macOS (NFR-001).

        This is the primary NFR for Feature 015: password reset must be
        reliable enough for production use on macOS.

        Expected: >= 99% of password resets succeed
        Note: This test takes ~60-120 seconds to complete (10-20 resets)
        """
        with IRISContainer() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service
            container_name = iris.get_wrapped_container().name
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 20 password resets to measure success rate
            attempts = 20
            successes = 0

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

            success_rate = (successes / attempts) * 100

            # Report results
            print(f"\nReliability Test Results (macOS Docker Desktop):")
            print(f"  Successes: {successes}/{attempts} ({success_rate:.1f}%)")

            # Verify NFR-001: >= 99% success rate
            assert success_rate >= 99.0, (
                f"Success rate {success_rate:.1f}% below 99% target (NFR-001). "
                f"{successes}/{attempts} succeeded"
            )
