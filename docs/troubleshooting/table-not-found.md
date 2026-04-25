# Troubleshooting: Table or View Not Found (SQLCODE -30)

**Error**: `ProgrammingError: [SQLCODE: <-30>:<Table or view not found>] [%msg: < Table 'GRAPH_KG.NODES' not found>]`

As of iris-devtester v1.15.1+, SQLCODE -30 automatically wraps as `ConnectionDiagnosticError` with schema visibility info and a suggested fix. If you are on an older version or need to diagnose manually, use the four scenarios below.

---

## Quick Diagnostic (all versions)

```python
from iris_devtester import probe_connection
result = probe_connection(conn)
print(result.report())
# ✓ Connected: localhost:32870 / USER / test
# Schema Graph_KG: 0 tables  ← tells you the problem immediately
```

---

## Scenario 1: Schema Not Seeded (Most Common)

**Symptom**: `Table 'GRAPH_KG.NODES' not found` immediately after connecting.

**Cause**: You connected to the container *before* `initialize_schema()` was called. The `Graph_KG` schema doesn't exist yet. The pytest fixture connection works because fixtures run `initialize_schema()` first — a manual probe before that runs sees nothing.

```
Timeline that produces SQLCODE -30:
  iris.connect(host, port, 'USER', 'test', 'test')   ← lands in empty USER namespace
  cursor.execute("SELECT * FROM Graph_KG.Nodes")      ← -30: Graph_KG doesn't exist yet
  ...later...
  pytest fixture runs initialize_schema()              ← now it exists
  cursor.execute("SELECT * FROM Graph_KG.Nodes")      ← works
```

**Fix**:
```python
from your_package import initialize_schema  # or engine.initialize_schema()
initialize_schema(conn)
cursor.execute("SELECT * FROM Graph_KG.Nodes")   # now works
```

---

## Scenario 2: `_SYSTEM` Password Expired on Fresh Container

**Symptom**: Auth succeeds but any query fails, or `probe_connection()` shows 0 schemas despite schema existing.

**Cause**: Fresh IRIS community containers set `ChangePassword=1` for `_SYSTEM`. The connection appears to succeed but the session is locked.

**Fix**:
```bash
idt test-connection --auto-fix          # auto-detect and reset
idt container reset-password iris_db    # manual reset
```

Or use a non-expired account:
```python
conn = iris.connect(hostname="localhost", port=1972, namespace="USER",
                    username="test", password="test")   # test user not subject to expiry
```

---

## Scenario 3: Schema Not in SQL Search Path

**Symptom**: `Table 'NODES' not found` (unqualified) but `SELECT * FROM Graph_KG.Nodes` works.

**Cause**: IRIS SQL requires fully-qualified table names (`Schema.Table`) unless the schema is in the session search path. `Graph_KG` is not in the default USER search path.

**Fix**: Always fully qualify:
```sql
SELECT * FROM Graph_KG.Nodes WHERE ...
-- NOT: SELECT * FROM Nodes WHERE ...
```

Or set the search path for the session (IRIS SQL):
```sql
SET OPTION EXTRINSIC="Graph_KG"
```

---

## Scenario 4: Probing Outside pytest Before Fixtures Run

**Symptom**: Manual `iris.connect()` in a REPL or script fails even though tests pass.

**Cause**: pytest fixtures run `initialize_schema()` as part of setup. A script connecting to the same container outside pytest misses this setup step.

**Fix**: Use `probe_connection()` to confirm the schema state, then call `initialize_schema()` manually:

```python
from iris_devtester import probe_connection
import iris

conn = iris.connect(hostname="localhost", port=32870, namespace="USER",
                    username="test", password="test")

# Step 1: probe
result = probe_connection(conn)
print(result.report())
# If "Graph_KG: 0 tables" → schema not seeded

# Step 2: seed
from your_package import initialize_schema
initialize_schema(conn)

# Step 3: verify
result2 = probe_connection(conn)
print(result2.report())
# Should show "Graph_KG: N tables"
```

---

## Reference: SQLCODE -23 (CTE Scoping)

`SQLCODE -23: Label not applicable` occurs when a CTE name is used outside its scope or referenced incorrectly. This is distinct from -30 but equally opaque.

**Common cause**: CTE defined in one subquery referenced from a sibling subquery.

```sql
-- WRONG (Graph_KG_cte not in scope for outer SELECT):
WITH Graph_KG_cte AS (SELECT * FROM Graph_KG.Nodes)
SELECT * FROM (SELECT id FROM Graph_KG_cte) sub
JOIN Graph_KG_cte ON sub.id = Graph_KG_cte.id   -- -23 here

-- CORRECT: re-reference the base table or restructure the query
```

iris-devtester wraps -23 with the same `ConnectionDiagnosticError` as -30.
