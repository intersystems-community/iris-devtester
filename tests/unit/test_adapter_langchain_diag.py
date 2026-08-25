"""
Unit tests for iris_container_adapter, langchain integration, and diagnostics.

Covers:
- VolumeMountSpec dataclass and parsing
- ContainerPersistenceCheck results
- IRISContainerManager static methods
- translate_docker_error() error translation
- LangChainIRISContainer instantiation and methods
- ConnectionProbe and probe_connection() diagnostics
"""

import sys
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest


# ====================
# VolumeMountSpec Tests
# ====================


class TestVolumeMountSpec:
    """Test VolumeMountSpec dataclass for Docker volume parsing."""

    def test_parse_default_mode(self):
        """Test parsing volume with default read-write mode."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        spec = VolumeMountSpec.parse("./data:/external")
        assert spec.host_path == "./data"
        assert spec.container_path == "/external"
        assert spec.mode == "rw"

    def test_parse_readonly_mode(self):
        """Test parsing volume with read-only mode."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        spec = VolumeMountSpec.parse("/tmp/data:/data:ro")
        assert spec.host_path == "/tmp/data"
        assert spec.container_path == "/data"
        assert spec.mode == "ro"

    def test_parse_readwrite_explicit(self):
        """Test parsing volume with explicit read-write mode."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        spec = VolumeMountSpec.parse("./workspace:/external:rw")
        assert spec.host_path == "./workspace"
        assert spec.container_path == "/external"
        assert spec.mode == "rw"

    def test_parse_invalid_format_too_few_parts(self):
        """Test that parsing volume with invalid format raises ValueError."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        with pytest.raises(ValueError) as exc_info:
            VolumeMountSpec.parse("./data")

        error_msg = str(exc_info.value)
        assert "invalid format" in error_msg.lower()
        assert "host:container" in error_msg

    def test_parse_invalid_mode(self):
        """Test that parsing volume with invalid mode raises ValueError."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        with pytest.raises(ValueError) as exc_info:
            VolumeMountSpec.parse("./data:/external:invalid")

        error_msg = str(exc_info.value)
        assert "invalid mode" in error_msg.lower()
        assert "rw" in error_msg
        assert "ro" in error_msg

    def test_dataclass_construction(self):
        """Test direct dataclass construction."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        spec = VolumeMountSpec(host_path="/host", container_path="/container", mode="ro")
        assert spec.host_path == "/host"
        assert spec.container_path == "/container"
        assert spec.mode == "ro"

    def test_dataclass_default_mode(self):
        """Test dataclass construction with default mode."""
        from iris_devtester.utils.iris_container_adapter import VolumeMountSpec

        spec = VolumeMountSpec(host_path="/host", container_path="/container")
        assert spec.mode == "rw"


# ====================
# ContainerPersistenceCheck Tests
# ====================


