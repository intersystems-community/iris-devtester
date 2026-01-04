# Embedded Python Considerations for IRIS DevTools

**Date**: 2025-10-05
**Status**: Design Decision
**Context**: IRIS has embedded Python runtime in addition to external DBAPI/JDBC

## Overview

InterSystems IRIS supports **three** Python connection methods:

1. **External Python + DBAPI** (`intersystems-irispython`) - Current focus
2. **External Python + JDBC** (`jaydebeapi`) - Current fallback
3. **Embedded Python** (runs inside IRIS process) - **NEW consideration**

This document analyzes embedded Python and explains why iris-devtester focuses on external Python.

## What is Embedded Python?

**Embedded Python** is a Python runtime that runs **inside** the IRIS database process:

```python
# Code running INSIDE IRIS (ObjectScript can call this)
ClassMethod MyMethod() As %String [ Language = python ]
{
    import iris
    # Direct access to IRIS objects, no network connection needed
    rs = iris.sql.exec("SELECT * FROM Users")
    return rs.fetchone()
}
```

### Characteristics

**Pros**:
- ✅ **Zero latency**: No network overhead (in-process)
- ✅ **Direct access**: Can access IRIS internals directly
- ✅ **No connection setup**: Already inside IRIS
- ✅ **Stored procedures**: Can write Python stored procedures

**Cons**:
- ❌ **Must run inside IRIS**: Can't run from external Python process
- ❌ **Limited use case**: Only for code executing within IRIS
- ❌ **Not suitable for testing**: Can't test external applications
- ❌ **Deployment complexity**: Code must be deployed to IRIS
- ❌ **Not PyPI compatible**: Can't be a standalone package

## Use Case Analysis

### When Embedded Python Makes Sense

**Scenario 1: Stored Procedures/Business Logic**
```python
# Running INSIDE IRIS
Class MyApp.BusinessLogic Extends %RegisteredObject [ Language = python ]
{
    # Complex calculations, data transformations
    # Access to IRIS globals, classes directly
}
```

**Scenario 2: IRIS Extensions**
```python
# Running INSIDE IRIS
# Custom IRIS functionality, plugins
# Performance-critical operations
```

**Scenario 3: WSGI Apps Hosted in IRIS** ⚠️ IMPORTANT
```python
# Flask/Django/FastAPI app running INSIDE IRIS embedded Python
# IRIS loads the WSGI app, serves HTTP requests
# App runs in embedded Python context

# app.py - Deployed to IRIS, served by IRIS web server
from flask import Flask
import iris  # Direct access, no external connection needed!

app = Flask(__name__)

@app.route('/users')
def get_users():
    # Already inside IRIS - use embedded Python context
    rs = iris.sql.exec("SELECT * FROM Users")
    return {'users': rs.fetchall()}

# IRIS configuration loads this WSGI app
# Serves requests via IRIS web server
```

**Why this matters**:
- App code runs **inside** IRIS (embedded Python)
- No external connection needed (already in-process)
- **iris-devtester would NOT be used** for database access
- But **iris-devtester COULD be used** for testing the app externally!

### When External Python Makes Sense (iris-devtester focus)

**Scenario 1: Python Applications** (TARGET)
```python
# Running OUTSIDE IRIS (FastAPI, Django, Flask apps)
from iris_devtester import get_iris_connection

conn = get_iris_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM Users")
# Application continues...
```

**Scenario 2: Testing & Development** (TARGET)
```python
# Running OUTSIDE IRIS (pytest tests)
def test_my_feature(iris_db):
    # Test against IRIS database
    # Isolated test environment
    # CI/CD compatible
```

**Scenario 3: Data Science & Analytics** (TARGET)
```python
# Running OUTSIDE IRIS (Jupyter notebooks)
import pandas as pd
from iris_devtester import get_iris_connection

conn = get_iris_connection()
df = pd.read_sql("SELECT * FROM SalesData", conn)
# Analysis continues...
```

