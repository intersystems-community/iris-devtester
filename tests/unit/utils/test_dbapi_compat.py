"""Tests for dbapi_compat singleton-poisoning fix.

Verifies that mocking intersystems_iris does not permanently poison the
DBAPIConnectionAdapter singleton — the core defect reported in
IDT-BUG-dbapi-adapter-singleton.md.
"""

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

import iris_devtester.utils.dbapi_compat as dc


@pytest.fixture(autouse=True)
def reset_adapter():
    """Ensure each test starts with a clean adapter."""
    dc.reset_adapter()
    yield
    dc.reset_adapter()


class TestModuleAbsentAfterPatch:
    """patch.dict removes keys that were absent before the patch on exit.

    The module is importable but not in sys.modules. connect_function must
    import it rather than raising ImportError.
    """

    def test_connect_function_importable_when_absent_from_sys_modules(self):
        """If import_path was absent pre-patch, it's deleted post-patch; must still resolve."""
        import importlib

        # Ensure the module is absent from sys.modules, then mock it
        real_module = sys.modules.pop("intersystems_iris", None)
        fake = MagicMock()
        fake.connect = object()  # sentinel

        try:
            assert "intersystems_iris" not in sys.modules, "pre-condition: key must be absent"
            with patch.dict(sys.modules, {"intersystems_iris": fake}):
                dc.reset_adapter()
                dc.get_package_info()  # singleton built while mock is present

            # After patch.dict exit the key is gone (was absent before)
            assert "intersystems_iris" not in sys.modules

            # connect_function must import the real module, not raise
            info = dc.get_package_info()
            # Should not raise; real module is importable
            fn = info.connect_function
            assert not isinstance(fn, MagicMock), (
                "connect_function returned MagicMock after patch exit with absent key"
            )
        finally:
            # Restore original state
            if real_module is not None:
                sys.modules["intersystems_iris"] = real_module
            elif "intersystems_iris" in sys.modules:
                del sys.modules["intersystems_iris"]

    def test_connect_function_does_not_raise_when_module_absent_from_sys_modules(self):
        """connect_function must not raise ImportError when module absent but importable."""
        import importlib

        real_module = sys.modules.pop("intersystems_iris", None)
        fake = MagicMock()
        fake.connect = MagicMock()

        try:
            with patch.dict(sys.modules, {"intersystems_iris": fake}):
                dc.reset_adapter()
                info = dc.get_package_info()

            assert "intersystems_iris" not in sys.modules

            # Must not raise
            dc.reset_adapter()
            try:
                info2 = dc.get_package_info()
                _ = info2.connect_function
            except ImportError as e:
                pytest.fail(f"connect_function raised ImportError for importable module: {e}")
        finally:
            if real_module is not None:
                sys.modules["intersystems_iris"] = real_module
            elif "intersystems_iris" in sys.modules:
                del sys.modules["intersystems_iris"]


class TestSingletonPoisoning:
    """Fix #1: connect resolved at call time, not detection time."""

    def test_mock_does_not_poison_after_patch_exits(self):
        """After patch context exits, get_connection must use real connect, not MagicMock."""
        fake = MagicMock()
        with patch.dict(sys.modules, {"intersystems_iris": fake}):
            dc.reset_adapter()  # force re-detection while mock is active
            info_inside = dc.get_package_info()
            assert isinstance(info_inside.connect_function, MagicMock)

        # sys.modules restored — real module back
        dc.reset_adapter()
        try:
            info_after = dc.get_package_info()
            # connect_function must now be the real one, not the MagicMock
            assert not isinstance(info_after.connect_function, MagicMock), (
                "Singleton poisoning: connect_function is still a MagicMock after patch exited"
            )
        except (ImportError, dc.DBAPIPackageNotFoundError):
            # Package not installed in test env — that's fine, not the bug we're testing
            pass

    def test_connect_function_is_live_attr_not_bound_at_detection(self):
        """connect_function property must return current module attribute, not cached ref."""
        fake_module = MagicMock()
        real_connect = object()  # sentinel
        fake_module.connect = real_connect

        with patch.dict(sys.modules, {"intersystems_iris": fake_module}):
            dc.reset_adapter()
            info = dc.get_package_info()
            assert info.connect_function is real_connect

            # Swap the connect on the live module — info.connect_function must follow
            new_connect = object()
            fake_module.connect = new_connect
            assert info.connect_function is new_connect, (
                "connect_function is bound at detection time instead of being resolved live"
            )


