# SQL vs ObjectScript in IRIS: Complete Execution Guide

**Status**: CRITICAL REFERENCE - Read Before Implementing Any IRIS Operations
**Last Updated**: 2025-10-18

## Executive Summary

InterSystems IRIS supports **two distinct execution paths**:
1. **SQL** - Via DBAPI/JDBC (fast, connection-pool friendly)
2. **ObjectScript** - Via iris.connect() or docker exec (full system access)

**Getting this wrong breaks everything.** This guide ensures you choose the right approach.

---

## The Fundamental Rule

### ✅ SQL Operations → Use DBAPI

```python
import intersystems_iris.dbapi._DBAPI as dbapi

conn = dbapi.connect("localhost:1972/USER", "_SYSTEM", "SYS")
cursor = conn.cursor()

# ✅ This works - Pure SQL
cursor.execute("SELECT COUNT(*) FROM MyTable")
cursor.execute("INSERT INTO MyTable (ID, Name) VALUES (1, 'Alice')")
cursor.execute("CREATE TABLE TestData (ID INT PRIMARY KEY, Name VARCHAR(100))")
cursor.execute("SELECT $SYSTEM.Version.GetVersion()")  # System function in SQL context
cursor.close()
```

### ✅ ObjectScript Operations → Use iris.connect()

```python
import iris

conn = iris.connect(
    hostname="localhost",
    port=1972,
    namespace="USER",
    username="_SYSTEM",
    password="SYS"
)

iris_obj = iris.createIRIS(conn)

# ✅ This works - ObjectScript execution
iris_obj.classMethodValue("%SYSTEM.OBJ", "Load", "MyClass.cls", "ck")
iris_obj.execute("Set ^GlobalData = 'value'")
iris_obj.execute("Do ##class(Config.Namespaces).Create('TEST')")

conn.close()
```

### ❌ NEVER Mix Them Incorrectly

```python
# ❌ WRONG - DBAPI cannot execute ObjectScript
cursor.execute("DO $SYSTEM.OBJ.Execute('...')")  # FAILS
cursor.execute("Set ^GlobalData = 'value'")       # FAILS

# ❌ WRONG - Wrapping in SELECT doesn't help
cursor.execute("SELECT $SYSTEM.OBJ.Execute('Do ##class(...)')")  # FAILS
```

---

## What Works Where: Complete Matrix

| Operation | DBAPI (SQL) | iris.connect() | docker exec | Best Choice |
|-----------|-------------|----------------|-------------|-------------|
| **Data Operations** |
| SELECT queries | ✅ Fast | ✅ Works | ❌ Awkward | **DBAPI** |
| INSERT/UPDATE/DELETE | ✅ Fast | ✅ Works | ❌ Awkward | **DBAPI** |
| CREATE TABLE | ✅ Fast | ✅ Works | ❌ Awkward | **DBAPI** |
| Transactions | ✅ Built-in | ✅ Works | ❌ No | **DBAPI** |
| **System Operations** |
| Create namespace | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| Delete namespace | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| Task Manager | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| User management | ❌ No | ✅ Yes | ✅ Yes | **docker exec** |
| Password reset | ❌ No | ❌ No | ✅ Only way | **docker exec** |
| **Globals** |
| Read globals | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| Write globals | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| Kill globals | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| **Classes** |
| Compile classes | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| Load code | ❌ No | ✅ Yes | ✅ Yes | **iris.connect()** |
| Execute methods | ⚠️ Limited | ✅ Full | ❌ Awkward | **iris.connect()** |
| **Queries** |
| SQL queries | ✅ Fast | ✅ Works | ❌ Awkward | **DBAPI** |
| System info queries | ✅ Yes* | ✅ Yes | ❌ Awkward | **DBAPI*** |
| Performance metrics | ✅ Yes* | ✅ Yes | ❌ Awkward | **DBAPI*** |

\* Via SQL-compatible system functions like `$SYSTEM.Version.GetVersion()`

---

## Common Operations: Working Examples

### 1. Create Namespace

#### ❌ WRONG - DBAPI Cannot Do This
```python
cursor.execute("DO ##class(Config.Namespaces).Create('TEST')")  # FAILS!
```

#### ✅ RIGHT - Use iris.connect()
```python
import iris

conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                    username="_SYSTEM", password="SYS")
iris_obj = iris.createIRIS(conn)
iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
conn.close()
```

