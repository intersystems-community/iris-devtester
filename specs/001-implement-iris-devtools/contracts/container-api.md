# Contract: Container Management API

**Feature**: 001-implement-iris-devtester
**Module**: `iris_devtester.containers`
**Date**: 2025-10-05

## Overview

This contract defines the enhanced IRIS container management API built on testcontainers-iris-python, adding automatic password remediation, better wait strategies, and edition support.

## Public Classes

### IRISContainer

**Purpose**: Enhanced IRIS container with automatic remediation and improved lifecycle management

**Base Class**: `testcontainers.iris.IRISContainer` (extends, not replaces)

**Class Methods**:

#### community()

**Signature**:
```python
@classmethod
def community(
    cls,
    *,
    image: str = "intersystemsdc/iris-community:latest",
    password: str = "SYS",
    namespace: str = "USER",
    wait_timeout: int = 60
) -> "IRISContainer":
    """Create Community edition container with sensible defaults"""
```

**Purpose**: Create IRIS Community edition container

**Parameters**:
- `image` (str): Docker image (default: latest community)
- `password` (str): SuperUser password (default: "SYS")
- `namespace` (str): Default namespace (default: "USER")
- `wait_timeout` (int): Maximum wait for ready in seconds (default: 60)

**Returns**: Configured IRISContainer instance

**Requirements**: FR-022, FR-029

**Example**:
```python
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # Use connection
# Automatic cleanup
```

---

#### enterprise()

**Signature**:
```python
@classmethod
def enterprise(
    cls,
    license_key: str,
    *,
    image: str = "intersystemsdc/iris:latest",
    password: str = "SYS",
    namespace: str = "USER",
    wait_timeout: int = 60
) -> "IRISContainer":
    """Create Enterprise edition container with license"""
```

**Purpose**: Create IRIS Enterprise edition container

**Parameters**:
- `license_key` (str): Enterprise license key (required)
- `image` (str): Docker image (default: latest enterprise)
- `password` (str): SuperUser password (default: "SYS")
- `namespace` (str): Default namespace (default: "USER")
- `wait_timeout` (int): Maximum wait for ready in seconds (default: 60)

**Returns**: Configured IRISContainer instance

**Raises**:
- `ValueError`: If license_key not provided

**Requirements**: FR-022

**Example**:
```python
license = os.getenv("IRIS_LICENSE_KEY")
with IRISContainer.enterprise(license) as iris:
    conn = iris.get_connection()
    # Enterprise features available
```

---

### Instance Methods

#### get_connection()

**Signature**:
```python
def get_connection(
    self,
    *,
    namespace: Optional[str] = None,
    username: str = "SuperUser",
    password: Optional[str] = None,
    driver: Literal["dbapi", "jdbc", "auto"] = "auto"
) -> Connection:
    """Get connection to IRIS container"""
```

**Purpose**: Get database connection to running container

**Parameters**:
- `namespace` (Optional[str]): Override default namespace
- `username` (str): Username (default: "SuperUser")
- `password` (Optional[str]): Override default password
- `driver` (Literal): Preferred driver (default: "auto" = DBAPI first)

**Returns**: Connection object

**Raises**:
- `ConnectionError`: If container not running or connection fails

**Behavior**:
1. Verify container is running
2. Get connection parameters from container
3. Attempt connection with driver preference
4. Automatic password reset if needed
5. Return connected Connection

**Requirements**: FR-001, FR-002, FR-004

**Example**:
```python
container = IRISContainer.community()
container.start()

# Default namespace
conn = container.get_connection()

# Custom namespace
conn_custom = container.get_connection(namespace="MYAPP")

# Force JDBC
conn_jdbc = container.get_connection(driver="jdbc")
```

---

#### wait_for_ready()

**Signature**:
```python
def wait_for_ready(
    self,
    *,
    timeout: int = 60,
    check_interval: int = 5
) -> None:
    """Wait for IRIS to be fully ready (not just started)"""
```

