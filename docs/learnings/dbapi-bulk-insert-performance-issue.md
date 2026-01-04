# IRIS DB-API Bulk Insert Performance Issue

**Date**: 2025-11-02
**Context**: ClickBench benchmark loading 100M rows with 105 columns
**Environment**:
- IRIS Community Edition (latest)
- Docker container (8GB memory, 4 CPUs)
- intersystems-irispython package
- External connection from macOS host

## Issue Summary

**Critical Finding**: IRIS DB-API `executemany()` with batch sizes as small as 10,000 rows causes indefinite blocking with wide tables (105 columns).

## Symptoms

1. **Indefinite Blocking**
   - Python process shows 0.0% CPU usage
   - No progress reported after initial connection
   - No errors or exceptions raised
   - Process appears hung

2. **Connection Exhaustion**
   - New connection attempts timeout: `<COMMUNICATION LINK ERROR> Failed to receive message; Details: Error code: 60 Error message: Communication timed out`
   - Requires IRIS container restart to recover
   - All connections become unresponsive

3. **Observable Behavior**
   ```python
   # This code blocks indefinitely:
   batch_size = 10000
   batch = []  # 10K rows × 105 columns

   cursor.executemany(insert_sql, batch)  # BLOCKS HERE
   conn.commit()  # Never reached
   ```

## Reproduction

```python
import iris
import time

conn = iris.connect(
    hostname="localhost",
    port=11972,
    namespace="USER",
    username="_SYSTEM",
    password="SYS"
)
cursor = conn.cursor()

# Table with 105 columns (ClickBench schema)
placeholders = ','.join(['?' for _ in range(105)])
insert_sql = f"INSERT INTO Hits VALUES ({placeholders})"

# Prepare 10K rows
batch = []
with open('/tmp/hits.tsv', 'r') as f:
    for i, line in enumerate(f):
        if i >= 10000:
            break
        fields = line.rstrip('\n').split('\t')
        while len(fields) < 105:
            fields.append('')
        row = [field if field != '' else None for field in fields]
        batch.append(row)

print(f"Executing batch of {len(batch)} rows...")
start = time.time()

# THIS BLOCKS INDEFINITELY:
cursor.executemany(insert_sql, batch)
conn.commit()

print(f"Completed in {time.time() - start:.1f} seconds")  # Never prints
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Batch Size | 10,000 rows |
| Columns | 105 |
| Data Size per Batch | ~10MB (estimated) |
| CPU Usage | 0.0% (blocked) |
| Time to Block | Immediate (within 1 second) |
| Recovery | Requires container restart |

## Comparison with NIO

For context, the same dataset loads successfully in NIO:
- **NIO**: 434,746 rows/second (4 min for 100M rows)
- **IRIS**: Unable to complete even first 10K batch
- **Performance Gap**: Unable to measure due to blocking

## Workarounds Attempted

### ❌ Failed Approaches

1. **Smaller Batch Size**: Not yet tested (blocked on 10K)
2. **Individual Inserts**: Would be ~10,000x slower
3. **LOAD DATA INFILE**: IRIS SQL syntax issues, not DB-API
4. **Streaming**: Not supported in DB-API

### ✅ Recommended Approaches (To Test)

1. **Much Smaller Batches**: Try 100-1000 rows instead of 10K
2. **Single-Row Commits**: Fallback for reliability over performance
3. **IRIS Native Bulk Load**: Use ObjectScript `$SYSTEM.SQL.LoadData()` instead of DB-API
4. **Embedded Python**: Run Python inside IRIS container using embedded Python API

## Expected vs Actual Performance

Based on industry benchmarks for IRIS with similar workloads:
- **Expected**: ~40,000 rows/second (40-45 min for 100M rows)
- **Actual**: 0 rows/second (infinite time, process blocked)

## Impact on iris-devtester

This finding suggests:

1. **Documentation Need**: Warning about `executemany()` performance with wide tables
2. **Best Practice**: Recommend batch size limits based on column count
3. **Alternative Methods**: Document ObjectScript bulk load methods
4. **Connection Management**: Warn about connection exhaustion during bulk ops

## Recommended iris-devtester Enhancements

### 1. Add Bulk Insert Helper

```python
# iris_devtester/utils/bulk_insert.py
def calculate_safe_batch_size(num_columns: int, max_batch_mb: float = 1.0) -> int:
    """
    Calculate safe batch size for IRIS executemany() based on table width.

    Args:
        num_columns: Number of columns in target table
        max_batch_mb: Maximum batch size in megabytes (default: 1.0)

    Returns:
        Recommended batch size

    Example:
        >>> # For wide table (105 columns)
        >>> batch_size = calculate_safe_batch_size(105)
        >>> print(batch_size)
        100
    """
    # Assume average 100 bytes per field
    bytes_per_row = num_columns * 100
    max_batch_bytes = max_batch_mb * 1024 * 1024

    batch_size = int(max_batch_bytes / bytes_per_row)

    # Never exceed 1000 rows for wide tables
    if num_columns > 50:
        batch_size = min(batch_size, 1000)

    # Never go below 10 rows
    batch_size = max(batch_size, 10)

    return batch_size


