"""Unit tests for ContainerConfig data model."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from pydantic import ValidationError

from iris_devtester.config.container_config import ContainerConfig


class TestContainerConfigValidation:
    """Test ContainerConfig validation rules."""

    def test_default_config_is_valid(self):
        """Test that default configuration is valid."""
        config = ContainerConfig.default()
        assert config.edition == "community"
        assert config.container_name == "iris_db"
        assert config.superserver_port == 1972
        assert config.webserver_port == 52773
        assert config.namespace == "USER"
        assert config.password == "SYS"
        assert config.license_key is None
        assert config.volumes == []
        assert config.image_tag == "latest"

    def test_explicit_construction_is_valid(self):
        """Test explicit construction with all fields."""
        config = ContainerConfig(
            edition="community",
            container_name="my_iris",
            superserver_port=2000,
            webserver_port=53000,
            namespace="MYAPP",
            password="SecurePass123",
            license_key=None,
            volumes=["./data:/external"],
            image_tag="2024.1"
        )
        assert config.edition == "community"
        assert config.container_name == "my_iris"
        assert config.superserver_port == 2000
        assert config.webserver_port == 53000
        assert config.namespace == "MYAPP"
        assert config.password == "SecurePass123"
        assert config.volumes == ["./data:/external"]
        assert config.image_tag == "2024.1"

    def test_invalid_superserver_port_below_range(self):
        """Test that superserver_port below 1024 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(superserver_port=1023)

        assert "superserver_port" in str(exc_info.value)

    def test_invalid_superserver_port_above_range(self):
        """Test that superserver_port above 65535 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(superserver_port=65536)

        assert "superserver_port" in str(exc_info.value)

    def test_invalid_webserver_port_below_range(self):
        """Test that webserver_port below 1024 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(webserver_port=1023)

        assert "webserver_port" in str(exc_info.value)

    def test_invalid_webserver_port_above_range(self):
        """Test that webserver_port above 65535 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(webserver_port=65536)

        assert "webserver_port" in str(exc_info.value)

    def test_enterprise_edition_requires_license_key(self):
        """Test that enterprise edition requires license_key."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(edition="enterprise", license_key=None)

        error_str = str(exc_info.value)
        assert "license_key" in error_str.lower()
        assert "required" in error_str.lower()

    def test_enterprise_edition_with_license_key_is_valid(self):
        """Test that enterprise edition with license_key is valid."""
        config = ContainerConfig(
            edition="enterprise",
            license_key="ABC-123-DEF-456"
        )
        assert config.edition == "enterprise"
        assert config.license_key == "ABC-123-DEF-456"

    def test_community_edition_does_not_require_license_key(self):
        """Test that community edition doesn't require license_key."""
        config = ContainerConfig(edition="community")
        assert config.license_key is None

    def test_invalid_container_name_starting_with_special_char(self):
        """Test that container name starting with special char raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(container_name="-invalid")

        assert "container_name" in str(exc_info.value)

    def test_invalid_container_name_with_invalid_chars(self):
        """Test that container name with invalid chars raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(container_name="my@container")

        assert "container_name" in str(exc_info.value)

    def test_valid_container_name_with_hyphens_and_dots(self):
        """Test that container name with hyphens and dots is valid."""
        config = ContainerConfig(container_name="my-iris.db_1")
        assert config.container_name == "my-iris.db_1"

    def test_invalid_namespace_lowercase(self):
        """Test that lowercase namespace raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(namespace="user")

        assert "namespace" in str(exc_info.value)

    def test_invalid_namespace_starting_with_digit(self):
        """Test that namespace starting with digit raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(namespace="1USER")

        assert "namespace" in str(exc_info.value)

    def test_invalid_namespace_with_lowercase_letters(self):
        """Test that namespace with lowercase letters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(namespace="MyApp")

        assert "namespace" in str(exc_info.value)

    def test_valid_namespace_with_percent(self):
        """Test that namespace with % is valid."""
        config = ContainerConfig(namespace="APP%DATA")
        assert config.namespace == "APP%DATA"

    def test_valid_namespace_with_digits(self):
        """Test that namespace with digits is valid."""
        config = ContainerConfig(namespace="APP123")
        assert config.namespace == "APP123"

    def test_empty_password_raises_error(self):
        """Test that empty password raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ContainerConfig(password="")

        assert "password" in str(exc_info.value)

    def test_invalid_edition_raises_error(self):
        """Test that invalid edition raises error."""
        with pytest.raises(ValidationError):
            ContainerConfig(edition="invalid")  # type: ignore


