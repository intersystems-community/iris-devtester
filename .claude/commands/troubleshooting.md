# description: Diagnose and fix common IRIS/Docker issues

# Troubleshooting Skill

## Prerequisites
- Error message available (e.g. `ImportError`, `SQLCODE`, `DockerException`)

## Common Issues & Fixes

### 1. CallIn Service Not Available
**Symptom**: `ERROR: CallIn service not available` or silent DBAPI failure.
**Cause**: The `%Service_CallIn` service is disabled by default in many IRIS images.
**Remediation**:
```bash
iris-devtester container enable-callin
```

### 2. Password Change Required
**Symptom**: `[SQLCODE: <-853>:<User xxx is required to change password before login>]`
**Cause**: Fresh IRIS containers have a security flag `ChangePassword=1` set for all users.
**Remediation**:
```bash
iris-devtester container reset-password --user _SYSTEM --password SYS
```

### 3. Image Not Found
**Symptom**: `image not found` or `manifest unknown`
**Cause**: Incorrect organization prefix.
- Community Edition: `intersystemsdc/iris-community:latest`
- Enterprise Edition: `intersystems/iris:latest`
**Remediation**:
Check `IRIS_IMAGE` environment variable.
```bash
export IRIS_IMAGE="intersystemsdc/iris-community:latest"
```

### 4. Connection Refused (macOS)
**Symptom**: `Connection refused` or `Access Denied` despite correct password.
**Cause**: macOS Docker Desktop latency or IPv6 resolution issues with "localhost".
**Remediation**:
Force IPv4 by using `127.0.0.1` explicitly instead of `localhost`.

### 5. Private Module Import Error
**Symptom**: `ImportError: cannot import name 'connect' from 'intersystems_iris.dbapi._DBAPI'`
**Cause**: Code is trying to import private modules that don't exist in the installed package.
**Remediation**:
Refactor import to use public API:
```python
# Change this:
from intersystems_iris.dbapi._DBAPI import connect
# To this:
import iris
conn = iris.connect(...)
```

### 6. Durable Folder Error
**Symptom**: Container exits with `Durable folder does not exist`.
**Cause**: `ISC_DATA_DIRECTORY` env var set for Community Edition (which doesn't support it the same way).
**Remediation**:
Unset the variable or fix the volume mount.
```bash
unset ISC_DATA_DIRECTORY
```
