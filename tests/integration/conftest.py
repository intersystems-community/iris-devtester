"""
pytest configuration and fixtures for iris-devtester integration tests.

Provides IRIS database connections and containers for integration testing.
"""

import logging
import os
import time

import pytest

from iris_devtester.containers import IRISContainer

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def clean_port_registry():
    """Ensure a clean port registry for each integration test."""
    from iris_devtester.ports.registry import PortRegistry

    registry = PortRegistry()
    registry.clear_all()
    yield
    registry.clear_all()


@pytest.fixture(scope="session")
def iris_container():
    """
    Provide IRIS container for all integration tests.

    This is session-scoped so we only start one container for all tests.
    """
    try:
        # Start fresh community container
        with IRISContainer.community() as container:
            # Wait for IRIS to be ready
            container.wait_for_ready(timeout=60)

            # Enable CallIn service for DBAPI connections (required)
            container.enable_callin_service()

            # Create a dedicated 'testuser' with %ALL role and known password
            # This ensures we have a predictable, high-privilege account for benchmarks.
            # We use a robust script that handles existing users and errors.
            create_user_script = """
 Set user="testuser",pass="testpassword"
 If ##class(Security.Users).Exists(user) Do ##class(Security.Users).Delete(user)
 Set p("PasswordExternal")=pass,p("Roles")="%ALL",p("ChangePassword")=0,p("PasswordNeverExpires")=1
 Set sc=##class(Security.Users).Create(user,.p)
 If $$$ISERR(sc) Write "ERR:",$System.Status.GetErrorText(sc) Halt
 Write "SUCCESS" Halt
 """
            container.execute_objectscript(create_user_script, namespace="%SYS")

            # Update the container object's credentials so get_config() returns them
            container._username = "testuser"
            container._password = "testpassword"

            # Verify the user actually works immediately
            from iris_devtester.config import IRISConfig
            from iris_devtester.connections import get_connection

            test_config = IRISConfig(
                host=container.get_container_host_ip(),
                port=int(container.get_exposed_port(1972)),
                username="testuser",
                password="testpassword",
                container_name=container.get_container_name(),
            )

            # This will raise if it fails, which is what we want (Fail Fast)
            conn = get_connection(test_config)
            conn.close()

            yield container

    except Exception as e:
        pytest.skip(f"IRIS container not available: {e}")


@pytest.fixture(scope="function")
def test_namespace(iris_container):
    """
    Provide unique test namespace for each test.
    """
    namespace = iris_container.get_test_namespace()
    yield namespace
    # Cleanup
    try:
        iris_container.delete_namespace(namespace)
    except:
        pass


@pytest.fixture(scope="function")
def iris_connection(iris_container, test_namespace):
    """
    Provide DBAPI connection to test namespace.
    """
    from iris_devtester.config import IRISConfig
    from iris_devtester.connections import get_connection

    # CRITICAL: Always use our verified testuser
    test_config = IRISConfig(
        host=iris_container.get_container_host_ip(),
        port=int(iris_container.get_exposed_port(1972)),
        namespace=test_namespace,
        username="testuser",
        password="testpassword",
        container_name=iris_container.get_container_name(),
    )

    # Use modern connection manager with automatic remediation
    from iris_devtester.connections.connection import get_connection as get_modern_connection

    conn = get_modern_connection(test_config)
    yield conn

    try:
        conn.close()
    except:
        pass


@pytest.fixture(scope="function")
def iris_objectscript_connection(iris_container, test_namespace):
    """
    Provide iris.connect() connection for ObjectScript operations.
    """
    import iris

    conn = iris.connect(
        hostname=iris_container.get_container_host_ip(),
        port=int(iris_container.get_exposed_port(1972)),
        namespace=test_namespace,
        username="testuser",
        password="testpassword",
    )

    yield conn
    conn.close()
