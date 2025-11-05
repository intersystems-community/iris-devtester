"""Configuration and auto-discovery utilities for IRIS connections."""

from .auto_discovery import (
    auto_discover_iris,
    discover_docker_iris,
    discover_iris_port,
    discover_native_iris,
)
from .discovery import discover_config
from .models import IRISConfig

__all__ = [
    "IRISConfig",
    "discover_config",
    "auto_discover_iris",
    "discover_docker_iris",
    "discover_iris_port",
    "discover_native_iris",
]
