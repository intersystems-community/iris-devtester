#!/usr/bin/env python
"""
Debug script to explore %SYS.Task table schema.
"""
from iris_devtools.connections import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()

    # Try to describe the table
    queries = [
        "SELECT TOP 1 * FROM %SYS.Task",
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Task' AND TABLE_SCHEMA = '%SYS'",
    ]

    for query in queries:
        print(f"\n=== Query: {query} ===")
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"Results ({len(results)} rows):")
            for row in results[:10]:  # First 10 rows
                print(f"  {row}")
        except Exception as e:
            print(f"Error: {e}")

    # Try ObjectScript approach
    print("\n=== Using ObjectScript ===")
    os_query = """
    SELECT
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = '%SYS'
    AND TABLE_NAME = 'Task'
    ORDER BY ORDINAL_POSITION
    """
    try:
        cursor.execute(os_query)
        columns = cursor.fetchall()
        print(f"Found {len(columns)} columns:")
        for col in columns:
            print(f"  {col}")
    except Exception as e:
        print(f"Error: {e}")

    conn.close()
    print("\n✓ Done")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