#### ✅ ALTERNATIVE - Use docker exec (for containers)
```python
import subprocess

subprocess.run([
    "docker", "exec", "iris_db",
    "iris", "session", "IRIS", "-U", "%SYS",
    "##class(Config.Namespaces).Create('TEST')"
], check=True)
```

---

### 2. Create Task Manager Task

#### ❌ WRONG - DBAPI Cannot Execute ObjectScript
```python
cursor.execute("""
    DO $SYSTEM.OBJ.Execute("
        Set task = ##class(%SYS.Task).%New()
        Set task.Name = 'MyTask'
        Do task.%Save()
    ")
""")  # FAILS!
```

#### ✅ RIGHT - Use iris.connect()
```python
import iris

conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                    username="_SYSTEM", password="SYS")
iris_obj = iris.createIRIS(conn)

# Create task via ObjectScript
iris_obj.execute("""
    Set task = ##class(%SYS.Task).%New()
    Set task.Name = "MyTask"
    Set task.NameSpace = "USER"
    Set sc = task.%Save()
    If sc {
        Write "SUCCESS"
    } Else {
        Write "FAILED"
    }
""")

conn.close()
```

---

### 3. Query Performance Metrics

#### ✅ GOOD - SQL via DBAPI (if SQL function exists)
```python
cursor.execute("SELECT $SYSTEM.Process.CPUTime()")
row = cursor.fetchone()
cpu_time = row[0]
```

#### ✅ BETTER - ObjectScript via iris.connect() (for complex queries)
```python
iris_obj.classMethodValue("%SYSTEM.Process", "CPUTime")
```

---

### 4. Backup Namespace (BACKUP^DBACK)

#### ❌ WRONG - This pattern fails
```python
cursor.execute("""
    DO ^BACKUP("USER", "/tmp/backup.dat")
""")  # FAILS!
```

#### ✅ RIGHT - Use SQL-compatible class method
```python
cursor.execute("""
    SELECT $SYSTEM.OBJ.Execute('
        Set sc = ##class(SYS.Database).BackupNamespace("USER", "/tmp/backup.dat")
        If sc { Write "SUCCESS" } Else { Write "FAILED" }
    ')
""")
result = cursor.fetchone()
print(result[0])  # "SUCCESS" or "FAILED"
```

**This works because**:
- `$SYSTEM.OBJ.Execute()` is a SQL function
- The ObjectScript is passed as a string argument
- Result is returned via SQL context

---

### 5. Restore Namespace (RESTORE)

#### ✅ WORKS - Via SQL function wrapper
```python
cursor.execute("""
    SELECT $SYSTEM.OBJ.Execute('
        Set sc = ##class(SYS.Database).RestoreNamespace("TARGET", "/tmp/backup.dat")
        If sc { Write "SUCCESS" } Else { Write "FAILED" }
    ')
""")
```

---

## The $SYSTEM.OBJ.Execute() Pattern

This is the **ONLY** way to execute ObjectScript through DBAPI:

### ✅ Pattern That Works
```python
cursor.execute("""
    SELECT $SYSTEM.OBJ.Execute('
        ObjectScript commands here
        Write result to return it
    ')
""")
result = cursor.fetchone()[0]
```

### Critical Rules:
1. Must be wrapped in `SELECT $SYSTEM.OBJ.Execute()`
2. ObjectScript must be single-quoted string
3. Use `Write` to return values
4. Limited to what `$SYSTEM.OBJ.Execute()` can do
5. **Cannot create namespaces** (security restriction)
6. **Cannot modify Task Manager** (requires %SYS namespace context)
7. **Cannot change user passwords** (security restriction)

### What Works via $SYSTEM.OBJ.Execute():
- ✅ Backup namespace
- ✅ Restore namespace
- ✅ Load classes
- ✅ Compile code
- ✅ Query system info
- ✅ Read/write globals (within current namespace)
- ✅ Execute class methods (within security limits)

### What Doesn't Work:
- ❌ Create/delete namespaces (use iris.connect())
- ❌ Task Manager operations (use iris.connect())
- ❌ User/password management (use docker exec)
- ❌ System configuration changes (use iris.connect())
- ❌ Cross-namespace operations requiring %SYS

---

## Integration Test Patterns

### Pattern 1: Test Setup with iris.connect(), Testing with DBAPI

