import unittest
from unittest.mock import MagicMock, patch

from iris_devtester.config import IRISConfig
from iris_devtester.utils.namespace import (
    check_namespace_exists,
    create_namespace,
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
