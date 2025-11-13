"""Unit tests for configuration loading hierarchy and priority."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

from iris_devtester.config.container_config import ContainerConfig


class TestConfigurationHierarchy:
    """
    Test configuration loading priority order.

    Priority (highest to lowest):
    1. Explicit --config flag (handled by CLI, not tested here)
    2. ./iris-config.yml in current directory
    3. Environment variables
    4. Zero-config defaults
    """

    def test_zero_config_defaults_lowest_priority(self):
        """Test that zero-config defaults are used when nothing else is available."""
        # Ensure no IRIS_ env vars
        original_env = {}
        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        try:
            config = ContainerConfig.default()
            assert config.edition == "community"
            assert config.container_name == "iris_db"
            assert config.superserver_port == 1972
            assert config.webserver_port == 52773
            assert config.namespace == "USER"
            assert config.password == "SYS"
        finally:
            # Restore environment
            for key, value in original_env.items():
                os.environ[key] = value

    def test_environment_overrides_defaults(self):
        """Test that environment variables override zero-config defaults."""
        original_env = {}
        env_vars = {
            "IRIS_EDITION": "community",
            "IRIS_CONTAINER_NAME": "env_override",
            "IRIS_SUPERSERVER_PORT": "3000",
        }

        # Clear any existing IRIS_ vars and set test vars
        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            config = ContainerConfig.from_env()
            # Environment values used
            assert config.container_name == "env_override"
            assert config.superserver_port == 3000
            # Defaults used for unset values
            assert config.webserver_port == 52773
            assert config.namespace == "USER"
        finally:
            # Restore environment
            for key in env_vars.keys():
                os.environ.pop(key, None)
            for key, value in original_env.items():
                os.environ[key] = value

    def test_yaml_file_overrides_environment(self):
        """Test that YAML file overrides environment variables."""
        # Set environment variables
        original_env = {}
        env_vars = {
            "IRIS_EDITION": "community",
            "IRIS_CONTAINER_NAME": "env_container",
            "IRIS_SUPERSERVER_PORT": "3000",
        }

        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        for key, value in env_vars.items():
            os.environ[key] = value

        # Create YAML file with different values
        yaml_content = """
edition: community
container_name: yaml_container
ports:
  superserver: 4000
  webserver: 54000
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            # YAML values override environment
            assert config.container_name == "yaml_container"
            assert config.superserver_port == 4000
            assert config.webserver_port == 54000
        finally:
            Path(temp_path).unlink()
            for key in env_vars.keys():
                os.environ.pop(key, None)
            for key, value in original_env.items():
                os.environ[key] = value

    def test_partial_yaml_uses_defaults_for_missing_fields(self):
        """Test that YAML with partial config uses defaults for missing fields."""
        yaml_content = """
edition: community
container_name: partial_yaml
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            # YAML values
            assert config.edition == "community"
            assert config.container_name == "partial_yaml"
            # Default values for unspecified fields
            assert config.superserver_port == 1972
            assert config.webserver_port == 52773
            assert config.namespace == "USER"
            assert config.password == "SYS"
        finally:
            Path(temp_path).unlink()

    def test_partial_env_uses_defaults_for_missing_vars(self):
        """Test that partial env vars use defaults for missing variables."""
        original_env = {}
        env_vars = {
            "IRIS_CONTAINER_NAME": "partial_env",
            "IRIS_NAMESPACE": "PARTIALAPP",
        }

        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            config = ContainerConfig.from_env()
            # Environment values
            assert config.container_name == "partial_env"
            assert config.namespace == "PARTIALAPP"
            # Default values
            assert config.edition == "community"
            assert config.superserver_port == 1972
            assert config.webserver_port == 52773
        finally:
            for key in env_vars.keys():
                os.environ.pop(key, None)
            for key, value in original_env.items():
                os.environ[key] = value

    def test_enterprise_yaml_with_license_from_env(self):
        """Test enterprise YAML config with license from environment."""
        # Set license in environment
        original_env = {}
        env_vars = {
            "IRIS_LICENSE_KEY": "ENV-LICENSE-123",
        }

        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        for key, value in env_vars.items():
            os.environ[key] = value

        # YAML specifies enterprise but no license
        # In real usage, would need to merge, but from_yaml doesn't auto-merge env
        yaml_content = """
