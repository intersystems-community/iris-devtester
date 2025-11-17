"""
Custom exceptions for IRIS port management.

All exceptions follow Constitutional Principle #5: Fail Fast with Guidance.
Error messages include structured context and remediation steps.
"""


class PortExhaustedError(Exception):
    """
    Raised when all available ports in the port range are in use.

    Follows Constitutional Principle #5: Fail Fast with Guidance.
    Error message includes current port assignments and remediation steps.
    """

    def __init__(self, port_range: tuple[int, int], current_assignments: list):
        """
        Initialize PortExhaustedError with context.

        Args:
            port_range: Tuple of (min_port, max_port)
            current_assignments: List of current PortAssignment objects
        """
        min_port, max_port = port_range
        assignments_text = "\n".join(
            f"  {assignment.project_path} → {assignment.port} "
            f"({assignment.assignment_type}, {assignment.status})"
            for assignment in current_assignments
        )

        message = (
            f"PortExhaustedError: All IRIS ports ({min_port}-{max_port}) are in use\n"
            "\n"
            "Current port assignments:\n"
            f"{assignments_text}\n"
            "\n"
            "How to fix:\n"
            "  1. Stop unused containers: iris-devtester ports list\n"
            "  2. Clean up stale assignments: iris-devtester ports clear\n"
            f"  3. Use manual port override: IRISContainer(port=<custom>, port_registry=registry)\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/ports/exhaustion/\n"
        )
        super().__init__(message)
        self.port_range = port_range
        self.current_assignments = current_assignments


class PortConflictError(Exception):
    """
    Raised when a requested port is already assigned to a different project.

    Follows Constitutional Principle #5: Fail Fast with Guidance.
    Error message includes conflict details and remediation steps.
    """

    def __init__(
        self,
        requested_port: int,
        requested_project: str,
        existing_project: str,
        existing_assignment_type: str,
        existing_status: str,
    ):
        """
        Initialize PortConflictError with context.

        Args:
            requested_port: Port number that was requested
            requested_project: Project path requesting the port
            existing_project: Project path that currently has the port
            existing_assignment_type: How existing port was assigned (auto/manual)
            existing_status: Status of existing assignment (active/stale)
        """
        message = (
            f"PortConflictError: Port {requested_port} already assigned to {existing_project}\n"
            "\n"
            f"Requested: {requested_project} → {requested_port}\n"
            f"Existing: {existing_project} → {requested_port} "
            f"({existing_assignment_type}, {existing_status})\n"
            "\n"
            "How to fix:\n"
            "  1. Use auto-assignment (omit port parameter)\n"
            f"  2. Choose different port: IRISContainer(port=<other>, ...)\n"
            "  3. Stop conflicting container: iris-devtester ports list\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/ports/conflicts/\n"
        )
        super().__init__(message)
        self.requested_port = requested_port
        self.requested_project = requested_project
        self.existing_project = existing_project


class PortAssignmentTimeoutError(Exception):
    """
    Raised when port assignment times out due to file lock contention.

    Follows Constitutional Principle #5: Fail Fast with Guidance.
    Error message includes lock file details and remediation steps.
    """

    def __init__(self, registry_path: str, lock_path: str, timeout_seconds: int = 5):
        """
        Initialize PortAssignmentTimeoutError with context.

        Args:
            registry_path: Path to port registry JSON file
            lock_path: Path to lock file
            timeout_seconds: Timeout value in seconds
        """
        message = (
            f"PortAssignmentTimeoutError: Port assignment timed out after {timeout_seconds} seconds\n"
            "\n"
            "Registry locked by another process:\n"
            f"  Registry: {registry_path}\n"
            f"  Lock file: {lock_path}\n"
            "\n"
            "How to fix:\n"
            "  1. Wait for other process to complete\n"
            "  2. Check for stale lock file (kill orphaned processes)\n"
            f"  3. Remove lock file manually (last resort): rm {lock_path}\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/ports/timeouts/\n"
        )
        super().__init__(message)
        self.registry_path = registry_path
        self.lock_path = lock_path
        self.timeout_seconds = timeout_seconds
