"""Contract tests for package detection logic.

Contract: contracts/no-package-error-contract.json (T006)
Contract: contracts/package-priority-contract.json (T007)
"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestNoPackageError:
    """Contract tests for error when no package installed (T006)."""

    def test_import_error_raised(self):
        """Contract: ImportError raised when neither package installed."""
        # Mock neither package available
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError):
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

    def test_error_message_has_header(self):
        """Contract: Error message starts with header."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            assert "No IRIS Python package detected" in str(exc_info.value)

    def test_error_message_has_what_section(self):
        """Contract: Error message has 'What went wrong' section."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            assert "What went wrong:" in str(exc_info.value)

    def test_error_message_has_why_section(self):
        """Contract: Error message has 'Why this happened' section."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            assert "Why this happened:" in str(exc_info.value)

    def test_error_message_has_how_section(self):
        """Contract: Error message has 'How to fix it' section."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            assert "How to fix it:" in str(exc_info.value)

    def test_error_message_has_documentation_link(self):
        """Contract: Error message has documentation link."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            error_msg = str(exc_info.value)
            assert "Documentation:" in error_msg
            assert "https://" in error_msg

    def test_error_message_suggests_modern_package(self):
        """Contract: Error message suggests modern package."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            assert "intersystems-irispython>=5.3.0" in str(exc_info.value)

    def test_error_message_provides_install_command(self):
        """Contract: Error message provides pip install command."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            assert "pip install" in str(exc_info.value)

    def test_error_message_mentions_both_packages(self):
        """Contract: Error message mentions both packages."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            with pytest.raises(ImportError) as exc_info:
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            error_msg = str(exc_info.value)
            assert "intersystems-irispython" in error_msg
            assert "intersystems-iris" in error_msg

    def test_logging_error_level(self, caplog):
        """Contract: Error logged at ERROR level."""
        def mock_import(name, *args, **kwargs):
            if 'intersystems' in name or 'iris' in name:
                raise ImportError(f"No module named '{name}'")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.ERROR)

            with pytest.raises(ImportError):
                from iris_devtester.utils.dbapi_compat import detect_dbapi_package
                detect_dbapi_package()

            # Should have ERROR log
            assert any(record.levelname == "ERROR" for record in caplog.records)

    def test_both_imports_attempted(self):
        """Contract: Both modern and legacy imports attempted."""
        # This verifies the try/except chain logic
        # Will be validated in T013 implementation
        pytest.skip("Will be validated in T013")


class TestPackagePriority:
    """Contract tests for package priority (T007)."""

    def test_modern_package_selected(self):
        """Contract: Modern package selected when both installed."""
        mock_modern_connect = MagicMock()
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        mock_legacy_connect = MagicMock()
        mock_irissdk = MagicMock()
        mock_irissdk.connect = mock_legacy_connect

        # Both packages available
        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern,
            'iris': MagicMock(),
            'iris.irissdk': mock_irissdk
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.package_name == "intersystems-irispython"

    def test_legacy_package_not_attempted(self, caplog):
        """Contract: Legacy package not attempted when modern available."""
        mock_modern_connect = MagicMock()
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.DEBUG)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            # Should NOT see fallback message
            assert "trying legacy" not in caplog.text.lower()

    def test_connection_uses_modern_package(self):
        """Contract: Connection uses modern package when both available."""
        mock_modern_connect = MagicMock()
        mock_connection = MagicMock()
        mock_modern_connect.return_value = mock_connection
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import get_connection

            conn = get_connection(hostname="localhost", port=1972,
                                 namespace="USER", username="_SYSTEM", password="SYS")
            # Modern package connect should have been called
            mock_modern_connect.assert_called_once()

    def test_detection_time_under_threshold(self):
        """Contract: Detection time <10ms even with both packages."""
        mock_modern_connect = MagicMock()
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.detection_time_ms < 10.0

    def test_package_info_shows_modern(self):
        """Contract: Package info shows modern package."""
        mock_modern_connect = MagicMock()
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            from iris_devtester.utils.dbapi_compat import get_package_info

            info = get_package_info()
            assert info.package_name == "intersystems-irispython"
            assert info.import_path == "intersystems_iris.dbapi._DBAPI"

    def test_logging_modern_package_selected(self, caplog):
        """Contract: Logging clearly indicates modern package selected."""
        mock_modern_connect = MagicMock()
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.INFO)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert "intersystems-irispython" in caplog.text

    def test_no_fallback_in_logs(self, caplog):
        """Contract: No fallback messages when modern available."""
        mock_modern_connect = MagicMock()
        mock_modern = MagicMock()
        mock_modern.connect = mock_modern_connect

        with patch.dict('sys.modules', {
            'intersystems_iris': MagicMock(),
            'intersystems_iris.dbapi': MagicMock(),
            'intersystems_iris.dbapi._DBAPI': mock_modern
        }), patch('importlib.metadata.version', return_value="5.3.0"):
            if 'iris_devtester.utils.dbapi_compat' in sys.modules:
                del sys.modules['iris_devtester.utils.dbapi_compat']

            import logging
            caplog.set_level(logging.DEBUG)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert "fallback" not in caplog.text.lower()
            assert "trying legacy" not in caplog.text.lower()

    def test_modern_invalid_legacy_valid_raises_error(self):
        """Contract: Modern invalid version + legacy valid = error (not fallback)."""
        # Modern package v5.2.0 (too old), should fail even if legacy valid
        pytest.skip("Complex scenario - will validate in T013/T014")

    def test_modern_valid_legacy_invalid_uses_modern(self):
        """Contract: Modern valid + legacy invalid = uses modern."""
        # Modern v5.3.0, legacy v2.9.0 (invalid) → modern used
        pytest.skip("Complex scenario - will validate in T013/T014")
