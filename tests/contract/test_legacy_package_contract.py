"""Contract tests for legacy package fallback.

Contract: contracts/legacy-package-contract.json
Tests the detection and fallback to intersystems-iris (legacy package).
"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestLegacyPackageContract:
    """Contract tests for legacy package (intersystems-iris)."""

    def test_legacy_package_detected(self):
        """Contract: Legacy package detected when modern unavailable."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        # Mock legacy package available, modern unavailable
        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            # This will fail until T013 is implemented
            info = detect_dbapi_package()
            assert info.package_name == "intersystems-iris"

    def test_legacy_package_import_path(self):
        """Contract: Legacy package uses correct import path."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.import_path == "iris.irissdk"

    def test_connection_successful(self):
        """Contract: Connection succeeds using legacy package."""
        mock_connect = MagicMock()
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import get_connection

            conn = get_connection(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="_SYSTEM",
                password="SYS"
            )
            assert conn is not None

    def test_modern_package_attempted_first(self, caplog):
        """Contract: Modern package attempted before fallback."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.DEBUG)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            # Should see DEBUG log indicating fallback
            assert "trying legacy" in caplog.text.lower() or "fallback" in caplog.text.lower()

    def test_fallback_occurred(self):
        """Contract: Fallback from modern to legacy occurred."""
        # This test verifies the fallback mechanism works
        # Implementation in T013
        pytest.skip("Will be implemented in T013")

    def test_detection_time_under_threshold(self):
        """Contract: Detection completes in <10ms even with fallback."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.detection_time_ms < 10.0

    def test_package_info_correct(self):
        """Contract: Package info contains correct legacy metadata."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import), \
             patch('importlib.metadata.version', return_value="3.2.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import get_package_info

            info = get_package_info()
            assert info.package_name == "intersystems-iris"
            assert info.version == "3.2.0"

    def test_logging_legacy_package(self, caplog):
        """Contract: Logging indicates legacy package selected."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import), \
             patch('importlib.metadata.version', return_value="3.2.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.INFO)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert "intersystems-iris" in caplog.text and "legacy" in caplog.text.lower()

    def test_version_validation(self):
        """Contract: Version validation enforces minimum version (3.0.0)."""
        mock_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_connect

        def mock_import(name, *args, **kwargs):
            if name == 'intersystems_iris.dbapi._DBAPI':
                raise ImportError("Modern package not available")
            return MagicMock()

        # Test with old version
        with patch.dict('sys.modules', {
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('builtins.__import__', side_effect=mock_import), \
             patch('importlib.metadata.version', return_value="2.9.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError):
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

    def test_backward_compatibility_fixtures(self):
        """Contract: DAT fixtures work with legacy package."""
        # Integration test - will be implemented in T009
        pytest.skip("Integration test - implement in T009")

    def test_backward_compatibility_connections(self):
        """Contract: Connections work with legacy package."""
        # Integration test - will be implemented in T009
        pytest.skip("Integration test - implement in T009")
