# Contract: Connection Management API

**Feature**: 001-implement-iris-devtester
**Module**: `iris_devtester.connections`
**Date**: 2025-10-05

## Overview

This contract defines the public API for IRIS database connection management, including automatic driver selection (DBAPI/JDBC), password remediation, and configuration discovery.

## Public Functions

### get_iris_connection()

**Signature**:
```python
def get_iris_connection(
    config: Optional[IRISConfig] = None,
    *,
    auto_remediate: bool = True,
    retry_attempts: int = 3,
    retry_delay: float = 1.0
) -> Connection
```

**Purpose**: Get an IRIS database connection with automatic driver selection and password remediation

**Parameters**:
- `config` (Optional[IRISConfig]): Configuration object. If None, auto-discovers from environment
- `auto_remediate` (bool): Whether to automatically reset password if change required (default: True)
- `retry_attempts` (int): Number of connection retry attempts (default: 3)
- `retry_delay` (float): Delay between retries in seconds (default: 1.0)

**Returns**: Connection object (DBAPI or JDBC)

**Raises**:
- `ConnectionError`: If connection fails after all retry attempts
  - Error message includes diagnosis, remediation steps, and documentation links
- `ValueError`: If config validation fails

**Behavior**:
1. If config is None, auto-discover from environment/Docker
2. Attempt DBAPI connection first
3. If DBAPI fails, fall back to JDBC
4. If "Password change required" detected and auto_remediate=True, reset password automatically
5. Retry connection up to retry_attempts times
6. Return connected Connection object

**Performance**: <500ms (DBAPI), <2s (JDBC) on first call

**Requirements**: FR-001, FR-002, FR-004, FR-006, FR-007, FR-026

**Example**:
```python
# Zero-config
conn = get_iris_connection()

# Explicit config
config = IRISConfig(host="iris.example.com", namespace="MYAPP")
conn = get_iris_connection(config)

# Disable auto-remediation
conn = get_iris_connection(auto_remediate=False)
```

---

### reset_password_if_needed()

**Signature**:
```python
def reset_password_if_needed(
    config: IRISConfig,
    *,
    new_password: Optional[str] = None,
    update_environment: bool = True
) -> PasswordResetResult
```

**Purpose**: Check if password reset required and perform automatic remediation

**Parameters**:
- `config` (IRISConfig): Configuration to check/update
- `new_password` (Optional[str]): Explicit new password. If None, generates secure random password
- `update_environment` (bool): Whether to update environment variables after reset (default: True)

**Returns**: PasswordResetResult with success status and new credentials

**Raises**:
- `PasswordResetError`: If reset fails and cannot recover
  - Error message includes manual remediation steps

**Behavior**:
1. Attempt connection with provided credentials
2. If "Password change required" detected, execute password reset
3. If Docker container, use docker exec for reset
4. If manual IRIS instance, provide clear instructions
5. Update environment variables if update_environment=True
6. Verify new password works

**Performance**: <10s for automatic reset

**Requirements**: FR-004, FR-005, FR-026

**Example**:
```python
config = IRISConfig()
result = reset_password_if_needed(config)
if result.success:
    print(f"Password reset to: {result.new_password}")
else:
    print(f"Manual reset required: {result.get_message()}")
```

---

### test_connection()

**Signature**:
```python
def test_connection(
    config: IRISConfig,
    *,
    timeout: int = 5
) -> tuple[bool, Optional[str]]
```

**Purpose**: Test if connection can be established without creating persistent connection

**Parameters**:
- `config` (IRISConfig): Configuration to test
- `timeout` (int): Maximum time to wait for connection in seconds (default: 5)

**Returns**: Tuple of (success: bool, error_message: Optional[str])

**Raises**: Never raises (returns error in tuple)

**Behavior**:
1. Attempt connection with provided config
2. Execute simple query (SELECT 1)
3. Close connection immediately
4. Return success status and any error message

**Performance**: <5s maximum (timeout controlled)

**Requirements**: FR-032

**Example**:
```python
config = IRISConfig(host="unknown.example.com")
success, error = test_connection(config)
if not success:
    print(f"Connection failed: {error}")
```

---

## Public Classes

### IRISConnectionManager

**Purpose**: Advanced connection management with pooling and lifecycle control

