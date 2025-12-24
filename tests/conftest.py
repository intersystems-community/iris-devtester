"""
pytest configuration and fixtures for iris-devtools tests.

Provides IRIS database connections and containers for integration testing.
"""

import logging
import os
import pytest
from iris_devtester.containers import IRISContainer

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def iris_db(request):
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
    import time
    import uuid
    import sys

    # Force unique container name per test to prevent reuse
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    container_id = str(uuid.uuid4())[:8]

    # Start IRIS container with unique name
    iris_container = IRISContainer()
    iris_container._name = f"iris_test_{test_name}_{container_id}"

    with iris_container as iris:
        # Enable CallIn service (required for DBAPI connections)
        from iris_devtester.utils.enable_callin import enable_callin_service
        import time
        import sys

        container_name = iris.get_wrapped_container().name

        success, msg = enable_callin_service(container_name, timeout=30)
        if not success:
            raise RuntimeError(f"Failed to enable CallIn service: {msg}")

        # Wait for test user creation to complete and CallIn to be fully ready
        time.sleep(2)

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
            # Cleanup connection first
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


@pytest.fixture(scope="function", params=["community", "enterprise"])
def iris_db_both_editions(request):
    """
    Parametrized fixture that tests both Community and Enterprise editions.

    Ensures Constitutional Principle #6 compliance: "Enterprise Ready, Community Friendly"

    Yields:
        Database connection for either Community or Enterprise edition

    Example:
        def test_password_reset_both_editions(iris_db_both_editions):
            # This test will run twice: once with Community, once with Enterprise
            conn = iris_db_both_editions
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
    """
    import time
    import uuid

    edition = request.param

    # Force unique container name per test to prevent reuse
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    container_id = str(uuid.uuid4())[:8]

    if edition == "community":
        # Community Edition
        iris_container = IRISContainer()
        iris_container._name = f"iris_test_community_{test_name}_{container_id}"
    else:
        # Enterprise Edition (requires license key)
        # Try to load from environment variable first, then from iris.key file
        license_key = os.environ.get("IRIS_LICENSE_KEY")

        if not license_key:
            # Try to load from iris.key file in project root
            import pathlib
            key_file = pathlib.Path(__file__).parent.parent / "iris.key"
            if key_file.exists():
                license_key = key_file.read_text().strip()
                logger.info(f"Loaded IRIS license key from {key_file}")

        if not license_key:
            pytest.skip("IRIS_LICENSE_KEY not set and iris.key not found - skipping Enterprise edition test")

        iris_container = IRISContainer.enterprise(license_key=license_key)
        iris_container._name = f"iris_test_enterprise_{test_name}_{container_id}"

    with iris_container as iris:
        # Enable CallIn service (required for DBAPI connections)
        from iris_devtester.utils.enable_callin import enable_callin_service

        container_name = iris.get_wrapped_container().name

        success, msg = enable_callin_service(container_name, timeout=30)
        if not success:
            raise RuntimeError(f"Failed to enable CallIn service: {msg}")

        # Wait for IRIS to settle (longer for Enterprise on macOS)
        import platform as platform_module
        if edition == "enterprise" and platform_module.system() == "Darwin":
            logger.info("Enterprise on macOS: waiting 12s for IRIS to fully settle...")
            time.sleep(12)  # macOS Docker Desktop networking delay
        else:
            time.sleep(2)  # Community or Linux

        # Get connection URL and create DBAPI connection using compatibility layer
        from iris_devtester.utils.dbapi_compat import get_connection

        # Parse connection details from container
        host = iris.get_container_host_ip()
        port = int(iris.get_exposed_port(1972))

        # Use appropriate credentials based on edition
        if edition == "community":
            # Community: Use test user created by testcontainers-iris
            username, password = "test", "test"
        else:
            # Enterprise: Use SuperUser (default Enterprise credentials)
            # Note: testcontainers-iris tries to create this user (harmless if exists)
            username, password = "SuperUser", "SYS"

        # CRITICAL: Harden password BEFORE any connection attempt
        # testcontainers-iris creates users with "password change required" state
        # which causes "Access Denied" errors on first connection
        from iris_devtester.utils.password_reset import reset_password

        # WORKAROUND FOR BUG #015: Enterprise edition password reset via docker exec
        # requires longer settle time on macOS (empirically determined: 15s minimum)
        if edition == "enterprise" and platform_module.system() == "Darwin":
            extra_wait = 3.0  # Additional wait beyond the 12s already done
            logger.info(f"[{edition.upper()}] Enterprise/macOS: waiting extra {extra_wait}s before password reset...")
            time.sleep(extra_wait)

        logger.info(f"[{edition.upper()}] Hardening {username} account...")
        success, msg = reset_password(
            container_name=container_name,
            username=username,
            new_password=password,
            hostname=host,
            port=port
        )

        if not success:
            logger.error(f"[{edition.upper()}] Password hardening FAILED: {msg}")
            raise RuntimeError(f"Password hardening failed for {username}: {msg}")

        logger.info(f"[{edition.upper()}] Password hardening complete: {msg}")

        # NOW get connection using hardened credentials
        conn = get_connection(
            hostname=host,
            port=port,
            namespace="USER",
            username=username,
            password=password,
        )

        # Add ObjectScript execution capability (TEST-ONLY workaround)
        def execute_objectscript(code):
            """Execute ObjectScript code via container exec (TEST-ONLY)."""
            result = iris.exec(
                ["iris", "session", "IRIS", "-U", "USER", code]
            )
            return result.output.decode() if result.output else ""

        # Attach method and metadata to connection
        conn.execute_objectscript = execute_objectscript
        conn._container = iris
        conn._edition = edition  # Track which edition we're testing

        try:
            yield conn
        finally:
            # Cleanup connection first
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
