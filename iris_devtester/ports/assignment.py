"""
Port assignment data model for IRIS container port management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class PortAssignment:
    """
    Represents a port assignment for an IRIS project.

    Attributes:
        project_path: Absolute path to project directory
        port: IRIS superserver port number (1972-1981 for auto-assignment)
        assigned_at: Timestamp when port was assigned
        assignment_type: How port was assigned (auto or manual)
        status: Current assignment status (active, released, stale)
        container_name: Optional name of the IRIS container using this port
    """

    project_path: str
    port: int
    assigned_at: datetime
    assignment_type: Literal["auto", "manual"]
    status: Literal["active", "released", "stale"]
    container_name: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation of the assignment
        """
        return {
            "project_path": self.project_path,
            "port": self.port,
            "assigned_at": self.assigned_at.isoformat(),
            "assignment_type": self.assignment_type,
            "status": self.status,
            "container_name": self.container_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortAssignment":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation of assignment

        Returns:
            PortAssignment instance
        """
        return cls(
            project_path=data["project_path"],
            port=data["port"],
            assigned_at=datetime.fromisoformat(data["assigned_at"]),
            assignment_type=data["assignment_type"],
            status=data["status"],
            container_name=data.get("container_name"),
        )
