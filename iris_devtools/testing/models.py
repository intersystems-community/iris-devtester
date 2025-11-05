"""
Testing models for schema validation, test state, and cleanup.

Provides dataclasses for schema definitions, validation results,
test state tracking, and cleanup management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional


# Schema Definition Models (T014)


@dataclass
class ColumnDefinition:
    """
    Definition of a database column.

    Attributes:
        name: Column name
        type: IRIS data type (VARCHAR, INTEGER, etc.)
        max_length: Maximum length for string types
        nullable: Whether NULL values are allowed
        default: Default value for the column
    """

    name: str
    type: str
    max_length: Optional[int] = None
    nullable: bool = True
    default: Optional[Any] = None


@dataclass
class IndexDefinition:
    """
    Definition of a database index.

    Attributes:
        name: Index name
        columns: List of indexed column names
        unique: Whether index enforces uniqueness
    """

    name: str
    columns: List[str]
    unique: bool = False


@dataclass
class TableDefinition:
    """
    Definition of a database table.

    Attributes:
        name: Table name
        columns: Dictionary mapping column names to ColumnDefinition
        indexes: List of IndexDefinition for this table
    """

    name: str
    columns: Dict[str, ColumnDefinition] = field(default_factory=dict)
    indexes: List[IndexDefinition] = field(default_factory=list)


@dataclass
class SchemaDefinition:
    """
    Complete database schema definition.

    Attributes:
        tables: Dictionary mapping table names to TableDefinition
        version: Schema version identifier
        description: Human-readable description
    """

    tables: Dict[str, TableDefinition] = field(default_factory=dict)
    version: str = "1.0.0"
    description: Optional[str] = None


@dataclass
class SchemaMismatch:
    """
    Represents a difference between expected and actual schema.

    Attributes:
        table: Table name where mismatch occurred
        type: Type of mismatch
        expected: Expected value
        actual: Actual value
        message: Human-readable description
    """

    table: str
    type: Literal["missing_table", "extra_table", "missing_column", "extra_column", "type_mismatch"]
    expected: Optional[str] = None
    actual: Optional[str] = None
    message: str = ""


@dataclass
class SchemaValidationResult:
    """
    Result of schema validation check.

    Attributes:
        is_valid: Overall validation result
        mismatches: List of schema differences found
        timestamp: When validation was performed
        schema_version: Version of schema validated against
    """

    is_valid: bool
    mismatches: List[SchemaMismatch] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    schema_version: str = "1.0.0"

    def get_summary(self) -> str:
        """
        Get human-readable summary of validation result.

        Args:
            (no arguments)

        Returns:
            Summary string describing validation outcome

        Example:
            >>> result = SchemaValidationResult(is_valid=True, mismatches=[])
            >>> print(result.get_summary())
            "Schema validation passed"
        """
        if self.is_valid:
            return "Schema validation passed"
        return f"Schema validation failed: {len(self.mismatches)} mismatch(es)"


# Validation and State Models (T015)


@dataclass
class PasswordResetResult:
    """
    Result of password reset attempt.

    Attributes:
        success: Whether reset succeeded
        new_password: New password if generated
        environment_updated: Whether environment variables were updated
        error: Error message if failed
        timestamp: When reset was attempted
        remediation_steps: Manual steps if automatic reset failed
    """

    success: bool
    new_password: Optional[str] = None
    environment_updated: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    remediation_steps: List[str] = field(default_factory=list)

    def get_message(self) -> str:
        """
        Get human-readable message about reset result.

        Args:
            (no arguments)

        Returns:
            Message describing reset outcome and next steps

        Example:
            >>> result = PasswordResetResult(success=True, new_password="newpass123")
            >>> print(result.get_message())
            "Password reset successful. New password: newpass123"
        """
        if self.success:
            return f"Password reset successful. New password: {self.new_password}"

        message = f"Password reset failed: {self.error}\n"
        if self.remediation_steps:
            message += "\nManual remediation steps:\n"
            message += "\n".join(f"  {i+1}. {step}" for i, step in enumerate(self.remediation_steps))
        return message


@dataclass
class CleanupAction:
    """
    Represents a cleanup action to perform after test.

    Attributes:
        action_type: Type of cleanup action
        target: Target resource (table name, container ID, etc.)
        priority: Cleanup order (higher = earlier)
    """

    action_type: Literal["drop_table", "delete_data", "drop_namespace", "stop_container"]
    target: str
    priority: int = 0


@dataclass
class TestState:
    """
    Tracks test environment state for isolation and cleanup.

    Attributes:
        test_id: Unique test identifier
        isolation_level: Isolation strategy
        namespace: Assigned namespace
        container_id: Container ID if container-isolated
        connection_info: Active connection metadata
        cleanup_registered: Cleanup actions to perform
        schema_validated: Whether schema validation was performed
        created_at: When test state was created
    """

    test_id: str
    isolation_level: Literal["none", "namespace", "container"]
    namespace: str
    container_id: Optional[str] = None
    connection_info: Optional[Any] = None  # Will be ConnectionInfo when imported
    cleanup_registered: List[CleanupAction] = field(default_factory=list)
    schema_validated: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def register_cleanup(self, action: CleanupAction):
        """
        Register a cleanup action.

        Actions are automatically sorted by priority (higher first).

        Args:
            action: CleanupAction to register

        Returns:
            None

        Example:
            >>> state = TestState(test_id="test-1", isolation_level="namespace", namespace="TEST")
            >>> action = CleanupAction(priority=10, description="Drop tables", action=lambda: drop_tables())
            >>> state.register_cleanup(action)
        """
        self.cleanup_registered.append(action)
        # Sort by priority descending (higher priority first)
        self.cleanup_registered.sort(key=lambda x: x.priority, reverse=True)


@dataclass
class ContainerConfig:
    """
    Configuration for IRIS container instances.

    Attributes:
        edition: IRIS edition (community or enterprise)
        image: Docker image name
        tag: Docker image tag
        license_key: Enterprise license key
        ports: Port mappings (internal: external)
        environment: Environment variables
        volumes: Volume mounts (host: container)
        wait_timeout: Maximum wait time for ready (seconds)
        health_check_interval: Health check interval (seconds)
    """

    edition: Literal["community", "enterprise"] = "community"
    image: str = "intersystemsdc/iris-community"
    tag: str = "latest"
    license_key: Optional[str] = None
    ports: Dict[str, int] = field(default_factory=lambda: {"1972": 1972, "52773": 52773})
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: Dict[str, str] = field(default_factory=dict)
    wait_timeout: int = 60
    health_check_interval: int = 5

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.edition == "enterprise" and not self.license_key:
            raise ValueError(
                "Enterprise edition requires license_key.\n"
                "\n"
                "Provide license key:\n"
                "  - Via parameter: ContainerConfig(edition='enterprise', license_key='...')\n"
                "  - Via environment: export IRIS_LICENSE_KEY='...'\n"
                "  - Via file: Place iris.key in project root"
            )

        if self.wait_timeout <= 0:
            raise ValueError(
                f"wait_timeout must be positive: {self.wait_timeout}\n"
                "\n"
                "Recommended timeouts:\n"
                "  - 60s (default, most cases)\n"
                "  - 120s (slow systems)\n"
                "  - 30s (fast systems with cached images)"
            )

        if self.health_check_interval <= 0:
            raise ValueError(
                f"health_check_interval must be positive: {self.health_check_interval}\n"
                "\n"
                "Recommended intervals:\n"
                "  - 5s (default, balanced)\n"
                "  - 10s (slow systems)\n"
                "  - 2s (fast health checks)"
            )
