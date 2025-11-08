"""
Integration tests for get_container_status utility.

Tests verify comprehensive status reporting on real IRIS containers.
"""

import pytest
from iris_devtester.utils.container_status import get_container_status


class TestContainerStatusIntegration:
    """Integration tests for get_container_status with real containers."""

    def test_status_on_running_container(self, iris_container):
        """
        Test status report on running Community Edition container.

        Expected: Returns (True, multi-line_status_report).
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        success, status_report = get_container_status(container_name)

        assert success is True, f"Status check should succeed: {status_report}"

        # Verify report contains expected sections
        assert f"Container Status: {container_name}" in status_report
        assert "Running:" in status_report
        assert "✓" in status_report, "Should contain success checkmark"
        assert "Overall:" in status_report

    def test_status_report_format(self, iris_container):
        """
        Test that status report has multi-line format.

        Expected: Contains separator, multiple status lines.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        success, status_report = get_container_status(container_name)

        assert success is True
        assert "━" in status_report, "Should contain separator line"

        lines = status_report.split("\n")
        assert len(lines) >= 5, f"Should have multiple lines, got {len(lines)}"

    def test_status_includes_connection_test(self, iris_container):
        """
        Test that status report includes connection test result.

        Expected: Status includes "Connection:" line.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        success, status_report = get_container_status(container_name)

        assert success is True
        assert "Connection:" in status_report
        assert "USER namespace" in status_report

    def test_status_on_nonexistent_container(self):
        """
        Test status check on non-existent container.

        Expected: Returns (False, error_message) with remediation.
        """
        success, status_report = get_container_status("nonexistent_container_xyz")

        assert success is False, "Should fail for non-existent container"
        assert "Running:" in status_report
        assert "✗" in status_report, "Should contain failure mark"
        assert "docker start" in status_report, "Should include remediation"

    def test_status_aggregates_multiple_checks(self, iris_container):
        """
        Test that status aggregates running, health, and connection checks.

        Expected: All three checks present in report.
        """
        container_name = iris_container.get_container_name()
        iris_container.enable_callin_service()

        success, status_report = get_container_status(container_name)

        assert success is True

        # Verify all status dimensions included
        assert "Running:" in status_report, "Should check running status"
        assert "Health:" in status_report or "healthcheck" in status_report.lower(), "Should check health"
        assert "Connection:" in status_report, "Should check connection"
        assert "Overall:" in status_report, "Should have overall summary"
