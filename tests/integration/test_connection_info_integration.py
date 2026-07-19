"""Integration tests for IRISContainer.connection_info().

Verifies the handoff contract against a real community IRIS container. A plain
community container has no WebGateway sidecar, so the authoritative result is
docker_only=True with a live host-mapped SuperServer port.
"""

import pytest

from iris_devtester.containers import IRISConnectionInfo

pytestmark = pytest.mark.integration


class TestConnectionInfoIntegration:
    """connection_info() against a real container (community, no WebGateway)."""

    def test_community_container_is_docker_only(self, iris_container):
        info = iris_container.connection_info()

        assert isinstance(info, IRISConnectionInfo)
        # Community edition has no WebGateway container -> docker_only.
        assert info.docker_only is True
        assert info.webgateway_url is None
        assert info.webgateway_container is None

    def test_reports_live_connection_details(self, iris_container):
        info = iris_container.connection_info()

        assert info.container == iris_container.get_container_name()
        assert info.superserver_port == iris_container.get_mapped_port(1972)
        assert info.superserver_port > 0
        assert info.host
        assert "iris" in info.iris_image.lower()
        # Credentials mirror the container's current state.
        assert info.namespace == iris_container._namespace
        assert info.username == iris_container._username
        assert info.password == iris_container._password

    def test_toml_snippet_is_docker_only(self, iris_container):
        snippet = iris_container.connection_info().to_toml_snippet()

        assert f'container = "{iris_container.get_container_name()}"' in snippet
        assert "docker_only = true" in snippet
        assert "web_port" not in snippet

    def test_toml_snippet_round_trips(self, iris_container):
        try:
            import tomllib
        except ModuleNotFoundError:
            pytest.skip("tomllib not available (<3.11)")

        snippet = iris_container.connection_info().to_toml_snippet()
        parsed = tomllib.loads(snippet)
        assert parsed["container"] == iris_container.get_container_name()
        assert parsed["docker_only"] is True
