"""
Configuration discovery and auto-detection.

Automatically discovers IRIS configuration from multiple sources:
1. Explicit parameters (highest priority)
2. Environment variables
3. .env files
4. Docker container inspection
5. Sensible defaults (lowest priority)
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from iris_devtester.config.defaults import (
    DEFAULT_AUTO_CREATE,
    DEFAULT_DRIVER,
    DEFAULT_HOST,
    DEFAULT_NAMESPACE,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DEFAULT_USERNAME,
)
from iris_devtester.config.models import IRISConfig

logger = logging.getLogger(__name__)


def discover_config(
    explicit_config: Optional[IRISConfig] = None,
    container_name: Optional[str] = None,
) -> IRISConfig:
    """
    Discover IRIS configuration from available sources.

    Configuration priority (highest to lowest):
    1. Explicit config parameter
    2. Environment variables (IRIS_HOST, IRIS_PORT, etc.)
    3. .env file in current directory
    4. Docker container inspection (if available)
    5. Default values

    Args:
        explicit_config: Optional explicit configuration to use
        container_name: Optional Docker container name to pin auto-detection to.
            When provided, Docker-based auto-detection only matches this container,
            making discovery deterministic on machines with multiple IRIS containers.

    Returns:
        IRISConfig with discovered or default values

    Example:
        >>> # Auto-discover from environment
        >>> config = discover_config()

        >>> # Override specific values
        >>> from iris_devtester.config import IRISConfig
        >>> explicit = IRISConfig(host="custom.host")
        >>> config = discover_config(explicit_config=explicit)

        >>> # Pin to specific container
        >>> config = discover_config(container_name="iris-vector-graph-main")
    """
    # If explicit config provided, return it directly
    if explicit_config is not None:
        return explicit_config

    # Start with defaults
    discovered: Dict[str, Any] = {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "namespace": DEFAULT_NAMESPACE,
        "username": DEFAULT_USERNAME,
        "password": DEFAULT_PASSWORD,
        "driver": DEFAULT_DRIVER,
        "timeout": DEFAULT_TIMEOUT,
        "auto_create": DEFAULT_AUTO_CREATE,
    }

    # Layer 3: .env file (override defaults)
    dotenv_config = _load_from_dotenv()
    discovered.update(dotenv_config)

    # Layer 2: Environment variables (override .env and defaults)
    env_config = _load_from_environment()
    discovered.update(env_config)

    # Layer 2.5: Detect persistent Dev Instance (Feature 026)
    # This takes precedence over auto-detection but respects environment/explicit config
    if discovered["host"] == DEFAULT_HOST and discovered["port"] == DEFAULT_PORT:
        from iris_devtester.containers.dev_instance import DevInstanceManager
        dev_manager = DevInstanceManager()
        dev_instance = dev_manager.get_instance()
        if dev_instance and dev_instance.status == "running":
            # Extract port mapping from dev instance
            ports = dev_instance.attrs.get("NetworkSettings", {}).get("Ports", {})
            if "1972/tcp" in ports and ports["1972/tcp"]:
                dev_port = int(ports["1972/tcp"][0]["HostPort"])
                discovered["port"] = dev_port
                discovered["container_name"] = dev_instance.name
                logger.info(f"Using persistent dev instance on port {dev_port}")

    # Layer 4: Auto-detect from Docker/native instances (ONLY if not already set)
    # Import here to avoid circular dependency
    from iris_devtester.connections.auto_discovery import auto_detect_iris_host_and_port

    # Only auto-detect if host AND port are still at defaults (not set by env or .env)
    # This ensures we don't partially override user config with auto-detection
    if discovered["host"] == DEFAULT_HOST and discovered["port"] == DEFAULT_PORT:
        auto_host, auto_port = auto_detect_iris_host_and_port(
            container_name=container_name,
        )
        if auto_host:
            discovered["host"] = auto_host
        if auto_port:
            discovered["port"] = auto_port
        # Propagate container_name into config so downstream code
        # (namespace creation, password reset) can target the right container
        if container_name and "container_name" not in discovered:
            discovered["container_name"] = container_name

    # Create and return config
    return IRISConfig(**discovered)


# Maps IRIS_* variable names to (config_key, converter) pairs.
# Converters transform the raw string value; a value of None means "skip this key".
def _parse_auto_create(value: str) -> Optional[bool]:
    val = value.lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return None


_ENV_MAPPINGS = {
    "IRIS_HOST": ("host", str),
    "IRIS_PORT": ("port", int),
    "IRIS_NAMESPACE": ("namespace", str),
    "IRIS_USERNAME": ("username", str),
    "IRIS_PASSWORD": ("password", str),
    "IRIS_DRIVER": ("driver", str),
    "IRIS_TIMEOUT": ("timeout", int),
    "IRIS_AUTO_CREATE": ("auto_create", _parse_auto_create),
}


def _apply_mapping(config: Dict[str, Any], key: str, value: str) -> None:
    """Apply a single IRIS_* key/value to the config dict using _ENV_MAPPINGS."""
    if key not in _ENV_MAPPINGS:
        return

    field_name, converter = _ENV_MAPPINGS[key]
    converted = converter(value)
    # _parse_auto_create returns None to signal "unrecognized value, skip"
    if key == "IRIS_AUTO_CREATE" and converted is None:
        return
    config[field_name] = converted


def _load_from_environment() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Looks for IRIS_* variables (see _ENV_MAPPINGS).

    Returns:
        Dictionary of discovered configuration values
    """
    config: Dict[str, Any] = {}
    for key in _ENV_MAPPINGS:
        if key in os.environ:
            _apply_mapping(config, key, os.environ[key])
    return config


def _load_from_dotenv() -> Dict[str, Any]:
    """
    Load configuration from .env file in current directory.

    Looks for .env file and parses IRIS_* variables.

    Returns:
        Dictionary of discovered configuration values
    """
    config: Dict[str, Any] = {}
    dotenv_path = Path.cwd() / ".env"

    if not dotenv_path.exists():
        return config

    try:
        with open(dotenv_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                _apply_mapping(config, key, value)

    except (IOError, ValueError):
        # If .env file can't be read or parsed, just skip it
        pass

    return config