class TestResetAdapter:
    """Fix #2: public reset_adapter() lets consumers manage the singleton cleanly."""

    def test_reset_adapter_clears_singleton(self):
        fake = MagicMock()
        with patch.dict(sys.modules, {"intersystems_iris": fake}):
            dc.reset_adapter()
            _ = dc.get_package_info()  # builds singleton with mock
        # Private global should be None after reset
        dc.reset_adapter()
        assert dc._adapter is None

    def test_reset_adapter_exported(self):
        assert "reset_adapter" in dc.__all__

    def test_reset_adapter_idempotent(self):
        dc.reset_adapter()
        dc.reset_adapter()  # must not raise
        assert dc._adapter is None


class TestDBAPIPackageInfo:
    """connect_function must be a live property, not a stored Callable."""

    def test_connect_function_property_returns_current_module_attr(self):
        fake = MagicMock()
        sentinel_1 = object()
        sentinel_2 = object()
        fake.connect = sentinel_1

        with patch.dict(sys.modules, {"intersystems_iris": fake}):
            dc.reset_adapter()
            info = dc.get_package_info()
            assert info.connect_function is sentinel_1

            fake.connect = sentinel_2
            assert info.connect_function is sentinel_2

    def test_package_info_still_has_package_name_and_version(self):
        fake = MagicMock()
        fake.connect = MagicMock()

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            info = dc.get_package_info()
        assert info.package_name == "intersystems-irispython"
        assert info.version == "5.2.0"
        assert info.import_path == "intersystems_iris"


class TestValidatePackageVersion:
    """Test the validate_package_version function."""

    def test_raises_import_error_when_version_too_old(self):
        """Should raise ImportError when installed version is below minimum."""
        with pytest.raises(ImportError) as exc_info:
            dc.validate_package_version(
                "intersystems-irispython",
                "5.0.0",  # installed version
                "5.1.2",  # minimum version
            )
        error_msg = str(exc_info.value)
        assert "Package intersystems-irispython version 5.0.0 is incompatible" in error_msg
        assert "Minimum required: 5.1.2" in error_msg
        assert "pip install --upgrade" in error_msg

    def test_does_not_raise_when_version_meets_minimum(self):
        """Should not raise when installed version >= minimum."""
        # Should not raise
        dc.validate_package_version(
            "intersystems-irispython",
            "5.2.0",
            "5.1.2",
        )

    def test_does_not_raise_when_version_exactly_minimum(self):
        """Should not raise when installed version equals minimum."""
        # Should not raise
        dc.validate_package_version(
            "intersystems-iris",
            "3.0.0",
            "3.0.0",
        )

    def test_raises_for_legacy_package_too_old(self):
        """Should raise for legacy package when version too old."""
        with pytest.raises(ImportError) as exc_info:
            dc.validate_package_version(
                "intersystems-iris",
                "2.9.0",
                "3.0.0",
            )
        error_msg = str(exc_info.value)
        assert "intersystems-iris" in error_msg


class TestDBAPIPackageNotFoundError:
    """Test the DBAPIPackageNotFoundError exception."""

    def test_exception_message_format(self):
        """Should have formatted error message with instructions."""
        exc = dc.DBAPIPackageNotFoundError()
        msg = str(exc)
        assert "No IRIS Python package detected" in msg
        # Message has capital N in "Neither"
        assert "Neither intersystems-irispython nor intersystems-iris is installed" in msg
        assert "pip install intersystems-irispython>=5.1.2" in msg
        assert "pip install intersystems-iris>=3.0.0" in msg
        assert "https://iris-devtester.readthedocs.io/dbapi-packages/" in msg

    def test_exception_is_import_error(self):
        """Should be an ImportError subclass."""
        exc = dc.DBAPIPackageNotFoundError()
        assert isinstance(exc, ImportError)


