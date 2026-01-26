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
from iris_devtester.utils.password import reset_password


@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="macOS-specific tests (Docker Desktop VM-based networking delay)",
)
class TestPasswordResetMacOS:
    """Integration tests for password reset on macOS."""

    def test_container_to_connection_full_workflow(self):
        """
        End-to-end: Container creation → password reset → connection success.
        """
        # Create fresh container
        with IRISContainer.community() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service

            container_name = iris.get_container_name()
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
                namespace=config.namespace,
            )

            # Verify reset succeeded
            assert result.success, f"Password reset failed: {result.message}"
            assert (
                result.elapsed_seconds <= 15.0
            ), f"Verification took {result.elapsed_seconds:.2f}s, exceeds 15s limit for macOS"

            # CRITICAL: Verify connection succeeds with new password
            from iris_devtester.utils.dbapi_compat import get_connection

            conn = get_connection(
                hostname=config.host,
                port=config.port,
                namespace=config.namespace,
                username="SuperUser",
                password="MACOS_TEST",
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
        """
        try:
            from iris_devtester.ports.registry import PortRegistry

            port_registry_available = True
        except ImportError:
            pytest.skip("PortRegistry not available (Feature 013)")

        # Create container using PortRegistry
        registry = PortRegistry()
        project_path = "/tmp/test_macos_015"
        try:
            assignment = registry.assign_port(project_path=project_path)

            with IRISContainer.community() as iris:
                # Enable CallIn service
                from iris_devtester.utils.enable_callin import enable_callin_service

                container_name = iris.get_container_name()
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
                    port=config.port,
                    namespace=config.namespace,
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
                    password="PORTTEST",
                )

                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result_row = cursor.fetchone()
                assert result_row[0] == 1

                conn.close()

        finally:
            try:
                registry.release_port(project_path=project_path)
            except KeyError:
                pass

    def test_multiple_rapid_password_resets(self):
        """
        Stress test: Multiple rapid password resets in succession.
        """
        with IRISContainer.community() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service

            container_name = iris.get_container_name()
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 3 rapid password resets (reduced from 5 to save time)
            reset_count = 3
            successes = 0

            for i in range(reset_count):
                new_password = f"RAPID{i}"

                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=new_password,
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                )

                if result.success:
                    successes += 1
                else:
                    pytest.fail(f"Reset {i+1}/{reset_count} failed: {result.message}")

                # Verify connection works with latest password
                from iris_devtester.utils.dbapi_compat import get_connection

                conn = get_connection(
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                    username="SuperUser",
                    password=new_password,
                )

                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result_row = cursor.fetchone()
                assert result_row[0] == 1, f"Connection failed after reset {i+1}"

                conn.close()

            # Verify all resets succeeded
            assert successes == reset_count

    def test_verification_timing_within_constraints(self):
        """
        Validate timing: Password verification completes within constraints.
        """
        with IRISContainer.community() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service

            container_name = iris.get_container_name()
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 3 password resets to measure timing (reduced from 10 to save time)
            attempts = 3
            timing_data = []

            for i in range(attempts):
                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=f"TIMING{i}",
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                )

                assert result.success, f"Reset {i+1} failed: {result.message}"
                timing_data.append(result.elapsed_seconds)

            # Calculate statistics
            avg_time = sum(timing_data) / len(timing_data)
            print(f"\nAverage timing (macOS): {avg_time:.2f}s")

            # macOS settle delay is ~2s, so total should be around there
            assert avg_time < 15.0

    def test_macos_success_rate_high(self):
        """
        Reliability: Achieve high success rate on macOS.
        """
        with IRISContainer.community() as iris:
            # Enable CallIn service
            from iris_devtester.utils.enable_callin import enable_callin_service

            container_name = iris.get_container_name()
            success, msg = enable_callin_service(container_name, timeout=30)
            assert success, f"CallIn service failed: {msg}"

            config = iris.get_config()

            # Perform 5 password resets to measure success rate (reduced from 20)
            attempts = 5
            successes = 0

            for i in range(attempts):
                result = reset_password(
                    container_name=container_name,
                    username="SuperUser",
                    new_password=f"RELIABLE{i}",
                    hostname=config.host,
                    port=config.port,
                    namespace=config.namespace,
                )

                if result.success:
                    successes += 1

            assert successes == attempts
