"""
Unit tests for configuration discovery.

Tests configuration auto-discovery from environment, .env files, Docker, and defaults.
"""

import os
import pytest
from unittest.mock import Mock, patch, mock_open


class TestConfigDiscovery:
    """Test configuration discovery functionality."""

    def test_can_import(self):
        """Test that discover_config function can be imported."""
        from iris_devtester.config.discovery import discover_config

        assert callable(discover_config)

    @patch.dict(os.environ, {
        "IRIS_HOST": "iris.example.com",
        "IRIS_PORT": "1973",
        "IRIS_NAMESPACE": "MYAPP",
        "IRIS_USERNAME": "admin",
        "IRIS_PASSWORD": "secret"
    }, clear=False)
    def test_discover_from_environment(self):
        """Test discovery from environment variables."""
        from iris_devtester.config.discovery import discover_config

        config = discover_config()
        assert config.host == "iris.example.com"
        assert config.port == 1973
        assert config.namespace == "MYAPP"
        assert config.username == "admin"
        assert config.password == "secret"

    @patch.dict(os.environ, {}, clear=True)
    def test_discover_uses_defaults_when_no_env(self):
        """Test that defaults are used when no environment variables."""
        from iris_devtester.config.discovery import discover_config

        config = discover_config()
        assert config.host == "localhost"
        assert config.port == 1972
        assert config.namespace == "USER"

    @patch.dict(os.environ, {"IRIS_HOST": "custom.host"}, clear=False)
    def test_partial_environment_merges_with_defaults(self):
        """Test that partial env vars merge with defaults."""
        from iris_devtester.config.discovery import discover_config

        config = discover_config()
        assert config.host == "custom.host"  # From env
        assert config.port == 1972  # From defaults

    @patch.dict(os.environ, {}, clear=True)
    @patch("builtins.open", mock_open(read_data="IRIS_HOST=dotenv.host\nIRIS_PORT=1974\n"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_discover_from_dotenv_file(self, mock_exists):
        """Test discovery from .env file."""
        from iris_devtester.config.discovery import discover_config

        config = discover_config()
        assert config.host == "dotenv.host"
        assert config.port == 1974

    @patch.dict(os.environ, {"IRIS_HOST": "env.host"}, clear=False)
    @patch("builtins.open", mock_open(read_data="IRIS_HOST=dotenv.host\n"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_environment_takes_precedence_over_dotenv(self, mock_exists):
        """Test that environment variables override .env file."""
        from iris_devtester.config.discovery import discover_config

        config = discover_config()
        # Environment should win
        assert config.host == "env.host"

    def test_explicit_config_overrides_discovery(self):
        """Test that explicit config parameters override discovery."""
        from iris_devtester.config.discovery import discover_config
        from iris_devtester.config import IRISConfig

        explicit = IRISConfig(host="explicit.host", port=9999)
        config = discover_config(explicit_config=explicit)
        assert config.host == "explicit.host"
        assert config.port == 9999


class TestConfigPriorityHierarchy:
    """Test configuration priority hierarchy."""

    @patch.dict(os.environ, {"IRIS_HOST": "env.host"}, clear=False)
    @patch("builtins.open", mock_open(read_data="IRIS_HOST=dotenv.host\n"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_priority_explicit_over_env(self, mock_exists):
        """Test priority: explicit > env > .env > defaults."""
        from iris_devtester.config.discovery import discover_config
        from iris_devtester.config import IRISConfig

        # Explicit should override everything
        explicit = IRISConfig(host="explicit.host")
        config = discover_config(explicit_config=explicit)
        assert config.host == "explicit.host"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
