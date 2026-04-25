from unittest.mock import MagicMock, patch

import pytest


class TestConnectionProbe:
    def test_returns_connection_probe_with_schemas(self):
        from iris_devtester.diagnostics import ConnectionProbe, probe_connection

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: s
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        cur = MagicMock()
        cur.fetchone.side_effect = [("IRIS for UNIX (Apple M3) 2025.1",), ("USER",)]
        cur.fetchall.return_value = [("Graph_KG", 7), ("SQLUser", 2)]
        mock_conn.cursor.return_value = cur

        result = probe_connection(mock_conn)

        assert isinstance(result, ConnectionProbe)
        assert isinstance(result.schemas, dict)
        assert result.schemas.get("Graph_KG") == 7

    def test_report_returns_string_with_schema_info(self):
        from iris_devtester.diagnostics import ConnectionProbe

        probe = ConnectionProbe(
            host="localhost", port=1972, namespace="USER", username="test",
            iris_version="IRIS 2025.1", schemas={"Graph_KG": 7}, latency_ms=12.3
        )
        report = probe.report()
        assert isinstance(report, str)
        assert "Graph_KG" in report
        assert "7" in report

    def test_report_flags_empty_schemas(self):
        from iris_devtester.diagnostics import ConnectionProbe

        probe = ConnectionProbe(
            host="localhost", port=1972, namespace="USER", username="test",
            iris_version="IRIS 2025.1", schemas={}, latency_ms=5.0
        )
        assert "empty" in probe.report().lower() or "no schema" in probe.report().lower()

    def test_latency_under_200ms_in_unit_context(self):
        from iris_devtester.diagnostics import probe_connection

        cur = MagicMock()
        cur.fetchone.side_effect = [("IRIS 2025.1",), ("USER",)]
        cur.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = cur

        result = probe_connection(mock_conn)
        assert result.latency_ms < 200


class TestConnectionDiagnosticError:
    def test_is_exception_subclass(self):
        from iris_devtester.diagnostics import ConnectionDiagnosticError
        assert issubclass(ConnectionDiagnosticError, Exception)

    def test_carries_sqlcode_probe_and_original(self):
        from iris_devtester.diagnostics import ConnectionDiagnosticError, ConnectionProbe

        probe = ConnectionProbe("h", 1972, "USER", "u", "v", {}, 5.0)
        orig = RuntimeError("orig")
        err = ConnectionDiagnosticError("msg", sqlcode=-30, original=orig, probe=probe)

        assert err.sqlcode == -30
        assert err.original is orig
        assert err.probe is probe

    def test_message_includes_schema_visibility(self):
        from iris_devtester.diagnostics import ConnectionProbe, build_diagnostic_error

        cur = MagicMock()
        cur.fetchone.side_effect = [("IRIS 2025.1",), ("USER",)]
        cur.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = cur

        orig = Exception("[SQLCODE: <-30>:<Table or view not found>][%msg: Table 'Graph_KG.Nodes' not found]")
        err = build_diagnostic_error(orig, mock_conn, -30)

        assert "Graph_KG" in str(err)
        assert "initialize_schema" in str(err).lower()


class TestDiagnosticCursor:
    def _make_cursor(self, sqlcode=None):
        from iris_devtester.connections.cursor_wrapper import DiagnosticCursor

        inner = MagicMock()
        if sqlcode is not None:
            inner.execute.side_effect = Exception(
                f"[SQLCODE: <{sqlcode}>:<Table or view not found>][%msg: Table 'X.Y' not found]"
            )

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        cur_fetch = MagicMock()
        cur_fetch.fetchone.side_effect = [("IRIS 2025.1",), ("USER",)]
        cur_fetch.fetchall.return_value = []
        mock_conn.cursor.return_value = cur_fetch

        return DiagnosticCursor(inner, mock_conn)

    def test_sqlcode_minus30_raises_diagnostic_error(self):
        from iris_devtester.diagnostics import ConnectionDiagnosticError
        cursor = self._make_cursor(sqlcode=-30)
        with pytest.raises(ConnectionDiagnosticError) as exc_info:
            cursor.execute("SELECT * FROM X.Y")
        assert exc_info.value.sqlcode == -30

    def test_sqlcode_minus23_raises_diagnostic_error(self):
        from iris_devtester.diagnostics import ConnectionDiagnosticError
        from iris_devtester.connections.cursor_wrapper import DiagnosticCursor

        inner = MagicMock()
        inner.execute.side_effect = Exception("[SQLCODE: <-23>:<Label not applicable>]")
        mock_conn = MagicMock()
        cur_inner = MagicMock()
        cur_inner.fetchone.side_effect = [("v",), ("USER",)]
        cur_inner.fetchall.return_value = []
        mock_conn.cursor.return_value = cur_inner
        cursor = DiagnosticCursor(inner, mock_conn)

        with pytest.raises(ConnectionDiagnosticError) as exc_info:
            cursor.execute("WITH cte AS (SELECT 1) SELECT * FROM cte JOIN cte c2")
        assert exc_info.value.sqlcode == -23

    def test_other_exceptions_pass_through_unchanged(self):
        from iris_devtester.connections.cursor_wrapper import DiagnosticCursor

        inner = MagicMock()
        inner.execute.side_effect = RuntimeError("unrelated error")
        cursor = DiagnosticCursor(inner, MagicMock())

        with pytest.raises(RuntimeError, match="unrelated error"):
            cursor.execute("SELECT 1")

    def test_delegates_fetchall_to_inner_cursor(self):
        from iris_devtester.connections.cursor_wrapper import DiagnosticCursor

        inner = MagicMock()
        inner.fetchall.return_value = [("row1",), ("row2",)]
        cursor = DiagnosticCursor(inner, MagicMock())

        assert cursor.fetchall() == [("row1",), ("row2",)]


class TestPublicExport:
    def test_probe_connection_importable_from_iris_devtester(self):
        from iris_devtester import probe_connection
        assert callable(probe_connection)


class TestContainerHealthSchemas:
    def test_schemas_defaults_to_none(self):
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
        )
        assert health.schemas is None

    def test_schemas_accepts_dict(self):
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus
        health = ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas={"Graph_KG": 7, "SQLUser": 0},
        )
        assert health.schemas["Graph_KG"] == 7