class TestContainerPersistenceCheck:
    """Test ContainerPersistenceCheck results dataclass."""

    def test_success_property_true(self):
        """Test success property returns True for valid check."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        check = ContainerPersistenceCheck(
            container_name="iris_test",
            exists=True,
            status="running",
            volume_mounts_verified=True,
            verification_time=1.5,
            error_details=None,
        )

        assert check.success is True

    def test_success_property_false_not_exists(self):
        """Test success property returns False when container doesn't exist."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        check = ContainerPersistenceCheck(
            container_name="iris_test",
            exists=False,
            status=None,
            volume_mounts_verified=False,
            verification_time=2.0,
            error_details="Container not found",
        )

        assert check.success is False

    def test_success_property_false_bad_status(self):
        """Test success property returns False for non-running status."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        check = ContainerPersistenceCheck(
            container_name="iris_test",
            exists=True,
            status="exited",
            volume_mounts_verified=True,
            verification_time=1.5,
            error_details=None,
        )

        assert check.success is False

    def test_success_property_false_volumes_not_verified(self):
        """Test success property returns False when volumes not verified."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        check = ContainerPersistenceCheck(
            container_name="iris_test",
            exists=True,
            status="running",
            volume_mounts_verified=False,
            verification_time=1.5,
            error_details="Volume mismatch",
        )

        assert check.success is False

    def test_success_property_false_has_error(self):
        """Test success property returns False when error_details present."""
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        check = ContainerPersistenceCheck(
            container_name="iris_test",
            exists=True,
            status="running",
            volume_mounts_verified=True,
            verification_time=1.5,
            error_details="Generic error",
        )

        assert check.success is False

    def test_get_error_message(self):
        """Test get_error_message returns constitutional format message."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import ContainerPersistenceCheck

        config = ContainerConfig.default()
        check = ContainerPersistenceCheck(
            container_name="iris_test",
            exists=False,
            status=None,
            volume_mounts_verified=False,
            verification_time=2.0,
            error_details="Container not found",
        )

        msg = check.get_error_message(config)

        assert "Container persistence verification failed" in msg
        assert "What went wrong" in msg
        assert "Why this happened" in msg
        assert "How to fix it" in msg


# ====================
# verify_container_persistence Tests
# ====================


class TestVerifyContainerPersistence:
    """Test verify_container_persistence() function."""

    @patch("time.sleep")
    @patch("docker.from_env")
    def test_verify_container_exists_and_running(self, mock_docker_from_env, mock_sleep):
        """Test successful persistence check for running container."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import verify_container_persistence

        # Setup mock docker client
        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client

        # Setup mock container
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {"Mounts": []}
        mock_client.containers.get.return_value = mock_container

        config = ContainerConfig.default()
        result = verify_container_persistence("iris_test", config, wait_seconds=0.5)

        assert result.exists is True
        assert result.status == "running"
        assert result.volume_mounts_verified is True
        assert result.error_details is None
        mock_sleep.assert_called_once_with(0.5)

    @patch("time.sleep")
    @patch("docker.from_env")
    def test_verify_container_not_found(self, mock_docker_from_env, mock_sleep):
        """Test persistence check when container not found."""
        from docker.errors import NotFound

        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import verify_container_persistence

        # Setup mock docker client
        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = NotFound("Container not found")

        config = ContainerConfig.default()
        result = verify_container_persistence("iris_test", config, wait_seconds=0.5)

        assert result.exists is False
        assert result.status is None
        assert result.volume_mounts_verified is False
        assert "not found" in result.error_details.lower()

    @patch("time.sleep")
    @patch("docker.from_env")
    def test_verify_container_generic_exception(self, mock_docker_from_env, mock_sleep):
        """Test persistence check with generic exception."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import verify_container_persistence

        # Setup mock docker client
        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = Exception("Generic error")

        config = ContainerConfig.default()
        result = verify_container_persistence("iris_test", config, wait_seconds=0.5)

        assert result.exists is False
        assert result.status is None
        assert result.volume_mounts_verified is False
        assert "error" in result.error_details.lower()

    @patch("time.sleep")
    @patch("docker.from_env")
    def test_verify_volume_mismatch(self, mock_docker_from_env, mock_sleep):
        """Test persistence check detects volume mount mismatch."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import verify_container_persistence

        # Setup mock docker client
        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client

        # Setup mock container with no mounts but volumes expected
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {"Mounts": []}
        mock_client.containers.get.return_value = mock_container

        config = ContainerConfig(volumes=["./data:/external"])
        result = verify_container_persistence("iris_test", config, wait_seconds=0.5)

        assert result.exists is True
        assert result.status == "running"
        assert result.volume_mounts_verified is False
        assert result.error_details is not None


# ====================
# IRISContainerManager Tests
# ====================


