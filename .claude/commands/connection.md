# description: Establish and troubleshoot database connections

# Connection Skill

## Prerequisites
- IRIS container is running (`/container status`)
- `intersystems-irispython` (for DBAPI) or `jaydebeapi` (for JDBC) installed

## CLI Commands

### Test Connection
Verifies connectivity to the running container.
```bash
iris-devtester test-connection
```

## Python API

### DBAPI Connection (Preferred)
**Constitutional Principle**: Always use DBAPI over JDBC for performance and reliability unless specifically testing JDBC features.

```python
from iris_devtester.connections import get_connection
from iris_devtester.config import IRISConfig

# Auto-discovers connection from environment or running container
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT 1")
print(cursor.fetchone())
```

### Handling "Password Change Required"
The `get_connection()` factory automatically handles the `ChangePassword=1` flag if the container was started with `iris-devtester`. If you are manually connecting:

```python
from iris_devtester.utils.password_reset import reset_password

# If connection fails with SQLCODE -853
reset_password(container_name="iris_db", username="_SYSTEM", new_password="SYS")
```

### CallIn Service Requirement
**Critical**: DBAPI requires the CallIn service to be enabled.

```python
from iris_devtester.utils.enable_callin import enable_callin_service

success, msg = enable_callin_service("iris_db")
if not success:
    raise RuntimeError(f"Failed to enable CallIn: {msg}")
```

## Troubleshooting

### Import Error: _DBAPI
**Symptom**: `ImportError: cannot import name 'connect' from 'intersystems_iris.dbapi._DBAPI'`
**Cause**: Using internal private modules directly.
**Fix**: Use the public API wrapper.
```python
# WRONG
from intersystems_iris.dbapi._DBAPI import connect

# RIGHT
import iris
conn = iris.connect(...)
```

### Connection Refused on macOS
**Symptom**: `Connection refused` or timeout when using `localhost`.
**Cause**: IPv6 resolution issues on macOS Docker Desktop.
**Fix**: Use `127.0.0.1` explicitly.
```python
config = IRISConfig(host="127.0.0.1")
```
