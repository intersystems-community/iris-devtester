"""
pytest configuration and fixtures for iris-devtools tests.

Provides IRIS database connections and containers for integration testing.
"""

import pytest
from testcontainers.iris import IRISContainer


@pytest.fixture(scope="function")
def iris_db():
    """
    Function-scoped IRIS database connection.

    Provides a fresh IRIS container and connection for each test.
    Container is automatically cleaned up after test completes.

    Constitutional Principle #3: Isolation by Default - Each test gets its own database.

    NOTE: This connection includes an `execute_objectscript()` method for running
    ObjectScript code. This is a TEST-ONLY workaround until Feature 003 implements
    proper ObjectScript execution via JDBC.

    Yields:
        Database connection object with execute_objectscript() method

    Example:
        def test_monitoring(iris_db):
            from iris_devtester.containers.monitoring import configure_monitoring
            success, msg = configure_monitoring(iris_db)
            assert success is True
    """
    # Start IRIS container
    with IRISContainer() as iris:
        # Enable CallIn service (required for DBAPI connections)
        from iris_devtester.utils.enable_callin import enable_callin_service
        container_name = iris.get_wrapped_container().name
        success, msg = enable_callin_service(container_name, timeout=30)
        if not success:
            raise RuntimeError(f"Failed to enable CallIn service: {msg}")

        # Get connection URL and create DBAPI connection using compatibility layer
        from iris_devtester.utils.dbapi_compat import get_connection

        # Parse connection details from container
        host = iris.get_container_host_ip()
        port = int(iris.get_exposed_port(1972))

        # Use the test user created by testcontainers-iris
        # (username="test", password="test", no expiration!)
        conn = get_connection(
            hostname=host,
            port=port,
            namespace="USER",
            username="test",
            password="test",
        )

        # Add ObjectScript execution capability (TEST-ONLY workaround)
        # TODO: Remove this when Feature 003 implements proper ObjectScript execution
        def execute_objectscript(code):
            """Execute ObjectScript code via container exec (TEST-ONLY)."""
            result = iris.exec(
                ["iris", "session", "IRIS", "-U", "USER", code]
            )
            return result.output.decode() if result.output else ""

        # Attach method to connection
        conn.execute_objectscript = execute_objectscript
        conn._container = iris  # Keep reference for cleanup

        try:
            yield conn
        finally:
            # Cleanup
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


@pytest.fixture(scope="module")
def iris_db_shared():
    """
    Module-scoped shared IRIS database connection.

    Provides a single IRIS container shared across all tests in a module.
    Faster than function-scoped but tests must be designed for shared state.

    Use when:
    - Tests don't modify database state
    - Tests are read-only
    - Speed is critical

    NOTE: This connection includes an `execute_objectscript()` method for running
    ObjectScript code. This is a TEST-ONLY workaround until Feature 003 implements
    proper ObjectScript execution via JDBC.

    Yields:
        Database connection object with execute_objectscript() method

    Example:
        def test_read_metrics(iris_db_shared):
            from iris_devtester.containers.performance import get_resource_metrics
            metrics = get_resource_metrics(iris_db_shared)
            assert metrics.cpu_percent >= 0
    """
    # Start IRIS container (shared for module)
    with IRISContainer() as iris:
        # Use Feature 003 modern connection manager
        from iris_devtester.connections import get_connection
        from iris_devtester.config import IRISConfig

        # Parse connection details from container
        host = iris.get_container_host_ip()
        port = int(iris.get_exposed_port(1972))

        # Use the test user created by testcontainers-iris
        # (username="test", password="test", no expiration!)
        config = IRISConfig(
            host=host,
            port=port,
            namespace="USER",
            username="test",
            password="test",
        )

        conn = get_connection(config, auto_retry=True, max_retries=3)

        # Add ObjectScript execution capability (TEST-ONLY workaround)
        # TODO: Remove this when Feature 003 implements proper ObjectScript execution
        def execute_objectscript(code):
            """Execute ObjectScript code via container exec (TEST-ONLY)."""
            result = iris.exec(
                ["iris", "session", "IRIS", "-U", "USER", code]
            )
            return result.output.decode() if result.output else ""

        # Attach method to connection
        conn.execute_objectscript = execute_objectscript
        conn._container = iris  # Keep reference for cleanup

        try:
            yield conn
        finally:
            # Cleanup
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


@pytest.fixture(scope="function")
def iris_container():
    """
    Function-scoped raw IRIS container access.

    Provides direct access to IRISContainer for advanced test scenarios.
    Use when you need container control beyond just the connection.

    Yields:
        IRISContainer instance

    Example:
        def test_container_lifecycle(iris_container):
            # Container is already started
            conn = iris_container.get_connection()

            # Can access container methods
            logs = iris_container.get_logs()
            assert "IRIS started" in logs
    """
    with IRISContainer() as iris:
        # Enable CallIn service (required for DBAPI connections)
        from iris_devtester.utils.enable_callin import enable_callin_service
        container_name = iris.get_wrapped_container().name
        success, msg = enable_callin_service(container_name, timeout=30)
        if not success:
            raise RuntimeError(f"Failed to enable CallIn service: {msg}")

        yield iris


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