class TestIRISContainerManager:
    """Test IRISContainerManager static methods."""

    @patch("iris_devtester.utils.iris_container_adapter.IRISContainer")
    def test_create_from_config_testcontainers(self, mock_iris_container_class):
        """Test create_from_config with testcontainers mode."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        # Setup mock container instance
        mock_container = MagicMock()
        mock_iris_container_class.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="test_iris",
            superserver_port=1972,
            webserver_port=52773,
        )

        result = IRISContainerManager.create_from_config(config, use_testcontainers=True)

        assert result is mock_container
        # Verify IRISContainer was instantiated with correct args
        mock_iris_container_class.assert_called_once()
        # Verify configuration methods were called
        mock_container.with_name.assert_called_once_with("test_iris")
        mock_container.with_bind_ports.assert_called()

    @patch("docker.from_env")
    def test_create_from_config_docker_sdk(self, mock_docker_from_env):
        """Test create_from_config with Docker SDK mode."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        # Setup mock Docker client
        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_client.containers.create.return_value = mock_container

        config = ContainerConfig(
            edition="community",
            container_name="test_iris",
            superserver_port=1972,
            webserver_port=52773,
        )

        result = IRISContainerManager.create_from_config(config, use_testcontainers=False)

        assert result is mock_container
        mock_client.containers.create.assert_called_once()
        mock_container.start.assert_called_once()

    @patch("docker.from_env")
    def test_create_from_config_docker_sdk_with_volumes_and_license(self, mock_docker_from_env):
        """Test create_from_config with Docker SDK, volumes, and enterprise license."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        # Setup mock Docker client
        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_client.containers.create.return_value = mock_container

        config = ContainerConfig(
            edition="enterprise",
            container_name="test_iris",
            superserver_port=1972,
            webserver_port=52773,
            volumes=["./data:/external:ro"],
            license_key="TEST-LICENSE-KEY-123",
        )

        result = IRISContainerManager.create_from_config(config, use_testcontainers=False)

        assert result is mock_container
        # Verify volumes were passed to create
        call_kwargs = mock_client.containers.create.call_args[1]
        assert call_kwargs["volumes"] is not None
        assert call_kwargs["environment"]["ISC_LICENSE_KEY"] == "TEST-LICENSE-KEY-123"

    @patch("docker.from_env")
    def test_get_existing_found(self, mock_docker_from_env):
        """Test getting existing container that exists."""
        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client

        mock_container = MagicMock()
        mock_container.name = "iris_test"
        mock_client.containers.get.return_value = mock_container

        result = IRISContainerManager.get_existing("iris_test")

        assert result is mock_container
        mock_client.containers.get.assert_called_once_with("iris_test")

    @patch("docker.from_env")
    def test_get_existing_not_found(self, mock_docker_from_env):
        """Test getting existing container that doesn't exist."""
        from docker.errors import NotFound

        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client
        mock_client.containers.get.side_effect = NotFound("Not found")

        result = IRISContainerManager.get_existing("iris_test")

        assert result is None

    @patch("docker.from_env")
    def test_get_existing_docker_error(self, mock_docker_from_env):
        """Test getting existing container with Docker error that gets translated."""
        from docker.errors import DockerException

        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client
        # Use error message that will be translated to ConnectionError (daemon/cannot connect)
        mock_client.containers.get.side_effect = DockerException("Cannot connect to docker daemon")

        with pytest.raises(ConnectionError):
            IRISContainerManager.get_existing("iris_test")

    @patch("docker.from_env")
    def test_get_docker_client_success(self, mock_docker_from_env):
        """Test getting Docker client successfully."""
        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        mock_client = MagicMock()
        mock_docker_from_env.return_value = mock_client
        mock_client.ping.return_value = True

        result = IRISContainerManager.get_docker_client()

        assert result is mock_client
        mock_client.ping.assert_called_once()

    @patch("docker.from_env")
    def test_get_docker_client_connection_error(self, mock_docker_from_env):
        """Test Docker client connection error."""
        from docker.errors import DockerException

        from iris_devtester.utils.iris_container_adapter import IRISContainerManager

        mock_docker_from_env.side_effect = DockerException("Connection refused")

        with pytest.raises(ConnectionError) as exc_info:
            IRISContainerManager.get_docker_client()

        error_msg = str(exc_info.value)
        assert "Docker daemon" in error_msg or "Docker" in error_msg


# ====================
# translate_docker_error Tests
# ====================


class TestTranslateDockerError:
    """Test translate_docker_error() function."""

    def test_translate_volume_mount_error(self):
        """Test translating volume mount error."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        config = ContainerConfig(volumes=["./data:/external"])
        original_error = Exception("volume mount failed: permission denied")

        result = translate_docker_error(original_error, config)

        assert isinstance(result, ValueError)
        assert "Volume mount failed" in str(result)
        assert "./data:/external" in str(result)

    def test_translate_port_conflict_error(self):
        """Test translating port conflict error."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        config = ContainerConfig(superserver_port=1972)
        original_error = Exception("port is already allocated")

        result = translate_docker_error(original_error, config)

        assert isinstance(result, ValueError)
        assert "Port" in str(result)
        assert "1972" in str(result)

    def test_translate_image_not_found_error(self):
        """Test translating image not found error."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        config = ContainerConfig(edition="community")
        original_error = Exception("image not found")

        result = translate_docker_error(original_error, config)

        assert isinstance(result, ValueError)
        assert "image" in str(result).lower()

    def test_translate_docker_not_running(self):
        """Test translating Docker daemon not running error."""
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        original_error = Exception("cannot connect to docker daemon")

        result = translate_docker_error(original_error, None)

        assert isinstance(result, ConnectionError)
        assert "Docker" in str(result) or "daemon" in str(result).lower()

    def test_translate_container_name_conflict(self):
        """Test translating container name already in use error."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        config = ContainerConfig(container_name="iris_test")
        original_error = Exception("container name is already in use")

        result = translate_docker_error(original_error, config)

        assert isinstance(result, ValueError)
        assert "name" in str(result).lower()

    def test_translate_architecture_mismatch(self):
        """Test translating architecture mismatch error."""
        from iris_devtester.config.container_config import ContainerConfig
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        config = ContainerConfig()
        original_error = Exception("unsupported cpu")

        result = translate_docker_error(original_error, config)

        assert isinstance(result, ValueError)
        assert "architecture" in str(result).lower()

    def test_translate_unknown_error_passthrough(self):
        """Test that unknown errors pass through unchanged."""
        from iris_devtester.utils.iris_container_adapter import translate_docker_error

        original_error = Exception("some unknown error")

        result = translate_docker_error(original_error, None)

        assert result is original_error


