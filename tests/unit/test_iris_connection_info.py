"""Unit tests for IRISConnectionInfo handoff contract and WebGateway detection.

Tests the iris-devtester -> iris-agentic-dev handoff contract:
- IRISConnectionInfo dataclass shape and defaults
- to_toml_snippet() emitting a valid .iris-agentic-dev.toml fragment
- WebGateway auto-detection via mocked Docker API
- docker_only semantics

Docker interactions are fully mocked; no container required.
"""

from unittest.mock import MagicMock

import pytest

from iris_devtester.containers.connection_info import (
    IRISConnectionInfo,
    detect_webgateway,
)


def _fake_container(name, image_tags, port_bindings=None, network_names=None):
    """Build a MagicMock resembling a docker-py Container."""
    c = MagicMock()
    c.name = name
    c.image.tags = image_tags
    networks = {n: {} for n in (network_names or ["bridge"])}
    c.attrs = {
        "NetworkSettings": {
            "Networks": networks,
            "Ports": port_bindings or {},
        }
    }
    return c


class TestIRISConnectionInfoDataclass:
    """The dataclass shape is the shared contract with iad."""

    def test_defaults(self):
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="iris_db",
            iris_image="intersystemsdc/iris-community:latest",
        )
        assert info.namespace == "USER"
        assert info.username == "_SYSTEM"
        assert info.password == "SYS"
        assert info.webgateway_url is None
        assert info.webgateway_container is None
        assert info.docker_only is True

    def test_docker_only_false_when_webgateway_present(self):
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="iris_db",
            iris_image="img",
            webgateway_url="http://localhost:52774",
            webgateway_container="my-webgateway",
        )
        assert info.docker_only is False

    def test_docker_only_explicit_override_respected(self):
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="iris_db",
            iris_image="img",
            webgateway_url="http://localhost:52774",
            docker_only=True,
        )
        assert info.docker_only is True


class TestToTomlSnippet:
    """to_toml_snippet() -> a .iris-agentic-dev.toml fragment iad hot-reloads."""

    def test_docker_only_snippet(self):
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="opsreview-iris",
            iris_image="img",
            namespace="USER",
        )
        snippet = info.to_toml_snippet()
        assert 'container = "opsreview-iris"' in snippet
        assert "docker_only = true" in snippet
        assert 'namespace = "USER"' in snippet
        assert "web_port" not in snippet

    def test_webgateway_snippet_emits_web_port(self):
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="opsreview-iris",
            iris_image="img",
            namespace="USER",
            webgateway_url="http://localhost:8080",
            webgateway_container="opsreview-webgateway",
        )
        snippet = info.to_toml_snippet()
        assert 'container = "opsreview-iris"' in snippet
        assert "web_port = 8080" in snippet
        assert "docker_only = false" in snippet
        assert 'namespace = "USER"' in snippet

    def test_snippet_falls_back_to_docker_only_when_url_has_no_port(self):
        # docker_only=False but a malformed URL yields no port: must NOT emit
        # "docker_only = false" with no web_port for iad to connect to.
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="c",
            iris_image="img",
            webgateway_url="http://localhost",  # no port
            docker_only=False,
        )
        snippet = info.to_toml_snippet()
        assert "docker_only = true" in snippet
        assert "web_port" not in snippet

    def test_snippet_is_parseable_toml(self):
        try:
            import tomllib  # py311+
        except ModuleNotFoundError:
            pytest.skip("tomllib not available (<3.11)")
        info = IRISConnectionInfo(
            host="localhost",
            superserver_port=1972,
            container="c",
            iris_image="img",
            webgateway_url="http://localhost:52774",
        )
        parsed = tomllib.loads(info.to_toml_snippet())
        assert parsed["container"] == "c"
        assert parsed["web_port"] == 52774
        assert parsed["docker_only"] is False


