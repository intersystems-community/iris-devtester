# Data Model: IRIS DevTools

**Feature**: 001-implement-iris-devtools
**Date**: 2025-10-05
**Purpose**: Define core entities, relationships, and data structures

## Overview

This document defines the data model for iris-devtools, extracted from feature spec entities and enhanced with type information from research phase. All entities use Python 3.9+ type hints and dataclasses.

## Core Entities

### 1. IRISConfig

**Purpose**: Represents connection configuration with auto-discovery support

**Attributes**:
- `host: str` - Database host (default: "localhost")
- `port: int` - Database port (default: 1972)
- `namespace: str` - IRIS namespace (default: "USER")
- `username: str` - Database username (default: "SuperUser")
- `password: str` - Database password (default: "SYS")
- `driver: Literal["dbapi", "jdbc", "auto"]` - Preferred driver (default: "auto")
- `connection_string: Optional[str]` - Override connection parameters
- `timeout: int` - Connection timeout in seconds (default: 30)

**Validation Rules**:
- `port` must be 1-65535
- `namespace` must be non-empty
- `timeout` must be positive
- `driver` must be one of ["dbapi", "jdbc", "auto"]

**Source**: Discovered from environment, .env files, Docker, or explicit constructor

**Implementation**:
```python
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass
class IRISConfig:
    host: str = "localhost"
    port: int = 1972
    namespace: str = "USER"
    username: str = "SuperUser"
    password: str = "SYS"
    driver: Literal["dbapi", "jdbc", "auto"] = "auto"
    connection_string: Optional[str] = None
    timeout: int = 30

    def __post_init__(self):
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Invalid port: {self.port}")
        if not self.namespace:
            raise ValueError("namespace cannot be empty")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive: {self.timeout}")
```

### 2. ConnectionInfo

**Purpose**: Metadata about an active database connection

**Attributes**:
- `driver_type: Literal["dbapi", "jdbc"]` - Actual driver used
- `host: str` - Connected host
- `port: int` - Connected port
- `namespace: str` - Connected namespace
- `username: str` - Connected username
- `connection_time: datetime` - When connection established
- `is_pooled: bool` - Whether connection is from pool
- `container_id: Optional[str]` - If testcontainer, the container ID

**Relationships**:
- Created from `IRISConfig`
- Attached to `Connection` object as metadata

**Implementation**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

@dataclass
class ConnectionInfo:
    driver_type: Literal["dbapi", "jdbc"]
    host: str
    port: int
    namespace: str
    username: str
    connection_time: datetime = field(default_factory=datetime.now)
    is_pooled: bool = False
    container_id: Optional[str] = None
```

### 3. SchemaDefinition

**Purpose**: Defines expected database schema for validation

**Attributes**:
- `tables: Dict[str, TableDefinition]` - Table definitions by name
- `version: str` - Schema version identifier
- `description: Optional[str]` - Human-readable description

**TableDefinition**:
- `name: str` - Table name
- `columns: Dict[str, ColumnDefinition]` - Column definitions by name
- `indexes: List[IndexDefinition]` - Index definitions

**ColumnDefinition**:
- `name: str` - Column name
- `type: str` - IRIS data type (VARCHAR, INTEGER, etc.)
- `max_length: Optional[int]` - Maximum length for string types
- `nullable: bool` - Whether NULL values allowed
- `default: Optional[Any]` - Default value

**IndexDefinition**:
- `name: str` - Index name
- `columns: List[str]` - Indexed columns
- `unique: bool` - Whether index is unique

**Implementation**:
```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ColumnDefinition:
    name: str
    type: str
    max_length: Optional[int] = None
    nullable: bool = True
    default: Optional[Any] = None

@dataclass
class IndexDefinition:
    name: str
    columns: List[str]
    unique: bool = False

@dataclass
class TableDefinition:
    name: str
    columns: Dict[str, ColumnDefinition] = field(default_factory=dict)
    indexes: List[IndexDefinition] = field(default_factory=list)

@dataclass
class SchemaDefinition:
    tables: Dict[str, TableDefinition] = field(default_factory=dict)
    version: str = "1.0.0"
    description: Optional[str] = None
