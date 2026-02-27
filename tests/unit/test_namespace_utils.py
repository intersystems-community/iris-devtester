import unittest
from unittest.mock import MagicMock, patch

from iris_devtester.config import IRISConfig
from iris_devtester.utils.namespace import (
    check_namespace_exists,
    check_namespace_via_iris_connect,
    create_namespace,
    create_namespace_via_iris_connect,
    ensure_namespace_exists,
)


class TestNamespaceUtils(unittest.TestCase):
    def setUp(self):
        self.config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="NEW_NS",
            container_name="test_iris"
        )

    @patch("subprocess.run")
    def test_check_namespace_exists_true(self, mock_run):
        # Mock IRIS returning "1" for existence check
        mock_run.return_value = MagicMock(
            stdout=b"1\n",
            returncode=0
        )
        
        exists = check_namespace_exists("test_iris", "NEW_NS")
        self.assertTrue(exists)
        
        # Verify the command sent to docker
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIn("docker", cmd)
        self.assertIn("exec", cmd)
        self.assertIn("test_iris", cmd)
        self.assertIn('##class(Config.Namespaces).Exists("NEW_NS")', kwargs["input"].decode())

    @patch("subprocess.run")
    def test_check_namespace_exists_false(self, mock_run):
        # Mock IRIS returning "0"
        mock_run.return_value = MagicMock(
            stdout=b"0\n",
            returncode=0
        )
        
        exists = check_namespace_exists("test_iris", "NEW_NS")
        self.assertFalse(exists)

    @patch("subprocess.run")
    def test_create_namespace_success(self, mock_run):
        # Mock successful creation
        mock_run.return_value = MagicMock(
            stdout=b"SUCCESS\n",
            returncode=0
        )
        
        with patch("iris_devtester.utils.enable_callin.enable_callin_service") as mock_enable:
            mock_enable.return_value = (True, "OK")
            success = create_namespace("test_iris", "NEW_NS")
            self.assertTrue(success)
            mock_enable.assert_called_once_with("test_iris")

    @patch("subprocess.run")
    def test_ensure_namespace_exists_already_exists(self, mock_run):
        # Mock IRIS returning "1" for existence check
        mock_run.return_value = MagicMock(
            stdout=b"1\n",
            returncode=0
        )
        
        ensure_namespace_exists(self.config)
        
        # Verify check was called
        self.assertGreaterEqual(mock_run.call_count, 1)

    @patch("subprocess.run")
    def test_ensure_namespace_exists_creates_if_missing(self, mock_run):
        # First call: check exists -> returns "0"
        # Second call: create -> returns "SUCCESS"
        # Third call (optional): enable callin
        mock_run.side_effect = [
            MagicMock(stdout=b"0\n", returncode=0),
            MagicMock(stdout=b"SUCCESS\n", returncode=0),
            MagicMock(stdout=b"1\n", returncode=0), # enable callin
        ]
        
        ensure_namespace_exists(self.config)
        
        self.assertGreaterEqual(mock_run.call_count, 2)

    def test_ensure_namespace_exists_skips_if_auto_create_false(self):
        self.config.auto_create = False
        
        with patch("iris_devtester.utils.namespace.check_namespace_exists") as mock_check:
            ensure_namespace_exists(self.config)
            mock_check.assert_not_called()

    def test_ensure_namespace_exists_skips_if_remote_and_no_opt_in(self):
        self.config.host = "remote.host"
        self.config.auto_create = None  # Use smart default
        
        with patch("iris_devtester.utils.namespace.check_namespace_exists") as mock_check:
            ensure_namespace_exists(self.config)
            mock_check.assert_not_called()

    def test_ensure_namespace_exists_proceeds_if_remote_and_opt_in(self):
        self.config.host = "remote.host"
        self.config.auto_create = True
        
        with patch("iris_devtester.utils.namespace.check_namespace_exists") as mock_check:
            mock_check.return_value = True
            ensure_namespace_exists(self.config)
            mock_check.assert_called_once()


