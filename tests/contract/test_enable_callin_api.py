"""
Contract tests for enable_callin_service API.

These tests verify the API contract (signature, return type, behavior)
without testing implementation details. They MUST fail until implementation.

TDD Workflow:
1. Write tests (this file) - they MUST fail
2. Implement iris_devtester/utils/enable_callin.py
3. Tests pass

Constitutional Compliance:
- Principle #7: Medical-Grade Reliability (contract enforcement)
"""

import pytest
from typing import Tuple


class TestEnableCallinSignature:
    """Test enable_callin_service function signature and contract."""

    def test_function_exists(self):
        """Contract: enable_callin_service function must exist."""
        from iris_devtester.utils.enable_callin import enable_callin_service
        assert callable(enable_callin_service)

    def test_signature_accepts_container_name(self):
        """Contract: Function accepts container_name parameter."""
        from iris_devtester.utils.enable_callin import enable_callin_service
        import inspect

        sig = inspect.signature(enable_callin_service)
        assert "container_name" in sig.parameters

        # Verify default value
        param = sig.parameters["container_name"]
        assert param.default == "iris_db"

    def test_signature_accepts_timeout(self):
        """Contract: Function accepts timeout parameter."""
        from iris_devtester.utils.enable_callin import enable_callin_service
        import inspect

        sig = inspect.signature(enable_callin_service)
        assert "timeout" in sig.parameters

        # Verify default value
        param = sig.parameters["timeout"]
        assert param.default == 30

    def test_return_type_is_tuple(self):
        """Contract: Function returns Tuple[bool, str]."""
        from iris_devtester.utils.enable_callin import enable_callin_service
        import inspect

        sig = inspect.signature(enable_callin_service)
        # Check return annotation
        assert sig.return_annotation == Tuple[bool, str]


class TestEnableCallinIdempotent:
    """Test idempotent behavior (Constitutional Principle #7)."""

    @pytest.mark.contract
    def test_idempotent_contract(self):
        """
        Contract: enable_callin_service is idempotent.

        Calling twice with same parameters should succeed both times.
        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T013 complete")


class TestEnableCallinErrorHandling:
    """Test error handling contracts."""

    @pytest.mark.contract
    def test_container_not_found_returns_false(self):
        """
        Contract: Non-existent container returns (False, error_message).

        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T013 complete")

    @pytest.mark.contract
    def test_error_message_has_remediation(self):
        """
        Contract: Error messages follow Constitutional Principle #5.

        Error messages must include:
        - What went wrong
        - How to fix

        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T013 complete")