# ====================
# LangChainIRISContainer Tests
# ====================


class TestLangChainIRISContainer:
    """Test LangChainIRISContainer class."""

    def test_langchain_container_import(self):
        """Test that LangChainIRISContainer can be imported."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer

        assert LangChainIRISContainer is not None

    def test_langchain_container_inherits_iris_container(self):
        """Test that LangChainIRISContainer inherits from IRISContainer."""
        from iris_devtester.containers.iris_container import IRISContainer
        from iris_devtester.integrations.langchain import LangChainIRISContainer

        assert issubclass(LangChainIRISContainer, IRISContainer)

    def test_get_connection_string_format(self):
        """Test get_connection_string returns properly formatted connection string."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer
        from unittest.mock import MagicMock, patch

        container = LangChainIRISContainer()

        # Mock dependencies
        with patch.object(container, "get_connection", return_value=MagicMock()):
            with patch.object(container, "get_container_host_ip", return_value="localhost"):
                with patch.object(container, "get_exposed_port", return_value=1972):
                    with patch.object(container, "username", "_SYSTEM", create=True):
                        with patch.object(container, "password", "SYS", create=True):
                            with patch.object(container, "namespace", "USER", create=True):
                                conn_str = container.get_connection_string()

        assert "iris://" in conn_str
        assert "_SYSTEM" in conn_str
        assert "SYS" in conn_str
        assert "USER" in conn_str
        assert "localhost:1972" in conn_str

    def test_get_langchain_vectorstore_import_error(self):
        """Test get_langchain_vectorstore raises ImportError when langchain-iris not installed."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer
        from unittest.mock import patch

        container = LangChainIRISContainer()

        # Mock missing langchain-iris import
        def mock_import(name, *args, **kwargs):
            if "langchain_iris" in name:
                raise ImportError("No module named 'langchain_iris'")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                container.get_langchain_vectorstore(MagicMock())

            assert "langchain-iris" in str(exc_info.value).lower()

    def test_get_langchain_chat_history_import_error(self):
        """Test get_langchain_chat_history raises ImportError when not available."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer

        container = LangChainIRISContainer()

        # Mock missing chat history import
        def mock_import(name, *args, **kwargs):
            if "langchain_iris" in name:
                raise ImportError("No module named 'langchain_iris'")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError) as exc_info:
                container.get_langchain_chat_history("session-123")

            assert "langchain" in str(exc_info.value).lower()

    def test_get_langchain_vectorstore_success(self):
        """Test get_langchain_vectorstore successfully creates vector store."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer

        container = LangChainIRISContainer()

        # Mock dependencies
        mock_embedding = MagicMock()
        mock_vectorstore = MagicMock()

        # Mock langchain_iris modules
        mock_langchain_iris = MagicMock()
        mock_langchain_iris.IRISVector = MagicMock(return_value=mock_vectorstore)

        with patch.dict(sys.modules, {"langchain_iris": mock_langchain_iris, "langchain_iris.vectorstores": mock_langchain_iris}):
            with patch.object(container, "get_connection", return_value=MagicMock()):
                with patch.object(container, "get_connection_string", return_value="iris://user:pass@host:1972/USER"):
                    result = container.get_langchain_vectorstore(mock_embedding, "test_collection")

        assert result is mock_vectorstore

    def test_get_langchain_chat_history_success(self):
        """Test get_langchain_chat_history successfully creates chat history."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer

        container = LangChainIRISContainer()

        mock_history = MagicMock()

        # Mock langchain_iris modules
        mock_langchain_iris = MagicMock()
        mock_langchain_iris.IRISChatMessageHistory = MagicMock(return_value=mock_history)

        with patch.dict(sys.modules, {"langchain_iris": mock_langchain_iris}):
            with patch.object(container, "get_connection_string", return_value="iris://user:pass@host:1972/USER"):
                result = container.get_langchain_chat_history("session-123")

        assert result is mock_history

    def test_for_rag_pipeline_with_namespace(self):
        """Test for_rag_pipeline factory method with custom namespace."""
        from iris_devtester.integrations.langchain import LangChainIRISContainer

        mock_embedding = MagicMock()
        mock_vectorstore = MagicMock()

        # Mock the class methods
        mock_container = MagicMock()
        mock_container.get_langchain_vectorstore.return_value = mock_vectorstore

        with patch.object(LangChainIRISContainer, "community", return_value=mock_container):
            container, vectorstore = LangChainIRISContainer.for_rag_pipeline(
                mock_embedding, namespace="CUSTOM"
            )

        assert container is mock_container
        assert vectorstore is mock_vectorstore
        mock_container.start.assert_called_once()
        mock_container.get_langchain_vectorstore.assert_called_once_with(mock_embedding)


