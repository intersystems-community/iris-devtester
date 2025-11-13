"""
Contract tests for get_container_status API.

These tests verify the API contract without testing implementation.
"""

import pytest
from typing import Tuple


class TestContainerStatusSignature:
    """Test get_container_status function signature and contract."""

    def test_function_exists(self):
        """Contract: get_container_status function must exist."""
        from iris_devtester.utils.container_status import get_container_status
        assert callable(get_container_status)

    def test_signature_accepts_container_name(self):
        """Contract: Function accepts container_name parameter."""
        from iris_devtester.utils.container_status import get_container_status
        import inspect

        sig = inspect.signature(get_container_status)
        assert "container_name" in sig.parameters
        assert sig.parameters["container_name"].default == "iris_db"

    def test_return_type_is_tuple(self):
        """Contract: Function returns Tuple[bool, str]."""
        from iris_devtester.utils.container_status import get_container_status
        import inspect

        sig = inspect.signature(get_container_status)
        assert sig.return_annotation == Tuple[bool, str]


class TestContainerStatusBehavior:
    """Test behavior contracts."""

    @pytest.mark.contract
    def test_status_report_format(self):
        """
        Contract: Success message is multi-line status report.

        Report should include:
        - Container name
        - Running status
        - Health status
        - CallIn status
        - Connection test result

        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T015 complete")
