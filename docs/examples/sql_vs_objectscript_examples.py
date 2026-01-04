"""
Working Examples: SQL vs ObjectScript Execution in IRIS

This file demonstrates the correct patterns for executing operations in IRIS.
Read CONSTITUTION.md Principle #2 and docs/SQL_VS_OBJECTSCRIPT.md first.

CRITICAL: These examples show what works and what doesn't. Copy these patterns.
"""

import intersystems_iris.dbapi._DBAPI as dbapi


# =============================================================================
# PATTERN 1: SQL Operations via DBAPI (✅ FAST - 3x faster)
# =============================================================================

def example_sql_operations():
    """✅ Correct: Use DBAPI for all SQL operations."""

    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
    cursor = conn.cursor()

    # ✅ CREATE TABLE
    cursor.execute("""
        CREATE TABLE Employee (
            ID INT PRIMARY KEY,
            Name VARCHAR(100),
            Department VARCHAR(50),
            Salary DECIMAL(10,2)
        )
    """)

    # ✅ INSERT DATA
    cursor.execute("INSERT INTO Employee VALUES (1, 'Alice', 'Engineering', 120000)")
    cursor.execute("INSERT INTO Employee VALUES (2, 'Bob', 'Sales', 95000)")
    cursor.execute("INSERT INTO Employee VALUES (3, 'Charlie', 'Engineering', 110000)")

    # ✅ SELECT QUERY
    cursor.execute("SELECT * FROM Employee WHERE Department = 'Engineering'")
    for row in cursor.fetchall():
        print(f"Employee: {row[1]}, Salary: ${row[3]:,.2f}")

    # ✅ UPDATE DATA
    cursor.execute("UPDATE Employee SET Salary = Salary * 1.10 WHERE Department = 'Engineering'")

    # ✅ COUNT QUERY
    cursor.execute("SELECT COUNT(*) FROM Employee")
    count = cursor.fetchone()[0]
    print(f"Total employees: {count}")

    # ✅ SYSTEM FUNCTION (SQL-compatible)
    cursor.execute("SELECT $SYSTEM.Version.GetVersion()")
    version = cursor.fetchone()[0]
    print(f"IRIS Version: {version}")

    # ✅ CLEANUP
    cursor.execute("DROP TABLE Employee")
    cursor.close()
    conn.close()


# =============================================================================
# PATTERN 2: Namespace Backup via DBAPI + $SYSTEM.OBJ.Execute() (✅ WORKS)
# =============================================================================

def example_backup_namespace_correct():
    """✅ Correct: Use $SYSTEM.OBJ.Execute() wrapper for backup operations."""

    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
    cursor = conn.cursor()

    # ✅ This works - ObjectScript wrapped in SQL function
    backup_path = "/tmp/user_backup.dat"

    cursor.execute(f"""
        SELECT $SYSTEM.OBJ.Execute('
            Set sc = ##class(SYS.Database).BackupNamespace("USER", "{backup_path}")
            If sc {{
                Write "SUCCESS"
            }} Else {{
                Write "FAILED: "_$system.Status.GetErrorText(sc)
            }}
        ')
    """)

    result = cursor.fetchone()[0]
    print(f"Backup result: {result}")

    if "SUCCESS" in result:
        print(f"Namespace backed up to: {backup_path}")
    else:
        print(f"Backup failed: {result}")

    cursor.close()
    conn.close()


# =============================================================================
# PATTERN 3: ObjectScript Operations via iris.connect() (✅ CORRECT)
# =============================================================================

def example_objectscript_operations():
    """✅ Correct: Use iris.connect() for ObjectScript operations."""

    import iris

    # Connect with iris.connect() for ObjectScript access
    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="%SYS",
        username="_SYSTEM",
        password="SYS"
    )

    iris_obj = iris.createIRIS(conn)

    # ✅ CREATE NAMESPACE
    print("Creating test namespace...")
    result = iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST_EXAMPLE")
    print(f"Create namespace result: {result}")

    # ✅ SET GLOBAL VARIABLE
    iris_obj.set("^EmployeeCount", "0")
    print("Set global ^EmployeeCount = 0")

    # ✅ GET GLOBAL VARIABLE
    count = iris_obj.get("^EmployeeCount")
    print(f"Get global ^EmployeeCount = {count}")

    # ✅ EXECUTE OBJECTSCRIPT CODE
    iris_obj.execute("""
        Set ^EmployeeCount = 100
        Set ^EmployeeNames(1) = "Alice"
        Set ^EmployeeNames(2) = "Bob"
        Set ^EmployeeNames(3) = "Charlie"
    """)
    print("Executed ObjectScript to populate globals")

    # ✅ READ UPDATED GLOBALS
    count = iris_obj.get("^EmployeeCount")
    name1 = iris_obj.get("^EmployeeNames", 1)
    name2 = iris_obj.get("^EmployeeNames", 2)
    print(f"Updated count: {count}, Names: {name1}, {name2}")

    # ✅ DELETE NAMESPACE (CLEANUP)
    print("Deleting test namespace...")
    result = iris_obj.classMethodValue("Config.Namespaces", "Delete", "TEST_EXAMPLE")
    print(f"Delete namespace result: {result}")

    conn.close()


