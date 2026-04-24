"""Contract tests for BUG-IDT-1: get_mapped_port() fails in Docker-in-Docker.

Tests define expected behavior BEFORE implementation. Each maps to a specific
fix in iris_container.py.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetMappedPortDinD:
    """FR-001: get_mapped_port() must not raise ConnectionError in DinD."""

    def test_get_mapped_port_1972_returns_cached_value(self):
        """Port 1972 returns _mapped_port cache without calling get_exposed_port."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        iris._mapped_port = 51234

        # Must use cache — never call get_exposed_port
        with patch.object(iris, "get_exposed_port", side_effect=Exception("should not be called")):
            assert iris.get_mapped_port(1972) == 51234

    def test_get_mapped_port_non_1972_uses_port_cache(self):
        """Non-1972 ports use _port_cache when available, without calling get_exposed_port."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        iris._port_cache[52773] = 52773  # DinD: internal port == reachable port

        with patch.object(iris, "get_exposed_port", side_effect=Exception("should not be called")):
            assert iris.get_mapped_port(52773) == 52773

    def test_get_mapped_port_falls_back_to_internal_on_connection_error(self):
        """In DinD, ConnectionError from get_exposed_port falls back to internal port.

        Root cause of BUG-IDT-1: DockerClient.port() returns None in DinD
        because the outer host's port binding is not visible to the inner
        Docker daemon. Testcontainers raises ConnectionError.
        Fix: catch ConnectionError, return internal port (which IS reachable
        via the container's gateway/bridge IP in DinD).
        """
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        # No cache set — simulate DinD where get_exposed_port fails
        with patch.object(
            iris,
            "get_exposed_port",
            side_effect=ConnectionError("Port mapping for container abc and port 52773 is not available"),
        ):
            # Must return internal port, not raise
            result = iris.get_mapped_port(52773)
            assert result == 52773

    def test_get_mapped_port_raises_on_non_connection_errors(self):
        """Non-ConnectionError exceptions are still propagated (not swallowed)."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        with patch.object(iris, "get_exposed_port", side_effect=RuntimeError("container not started")):
            with pytest.raises(RuntimeError, match="container not started"):
                iris.get_mapped_port(52773)

    def test_get_mapped_port_populates_port_cache_on_success(self):
        """Successful get_exposed_port result is stored in _port_cache for reuse."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        with patch.object(iris, "get_exposed_port", return_value=52999):
            result = iris.get_mapped_port(52773)
            assert result == 52999
            assert iris._port_cache.get(52773) == 52999


class TestPortCacheInit:
    """FR-002: IRISContainer initializes with _port_cache dict attribute."""

    def test_port_cache_initialized_on_construction(self):
        """_port_cache dict exists on new IRISContainer, empty by default."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        assert hasattr(iris, "_port_cache")
        assert isinstance(iris._port_cache, dict)
        assert len(iris._port_cache) == 0

    def test_port_cache_independent_across_instances(self):
        """Each IRISContainer instance has its own _port_cache."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris1 = IRISContainer.community()
        iris2 = IRISContainer.community()
        iris1._port_cache[52773] = 11111
        assert 52773 not in iris2._port_cache


class TestGetConfigDinDResilience:
    """FR-003: get_config() must not silently swallow port discovery errors."""

    def test_get_config_returns_internal_port_when_mapping_fails(self):
        """In DinD, get_config() uses internal port (1972) when mapping raises ConnectionError."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        iris._mapped_port = None  # not yet discovered

        with patch.object(
            iris,
            "get_exposed_port",
            side_effect=ConnectionError("Port mapping is not available"),
        ), patch.object(iris, "get_container_host_ip", return_value="172.17.0.1"):
            config = iris.get_config()
            # Should use internal port 1972 as fallback, not raise
            assert config.port == 1972
            assert config.host == "172.17.0.1"
