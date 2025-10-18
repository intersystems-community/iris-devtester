"""
Example 4: pytest Integration - Using IRIS in tests.

This example shows how to use iris-devtools with pytest for
integration testing with proper isolation.

Constitutional Principles:
- #3: Isolation by Default
- #4: Zero Configuration Viable
- #7: Medical-Grade Reliability
"""

import pytest
from iris_devtools.containers import IRISContainer


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
    conn = iris_container.get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SET NAMESPACE {test_namespace}")
    cursor.close()
    yield conn


# Test examples using the fixtures
class TestMyFeature:
    """Example test class using IRIS fixtures."""

    def test_database_connection(self, iris_connection):
        """Test basic database connectivity."""
        cursor = iris_connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()

        assert result[0] == 1

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
        cursor.close()

        assert count == 1
        print(f"✓ Test passed in namespace: {test_namespace}")

    def test_isolation_from_other_tests(self, iris_connection):
        """Test that previous test's data is gone (isolation)."""
        cursor = iris_connection.cursor()

        # This should fail because we're in a NEW namespace
        with pytest.raises(Exception):
            cursor.execute("SELECT COUNT(*) FROM TestData")

        cursor.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