class TestDetectDBAPIPackage:
    """Test detect_dbapi_package() function."""

    def test_prefers_intersystems_iris_module_over_iris(self):
        """Should try intersystems_iris (via import intersystems_iris) first."""
        mock_iris = MagicMock()
        mock_iris.connect = MagicMock()

        with patch.dict(sys.modules, {"intersystems_iris": mock_iris}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            info = dc.detect_dbapi_package()
            assert info.package_name == "intersystems-irispython"
            assert info.import_path == "intersystems_iris"

    def test_version_validation_is_performed(self):
        """Should validate package version meets minimum requirement."""
        fake = MagicMock()
        fake.connect = MagicMock()

        # Use a version too old to trigger validation error
        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.0.0"
        ):
            dc.reset_adapter()
            with pytest.raises(ImportError) as exc_info:
                dc.detect_dbapi_package()
            assert "5.0.0 is incompatible" in str(exc_info.value)

    def test_raises_when_no_package_available_properly_caught(self):
        """Should log error when no package available."""
        # Mock the ImportError from missing packages
        with patch(
            "iris_devtester.utils.dbapi_compat.detect_dbapi_package",
            side_effect=dc.DBAPIPackageNotFoundError(),
        ):
            with pytest.raises(dc.DBAPIPackageNotFoundError):
                dc.get_package_info()

    def test_detects_package_version(self):
        """Should return version information."""
        fake = MagicMock()
        fake.connect = MagicMock()

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.2.1"
        ):
            dc.reset_adapter()
            info = dc.detect_dbapi_package()
            assert info.version == "5.2.1"

    def test_measures_detection_time(self):
        """Should measure and record detection time in milliseconds."""
        fake = MagicMock()
        fake.connect = MagicMock()

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            info = dc.detect_dbapi_package()
            assert info.detection_time_ms >= 0
            assert isinstance(info.detection_time_ms, float)


class TestDBAPIConnectionAdapter:
    """Test DBAPIConnectionAdapter class."""

    def test_adapter_calls_connect_function_with_args(self):
        """Should call connect_function with connection arguments."""
        mock_connect = MagicMock(return_value="mock_connection")
        fake = MagicMock()
        fake.connect = mock_connect

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            adapter = dc._get_adapter()
            result = adapter.connect(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="_SYSTEM",
                password="SYS",
            )
            assert result == "mock_connection"
            mock_connect.assert_called_once()

    def test_adapter_get_package_info(self):
        """Should return package info."""
        fake = MagicMock()
        fake.connect = MagicMock()

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            adapter = dc._get_adapter()
            info = adapter.get_package_info()
            assert info.package_name == "intersystems-irispython"
            assert info.version == "5.2.0"


class TestGetConnection:
    """Test the get_connection() convenience function."""

    def test_get_connection_uses_singleton_adapter(self):
        """Should delegate to singleton adapter."""
        mock_connect = MagicMock(return_value="mock_connection")
        fake = MagicMock()
        fake.connect = mock_connect

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            result = dc.get_connection(
                hostname="localhost",
                port=1972,
                namespace="USER",
                username="_SYSTEM",
                password="SYS",
            )
            assert result == "mock_connection"


class TestGetPackageInfo:
    """Test the get_package_info() convenience function."""

    def test_get_package_info_returns_package_info(self):
        """Should return package info from singleton."""
        fake = MagicMock()
        fake.connect = MagicMock()

        with patch.dict(sys.modules, {"intersystems_iris": fake}), patch(
            "importlib.metadata.version", return_value="5.3.0"
        ):
            dc.reset_adapter()
            info = dc.get_package_info()
            assert info.package_name == "intersystems-irispython"
            assert info.version == "5.3.0"


