"""pytest plugin for IRIS .DAT fixture integration.

This module provides pytest hooks and decorators for declarative fixture
management with @pytest.mark.dat_fixture.

Usage:
    @pytest.mark.dat_fixture("./fixtures/test-data")
    def test_with_fixture(iris_connection):
        # Fixture is automatically loaded before test
        # Automatically cleaned up after test
        cursor = iris_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        assert cursor.fetchone()[0] > 0

Configuration in conftest.py:
    pytest_plugins = ["iris_devtools.fixtures.pytest_plugin"]

Or in pytest.ini:
    [pytest]
    plugins = iris_devtools.fixtures.pytest_plugin
"""

import pytest
import os
from pathlib import Path
from typing import Optional, Dict, Any

from .loader import DATFixtureLoader
from .manifest import FixtureLoadError


# Global registry to track loaded fixtures per test
_loaded_fixtures: Dict[str, Any] = {}


def pytest_configure(config):
    """Register custom markers for pytest."""
    config.addinivalue_line(
        "markers",
        "dat_fixture(path): Load IRIS .DAT fixture before test, cleanup after test"
    )


def pytest_runtest_setup(item):
    """Hook called before each test - load fixtures if marked."""
    # Check if test has dat_fixture marker
    marker = item.get_closest_marker("dat_fixture")

    if marker:
        # Get fixture path from marker
        if not marker.args:
            pytest.fail("@pytest.mark.dat_fixture requires a fixture path argument")

        fixture_path = marker.args[0]

        # Get optional parameters
        namespace = marker.kwargs.get("namespace", None)
        validate_checksum = marker.kwargs.get("validate_checksum", True)

        # Generate unique namespace for this test (for parallel execution)
        test_id = item.nodeid.replace("::", "_").replace("/", "_")
        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
        unique_namespace = namespace or f"PYTEST_{worker_id}_{test_id}"[:64]  # IRIS namespace limit

        try:
            # Load fixture
            loader = DATFixtureLoader()
            result = loader.load_fixture(
                fixture_path=fixture_path,
                target_namespace=unique_namespace,
                validate_checksum=validate_checksum
            )

            # Store result for cleanup
            _loaded_fixtures[item.nodeid] = {
                'loader': loader,
                'namespace': result.namespace,
                'result': result
            }

            # Store namespace in item for test access
            item.dat_fixture_namespace = result.namespace
            item.dat_fixture_result = result

        except Exception as e:
            pytest.fail(f"Failed to load DAT fixture '{fixture_path}': {e}")


def pytest_runtest_teardown(item, nextitem):
    """Hook called after each test - cleanup fixtures if loaded."""
    if item.nodeid in _loaded_fixtures:
        fixture_info = _loaded_fixtures[item.nodeid]

        try:
            # Cleanup loaded fixture
            loader = fixture_info['loader']
            namespace = fixture_info['namespace']

            # Delete namespace entirely (cleanup test data)
            loader.cleanup_fixture(namespace, delete_namespace=True)

        except Exception as e:
            # Log warning but don't fail the test
            import warnings
            warnings.warn(f"Failed to cleanup DAT fixture namespace '{namespace}': {e}")

        finally:
            # Remove from registry
            del _loaded_fixtures[item.nodeid]


@pytest.fixture
def dat_fixture_namespace(request):
    """Pytest fixture to access the loaded DAT fixture's namespace.

    Usage:
        @pytest.mark.dat_fixture("./fixtures/test-data")
        def test_something(dat_fixture_namespace):
            assert dat_fixture_namespace == "PYTEST_..."
    """
    if hasattr(request.node, 'dat_fixture_namespace'):
        return request.node.dat_fixture_namespace
    else:
        pytest.fail("Test must be marked with @pytest.mark.dat_fixture to use dat_fixture_namespace")


@pytest.fixture
def dat_fixture_result(request):
    """Pytest fixture to access the LoadResult from DAT fixture loading.

    Usage:
        @pytest.mark.dat_fixture("./fixtures/test-data")
        def test_something(dat_fixture_result):
            assert dat_fixture_result.success
            assert len(dat_fixture_result.tables_loaded) > 0
    """
    if hasattr(request.node, 'dat_fixture_result'):
        return request.node.dat_fixture_result
    else:
        pytest.fail("Test must be marked with @pytest.mark.dat_fixture to use dat_fixture_result")


@pytest.fixture
def dat_fixture_connection(request):
    """Pytest fixture to get IRIS connection for the loaded DAT fixture.

    Returns a connection configured for the fixture's namespace.

    Usage:
        @pytest.mark.dat_fixture("./fixtures/test-data")
        def test_with_connection(dat_fixture_connection):
            cursor = dat_fixture_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
            count = cursor.fetchone()[0]
            assert count > 0
    """
    if not hasattr(request.node, 'dat_fixture_namespace'):
        pytest.fail("Test must be marked with @pytest.mark.dat_fixture to use dat_fixture_connection")

    if request.node.nodeid not in _loaded_fixtures:
        pytest.fail("DAT fixture not loaded")

    loader = _loaded_fixtures[request.node.nodeid]['loader']
    return loader.get_connection()


# Auto-register plugin if imported
def pytest_configure_custom(config):
    """Custom configuration for plugin."""
    # Check if iris_devtools.fixtures is available
    try:
        from iris_devtools.fixtures import DATFixtureLoader
    except ImportError:
        import warnings
        warnings.warn(
            "iris_devtools.fixtures not available - DAT fixture plugin disabled"
        )