# =============================================================================
# PATTERN 4: Integration Test Setup (✅ CORRECT PATTERN)
# =============================================================================

def example_integration_test_pattern():
    """
    ✅ Correct: Use iris.connect() for setup/cleanup, DBAPI for testing.

    This is the pattern all integration tests should follow.
    """

    import iris
    import uuid

    # Generate unique namespace name
    namespace = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    # SETUP: Use iris.connect() for namespace creation
    print(f"Setting up test namespace: {namespace}")
    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="%SYS",
        username="_SYSTEM",
        password="SYS"
    )
    iris_obj = iris.createIRIS(conn)
    iris_obj.classMethodValue("Config.Namespaces", "Create", namespace)
    conn.close()

    try:
        # TESTING: Use DBAPI for SQL operations (3x faster)
        print(f"Running tests in namespace: {namespace}")
        conn = dbapi.connect(f"localhost:1972/{namespace}", "_SYSTEM", "SYS")
        cursor = conn.cursor()

        # Test operations
        cursor.execute("CREATE TABLE TestData (ID INT PRIMARY KEY, Value VARCHAR(100))")
        cursor.execute("INSERT INTO TestData VALUES (1, 'Test Value')")
        cursor.execute("SELECT COUNT(*) FROM TestData")

        count = cursor.fetchone()[0]
        assert count == 1, f"Expected 1 row, got {count}"
        print(f"✓ Test passed: {count} row(s) found")

        cursor.close()
        conn.close()

    finally:
        # CLEANUP: Use iris.connect() for namespace deletion
        print(f"Cleaning up test namespace: {namespace}")
        conn = iris.connect(
            hostname="localhost",
            port=1972,
            namespace="%SYS",
            username="_SYSTEM",
            password="SYS"
        )
        iris_obj = iris.createIRIS(conn)
        iris_obj.classMethodValue("Config.Namespaces", "Delete", namespace)
        conn.close()


# =============================================================================
# ANTI-PATTERN 1: ObjectScript via DBAPI (❌ BREAKS!)
# =============================================================================

def antipattern_objectscript_via_dbapi():
    """
    ❌ WRONG: Cannot execute ObjectScript through DBAPI cursor.execute()

    This will fail with: "SQL ERROR: SQL statement expected"
    """

    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
    cursor = conn.cursor()

    try:
        # ❌ BREAKS - DBAPI cannot execute ObjectScript
        cursor.execute("Set ^MyGlobal = 'value'")
        print("This line never executes")

    except Exception as e:
        print(f"❌ Failed as expected: {e}")

    try:
        # ❌ BREAKS - DO command not supported
        cursor.execute("DO ##class(MyClass).MyMethod()")
        print("This line never executes")

    except Exception as e:
        print(f"❌ Failed as expected: {e}")

    cursor.close()
    conn.close()


# =============================================================================
# ANTI-PATTERN 2: Namespace Creation via DBAPI (❌ SECURITY ERROR!)
# =============================================================================

def antipattern_namespace_creation_via_dbapi():
    """
    ❌ WRONG: Cannot create namespaces via $SYSTEM.OBJ.Execute()

    This will fail with security error - namespace operations require
    proper %SYS context which $SYSTEM.OBJ.Execute() doesn't provide.
    """

    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
    cursor = conn.cursor()

    try:
        # ❌ BREAKS - Security restriction
        cursor.execute("""
            SELECT $SYSTEM.OBJ.Execute('
                Do ##class(Config.Namespaces).Create("TEST_FAIL")
            ')
        """)
        print("This line never executes")

    except Exception as e:
        print(f"❌ Failed as expected: {e}")

    cursor.close()
    conn.close()


# =============================================================================
# ANTI-PATTERN 3: Using iris.connect() for SQL Queries (⚠️ SLOW!)
# =============================================================================