class TestContainerConfigFromYAML:
    """Test ContainerConfig.from_yaml() class method."""

    def test_from_yaml_with_all_fields(self):
        """Test loading config from YAML with all fields."""
        yaml_content = """
edition: community
container_name: my_iris
ports:
  superserver: 2000
  webserver: 53000
namespace: MYAPP
password: SecurePass123
license_key: ""
volumes:
  - ./data:/external
  - ./backup:/backup
image_tag: "2024.1"
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            assert config.edition == "community"
            assert config.container_name == "my_iris"
            assert config.superserver_port == 2000
            assert config.webserver_port == 53000
            assert config.namespace == "MYAPP"
            assert config.password == "SecurePass123"
            assert config.volumes == ["./data:/external", "./backup:/backup"]
            assert config.image_tag == "2024.1"
        finally:
            Path(temp_path).unlink()

    def test_from_yaml_with_minimal_fields(self):
        """Test loading config from YAML with minimal fields (uses defaults)."""
        yaml_content = """
edition: community
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            assert config.edition == "community"
            # Should use defaults for other fields
            assert config.container_name == "iris_db"
            assert config.superserver_port == 1972
            assert config.webserver_port == 52773
        finally:
            Path(temp_path).unlink()

    def test_from_yaml_with_nested_ports(self):
        """Test that nested ports structure is correctly transformed."""
        yaml_content = """
edition: community
ports:
  superserver: 3000
  webserver: 54000
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            assert config.superserver_port == 3000
            assert config.webserver_port == 54000
        finally:
            Path(temp_path).unlink()

    def test_from_yaml_with_enterprise_and_license(self):
        """Test loading enterprise config with license key."""
        yaml_content = """
edition: enterprise
license_key: ABC-123-DEF-456
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ContainerConfig.from_yaml(temp_path)
            assert config.edition == "enterprise"
            assert config.license_key == "ABC-123-DEF-456"
        finally:
            Path(temp_path).unlink()

    def test_from_yaml_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            ContainerConfig.from_yaml("nonexistent.yml")


class TestContainerConfigFromEnv:
    """Test ContainerConfig.from_env() class method."""

    def test_from_env_with_all_variables(self):
        """Test loading config from environment variables."""
        env_vars = {
            "IRIS_EDITION": "community",
            "IRIS_CONTAINER_NAME": "env_iris",
            "IRIS_SUPERSERVER_PORT": "3000",
            "IRIS_WEBSERVER_PORT": "54000",
            "IRIS_NAMESPACE": "ENVAPP",
            "IRIS_PASSWORD": "EnvPass123",
            "IRIS_VOLUMES": "./data:/external,./backup:/backup",
            "IRIS_IMAGE_TAG": "2024.2",
        }

        # Set environment
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = ContainerConfig.from_env()
            assert config.edition == "community"
            assert config.container_name == "env_iris"
            assert config.superserver_port == 3000
            assert config.webserver_port == 54000
            assert config.namespace == "ENVAPP"
            assert config.password == "EnvPass123"
            assert config.volumes == ["./data:/external", "./backup:/backup"]
            assert config.image_tag == "2024.2"
        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_from_env_with_minimal_variables(self):
        """Test loading config from env with minimal vars (uses defaults)."""
        env_vars = {
            "IRIS_EDITION": "community",
        }

        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = ContainerConfig.from_env()
            assert config.edition == "community"
            # Should use defaults
            assert config.container_name == "iris_db"
            assert config.superserver_port == 1972
        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_from_env_with_enterprise_and_license(self):
        """Test loading enterprise config from environment."""
        env_vars = {
            "IRIS_EDITION": "enterprise",
            "IRIS_LICENSE_KEY": "ENV-LICENSE-KEY",
        }

        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = ContainerConfig.from_env()
            assert config.edition == "enterprise"
            assert config.license_key == "ENV-LICENSE-KEY"
        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_from_env_with_no_variables(self):
        """Test loading from env with no variables uses defaults."""
        # Ensure no IRIS_ env vars are set
        iris_vars = [k for k in os.environ.keys() if k.startswith("IRIS_")]
        original_env = {k: os.environ.pop(k) for k in iris_vars}

        try:
            config = ContainerConfig.from_env()
            # Should use all defaults
            assert config.edition == "community"
            assert config.container_name == "iris_db"
            assert config.superserver_port == 1972
        finally:
            # Restore environment
            for key, value in original_env.items():
                os.environ[key] = value


