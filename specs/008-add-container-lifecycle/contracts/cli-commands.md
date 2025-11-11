# CLI Command Contracts: Container Lifecycle

**Feature**: 008-add-container-lifecycle
**Date**: 2025-01-10
**Phase**: 1 (Design - Contracts)

## Overview

This document defines the contracts for all container lifecycle CLI commands. Each command specifies:
- Command signature (flags, arguments)
- Success/failure exit codes
- Output format (stdout/stderr)
- Side effects (Docker operations)

## Command: `container up`

**Purpose**: Create and start IRIS container from configuration (docker-compose style)

**Signature**:
```bash
iris-devtester container up [OPTIONS]
```

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--config PATH` | Path | ./iris-config.yml | No | Path to configuration file |
| `--detach / --no-detach` | Boolean | True | No | Run in background mode |
| `--timeout SECONDS` | Integer | 60 | No | Health check timeout |

**Exit Codes**:
- `0`: Success - container created/already running
- `1`: Docker not installed/not running
- `2`: Invalid configuration file
- `3`: Port conflict
- `4`: Disk space insufficient
- `5`: Health check timeout
- `6`: License validation failed (enterprise)

**Output (Success)**:
```
⚡ Creating new container 'iris_db' from iris-config.yml
  → Pulling image: intersystems/iris-community:latest
  → Starting container...
  → Waiting for health check... [30s]
  → Enabling CallIn service...
✓ Container 'iris_db' is running and healthy

Connection Information:
  SuperServer: localhost:1972
  Web Portal:  localhost:52773
  Namespace:   USER
  Username:    _SYSTEM
  Password:    SYS
```

**Output (Already Running - Idempotent)**:
```
✓ Container 'iris_db' already running and healthy

Connection Information:
  SuperServer: localhost:1972
  Web Portal:  localhost:52773
  Namespace:   USER
```

**Output (Error - Docker Not Running)**:
```
✗ Failed to connect to Docker daemon

What went wrong:
  Docker is not running or not accessible by current user.

Why it matters:
  Container lifecycle commands require Docker to create and manage IRIS containers.

How to fix it:
  1. Start Docker Desktop (macOS/Windows):
     → Open Docker Desktop application

  2. Start Docker daemon (Linux):
     → sudo systemctl start docker

  3. Verify Docker is running:
     → docker --version
     → docker ps

Documentation:
  https://iris-devtester.readthedocs.io/troubleshooting/docker-not-running/
```

**Side Effects**:
1. Pulls IRIS Docker image (if not present)
2. Creates Docker container with specified config
3. Starts container in detached mode (if --detach)
4. Waits for health check (SuperServer port 1972)
5. Enables CallIn service (if DBAPI installed)
6. Adds labels to container (config source, version)

**Idempotency**: YES - Multiple calls succeed, display "already running"

---

## Command: `container start`

**Purpose**: Start existing or create new IRIS container

**Signature**:
```bash
iris-devtester container start [OPTIONS] [CONTAINER_NAME]
```

**Arguments**:
| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_NAME` | String | iris_db | No | Container name to start |

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--config PATH` | Path | ./iris-config.yml | No | Config file (if creating) |
| `--timeout SECONDS` | Integer | 60 | No | Health check timeout |

**Exit Codes**:
- `0`: Success - container started
- `1`: Docker error
- `2`: Container not found and no config
- `5`: Health check timeout

**Output (Success - Existing)**:
```
⚡ Starting container 'iris_db'
  → Waiting for health check... [15s]
✓ Container 'iris_db' started successfully

Status: running (healthy)
Uptime: 15 seconds
```

**Output (Success - Created New)**:
```
⚡ Container 'iris_db' not found, creating from iris-config.yml
  → Pulling image: intersystems/iris-community:latest
  → Creating container...
  → Starting container...
✓ Container 'iris_db' started successfully
```

**Side Effects**:
1. Starts existing container (if exists and stopped)
2. OR creates new container from config (if not exists)
3. Waits for health check
4. Updates container state (stopped → running)

**Idempotency**: YES - Starting already-running container succeeds

---

## Command: `container stop`

**Purpose**: Gracefully stop running IRIS container

**Signature**:
```bash
iris-devtester container stop [OPTIONS] [CONTAINER_NAME]
```

**Arguments**:
| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_NAME` | String | iris_db | No | Container name to stop |

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--timeout SECONDS` | Integer | 30 | No | Grace period before force kill |

**Exit Codes**:
- `0`: Success - container stopped
- `1`: Docker error
- `2`: Container not found

**Output (Success)**:
```
⚡ Stopping container 'iris_db'
  → Graceful shutdown... [10s]
✓ Container 'iris_db' stopped successfully