**Signature**:
```python
class IRISConnectionManager:
    def __init__(
        self,
        config: Optional[IRISConfig] = None,
        *,
        pool_size: int = 1,
        auto_remediate: bool = True
    ):
        """Initialize connection manager"""

    def get_connection(self) -> Connection:
        """Get connection from pool or create new"""

    def close_all(self) -> None:
        """Close all managed connections"""

    def __enter__(self) -> "IRISConnectionManager":
        """Context manager support"""

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Automatic cleanup on context exit"""
```

**Attributes**:
- `config: IRISConfig` - Configuration used for connections
- `driver_type: Literal["dbapi", "jdbc"]` - Selected driver type
- `active_connections: int` - Number of active connections

**Requirements**: FR-001, FR-002, FR-006, FR-008

**Example**:
```python
# Context manager (automatic cleanup)
with IRISConnectionManager() as manager:
    conn = manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")

# Manual management
manager = IRISConnectionManager(pool_size=5)
conn1 = manager.get_connection()
conn2 = manager.get_connection()
manager.close_all()
```

---

## Error Messages

All errors follow constitutional requirement (Principle #5: Fail Fast with Guidance).

**Example ConnectionError**:
```
Failed to connect to IRIS at localhost:1972

What went wrong:
  The IRIS database is not running or not accessible.

How to fix it:
  1. Start IRIS: docker-compose up -d
  2. Wait 30 seconds for startup
  3. Verify: docker logs iris_db
  4. Check port: nc -zv localhost 1972

Alternative: Use testcontainers for automatic IRIS management:
  from iris_devtester.containers import IRISContainer
  with IRISContainer.community() as iris:
      conn = iris.get_connection()

Documentation: https://iris-devtester.readthedocs.io/troubleshooting/connection-errors
```

**Example PasswordResetError**:
```
Automatic password reset failed

What went wrong:
  Container access denied or IRIS not running in container.

How to fix it manually:
  1. Access IRIS terminal:
     docker exec -it <container_id> iris session IRIS
  2. Run password reset:
     do ##class(Security.Users).UnExpireUserPasswords("*")
  3. Update environment:
     export IRIS_PASSWORD=<new_password>

Documentation: https://iris-devtester.readthedocs.io/troubleshooting/password-reset
```

## Logging

All connection operations log with structured context:

```python
logger.info("Attempting DBAPI connection", extra={
    "driver": "dbapi",
    "host": config.host,
    "port": config.port,
    "namespace": config.namespace
})

logger.warning("DBAPI connection failed, falling back to JDBC", extra={
    "dbapi_error": str(dbapi_error),
    "fallback": "jdbc"
})

logger.info("Connection established successfully", extra={
    "driver": driver_type,
    "connection_time_ms": elapsed_ms
})
```

## Performance Guarantees

| Operation | Target | Measured |
|-----------|--------|----------|
| DBAPI connection | <500ms | ~300ms (rag-templates) |
| JDBC connection | <2s | ~1.5s (rag-templates) |
| Password reset | <10s | ~5s (container), ~manual (standalone) |
| Connection test | <5s | ~2s (success), 5s (timeout) |

## Backwards Compatibility

**rag-templates Migration**:
```python
# Old (rag-templates)
from common.iris_connection_manager import IRISConnectionManager
manager = IRISConnectionManager()
conn = manager.get_connection()

# New (iris-devtester, backwards compatible)
from iris_devtester.connections import IRISConnectionManager  # Same class!
manager = IRISConnectionManager()
conn = manager.get_connection()  # Same method!

# New (iris-devtester, preferred)
from iris_devtester import get_iris_connection
conn = get_iris_connection()  # Simpler!
```

All rag-templates APIs preserved for v1.0.0 compatibility.

## Contract Tests

**Location**: `tests/contract/test_connection_api.py`

**Test Cases**:
1. `test_get_connection_zero_config()` - Auto-discovery works
2. `test_get_connection_explicit_config()` - Explicit config works
3. `test_get_connection_dbapi_first()` - DBAPI attempted first
4. `test_get_connection_jdbc_fallback()` - JDBC fallback on DBAPI failure
5. `test_password_reset_automatic()` - Automatic password reset
6. `test_password_reset_environment_update()` - Environment variables updated
7. `test_connection_retry()` - Retry logic works
8. `test_connection_manager_context()` - Context manager cleanup
9. `test_connection_manager_pool()` - Connection pooling
10. `test_connection_test_timeout()` - Test connection timeout

---

**Contract Version**: 1.0.0
**Last Updated**: 2025-10-05
**Status**: Ready for implementation