**Scenario 4: ETL & Data Integration** (TARGET)
```python
# Running OUTSIDE IRIS (Airflow, Luigi pipelines)
from iris_devtester import get_iris_connection

# Extract from source
# Transform data
# Load into IRIS
```

## Design Decision: External Python Focus

### Decision

**iris-devtester will focus exclusively on external Python connectivity** (DBAPI/JDBC).

### Rationale

1. **Different use cases**: Embedded Python is for IRIS-internal code; iris-devtester is for external applications
2. **PyPI distribution**: External package can be `pip install`ed; embedded code cannot
3. **Testing focus**: Testing utilities need external connections (testcontainers)
4. **Broader applicability**: Most Python developers use external connections
5. **Constitutional alignment**: Zero-config, pip install, pytest - all external patterns

### Implications

**What iris-devtester DOES**:
- ✅ Connect to IRIS from external Python processes
- ✅ Support DBAPI (fast) and JDBC (fallback) drivers
- ✅ Provide pytest fixtures for testing against IRIS
- ✅ Manage IRIS containers for development/testing
- ✅ Support Python 3.9+ external runtimes

**What iris-devtester DOES NOT**:
- ❌ Run code inside IRIS embedded Python
- ❌ Provide embedded Python utilities
- ❌ Support IRIS-internal testing
- ❌ Deploy Python code to IRIS

### Complementary Tools

For embedded Python use cases, developers should use:
- **InterSystems documentation**: Embedded Python guides
- **IRIS IDE**: VSCode extension for embedded Python development
- **iris-python-suite**: Community tools for embedded Python (if available)

## Connection Type Comparison

| Feature | DBAPI (External) | JDBC (External) | Embedded Python |
|---------|------------------|-----------------|-----------------|
| **Speed** | Fast (3x vs JDBC) | Slower | Fastest (no network) |
| **Network Required** | Yes | Yes | No (in-process) |
| **Use Case** | External apps | External apps (Java) | IRIS-internal code, WSGI apps |
| **Testing with iris-devtester** | ✅ Full support | ✅ Full support | ✅ **For test data setup!** |
| **Production Use** | ✅ External apps | ✅ External apps | ✅ WSGI in IRIS |
| **PyPI Package** | ✅ Yes | ✅ Yes | ❌ No |
| **iris-devtester Primary Support** | ✅ Yes | ✅ Fallback | ⚠️ Testing only |
| **CallIn Required** | ✅ Yes | ❌ No | ❌ No |
| **Installation** | pip install | pip install | Built-in to IRIS |
| **WSGI App Database Access** | ✅ Yes (external) | ✅ Yes (external) | ✅ Yes (embedded - fastest) |
| **WSGI App Testing Setup** | ✅ iris-devtester | ✅ iris-devtester | ✅ **iris-devtester!** |

## Connection Priority (iris-devtester)

```
1. DBAPI (intersystems-irispython)
   ↓ (if unavailable)
2. JDBC (jaydebeapi)
   ↓ (if unavailable)
3. ERROR with clear message
```

**NOT**:
```
❌ 3. Embedded Python (out of scope)
```

## Example: External vs Embedded

### External Python (iris-devtester use case)

```python
# app.py - Running on your laptop/server
from iris_devtester import get_iris_connection

# Connect to IRIS database (network connection)
conn = get_iris_connection()
cursor = conn.cursor()

# Execute query
cursor.execute("SELECT COUNT(*) FROM Users")
count = cursor.fetchone()[0]
print(f"Total users: {count}")

conn.close()
```

**Deployment**:
```bash
pip install iris-devtester
python app.py
# Connects to IRIS over network
```

### Embedded Python (NOT iris-devtester use case)

```objectscript
// MyApp.BusinessLogic.cls - Deployed to IRIS
Class MyApp.BusinessLogic Extends %RegisteredObject [ Language = python ]
{

ClassMethod GetUserCount() As %Integer [ Language = python ]
{
    import iris
    # Already inside IRIS, no connection needed
    rs = iris.sql.exec("SELECT COUNT(*) FROM Users")
    return rs.fetchone()[0]
}

}
```