class TestDetectWebGateway:
    """Auto-detection: containers on the same network with */webgateway* image."""

    def test_detects_webgateway_on_shared_network(self):
        client = MagicMock()
        wg = _fake_container(
            name="proj-webgateway",
            image_tags=["containers.intersystems.com/intersystems/webgateway:latest-cd"],
            port_bindings={"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "52774"}]},
            network_names=["proj_default"],
        )
        client.containers.list.return_value = [wg]

        url, name = detect_webgateway(client, iris_networks={"proj_default"}, host="localhost")
        assert url == "http://localhost:52774"
        assert name == "proj-webgateway"

    def test_no_webgateway_returns_none(self):
        client = MagicMock()
        other = _fake_container(
            name="some-app",
            image_tags=["nginx:latest"],
            network_names=["proj_default"],
        )
        client.containers.list.return_value = [other]

        url, name = detect_webgateway(client, iris_networks={"proj_default"}, host="localhost")
        assert url is None
        assert name is None

    def test_webgateway_on_different_network_ignored(self):
        client = MagicMock()
        wg = _fake_container(
            name="unrelated-webgateway",
            image_tags=["myrepo/webgateway:1.0"],
            port_bindings={"80/tcp": [{"HostPort": "9999"}]},
            network_names=["other_net"],
        )
        client.containers.list.return_value = [wg]

        url, name = detect_webgateway(client, iris_networks={"proj_default"}, host="localhost")
        assert url is None
        assert name is None

    def test_first_match_wins(self):
        client = MagicMock()
        wg1 = _fake_container(
            name="wg-one",
            image_tags=["x/webgateway:a"],
            port_bindings={"80/tcp": [{"HostPort": "1111"}]},
            network_names=["net"],
        )
        wg2 = _fake_container(
            name="wg-two",
            image_tags=["x/webgateway:b"],
            port_bindings={"80/tcp": [{"HostPort": "2222"}]},
            network_names=["net"],
        )
        client.containers.list.return_value = [wg1, wg2]

        url, name = detect_webgateway(client, iris_networks={"net"}, host="localhost")
        assert url == "http://localhost:1111"
        assert name == "wg-one"

    def test_webgateway_without_port80_binding_skipped(self):
        client = MagicMock()
        wg = _fake_container(
            name="wg-no-port",
            image_tags=["x/webgateway:a"],
            port_bindings={},  # port 80 not published
            network_names=["net"],
        )
        client.containers.list.return_value = [wg]

        url, name = detect_webgateway(client, iris_networks={"net"}, host="localhost")
        assert url is None
        assert name is None

    def test_matches_untagged_image_via_repo_name(self):
        """Container image may lack tags; fall back to image.attrs RepoTags."""
        client = MagicMock()
        wg = _fake_container(
            name="wg",
            image_tags=[],
            port_bindings={"80/tcp": [{"HostPort": "80"}]},
            network_names=["net"],
        )
        wg.image.attrs = {"RepoTags": ["intersystems/webgateway:latest-cd"]}
        client.containers.list.return_value = [wg]

        url, name = detect_webgateway(client, iris_networks={"net"}, host="localhost")
        assert url == "http://localhost:80"
        assert name == "wg"

    def test_docker_error_is_swallowed(self):
        client = MagicMock()
        client.containers.list.side_effect = Exception("docker down")
        url, name = detect_webgateway(client, iris_networks={"net"}, host="localhost")
        assert url is None
        assert name is None


class TestIRISContainerConnectionInfo:
    """IRISContainer.connection_info() wiring (Docker fully mocked)."""

    def _make_container(self):
        from iris_devtester.containers import IRISContainer

        c = IRISContainer(image="intersystemsdc/iris-community:latest")
        c.host = "localhost"
        c._namespace = "USER"
        c._username = "_SYSTEM"
        c._password = "SYS"
        c._container_name = "iris_db"
        c._mapped_port = 1972
        return c

    def test_docker_only_when_no_webgateway(self):
        c = self._make_container()
        wrapped = _fake_container(
            name="iris_db",
            image_tags=["intersystemsdc/iris-community:latest"],
            network_names=["proj_default"],
        )
        wrapped.client.containers.list.return_value = [wrapped]  # only IRIS on net
        c.get_wrapped_container = MagicMock(return_value=wrapped)

        info = c.connection_info()
        assert info.docker_only is True
        assert info.webgateway_url is None
        assert info.container == "iris_db"
        assert info.superserver_port == 1972
        assert info.iris_image == "intersystemsdc/iris-community:latest"
        assert "docker_only = true" in info.to_toml_snippet()

    def test_detects_webgateway_on_shared_network(self):
        c = self._make_container()
        iris = _fake_container(
            name="iris_db",
            image_tags=["intersystemsdc/iris-community:latest"],
            network_names=["proj_default"],
        )
        wg = _fake_container(
            name="proj-webgateway",
            image_tags=["intersystems/webgateway:latest-cd"],
            port_bindings={"80/tcp": [{"HostPort": "52774"}]},
            network_names=["proj_default"],
        )
        iris.client.containers.list.return_value = [iris, wg]
        c.get_wrapped_container = MagicMock(return_value=iris)

        info = c.connection_info()
        assert info.docker_only is False
        assert info.webgateway_url == "http://localhost:52774"
        assert info.webgateway_container == "proj-webgateway"
        assert "web_port = 52774" in info.to_toml_snippet()

    def test_web_port_fallback_when_no_detection(self):
        c = self._make_container()
        iris = _fake_container(
            name="iris_db",
            image_tags=["intersystemsdc/iris-community:latest"],
            network_names=["proj_default"],
        )
        iris.client.containers.list.return_value = [iris]
        c.get_wrapped_container = MagicMock(return_value=iris)

        info = c.connection_info(web_port=8080)
        assert info.webgateway_url == "http://localhost:8080"
        assert info.docker_only is False

    def test_detection_wins_over_web_port_fallback(self):
        c = self._make_container()
        iris = _fake_container(
            name="iris_db",
            image_tags=["intersystemsdc/iris-community:latest"],
            network_names=["proj_default"],
        )
        wg = _fake_container(
            name="proj-webgateway",
            image_tags=["intersystems/webgateway:latest-cd"],
            port_bindings={"80/tcp": [{"HostPort": "52774"}]},
            network_names=["proj_default"],
        )
        iris.client.containers.list.return_value = [iris, wg]
        c.get_wrapped_container = MagicMock(return_value=iris)

        info = c.connection_info(web_port=8080)
        assert info.webgateway_url == "http://localhost:52774"

    def test_graceful_when_wrapped_container_unavailable(self):
        c = self._make_container()
        c.get_wrapped_container = MagicMock(side_effect=Exception("not started"))

        info = c.connection_info()
        assert info.docker_only is True
        assert info.container == "iris_db"
        assert info.iris_image == "intersystemsdc/iris-community:latest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
