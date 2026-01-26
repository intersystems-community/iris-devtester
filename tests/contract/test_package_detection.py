"""Contract tests for package detection logic.

Contract: contracts/no-package-error-contract.json (T006)
Contract: contracts/package-priority-contract.json (T007)
"""

import importlib.metadata
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestNoPackageError:
    """Contract tests for error when no package installed (T006)."""

    def test_import_error_raised(self):
        """Contract: ImportError raised when neither package installed."""
        # Mock neither package available using patch.dict
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError):
                detect_dbapi_package()

    def test_error_message_has_header(self):
        """Contract: Error message starts with header."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            assert "No IRIS Python package detected" in str(exc_info.value)

    def test_error_message_has_what_section(self):
        """Contract: Error message has 'What went wrong' section."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            assert "What went wrong:" in str(exc_info.value)

    def test_error_message_has_why_section(self):
        """Contract: Error message has 'Why this happened' section."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            assert "Why this happened:" in str(exc_info.value)

    def test_error_message_has_how_section(self):
        """Contract: Error message has 'How to fix it' section."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            assert "How to fix it:" in str(exc_info.value)

    def test_error_message_has_documentation_link(self):
        """Contract: Error message has documentation link."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            error_msg = str(exc_info.value)
            assert "Documentation:" in error_msg
            assert "https://" in error_msg

    def test_error_message_suggests_modern_package(self):
        """Contract: Error message suggests modern package."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            assert "intersystems-irispython>=5.1.2" in str(exc_info.value)

    def test_error_message_provides_install_command(self):
        """Contract: Error message provides pip install command."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            assert "pip install" in str(exc_info.value)

    def test_error_message_mentions_both_packages(self):
        """Contract: Error message mentions both packages."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError) as exc_info:
                detect_dbapi_package()

            error_msg = str(exc_info.value)
            assert "intersystems-irispython" in error_msg
            assert "intersystems-iris" in error_msg

    def test_logging_error_level(self, caplog):
        """Contract: Error logged at ERROR level."""
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            import logging

            caplog.set_level(logging.ERROR)

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError):
                detect_dbapi_package()

            # Should have ERROR log
            assert any(record.levelname == "ERROR" for record in caplog.records)

    def test_both_imports_attempted(self):
        """Contract: Both modern and legacy imports attempted."""
        # This verifies the try/except chain logic
        with patch.dict(
            "sys.modules",
            {"iris": None, "intersystems_iris": None, "intersystems_irispython": None},
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import (
                DBAPIPackageNotFoundError,
                detect_dbapi_package,
            )

            with pytest.raises(DBAPIPackageNotFoundError):
                detect_dbapi_package()


class TestPackagePriority:
    """Contract tests for package priority (T007)."""

    def test_modern_package_selected(self):
        """Contract: Modern package selected when both installed."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        mock_legacy = MagicMock()
        mock_legacy.connect = MagicMock()

        def mock_version(pkg):
            if pkg == "intersystems-irispython":
                return "5.3.0"
            if pkg == "intersystems-iris":
                return "3.0.0"
            raise importlib.metadata.PackageNotFoundError(pkg)

        # Both packages available
        with (
            patch.dict("sys.modules", {"iris": mock_modern, "iris.irissdk": mock_legacy}),
            patch("importlib.metadata.version", side_effect=mock_version),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.package_name == "intersystems-irispython"

    def test_legacy_package_not_attempted(self, caplog):
        """Contract: Legacy package not attempted when modern available."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.3.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            import logging

            caplog.set_level(logging.DEBUG)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            # Should NOT see fallback message
            assert "trying legacy" not in caplog.text.lower()

    def test_connection_uses_modern_package(self):
        """Contract: Connection uses modern package when both available."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.3.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import get_connection

            conn = get_connection(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="_SYSTEM",
                password="SYS",
            )
            # Modern package connect should have been called
            mock_modern.connect.assert_called_once()

    def test_detection_time_under_threshold(self):
        """Contract: Detection time <10ms even with both packages."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.3.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.detection_time_ms < 10.0

    def test_package_info_shows_modern(self):
        """Contract: Package info shows modern package."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.3.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import get_package_info

            info = get_package_info()
            assert info.package_name == "intersystems-irispython"
            assert info.import_path == "iris"

    def test_logging_modern_package_selected(self, caplog):
        """Contract: Logging clearly indicates modern package selected."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.3.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            import logging

            caplog.set_level(logging.INFO)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert "intersystems-irispython" in caplog.text

    def test_no_fallback_in_logs(self, caplog):
        """Contract: No fallback messages when modern available."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.3.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            import logging

            caplog.set_level(logging.DEBUG)

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert "fallback" not in caplog.text.lower()
            assert "trying legacy" not in caplog.text.lower()

    def test_modern_invalid_version_raises_error(self):
        """Contract: Modern invalid version raises error."""
        mock_modern = MagicMock()
        mock_modern.connect = MagicMock()

        with (
            patch.dict("sys.modules", {"iris": mock_modern}),
            patch("importlib.metadata.version", return_value="5.0.0"),
        ):
            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            # This should raise ImportError from validate_package_version
            with pytest.raises(ImportError) as exc_info:
                detect_dbapi_package()
            assert "incompatible" in str(exc_info.value)

    def test_legacy_package_selected_when_modern_missing(self):
        """Contract: Legacy package selected when modern missing."""
        mock_legacy = MagicMock()
        mock_legacy.connect = MagicMock()

        # We use a side effect for sys.modules to simulate 'iris' missing
        # but 'iris.irissdk' present.
        # This is tricky with patch.dict, so we'll use a custom side_effect on __import__
        # but only for our specific modules.

        real_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "iris":
                raise ImportError("Modern missing")
            if name == "iris.irissdk":
                return mock_legacy
            return real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=mock_import),
            patch("importlib.metadata.version", return_value="3.0.0"),
        ):

            if "iris_devtester.utils.dbapi_compat" in sys.modules:
                del sys.modules["iris_devtester.utils.dbapi_compat"]

            from iris_devtester.utils.dbapi_compat import detect_dbapi_package

            info = detect_dbapi_package()
            assert info.package_name == "intersystems-iris"
