import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

_SQLCODE_MESSAGES = {
    -30: "Table or view not found",
    -23: "Label not applicable (CTE scoping error)",
}


@dataclass
class ConnectionProbe:
    host: str
    port: int
    namespace: str
    username: str
    iris_version: str
    schemas: dict
    latency_ms: float
    error: Optional[str] = None

    def report(self) -> str:
        lines = [
            f"✓ Connected: {self.host}:{self.port} / {self.namespace} / {self.username}",
            f"  IRIS version: {self.iris_version}",
            f"  Probe latency: {self.latency_ms:.1f}ms",
        ]
        if self.schemas:
            for schema, count in sorted(self.schemas.items()):
                lines.append(f"  Schema {schema}: {count} table(s)")
        else:
            lines.append("  No schemas visible (namespace may be empty)")
        if self.error:
            lines.append(f"  Probe error: {self.error}")
        return "\n".join(lines)


class ConnectionDiagnosticError(Exception):
    def __init__(self, message: str, sqlcode: int, original: Exception, probe: ConnectionProbe):
        super().__init__(message)
        self.sqlcode = sqlcode
        self.original = original
        self.probe = probe


def _extract_sqlcode(error_text: str) -> Optional[int]:
    import re
    m = re.search(r"SQLCODE:\s*<(-\d+)>", error_text)
    return int(m.group(1)) if m else None


def _extract_table_name(error_text: str) -> Optional[str]:
    import re
    m = re.search(r"Table '([^']+)' not found", error_text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"table or view not found[^']*'([^']+)'", error_text, re.IGNORECASE)
    return m.group(1) if m else None


def probe_connection(conn: Any) -> ConnectionProbe:
    t0 = time.monotonic()
    host, port, namespace, username, iris_version = "unknown", 0, "USER", "unknown", "unknown"
    schemas: dict = {}
    error: Optional[str] = None

    try:
        cur = conn.cursor()

        cur.execute("SELECT $ZVERSION")
        row = cur.fetchone()
        if row:
            iris_version = str(row[0])

        cur.execute(
            "SELECT TABLE_SCHEMA, COUNT(*) AS cnt "
            "FROM INFORMATION_SCHEMA.TABLES "
            "GROUP BY TABLE_SCHEMA"
        )
        for schema_row in cur.fetchall():
            schemas[schema_row[0]] = int(schema_row[1])

        cur.execute("SELECT $NAMESPACE")
        row = cur.fetchone()
        if row:
            namespace = str(row[0])

        try:
            ci = conn.connection_info if hasattr(conn, "connection_info") else None
            if ci:
                host = getattr(ci, "hostname", host)
                port = getattr(ci, "port", port)
        except Exception:
            pass

    except Exception as e:
        error = str(e)

    latency_ms = (time.monotonic() - t0) * 1000
    return ConnectionProbe(
        host=host,
        port=port,
        namespace=namespace,
        username=username,
        iris_version=iris_version,
        schemas=schemas,
        latency_ms=latency_ms,
        error=error,
    )


def build_diagnostic_error(
    original: Exception, conn: Any, sqlcode: int
) -> ConnectionDiagnosticError:
    probe = probe_connection(conn)
    error_text = str(original)
    table_name = _extract_table_name(error_text)

    schema_name = None
    if table_name and "." in table_name:
        schema_name = table_name.split(".")[0]

    if sqlcode == -30:
        if schema_name and schema_name not in probe.schemas:
            cause = (
                f"Schema '{schema_name}' is NOT VISIBLE on this connection "
                f"({len(probe.schemas)} schema(s) visible: {sorted(probe.schemas) or 'none'}).\n"
                f"  Most likely cause: initialize_schema() has not been called yet.\n"
                f"  Fix: call initialize_schema() or engine.initialize_schema() before running queries."
            )
        elif not probe.schemas:
            cause = (
                "No schemas visible on this connection — namespace appears empty.\n"
                "  Most likely cause: initialize_schema() has not been called yet.\n"
                "  Fix: call initialize_schema() before running queries.\n"
                "  Probe: use probe_connection(conn).report() to inspect schema state."
            )
        else:
            cause = (
                f"Table {table_name!r} not found.\n"
                f"  Visible schemas: {sorted(probe.schemas)}\n"
                "  Check: table name correct? schema fully qualified? correct namespace?"
            )
    else:
        cause = (
            f"SQLCODE {sqlcode}: {_SQLCODE_MESSAGES.get(sqlcode, 'SQL error')}\n"
            f"  Original: {error_text}"
        )

    message = (
        f"ConnectionDiagnosticError (SQLCODE {sqlcode}): {_SQLCODE_MESSAGES.get(sqlcode, 'SQL error')}\n\n"
        f"Diagnostic:\n  {cause}\n\n"
        f"Connection state:\n{probe.report()}\n\n"
        f"Original error: {error_text}"
    )
    return ConnectionDiagnosticError(message, sqlcode=sqlcode, original=original, probe=probe)
