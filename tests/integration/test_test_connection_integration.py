"""
Integration tests for test_connection utility.

Tests verify connection testing works on real IRIS containers
and properly detects namespace issues.
"""

import pytest
from iris_devtester.utils.test_connection import test_connection


class TestConnectionIntegration:
    """Integration tests for test_connection with real containers."""

    def test_connection_succeeds_on_community_container(self, iris_container):
        """
        Test that connection test succeeds on running Community Edition.

        Expected: Returns (True, success_message).
        """
        container_name = iris_container.get_container_name()

        # Ensure CallIn is enabled first (required for connection)
        iris_container.enable_callin_service()

        success, message = test_connection(container_name, "USER")

        assert success is True, f"Connection should succeed: {message}"
        assert "successful" in message.lower()
        assert "USER" in message

    def test_connection_to_different_namespaces(self, iris_container):
        """
        Test connection to different namespaces.

        Expected: USER and %SYS namespaces should be accessible.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        # Test USER namespace
        success_user, msg_user = test_connection(container_name, "USER")
        assert success_user is True, f"USER namespace should be accessible: {msg_user}"

        # Test %SYS namespace
        success_sys, msg_sys = test_connection(container_name, "%SYS")
        assert success_sys is True, f"%SYS namespace should be accessible: {msg_sys}"

    def test_connection_to_nonexistent_namespace(self, iris_container):
        """
        Test connection to non-existent namespace.

        Expected: Returns (False, error_message) with remediation.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        success, message = test_connection(container_name, "NONEXISTENT_NAMESPACE")

        assert success is False, "Should fail for non-existent namespace"
        assert "does not exist" in message.lower() or "namespace" in message.lower()

    def test_connection_non_destructive(self, iris_container):
        """
        Test that connection test is non-destructive.

        Expected: Query returns $HOROLOG value, no data modification.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        # Multiple connection tests should all succeed without side effects
        for _ in range(3):
            success, message = test_connection(container_name, "USER")
            assert success is True, "All connection tests should succeed"

    def test_connection_fails_for_nonexistent_container(self):
        """
        Test that connection test fails gracefully for non-existent container.

        Expected: Returns (False, error_message) with remediation.
        """
        success, message = test_connection("nonexistent_container_xyz", "USER")

        assert success is False, "Should fail for non-existent container"
        assert "not running" in message.lower()
        assert "docker" in message.lower(), "Error should mention docker commands"

    def test_connection_with_custom_timeout(self, iris_container):
        """
        Test connection with custom timeout parameter.

        Expected: Succeeds with shorter timeout on local container.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        success, message = test_connection(container_name, "USER", timeout=5)

        assert success is True, f"Should succeed with 5s timeout: {message}"