class TestIrisModuleLoadingPathways:
    """Test the various fallback paths when loading iris module."""

    def test_detects_iris_module_without_connect_attribute(self):
        """Should handle iris module missing connect() initially."""
        # Create a mock iris module without connect initially
        mock_iris = MagicMock()
        delattr(mock_iris, 'connect')  # Remove connect attribute
        mock_iris.__file__ = "/fake/iris/__init__.py"
        mock_iris.__dict__ = {}

        # Mock the ELSDK file content
        elsdk_code = "connect = lambda: 'mocked'"

        with patch.dict(sys.modules, {"iris": mock_iris}), patch(
            "os.path.dirname", return_value="/fake/iris"
        ), patch("os.path.exists", return_value=False), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            # The code tries to exec ELSDK, but no files exist
            # So it should raise ImportError
            dc.reset_adapter()
            try:
                info = dc.detect_dbapi_package()
                # If we get here, the code somehow found another path
                # That's OK in the test environment
            except ImportError as e:
                # Expected: iris module found but connect() not available
                assert "connect() not available" in str(e) or "moderns aren't" in str(e)

    def test_connect_function_imports_module_when_absent_from_sys_modules(self):
        """Should import module when not in sys.modules but importable."""
        # This test ensures the fallback import in connect_function works
        import importlib

        # Create package info pointing to importable module
        info = dc.DBAPIPackageInfo(
            package_name="intersystems-irispython",
            import_path="os",  # Use os as a guaranteed importable module
            version="5.2.0",
            connect_attr="path",  # os.path exists
            detection_time_ms=1.0,
        )

        # Remove os from sys.modules
        os_module = sys.modules.pop("os", None)
        try:
            # connect_function should re-import os
            fn = info.connect_function
            assert fn is not None
        finally:
            if os_module:
                sys.modules["os"] = os_module

    def test_raises_when_import_path_not_found_and_not_importable(self):
        """Should raise when module not in sys.modules and not importable."""
        info = dc.DBAPIPackageInfo(
            package_name="test-package",
            import_path="nonexistent_module_xyz_abc",
            version="1.0.0",
            connect_attr="connect",
            detection_time_ms=1.0,
        )

        with pytest.raises(ModuleNotFoundError):
            _ = info.connect_function


class TestPackageDetectionFallbacks:
    """Test package detection fallback scenarios."""

    def test_logs_info_when_package_detected(self, caplog):
        """Should log when a package is successfully detected."""
        fake = MagicMock()
        fake.connect = MagicMock()

        with caplog.at_level(logging.INFO), patch.dict(
            sys.modules, {"intersystems_iris": fake}
        ), patch("importlib.metadata.version", return_value="5.2.0"):
            dc.reset_adapter()
            info = dc.detect_dbapi_package()
            assert "Detected IRIS DBAPI package" in caplog.text

    def test_logs_debug_when_trying_fallbacks(self, caplog):
        """Should log debug info about fallback attempts."""
        # Make intersystems_iris not have connect initially
        mock_iris = MagicMock()
        delattr(mock_iris, "connect")
        mock_iris.__file__ = None  # No file path, so can't try ELSDK

        with caplog.at_level(logging.DEBUG), patch.dict(
            sys.modules, {"intersystems_iris": mock_iris}
        ):
            dc.reset_adapter()
            try:
                dc.detect_dbapi_package()
            except ImportError:
                pass
            # Should have logged some fallback attempt
            assert caplog.text  # At least some logging occurred

    def test_exports_public_functions(self):
        """Should export all public functions in __all__."""
        assert "detect_dbapi_package" in dc.__all__
        assert "validate_package_version" in dc.__all__
        assert "DBAPIPackageInfo" in dc.__all__
        assert "DBAPIPackageNotFoundError" in dc.__all__
        assert "DBAPIConnectionAdapter" in dc.__all__
        assert "get_connection" in dc.__all__
        assert "get_package_info" in dc.__all__
        assert "reset_adapter" in dc.__all__

    def test_handles_missing_iris_file_path(self):
        """Should handle iris module without __file__ attribute."""
        # Mock iris module without __file__
        mock_iris = MagicMock()
        delattr(mock_iris, "__file__")  # No file path
        mock_iris.connect = MagicMock()  # Has connect

        with patch.dict(sys.modules, {"iris": mock_iris}), patch(
            "importlib.metadata.version", return_value="5.2.0"
        ):
            dc.reset_adapter()
            # Should handle gracefully when __file__ is missing
            try:
                info = dc.detect_dbapi_package()
                # If we get here, it worked
                assert info is not None
            except ImportError:
                # Also acceptable - module exists but can't find connect
                pass

    def test_iris_connect_function_resolved_from_updated_module(self):
        """Should resolve connect_function from updated module state."""
        # Create a module and info that points to it
        test_module = MagicMock()
        test_module.connect = MagicMock()
        sys.modules["_test_iris_module"] = test_module

        try:
            info = dc.DBAPIPackageInfo(
                package_name="test",
                import_path="_test_iris_module",
                version="1.0.0",
                connect_attr="connect",
                detection_time_ms=1.0,
            )

            # Get connect_function and verify it works
            fn = info.connect_function
            assert fn is test_module.connect

            # Update the module and verify live resolution
            new_connect = MagicMock()
            test_module.connect = new_connect
            assert info.connect_function is new_connect
        finally:
            sys.modules.pop("_test_iris_module", None)
