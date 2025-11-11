# Quickstart: Container Lifecycle CLI Commands

**Feature**: 008-add-container-lifecycle
**Date**: 2025-01-10
**Audience**: End users

## 5-Minute Getting Started

### Prerequisites
- Python 3.9+
- Docker installed and running
- iris-devtester v1.1.0+ (after this feature ships)

### Installation
```bash
pip install "iris-devtester[all]"
```

### Zero-Config Quick Start

**Start an IRIS container** (no configuration needed):
```bash
iris-devtester container up
```

Output:
```
⚡ Creating new container 'iris_db' from zero-config defaults
  → Pulling image: intersystems/iris-community:latest
  → Starting container...
  → Waiting for health check... [25s]
  → Enabling CallIn service...
✓ Container 'iris_db' is running and healthy

Connection Information:
  SuperServer: localhost:1972
  Web Portal:  localhost:52773
  Namespace:   USER
  Username:    _SYSTEM
  Password:    SYS
```

**Check container status**:
```bash
iris-devtester container status
```

**View logs**:
```bash
iris-devtester container logs --tail 20
```

**Stop container**:
```bash
iris-devtester container stop
```

**Remove container** (cleanup):
```bash
iris-devtester container remove --volumes
```

---

## Configuration File Usage

### Create Configuration File

Create `iris-config.yml` in your project directory:

```yaml
# iris-config.yml - Community Edition
edition: community
container_name: my_iris_dev
ports:
  superserver: 1972
  webserver: 52773
namespace: USER
password: MySecurePassword123
volumes:
  - ./data:/external
image_tag: latest
```

### Start Container from Config

```bash
iris-devtester container up --config iris-config.yml
```

Output:
```
⚡ Creating new container 'my_iris_dev' from iris-config.yml
  → Pulling image: intersystems/iris-community:latest
  → Starting container...
  → Waiting for health check... [22s]
  → Enabling CallIn service...
✓ Container 'my_iris_dev' is running and healthy

Connection Information:
  SuperServer: localhost:1972
  Web Portal:  localhost:52773
  Namespace:   USER
  Username:    _SYSTEM
  Password:    MySecurePassword123
```

### Idempotent Operations

Running `up` again is safe:
```bash
iris-devtester container up --config iris-config.yml
```

Output (second run):
```
✓ Container 'my_iris_dev' already running and healthy

Connection Information:
  SuperServer: localhost:1972
  Web Portal:  localhost:52773
  Namespace:   USER
```

---

## Enterprise Edition

### Create Enterprise Config

```yaml
# iris-config-enterprise.yml
edition: enterprise
container_name: iris_prod
ports:
  superserver: 1972
  webserver: 52773
namespace: PROD
password: EnterpriseSecurePass456
license_key: "AB12-CD34-EF56-GH78-IJ90-KL12-MN34-OP56"
volumes:
  - ./prod-data:/external
  - ./prod-backups:/backups
image_tag: latest
```

### Start Enterprise Container

```bash
iris-devtester container up --config iris-config-enterprise.yml
```

Output:
```
⚡ Creating new container 'iris_prod' from iris-config-enterprise.yml
  → Pulling image: intersystems/iris:latest
  → Validating license key... ✓
  → Starting container...
  → Waiting for health check... [30s]
  → Enabling CallIn service...
✓ Container 'iris_prod' is running and healthy

Connection Information:
  SuperServer: localhost:1972
  Web Portal:  localhost:52773
  Namespace:   PROD
  Edition:     Enterprise
  Username:    _SYSTEM
  Password:    EnterpriseSecurePass456
```

---

## Common Workflows

### Workflow 1: Development Setup

**Goal**: Start IRIS container for local development

```bash
# 1. Create config file (optional, or use zero-config)
cat > iris-config.yml <<EOF
edition: community
container_name: iris_dev
namespace: DEV
password: dev123
volumes:
  - ./src:/external/src
EOF

# 2. Start container
iris-devtester container up

# 3. Verify running
iris-devtester container status

# 4. View logs if needed
iris-devtester container logs --follow

# 5. Connect from Python
python -c "
import irisnative
conn = irisnative.createConnection('localhost', 1972, 'DEV', '_SYSTEM', 'dev123')
cursor = conn.cursor()
cursor.execute('SELECT $ZVERSION AS version')
print(cursor.fetchone())
"
```

