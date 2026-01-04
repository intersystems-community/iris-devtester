"""
pytest configuration and fixtures for iris-devtester tests.

Provides IRIS database connections and containers for integration testing.
"""

import logging
import os
import pytest
from iris_devtester.containers import IRISContainer

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def iris_db(request):
    import uuid
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    container_id = str(uuid.uuid4())[:8]
    name = f"iris_test_{test_name}_{container_id}"

    with IRISContainer.community(
        username="test",
        password="test"
    ) as iris:
        iris._name = name
        conn = iris.get_connection()

        def execute_objectscript(code):
            result = iris.exec(
                ["iris", "session", "IRIS", "-U", "USER", code]
            )
            return result.output.decode() if result.output else ""

        conn.execute_objectscript = execute_objectscript
        conn._container = iris

        try:
            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # Container cleanup handled by IRISContainer context manager

    # CRITICAL: Wait for container to be fully removed before next test
    # This prevents test isolation issues where test 2 connects to test 1's container
    import docker
    try:
        client = docker.from_env()
        # Wait up to 10 seconds for container to be fully removed
        for _ in range(10):
            try:
                client.containers.get(iris.get_wrapped_container().id)
                time.sleep(1)  # Container still exists, wait
            except docker.errors.NotFound:
                break  # Container removed, we're done
    except Exception:
        pass  # Ignore docker errors during cleanup verification


@pytest.fixture(scope="module")
def iris_db_shared():
    with IRISContainer.community(
        username="test",
        password="test"
    ) as iris:
        conn = iris.get_connection()

        def execute_objectscript(code):
            result = iris.exec(
                ["iris", "session", "IRIS", "-U", "USER", code]
            )
            return result.output.decode() if result.output else ""

        conn.execute_objectscript = execute_objectscript
        conn._container = iris

        try:
            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


@pytest.fixture(scope="function")
def iris_container():
    with IRISContainer.community() as iris:
        yield iris


@pytest.fixture(scope="function", params=["community", "enterprise"])
def iris_db_both_editions(request):
    import uuid
    import os
    edition = request.param
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    container_id = str(uuid.uuid4())[:8]
    name = f"iris_test_{edition}_{test_name}_{container_id}"

    if edition == "community":
        iris_container = IRISContainer.community(username="test", password="test")
    else:
        license_key = os.environ.get("IRIS_LICENSE_KEY")
        if not license_key:
            import pathlib
            key_file = pathlib.Path(__file__).parent.parent / "iris.key"
            if key_file.exists():
                license_key = key_file.read_text().strip()
        if not license_key:
            pytest.skip("IRIS_LICENSE_KEY not set")
        iris_container = IRISContainer.enterprise(license_key=license_key, username="SuperUser", password="SYS")

    iris_container._name = name
    with iris_container as iris:
        conn = iris.get_connection()

        def execute_objectscript(code):
            result = iris.exec(
                ["iris", "session", "IRIS", "-U", "USER", code]
            )
            return result.output.decode() if result.output else ""

        conn.execute_objectscript = execute_objectscript
        conn._container = iris
        conn._edition = edition

        try:
            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    # Container cleanup handled by IRISContainer context manager

    # CRITICAL: Wait for container to be fully removed before next test
    import docker
    try:
        client = docker.from_env()
        # Wait up to 10 seconds for container to be fully removed
        for _ in range(10):
            try:
                client.containers.get(iris.get_wrapped_container().id)
                time.sleep(1)  # Container still exists, wait
            except docker.errors.NotFound:
                break  # Container removed, we're done
    except Exception:
        pass  # Ignore docker errors during cleanup verification


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires IRIS container)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (>5 seconds)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "enterprise: mark test as requiring Enterprise edition (needs IRIS_LICENSE_KEY)"
    )