# ====================
# ConnectionProbe Tests
# ====================


class TestConnectionProbe:
    """Test ConnectionProbe dataclass."""

    def test_probe_instantiation(self):
        """Test creating ConnectionProbe instance."""
        from iris_devtester.diagnostics import ConnectionProbe

        probe = ConnectionProbe(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            iris_version="2025.1",
            schemas={"User": 10},
            latency_ms=50.0,
        )

        assert probe.host == "localhost"
        assert probe.port == 1972
        assert probe.namespace == "USER"
        assert probe.username == "_SYSTEM"
        assert probe.iris_version == "2025.1"
        assert probe.schemas == {"User": 10}
        assert probe.latency_ms == 50.0

    def test_probe_report_format(self):
        """Test ConnectionProbe.report() returns formatted string."""
        from iris_devtester.diagnostics import ConnectionProbe

        probe = ConnectionProbe(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            iris_version="2025.1",
            schemas={"User": 10, "Config": 5},
            latency_ms=50.5,
        )

        report = probe.report()

        assert "localhost:1972" in report
        assert "USER" in report
        assert "_SYSTEM" in report
        assert "2025.1" in report
        assert "50.5" in report
        assert "User: 10" in report
        assert "Config: 5" in report

    def test_probe_report_no_schemas(self):
        """Test ConnectionProbe.report() when no schemas visible."""
        from iris_devtester.diagnostics import ConnectionProbe

        probe = ConnectionProbe(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            iris_version="2025.1",
            schemas={},
            latency_ms=50.0,
        )

        report = probe.report()

        assert "No schemas visible" in report

    def test_probe_report_with_error(self):
        """Test ConnectionProbe.report() includes error if present."""
        from iris_devtester.diagnostics import ConnectionProbe

        probe = ConnectionProbe(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            iris_version="unknown",
            schemas={},
            latency_ms=100.0,
            error="Connection timeout",
        )

        report = probe.report()

        assert "Connection timeout" in report


# ====================
# probe_connection Tests
# ====================


