"""
Pytest configuration for integration tests.

Provides fixtures for IRIS container and connections.
"""

import pytest
from iris_devtester.containers import IRISContainer


@pytest.fixture(scope="session")
def iris_container():
    """
    Provide IRIS container for all integration tests.

    This is session-scoped so we only start one container for all tests.
    Individual tests should use unique namespaces for isolation.
    """
    try:
        with IRISContainer.community() as container:
            # Wait for IRIS to be ready
            container.wait_for_ready(timeout=60)

            # Enable CallIn service for DBAPI connections (required)
            container.enable_callin_service()

            # Unexpire passwords to prevent "password change required" errors
            from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords
            container_name = container.get_container_name()
            unexpire_all_passwords(container_name)

            yield container

    except Exception as e:
        pytest.skip(f"IRIS container not available: {e}")


@pytest.fixture(scope="function")
def test_namespace(iris_container):
    """
    Provide unique test namespace for each test.

    Creates a unique namespace, yields it for testing, then cleans up.
    Use this for test isolation.

    Example:
        >>> def test_my_feature(test_namespace):
        ...     # test_namespace is "TEST_A1B2C3D4"
        ...     # Use it for your test
    """
    # Ensure CallIn service is enabled (idempotent)
    iris_container.enable_callin_service()

    namespace = iris_container.get_test_namespace()
    yield namespace
    # Cleanup
    iris_container.delete_namespace(namespace)


@pytest.fixture(scope="function")
def iris_connection(iris_container, test_namespace):
    """
    Provide DBAPI connection to test namespace.

    Use this for SQL operations (SELECT, INSERT, UPDATE, DELETE).
    For ObjectScript operations, use iris_container.get_iris_connection().

    Example:
        >>> def test_sql_operations(iris_connection):
        ...     cursor = iris_connection.cursor()
        ...     cursor.execute("CREATE TABLE TestData (ID INT, Name VARCHAR(100))")
        ...     cursor.execute("INSERT INTO TestData VALUES (1, 'Alice')")
    """
    # Get DBAPI connection to the test namespace
    # Note: Create a fresh connection for each test to avoid stale connections
    import dataclasses
    from iris_devtester.connections import get_connection

    config = iris_container.get_config()
    test_config = dataclasses.replace(config, namespace=test_namespace)
    conn = get_connection(test_config)

    yield conn

    # Cleanup: Close connection after test
    try:
        conn.close()
    except:
        pass  # Ignore errors if connection already closed


@pytest.fixture(scope="function")
def iris_objectscript_connection(iris_container, test_namespace):
    """
    Provide iris.connect() connection for ObjectScript operations.

    Use this for ObjectScript operations (globals, class methods, etc.).
    For SQL operations, use iris_connection instead (3x faster).

    Example:
        >>> def test_objectscript_operations(iris_objectscript_connection):
        ...     import iris
        ...     iris_obj = iris.createIRIS(iris_objectscript_connection)
        ...     iris_obj.set("^MyGlobal", "test value")
        ...     value = iris_obj.get("^MyGlobal")
    """
    import iris

    config = iris_container.get_config()

    conn = iris.connect(
        hostname=config.host,
        port=config.port,
        namespace=test_namespace,  # Connect to test namespace
        username=config.username,
        password=config.password,
    )

    yield conn

    conn.close()
