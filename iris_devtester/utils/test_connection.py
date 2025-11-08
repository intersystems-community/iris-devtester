"""
Test connection to IRIS containers.

This module provides utilities to validate connectivity to IRIS instances,
useful for troubleshooting and health checks.

Pattern: Follows password_reset.py proven pattern.
"""

from typing import Tuple


def test_connection(
    container_name: str = "iris_db",
    namespace: str = "USER",
    timeout: int = 10
) -> Tuple[bool, str]:
    """
    Test connection to IRIS container.

    Attempts to connect to the IRIS database and execute a simple query
    to verify connectivity. Tries DBAPI first (faster), falls back to
    docker exec if needed.

    Args:
        container_name: Name of the IRIS Docker container (default: "iris_db")
        namespace: IRIS namespace to connect to (default: "USER")
        timeout: Maximum time in seconds to wait for connection (default: 10)

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "Connection successful to <namespace>") on success
        - (False, "Error message with remediation steps") on failure

    Example:
        >>> from iris_devtester.utils import test_connection
        >>> success, msg = test_connection("my-iris-container", "USER")
        >>> if success:
        ...     print("IRIS is accessible!")

    Constitutional Compliance:
        - Principle #2: DBAPI first, docker exec fallback
        - Principle #4: Zero configuration (auto-discovers connection params)
        - Principle #5: Fail fast with guidance (detailed error messages)
        - Principle #7: Medical-grade reliability (non-destructive check)
    """
    # Implementation will follow password_reset.py pattern
    # TODO: Implement in Phase 3.3
    raise NotImplementedError("To be implemented in Phase 3.3 (T014)")
