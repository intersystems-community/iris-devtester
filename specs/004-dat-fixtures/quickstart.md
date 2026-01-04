# Quickstart: IRIS .DAT Fixture Management

**Feature**: 004-dat-fixtures
**Date**: 2025-10-14
**Audience**: IRIS developers writing tests

## Overview

This quickstart walks you through creating, validating, and loading .DAT fixtures for fast, reproducible testing.

**Time**: <5 minutes
**Prerequisites**: IRIS instance running, iris-devtester installed

---

## Installation

```bash
# Install iris-devtester with fixtures support
pip install iris-devtester[fixtures]

# Verify installation
iris-devtester --version
```

---

## Step 1: Start IRIS Container

```bash
# Start IRIS Community edition
docker run -d \
  --name iris_db \
  -p 1972:1972 \
  -p 52773:52773 \
  -e IRIS_PASSWORD=SYS \
  -e IRIS_USERNAME=_SYSTEM \
  intersystems/iris-community:latest

# Wait for IRIS to be ready (~30 seconds)
sleep 30

# Verify IRIS is running
docker logs iris_db | grep "InterSystems IRIS"
```

**Expected output**:
```
InterSystems IRIS for UNIX ... 2024.1 ...
```

---

## Step 2: Create Test Data

Create some test data programmatically (the "slow" way we'll replace with fixtures):

```python
# create_test_data.py
from iris_devtester.connections import get_connection

# Connect to IRIS (auto-discovery)
conn = get_connection()
cursor = conn.cursor()

# Create test table
cursor.execute("""
    CREATE TABLE RAG.Entities (
        ID INT PRIMARY KEY,
        EntityType VARCHAR(50),
        Name VARCHAR(100),
        Description VARCHAR(500)
    )
""")

# Insert 100 test rows
for i in range(100):
    cursor.execute(
        "INSERT INTO RAG.Entities (ID, EntityType, Name, Description) VALUES (?, ?, ?, ?)",
        (i, "Person", f"Entity_{i}", f"Test entity number {i}")
    )

conn.commit()
print("✅ Created 100 test entities")
```

Run it:
```bash
python create_test_data.py
```

**Expected output**:
```
✅ Created 100 test entities
```

**Performance**: ~30 seconds for 100 rows (slow!)

---

## Step 3: Export to Fixture

Now export this test data to a reusable .DAT fixture:

```bash
# Create fixture from USER namespace
iris-devtester fixture create \
  --name test-entities-100 \
  --namespace USER \
  --output ./fixtures/test-entities-100 \
  --description "Test data with 100 RAG entities" \
  --version 1.0.0
```

**Expected output**:
```
Connecting to IRIS...
Backing up namespace USER...
Calculating checksum...
Querying table list...
Writing manifest...

✅ Fixture created: test-entities-100

Location: ./fixtures/test-entities-100
Namespace: USER
Tables: 1
Total rows: 100
Size: 0.45 MB
Time: 2.3s

Next steps:
  1. Validate: iris-devtester fixture validate --fixture ./fixtures/test-entities-100
  2. Load: iris-devtester fixture load --fixture ./fixtures/test-entities-100
  3. Commit to git: git add ./fixtures/test-entities-100
```

**Performance**: <5 seconds for 100 rows

**Fixture contents**:
```bash
ls -la ./fixtures/test-entities-100/
```

Output:
```
-rw-r--r--  manifest.json
-rw-r--r--  IRIS.DAT
```

---

## Step 4: Validate Fixture

Validate the fixture integrity (checksums, manifest):

```bash
iris-devtester fixture validate --fixture ./fixtures/test-entities-100
```

**Expected output**:
```
Loading manifest...
Checking IRIS.DAT file...
Validating checksum...

✅ Fixture is valid: test-entities-100

Fixture: test-entities-100
Version: 1.0.0
Schema: 1.0
Namespace: USER
Tables: 1
Total rows: 100
Size: 0.45 MB

IRIS.DAT checksum: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Tables included:
  - RAG.Entities (100 rows)
```

**Performance**: <2 seconds

---

## Step 5: Clean Database

Clean out the test data to simulate a fresh environment:

```python
# clean_database.py
from iris_devtester.connections import get_connection

conn = get_connection()
cursor = conn.cursor()

# Drop test table
cursor.execute("DROP TABLE RAG.Entities")
conn.commit()

print("✅ Database cleaned")
```

Run it:
```bash
python clean_database.py
```

---

## Step 6: Load Fixture (Fast!)

Now load the fixture back into the database:

```bash
iris-devtester fixture load --fixture ./fixtures/test-entities-100
```

**Expected output**:
```
Validating fixture...
Validating IRIS.DAT checksum...
Mounting namespace...

✅ Fixture loaded: test-entities-100

Namespace: USER
Tables: 1
Total rows: 100
Time: 0.8s

Tables:
  - RAG.Entities (100 rows)

Next steps:
  Run your tests or query the data
```

**Performance**: <1 second for 100 rows (30x faster than programmatic creation!)

---

## Step 7: Verify Data Matches Original

Verify the loaded data matches what we originally created:

```python
# verify_data.py
from iris_devtester.connections import get_connection

conn = get_connection()
cursor = conn.cursor()

# Count rows
cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
count = cursor.fetchone()[0]
print(f"Row count: {count}")

# Check first row
cursor.execute("SELECT * FROM RAG.Entities WHERE ID = 0")
row = cursor.fetchone()
print(f"First row: ID={row[0]}, EntityType={row[1]}, Name={row[2]}")

# Verify all rows
cursor.execute("SELECT ID FROM RAG.Entities ORDER BY ID")
ids = [row[0] for row in cursor.fetchall()]
expected_ids = list(range(100))

if ids == expected_ids:
    print("✅ Data matches original!")
else:
    print("❌ Data mismatch")
```

Run it:
```bash
python verify_data.py
```

**Expected output**:
```
Row count: 100
First row: ID=0, EntityType=Person, Name=Entity_0
✅ Data matches original!
```

---

## Step 8: Use in pytest

Now use the fixture in your pytest tests:

```python
# test_rag_queries.py
import pytest
from iris_devtester.fixtures import DATFixtureLoader

@pytest.fixture(scope="class")
def loaded_fixture():
    """Load test fixture before tests."""
    loader = DATFixtureLoader()
    result = loader.load_fixture("./fixtures/test-entities-100")
    yield result
    # Cleanup after tests
    loader.cleanup_fixture(result.manifest)

class TestRAGQueries:
    def test_entity_count(self, loaded_fixture, iris_db):
        cursor = iris_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        count = cursor.fetchone()[0]
        assert count == 100

    def test_entity_types(self, loaded_fixture, iris_db):
        cursor = iris_db.cursor()
        cursor.execute("SELECT DISTINCT EntityType FROM RAG.Entities")
        types = [row[0] for row in cursor.fetchall()]
        assert types == ["Person"]

    def test_query_by_id(self, loaded_fixture, iris_db):
        cursor = iris_db.cursor()
        cursor.execute("SELECT Name FROM RAG.Entities WHERE ID = 42")
        name = cursor.fetchone()[0]
        assert name == "Entity_42"
```

Run tests:
```bash
pytest test_rag_queries.py -v
```

**Expected output**:
```
test_rag_queries.py::TestRAGQueries::test_entity_count PASSED
test_rag_queries.py::TestRAGQueries::test_entity_types PASSED
test_rag_queries.py::TestRAGQueries::test_query_by_id PASSED

==================== 3 passed in 2.1s ====================
```

**Performance**: Fixture loads in <2s, tests run in <0.1s each

---

## Step 9: Use pytest Decorator (Declarative)

Use the declarative pytest marker for even simpler tests:

```python
# test_rag_queries_declarative.py
import pytest

@pytest.mark.dat_fixture("./fixtures/test-entities-100", scope="class")
class TestRAGQueriesDeclarative:
    """Fixture auto-loads before class, auto-cleans after."""

    def test_entity_count(self, iris_db):
        cursor = iris_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        count = cursor.fetchone()[0]
        assert count == 100

    def test_query_performance(self, iris_db):
        import time
        cursor = iris_db.cursor()

        start = time.time()
        cursor.execute("SELECT * FROM RAG.Entities WHERE EntityType = 'Person'")
        results = cursor.fetchall()
        elapsed = time.time() - start

        assert len(results) == 100
        assert elapsed < 0.1  # Fast query
```

Run tests:
```bash
pytest test_rag_queries_declarative.py -v
```

**Expected output**:
```
test_rag_queries_declarative.py::TestRAGQueriesDeclarative::test_entity_count PASSED
test_rag_queries_declarative.py::TestRAGQueriesDeclarative::test_query_performance PASSED

==================== 2 passed in 1.9s ====================
```

---

## Step 10: Version Control Fixture

Commit the fixture to git for team sharing:

```bash
# Add fixture to git
git add ./fixtures/test-entities-100/

# Check fixture size
du -sh ./fixtures/test-entities-100/
# Output: 464K

# For files >10MB, use Git LFS
# echo "fixtures/**/*.dat filter=lfs diff=lfs merge=lfs -text" >> .gitattributes

# Commit
git commit -m "Add test-entities-100 fixture for RAG integration tests"

# Push to remote
git push origin main
```

**Team benefit**: Other developers can now clone and instantly load this test data without running slow data generation scripts!

---

## Performance Comparison

| Operation | Programmatic (Slow) | Fixture (Fast) | Speedup |
|-----------|---------------------|----------------|---------|
| Create 100 rows | 30s | 2.3s (one-time) | N/A |
| Load 100 rows | 30s | 0.8s | **37x faster** |
| Create 10K rows | ~50 minutes | 20s (one-time) | N/A |
| Load 10K rows | ~50 minutes | <2s | **1500x faster** |

---

## Advanced Usage

### Namespace with Multiple Tables

Create fixture from namespace containing multiple tables:

```bash
iris-devtester fixture create \
  --name rag-full \
  --namespace RAG_PRODUCTION \
  --output ./fixtures/rag-full \
  --description "Complete RAG dataset for integration tests"
```

**Note**: All tables in the namespace will be included in the fixture.

### Load to Different Target Namespace

Load fixture to a different target namespace than the source:

```bash
iris-devtester fixture load \
  --fixture ./fixtures/test-entities-100 \
  --namespace USER_TEST_001
```

**Use case**: Isolate test runs by loading fixtures to unique namespaces.

### List Available Fixtures

```bash
iris-devtester fixture list ./fixtures/
```

Output:
```
Available fixtures in ./fixtures:

  1. test-entities-100 (v1.0.0)
     Description: Test data with 100 RAG entities
     Tables: 1
     Size: 0.45 MB

  2. rag-full (v2.0.0)
     Description: Complete RAG dataset for integration tests
     Tables: 3
     Size: 12.3 MB

Total: 2 fixtures, 12.75 MB
```

### Fixture Info

Get detailed fixture information:

```bash
iris-devtester fixture info --fixture ./fixtures/test-entities-100
```

Output:
```
Fixture: test-entities-100
Version: 1.0.0
Description: Test data with 100 RAG entities
Created: 2025-10-14T15:30:00Z
IRIS Version: 2024.1
Schema Version: 1.0
Namespace: USER

IRIS.DAT:
  Size: 0.43 MB
  Checksum: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

Tables (1):
  - RAG.Entities (100 rows)

Size:
  Total: 0.45 MB
  Manifest: 2.1 KB
  IRIS.DAT: 0.43 MB

Location: ./fixtures/test-entities-100
```

---

## Troubleshooting

### Checksum Mismatch

```bash
# Error: Checksum mismatch for IRIS.DAT
# Fix: Recalculate checksum
iris-devtester fixture validate --fixture ./fixtures/test-entities-100 --recalc
```

### Fixture Load Fails

```bash
# Error: Namespace already exists
# Cause: Target namespace conflicts with existing namespace
# Fix: Load to different target namespace
iris-devtester fixture load \
  --fixture ./fixtures/test-entities-100 \
  --namespace USER_TEST_002
```

### Refresh Fixture After Data Changes

```bash
# Fix: Re-create fixture from current namespace state
iris-devtester fixture create \
  --name test-entities-100 \
  --namespace USER \
  --output ./fixtures/test-entities-100-v2
```

### Connection Issues

```bash
# Error: Failed to connect to IRIS
# Fix: Verify IRIS is running and accessible
docker ps | grep iris_db
docker logs iris_db

# Test connection
iris-devtester connection test
```

---

## Next Steps

1. **Create fixtures for your project**: Export your test data
2. **Commit to git**: Share fixtures with your team
3. **Update tests**: Replace slow data generation with fast fixture loading
4. **Measure improvement**: Track test suite speedup

**Expected improvement**: 80-95% reduction in test setup time

---

## Summary

You've successfully:
- ✅ Installed iris-devtester with fixtures support
- ✅ Created test data programmatically
- ✅ Exported namespace to IRIS.DAT fixture (2.3s)
- ✅ Validated fixture integrity (single checksum)
- ✅ Loaded fixture back to database (0.8s, 37x faster via namespace mounting)
- ✅ Verified data integrity
- ✅ Used fixtures in pytest tests
- ✅ Committed fixture to version control

**Key takeaways**:
- Fixtures are 30-1500x faster than programmatic data creation
- Namespace mounting is near-instant (<1 second)
- Single SHA256 checksum ensures data integrity
- Atomic namespace operations prevent partial state
- Version control enables team sharing
- pytest integration provides declarative usage

**Total time**: <5 minutes ✅

---

## Acceptance Criteria

This quickstart meets the acceptance criteria from spec.md:

- ✅ **Scenario 1**: Created fixture with manifest.json and checksums
- ✅ **Scenario 2**: Loaded fixture in <10s for 100 rows
- ✅ **Scenario 3**: Validated fixture with checksum confirmation
- ✅ **Scenario 4**: Used Python API programmatically
- ✅ **Scenario 5**: Used pytest decorator declaratively
- ✅ **Scenario 6**: Inspected human-readable manifest metadata

---

**Quickstart Complete** - Ready for /tasks command
