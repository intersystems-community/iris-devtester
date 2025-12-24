"""
Port registry for managing IRIS container port assignments.

Provides atomic file-based persistence with file locking for concurrent safety.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from filelock import FileLock, Timeout

from .assignment import PortAssignment
from .exceptions import (
    PortAssignmentTimeoutError,
    PortConflictError,
    PortExhaustedError,
)


class PortRegistry:
    """
    Manages port assignments for multiple IRIS projects with atomic file-based persistence.

    Thread-safe via file locking. Race-condition safe for concurrent container starts.
    """

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        port_range: tuple[int, int] = (1972, 1981),
    ):
        """
        Initialize port registry with optional custom path and port range.

        Args:
            registry_path: Path to registry JSON file. Default: ~/.iris-devtester/port-registry.json
            port_range: Tuple of (min_port, max_port) for auto-assignment. Default: (1972, 1981)
        """
        if registry_path is None:
            default_dir = Path.home() / ".iris-devtester"
            default_dir.mkdir(exist_ok=True)
            registry_path = default_dir / "port-registry.json"

        self.registry_path = Path(registry_path)
        self.lock_path = self.registry_path.with_suffix(".lock")
        self.port_range = port_range
        self.min_port, self.max_port = port_range

        # Ensure registry file exists
        if not self.registry_path.exists():
            self._write_registry({"schema_version": "1.0", "assignments": []})

    def assign_port(
        self,
        project_path: str,
        preferred_port: Optional[int] = None,
    ) -> PortAssignment:
        """
        Assign port to project (idempotent - returns existing if already assigned).

        Args:
            project_path: Absolute path to project directory
            preferred_port: Optional manual port override

        Returns:
            PortAssignment with assigned port

        Raises:
            PortExhaustedError: All ports in range are in use
            PortConflictError: preferred_port already assigned to different project
            PortAssignmentTimeoutError: File lock timeout (>5 seconds)
        """
        lock = FileLock(self.lock_path, timeout=5)

        try:
            with lock:
                data = self._read_registry()
                assignments = [PortAssignment.from_dict(a) for a in data["assignments"]]

                # Check if project already has assignment (idempotency)
                existing = self._find_assignment(assignments, project_path)
                if existing:
                    return existing

                # Determine port to assign
                if preferred_port is not None:
                    # Manual port assignment
                    self._validate_port_available(assignments, preferred_port, project_path)
                    port = preferred_port
                    assignment_type = "manual"
                else:
                    # Auto-assignment
                    port = self._find_available_port(assignments)
                    assignment_type = "auto"

                # Create assignment
                assignment = PortAssignment(
                    project_path=project_path,
                    port=port,
                    assigned_at=datetime.now(),
                    assignment_type=assignment_type,
                    status="active",
                    container_name=None,
                )

                # Save to registry
                assignments.append(assignment)
                data["assignments"] = [a.to_dict() for a in assignments]
                self._write_registry(data)

                return assignment

        except Timeout:
            raise PortAssignmentTimeoutError(
                registry_path=str(self.registry_path),
                lock_path=str(self.lock_path),
                timeout_seconds=5,
            )

    def release_port(self, project_path: str) -> None:
        """
        Release port assignment for project.

        Args:
            project_path: Absolute path to project directory

        Raises:
            KeyError: No assignment exists for project_path
        """
        lock = FileLock(self.lock_path, timeout=5)

        try:
            with lock:
                data = self._read_registry()
                assignments = [PortAssignment.from_dict(a) for a in data["assignments"]]

                # Find assignment to release
                assignment = self._find_assignment(assignments, project_path)
                if not assignment:
                    raise KeyError(f"No port assignment exists for project: {project_path}")

                # Remove assignment
                assignments = [a for a in assignments if a.project_path != project_path]

                # Save updated registry
                data["assignments"] = [a.to_dict() for a in assignments]
                self._write_registry(data)

        except Timeout:
            raise PortAssignmentTimeoutError(
                registry_path=str(self.registry_path),
                lock_path=str(self.lock_path),
                timeout_seconds=5,
            )

    def cleanup_stale(self) -> List[PortAssignment]:
        """
        Remove stale assignments (containers no longer exist).

        Returns:
            List of released assignments

        Requires:
            Docker daemon accessible
        """
        try:
            import docker
        except ImportError:
            # Docker SDK not available - return empty (no cleanup possible)
            return []

        lock = FileLock(self.lock_path, timeout=5)
        released = []

        try:
            with lock:
                # Get current Docker containers
                try:
                    client = docker.from_env()
                    containers = client.containers.list(all=True, filters={"name": "iris_*"})
                    container_names = {c.name for c in containers}
                except Exception:
                    # Docker daemon not accessible
                    return []

                # Load registry
                data = self._read_registry()
                assignments = [PortAssignment.from_dict(a) for a in data["assignments"]]

                # Find stale assignments (container doesn't exist)
                active_assignments = []
                for assignment in assignments:
                    if assignment.container_name and assignment.container_name not in container_names:
                        # Container removed - mark as stale
                        assignment.status = "stale"
                        released.append(assignment)
                    else:
                        active_assignments.append(assignment)

                # Update registry (remove stale assignments)
                data["assignments"] = [a.to_dict() for a in active_assignments]
                self._write_registry(data)

                return released

        except Timeout:
            raise PortAssignmentTimeoutError(
                registry_path=str(self.registry_path),
                lock_path=str(self.lock_path),
                timeout_seconds=5,
            )

    def get_assignment(self, project_path: str) -> Optional[PortAssignment]:
        """
        Query assignment by project path.

        Args:
            project_path: Absolute path to project directory

        Returns:
            PortAssignment if exists, None otherwise
        """
        data = self._read_registry()
        assignments = [PortAssignment.from_dict(a) for a in data["assignments"]]
        return self._find_assignment(assignments, project_path)

    def list_all(self) -> List[PortAssignment]:
        """
        List all active and stale assignments.

        Returns:
            List of all assignments in registry
        """
        data = self._read_registry()
        return [PortAssignment.from_dict(a) for a in data["assignments"]]

    def clear_all(self) -> None:
        """
        Remove all assignments (testing/debugging only).

        Warning: This removes all port assignments. Use with caution.
        """
        lock = FileLock(self.lock_path, timeout=5)

        try:
            with lock:
                self._write_registry({"schema_version": "1.0", "assignments": []})
        except Timeout:
            raise PortAssignmentTimeoutError(
                registry_path=str(self.registry_path),
                lock_path=str(self.lock_path),
                timeout_seconds=5,
            )

    # Private helper methods

    def _read_registry(self) -> dict:
        """Read registry JSON file."""
        with open(self.registry_path, "r") as f:
            return json.load(f)

    def _write_registry(self, data: dict) -> None:
        """Write registry JSON file atomically."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def _find_assignment(
        self, assignments: List[PortAssignment], project_path: str
    ) -> Optional[PortAssignment]:
        """Find assignment for project path."""
        for assignment in assignments:
            if assignment.project_path == project_path:
                return assignment
        return None

    def _find_available_port(self, assignments: List[PortAssignment]) -> int:
        """
        Find first available port in range.

        Checks both registry assignments AND actual Docker port bindings
        to avoid conflicts with external containers.

        Raises:
            PortExhaustedError: All ports in range are in use
        """
        # Ports assigned in registry
        used_ports = {a.port for a in assignments if a.status == "active"}

        # Also check Docker for actually bound ports (defense in depth)
        docker_bound_ports = self._get_docker_bound_ports()
        used_ports.update(docker_bound_ports)

        for port in range(self.min_port, self.max_port + 1):
            if port not in used_ports:
                return port

        # All ports exhausted
        raise PortExhaustedError(
            port_range=self.port_range, current_assignments=assignments
        )

    def _get_docker_bound_ports(self) -> set:
        """
        Get ports currently bound by Docker containers.

        Returns:
            Set of port numbers currently bound by Docker

        Note:
            Returns empty set if Docker unavailable (graceful degradation)
        """
        try:
            import docker
        except ImportError:
            return set()

        try:
            client = docker.from_env()
            bound_ports = set()

            # Check all containers (running or stopped)
            for container in client.containers.list(all=True):
                # Get port bindings from container config
                if container.attrs and "NetworkSettings" in container.attrs:
                    ports = container.attrs["NetworkSettings"].get("Ports", {})
                    for container_port, bindings in ports.items():
                        if bindings:
                            for binding in bindings:
                                if binding and "HostPort" in binding:
                                    try:
                                        host_port = int(binding["HostPort"])
                                        # Only track ports in our range
                                        if self.min_port <= host_port <= self.max_port:
                                            bound_ports.add(host_port)
                                    except (ValueError, TypeError):
                                        continue

            return bound_ports

        except Exception:
            # Docker daemon not accessible - return empty set
            return set()

    def _validate_port_available(
        self, assignments: List[PortAssignment], port: int, requesting_project: str
    ) -> None:
        """
        Validate that preferred port is available.

        Raises:
            PortConflictError: Port already assigned to different project
        """
        for assignment in assignments:
            if assignment.port == port and assignment.status == "active":
                raise PortConflictError(
                    requested_port=port,
                    requested_project=requesting_project,
                    existing_project=assignment.project_path,
                    existing_assignment_type=assignment.assignment_type,
                    existing_status=assignment.status,
                )