```python
import iris
import intersystems_iris.dbapi._DBAPI as dbapi

def test_my_feature():
    # Setup: Use iris.connect() for ObjectScript operations
    conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                        username="_SYSTEM", password="SYS")
    iris_obj = iris.createIRIS(conn)

    # Create test namespace
    iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
    conn.close()

    # Testing: Use DBAPI for SQL operations
    db_conn = dbapi.connect("localhost:1972/TEST", "_SYSTEM", "SYS")
    cursor = db_conn.cursor()

    # Create test data via SQL
    cursor.execute("CREATE TABLE TestData (ID INT PRIMARY KEY, Name VARCHAR(100))")
    cursor.execute("INSERT INTO TestData VALUES (1, 'Alice')")

    # Test your feature
    cursor.execute("SELECT COUNT(*) FROM TestData")
    assert cursor.fetchone()[0] == 1

    cursor.close()
    db_conn.close()

    # Cleanup: Use iris.connect() again
    conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                        username="_SYSTEM", password="SYS")
    iris_obj = iris.createIRIS(conn)
    iris_obj.classMethodValue("Config.Namespaces", "Delete", "TEST")
    conn.close()
```

### Pattern 2: Docker Exec for Container Operations

```python
import subprocess

def reset_iris_password(container="iris_db"):
    """Reset IRIS password using docker exec."""
    subprocess.run([
        "docker", "exec", container,
        "bash", "-c",
        'echo "Set props(\\"ChangePassword\\")=0 Set props(\\"ExternalPassword\\")=\\"SYS\\" '
        'Write ##class(Security.Users).Modify(\\"_SYSTEM\\",.props)" | '
        'iris session IRIS -U %SYS'
    ], check=True)
```

### Pattern 3: Fixture Creation (Current Implementation)

```python
# ✅ This works - FixtureCreator.export_namespace_to_dat()
cursor.execute(f"""
    SELECT $SYSTEM.OBJ.Execute('
        Set sc = ##class(SYS.Database).BackupNamespace("{namespace}", "{dat_file}")
        If sc {{ Write "SUCCESS" }} Else {{ Write "FAILED" }}
    ')
""")
```

---

## Performance Implications

### DBAPI Performance
- **Connection**: ~50-100ms
- **Simple query**: ~1-5ms
- **Complex query**: ~10-50ms
- **Transaction**: ~5-20ms
- **3x faster** than iris.connect() for SQL operations

### iris.connect() Performance
- **Connection**: ~200-500ms (includes embedded Python initialization)
- **ObjectScript execution**: ~10-50ms
- **Class method call**: ~20-100ms
- Required for system operations

### docker exec Performance
- **Command execution**: ~200-1000ms (includes container overhead)
- **Only use** for operations unavailable via iris.connect()
- Best for one-time setup (password reset, etc.)

---

## Decision Tree

```
Operation needed?
│
├─ Data query/manipulation (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE)?
│  └─ Use DBAPI ✅
│
├─ System function in SQL context ($SYSTEM.Version.GetVersion())?
│  └─ Use DBAPI ✅
│
├─ Backup/Restore namespace?
│  └─ Use DBAPI with $SYSTEM.OBJ.Execute() ✅
│
├─ Create/delete namespace?
│  └─ Use iris.connect() ✅
│
├─ Task Manager operations?
│  └─ Use iris.connect() ✅
│
├─ User/password management?
│  └─ Use docker exec ✅
│
├─ Global variables?
│  └─ Use iris.connect() ✅
│
└─ Not sure?
   └─ Try DBAPI first, fall back to iris.connect() if it fails
```

---

## Common Mistakes and Fixes

### Mistake 1: Trying to execute ObjectScript via DBAPI

```python
# ❌ WRONG
cursor.execute("DO ##class(MyClass).MyMethod()")

# ✅ RIGHT
import iris
conn = iris.connect(...)
iris_obj = iris.createIRIS(conn)
iris_obj.classMethodValue("MyClass", "MyMethod")
```

### Mistake 2: Using SELECT $SYSTEM.OBJ.Execute() for namespace creation

```python
# ❌ WRONG - Security restriction
cursor.execute("SELECT $SYSTEM.OBJ.Execute('Do ##class(Config.Namespaces).Create(\"TEST\")')")

# ✅ RIGHT
import iris
conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS", ...)
iris_obj = iris.createIRIS(conn)
iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")
```

### Mistake 3: Using iris.connect() for simple queries

```python
# ❌ SLOW - 3x slower than DBAPI
import iris
conn = iris.connect(...)
iris_obj = iris.createIRIS(conn)
result = iris_obj.sql("SELECT COUNT(*) FROM MyTable")

# ✅ FAST
import intersystems_iris.dbapi._DBAPI as dbapi
conn = dbapi.connect(...)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM MyTable")
```

---

