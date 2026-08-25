"""
Additional unit tests for IRISContainer to improve coverage.

Tests factory methods, config discovery, port mapping, credential handling,
and graceful stop patterns.
"""

from unittest.mock import MagicMock, Mock, patch, call, PropertyMock
import os
import pytest
import tempfile


def make_container(**kwargs) -> "IRISContainer":
    """Create a bare IRISContainer instance for testing (without testcontainers)."""
    from iris_devtester.containers.iris_container import IRISContainer

    # Create a new instance without calling __init__ normally
    container = IRISContainer.__new__(IRISContainer)

    # Set required attributes
    container._container_name = kwargs.pop("_container_name", "test-iris")
    container._mapped_port = kwargs.pop("_mapped_port", 1972)
    container._password = kwargs.pop("_password", "SYS")
    container._username = kwargs.pop("_username", "_SYSTEM")
    container._namespace = kwargs.pop("_namespace", "USER")
    container.image = kwargs.pop("image", "intersystemsdc/iris-community:latest")
    container.host = kwargs.pop("host", "localhost")
    container.port = kwargs.pop("port", 1972)
    container._container = kwargs.pop("_container", None)
    container._is_attached = kwargs.pop("_is_attached", False)
    container._connection = None
    container._callin_enabled = False
    container._password_preconfigured = False
    container._config = None
    container._port_cache = {}
    container._password_handled = False
    container._preconfigure_password = None
    container._preconfigure_username = None
    container._port_registry = kwargs.pop("_port_registry", None)
    container._preferred_port = kwargs.pop("_preferred_port", None)
    container._project_path = kwargs.pop("_project_path", None)
    container._port_assignment = None
    container._edition = kwargs.pop("_edition", None)
    container._durable_path = kwargs.pop("_durable_path", None)
    container._use_tmpfs_durable = kwargs.pop("_use_tmpfs_durable", False)

    # Apply any remaining kwargs
    for k, v in kwargs.items():
        setattr(container, k, v)

    return container