---

### Workflow 2: Testing with Fresh Container

**Goal**: Reset container between test runs

```bash
# 1. Start container
iris-devtester container up

# 2. Run tests
pytest tests/integration/

# 3. Clean up completely
iris-devtester container remove --force --volumes

# 4. Start fresh for next test run
iris-devtester container up
```

---

### Workflow 3: Container Lifecycle Management

**Goal**: Manage running container lifecycle

```bash
# Start in background (default)
iris-devtester container up --detach

# Check status anytime
iris-devtester container status

# View recent logs
iris-devtester container logs --tail 50

# Restart if needed (e.g., after config change)
iris-devtester container restart

# Stop when done
iris-devtester container stop

# Remove (keeps volumes by default)
iris-devtester container remove

# Or remove everything (data loss!)
iris-devtester container remove --force --volumes
```

---

### Workflow 4: Port Conflict Resolution

**Goal**: Handle port conflicts gracefully

```bash
# Try to start with default ports
iris-devtester container up
```

If port 1972 is in use, you'll see:
```
✗ Failed to start container 'iris_db'

What went wrong:
  Port 1972 is already in use by another process.

Why it matters:
  IRIS SuperServer requires port 1972 to be available for connections.

How to fix it:
  1. Find the process using port 1972:
     → lsof -i :1972  (macOS/Linux)
     → netstat -ano | findstr :1972  (Windows)

  2. Stop the conflicting process:
     → kill <PID>

  3. Or use a different port in iris-config.yml:
     ports:
       superserver: 11972
       webserver: 52773

  4. Then restart:
     → iris-devtester container up --config iris-config.yml

Documentation:
  https://iris-devtester.readthedocs.io/troubleshooting/port-conflicts/
```

**Solution**: Use custom port
```yaml
# iris-config.yml
edition: community
ports:
  superserver: 11972  # Changed from 1972
  webserver: 52773
```

```bash
iris-devtester container up --config iris-config.yml
```

---

## Advanced Usage

### Custom Container Names

Run multiple IRIS instances:

```bash
# Development instance
iris-devtester container up --config iris-dev.yml
# Config: container_name: iris_dev

# Testing instance
iris-devtester container up --config iris-test.yml
# Config: container_name: iris_test

# Both running simultaneously
iris-devtester container status iris_dev
iris-devtester container status iris_test
```

### Background vs Foreground

```bash
# Background (default - returns immediately)
iris-devtester container up --detach

# Foreground (shows logs, blocks terminal)
iris-devtester container up --no-detach
```

### Health Check Timeout

For slow machines or large images:

```bash
# Default timeout: 60 seconds
iris-devtester container up

# Custom timeout: 120 seconds
iris-devtester container up --timeout 120
```

### Log Streaming

```bash
# View last 100 lines (default)
iris-devtester container logs

# View last 20 lines
iris-devtester container logs --tail 20

# Stream continuously (CTRL+C to exit)
iris-devtester container logs --follow

# Logs since specific time
iris-devtester container logs --since "2025-01-10T14:30:00"
```

### JSON Output for Automation

```bash
# Get status as JSON
iris-devtester container status --format json

# Example output:
{
  "container_id": "a1b2c3d4e5f6...",
  "container_name": "iris_db",
  "status": "running",
  "health_status": "healthy",
  "created_at": "2025-01-10T14:30:22Z",
  "started_at": "2025-01-10T14:30:25Z",
  "uptime_seconds": 3600,
  "ports": {
    "1972/tcp": "localhost:1972",
    "52773/tcp": "localhost:52773"
  },
  "image": "intersystems/iris-community:latest",
  "config_source": "./iris-config.yml"
}
```

