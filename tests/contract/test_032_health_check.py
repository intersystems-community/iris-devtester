import pytest


class TestContainerHealthExtensions:
    def _make_health(self, schemas=None):
        from iris_devtester.containers.models import ContainerHealth, ContainerHealthStatus
        return ContainerHealth(
            container_name="iris_db",
            status=ContainerHealthStatus.HEALTHY,
            running=True,
            accessible=True,
            docker_sdk_version="6.1.0",
            schemas=schemas,
        )

    def test_tables_visible_false_when_schemas_empty(self):
        assert self._make_health(schemas={}).tables_visible is False

    def test_tables_visible_false_when_schemas_none(self):
        assert self._make_health(schemas=None).tables_visible is False

    def test_tables_visible_true_when_schemas_populated(self):
        assert self._make_health(schemas={"Graph_KG": 7}).tables_visible is True

    def test_report_includes_warning_on_empty_schemas(self):
        report = self._make_health(schemas={}).report()
        assert any(w in report.lower() for w in ("no schema", "not visible", "warning", "initialize"))

    def test_report_includes_schema_names_when_present(self):
        report = self._make_health(schemas={"Graph_KG": 7, "SQLUser": 2}).report()
        assert "Graph_KG" in report
        assert "7" in report

    def test_to_dict_includes_schemas(self):
        health = self._make_health(schemas={"Graph_KG": 7})
        d = health.to_dict()
        assert "schemas" in d
        assert d["schemas"] == {"Graph_KG": 7}

    def test_report_indicates_probe_not_run_when_none(self):
        report = self._make_health(schemas=None).report()
        assert "probe" in report.lower() or "not run" in report.lower()


class TestTopLevelImports:
    def test_container_health_importable(self):
        from iris_devtester import ContainerHealth
        assert ContainerHealth is not None

    def test_connection_diagnostic_error_importable(self):
        from iris_devtester import ConnectionDiagnosticError
        assert ConnectionDiagnosticError is not None

    def test_connection_probe_importable(self):
        from iris_devtester import ConnectionProbe
        assert ConnectionProbe is not None

    def test_all_exports_present(self):
        import iris_devtester
        for name in ("ContainerHealth", "ConnectionDiagnosticError", "ConnectionProbe", "probe_connection"):
            assert name in iris_devtester.__all__, f"{name} missing from __all__"


class TestIRISContainerHealthCheck:
    def test_health_check_method_exists(self):
        from iris_devtester import IRISContainer
        assert callable(getattr(IRISContainer, "health_check", None))

    def test_health_check_returns_container_health(self):
        from unittest.mock import MagicMock, patch
        from iris_devtester import IRISContainer
        from iris_devtester.diagnostics import ConnectionProbe

        iris = IRISContainer.community()
        mock_conn = MagicMock()
        mock_probe = ConnectionProbe(
            host="localhost", port=1972, namespace="USER", username="test",
            iris_version="IRIS 2025.1", schemas={"Graph_KG": 7}, latency_ms=10.0
        )

        with patch.object(iris, "get_connection", return_value=mock_conn), \
             patch("iris_devtester.diagnostics.probe_connection", return_value=mock_probe):
            result = iris.health_check()

        from iris_devtester import ContainerHealth
        assert isinstance(result, ContainerHealth)
        assert result.schemas == {"Graph_KG": 7}
        assert result.tables_visible is True
