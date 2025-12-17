# Docker-Compose Integration

Work with existing IRIS containers managed by docker-compose, licensed IRIS, or external containers.

## Overview

When you already have IRIS running via docker-compose (common with licensed Enterprise editions), you don't need testcontainers overhead. This feature lets you:
- Attach to existing containers without lifecycle management
- Use CLI commands for quick operations
- Integrate with shell scripts and automation
- Auto-discover container ports

## Quick Start

### Python API

```python
from iris_devtester.containers import IRISContainer
from iris_devtester.utils import enable_callin_service, test_connection, get_container_status

# Approach 1: Attach to existing container
iris = IRISContainer.attach("iris_db")  # Your docker-compose service name
conn = iris.get_connection()  # Auto-enables CallIn, discovers port
cursor = conn.cursor()
cursor.execute("SELECT $ZVERSION")

# Approach 2: Standalone utilities (shell-friendly)
success, msg = enable_callin_service("iris_db")
success, msg = test_connection("iris_db", namespace="USER")
success, report = get_container_status("iris_db")
```

### CLI Commands

```bash
# Check container status (aggregates running, health, connection)
iris-devtester container status iris_db

# Enable CallIn service (required for DBAPI connections)
iris-devtester container enable-callin iris_db

# Test database connection
iris-devtester container test-connection iris_db --namespace USER

# Reset password if needed
iris-devtester container reset-password iris_db --user _SYSTEM --password SYS
```

## Docker-Compose Setup

### Example docker-compose.yml

```yaml
version: '3.8'
services:
  iris_db:
    image: intersystemsdc/iris:latest  # Or licensed IRIS image
    container_name: iris_db
    ports:
      - "1972:1972"    # SuperServer port
      - "52773:52773"  # Management Portal
    environment:
      - ISC_DATA_DIRECTORY=/iris/data
    volumes:
      - iris_data:/iris/data
      - ./iris.key:/iris/license/iris.key:ro  # License for Enterprise

volumes:
  iris_data:
```

### Using with iris-devtester

```python
# No testcontainers overhead - use existing container
iris = IRISContainer.attach("iris_db")
conn = iris.get_connection()

# Work with your database
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM MyApp.Users")
print(cursor.fetchone())
```

## Container Lifecycle Commands

Full lifecycle management for development:

```bash
# Create and start a new container
iris-devtester container up

# Start existing stopped container
iris-devtester container start iris_db

# Stop running container
iris-devtester container stop iris_db

# Restart container with health checks
iris-devtester container restart iris_db

# View container logs
iris-devtester container logs iris_db --follow

# Remove container (with optional volume cleanup)
iris-devtester container remove iris_db --volumes
```

## Health Checks

Multi-layer health validation:
1. **Container running** - Fast fail on crashes
2. **Docker health check** - If defined in image
3. **SuperServer port** - IRIS accepting connections

```python
from iris_devtester.containers import IRISContainer

iris = IRISContainer.attach("iris_db")
status = iris.get_status()

print(f"Running: {status.is_running}")
print(f"Healthy: {status.is_healthy}")
print(f"Port: {status.port}")
```

## Best Practices

1. **Use named containers**: Consistent names across environments
2. **Enable CallIn service**: Required for DBAPI connections (done automatically)
3. **Mount license files read-only**: Prevent accidental modification
4. **Use volumes for data**: Persist data across container restarts
5. **Health checks**: Let IRIS fully start before connecting

## Troubleshooting

### Connection refused
- Verify container is running: `docker ps`
- Check port mapping: `docker port iris_db`
- Wait for IRIS startup: `iris-devtester container status iris_db`

### CallIn service not enabled
- Run: `iris-devtester container enable-callin iris_db`
- Restart may be required for some IRIS versions

### License issues (Enterprise)
- Verify license mount: `docker exec iris_db cat /iris/license/iris.key`
- Check IRIS license status in Management Portal

## See Also

- [Testcontainers Integration](testcontainers.md) - For isolated test containers
- [examples/10_docker_compose_integration.py](../../examples/10_docker_compose_integration.py) - Complete example