```

### 4. SchemaValidationResult

**Purpose**: Result of schema validation check

**Attributes**:
- `is_valid: bool` - Overall validation result
- `mismatches: List[SchemaMismatch]` - List of schema differences
- `timestamp: datetime` - When validation performed
- `schema_version: str` - Version of schema validated against

**SchemaMismatch**:
- `table: str` - Table name
- `type: Literal["missing_table", "extra_table", "missing_column", "extra_column", "type_mismatch"]`
- `expected: Optional[str]` - Expected value
- `actual: Optional[str]` - Actual value
- `message: str` - Human-readable description

**Relationships**:
- Created from `SchemaDefinition` validation
- Used to decide schema reset action

**Implementation**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional

@dataclass
class SchemaMismatch:
    table: str
    type: Literal["missing_table", "extra_table", "missing_column", "extra_column", "type_mismatch"]
    expected: Optional[str] = None
    actual: Optional[str] = None
    message: str = ""

@dataclass
class SchemaValidationResult:
    is_valid: bool
    mismatches: List[SchemaMismatch] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    schema_version: str = "1.0.0"

    def get_summary(self) -> str:
        if self.is_valid:
            return "Schema validation passed"
        return f"Schema validation failed: {len(self.mismatches)} mismatch(es)"
```

### 5. TestState

**Purpose**: Tracks test environment state for isolation and cleanup

**Attributes**:
- `test_id: str` - Unique test identifier
- `isolation_level: Literal["none", "namespace", "container"]` - Isolation strategy
- `namespace: str` - Assigned namespace
- `container_id: Optional[str]` - If container-isolated, the container ID
- `connection_info: Optional[ConnectionInfo]` - Active connection metadata
- `cleanup_registered: List[CleanupAction]` - Cleanup actions to perform
- `schema_validated: bool` - Whether schema validation performed
- `created_at: datetime` - When test state created

**CleanupAction**:
- `action_type: Literal["drop_table", "delete_data", "drop_namespace", "stop_container"]`
- `target: str` - Target resource (table name, container ID, etc.)
- `priority: int` - Cleanup order (higher = earlier)

**Relationships**:
- 1:1 with `Connection` (each test has one connection)
- 1:1 optional with `ContainerConfig` (if container-isolated)
- 1:N with `CleanupAction` (multiple cleanup actions)

**Implementation**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional

@dataclass
class CleanupAction:
    action_type: Literal["drop_table", "delete_data", "drop_namespace", "stop_container"]
    target: str
    priority: int = 0

@dataclass
class TestState:
    test_id: str
    isolation_level: Literal["none", "namespace", "container"]
    namespace: str
    container_id: Optional[str] = None
    connection_info: Optional[ConnectionInfo] = None
    cleanup_registered: List[CleanupAction] = field(default_factory=list)
    schema_validated: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def register_cleanup(self, action: CleanupAction):
        self.cleanup_registered.append(action)
        self.cleanup_registered.sort(key=lambda x: x.priority, reverse=True)
```

### 6. ContainerConfig

**Purpose**: Configuration for IRIS container instances

**Attributes**:
- `edition: Literal["community", "enterprise"]` - IRIS edition
- `image: str` - Docker image name
- `tag: str` - Docker image tag
- `license_key: Optional[str]` - Enterprise license key
- `ports: Dict[str, int]` - Port mappings (internal: external)
- `environment: Dict[str, str]` - Environment variables
- `volumes: Dict[str, str]` - Volume mounts (host: container)
- `wait_timeout: int` - Maximum wait time for ready (seconds)
- `health_check_interval: int` - Health check interval (seconds)

**Validation Rules**:
- `edition` must be "community" or "enterprise"
- `license_key` required if edition is "enterprise"
- `wait_timeout` must be positive
- `health_check_interval` must be positive

**Relationships**:
- Used to create `IRISContainer` instances
- Associated with `TestState` when container-isolated

**Implementation**:
```python
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional

@dataclass
class ContainerConfig:
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
        if self.edition == "enterprise" and not self.license_key:
            raise ValueError("license_key required for enterprise edition")
        if self.wait_timeout <= 0:
            raise ValueError(f"wait_timeout must be positive: {self.wait_timeout}")
        if self.health_check_interval <= 0:
            raise ValueError(f"health_check_interval must be positive: {self.health_check_interval}")
```

### 7. PasswordResetResult

**Purpose**: Result of automatic password reset attempt

**Attributes**:
- `success: bool` - Whether reset succeeded
- `new_password: Optional[str]` - New password if generated
- `environment_updated: bool` - Whether environment variables updated
- `error: Optional[str]` - Error message if failed
- `timestamp: datetime` - When reset attempted
- `remediation_steps: List[str]` - Manual steps if automatic reset failed

**Relationships**:
- Created during connection attempt if password change detected
- Used to update `IRISConfig` with new credentials

**Implementation**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class PasswordResetResult:
    success: bool
    new_password: Optional[str] = None
    environment_updated: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    remediation_steps: List[str] = field(default_factory=list)

    def get_message(self) -> str:
        if self.success:
            return f"Password reset successful. New password: {self.new_password}"
        return f"Password reset failed: {self.error}\n" + "\n".join(self.remediation_steps)
```

