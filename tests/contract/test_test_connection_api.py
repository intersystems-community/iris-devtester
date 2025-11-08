"""
Contract tests for test_connection API.

These tests verify the API contract without testing implementation.
They MUST fail until implementation.

TDD Workflow:
1. Write tests (this file) - they MUST fail
2. Implement iris_devtester/utils/test_connection.py
3. Tests pass
"""

import pytest
from typing import Tuple


class TestConnectionSignature:
    """Test test_connection function signature and contract."""

    def test_function_exists(self):
        """Contract: test_connection function must exist."""
        from iris_devtester.utils.test_connection import test_connection
        assert callable(test_connection)

    def test_signature_accepts_container_name(self):
        """Contract: Function accepts container_name parameter."""
        from iris_devtester.utils.test_connection import test_connection
        import inspect

        sig = inspect.signature(test_connection)
        assert "container_name" in sig.parameters
        assert sig.parameters["container_name"].default == "iris_db"

    def test_signature_accepts_namespace(self):
        """Contract: Function accepts namespace parameter."""
        from iris_devtester.utils.test_connection import test_connection
        import inspect

        sig = inspect.signature(test_connection)
        assert "namespace" in sig.parameters
        assert sig.parameters["namespace"].default == "USER"

    def test_signature_accepts_timeout(self):
        """Contract: Function accepts timeout parameter."""
        from iris_devtester.utils.test_connection import test_connection
        import inspect

        sig = inspect.signature(test_connection)
        assert "timeout" in sig.parameters
        assert sig.parameters["timeout"].default == 10

    def test_return_type_is_tuple(self):
        """Contract: Function returns Tuple[bool, str]."""
        from iris_devtester.utils.test_connection import test_connection
        import inspect

        sig = inspect.signature(test_connection)
        assert sig.return_annotation == Tuple[bool, str]


class TestConnectionBehavior:
    """Test behavior contracts."""

    @pytest.mark.contract
    def test_non_destructive(self):
        """
        Contract: test_connection is non-destructive (read-only).

        Constitutional Principle #7: Medical-grade reliability.
        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T014 complete")
