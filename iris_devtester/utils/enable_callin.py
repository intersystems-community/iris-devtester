"""
Enable CallIn service for IRIS containers.

This module provides utilities to enable CallIn service, which is required for:
- DBAPI connections (intersystems-irispython)
- Embedded Python (iris module)
- Python callouts from ObjectScript

Pattern: Follows password_reset.py proven pattern.
"""

from typing import Tuple


def enable_callin_service(
    container_name: str = "iris_db",
    timeout: int = 30
) -> Tuple[bool, str]:
    """
    Enable CallIn service for DBAPI and embedded Python.

    CRITICAL: CallIn service must be enabled for:
    - DBAPI connections (intersystems-irispython)
    - Embedded Python (iris module)
    - Python callouts from ObjectScript

    This function uses Docker exec to run ObjectScript commands that enable
    the %Service_CallIn service with password + Kerberos authentication.

    Args:
        container_name: Name of the IRIS Docker container (default: "iris_db")
        timeout: Maximum time in seconds to wait for operation (default: 30)

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "CallIn service enabled successfully") on success
        - (False, "Error message with remediation steps") on failure

    Example:
        >>> from iris_devtester.utils import enable_callin_service
        >>> success, msg = enable_callin_service("my-iris-container")
        >>> if not success:
        ...     print(f"Failed: {msg}")

    Constitutional Compliance:
        - Principle #1: Automatic remediation (enables service automatically)
        - Principle #2: Choose right tool (docker exec for admin operations)
        - Principle #5: Fail fast with guidance (detailed error messages)
        - Principle #7: Medical-grade reliability (idempotent operation)
    """
    # Implementation will follow password_reset.py pattern
    # TODO: Implement in Phase 3.3
    raise NotImplementedError("To be implemented in Phase 3.3 (T013)")