## Entity Relationships

```
IRISConfig ──(1:N)──> ConnectionInfo
     │                      │
     └──────(used by)───────┘
                            │
                            v
                       Connection (DBAPI/JDBC)
                            │
                            │ (1:1)
                            v
                       TestState ──(1:1 optional)──> ContainerConfig
                            │
                            │ (1:N)
                            v
                      CleanupAction

SchemaDefinition ──(validates)──> SchemaValidationResult
                                        │
                                        │ (cached in)
                                        v
                                   TestState

IRISConfig ──(password reset)──> PasswordResetResult
     │                                  │
     └──────(updates config)────────────┘
```

## State Transitions

### Test Lifecycle
```
Created → Schema Validated → Active → Cleanup Registered → Cleaned Up
```

### Connection States
```
Configured → Connecting → Connected → In Use → Closed
                  │           │
                  v           v
            Password Reset  Connection Lost → Retry → Connected
```

### Schema Validation
```
Unchecked → Validating → Valid → Cached
                │           │
                v           v
            Invalid → Reset → Validating
```

## Validation Rules Summary

| Entity | Validation Rules |
|--------|------------------|
| IRISConfig | port 1-65535, namespace non-empty, timeout positive, driver in allowed list |
| ConnectionInfo | driver_type in ["dbapi", "jdbc"], timestamps valid |
| SchemaDefinition | table names unique, column types valid IRIS types |
| SchemaValidationResult | mismatches reference valid tables |
| TestState | isolation_level in allowed list, namespace non-empty, cleanup actions sorted |
| ContainerConfig | edition valid, license_key if enterprise, timeouts positive |
| PasswordResetResult | timestamp valid, remediation_steps non-empty if failed |

## Type Hierarchy

### Protocols (Duck Typing)

**Connection Protocol**:
```python
from typing import Protocol, Any

class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...

class Cursor(Protocol):
    def execute(self, query: str, params: tuple = ()) -> None: ...
    def fetchone(self) -> Optional[tuple]: ...
    def fetchall(self) -> List[tuple]: ...
    def close(self) -> None: ...
```

This allows both DBAPI and JDBC connections to satisfy the same interface.

## Serialization

All entities support JSON serialization via `dataclasses.asdict()` and deserialization via `**dict`:

```python
# Serialize
config = IRISConfig(host="example.com", port=1972)
config_dict = asdict(config)
config_json = json.dumps(config_dict)

# Deserialize
config_dict = json.loads(config_json)
config = IRISConfig(**config_dict)
```

**Note**: datetime fields require custom serialization:

```python
from dataclasses import asdict
import json

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

result_json = json.dumps(asdict(result), default=serialize_datetime)
```

## Usage Examples

### Basic Configuration
```python
# Auto-discovery (zero config)
config = IRISConfig()

# Explicit configuration
config = IRISConfig(
    host="iris-server.example.com",
    port=1972,
    namespace="MYAPP",
    username="admin",
    password="secret",
    driver="dbapi"
)
```

### Schema Definition
```python
schema = SchemaDefinition(
    version="1.0.0",
    description="User management schema",
    tables={
        "users": TableDefinition(
            name="users",
            columns={
                "id": ColumnDefinition(name="id", type="INTEGER", nullable=False),
                "username": ColumnDefinition(name="username", type="VARCHAR", max_length=50, nullable=False),
                "email": ColumnDefinition(name="email", type="VARCHAR", max_length=100, nullable=True)
            },
            indexes=[
                IndexDefinition(name="idx_username", columns=["username"], unique=True)
            ]
        )
    }
)
```

### Test State Management
```python
# Create test state
test_state = TestState(
    test_id="test_user_creation_001",
    isolation_level="container",
    namespace="TEST_001",
    container_id="abc123"
)

# Register cleanup
test_state.register_cleanup(CleanupAction(
    action_type="drop_table",
    target="temp_users",
    priority=10
))
test_state.register_cleanup(CleanupAction(
    action_type="stop_container",
    target="abc123",
    priority=1
))
```

---

**Data Model Complete**: 2025-10-05
**Ready for Contracts Phase**: ✓
