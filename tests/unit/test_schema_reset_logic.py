import pytest
from unittest.mock import MagicMock, patch
from iris_devtester.testing.schema_reset import SchemaResetter, DEFAULT_RAG_ORDER

def test_topological_sort_logic():
    """Verify tables are sorted correctly based on dependencies."""
    mock_conn = MagicMock()
    resetter = SchemaResetter(mock_conn)
    
    tables = ["Parent", "Child", "Grandchild", "Orphan"]
    # Child -> Parent (Child depends on Parent)
    # Grandchild -> Child (Grandchild depends on Child)
    dependencies = [
        ("Child", "Parent"),
        ("Grandchild", "Child"),
    ]
    
    # We want to DELETE leaf first: Grandchild, then Child, then Parent
    sorted_tables = resetter._topological_sort(tables, dependencies)
    
    assert sorted_tables.index("Grandchild") < sorted_tables.index("Child")
    assert sorted_tables.index("Child") < sorted_tables.index("Parent")
    assert "Orphan" in sorted_tables

def test_reset_rag_schema_order():
    """Verify reset_rag_schema uses the correct priority order."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    
    # Simulate tables found in schema
    # Mixed order to test sorting logic
    tables = [
        ("SourceDocuments",),
        ("Entities",),
        ("SomethingElse",),
        ("EntityRelationships",),
        ("DocumentChunks",),
    ]
    mock_cursor.fetchall.return_value = tables
    
    resetter = SchemaResetter(mock_conn)
    results = resetter.reset_rag_schema()
    
    assert results["total"] == 5
    assert results["success"] == 5
    
    # Verify execution order
    # Priority tables from DEFAULT_RAG_ORDER should come first
    executed_sql = [call.args[0] for call in mock_cursor.execute.call_args_list]
    
    # First query is the discovery
    assert "SELECT TABLE_NAME" in executed_sql[0]
    
    # Subsequent queries are the DELETEs
    deletes = [sql for sql in executed_sql if "DELETE FROM" in sql]
    
    # Check that EntityRelationships (index 0 in DEFAULT_RAG_ORDER) was deleted before SourceDocuments
    er_index = next(i for i, sql in enumerate(deletes) if "EntityRelationships" in sql)
    sd_index = next(i for i, sql in enumerate(deletes) if "SourceDocuments" in sql)
    assert er_index < sd_index
    
    # Check that "SomethingElse" (not in priority list) was handled
    assert any("SomethingElse" in sql for sql in deletes)

def test_truncate_schema_safety():
    """Verify system schemas are protected."""
    mock_conn = MagicMock()
    resetter = SchemaResetter(mock_conn)
    
    with pytest.raises(ValueError, match="protected system schema"):
        resetter.truncate_schema("%SYS")
    
    with pytest.raises(ValueError, match="protected system schema"):
        resetter.truncate_schema("INFORMATION_SCHEMA")

def test_truncate_schema_strict_failure():
    """Verify strict mode raises on failure."""
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchall.return_value = [("Table1",)]
    mock_cursor.execute.side_effect = [None, Exception("SQL Error")] # Discovery success, Delete fail
    
    resetter = SchemaResetter(mock_conn)
    with pytest.raises(RuntimeError, match="Failed to clean RAG.Table1"):
        resetter.truncate_schema("RAG", strict=True)
