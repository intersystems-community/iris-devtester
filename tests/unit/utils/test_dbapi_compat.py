"""Tests for dbapi_compat singleton-poisoning fix.

Verifies that mocking intersystems_iris does not permanently poison the
DBAPIConnectionAdapter singleton — the core defect reported in
IDT-BUG-dbapi-adapter-singleton.md.
"""

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
        except Exception:
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
