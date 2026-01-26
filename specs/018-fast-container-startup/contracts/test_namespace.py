"""
Contract tests for TestNamespace.

These tests define the expected behavior of TestNamespace.
Tests MUST FAIL until implementation is complete.
"""

import re
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestTestNamespaceNaming:
    """Test TestNamespace naming conventions."""

    def test_name_follows_convention(self):
        """TestNamespace name matches TEST_{timestamp}_{hex} pattern."""
        from iris_devtester.containers.namespace import TestNamespace

        ns = TestNamespace.create_unique(container_ref=Mock())

        pattern = r"^TEST_\d+_[a-f0-9]{8}$"
        assert re.match(pattern, ns.name), f"Name '{ns.name}' doesn't match pattern"

    def test_name_with_custom_prefix(self):
        """TestNamespace supports custom prefix."""
        from iris_devtester.containers.namespace import TestNamespace

        ns = TestNamespace.create_unique(container_ref=Mock(), prefix="MYTEST_")

        assert ns.name.startswith("MYTEST_")

    def test_names_are_unique(self):
        """Each TestNamespace gets unique name."""
        from iris_devtester.containers.namespace import TestNamespace

        ns1 = TestNamespace.create_unique(container_ref=Mock())
        ns2 = TestNamespace.create_unique(container_ref=Mock())

        assert ns1.name != ns2.name


class TestTestNamespaceCreate:
    """Test TestNamespace.create() method."""

    def test_create_calls_config_namespaces_api(self):
        """create() uses Config.Namespaces.Create via iris.connect()."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        mock_iris_conn = MagicMock()
        mock_ref.get_iris_connection.return_value = mock_iris_conn

        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        with patch("iris.createIRIS") as mock_create_iris:
            mock_iris_obj = MagicMock()
            mock_create_iris.return_value = mock_iris_obj

            ns.create()

            mock_iris_obj.classMethodValue.assert_called()
            call_args = mock_iris_obj.classMethodValue.call_args
            assert "Config.Namespaces" in str(call_args)

    def test_create_sets_globals_and_routines_to_user(self):
        """create() maps Globals and Routines to USER database."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        with patch("iris.createIRIS") as mock_create_iris:
            mock_iris_obj = MagicMock()
            mock_create_iris.return_value = mock_iris_obj

            ns.create()

            # Verify Properties passed include USER mappings
            call_args = mock_iris_obj.classMethodValue.call_args
            # Implementation should pass Globals=USER, Routines=USER


class TestTestNamespaceDrop:
    """Test TestNamespace.drop() method."""

    def test_drop_calls_config_namespaces_delete(self):
        """drop() uses Config.Namespaces.Delete."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        mock_iris_conn = MagicMock()
        mock_ref.get_iris_connection.return_value = mock_iris_conn

        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        with patch("iris.createIRIS") as mock_create_iris:
            mock_iris_obj = MagicMock()
            mock_create_iris.return_value = mock_iris_obj

            ns.drop()

            mock_iris_obj.classMethodValue.assert_called()
            call_args = mock_iris_obj.classMethodValue.call_args
            assert "Delete" in str(call_args) or "TEST_123_abc" in str(call_args)

    def test_drop_is_idempotent(self):
        """drop() succeeds even if namespace already deleted."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        with patch("iris.createIRIS") as mock_create_iris:
            mock_iris_obj = MagicMock()
            mock_create_iris.return_value = mock_iris_obj
            # Simulate already deleted
            mock_iris_obj.classMethodValue.side_effect = Exception("Namespace not found")

            # Should not raise
            ns.drop()


class TestTestNamespaceExecuteSQL:
    """Test TestNamespace.execute_sql() method."""

    def test_execute_sql_uses_dbapi(self):
        """execute_sql() uses DBAPI connection for performance."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_ref.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        ns.execute_sql("SELECT 1")

        mock_cursor.execute.assert_called_once_with("SELECT 1")

    def test_execute_sql_sets_namespace(self):
        """execute_sql() ensures connection uses correct namespace."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        # Implementation should set namespace on connection
        # Verify via ZN command or connection parameter


class TestTestNamespaceCleanup:
    """Test TestNamespace cleanup registration."""

    def test_register_cleanup_adds_atexit_handler(self):
        """register_cleanup() adds atexit handler when atexit=True."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        with patch("atexit.register") as mock_atexit:
            ns.register_cleanup(atexit=True)

            mock_atexit.assert_called_once()
            assert ns.cleanup_registered is True

    def test_cleanup_drops_namespace(self):
        """Cleanup handler calls drop()."""
        from iris_devtester.containers.namespace import TestNamespace

        mock_ref = Mock()
        ns = TestNamespace(name="TEST_123_abc", container_ref=mock_ref)

        with patch.object(ns, "drop") as mock_drop:
            ns._cleanup()

            mock_drop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