## Constitutional Principle #2: Updated

**OLD**: "DBAPI First, JDBC Fallback"

**NEW**: "Choose the Right Tool"

1. **SQL Operations** → DBAPI (3x faster)
   - SELECT, INSERT, UPDATE, DELETE
   - CREATE TABLE, DROP TABLE
   - Transactions
   - SQL-compatible system functions

2. **ObjectScript via SQL** → DBAPI with $SYSTEM.OBJ.Execute()
   - Backup/Restore namespace
   - Load/compile classes
   - Limited system operations

3. **System Operations** → iris.connect()
   - Create/delete namespaces
   - Task Manager
   - Global variables
   - Full ObjectScript execution

4. **Container Operations** → docker exec
   - User/password management
   - System configuration
   - One-time setup operations

**Always try the fastest option first**, but choose based on what the operation actually requires.

---

## Testing Strategy

### Unit Tests
- Mock IRIS connections
- Test logic, not IRIS operations
- No IRIS required

### Contract Tests
- Validate API signatures
- Mock IRIS responses
- Verify error handling patterns

### Integration Tests
- **Setup**: iris.connect() or docker exec
- **Testing**: DBAPI for SQL operations
- **Cleanup**: iris.connect() or docker exec

### Example Integration Test Structure

```python
@pytest.fixture(scope="function")
def test_namespace():
    """Create isolated test namespace."""
    namespace = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    # Setup via iris.connect()
    conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                        username="_SYSTEM", password="SYS")
    iris_obj = iris.createIRIS(conn)
    iris_obj.classMethodValue("Config.Namespaces", "Create", namespace)
    conn.close()

    yield namespace

    # Cleanup via iris.connect()
    conn = iris.connect(hostname="localhost", port=1972, namespace="%SYS",
                        username="_SYSTEM", password="SYS")
    iris_obj = iris.createIRIS(conn)
    iris_obj.classMethodValue("Config.Namespaces", "Delete", namespace)
    conn.close()

def test_my_feature(test_namespace):
    """Test using DBAPI for SQL operations."""
    conn = dbapi.connect(f"localhost:1972/{test_namespace}", "_SYSTEM", "SYS")
    cursor = conn.cursor()

    # Test SQL operations
    cursor.execute("CREATE TABLE TestData (ID INT, Name VARCHAR(100))")
    cursor.execute("INSERT INTO TestData VALUES (1, 'Alice')")
    cursor.execute("SELECT COUNT(*) FROM TestData")

    assert cursor.fetchone()[0] == 1
```

---

## Quick Reference Card

| Need to... | Use... | Example |
|------------|--------|---------|
| Query data | DBAPI | `cursor.execute("SELECT * FROM MyTable")` |
| Insert data | DBAPI | `cursor.execute("INSERT INTO MyTable ...")` |
| Create table | DBAPI | `cursor.execute("CREATE TABLE ...")` |
| Backup namespace | DBAPI + $SYSTEM.OBJ.Execute | `cursor.execute("SELECT $SYSTEM.OBJ.Execute('...')")` |
| Create namespace | iris.connect() | `iris_obj.classMethodValue("Config.Namespaces", "Create", "TEST")` |
| Delete namespace | iris.connect() | `iris_obj.classMethodValue("Config.Namespaces", "Delete", "TEST")` |
| Task Manager | iris.connect() | `iris_obj.execute("Set task = ##class(%SYS.Task).%New() ...")` |
| Set global | iris.connect() | `iris_obj.set("^MyGlobal", "value")` |
| Get global | iris.connect() | `iris_obj.get("^MyGlobal")` |
| Reset password | docker exec | `docker exec iris_db iris session IRIS -U %SYS ...` |
| System version | DBAPI | `cursor.execute("SELECT $SYSTEM.Version.GetVersion()")` |

---

## Summary

**The Critical Rules**:

1. ✅ **DBAPI for SQL** - Fast, poolable, reliable
2. ✅ **iris.connect() for ObjectScript** - System operations, globals, classes
3. ✅ **docker exec for admin** - Password reset, system config
4. ❌ **NEVER mix incorrectly** - DBAPI cannot execute ObjectScript directly
5. ⚠️ **$SYSTEM.OBJ.Execute() is limited** - Works for some operations, not all

**When in doubt**:
1. Check this guide
2. Try DBAPI first
3. Fall back to iris.connect() if DBAPI fails
4. Use docker exec only for container admin operations

**This is the foundation of iris-devtester success.** Get this right, and everything else works. Get this wrong, and nothing works.