class TestFactoryMethods:
    """Test factory methods for creating containers."""

    def test_community_default_image_x86(self):
        """Test community() with default image on x86_64."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("platform.machine", return_value="x86_64"):
            container = IRISContainer.community()
            assert "intersystemsdc/iris-community:latest" in container.image

    def test_community_default_image_arm64(self):
        """Test community() with default image on ARM64 (Apple Silicon)."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("platform.machine", return_value="arm64"):
            container = IRISContainer.community()
            assert "containers.intersystems.com/intersystems/iris-community:2025.1" in container.image

    def test_community_custom_image(self):
        """Test community() with explicit image override."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.community(image="custom-image:v1")
        assert container.image == "custom-image:v1"

    def test_community_version_parameter(self):
        """Test community() version parameter."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("platform.machine", return_value="x86_64"):
            container = IRISContainer.community(version="2024.2")
            assert "2024.2" in container.image

    def test_enterprise_requires_license_via_env(self):
        """Test enterprise() can read license from env var."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict("os.environ", {"IRIS_LICENSE_KEY": "/path/to/key"}, clear=False):
            with patch("os.path.exists", return_value=True):
                container = IRISContainer.enterprise()
                assert hasattr(container, "_license_key_path")
                assert container._license_key_path == "/path/to/key"

    def test_enterprise_missing_license_no_param_no_env(self):
        """Test enterprise() raises when no license is provided."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Enterprise edition requires a license key"):
                IRISContainer.enterprise()

    def test_enterprise_nonexistent_license_file(self):
        """Test enterprise() raises when license file doesn't exist."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("os.path.exists", return_value=False):
            with pytest.raises(ValueError, match="License key file not found"):
                IRISContainer.enterprise(license_key="/nonexistent/key")

    def test_enterprise_custom_image(self):
        """Test enterprise() with custom image."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("os.path.exists", return_value=True):
            container = IRISContainer.enterprise(
                license_key="/path/to/key", image="custom-enterprise:v1"
            )
            assert container.image == "custom-enterprise:v1"

    def test_enterprise_default_image(self):
        """Test enterprise() uses default image when not specified."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("os.path.exists", return_value=True):
            container = IRISContainer.enterprise(license_key="/path/to/key")
            assert "containers.intersystems.com/intersystems/iris:latest" in container.image

    def test_light_default_image(self):
        """Test light() uses caretdev image."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.light()
        assert "caretdev/iris-community-light:" in container.image

    def test_light_version_latest_em(self):
        """Test light() with version='latest' defaults to latest-em."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.light(version="latest")
        assert "latest-em" in container.image

    def test_light_custom_version(self):
        """Test light() with custom version."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.light(version="2025.1")
        assert "2025.1" in container.image

    def test_light_custom_image(self):
        """Test light() with custom image override."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.light(image="my-light:v1")
        assert container.image == "my-light:v1"

    def test_health_default_image(self):
        """Test health() uses irishealth-community image."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.health()
        assert "intersystemsdc/irishealth-community:" in container.image
        assert container._edition == "health"

    def test_health_custom_version(self):
        """Test health() with custom version."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.health(version="2024.1")
        assert "2024.1" in container.image

    def test_health_custom_image(self):
        """Test health() with custom image override."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.health(image="custom-health:v1")
        assert container.image == "custom-health:v1"
        assert container._edition == "health"

    def test_ai_hub_default_build(self):
        """Test ai_hub() uses default build number."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.ai_hub()
        assert "irishealth:2026.2.0AI.159.0" in container.image
        assert container._edition == "ai_hub"
        assert container._use_tmpfs_durable is True

    def test_ai_hub_custom_build(self):
        """Test ai_hub() with custom build number."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.ai_hub(build="200")
        assert "2026.2.0AI.200.0" in container.image

    def test_ai_hub_custom_image(self):
        """Test ai_hub() with custom image override."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.ai_hub(image="custom-aihub:v1")
        assert container.image == "custom-aihub:v1"
        assert container._edition == "ai_hub"

    def test_ai_hub_with_durable_path(self):
        """Test ai_hub() with persistent durable path."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.ai_hub(durable_path="/mnt/data")
        assert container._durable_path == "/mnt/data"
        assert container._use_tmpfs_durable is False

    def test_ai_hub_without_durable_path(self):
        """Test ai_hub() without durable path uses tmpfs."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = IRISContainer.ai_hub()
        assert container._durable_path is None
        assert container._use_tmpfs_durable is True


class TestAttachMethod:
    """Test the attach() class method for connecting to existing containers."""

    def _make_mock_docker_container(self, host_port: int = 31972):
        """Create a mock Docker container."""
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {
                "Ports": {"1972/tcp": [{"HostPort": str(host_port)}]},
            }
        }
        mock_container.name = "test-iris"
        mock_container.get_container_host_ip = MagicMock(return_value="localhost")
        mock_container.get_exposed_port = MagicMock(return_value=host_port)
        return mock_container

    def test_attach_requires_container_name(self):
        """Test attach() raises when container_name is empty."""
        from iris_devtester.containers.iris_container import IRISContainer

        with pytest.raises(ValueError, match="container_name must be a non-empty string"):
            IRISContainer.attach("")

    def test_attach_explicit_port_override(self):
        """Test attach() with explicit port parameter overrides docker lookup."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container(
                host_port=31972
            )

            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                container = IRISContainer.attach("test-iris", port=31971)

            assert container._mapped_port == 31971
            assert container._is_attached is True

    def test_attach_without_explicit_port_reads_docker(self):
        """Test attach() without port parameter reads docker binding."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container(
                host_port=31972
            )

            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                container = IRISContainer.attach("test-iris")

            # Port is read from docker attrs
            assert container._mapped_port == 31972

    def test_attach_respects_ivg_port_env_var(self):
        """Test attach() respects IVG_PORT environment variable."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict("os.environ", {"IVG_PORT": "31971"}, clear=False):
            with patch("docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client
                mock_client.containers.get.return_value = self._make_mock_docker_container(
                    host_port=31972
                )

                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    container = IRISContainer.attach("test-iris")

                assert container._mapped_port == 31971

    def test_attach_respects_iris_port_env_var_when_ivg_missing(self):
        """Test attach() respects IRIS_PORT env var when IVG_PORT is not set."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict("os.environ", {"IRIS_PORT": "31970"}, clear=True):
            with patch("docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client
                mock_client.containers.get.return_value = self._make_mock_docker_container(
                    host_port=31972
                )

                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    container = IRISContainer.attach("test-iris")

                assert container._mapped_port == 31970

    def test_attach_port_parameter_priority_over_env(self):
        """Test attach() port parameter has priority over env vars."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict("os.environ", {"IVG_PORT": "31970", "IRIS_PORT": "31969"}, clear=False):
            with patch("docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client
                mock_client.containers.get.return_value = self._make_mock_docker_container(
                    host_port=31972
                )

                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    container = IRISContainer.attach("test-iris", port=31968)

                assert container._mapped_port == 31968

    def test_attach_invalid_port_env_var_ignored(self):
        """Test attach() ignores invalid port env var values."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch.dict("os.environ", {"IVG_PORT": "not-a-port"}, clear=False):
            with patch("docker.from_env") as mock_docker:
                mock_client = MagicMock()
                mock_docker.return_value = mock_client
                mock_client.containers.get.return_value = self._make_mock_docker_container(
                    host_port=31972
                )

                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    container = IRISContainer.attach("test-iris")

                # Falls back to docker reading
                assert container._mapped_port == 31972

    def test_attach_container_not_found_raises(self):
        """Test attach() raises when container doesn't exist."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.side_effect = Exception("Container not found")

            with pytest.raises(ValueError, match="Container.*not found or not running"):
                IRISContainer.attach("nonexistent")

    def test_attach_passes_kwargs_to_constructor(self):
        """Test attach() forwards kwargs to __init__."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container()

            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                container = IRISContainer.attach(
                    "test-iris",
                    username="CUSTOM",
                    password="PASS123",
                    namespace="CUSTOM_NS",
                )

            assert container._username == "CUSTOM"
            assert container._password == "PASS123"
            assert container._namespace == "CUSTOM_NS"

    def test_attach_with_testcontainers_calls_get_config(self):
        """Test attach() with testcontainers enabled calls get_config()."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container()

            with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", True):
                with patch.object(IRISContainer, "get_config") as mock_get_config:
                    IRISContainer.attach("test-iris", port=31971)
                    mock_get_config.assert_called_once()

    def test_attach_unexpire_passwords_by_default(self):
        """Test attach() calls unexpire_all_passwords() by default."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container()

            with patch(
                "iris_devtester.containers.iris_container.unexpire_all_passwords"
            ) as mock_unexpire:
                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    IRISContainer.attach("test-iris")
                    mock_unexpire.assert_called_once_with("test-iris")

    def test_attach_skip_unexpire_passwords_when_disabled(self):
        """Test attach() skips unexpire_all_passwords() when disabled."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container()

            with patch(
                "iris_devtester.containers.iris_container.unexpire_all_passwords"
            ) as mock_unexpire:
                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    IRISContainer.attach("test-iris", unexpire_passwords=False)
                    mock_unexpire.assert_not_called()

    def test_attach_unexpire_failure_is_nonfatal(self):
        """Test attach() continues even if unexpire_all_passwords() fails."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch("docker.from_env") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            mock_client.containers.get.return_value = self._make_mock_docker_container()

            with patch(
                "iris_devtester.containers.iris_container.unexpire_all_passwords",
                side_effect=Exception("Failed to unexpire"),
            ):
                with patch("iris_devtester.containers.iris_container.HAS_TESTCONTAINERS", False):
                    # Should not raise, just continue
                    container = IRISContainer.attach("test-iris")
                    assert container is not None


class TestGetConfigMethod:
    """Test the get_config() method."""

    def test_get_config_returns_iris_config(self):
        """Test get_config() returns an IRISConfig object."""
        from iris_devtester.config.models import IRISConfig

        container = make_container()

        with patch.object(container, "get_container_host_ip", return_value="localhost"):
            with patch.object(container, "get_mapped_port", return_value=1972):
                config = container.get_config()

        assert isinstance(config, IRISConfig)
        assert config.username == "_SYSTEM"
        assert config.password == "SYS"
        assert config.namespace == "USER"

    def test_get_config_normalizes_container_ip(self):
        """Test get_config() normalizes 0.0.0.0 and :: to localhost."""
        container = make_container()

        with patch.object(container, "get_container_host_ip", return_value="0.0.0.0"):
            with patch.object(container, "get_mapped_port", return_value=1972):
                config = container.get_config()

        assert config.host == "localhost"
        assert container.host == "localhost"

    def test_get_config_handles_ipv6_any(self):
        """Test get_config() handles IPv6 any address ::."""
        container = make_container()

        with patch.object(container, "get_container_host_ip", return_value="::"):
            with patch.object(container, "get_mapped_port", return_value=1972):
                config = container.get_config()

        assert config.host == "localhost"

    def test_get_config_caches_in_instance(self):
        """Test get_config() stores config in _config attribute."""
        container = make_container()

        with patch.object(container, "get_container_host_ip", return_value="localhost"):
            with patch.object(container, "get_mapped_port", return_value=1972):
                config = container.get_config()

        assert container._config == config

    def test_get_config_catches_connection_error(self):
        """Test get_config() continues even if get_mapped_port() raises ConnectionError."""
        container = make_container()

        with patch.object(
            container, "get_container_host_ip", return_value="localhost"
        ):
            with patch.object(container, "get_mapped_port", side_effect=ConnectionError("DinD")):
                # Should not raise
                config = container.get_config()

        assert config is not None


class TestGetContainerName:
    """Test the get_container_name() method."""

    def test_get_container_name_returns_set_name(self):
        """Test get_container_name() returns _container_name if set."""
        container = make_container(_container_name="my-iris")
        assert container.get_container_name() == "my-iris"

    def test_get_container_name_from_docker_container(self):
        """Test get_container_name() reads from _container when available."""
        mock_docker_container = MagicMock()
        mock_docker_container.name = "docker-iris"
        container = make_container(_container_name=None, _container=mock_docker_container)

        name = container.get_container_name()
        assert name == "docker-iris"

    def test_get_container_name_fallback_to_iris_db(self):
        """Test get_container_name() falls back to 'iris_db'."""
        container = make_container(_container_name=None, _container=None)
        name = container.get_container_name()
        assert name == "iris_db"

    def test_get_container_name_ignores_docker_container_exception(self):
        """Test get_container_name() ignores exceptions reading from _container."""
        mock_docker_container = MagicMock()
        type(mock_docker_container).name = PropertyMock(side_effect=Exception("Access error"))
        container = make_container(_container_name=None, _container=mock_docker_container)

        # Should fall back gracefully
        name = container.get_container_name()
        assert name == "iris_db"


class TestGetMappedPort:
    """Test the get_mapped_port() method."""

    def test_get_mapped_port_returns_pinned_mapped_port(self):
        """Test get_mapped_port(1972) returns _mapped_port if set."""
        container = make_container(_mapped_port=31972)
        port = container.get_mapped_port(1972)
        assert port == 31972

    def test_get_mapped_port_returns_cached_port(self):
        """Test get_mapped_port() returns cached port if available."""
        container = make_container(_mapped_port=None)
        container._port_cache[52773] = 31052

        port = container.get_mapped_port(52773)
        assert port == 31052

    def test_get_mapped_port_calls_get_exposed_port_when_not_cached(self):
        """Test get_mapped_port() calls get_exposed_port() for uncached ports."""
        container = make_container(_mapped_port=None)

        with patch.object(container, "get_exposed_port", return_value=31052):
            port = container.get_mapped_port(52773)

        assert port == 31052
        assert container._port_cache[52773] == 31052

    def test_get_mapped_port_handles_connection_error_returns_internal_port(self):
        """Test get_mapped_port() returns internal port when get_exposed_port() fails."""
        container = make_container(_mapped_port=None)

        with patch.object(
            container, "get_exposed_port", side_effect=ConnectionError("DinD")
        ):
            port = container.get_mapped_port(52773)

        assert port == 52773  # Returns the internal port
        assert container._port_cache[52773] == 52773


class TestStopGracefully:
    """Test the stop_gracefully() method."""

    def test_stop_gracefully_success(self):
        """Test stop_gracefully() returns True when iris stop succeeds."""
        container = make_container()
        mock_docker_container = MagicMock()
        mock_docker_container.exec_run.return_value = (0, b"stopped")
        container._container = mock_docker_container

        result = container.stop_gracefully()
        assert result is True
        mock_docker_container.exec_run.assert_called_once_with(
            "iris stop IRIS quietly", user="irisowner"
        )

    def test_stop_gracefully_returns_false_on_exit_code_error(self):
        """Test stop_gracefully() returns False when iris stop returns nonzero."""
        container = make_container()
        mock_docker_container = MagicMock()
        mock_docker_container.exec_run.return_value = (1, b"error")
        container._container = mock_docker_container

        result = container.stop_gracefully()
        assert result is False

    def test_stop_gracefully_returns_false_when_container_is_none(self):
        """Test stop_gracefully() returns False when _container is None."""
        container = make_container(_container=None)
        result = container.stop_gracefully()
        assert result is False

    def test_stop_gracefully_returns_false_on_exception(self):
        """Test stop_gracefully() returns False on any exception."""
        container = make_container()
        mock_docker_container = MagicMock()
        mock_docker_container.exec_run.side_effect = Exception("Docker error")
        container._container = mock_docker_container

        result = container.stop_gracefully()
        assert result is False

    def test_stop_gracefully_with_custom_timeout(self):
        """Test stop_gracefully() accepts custom timeout parameter."""
        container = make_container()
        mock_docker_container = MagicMock()
        mock_docker_container.exec_run.return_value = (0, b"stopped")
        container._container = mock_docker_container

        # Timeout param is accepted but not used in current implementation
        result = container.stop_gracefully(timeout=60)
        assert result is True


class TestWithMethods:
    """Test builder/fluent methods like with_name(), with_cpf_merge(), etc."""

    def test_with_name_sets_container_name(self):
        """Test with_name() sets _container_name."""
        container = make_container()
        result = container.with_name("new-name")

        assert container._container_name == "new-name"
        assert result is container  # Returns self for chaining

    def test_with_name_sets_parent_name(self):
        """Test with_name() also sets _name for parent class."""
        container = make_container()
        container.with_name("new-name")

        assert container._name == "new-name"

    def test_with_preconfigured_password_valid(self):
        """Test with_preconfigured_password() sets password."""
        container = make_container()
        result = container.with_preconfigured_password("NewPass123")

        assert container._preconfigure_password == "NewPass123"
        assert container._password == "NewPass123"
        assert result is container

    def test_with_preconfigured_password_empty_raises(self):
        """Test with_preconfigured_password() raises on empty password."""
        container = make_container()

        with pytest.raises(ValueError, match="Password cannot be empty"):
            container.with_preconfigured_password("")

    def test_with_credentials_sets_both(self):
        """Test with_credentials() sets username and password."""
        container = make_container()
        result = container.with_credentials("USER1", "PASS1")

        assert container._preconfigure_username == "USER1"
        assert container._preconfigure_password == "PASS1"
        assert container._username == "USER1"
        assert container._password == "PASS1"
        assert result is container

    def test_with_credentials_empty_username_raises(self):
        """Test with_credentials() raises on empty username."""
        container = make_container()

        with pytest.raises(ValueError, match="Username cannot be empty"):
            container.with_credentials("", "PASS")

    def test_with_credentials_empty_password_raises(self):
        """Test with_credentials() raises on empty password."""
        container = make_container()

        with pytest.raises(ValueError, match="Password cannot be empty"):
            container.with_credentials("USER", "")

    def test_with_cpf_merge_from_content(self):
        """Test with_cpf_merge() handles CPF content string."""
        container = make_container()

        # CPF content has newlines/brackets
        cpf_content = "[Actions]\nKey1=Value1"

        with patch.object(container, "with_volume_mapping"):
            with patch.object(container, "with_env"):
                result = container.with_cpf_merge(cpf_content)

        assert result is container
        assert hasattr(container, "_cpf_temp_files")

    def test_with_cpf_merge_from_file_path(self):
        """Test with_cpf_merge() handles file path."""
        container = make_container()

        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cpf", delete=False) as f:
            f.write("[Actions]\nKey=Value")
            temp_path = f.name

        try:
            with patch.object(container, "with_volume_mapping"):
                with patch.object(container, "with_env"):
                    result = container.with_cpf_merge(temp_path)

            assert result is container
        finally:
            os.unlink(temp_path)

    def test_with_cpf_merge_missing_file_raises(self):
        """Test with_cpf_merge() raises when file doesn't exist."""
        container = make_container()

        with pytest.raises(FileNotFoundError, match="CPF merge file not found"):
            container.with_cpf_merge("/nonexistent/file.cpf")


class TestCredentialMethods:
    """Test credential-related methods."""

    def test_get_password_returns_current_password(self):
        """Test get_password() returns _password."""
        container = make_container(_password="MYPASS")
        assert container.get_password() == "MYPASS"

    def test_get_username_returns_current_username(self):
        """Test get_username() returns _username."""
        container = make_container(_username="MYUSER")
        assert container.get_username() == "MYUSER"


class TestPortRegistry:
    """Test port registry integration in start()."""

    def test_start_with_port_registry_calls_assign_port(self):
        """Test start() calls port_registry.assign_port() when configured."""
        from iris_devtester.containers.iris_container import IRISContainer

        # Create a container with port registry
        mock_port_registry = MagicMock()
        mock_port_assignment = MagicMock()
        mock_port_assignment.port = 31972
        mock_port_registry.assign_port.return_value = mock_port_assignment

        container = make_container(
            _port_registry=mock_port_registry, _project_path="/project/path"
        )

        with patch.object(container, "with_cpf_merge"):
            with patch.object(container, "with_env"):
                with patch.object(container, "with_bind_ports"):
                    with patch.object(container, "get_config"):
                        with patch("iris_devtester.containers.iris_container.IRISBase.start"):
                            container.start()

        mock_port_registry.assign_port.assert_called_once_with(
            project_path="/project/path", preferred_port=None
        )
        assert container._port_assignment is mock_port_assignment

    def test_start_without_port_registry_skips_assign_port(self):
        """Test start() skips port registry when not configured."""
        from iris_devtester.containers.iris_container import IRISContainer

        container = make_container(_port_registry=None)

        with patch.object(container, "with_cpf_merge"):
            with patch.object(container, "with_env"):
                with patch.object(container, "get_config"):
                    with patch("iris_devtester.containers.iris_container.IRISBase.start"):
                        container.start()

        assert container._port_assignment is None


class TestConnectionInfo:
    """Test connection_info() method."""

    def test_connection_info_returns_iris_connection_info(self):
        """Test connection_info() returns IRISConnectionInfo object."""
        from iris_devtester.containers.connection_info import IRISConnectionInfo

        container = make_container()

        with patch.object(container, "get_container_host_ip", return_value="localhost"):
            with patch.object(container, "get_mapped_port", return_value=1972):
                with patch.object(container, "get_wrapped_container", return_value=None):
                    info = container.connection_info()

        assert isinstance(info, IRISConnectionInfo)
        assert info.host == "localhost"
        assert info.superserver_port == 1972
        assert info.username == "_SYSTEM"
        assert info.password == "SYS"
        assert info.namespace == "USER"

    def test_connection_info_uses_explicit_web_port_fallback(self):
        """Test connection_info() uses web_port param as fallback."""
        container = make_container()

        with patch.object(container, "get_container_host_ip", return_value="localhost"):
            with patch.object(container, "get_mapped_port", return_value=1972):
                with patch.object(container, "get_wrapped_container", return_value=None):
                    info = container.connection_info(web_port=8080)

        assert info.webgateway_url == "http://localhost:8080"


class TestValidation:
    """Test validate() and assert_healthy() methods."""

    def test_validate_calls_validate_container(self):
        """Test validate() calls the validation module."""
        from iris_devtester.containers.models import HealthCheckLevel

        container = make_container()

        with patch(
            "iris_devtester.containers.validation.validate_container"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(success=True)
            result = container.validate(level=HealthCheckLevel.STANDARD)

        mock_validate.assert_called_once_with(
            container_name="test-iris", level=HealthCheckLevel.STANDARD
        )

    def test_assert_healthy_raises_on_failure(self):
        """Test assert_healthy() raises RuntimeError on validation failure."""
        from iris_devtester.containers.models import HealthCheckLevel

        container = make_container()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.format_message.return_value = "Container is unhealthy"

        with patch(
            "iris_devtester.containers.validation.validate_container",
            return_value=mock_result,
        ):
            with pytest.raises(RuntimeError, match="Container is unhealthy"):
                container.assert_healthy(level=HealthCheckLevel.STANDARD)

    def test_assert_healthy_passes_on_success(self):
        """Test assert_healthy() returns normally on validation success."""
        from iris_devtester.containers.models import HealthCheckLevel

        container = make_container()

        mock_result = MagicMock()
        mock_result.success = True

        with patch(
            "iris_devtester.containers.validation.validate_container",
            return_value=mock_result,
        ):
            # Should not raise
            container.assert_healthy(level=HealthCheckLevel.STANDARD)


class TestDevMethod:
    """Test the dev() class method."""

    def test_dev_creates_dev_instance(self):
        """Test dev() calls DevInstanceManager and attaches to it."""
        from iris_devtester.containers.iris_container import IRISContainer

        with patch(
            "iris_devtester.containers.dev_instance.DevInstanceManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_instance = MagicMock()
            mock_instance.name = "iris_dev"
            mock_manager.ensure_ready.return_value = mock_instance
            mock_manager_class.return_value = mock_manager

            with patch("iris_devtester.containers.dev_instance.get_project_namespace", return_value="DEV_NS"):
                with patch.object(IRISContainer, "attach") as mock_attach:
                    mock_attach.return_value = MagicMock()
                    IRISContainer.dev()

            mock_attach.assert_called_once()
            # Check that namespace was passed
            call_kwargs = mock_attach.call_args[1]
            assert call_kwargs["namespace"] == "DEV_NS"


class TestGetPort:
    """Test get_assigned_port() and get_project_path()."""

    def test_get_assigned_port_returns_port_when_set(self):
        """Test get_assigned_port() returns port when _port_assignment is set."""
        container = make_container()
        mock_assignment = MagicMock()
        mock_assignment.port = 31972
        container._port_assignment = mock_assignment

        assert container.get_assigned_port() == 31972

    def test_get_assigned_port_returns_none_when_not_set(self):
        """Test get_assigned_port() returns None when _port_assignment is not set."""
        container = make_container()
        assert container.get_assigned_port() is None

    def test_get_project_path_returns_path_when_set(self):
        """Test get_project_path() returns _project_path."""
        container = make_container(_project_path="/project/path")
        assert container.get_project_path() == "/project/path"

    def test_get_project_path_returns_none_when_not_set(self):
        """Test get_project_path() returns None when not set."""
        container = make_container(_project_path=None)
        assert container.get_project_path() is None


class TestConfigDiscovery:
    """Test configuration discovery from environment/container."""

    def test_iris_config_initialization(self):
        """Test IRISConfig can be created with container info."""
        from iris_devtester.config.models import IRISConfig

        config = IRISConfig(
            username="_SYSTEM",
            password="SYS",
            namespace="USER",
            container_name="test-iris",
        )

        assert config.username == "_SYSTEM"
        assert config.password == "SYS"
        assert config.namespace == "USER"
        assert config.container_name == "test-iris"


