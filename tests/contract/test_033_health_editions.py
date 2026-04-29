from unittest.mock import MagicMock, patch
import pytest


class TestHealthFactory:
    def test_health_factory_uses_irishealth_community_image(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.health()
        assert "irishealth-community" in iris.image

    def test_health_factory_sets_edition(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.health()
        assert iris._edition == "health"

    def test_health_factory_accepts_version(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.health(version="2024.1")
        assert "2024.1" in iris.image

    def test_health_factory_accepts_image_override(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.health(image="custom/irishealth:test")
        assert iris.image == "custom/irishealth:test"


class TestAiHubFactory:
    def test_ai_hub_uses_internal_registry(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub()
        assert "docker.iscinternal.com" in iris.image

    def test_ai_hub_default_build_159(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub()
        assert "159" in iris.image

    def test_ai_hub_build_override(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub(build="200")
        assert "200" in iris.image

    def test_ai_hub_defaults_to_tmpfs(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub()
        assert iris._use_tmpfs_durable is True
        assert iris._durable_path is None

    def test_ai_hub_accepts_durable_path(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub(durable_path="/data/durable")
        assert iris._durable_path == "/data/durable"
        assert iris._use_tmpfs_durable is False

    def test_ai_hub_sets_edition(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub()
        assert iris._edition == "ai_hub"

    def test_ai_hub_accepts_image_override(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.ai_hub(image="custom/ai:test")
        assert iris.image == "custom/ai:test"


class TestFHIRContainerHealth:
    def _make_health(self, **kwargs):
        from iris_devtester.containers.models import FHIRContainerHealth
        defaults = dict(container_name="iris_db", accessible=True, endpoint="http://localhost:52773/csp/healthshare/demo/fhir/r4")
        defaults.update(kwargs)
        return FHIRContainerHealth(**defaults)

    def test_ready_true_when_accessible_and_fhir_version_set(self):
        h = self._make_health(fhir_version="4.0.1", resource_types_count=148)
        assert h.ready is True

    def test_ready_false_when_not_accessible(self):
        h = self._make_health(accessible=False)
        assert h.ready is False

    def test_ready_false_when_fhir_version_missing(self):
        h = self._make_health(fhir_version=None)
        assert h.ready is False

    def test_report_includes_fhir_version(self):
        h = self._make_health(fhir_version="4.0.1", resource_types_count=148)
        assert "4.0.1" in h.report()
        assert "148" in h.report()

    def test_report_warns_when_not_accessible(self):
        h = self._make_health(accessible=False, fhir_version=None)
        report = h.report().lower()
        assert "not reachable" in report or "warning" in report or "foundation" in report


class TestFHIRReadyWaitStrategy:
    def test_strategy_instantiates(self):
        from iris_devtester.containers.wait_strategies import FHIRReadyWaitStrategy
        s = FHIRReadyWaitStrategy(timeout=30)
        assert s.timeout == 30
        assert s.web_port == 52773
        assert s.superserver_port == 1972


class TestFHIRHealthCheck:
    def test_fhir_health_check_method_exists(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.health()
        assert callable(getattr(iris, "fhir_health_check", None))

    def test_fhir_health_check_returns_fhir_container_health_on_success(self):
        from iris_devtester.containers.iris_container import IRISContainer
        from iris_devtester.containers.models import FHIRContainerHealth
        import json

        iris = IRISContainer.health()
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "fhirVersion": "4.0.1",
            "rest": [{"resource": [{"type": "Patient"}, {"type": "Observation"}]}]
        }).encode()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(iris, "get_container_host_ip", return_value="localhost"), \
             patch.object(iris, "get_container_name", return_value="iris_db"), \
             patch.object(iris, "get_mapped_port", return_value=52773), \
             patch("urllib.request.urlopen", return_value=mock_response):
            result = iris.fhir_health_check()

        assert isinstance(result, FHIRContainerHealth)
        assert result.fhir_version == "4.0.1"
        assert result.resource_types_count == 2
        assert result.ready is True

    def test_fhir_health_check_returns_inaccessible_on_error(self):
        from iris_devtester.containers.iris_container import IRISContainer
        import urllib.error

        iris = IRISContainer.health()
        with patch.object(iris, "get_container_host_ip", return_value="localhost"), \
             patch.object(iris, "get_container_name", return_value="iris_db"), \
             patch.object(iris, "get_mapped_port", return_value=52773), \
             patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            result = iris.fhir_health_check()

        assert result.accessible is False
        assert result.ready is False
        assert result.error is not None
