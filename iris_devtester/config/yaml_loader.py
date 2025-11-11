"""YAML configuration file loader for IRIS container management."""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """
    Load and parse YAML configuration file.

    Args:
        file_path: Path to YAML configuration file

    Returns:
        Dictionary containing parsed YAML content

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with open(file_path, "r") as f:
        try:
            config = yaml.safe_load(f)
            if config is None:
                return {}
            return config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {file_path}: {e}")


def validate_schema(config: Dict[str, Any]) -> None:
    """
    Validate YAML configuration schema.

    Checks for required fields and valid values.
    Will be implemented in later tasks with ContainerConfig.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If configuration is invalid
    """
    # Placeholder - full validation will be done by ContainerConfig dataclass
    pass