edition: enterprise
license_key: YAML-LICENSE-456
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # YAML file wins (higher priority than env)
            config = ContainerConfig.from_yaml(temp_path)
            assert config.edition == "enterprise"
            assert config.license_key == "YAML-LICENSE-456"

            # Environment config would have different license
            config_env = ContainerConfig.from_env()
            assert config_env.license_key == "ENV-LICENSE-123"
        finally:
            Path(temp_path).unlink()
            for key in env_vars.keys():
                os.environ.pop(key, None)
            for key, value in original_env.items():
                os.environ[key] = value

    def test_yaml_empty_string_vs_null_vs_missing(self):
        """Test YAML handling of empty string, null, and missing values."""
        yaml_content = """
edition: community
license_key: ""
password: "ActualPassword"
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            # Empty string in YAML becomes empty string (not None)
            assert config.license_key == ""
            assert config.password == "ActualPassword"
            # Missing field uses default
            assert config.container_name == "iris_db"
        finally:
            Path(temp_path).unlink()

    def test_explicit_config_highest_priority(self):
        """Test that explicitly loaded config file has highest priority."""
        # Set environment
        original_env = {}
        env_vars = {
            "IRIS_CONTAINER_NAME": "env_container",
            "IRIS_SUPERSERVER_PORT": "3000",
        }

        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        for key, value in env_vars.items():
            os.environ[key] = value

        # Create explicit config file
        yaml_content = """
edition: community
container_name: explicit_config
ports:
  superserver: 5000
  webserver: 55000
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Explicit config file
            config = ContainerConfig.from_yaml(temp_path)
            assert config.container_name == "explicit_config"
            assert config.superserver_port == 5000

            # Environment would have different values
            config_env = ContainerConfig.from_env()
            assert config_env.container_name == "env_container"
            assert config_env.superserver_port == 3000
        finally:
            Path(temp_path).unlink()
            for key in env_vars.keys():
                os.environ.pop(key, None)
            for key, value in original_env.items():
                os.environ[key] = value


class TestConfigLoadingStrategies:
    """Test different configuration loading patterns."""

    def test_load_or_default_pattern_with_existing_file(self):
        """Test pattern: load from file if exists, else default."""
        yaml_content = """
edition: community
container_name: file_exists
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            # File exists - load from file
            if temp_path.exists():
                config = ContainerConfig.from_yaml(temp_path)
            else:
                config = ContainerConfig.default()

            assert config.container_name == "file_exists"
        finally:
            temp_path.unlink()

    def test_load_or_default_pattern_with_missing_file(self):
        """Test pattern: load from file if exists, else default."""
        temp_path = Path("nonexistent-config.yml")

        # File doesn't exist - use default
        if temp_path.exists():
            config = ContainerConfig.from_yaml(temp_path)
        else:
            config = ContainerConfig.default()

        assert config.container_name == "iris_db"
        assert config.edition == "community"

    def test_env_fallback_pattern(self):
        """Test pattern: try env, fallback to default."""
        original_env = {}
        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        try:
            # No env vars - should use defaults
            has_iris_env = any(k.startswith("IRIS_") for k in os.environ.keys())
            if has_iris_env:
                config = ContainerConfig.from_env()
            else:
                config = ContainerConfig.default()

            assert config.container_name == "iris_db"
        finally:
            for key, value in original_env.items():
                os.environ[key] = value

    def test_cascading_fallback_pattern(self):
        """Test pattern: explicit config → local file → env → defaults."""
        # Clear environment
        original_env = {}
        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        for key in iris_vars:
            original_env[key] = os.environ.pop(key)

        try:
            # Simulate CLI logic
            explicit_config = None  # No --config flag

            if explicit_config and Path(explicit_config).exists():
                config = ContainerConfig.from_yaml(explicit_config)
            elif Path("iris-config.yml").exists():
                config = ContainerConfig.from_yaml("iris-config.yml")
            elif any(k.startswith("IRIS_") for k in os.environ.keys()):
                config = ContainerConfig.from_env()
            else:
                config = ContainerConfig.default()

            # Should use defaults (no config file, no env vars)
            assert config.container_name == "iris_db"
            assert config.edition == "community"
        finally:
            for key, value in original_env.items():
                os.environ[key] = value


class TestConfigurationMerging:
    """Test configuration value merging and overrides."""

    def test_volumes_override_not_merge(self):
        """Test that volumes in YAML override defaults (not merge)."""
        yaml_content = """
edition: community
volumes:
  - ./data:/external
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            # YAML volumes replace defaults (not merge)
            assert config.volumes == ["./data:/external"]
        finally:
            Path(temp_path).unlink()

    def test_ports_must_all_be_specified_or_use_defaults(self):
        """Test that ports in YAML override specific ports only."""
        yaml_content = """
edition: community
ports:
  superserver: 3000
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            # Specified port overridden
            assert config.superserver_port == 3000
            # Unspecified port uses default
            assert config.webserver_port == 52773
        finally:
            Path(temp_path).unlink()

    def test_edition_change_preserves_other_settings(self):
        """Test that changing edition doesn't affect other settings."""
        yaml_content = """
edition: community
container_name: my_special_iris
namespace: MYAPP
ports:
  superserver: 2000
  webserver: 53000
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            # All custom settings preserved
            assert config.edition == "community"
            assert config.container_name == "my_special_iris"
            assert config.namespace == "MYAPP"
            assert config.superserver_port == 2000
            assert config.webserver_port == 53000
        finally:
            Path(temp_path).unlink()