class TestContainerConfigImageName:
    """Test ContainerConfig.get_image_name() method."""

    def test_get_image_name_community_latest(self):
        """Test image name for community edition with latest tag."""
        config = ContainerConfig(edition="community", image_tag="latest")
        # Bug Fix #1: Community images use 'intersystemsdc/' prefix (not 'intersystems/')
        assert config.get_image_name() == "intersystemsdc/iris-community:latest"

    def test_get_image_name_community_specific_tag(self):
        """Test image name for community edition with specific tag."""
        config = ContainerConfig(edition="community", image_tag="2024.1")
        # Bug Fix #1: Community images use 'intersystemsdc/' prefix
        assert config.get_image_name() == "intersystemsdc/iris-community:2024.1"

    def test_get_image_name_enterprise_latest(self):
        """Test image name for enterprise edition with latest tag."""
        config = ContainerConfig(
            edition="enterprise",
            license_key="TEST-KEY",
            image_tag="latest"
        )
        assert config.get_image_name() == "intersystems/iris:latest"

    def test_get_image_name_enterprise_specific_tag(self):
        """Test image name for enterprise edition with specific tag."""
        config = ContainerConfig(
            edition="enterprise",
            license_key="TEST-KEY",
            image_tag="2024.1"
        )
        assert config.get_image_name() == "intersystems/iris:2024.1"


class TestContainerConfigVolumeValidation:
    """Test ContainerConfig.validate_volume_paths() method (Feature 011 - T001)."""

    def test_validate_volume_paths_all_valid(self):
        """Test that validation passes when all host paths exist."""
        import tempfile

        # Create temp directories that exist
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:

            config = ContainerConfig(
                volumes=[
                    f"{temp_dir1}:/data1",
                    f"{temp_dir2}:/data2:ro"
                ]
            )

            # Should return empty list (no errors)
            errors = config.validate_volume_paths()
            assert errors == []

    def test_validate_volume_paths_nonexistent(self):
        """Test that validation fails when one host path doesn't exist."""
        config = ContainerConfig(
            volumes=[
                "/nonexistent/path:/data",
                "/another/missing:/data2:ro"
            ]
        )

        # Should return error messages for missing paths
        errors = config.validate_volume_paths()
        assert len(errors) == 2
        assert "/nonexistent/path" in errors[0]
        assert "/another/missing" in errors[1]
        assert "does not exist" in errors[0].lower()

    def test_validate_volume_paths_empty_list(self):
        """Test that validation passes with no volumes configured."""
        config = ContainerConfig(volumes=[])

        # Empty volumes should be valid (no errors)
        errors = config.validate_volume_paths()
        assert errors == []

    def test_validate_volume_paths_multiple_errors(self):
        """Test error messages for multiple invalid paths."""
        config = ContainerConfig(
            volumes=[
                "/fake/path1:/data1",
                "/fake/path2:/data2:rw",
                "/fake/path3:/data3:ro"
            ]
        )

        errors = config.validate_volume_paths()
        assert len(errors) == 3

        # Verify each error mentions the corresponding path
        assert any("/fake/path1" in err for err in errors)
        assert any("/fake/path2" in err for err in errors)
        assert any("/fake/path3" in err for err in errors)