class TestCheckNamespaceViaIrisConnect(unittest.TestCase):
    """Tests for check_namespace_via_iris_connect() — Contract 2."""

    def setUp(self):
        self.config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            password="SYS",
        )

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_namespace_exists(self, mock_iris):
        """Contract 2 scenario 1: Namespace exists → returns True."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 1  # exists

        result = check_namespace_via_iris_connect(self.config, "USER")

        self.assertTrue(result)
        mock_iris.connect.assert_called_once_with(
            hostname="localhost",
            port=1972,
            namespace="%SYS",
            username="_SYSTEM",
            password="SYS",
        )
        mock_iris_obj.classMethodValue.assert_called_once_with(
            "Config.Namespaces", "Exists", "USER"
        )
        mock_conn.close.assert_called_once()

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_namespace_not_found(self, mock_iris):
        """Contract 2 scenario 2: Namespace does not exist → returns False."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 0  # does not exist

        result = check_namespace_via_iris_connect(self.config, "NONEXISTENT")

        self.assertFalse(result)
        mock_conn.close.assert_called_once()

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_access_denied(self, mock_iris):
        """Contract 2 scenario 3: %SYS access denied → returns False with warning."""
        mock_iris.connect.side_effect = Exception("Access denied to namespace %SYS")

        result = check_namespace_via_iris_connect(self.config, "USER")

        self.assertFalse(result)

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_connection_refused(self, mock_iris):
        """Contract 2 scenario 4: Connection refused → returns False with warning."""
        mock_iris.connect.side_effect = ConnectionRefusedError("Connection refused")

        result = check_namespace_via_iris_connect(self.config, "USER")

        self.assertFalse(result)

    @patch("iris_devtester.utils.namespace._iris_module", None)
    def test_iris_module_not_available(self):
        """iris module not installed → returns False gracefully."""
        result = check_namespace_via_iris_connect(self.config, "USER")
        self.assertFalse(result)


class TestCreateNamespaceViaIrisConnect(unittest.TestCase):
    """Tests for create_namespace_via_iris_connect() — Contract 3."""

    def setUp(self):
        self.config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            password="SYS",
        )

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_create_success(self, mock_iris):
        """Namespace created successfully → returns True."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 1  # success

        result = create_namespace_via_iris_connect(self.config, "NEW_NS")

        self.assertTrue(result)
        mock_iris_obj.classMethodValue.assert_called_once_with(
            "Config.Namespaces", "Create", "NEW_NS"
        )
        mock_conn.close.assert_called_once()

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_create_failure(self, mock_iris):
        """Config.Namespaces.Create returns failure → returns False."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 0  # failure

        result = create_namespace_via_iris_connect(self.config, "NEW_NS")

        self.assertFalse(result)
        mock_conn.close.assert_called_once()

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_access_denied(self, mock_iris):
        """Access denied → returns False gracefully."""
        mock_iris.connect.side_effect = Exception("Access denied to namespace %SYS")

        result = create_namespace_via_iris_connect(self.config, "NEW_NS")

        self.assertFalse(result)

    @patch("iris_devtester.utils.namespace._iris_module")
    def test_connection_error(self, mock_iris):
        """Connection error → returns False gracefully."""
        mock_iris.connect.side_effect = ConnectionRefusedError("Connection refused")

        result = create_namespace_via_iris_connect(self.config, "NEW_NS")

        self.assertFalse(result)

    @patch("iris_devtester.utils.namespace._iris_module", None)
    def test_iris_module_not_available(self):
        """iris module not installed → returns False gracefully."""
        result = create_namespace_via_iris_connect(self.config, "NEW_NS")
        self.assertFalse(result)