Final status: stopped
Uptime: 5 minutes 42 seconds
```

**Output (Already Stopped - Idempotent)**:
```
✓ Container 'iris_db' already stopped
```

**Side Effects**:
1. Sends SIGTERM to container process
2. Waits for graceful shutdown (up to timeout)
3. Sends SIGKILL if timeout exceeded
4. Updates container state (running → stopped)
5. Preserves container and volumes

**Idempotency**: YES - Stopping already-stopped container succeeds

---

## Command: `container restart`

**Purpose**: Restart IRIS container (stop + start)

**Signature**:
```bash
iris-devtester container restart [OPTIONS] [CONTAINER_NAME]
```

**Arguments**:
| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_NAME` | String | iris_db | No | Container name to restart |

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--timeout SECONDS` | Integer | 60 | No | Health check timeout |

**Exit Codes**:
- `0`: Success - container restarted
- `1`: Docker error
- `2`: Container not found
- `5`: Health check timeout after restart

**Output (Success)**:
```
⚡ Restarting container 'iris_db'
  → Stopping... [5s]
  → Starting... [15s]
  → Waiting for health check... [10s]
✓ Container 'iris_db' restarted successfully

Status: running (healthy)
Restart took: 30 seconds
```

**Side Effects**:
1. Stops running container
2. Starts container
3. Waits for health check
4. Updates container state (running → stopped → running)

**Idempotency**: YES - Safe to call on any state

---

## Command: `container status`

**Purpose**: Display current container state and health

**Signature**:
```bash
iris-devtester container status [OPTIONS] [CONTAINER_NAME]
```

**Arguments**:
| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_NAME` | String | iris_db | No | Container name to check |

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--format FORMAT` | Choice[text,json] | text | No | Output format |

**Exit Codes**:
- `0`: Success - container exists
- `2`: Container not found

**Output (Text Format - Running)**:
```
Container: iris_db
Status:    running
Health:    healthy
Uptime:    2 hours 15 minutes
Created:   2025-01-10 14:30:22
Started:   2025-01-10 14:30:25

Ports:
  1972/tcp → localhost:1972 (SuperServer)
  52773/tcp → localhost:52773 (Web Portal)

Image:     intersystems/iris-community:latest
Config:    /Users/dev/project/iris-config.yml
```

**Output (JSON Format - Running)**:
```json
{
  "container_id": "a1b2c3d4e5f6...",
  "container_name": "iris_db",
  "status": "running",
  "health_status": "healthy",
  "created_at": "2025-01-10T14:30:22Z",
  "started_at": "2025-01-10T14:30:25Z",
  "uptime_seconds": 8100,
  "ports": {
    "1972/tcp": "localhost:1972",
    "52773/tcp": "localhost:52773"
  },
  "image": "intersystems/iris-community:latest",
  "config_source": "/Users/dev/project/iris-config.yml"
}
```

**Output (Not Found)**:
```
✗ Container 'iris_db' not found

How to create it:
  iris-devtester container up [--config iris-config.yml]

Documentation:
  https://iris-devtester.readthedocs.io/cli/container-up/
```

**Side Effects**: None (read-only query)

---

## Command: `container logs`

**Purpose**: Display container logs

**Signature**:
```bash
iris-devtester container logs [OPTIONS] [CONTAINER_NAME]
```

**Arguments**:
| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_NAME` | String | iris_db | No | Container name |

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--follow / -f` | Boolean | False | No | Stream logs continuously |
| `--tail LINES` | Integer | 100 | No | Number of lines to show |
| `--since TIMESTAMP` | String | None | No | Show logs since timestamp |

**Exit Codes**:
- `0`: Success - logs displayed
- `2`: Container not found

**Output (Last 100 Lines)**:
```
[2025-01-10 14:30:25] Starting IRIS...
[2025-01-10 14:30:28] ^STUP routine started
[2025-01-10 14:30:30] License key valid
[2025-01-10 14:30:32] SuperServer started on port 1972
[2025-01-10 14:30:35] Web Gateway started on port 52773
[2025-01-10 14:30:37] IRIS initialization complete
```

**Output (Follow Mode - CTRL+C to exit)**:
```
[2025-01-10 14:30:37] IRIS initialization complete
[2025-01-10 14:31:15] Connection from 172.17.0.1:54321
[2025-01-10 14:31:16] User _SYSTEM authenticated
^C
```

**Side Effects**: None (read-only query)

---

## Command: `container remove`

**Purpose**: Remove stopped container and optionally volumes

**Signature**:
```bash
iris-devtester container remove [OPTIONS] [CONTAINER_NAME]
```

**Arguments**:
| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CONTAINER_NAME` | String | iris_db | No | Container name to remove |