**Purpose**: Wait for IRIS database to be fully initialized and ready for connections

**Parameters**:
- `timeout` (int): Maximum wait time in seconds (default: 60)
- `check_interval` (int): Time between checks in seconds (default: 5)

**Returns**: None

**Raises**:
- `TimeoutError`: If IRIS not ready within timeout

**Behavior**:
1. Wait for container to start
2. Wait for port to be open
3. Wait for IRIS process to be ready
4. Execute health check query (SELECT 1)
5. Verify namespaces created
6. Return when fully ready

**Performance**: ~25-30s for Community, ~35-45s for Enterprise

**Requirements**: FR-020, FR-021

**Example**:
```python
container = IRISContainer.community()
container.start()
container.wait_for_ready(timeout=60)
# IRIS is now fully ready
```

---

#### execute_command()

**Signature**:
```python
def execute_command(
    self,
    command: Union[str, List[str]],
    *,
    user: Optional[str] = None,
    workdir: Optional[str] = None
) -> tuple[int, str]:
    """Execute command inside container"""
```

**Purpose**: Execute arbitrary command inside running container

**Parameters**:
- `command` (Union[str, List[str]]): Command to execute
- `user` (Optional[str]): User to run command as
- `workdir` (Optional[str]): Working directory for command

**Returns**: Tuple of (exit_code: int, output: str)

**Example**:
```python
container = IRISContainer.community()
container.start()

# Execute IRIS command
exit_code, output = container.execute_command([
    "iris", "session", "IRIS", "-U", "USER"
])
```

---

#### reset_password()

**Signature**:
```python
def reset_password(
    self,
    new_password: Optional[str] = None,
    *,
    update_config: bool = True
) -> PasswordResetResult:
    """Reset SuperUser password in container"""
```

**Purpose**: Reset IRIS SuperUser password using docker exec

**Parameters**:
- `new_password` (Optional[str]): New password (generated if None)
- `update_config` (bool): Update container config with new password (default: True)

**Returns**: PasswordResetResult with reset outcome

**Behavior**:
1. Generate secure password if not provided
2. Execute password reset via docker exec
3. Verify new password works
4. Update container configuration
5. Return result

**Requirements**: FR-004, FR-023

**Example**:
```python
container = IRISContainer.community()
container.start()

result = container.reset_password()
if result.success:
    print(f"New password: {result.new_password}")
```

---

## Enhanced Wait Strategies

### IRISReadyWaitStrategy

**Purpose**: Custom wait strategy that verifies IRIS is fully ready

**Signature**:
```python
class IRISReadyWaitStrategy:
    def __init__(
        self,
        *,
        timeout: int = 60,
        check_interval: int = 5,
        verify_namespaces: List[str] = ["USER"]
    ):
        """Initialize wait strategy"""

    def wait_until_ready(
        self,
        container: DockerContainer
    ) -> None:
        """Wait until IRIS is ready"""
```

**Checks Performed**:
1. Container is running
2. Port 1972 is open
3. IRIS process is active
4. Database accepts connections
5. Specified namespaces exist

**Requirements**: FR-020, FR-021

**Example**:
```python
wait_strategy = IRISReadyWaitStrategy(
    timeout=60,
    verify_namespaces=["USER", "MYAPP"]
)

container = IRISContainer.community()
container.with_wait_strategy(wait_strategy)
container.start()
```

---

## Configuration Integration

### Auto-Discovery from Container

**Function**: `discover_config_from_container()`

**Signature**:
```python
def discover_config_from_container(
    container: IRISContainer
) -> IRISConfig:
    """Auto-discover IRISConfig from running container"""
```

**Purpose**: Extract connection configuration from running container

**Returns**: IRISConfig with container connection parameters

**Behavior**:
1. Get container host (docker host or localhost)
2. Get mapped ports
3. Get environment variables (namespace, credentials)
4. Return populated IRISConfig

**Example**:
```python
container = IRISContainer.community()
container.start()

config = discover_config_from_container(container)
# config has correct host, port, namespace, credentials
```

