"""Contract tests for modern package detection.

Contract: contracts/modern-package-contract.json
Tests the detection and usage of intersystems-irispython (modern package).

CRITICAL: These tests use the OFFICIAL iris.connect() API (Constitutional Principle #8).
The _DBAPI private module does NOT exist in intersystems-irispython v5.1.2 or v5.3.0.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestModernPackageContract:
    """Contract tests for modern package (intersystems-irispython)."""

    def test_modern_package_detected(self):
        """Contract: Modern package detected when installed."""
        # Mock modern package available (official iris module, NOT _DBAPI!)
        mock_connect = MagicMock()
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        with patch.dict('sys.modules', {
            'iris': mock_iris
        }):
            # Clear module cache to force re-detection
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            # This will fail until T013 is implemented
            info = detect_dbapi_package()
            assert info.package_name == "intersystems-irispython"

    def test_modern_package_import_path(self):
        """Contract: Modern package uses correct import path."""
        mock_connect = MagicMock()
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        with patch.dict('sys.modules', {
            'iris': mock_iris
        }):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.import_path == "iris"  # NOT "intersystems_iris.dbapi._DBAPI"!

    def test_connection_successful(self):
        """Contract: Connection succeeds using modern package."""
        mock_connect = MagicMock()
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        with patch.dict('sys.modules', {
            'iris': mock_iris
        }):
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

    def test_detection_time_under_threshold(self):
        """Contract: Detection completes in <10ms (NFR-001)."""
        mock_connect = MagicMock()
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        with patch.dict('sys.modules', {
            'iris': mock_iris
        }):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.detection_time_ms < 10.0, f"Detection took {info.detection_time_ms}ms (>10ms)"

    def test_package_info_correct(self):
        """Contract: Package info contains correct metadata."""
        mock_connect = MagicMock()
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        with patch.dict('sys.modules', {
            'iris': mock_iris
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import get_package_info

            info = get_package_info()
            assert info.package_name == "intersystems-irispython"
            assert info.version == "5.3.0"
            assert info.import_path == "iris"  # Official API!

    def test_logging_modern_package(self, caplog):
        """Contract: Logging indicates modern package selected."""
        mock_connect = MagicMock()
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        with patch.dict('sys.modules', {
            'iris': mock_iris
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.INFO)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert "intersystems-irispython" in caplog.text

    def test_version_validation(self):
        """Contract: Version validation enforces minimum version."""
        # Clear module cache first
        if 'iris_devtester.utils.dbapi_compat' in sys.modules:
            del sys.modules['iris_devtester.utils.dbapi_compat']

        mock_connect = MagicMock()
        mock_iris = MagicMock()
        mock_iris.connect = mock_connect

        # Test with old version (should fail - minimum is 5.1.2)
        # Mock both the iris module AND importlib.metadata.version
        with patch.dict('sys.modules', {'iris': mock_iris}), \
             patch('iris_devtester.utils.dbapi_compat.importlib.metadata.version', return_value="5.1.0"):

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            # Check for version incompatibility message
            error_message = str(exc_info.value)
            assert "5.1.0" in error_message  # Version should be mentioned
            assert ("incompatible" in error_message.lower() or
                    "minimum required" in error_message.lower())
