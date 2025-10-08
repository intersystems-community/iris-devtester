"""
Connection metadata models.

Provides ConnectionInfo dataclass for tracking active connection metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


@dataclass
class ConnectionInfo:
    """
    Metadata about an active IRIS database connection.

    Tracks driver type, connection parameters, and lifecycle information
    for debugging and monitoring purposes.

    Attributes:
        driver_type: Actual driver used ("dbapi" or "jdbc")
        host: Connected host
        port: Connected port
        namespace: Connected namespace
        username: Connected username
        connection_time: When connection was established
        is_pooled: Whether connection is from a pool
        container_id: Container ID if using testcontainers

    Example:
        >>> from datetime import datetime
        >>> info = ConnectionInfo(
        ...     driver_type="dbapi",
        ...     host="localhost",
        ...     port=1972,
        ...     namespace="USER",
        ...     username="SuperUser"
        ... )
        >>> info.driver_type
        'dbapi'
        >>> isinstance(info.connection_time, datetime)
        True
    """

    driver_type: Literal["dbapi", "jdbc"]
    host: str
    port: int
    namespace: str
    username: str
    connection_time: datetime = field(default_factory=datetime.now)
    is_pooled: bool = False
    container_id: Optional[str] = None