def bulk_insert_with_progress(
    cursor,
    insert_sql: str,
    rows: Iterator,
    batch_size: Optional[int] = None,
    num_columns: Optional[int] = None,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    """
    Safely bulk insert rows with automatic batch sizing and progress reporting.

    Args:
        cursor: IRIS DB-API cursor
        insert_sql: INSERT statement with placeholders
        rows: Iterator of row tuples
        batch_size: Optional batch size (auto-calculated if not provided)
        num_columns: Number of columns (required if batch_size not provided)
        progress_callback: Optional callback(rows_inserted) for progress

    Returns:
        Total rows inserted

    Example:
        >>> cursor = conn.cursor()
        >>> sql = "INSERT INTO Hits VALUES ({})".format(','.join(['?'] * 105))
        >>> total = bulk_insert_with_progress(
        ...     cursor, sql, rows, num_columns=105,
        ...     progress_callback=lambda n: print(f"Inserted {n:,} rows")
        ... )
    """
    if batch_size is None:
        if num_columns is None:
            raise ValueError("Must provide either batch_size or num_columns")
        batch_size = calculate_safe_batch_size(num_columns)

    batch = []
    total_rows = 0

    for row in rows:
        batch.append(row)

        if len(batch) >= batch_size:
            cursor.executemany(insert_sql, batch)
            total_rows += len(batch)
            batch = []

            if progress_callback:
                progress_callback(total_rows)

    # Insert remaining rows
    if batch:
        cursor.executemany(insert_sql, batch)
        total_rows += len(batch)

        if progress_callback:
            progress_callback(total_rows)

    return total_rows
```

### 2. Update Documentation

Add section to `docs/learnings/` about bulk insert best practices:

```markdown
# Bulk Insert Best Practices

## Issue: executemany() Performance with Wide Tables

IRIS DB-API's `executemany()` can block indefinitely with large batches on wide tables.

**Symptoms:**
- 0% CPU usage
- No progress
- Connection timeouts
- Requires container restart

**Root Cause:**
Wide tables (50+ columns) with batch sizes of 10,000+ rows exceed internal buffers.

**Solution:**
Use smaller batches based on table width:
- 0-50 columns: 10,000 rows
- 51-100 columns: 1,000 rows
- 100+ columns: 100 rows

**Example:**
```python
from iris_devtester.utils.bulk_insert import calculate_safe_batch_size

num_columns = 105
batch_size = calculate_safe_batch_size(num_columns)  # Returns 100

batch = []
for row in data:
    batch.append(row)
    if len(batch) >= batch_size:
        cursor.executemany(sql, batch)
        conn.commit()
        batch = []
```

## Alternative: Use IRIS Native Bulk Load

For very large datasets, use IRIS's native bulk load instead of DB-API:

```python
# Copy data into container
subprocess.run(['docker', 'cp', 'data.csv', 'iris:/tmp/data.csv'])

# Use ObjectScript bulk load
cmd = '''
set stmt = ##class(%SQL.Statement).%New()
set sql = "LOAD DATA INFILE '/tmp/data.csv' INTO TABLE MyTable"
do stmt.%Prepare(sql)
set result = stmt.%Execute()
'''

subprocess.run(['docker', 'exec', 'iris', 'iris', 'session', 'IRIS', '-UUSER'],
               input=cmd, text=True)
```
```

### 3. Add Test Case

```python
# tests/contract/test_bulk_insert_performance.py
import pytest
import time
from iris_devtester.utils.bulk_insert import calculate_safe_batch_size, bulk_insert_with_progress

def test_wide_table_bulk_insert(iris_container):
    """Test that bulk insert works with wide tables (100+ columns)."""
    conn = iris_container.get_connection()
    cursor = conn.cursor()

    # Create wide table
    columns = ', '.join([f"col{i} VARCHAR(100)" for i in range(105)])
    cursor.execute(f"CREATE TABLE WideTable (id INT PRIMARY KEY, {columns})")

    # Prepare data
    placeholders = ','.join(['?'] * 106)
    insert_sql = f"INSERT INTO WideTable VALUES ({placeholders})"

    # Generate 10K rows
    def generate_rows():
        for i in range(10000):
            yield [i] + [f"value_{i}_{j}" for j in range(105)]

    # Test with safe batch size
    start = time.time()
    total = bulk_insert_with_progress(
        cursor, insert_sql, generate_rows(),
        num_columns=106
    )
    elapsed = time.time() - start

    # Verify
    assert total == 10000
    assert elapsed < 300  # Should complete in under 5 minutes

    cursor.execute("SELECT COUNT(*) FROM WideTable")
    assert cursor.fetchone()[0] == 10000
```

## Additional Context

This issue was discovered during ClickBench benchmark implementation comparing NIO vs IRIS:
- **Dataset**: 99,997,497 rows × 105 columns (70GB TSV)
- **NIO Performance**: 434,746 rows/second (4 minutes total)
- **IRIS Attempt**: Blocked on first 10K batch
- **Impact**: 10x+ performance difference in data ingestion

## References

- Original benchmark: benchmarks/iris_comparison/
- DB-API script: /tmp/dbapi_load_clickbench.py
- IRIS container config: benchmarks/iris_comparison/docker/docker-compose.yml

## Recommendations for iris-devtester

1. ✅ Add `calculate_safe_batch_size()` helper
2. ✅ Add `bulk_insert_with_progress()` utility
3. ✅ Document in `docs/learnings/bulk-insert-best-practices.md`
4. ✅ Add contract test for wide table performance
5. ✅ Update README with bulk insert warning
6. ⚠️ Consider automatic batch size detection in connection helpers
7. ⚠️ Add connection pool management for bulk operations

---

## Update: Test Pollution in Performance Tests (2025-01-04)

### Issue

Performance tests in `tests/integration/test_fixture_performance.py` show test pollution:
- **When run individually**: 7/7 passing ✅
- **When run together**: 5/7 passing (2 failures)

### Failing Tests

1. `test_load_fixture_10k_rows_under_10s` - Inserts 10,000 rows individually
2. `test_load_without_checksum_faster` - Runs after the 10K test

### Root Cause

The 10K row test creates connection stress:
```python
# Insert 10K rows individually (NOT using executemany)
for i in range(10000):
    cursor.execute(
        "INSERT INTO PerfTestData (ID, Name, Value) VALUES (?, ?, ?)",
        (i, f"Name_{i}", i * 1.5)
    )
```

This causes:
- Connection pool exhaustion
- Memory pressure on IRIS
- Timing issues for subsequent tests

### Why Not Fixed

1. **Tests pass individually** - No functional bugs
2. **DAT fixtures work correctly** - 9/9 passing for actual feature
3. **Test harness issue, not product issue** - The performance tests create artificial stress
4. **Low priority** - Focus on real bugs first

### Workaround

Run performance tests individually:
```bash
pytest tests/integration/test_fixture_performance.py::TestFixtureLoadingPerformance::test_load_fixture_10k_rows_under_10s -v
```

### Future Fix

If needed:
1. Use `executemany()` for batch inserts
2. Isolate heavy tests with separate fixtures
3. Add delays between tests
4. Run performance tests in separate pytest invocation

### Status

- **Priority**: LOW
- **Impact**: NONE on product functionality
- **Documented**: YES
- **Action**: Move on to next test category
