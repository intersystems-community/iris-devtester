"""
Unit tests for enhanced IRIS container.

Tests wrapper around testcontainers-iris-python with automatic connection
and password reset integration.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestIRISContainer:
    """Test enhanced IRIS container class."""

    def test_can_import(self):
        """Test that IRISContainer can be imported."""
        from iris_devtester.containers import IRISContainer

        assert IRISContainer is not None

    def test_community_class_method_exists(self):
        """Test that .community() class method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "community")
        assert callable(IRISContainer.community)

    def test_enterprise_class_method_exists(self):
        """Test that .enterprise() class method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "enterprise")
        assert callable(IRISContainer.enterprise)

    def test_light_class_method_exists(self):
        """Test that .light() class method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "light")
        assert callable(IRISContainer.light)

    def test_light_creates_container_with_correct_image(self):
        """Test that .light() returns a container with caretdev image."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.light()

        assert container is not None
        assert isinstance(container, IRISContainer)
        assert "caretdev/iris-community-light" in container.image

    def test_light_accepts_version_parameter(self):
        """Test that .light() accepts version parameter."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.light(version="2025.1")

        assert "2025.1" in container.image

    def test_community_accepts_version_parameter(self):
        """Test that .community() accepts version parameter."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community(version="2025.2")

        assert "2025.2" in container.image

    def test_community_creates_container_object(self):
        """Test that .community() returns a container instance."""
        from iris_devtester.containers import IRISContainer

        container = IRISContainer.community()

        # Should return an IRISContainer instance
        assert container is not None
        assert isinstance(container, IRISContainer)

    def test_get_connection_method_exists(self):
        """Test that get_connection() method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "get_connection") and callable(IRISContainer.get_connection)

    def test_wait_for_ready_method_exists(self):
        """Test that wait_for_ready() method exists."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "wait_for_ready") and callable(IRISContainer.wait_for_ready)

    def test_with_preconfigured_password_method_exists(self):
        """Test that with_preconfigured_password() method exists for password pre-configuration."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "with_preconfigured_password")
        assert callable(getattr(IRISContainer, "with_preconfigured_password"))

    def test_with_credentials_method_exists(self):
        """Test that with_credentials() method exists for credential pre-configuration."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "with_credentials")
        assert callable(getattr(IRISContainer, "with_credentials"))

    def test_get_config_method_exists(self):
        """Test that get_config() method returns IRISConfig."""
        from iris_devtester.containers import IRISContainer

        assert hasattr(IRISContainer, "get_config") and callable(IRISContainer.get_config)


class TestIRISContainerIntegration:
    """Test IRIS container integration with other components."""

    def test_password_preconfig_sets_env_vars(self):
        """Test that password pre-configuration works via env vars."""
        from iris_devtester.containers import IRISContainer

        # Create container with pre-configured password
        container = IRISContainer.community()
        container.with_preconfigured_password("TestPass123")

        # Verify internal state was set
        assert container._preconfigure_password == "TestPass123"
        assert container._password == "TestPass123"

class TestAttachPortOverride:
    """attach(port=) must skip docker port lookup and use the supplied port directly."""

    def _make_mock_container(self, host_port: int = 31972):
        """Return a mock Docker container whose port binding reports host_port."""
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {
                "Ports": {"1972/tcp": [{"HostPort": str(host_port)}]},
                "Networks": {},
            }
        }
        mock_container.name = "ivg-iris-enterprise"
        # get_container_host_ip() is called by get_config() in the testcontainers path
        mock_container.get_container_host_ip = MagicMock(return_value="localhost")
        mock_container.get_exposed_port = MagicMock(return_value=host_port)
        return mock_container

    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_explicit_port_skips_docker_lookup(self, mock_docker, mock_get_config):
        """When port= is supplied, _mapped_port must equal that port, not the docker binding."""
        from iris_devtester.containers import IRISContainer

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.get.return_value = self._make_mock_container(host_port=31972)

        iris = IRISContainer.attach("ivg-iris-enterprise", port=31971)

        assert iris._mapped_port == 31971, (
            f"Expected _mapped_port=31971 (explicit), got {iris._mapped_port}"
        )

    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_explicit_port_used_by_get_mapped_port(self, mock_docker, mock_get_config):
        """get_mapped_port(1972) must return the explicit port, not the docker-inspected one."""
        from iris_devtester.containers import IRISContainer

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.get.return_value = self._make_mock_container(host_port=31972)

        iris = IRISContainer.attach("ivg-iris-enterprise", port=31971)

        assert iris.get_mapped_port(1972) == 31971

    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_without_port_does_not_pin_mapped_port(self, mock_docker, mock_get_config):
        """Without port=, _mapped_port is not pinned by attach() — port discovery deferred to get_config()."""
        from iris_devtester.containers import IRISContainer

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.get.return_value = self._make_mock_container(host_port=31972)

        iris = IRISContainer.attach("ivg-iris-enterprise")

        # No explicit port: _mapped_port is not set by attach itself (get_config handles discovery)
        assert iris._mapped_port is None

    @patch.dict("os.environ", {"IVG_PORT": "31971"})
    @patch("iris_devtester.containers.iris_container.IRISContainer.get_config")
    @patch("docker.from_env")
    def test_ivg_port_env_var_respected(self, mock_docker, mock_get_config):
        """IVG_PORT env var must be honoured as a port override in attach()."""
        from iris_devtester.containers import IRISContainer

        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.get.return_value = self._make_mock_container(host_port=31972)

        iris = IRISContainer.attach("ivg-iris-enterprise")

        assert iris._mapped_port == 31971, (
            f"IVG_PORT=31971 should override docker binding 31972, got {iris._mapped_port}"
        )


class TestIRISContainerConfiguration:
    """Test IRIS container configuration options."""

    def test_enterprise_requires_license_key(self):
        """Test that enterprise() raises error without license key."""
        import pytest

        from iris_devtester.containers import IRISContainer

        # Enterprise edition should require license
        with pytest.raises(ValueError, match="Enterprise edition requires a license key"):
            IRISContainer.enterprise()

    def test_enterprise_validates_license_file_exists(self):
        """Test that enterprise() validates license file exists."""
        import pytest

        from iris_devtester.containers import IRISContainer

        with pytest.raises(ValueError, match="License key file not found"):
            IRISContainer.enterprise(license_key="/nonexistent/path/iris.key")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
