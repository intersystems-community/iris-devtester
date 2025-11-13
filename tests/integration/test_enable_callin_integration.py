"""
Integration tests for enable_callin_service utility.

Tests verify CallIn service can be enabled on real IRIS containers
and that the service configuration persists.
"""

import pytest
import subprocess
from iris_devtester.utils.enable_callin import enable_callin_service


class TestEnableCallinIntegration:
    """Integration tests for enable_callin_service with real containers."""

    def test_enable_callin_on_community_container(self, iris_container):
        """
        Test enabling CallIn service on Community Edition container.

        Expected: Service enabled successfully, returns True.
        """
        container_name = iris_container.get_container_name()

        success, message = enable_callin_service(container_name)

        assert success is True, f"CallIn enablement should succeed: {message}"
        assert "enabled" in message.lower() or "configured" in message.lower()

    def test_enable_callin_idempotent(self, iris_container):
        """
        Test that enabling CallIn twice is idempotent.

        Expected: Both calls return True, no errors on second call.
        """
        container_name = iris_container.get_container_name()

        # First call
        success1, message1 = enable_callin_service(container_name)
        assert success1 is True, f"First call should succeed: {message1}"

        # Second call (idempotent)
        success2, message2 = enable_callin_service(container_name)
        assert success2 is True, f"Second call should succeed: {message2}"

    def test_callin_service_persists(self, iris_container):
        """
        Test that CallIn service configuration persists.

        Expected: After enabling, service should remain enabled.
        """
        container_name = iris_container.get_container_name()

        # Enable CallIn
        success, _ = enable_callin_service(container_name)
        assert success is True

        # Verify via ObjectScript query
        check_cmd = [
            "docker",
            "exec",
            container_name,
            "bash",
            "-c",
            'echo "Do ##class(Security.Services).Get(\\"%Service_CallIn\\",.prop) Write prop(\\"Enabled\\")" | iris session IRIS -U %SYS',
        ]

        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)

        assert result.returncode == 0, "ObjectScript query should succeed"
        assert "1" in result.stdout, "CallIn Enabled should be 1"

    def test_enable_callin_returns_error_for_nonexistent_container(self):
        """
        Test that enabling CallIn on non-existent container returns error.

        Expected: Returns (False, error_message) with remediation.
        """
        success, message = enable_callin_service("nonexistent_container_xyz")

        assert success is False, "Should fail for non-existent container"
        assert "not running" in message.lower() or "not found" in message.lower()
        assert "docker" in message.lower(), "Error should mention docker commands"
