# Why Not SQL/DBAPI for Namespace Existence Check?

**Date**: 2026-02-27
**Feature**: 027-fix-namespace-lookup
**Category**: Blind Alley

## What We Tried

Using `cursor.execute("SELECT COUNT(*) FROM %SYS.Namespace WHERE ...")` via DBAPI
to check if an IRIS namespace exists, as an alternative to Docker exec.

## Why It Didn't Work

1. **Constitution Principle 2** explicitly mandates `iris.connect()` for namespace
   operations — not DBAPI/SQL. The `docs/SQL_VS_OBJECTSCRIPT.md` decision matrix
   classifies namespace create/delete as `iris.connect()` operations.

2. The `%SYS.Namespace` table column names were never validated in the codebase.
   The only example (`SELECT COUNT(*) FROM %SYS.Namespace` in
   `examples/02_connection_management.py`) counts all rows — it never queries
   by namespace name, so the column schema is unconfirmed.

3. The canonical IRIS API for checking namespace existence is
   `##class(Config.Namespaces).Exists(name)` — an ObjectScript class method.
   The `iris.connect()` equivalent (`classMethodValue("Config.Namespaces", "Exists", name)`)
   is a direct 1:1 translation of the Docker exec pattern already in use.

4. Using DBAPI would require connecting to `%SYS` via DBAPI, which has different
   connection semantics than `iris.connect()`.

## What We Use Instead

`iris.connect()` to `%SYS` + `iris.createIRIS()` +
`classMethodValue("Config.Namespaces", "Exists", namespace_name)`

This is the direct programmatic equivalent of the Docker exec ObjectScript
that was already working. It's consistent with the constitution, uses the
official API, and has been validated in the codebase.

## Evidence

- Constitution Principle 2: "Use iris.connect() for ObjectScript operations (namespaces, Task Manager, globals)"
- `docs/SQL_VS_OBJECTSCRIPT.md` lines 80-81: namespace operations → iris.connect()
- Existing Docker exec uses same ObjectScript: `namespace.py` line 41
- Research documented in `specs/027-fix-namespace-lookup/research.md` R1, R6