class TestEnsureNamespaceStrategySelection(unittest.TestCase):
    """Tests for ensure_namespace_exists() strategy selection — Contract 1 (T007+T008)."""

    def _make_config(self, host="localhost", container_name=None, auto_create=None):
        return IRISConfig(
            host=host,
            port=1972,
            namespace="TEST_NS",
            username="_SYSTEM",
            password="SYS",
            container_name=container_name,
            auto_create=auto_create,
        )

    # --- Contract 1 scenario 1: auto_create=False → skip entirely ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_auto_create_false_skips_all(self, mock_iris, mock_subprocess):
        """auto_create=False: no subprocess, no iris.connect()."""
        config = self._make_config(auto_create=False)
        result = ensure_namespace_exists(config)
        self.assertTrue(result)
        mock_subprocess.assert_not_called()
        mock_iris.connect.assert_not_called()

    # --- Contract 1 scenario 2: container_name set → Docker exec ---
    @patch("subprocess.run")
    def test_container_name_set_uses_docker_exec(self, mock_subprocess):
        """container_name='my-iris': uses Docker exec strategy."""
        mock_subprocess.return_value = MagicMock(stdout=b"1\n", returncode=0)
        config = self._make_config(container_name="my-iris", auto_create=True)
        ensure_namespace_exists(config)
        # Verify subprocess was called with the provided container name
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]
        self.assertIn("my-iris", cmd)

    # --- Contract 1 scenario 3: auto_create=True, no container, localhost → iris.connect() ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_true_no_container_localhost_uses_iris_connect(self, mock_iris, mock_subprocess):
        """auto_create=True, no container_name, localhost: uses iris.connect()."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 1  # namespace exists

        config = self._make_config(host="localhost", auto_create=True)
        result = ensure_namespace_exists(config)

        self.assertTrue(result)
        mock_subprocess.assert_not_called()
        mock_iris.connect.assert_called_once()

    # --- Contract 1 scenario 4: auto_create=True, no container, remote → iris.connect() ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_true_no_container_remote_uses_iris_connect(self, mock_iris, mock_subprocess):
        """auto_create=True, no container_name, remote: uses iris.connect()."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 1

        config = self._make_config(host="10.0.0.5", auto_create=True)
        result = ensure_namespace_exists(config)

        self.assertTrue(result)
        mock_subprocess.assert_not_called()
        mock_iris.connect.assert_called_once()

    # --- Contract 1 scenario 5: auto_create=None, localhost, no container → iris.connect() ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_none_localhost_no_container_uses_iris_connect(self, mock_iris, mock_subprocess):
        """auto_create=None, localhost, no container: resolves True, uses iris.connect()."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 1

        config = self._make_config(host="localhost", auto_create=None)
        result = ensure_namespace_exists(config)

        self.assertTrue(result)
        mock_subprocess.assert_not_called()

    # --- Contract 1 scenario 6: auto_create=None, remote, no container → skip ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_none_remote_no_container_skips(self, mock_iris, mock_subprocess):
        """auto_create=None, remote, no container: resolves False, skips."""
        config = self._make_config(host="10.0.0.5", auto_create=None)
        result = ensure_namespace_exists(config)
        self.assertTrue(result)
        mock_subprocess.assert_not_called()
        mock_iris.connect.assert_not_called()

    # --- Contract 1 scenario 7: auto_create=None, localhost, container_name set → Docker exec ---
    @patch("subprocess.run")
    def test_none_localhost_with_container_uses_docker(self, mock_subprocess):
        """auto_create=None, localhost, container_name='my-iris': uses Docker exec."""
        mock_subprocess.return_value = MagicMock(stdout=b"1\n", returncode=0)
        config = self._make_config(host="localhost", container_name="my-iris", auto_create=None)
        ensure_namespace_exists(config)
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]
        self.assertIn("my-iris", cmd)

    # --- Contract 1 scenario 8: empty string container_name treated as unset ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_empty_string_container_treated_as_unset(self, mock_iris, mock_subprocess):
        """container_name='' (empty): treated as unset, uses iris.connect()."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 1

        config = self._make_config(host="localhost", container_name="", auto_create=True)
        result = ensure_namespace_exists(config)

        self.assertTrue(result)
        mock_subprocess.assert_not_called()

    # --- Contract 4 (T008): No hardcoded iris_db ---
    @patch("subprocess.run")
    @patch("iris_devtester.utils.namespace._iris_module")
    def test_no_hardcoded_iris_db(self, mock_iris, mock_subprocess):
        """NEGATIVE: No subprocess call should ever contain 'iris_db' when container_name=None."""
        mock_conn = MagicMock()
        mock_iris_obj = MagicMock()
        mock_iris.connect.return_value = mock_conn
        mock_iris.createIRIS.return_value = mock_iris_obj
        mock_iris_obj.classMethodValue.return_value = 0  # not found

        config = self._make_config(host="localhost", container_name=None, auto_create=True)
        ensure_namespace_exists(config)

        # subprocess should never be called when container_name is None
        mock_subprocess.assert_not_called()
