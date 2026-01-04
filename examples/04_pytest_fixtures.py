"""
Example 4: pytest Integration - Using IRIS in tests.

This example shows how to use iris-devtester with pytest for
integration testing with proper isolation.

Constitutional Principles:
- #3: Isolation by Default
- #4: Zero Configuration Viable
- #7: Medical-Grade Reliability
"""

import pytest
from iris_devtester.containers import IRISContainer


# conftest.py pattern
@pytest.fixture(scope="session")
def iris_container():
    """
    Provide IRIS container for all tests.

    Session-scoped for performance - one container for entire test session.
    """
    with IRISContainer.community() as container:
        container.wait_for_ready(timeout=60)
        yield container


@pytest.fixture(scope="function")
def test_namespace(iris_container):
    """
    Provide unique namespace for each test.

    Function-scoped for isolation - each test gets fresh namespace.
    Automatic cleanup ensures no test data pollution.
    """
    namespace = iris_container.get_test_namespace()
    yield namespace
    # Cleanup happens automatically
    iris_container.delete_namespace(namespace)


@pytest.fixture(scope="function")
def iris_connection(iris_container, test_namespace):
    """
    Provide DBAPI connection to test namespace.

    Use for SQL operations (3x faster than JDBC).
    """
    # Update config to use test namespace before getting connection
    original_namespace = iris_container._config.namespace
    iris_container._config.namespace = test_namespace

    conn = iris_container.get_connection()

    # Restore original namespace config
    iris_container._config.namespace = original_namespace

    yield conn


# Test examples using the fixtures
class TestMyFeature:
    """Example test class using IRIS fixtures."""

    def test_database_connection(self, iris_connection):
        """Test basic database connectivity."""
        cursor = iris_connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        # Expected output: result = (1,)
        cursor.close()

        assert result[0] == 1
        # ✅ Success: Basic connectivity verified

    def test_table_creation(self, iris_connection, test_namespace):
        """Test table creation in isolated namespace."""
        cursor = iris_connection.cursor()

        # Create table
        cursor.execute("""
            CREATE TABLE TestData (
                ID INT PRIMARY KEY,
                Name VARCHAR(100)
            )
        """)

        # Insert data
        cursor.execute("INSERT INTO TestData (ID, Name) VALUES (1, 'Test')")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM TestData")
        count = cursor.fetchone()[0]
        # Expected output: count = 1
        cursor.close()

        assert count == 1
        print(f"✓ Test passed in namespace: {test_namespace}")
        # Expected output: ✓ Test passed in namespace: TESTNS_1234567890

    def test_isolation_from_other_tests(self, iris_connection):
        """Test that previous test's data is gone (isolation)."""
        cursor = iris_connection.cursor()

        # This should fail because we're in a NEW namespace
        with pytest.raises(Exception):
            cursor.execute("SELECT COUNT(*) FROM TestData")
            # Expected output: Exception raised (table doesn't exist in new namespace)
            # ✅ Success: Demonstrates test isolation - each test has clean state

        cursor.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
    # Expected output:
    # ============================= test session starts ==============================
    # collected 3 items
    #
    # 04_pytest_fixtures.py::TestMyFeature::test_database_connection PASSED   [ 33%]
    # 04_pytest_fixtures.py::TestMyFeature::test_table_creation PASSED        [ 66%]
    # ✓ Test passed in namespace: TESTNS_1234567890
    # 04_pytest_fixtures.py::TestMyFeature::test_isolation_from_other_tests PASSED [100%]
    #
    # ============================== 3 passed in 5.23s ===============================
    # ✅ Success: All tests passed with proper isolation