def antipattern_sql_via_iris_connect():
    """
    ⚠️ SLOW: Using iris.connect() for SQL queries is 3x slower than DBAPI.

    This works but is inefficient. Always use DBAPI for SQL operations.
    """

    import iris
    import time

    conn = iris.connect(
        hostname="localhost",
        port=1972,
        namespace="USER",
        username="_SYSTEM",
        password="SYS"
    )
    iris_obj = iris.createIRIS(conn)

    # ⚠️ Works but SLOW - 3x slower than DBAPI
    start = time.time()
    result = iris_obj.sql("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
    elapsed = time.time() - start

    print(f"⚠️ iris.connect() SQL query took: {elapsed:.3f}s")
    print("   Use DBAPI instead for 3x speedup!")

    conn.close()

    # ✅ BETTER - Use DBAPI
    conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
    cursor = conn.cursor()

    start = time.time()
    cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
    result = cursor.fetchone()
    elapsed = time.time() - start

    print(f"✅ DBAPI SQL query took: {elapsed:.3f}s")

    cursor.close()
    conn.close()


# =============================================================================
# DECISION HELPER FUNCTION
# =============================================================================

def what_tool_should_i_use(operation: str) -> str:
    """
    Quick reference: What tool should I use for this operation?

    Args:
        operation: Description of what you want to do

    Returns:
        Recommended tool and example
    """

    decision_map = {
        "query data": ("DBAPI", "cursor.execute('SELECT * FROM MyTable')"),
        "insert data": ("DBAPI", "cursor.execute('INSERT INTO MyTable VALUES (...)')"),
        "create table": ("DBAPI", "cursor.execute('CREATE TABLE ...')"),
        "backup namespace": ("DBAPI + $SYSTEM.OBJ.Execute", "cursor.execute('SELECT $SYSTEM.OBJ.Execute(...)')"),
        "restore namespace": ("DBAPI + $SYSTEM.OBJ.Execute", "cursor.execute('SELECT $SYSTEM.OBJ.Execute(...)')"),
        "create namespace": ("iris.connect()", "iris_obj.classMethodValue('Config.Namespaces', 'Create', 'TEST')"),
        "delete namespace": ("iris.connect()", "iris_obj.classMethodValue('Config.Namespaces', 'Delete', 'TEST')"),
        "task manager": ("iris.connect()", "iris_obj.execute('Set task = ##class(%SYS.Task).%New()')"),
        "set global": ("iris.connect()", "iris_obj.set('^MyGlobal', 'value')"),
        "get global": ("iris.connect()", "iris_obj.get('^MyGlobal')"),
        "reset password": ("docker exec", "docker exec iris_db iris session IRIS -U %SYS ..."),
        "get version": ("DBAPI", "cursor.execute('SELECT $SYSTEM.Version.GetVersion()')"),
    }

    operation_lower = operation.lower()

    for key, (tool, example) in decision_map.items():
        if key in operation_lower:
            return f"Use: {tool}\nExample: {example}"

    return "Not sure - check docs/SQL_VS_OBJECTSCRIPT.md"


# =============================================================================
# MAIN - Run Examples
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("SQL vs ObjectScript Examples - iris-devtester")
    print("=" * 80)
    print()

    # Show decision helper
    print("Quick reference:")
    print(what_tool_should_i_use("query data"))
    print()
    print(what_tool_should_i_use("create namespace"))
    print()
    print(what_tool_should_i_use("set global"))
    print()

    # Run examples (commented out - uncomment to run with real IRIS)
    # print("\n1. SQL Operations (DBAPI):")
    # example_sql_operations()
    #
    # print("\n2. Namespace Backup (DBAPI + $SYSTEM.OBJ.Execute):")
    # example_backup_namespace_correct()
    #
    # print("\n3. ObjectScript Operations (iris.connect):")
    # example_objectscript_operations()
    #
    # print("\n4. Integration Test Pattern:")
    # example_integration_test_pattern()
    #
    # print("\n5. Anti-Pattern: ObjectScript via DBAPI (will fail):")
    # antipattern_objectscript_via_dbapi()
    #
    # print("\n6. Anti-Pattern: Namespace via DBAPI (will fail):")
    # antipattern_namespace_creation_via_dbapi()
    #
    # print("\n7. Anti-Pattern: SQL via iris.connect (slow):")
    # antipattern_sql_via_iris_connect()

    print("\n" + "=" * 80)
    print("Read CONSTITUTION.md Principle #2 for full details")
    print("Read docs/SQL_VS_OBJECTSCRIPT.md for complete guide")
    print("=" * 80)
