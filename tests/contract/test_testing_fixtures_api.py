"""
Contract tests for Testing Fixtures API.

These tests validate the public API interface defined in:
specs/001-implement-iris-devtester/contracts/testing-fixtures-api.md

These tests MUST FAIL until implementation is complete.
"""


import pytest

pytestmark = pytest.mark.contract


class TestIrisDbFixture:
    """Contract tests for iris_db fixture."""

    def test_fixture_exists(self):
        """Test that iris_db fixture can be imported."""
        from iris_devtester.testing import fixtures

        assert hasattr(fixtures, 'iris_db')

    def test_fixture_is_callable(self):
        """Test that iris_db is a fixture function."""
        from iris_devtester.testing.fixtures import iris_db

        # Check for pytest fixture marker
        assert hasattr(iris_db, '_pytestfixturefunction')

    def test_fixture_scope(self):
        """Test that iris_db has function scope."""
        from iris_devtester.testing.fixtures import iris_db

        # Function scope means each test gets new instance
        fixture_info = iris_db._pytestfixturefunction
        assert fixture_info.scope == 'function'


class TestIrisDbSharedFixture:
    """Contract tests for iris_db_shared fixture."""

    def test_fixture_exists(self):
        """Test that iris_db_shared fixture can be imported."""
        from iris_devtester.testing import fixtures

        assert hasattr(fixtures, 'iris_db_shared')

    def test_fixture_is_callable(self):
        """Test that iris_db_shared is a fixture function."""
        from iris_devtester.testing.fixtures import iris_db_shared

        assert hasattr(iris_db_shared, '_pytestfixturefunction')

    def test_fixture_scope(self):
        """Test that iris_db_shared has module scope."""
        from iris_devtester.testing.fixtures import iris_db_shared

        fixture_info = iris_db_shared._pytestfixturefunction
        assert fixture_info.scope == 'module'


class TestIrisContainerFixture:
    """Contract tests for iris_container fixture."""

    def test_fixture_exists(self):
        """Test that iris_container fixture can be imported."""
        from iris_devtester.testing import fixtures

        assert hasattr(fixtures, 'iris_container')

    def test_fixture_is_callable(self):
        """Test that iris_container is a fixture function."""
        from iris_devtester.testing.fixtures import iris_container

        assert hasattr(iris_container, '_pytestfixturefunction')

    def test_fixture_scope(self):
        """Test that iris_container has function scope."""
        from iris_devtester.testing.fixtures import iris_container

        fixture_info = iris_container._pytestfixturefunction
        assert fixture_info.scope == 'function'


class TestValidateSchema:
    """Contract tests for validate_schema() function."""

    def test_function_exists(self):
        """Test that validate_schema function can be imported."""
        from iris_devtester.testing import validate_schema

        assert callable(validate_schema)

    def test_signature(self):
        """Test that validate_schema accepts required parameters."""
        from iris_devtester.testing import validate_schema
        from iris_devtester.testing.models import SchemaDefinition
        from unittest.mock import Mock

        mock_conn = Mock()
        schema = SchemaDefinition()
        result = validate_schema(mock_conn, schema)
        assert hasattr(result, 'is_valid')

    def test_returns_schema_validation_result(self):
        """Test that validate_schema returns SchemaValidationResult."""
        from iris_devtester.testing import validate_schema
        from iris_devtester.testing.models import SchemaDefinition, SchemaValidationResult
        from unittest.mock import Mock

        mock_conn = Mock()
        schema = SchemaDefinition()
        result = validate_schema(mock_conn, schema)
        assert isinstance(result, SchemaValidationResult)


class TestResetSchema:
    """Contract tests for reset_schema() function."""

    def test_function_exists(self):
        """Test that reset_schema function can be imported."""
        from iris_devtester.testing import reset_schema

        assert callable(reset_schema)

    def test_signature(self):
        """Test that reset_schema accepts required parameters."""
        from iris_devtester.testing import reset_schema
        from iris_devtester.testing.models import SchemaDefinition
        from unittest.mock import Mock

        mock_conn = Mock()
        schema = SchemaDefinition()
        # Should not raise
        reset_schema(mock_conn, schema)


class TestRegisterCleanup:
    """Contract tests for register_cleanup() function."""

    def test_function_exists(self):
        """Test that register_cleanup function can be imported."""
        from iris_devtester.testing import register_cleanup

        assert callable(register_cleanup)

    def test_signature(self):
        """Test that register_cleanup accepts cleanup action."""
        from iris_devtester.testing import register_cleanup
        from iris_devtester.testing.models import CleanupAction

        action = CleanupAction(action_type="drop_table", target="test_table")
        # Should not raise
        register_cleanup(action)


class TestSchemaDefinitionModel:
    """Contract tests for SchemaDefinition and related models."""

    def test_schema_definition_exists(self):
        """Test that SchemaDefinition can be imported."""
        from iris_devtester.testing.models import SchemaDefinition

        assert SchemaDefinition is not None

    def test_table_definition_exists(self):
        """Test that TableDefinition can be imported."""
        from iris_devtester.testing.models import TableDefinition

        assert TableDefinition is not None

    def test_column_definition_exists(self):
        """Test that ColumnDefinition can be imported."""
        from iris_devtester.testing.models import ColumnDefinition

        assert ColumnDefinition is not None

    def test_index_definition_exists(self):
        """Test that IndexDefinition can be imported."""
        from iris_devtester.testing.models import IndexDefinition

        assert IndexDefinition is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