**Options**:
| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--force / -f` | Boolean | False | No | Force remove running container |
| `--volumes / -v` | Boolean | False | No | Remove associated volumes |

**Exit Codes**:
- `0`: Success - container removed
- `1`: Docker error
- `2`: Container not found
- `3`: Container running (without --force)

**Output (Success)**:
```
⚡ Removing container 'iris_db'
  → Stopping container... [5s]
  → Removing container...
  → Removing volumes... (1 volume)
✓ Container 'iris_db' removed successfully
```

**Output (Running Without Force)**:
```
✗ Cannot remove running container 'iris_db'

How to fix it:
  1. Stop the container first:
     iris-devtester container stop iris_db

  2. Then remove it:
     iris-devtester container remove iris_db

  3. Or force remove (data loss!):
     iris-devtester container remove --force iris_db

Warning: Force remove will lose unsaved data
```

**Side Effects**:
1. Stops container (if --force and running)
2. Removes container from Docker
3. Removes associated volumes (if --volumes)
4. Frees ports and resources

**Idempotency**: NO - Removing non-existent container fails (exit code 2)

---

## Shared Behavior

### Configuration Loading Hierarchy
All commands follow this hierarchy for config file:
1. `--config` flag (explicit path)
2. `./iris-config.yml` (current directory)
3. Environment variables (IRIS_EDITION, IRIS_LICENSE_KEY, etc.)
4. Zero-config defaults

### Docker Validation
All commands validate Docker before executing:
```python
def validate_docker():
    """Validate Docker is available."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        client = docker.from_env()
        client.ping()
    except FileNotFoundError:
        raise DockerNotInstalledError()
    except docker.errors.DockerException:
        raise DockerNotRunningError()
```

### Progress Indicators
All long-running operations show progress:
- Spinner: `⚡` for active operations
- Success: `✓` for completed operations
- Error: `✗` for failed operations
- Info: `→` for sub-steps

### Constitutional Error Messages
All errors follow Constitutional Principle #5 format:
1. **What went wrong**: Single sentence
2. **Why it matters**: Context/impact
3. **How to fix it**: Step-by-step remediation
4. **Documentation**: Link to relevant docs

---

## Contract Test Matrix

| Command | Test | Expected Outcome |
|---------|------|------------------|
| `up` | Zero-config | Creates container with defaults |
| `up` | With YAML config | Creates container from file |
| `up` | Already running | Reports "already running" (exit 0) |
| `up` | Docker not running | Constitutional error message |
| `up` | Port conflict | Constitutional error with port details |
| `start` | Existing stopped container | Starts successfully |
| `start` | Non-existent + no config | Error with create suggestion |
| `start` | Already running | Reports "already running" (exit 0) |
| `stop` | Running container | Stops successfully |
| `stop` | Already stopped | Reports "already stopped" (exit 0) |
| `stop` | Non-existent | Error (exit 2) |
| `restart` | Running container | Restarts successfully |
| `restart` | Stopped container | Starts successfully |
| `status` | Running container | Shows full status (text) |
| `status --format json` | Running | Returns valid JSON |
| `status` | Non-existent | Error with create suggestion |
| `logs` | Running container | Shows last 100 lines |
| `logs --follow` | Running | Streams continuously |
| `logs --tail 10` | Running | Shows last 10 lines |
| `remove` | Stopped container | Removes successfully |
| `remove` | Running (no --force) | Error with stop suggestion |
| `remove --force` | Running | Force removes |
| `remove --volumes` | Any | Removes container + volumes |

---

## JSON Output Schema

For `--format json` outputs (status command):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ContainerStatus",
  "type": "object",
  "required": ["container_id", "container_name", "status", "created_at"],
  "properties": {
    "container_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "Docker container ID (full hash)"
    },
    "container_name": {
      "type": "string",
      "description": "Container name"
    },
    "status": {
      "type": "string",
      "enum": ["creating", "running", "stopped", "removing"],
      "description": "Current lifecycle state"
    },
    "health_status": {
      "type": ["string", "null"],
      "enum": ["starting", "healthy", "unhealthy", null],
      "description": "Docker health check status"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Container creation timestamp (ISO 8601)"
    },
    "started_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "Last start timestamp (ISO 8601)"
    },
    "uptime_seconds": {
      "type": ["integer", "null"],
      "minimum": 0,
      "description": "Seconds since started_at"
    },
    "ports": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      },
      "description": "Port mappings (container:host)"
    },
    "image": {
      "type": "string",
      "description": "Docker image reference"
    },
    "config_source": {
      "type": ["string", "null"],
      "description": "Path to config file (if any)"
    }
  }
}
```

---

## Next Phase

CLI contracts complete. Proceed to quickstart documentation generation.