**Deployment**:
```bash
# Deploy to IRIS
iris session IRIS < import_classes.script
# Code runs INSIDE IRIS when called
```

**Invocation from ObjectScript**:
```objectscript
Set count = ##class(MyApp.BusinessLogic).GetUserCount()
Write "Total users: ", count
```

## FAQ

### Q: Why doesn't iris-devtester support embedded Python?

**A**: Different use case. Embedded Python is for code running **inside** IRIS (stored procedures, business logic). iris-devtester is for external Python applications connecting **to** IRIS (web apps, tests, data pipelines).

### Q: Can I use iris-devtester from embedded Python?

**A**: No, and you don't need to. Embedded Python already has direct IRIS access via the `iris` module. You don't need external connections when you're already inside the database.

### Q: What if I want to test embedded Python code?

**A**: Test embedded Python differently:
1. Deploy to test IRIS instance
2. Call via ObjectScript or REST API
3. Use IRIS unit testing framework
4. Or extract business logic to external Python and test with iris-devtester

### Q: Performance: Embedded vs DBAPI vs JDBC?

**A**: For in-IRIS code, embedded is fastest (no network). For external apps:
- DBAPI: ~2-3ms per query
- JDBC: ~7ms per query
- Embedded: N/A (can't use from external apps)

### Q: Can iris-devtester call embedded Python functions?

**A**: Yes, indirectly via SQL or REST:

```python
# External Python using iris-devtester
from iris_devtester import get_iris_connection

conn = get_iris_connection()
cursor = conn.cursor()

# Call embedded Python stored procedure via SQL
cursor.execute("SELECT MyApp.BusinessLogic_GetUserCount()")
count = cursor.fetchone()[0]
```

Or via REST API if exposed.

### Q: Should I use embedded Python or external Python?

**A**: Depends on use case:

**Use Embedded Python when**:
- Writing IRIS stored procedures
- Building IRIS extensions
- Need zero-latency IRIS internals access
- Code is part of IRIS application

**Use External Python (iris-devtester) when**:
- Building web applications (FastAPI, Django, Flask)
- Writing tests with pytest
- Data science / analytics (Jupyter, pandas)
- ETL / data pipelines
- Microservices architecture
- Need PyPI packages

Most Python developers use **external Python** → **iris-devtester is for you**

## Future Considerations

### Hybrid Scenarios

### Hybrid 1: External App Calling Embedded Functions

Some applications might use **both**:

```python
# External app (uses iris-devtester)
from iris_devtester import get_iris_connection

conn = get_iris_connection()
cursor = conn.cursor()

# Call embedded Python stored procedure for complex calculation
cursor.execute("CALL MyApp.ComplexCalculation(?)", (data,))
result = cursor.fetchone()
```

This is **already supported** by iris-devtester - you just call the stored procedure via SQL.

### Hybrid 2: Testing WSGI Apps Hosted in IRIS ⚠️ KEY USE CASE

**Problem**: You have a Flask/FastAPI app running **inside** IRIS (embedded Python), but you want to **test it externally**:

```python
# app.py - Runs INSIDE IRIS embedded Python
from flask import Flask
import iris

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # Uses embedded Python context
    rs = iris.sql.exec("SELECT * FROM Users")
    return {'users': [dict(row) for row in rs.fetchall()]}
```

**Testing Strategy** - Use iris-devtester for test data setup:

```python
# test_app.py - Runs OUTSIDE IRIS (pytest)
import requests
from iris_devtester import get_iris_connection

def test_get_users_endpoint(iris_db):
    # Use iris-devtester to set up test data
    cursor = iris_db.cursor()
    cursor.execute("INSERT INTO Users (id, name) VALUES (1, 'Alice')")
    iris_db.commit()

    # Test the WSGI app running in IRIS
    response = requests.get('http://localhost:52773/api/users')
    assert response.status_code == 200
    users = response.json()['users']
    assert len(users) == 1
    assert users[0]['name'] == 'Alice'

    # Cleanup handled by iris_db fixture
```

**Why iris-devtester is valuable here**:
- ✅ **Test data setup**: Use iris-devtester to create test data
- ✅ **Test isolation**: Each test gets clean database via fixtures
- ✅ **Cleanup**: Automatic cleanup after tests
- ✅ **CI/CD**: Can run tests in isolated containers
- ✅ **Schema validation**: Ensure schema matches expectations

**The app uses embedded Python, but the tests use iris-devtester!**

### Hybrid 3: Development Workflow for Embedded Apps

Even if your app runs in embedded Python, iris-devtester helps during development:

```python
# Development: Prototype queries externally with iris-devtester
from iris_devtester import get_iris_connection

conn = get_iris_connection()
cursor = conn.cursor()

# Prototype the query
cursor.execute("SELECT * FROM Users WHERE status = 'active'")
print(cursor.fetchall())

# Once working, move to embedded Python app
# app.py:
#   rs = iris.sql.exec("SELECT * FROM Users WHERE status = 'active'")
```

**Benefits**:
- Faster development (no deploy to IRIS needed)
- Interactive REPL/Jupyter testing
- Schema exploration
- Query optimization

Then deploy the working query to embedded Python app.

### Monitoring & Diagnostics

Future enhancement: Detect if IRIS has embedded Python enabled, log informational message:

```python
# Future feature
logger.info("IRIS embedded Python detected: version X.Y.Z")
logger.info("Embedded Python is for IRIS-internal code")
logger.info("iris-devtester provides external connectivity")
```

## Conclusion

### Core Scope

**iris-devtester scope**: External Python connectivity (DBAPI/JDBC)

**Primary focus**:
- Python apps running **outside** IRIS
- Testing infrastructure for **any** IRIS application
- Development tools for query prototyping

**Out of scope for database access**:
- Code running **inside** IRIS embedded Python
- Direct `import iris` module usage
- WSGI apps' internal database access

### The WSGI App Reality

**Key insight**: Even if your **production** app runs in IRIS embedded Python (WSGI), you **still benefit from iris-devtester**:

1. **Testing**: Set up test data, validate schemas, ensure isolation
2. **Development**: Prototype queries interactively before deploying to IRIS
3. **CI/CD**: Automated testing with isolated containers
4. **Debugging**: External tools to inspect database state

**Example workflow**:
```
Development:
  - Use iris-devtester to prototype queries ✅
  - Test queries in Jupyter/REPL ✅

Production:
  - Deploy WSGI app to IRIS (embedded Python)
  - App uses `import iris` for database access

Testing:
  - Use iris-devtester to set up test data ✅
  - Test WSGI app endpoints via HTTP ✅
  - Automatic cleanup via iris-devtester fixtures ✅
```

### Decision Summary

**iris-devtester provides**:
- ✅ External connectivity (DBAPI/JDBC)
- ✅ Testing infrastructure (fixtures, isolation, cleanup)
- ✅ Development tools (prototyping, exploration)
- ✅ **Valuable even for embedded Python apps** (testing!)

**iris-devtester does NOT provide**:
- ❌ Embedded Python runtime support
- ❌ `import iris` module functionality
- ❌ WSGI app internal database access

**Complementary relationship**:
- Production app: May use embedded Python
- Testing/development: Uses iris-devtester
- Both can coexist and complement each other

**Decision final**: Focus on external connectivity for maximum utility across all IRIS development scenarios

---

**References**:
- [InterSystems Embedded Python Documentation](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AEPYTHON)
- [DBAPI vs JDBC Benchmarks](./why-dbapi-first.md)
- [IRIS DevTools Constitution](../../CONSTITUTION.md)

**Version**: 1.0.0
**Ratified**: 2025-10-05
