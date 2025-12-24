"""
Unit tests for schema definition models.

Tests MUST FAIL until iris_devtester/testing/models.py is implemented.
"""

import pytest


class TestColumnDefinition:
    """Test ColumnDefinition dataclass."""

    def test_can_import(self):
        """Test that ColumnDefinition can be imported."""
        from iris_devtester.testing.models import ColumnDefinition

        assert ColumnDefinition is not None

    def test_required_fields(self):
        """Test that ColumnDefinition requires name and type."""
        from iris_devtester.testing.models import ColumnDefinition

        col = ColumnDefinition(name="id", type="INTEGER")
        assert col.name == "id"
        assert col.type == "INTEGER"

    def test_optional_fields(self):
        """Test that ColumnDefinition has optional fields."""
        from iris_devtester.testing.models import ColumnDefinition

        col = ColumnDefinition(
            name="username",
            type="VARCHAR",
            max_length=50,
            nullable=False,
            default="guest"
        )
        assert col.max_length == 50
        assert col.nullable == False
        assert col.default == "guest"


class TestIndexDefinition:
    """Test IndexDefinition dataclass."""

    def test_can_import(self):
        """Test that IndexDefinition can be imported."""
        from iris_devtester.testing.models import IndexDefinition

        assert IndexDefinition is not None

    def test_required_fields(self):
        """Test that IndexDefinition requires name and columns."""
        from iris_devtester.testing.models import IndexDefinition

        idx = IndexDefinition(name="idx_username", columns=["username"])
        assert idx.name == "idx_username"
        assert idx.columns == ["username"]
        assert idx.unique == False

    def test_unique_index(self):
        """Test that IndexDefinition supports unique flag."""
        from iris_devtester.testing.models import IndexDefinition

        idx = IndexDefinition(name="idx_email", columns=["email"], unique=True)
        assert idx.unique == True


class TestTableDefinition:
    """Test TableDefinition dataclass."""

    def test_can_import(self):
        """Test that TableDefinition can be imported."""
        from iris_devtester.testing.models import TableDefinition

        assert TableDefinition is not None

    def test_required_fields(self):
        """Test that TableDefinition requires name."""
        from iris_devtester.testing.models import TableDefinition

        table = TableDefinition(name="users")
        assert table.name == "users"
        assert table.columns == {}
        assert table.indexes == []

    def test_with_columns(self):
        """Test that TableDefinition can have columns."""
        from iris_devtester.testing.models import TableDefinition, ColumnDefinition

        col1 = ColumnDefinition(name="id", type="INTEGER")
        col2 = ColumnDefinition(name="username", type="VARCHAR", max_length=50)

        table = TableDefinition(
            name="users",
            columns={"id": col1, "username": col2}
        )
        assert len(table.columns) == 2
        assert "id" in table.columns
        assert "username" in table.columns


class TestSchemaDefinition:
    """Test SchemaDefinition dataclass."""

    def test_can_import(self):
        """Test that SchemaDefinition can be imported."""
        from iris_devtester.testing.models import SchemaDefinition

        assert SchemaDefinition is not None

    def test_default_values(self):
        """Test that SchemaDefinition has default values."""
        from iris_devtester.testing.models import SchemaDefinition

        schema = SchemaDefinition()
        assert schema.tables == {}
        assert schema.version == "1.0.0"
        assert schema.description is None

    def test_with_tables(self):
        """Test that SchemaDefinition can contain tables."""
        from iris_devtester.testing.models import SchemaDefinition, TableDefinition

        table1 = TableDefinition(name="users")
        table2 = TableDefinition(name="products")

        schema = SchemaDefinition(
            tables={"users": table1, "products": table2},
            version="2.0.0",
            description="Test schema"
        )
        assert len(schema.tables) == 2
        assert schema.version == "2.0.0"
        assert schema.description == "Test schema"


class TestSchemaMismatch:
    """Test SchemaMismatch dataclass."""

    def test_can_import(self):
        """Test that SchemaMismatch can be imported."""
        from iris_devtester.testing.models import SchemaMismatch

        assert SchemaMismatch is not None

    def test_required_fields(self):
        """Test that SchemaMismatch requires table and type."""
        from iris_devtester.testing.models import SchemaMismatch

        mismatch = SchemaMismatch(
            table="users",
            type="missing_column"
        )
        assert mismatch.table == "users"
        assert mismatch.type == "missing_column"


class TestSchemaValidationResult:
    """Test SchemaValidationResult dataclass."""

    def test_can_import(self):
        """Test that SchemaValidationResult can be imported."""
        from iris_devtester.testing.models import SchemaValidationResult

        assert SchemaValidationResult is not None

    def test_valid_result(self):
        """Test that SchemaValidationResult can represent valid schema."""
        from iris_devtester.testing.models import SchemaValidationResult

        result = SchemaValidationResult(is_valid=True)
        assert result.is_valid == True
        assert result.mismatches == []

    def test_invalid_result(self):
        """Test that SchemaValidationResult can represent invalid schema."""
        from iris_devtester.testing.models import SchemaValidationResult, SchemaMismatch

        mismatch = SchemaMismatch(table="users", type="missing_column")
        result = SchemaValidationResult(
            is_valid=False,
            mismatches=[mismatch]
        )
        assert result.is_valid == False
        assert len(result.mismatches) == 1

    def test_get_summary(self):
        """Test that SchemaValidationResult has get_summary method."""
        from iris_devtester.testing.models import SchemaValidationResult

        result = SchemaValidationResult(is_valid=True)
        summary = result.get_summary()
        assert isinstance(summary, str)
        assert "passed" in summary.lower() or "valid" in summary.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
