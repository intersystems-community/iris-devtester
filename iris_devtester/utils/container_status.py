"""
Get comprehensive status of IRIS containers.

This module provides utilities to retrieve container health, CallIn status,
password status, and connection test results in a single operation.

Pattern: Follows password_reset.py proven pattern.
"""

from typing import Tuple


def get_container_status(
    container_name: str = "iris_db"
) -> Tuple[bool, str]:
    """
    Get comprehensive status of IRIS container.

    Retrieves and formats a multi-line status report including:
    - Container running status
    - Container health check status
    - CallIn service status (enabled/disabled)
    - Password expiration status
    - Connection test result

    Args:
        container_name: Name of the IRIS Docker container (default: "iris_db")

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "Multi-line status report") on success
        - (False, "Error message") on failure

    Example:
        >>> from iris_devtester.utils import get_container_status
        >>> success, status = get_container_status("my-iris-container")
        >>> print(status)
        Container: my-iris-container
        Status: Running (healthy)
        CallIn: Enabled
        Password: No expiration required
        Connection: Successful

    Constitutional Compliance:
        - Principle #1: Automatic remediation (identifies issues)
        - Principle #4: Zero configuration (auto-discovers all status)
        - Principle #5: Fail fast with guidance (clear status reporting)
        - Principle #7: Medical-grade reliability (non-destructive check)
    """
    # Implementation will call enable_callin.py and test_connection.py
    # TODO: Implement in Phase 3.3
    raise NotImplementedError("To be implemented in Phase 3.3 (T015)")