**Use in scripts**:
```bash
#!/bin/bash
STATUS=$(iris-devtester container status --format json)
UPTIME=$(echo $STATUS | jq -r '.uptime_seconds')

if [ $UPTIME -gt 3600 ]; then
  echo "Container has been running for over 1 hour"
  iris-devtester container restart
fi
```

---

## Troubleshooting

### Error: Docker Not Running

```
✗ Failed to connect to Docker daemon

What went wrong:
  Docker is not running or not accessible by current user.
```

**Solution**:
```bash
# macOS/Windows: Start Docker Desktop
open -a Docker  # macOS
# Or use GUI to start Docker Desktop

# Linux: Start Docker daemon
sudo systemctl start docker

# Verify Docker is running
docker ps
```

### Error: Container Name Already Exists

```
✗ Failed to create container 'iris_db'

What went wrong:
  A container with name 'iris_db' already exists.
```

**Solution Option 1** - Use existing container:
```bash
# Start existing container
iris-devtester container start iris_db
```

**Solution Option 2** - Remove and recreate:
```bash
# Remove old container
iris-devtester container remove iris_db

# Create new container
iris-devtester container up
```

**Solution Option 3** - Use different name:
```yaml
# iris-config.yml
container_name: iris_db_v2
```

### Error: Invalid License Key (Enterprise)

```
✗ Failed to start container 'iris_prod'

What went wrong:
  License key validation failed.

Why it matters:
  Enterprise edition requires a valid license key.

How to fix it:
  1. Verify license key format (e.g., AB12-CD34-EF56-GH78...)

  2. Check license key in config file:
     license_key: "YOUR-LICENSE-KEY-HERE"

  3. Or use environment variable:
     export IRIS_LICENSE_KEY="YOUR-LICENSE-KEY-HERE"

  4. Contact InterSystems for license:
     https://www.intersystems.com/contact/

Documentation:
  https://iris-devtester.readthedocs.io/enterprise-setup/
```

**Solution**:
```yaml
# iris-config.yml
edition: enterprise
license_key: "VALID-LICENSE-KEY-FROM-INTERSYSTEMS"
```

---

## Integration with Python Code

### Before This Feature
```python
from iris_devtester.containers import IRISContainer

# Must use Python context manager
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # ... use connection
# Container auto-removed when context exits
```

### After This Feature
```bash
# Start once from CLI
iris-devtester container up

# Use from any Python script (container persists)
import irisnative
conn = irisnative.createConnection('localhost', 1972, 'USER', '_SYSTEM', 'SYS')
# ... use connection

# Container keeps running until you stop it
```

**Benefit**: No need to restart container for each Python script run!

---

## Next Steps

1. **Read the full CLI reference**: `iris-devtester container --help`
2. **Explore config options**: See [data-model.md](./data-model.md) for all configuration fields
3. **Review error handling**: See [contracts/cli-commands.md](./contracts/cli-commands.md) for all error scenarios
4. **Check out examples**: See `/examples/cli/` directory after feature ships

---

## Quick Reference Card

```bash
# Container Lifecycle
iris-devtester container up              # Create/start container
iris-devtester container start           # Start existing or create new
iris-devtester container stop            # Stop running container
iris-devtester container restart         # Restart container
iris-devtester container remove          # Remove stopped container
iris-devtester container remove -fv      # Force remove + delete volumes

# Container Info
iris-devtester container status          # Show container state
iris-devtester container status --format json  # JSON output
iris-devtester container logs            # View last 100 log lines
iris-devtester container logs -f         # Stream logs continuously
iris-devtester container logs --tail 20  # Last 20 lines

# Configuration
--config PATH                # Use custom config file
--detach / --no-detach       # Background vs foreground
--timeout SECONDS            # Health check timeout
--force                      # Force operation (remove)
--volumes                    # Include volumes (remove)

# Zero-Config Defaults
container_name: iris_db
edition: community
superserver_port: 1972
webserver_port: 52773
namespace: USER
password: SYS
```

---

**Ready to use container lifecycle CLI commands!** 🚀