---

## Environment Variable Integration

**Supported Environment Variables**:
```bash
IRIS_HOST=localhost
IRIS_PORT=1972
IRIS_NAMESPACE=USER
IRIS_USERNAME=SuperUser
IRIS_PASSWORD=SYS
IRIS_LICENSE_KEY=/path/to/iris.key  # Enterprise only
```

**Container Setup**:
```python
# Automatically reads from environment
container = IRISContainer.community()

# Override environment
container = IRISContainer.community(
    password=os.getenv("CUSTOM_PASSWORD", "SYS")
)
```

**Requirements**: FR-005, FR-006

---

## Volume Mounts

**Supported Volumes**:
```python
container = IRISContainer.community()

# Mount license key
container.with_volume_mapping("/path/to/iris.key", "/license/iris.key")

# Mount data directory
container.with_volume_mapping("./iris-data", "/usr/irissys/mgr")

# Mount custom code
container.with_volume_mapping("./src", "/opt/app/src")
```

---

## Port Mapping

**Default Ports**:
- `1972`: SuperServer port (DBAPI/JDBC connections)
- `52773`: Management Portal
- `53773`: Private Web Server (if enabled)

**Custom Port Mapping**:
```python
container = IRISContainer.community()
container.with_bind_ports(1972, 9999)  # Map 1972 to host 9999
container.with_bind_ports(52773, 8080)  # Map 52773 to host 8080
```

**Dynamic Port Allocation**:
```python
container = IRISContainer.community()
container.start()

# Get dynamically assigned host port
port = container.get_exposed_port(1972)
print(f"IRIS accessible on: {container.get_container_host_ip()}:{port}")
```

---

## Error Messages

**Example TimeoutError**:
```
IRIS container failed to become ready within 60 seconds

What went wrong:
  IRIS database did not finish initialization in time.

Health check details:
  - Container started: ✓
  - Port 1972 open: ✓
  - IRIS process running: ✓
  - Database ready: ✗ (timeout)

How to fix:
  1. Increase timeout: IRISContainer.community(wait_timeout=120)
  2. Check container logs: docker logs <container_id>
  3. Verify system resources (disk space, memory)

Documentation: https://iris-devtester.readthedocs.io/troubleshooting/container-timeout
```

---

## Performance Targets

| Operation | Community | Enterprise | Notes |
|-----------|-----------|------------|-------|
| Container start | ~25s | ~35s | Image cached |
| First start (pull) | ~70s | ~80s | Image download |
| Health check | ~5s | ~10s | Includes query |
| Password reset | ~3s | ~3s | Container exec |
| Container stop | ~5s | ~5s | Graceful shutdown |

---

## Backwards Compatibility

**testcontainers-iris-python Migration**:
```python
# Old (testcontainers-iris-python)
from testcontainers.iris import IRISContainer
container = IRISContainer()
container.start()

# New (iris-devtester, extends base class)
from iris_devtester.containers import IRISContainer
container = IRISContainer.community()  # Enhanced!
container.start()

# Still compatible with base class
from testcontainers.iris import IRISContainer
container = IRISContainer()  # Base class still works
```

All testcontainers-iris-python APIs preserved.

---

## Contract Tests

**Location**: `tests/contract/test_container_api.py`

**Test Cases**:
1. `test_community_container_creation()` - Community edition works
2. `test_enterprise_container_creation()` - Enterprise edition requires license
3. `test_get_connection_from_container()` - Connection works
4. `test_wait_for_ready()` - Wait strategy works
5. `test_wait_for_ready_timeout()` - Timeout detection
6. `test_password_reset_in_container()` - Password reset works
7. `test_execute_command()` - Command execution works
8. `test_discover_config_from_container()` - Auto-discovery works
9. `test_volume_mounts()` - Volume mounting works
10. `test_port_mapping()` - Port mapping works

---

**Contract Version**: 1.0.0
**Last Updated**: 2025-10-05
**Status**: Ready for implementation
