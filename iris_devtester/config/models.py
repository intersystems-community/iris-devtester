"""
Configuration models for IRIS DevTools.

Provides IRISConfig dataclass for database connection configuration.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class IRISConfig:
    """
    Configuration for IRIS database connections.

    Provides sensible defaults for zero-configuration usage while allowing
    explicit configuration for advanced use cases.

    Attributes:
        host: Database host (default: "localhost")
        port: Database port (default: 1972)
        namespace: IRIS namespace (default: "USER")
        username: Database username (default: "SuperUser")
        password: Database password (default: "SYS")
        driver: Preferred driver type (default: "auto")
        connection_string: Optional override connection string
        timeout: Connection timeout in seconds (default: 30)

    Raises:
        ValueError: If validation fails (invalid port, empty namespace, etc.)

    Example:
        >>> # Zero-config (uses defaults)
        >>> config = IRISConfig()
        >>> config.host
        'localhost'

        >>> # Explicit configuration
        >>> config = IRISConfig(
        ...     host="iris.example.com",
        ...     namespace="MYAPP",
        ...     driver="dbapi"
        ... )
    """

    host: str = "localhost"
    port: int = 1972
    namespace: str = "USER"
    username: str = "SuperUser"
    password: str = "SYS"
    driver: Literal["dbapi", "jdbc", "auto"] = "auto"
    connection_string: Optional[str] = None
    timeout: int = 30

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate port range
        if not 1 <= self.port <= 65535:
            raise ValueError(
                f"Invalid port: {self.port}\n"
                "\n"
                "Port must be in range 1-65535.\n"
                "Common IRIS ports: 1972 (default), 51773 (web), 52773 (management)"
            )

        # Validate namespace
        if not self.namespace:
            raise ValueError(
                "Namespace cannot be empty.\n"
                "\n"
                "Common namespaces:\n"
                "  - USER (default)\n"
                "  - SAMPLES (example data)\n"
                "  - %SYS (system)"
            )

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError(
                f"Timeout must be positive: {self.timeout}\n"
                "\n"
                "Recommended timeouts:\n"
                "  - 30s (default, most cases)\n"
                "  - 60s (slow networks)\n"
                "  - 5s (fast fail for availability checks)"
            )
