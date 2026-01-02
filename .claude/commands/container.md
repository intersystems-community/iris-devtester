# description: Start, stop, and manage IRIS containers

# Container Skill

## Prerequisites
- Docker Desktop is running
- `iris-devtester` package is installed (`pip install -e .`)

## CLI Commands

### Start a Container
Starts an IRIS Community container. If it doesn't exist, it creates one.
```bash
iris-devtester container up
```

### Check Status
Verifies if container is running and healthy (port 1972 open).
```bash
iris-devtester container status
```

### Stop Container
Stops the container without removing data (unless --remove used).
```bash
iris-devtester container stop
```

### View Logs
```bash
iris-devtester container logs
```

### Reset Password
If you get "Password change required" errors:
```bash
iris-devtester container reset-password --user _SYSTEM --password SYS
```

## Python API

### Using Context Manager (Recommended)
```python
from iris_devtester.containers.iris_container import IRISContainer

with IRISContainer.community() as iris:
    # Container is started and health-checked
    conn_info = iris.get_connection_info()
    print(f"Connected to {conn_info.host}:{conn_info.port}")
    # ... run tests ...
# Container is stopped automatically
```

### Manual Control
```python
from iris_devtester.containers.iris_container import IRISContainer

iris = IRISContainer.community()
iris.start()
try:
    # Do work
    pass
finally:
    iris.stop()
```

## Troubleshooting

### Container Fails to Start
**Symptom**: `Container exited with code 1` or `Durable folder does not exist`
**Fix**: Ensure you are using the correct image. Community Edition handles durable sys defaults differently.
```bash
# Force community image
export IRIS_IMAGE="intersystemsdc/iris-community:latest"
iris-devtester container up
```

### CallIn Service Disabled
**Symptom**: `ERROR: CallIn service not available`
**Fix**: Enable it explicitly.
```bash
iris-devtester container enable-callin
```
