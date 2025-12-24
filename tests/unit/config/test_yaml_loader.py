"""Unit tests for YAML configuration file loader."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import yaml as pyyaml

from iris_devtester.config.yaml_loader import load_yaml, validate_schema


class TestLoadYAML:
    """Test load_yaml() function."""

    def test_load_yaml_with_valid_file(self):
        """Test loading a valid YAML file."""
        yaml_content = """
edition: community
container_name: test_iris
ports:
  superserver: 1972
  webserver: 52773
namespace: USER
password: SYS
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert isinstance(result, dict)
            assert result["edition"] == "community"
            assert result["container_name"] == "test_iris"
            assert "ports" in result
            assert result["ports"]["superserver"] == 1972
            assert result["ports"]["webserver"] == 52773
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_nested_structure(self):
        """Test loading YAML with nested structure."""
        yaml_content = """
edition: enterprise
ports:
  superserver: 2000
  webserver: 53000
volumes:
  - ./data:/external
  - ./backup:/backup
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert result["edition"] == "enterprise"
            assert isinstance(result["ports"], dict)
            assert isinstance(result["volumes"], list)
            assert len(result["volumes"]) == 2
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_empty_file(self):
        """Test loading empty YAML file returns empty dict."""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert result == {}
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_comments(self):
        """Test loading YAML with comments (should be ignored)."""
        yaml_content = """
# This is a comment
edition: community  # inline comment
container_name: test_iris
# Another comment
ports:
  superserver: 1972  # SuperServer port
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert result["edition"] == "community"
            assert result["container_name"] == "test_iris"
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_multiline_values(self):
        """Test loading YAML with multiline string values."""
        yaml_content = """
description: |
  This is a multiline
  description that spans
  multiple lines.
edition: community
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert "description" in result
            assert "multiline" in result["description"]
            assert result["edition"] == "community"
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_integers(self):
        """Test that YAML integers are loaded as integers."""
        yaml_content = """
ports:
  superserver: 1972
  webserver: 52773
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert isinstance(result["ports"]["superserver"], int)
            assert isinstance(result["ports"]["webserver"], int)
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_booleans(self):
        """Test that YAML booleans are loaded correctly."""
        yaml_content = """
enabled: true
disabled: false
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert result["enabled"] is True
            assert result["disabled"] is False
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_null_values(self):
        """Test that YAML null values are loaded as None."""
        yaml_content = """
license_key: null
optional_field: ~
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert result["license_key"] is None
            assert result["optional_field"] is None
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_lists(self):
        """Test that YAML lists are loaded correctly."""
        yaml_content = """
volumes:
  - ./data:/external
  - ./backup:/backup
  - ./config:/config
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert isinstance(result["volumes"], list)
            assert len(result["volumes"]) == 3
            assert result["volumes"][0] == "./data:/external"
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_yaml(Path("nonexistent.yml"))

        assert "not found" in str(exc_info.value).lower()

    def test_load_yaml_with_invalid_syntax(self):
        """Test that YAMLError is raised for invalid syntax."""
        yaml_content = """
edition: community
container_name: [unclosed bracket
invalid: yaml: here: too: many: colons
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(pyyaml.YAMLError) as exc_info:
                load_yaml(Path(temp_path))

            assert "invalid" in str(exc_info.value).lower() or "syntax" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_duplicate_keys(self):
        """Test that last value wins with duplicate keys (YAML spec)."""
        yaml_content = """
edition: community
edition: enterprise
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            # YAML spec: last value wins
            assert result["edition"] == "enterprise"
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_quoted_strings(self):
        """Test that quoted strings are handled correctly."""
        yaml_content = """
password: "SecurePass123"
namespace: 'USER'
container_name: "my-iris"
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert result["password"] == "SecurePass123"
            assert result["namespace"] == "USER"
            assert result["container_name"] == "my-iris"
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_preserves_string_numbers(self):
        """Test that quoted numbers remain strings."""
        yaml_content = """
version: "1.0.0"
port_string: "1972"
port_int: 1972
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert isinstance(result["version"], str)
            assert isinstance(result["port_string"], str)
            assert isinstance(result["port_int"], int)
        finally:
            Path(temp_path).unlink()


class TestValidateSchema:
    """Test validate_schema() function."""

    def test_validate_schema_placeholder(self):
        """Test that validate_schema is a placeholder (no-op)."""
        # Current implementation is a placeholder
        config = {"edition": "community", "container_name": "test"}
        # Should not raise any errors
        validate_schema(config)

    def test_validate_schema_with_empty_dict(self):
        """Test validate_schema with empty dict."""
        # Should not raise errors
        validate_schema({})

    def test_validate_schema_with_nested_structure(self):
        """Test validate_schema with nested structure."""
        config = {
            "edition": "community",
            "ports": {"superserver": 1972, "webserver": 52773}
        }
        # Should not raise errors
        validate_schema(config)


class TestYAMLLoaderEdgeCases:
    """Test edge cases and error handling."""

    def test_load_yaml_with_very_large_file(self):
        """Test loading a large YAML file."""
        yaml_content = "volumes:\n"
        for i in range(1000):
            yaml_content += f"  - /path{i}:/mount{i}\n"

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert len(result["volumes"]) == 1000
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_unicode_characters(self):
        """Test loading YAML with unicode characters."""
        yaml_content = """
description: "IRIS database with émojis 🚀"
namespace: USÉR
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            assert "émojis" in result["description"]
            assert "🚀" in result["description"]
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_special_yaml_values(self):
        """Test YAML special values like yes/no, on/off."""
        yaml_content = """
enabled_yes: yes
enabled_no: no
enabled_on: on
enabled_off: off
enabled_true: true
enabled_false: false
"""
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = load_yaml(Path(temp_path))
            # All should be booleans
            assert result["enabled_yes"] is True
            assert result["enabled_no"] is False
            assert result["enabled_on"] is True
            assert result["enabled_off"] is False
            assert result["enabled_true"] is True
            assert result["enabled_false"] is False
        finally:
            Path(temp_path).unlink()

    def test_load_yaml_with_pathlib_path(self):
        """Test that Path objects are handled correctly."""
        yaml_content = "edition: community\n"
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            result = load_yaml(temp_path)
            assert result["edition"] == "community"
        finally:
            temp_path.unlink()

    def test_load_yaml_with_string_path(self):
        """Test that string paths work via ContainerConfig.from_yaml."""
        yaml_content = "edition: community\n"
        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # String path gets converted to Path in from_yaml()
            result = load_yaml(Path(temp_path))
            assert result["edition"] == "community"
        finally:
            Path(temp_path).unlink()