class TestProbeConnection:
    """Test probe_connection() function."""

    def test_probe_connection_success(self):
        """Test probe_connection with successful connection."""
        from iris_devtester.diagnostics import probe_connection

        # Mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.connection_info = None

        # Setup cursor responses
        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),  # $ZVERSION
            ("USER",),  # $NAMESPACE
        ]
        mock_cursor.fetchall.return_value = [
            ("User", 10),
            ("Config", 5),
        ]

        probe = probe_connection(mock_conn)

        assert probe.host == "unknown"
        assert probe.iris_version == "IRIS 2025.1"
        assert probe.namespace == "USER"
        assert probe.schemas == {"User": 10, "Config": 5}
        assert probe.error is None
        assert probe.latency_ms >= 0

    def test_probe_connection_error_handling(self):
        """Test probe_connection handles connection errors."""
        from iris_devtester.diagnostics import probe_connection

        # Mock connection that raises an error
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Connection refused")

        probe = probe_connection(mock_conn)

        assert probe.iris_version == "unknown"
        assert probe.schemas == {}
        assert probe.error is not None
        assert "Connection refused" in probe.error

    def test_probe_connection_with_connection_info(self):
        """Test probe_connection extracts connection_info when available."""
        from iris_devtester.diagnostics import probe_connection

        # Mock connection with connection_info
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup connection_info
        mock_ci = MagicMock()
        mock_ci.hostname = "iris.example.com"
        mock_ci.port = 1972
        mock_conn.connection_info = mock_ci

        # Setup cursor responses
        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),
            ("USER",),
        ]
        mock_cursor.fetchall.return_value = [("User", 5)]

        probe = probe_connection(mock_conn)

        assert probe.host == "iris.example.com"
        assert probe.port == 1972

    def test_probe_connection_no_connection_info(self):
        """Test probe_connection when connection_info is None."""
        from iris_devtester.diagnostics import probe_connection

        # Mock connection without connection_info
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.connection_info = None

        # Setup cursor responses
        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),
            ("USER",),
        ]
        mock_cursor.fetchall.return_value = [("User", 5)]

        probe = probe_connection(mock_conn)

        # Should work with defaults when no connection_info
        assert probe.host == "unknown"
        assert probe.port == 0
        assert probe.iris_version == "IRIS 2025.1"


# ====================
# build_diagnostic_error Tests
# ====================


class TestBuildDiagnosticError:
    """Test build_diagnostic_error() function."""

    def test_build_diagnostic_error_table_not_found_missing_schema(self):
        """Test diagnostic error for table not found due to missing schema."""
        from iris_devtester.diagnostics import build_diagnostic_error

        # Mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup cursor responses (only User schema visible, not Config)
        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),
            ("USER",),
        ]
        mock_cursor.fetchall.return_value = [("User", 5)]

        original_error = Exception(
            "SQLCODE: <-30> Table 'Config.MyTable' not found at line 1, column 15"
        )

        error = build_diagnostic_error(original_error, mock_conn, -30)

        assert error.sqlcode == -30
        assert "Table or view not found" in str(error)
        assert "Config" in str(error) or "schema" in str(error).lower()

    def test_build_diagnostic_error_sqlcode_message(self):
        """Test diagnostic error includes SQLCODE message."""
        from iris_devtester.diagnostics import build_diagnostic_error

        # Mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup cursor responses
        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),
            ("USER",),
        ]
        mock_cursor.fetchall.return_value = []

        original_error = Exception("SQLCODE: <-23> Label not applicable")

        error = build_diagnostic_error(original_error, mock_conn, -23)

        assert error.sqlcode == -23
        assert "Label not applicable" in str(error)

    def test_extract_sqlcode(self):
        """Test _extract_sqlcode extracts SQLCODE from error text."""
        from iris_devtester.diagnostics import _extract_sqlcode

        text = "SQLCODE: <-30> Table not found"
        sqlcode = _extract_sqlcode(text)

        assert sqlcode == -30

    def test_extract_table_name(self):
        """Test _extract_table_name extracts table name from error text."""
        from iris_devtester.diagnostics import _extract_table_name

        text = "Table 'User.MyTable' not found"
        table_name = _extract_table_name(text)

        assert table_name == "User.MyTable"

    def test_build_diagnostic_error_no_schemas(self):
        """Test build_diagnostic_error when no schemas are visible."""
        from iris_devtester.diagnostics import build_diagnostic_error

        # Mock connection with no schemas
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),
            ("USER",),
        ]
        # Empty schemas
        mock_cursor.fetchall.return_value = []

        original_error = Exception("SQLCODE: <-30> Table 'User.MyTable' not found")

        error = build_diagnostic_error(original_error, mock_conn, -30)

        assert error.sqlcode == -30
        assert "No schemas visible" in str(error)
        assert "initialize_schema()" in str(error)

    def test_build_diagnostic_error_table_found_in_visible_schemas(self):
        """Test build_diagnostic_error when table not found but schemas are visible."""
        from iris_devtester.diagnostics import build_diagnostic_error

        # Mock connection with visible schemas
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            ("IRIS 2025.1",),
            ("USER",),
        ]
        # Some schemas visible but not Config
        mock_cursor.fetchall.return_value = [("User", 5), ("Public", 3)]

        original_error = Exception("SQLCODE: <-30> Table 'User.MyTable' not found")

        error = build_diagnostic_error(original_error, mock_conn, -30)

        assert error.sqlcode == -30
        assert "Visible schemas" in str(error)
        assert "User" in str(error)


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
