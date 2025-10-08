"""Configuration discovery and management."""

from iris_devtools.config.models import IRISConfig
from iris_devtools.config.discovery import discover_config
from iris_devtools.config import defaults

__all__ = ["IRISConfig", "discover_config", "defaults"]
