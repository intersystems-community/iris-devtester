"""
Contract tests for IRISContainer.attach() method.

These tests verify the API contract for attaching to existing containers.
Tests check method exists and signature, behavior tests skip until implementation.

TDD Workflow:
1. Write tests (this file) - signature tests pass, behavior tests skip
2. Implement IRISContainer.attach() in iris_container.py
3. All tests pass
"""

import pytest


class TestAttachMethodSignature:
    """Test IRISContainer.attach() method signature (T011)."""

    def test_attach_method_exists(self):
        """Contract: IRISContainer.attach() class method must exist."""
        from iris_devtester.containers.iris_container import IRISContainer
        assert hasattr(IRISContainer, "attach")
        assert callable(getattr(IRISContainer, "attach"))

    def test_attach_is_classmethod(self):
        """Contract: attach() is a class method, not instance method."""
        from iris_devtester.containers.iris_container import IRISContainer
        import inspect

        # Class methods have __func__ attribute
        method = getattr(IRISContainer, "attach")
        assert isinstance(inspect.getattr_static(IRISContainer, "attach"), classmethod)

    def test_attach_signature(self):
        """Contract: attach() accepts container_name parameter."""
        from iris_devtester.containers.iris_container import IRISContainer
        import inspect

        sig = inspect.signature(IRISContainer.attach)
        params = list(sig.parameters.keys())
        # First param is 'cls' (class method), second is container_name
        assert "container_name" in params

    def test_attach_returns_iriscontainer(self):
        """Contract: attach() returns IRISContainer instance."""
        from iris_devtester.containers.iris_container import IRISContainer
        import inspect

        sig = inspect.signature(IRISContainer.attach)
        # Return annotation should be IRISContainer or "IRISContainer" (string)
        return_annotation = sig.return_annotation
        assert return_annotation in [IRISContainer, "IRISContainer", "\"IRISContainer\""]


class TestAttachLifecycleGuards:
    """Test lifecycle method guards for attached containers (T012)."""

    @pytest.mark.contract
    def test_attached_container_rejects_start(self):
        """
        Contract: Attached container raises error on start().

        Lifecycle management is disabled for attached containers.
        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T020 complete")

    @pytest.mark.contract
    def test_attached_container_rejects_stop(self):
        """
        Contract: Attached container raises error on stop().

        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T020 complete")

    @pytest.mark.contract
    def test_attached_container_rejects_context_manager(self):
        """
        Contract: Attached container raises error on __enter__/__exit__.

        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T020 complete")

    @pytest.mark.contract
    def test_utility_methods_work_on_attached(self):
        """
        Contract: Utility methods (get_connection, enable_callin, etc.) work on attached containers.

        Only lifecycle methods are disabled.
        This test will fail until implementation is complete.
        """
        pytest.skip("Implementation required - test will fail until T020 complete")
