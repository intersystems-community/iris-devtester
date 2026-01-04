# Troubleshooting Guide

This guide covers the most common issues you might encounter when using IRIS DevTools and how to resolve them.

## Top 5 Issues

### 1. Docker Daemon Not Running

**Symptom:**
```
docker.errors.DockerException: Error while fetching server API version
```

**Diagnosis:**
The Docker daemon is not running or not accessible to your user account.

**Solution:**
```bash
# macOS/Windows: Start Docker Desktop
# Verify Docker is running
docker ps

# Linux: Start Docker daemon
sudo systemctl start docker

# Verify your user has Docker permissions (Linux)
sudo usermod -aG docker $USER
# Log out and log back in for group changes to take effect
```

**Prevention:**
- macOS/Windows: Set Docker Desktop to start at login
- Linux: Enable Docker service: `sudo systemctl enable docker`
- Add health check to CI workflows before running tests

---

### 2. Password Change Required

**Symptom:**
```
[SQLCODE: <-853>:<User xxx is required to change password before login>]
```

**Diagnosis:**
IRIS requires password change on first login, but IRIS DevTools should auto-remediate this. If you see this error, auto-remediation failed.

**Solution:**
IRIS DevTools automatically handles this, but if you encounter the error:

```python
# The library should automatically reset the password
# If it doesn't work, check Docker container access:
from iris_devtester.containers import IRISContainer

with IRISContainer.community() as iris:
    # Auto-remediation happens here
    conn = iris.get_connection()
```

**Manual workaround (if auto-remediation fails):**
```bash
# Get container ID
docker ps | grep iris

# Reset password manually
docker exec -it <container_id> iris session IRIS -U%SYS <<EOF
do ##class(Security.Users).UnExpireUserPasswords("*")
halt
EOF
```

**Prevention:**
- Ensure Docker exec access is available (not blocked by security policy)
- Check container logs: `docker logs <container_id>`
- Report as bug if auto-remediation consistently fails

---

### 3. Port Conflicts

**Symptom:**
```
docker.errors.APIError: ... Bind for 0.0.0.0:1972 failed: port is already allocated
```

**Diagnosis:**
Another IRIS instance or container is using the default port (1972).

**Solution:**

**Option 1: Let testcontainers auto-assign ports (recommended)**
```python
from iris_devtester.containers import IRISContainer

# Testcontainers will automatically find available port
with IRISContainer.community() as iris:
    # Port is auto-assigned
    conn = iris.get_connection()
```

**Option 2: Stop conflicting container**
```bash
# Find container using port 1972
docker ps | grep 1972

# Stop it
docker stop <container_id>
```

**Option 3: Specify different port**
```python
with IRISContainer.community(port=1973) as iris:
    conn = iris.get_connection()
```

**Prevention:**
- Use pytest fixtures (one container per test class, auto-cleanup)
- Don't hardcode ports in tests
- Use `docker ps` to check for orphaned containers: `docker ps -a | grep iris`

---

### 4. Connection Failures

**Symptom:**
```
ConnectionRefusedError: [Errno 61] Connection refused
# or
SQLCODE: <-99>:<Connect failed to remote server>
```

**Diagnosis:**
Cannot connect to IRIS instance. Common causes:
- Container still starting up
- Wrong host/port
- IRIS startup failed

**Solution:**

**Step 1: Verify container is running**
```bash
docker ps | grep iris
# Should show running container
```

**Step 2: Check container logs**
```bash
docker logs <container_id>
# Look for "IRIS started successfully" or error messages
```

**Step 3: Wait for startup**
```python
from iris_devtester.containers import IRISContainer
import time

with IRISContainer.community() as iris:
    # Wait for IRIS to be ready (auto-handled by testcontainers)
    # If you need manual wait:
    time.sleep(10)  # IRIS typically starts in 5-10 seconds
    conn = iris.get_connection()
```

**Step 4: Verify connection parameters**
```python
# Print connection details
with IRISContainer.community() as iris:
    print(f"Host: {iris.get_connection_url()}")
    conn = iris.get_connection()
```

**Prevention:**
- Always use context managers (`with` statements) for containers
- Check Docker resource limits (4GB+ RAM recommended)
- Use testcontainers wait strategies (built-in)

---

### 5. Permission Issues

**Symptom:**
```
PermissionError: [Errno 13] Permission denied
# or
docker.errors.APIError: ... permission denied while trying to connect to the Docker daemon socket
```

**Diagnosis:**
Your user account doesn't have permission to access Docker or files.

**Solution:**

**For Docker socket permission (Linux):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in
# Verify
docker ps  # Should work without sudo
```

**For file permission issues:**
```bash
# Check file permissions
ls -la /path/to/file

# Fix ownership (if needed)
sudo chown $USER:$USER /path/to/file

# For test fixtures directory
mkdir -p ./fixtures
chmod 755 ./fixtures
```

**For IRIS license file:**
```bash
# Ensure license file is readable
chmod 644 ~/.iris/iris.key
```

**Prevention:**
- Don't run Docker commands with `sudo` (configure user permissions instead)
- Ensure test directories are writable: `chmod -R 755 ./tests`
- Check CI runner has Docker permissions

---

## Getting Additional Help

If your issue isn't covered here:

1. **Check Examples**: The [examples/](https://github.com/intersystems-community/iris-devtester/blob/main/examples/) directory has working code samples
2. **Search Issues**: [GitHub Issues](https://github.com/intersystems-community/iris-devtester/issues) may have solutions
3. **Report Bug**: Use the [bug report template](https://github.com/intersystems-community/iris-devtester/issues/new?template=bug_report.yml)
4. **Ask Community**: [Stack Overflow](https://stackoverflow.com/questions/tagged/intersystems-iris) with tag `intersystems-iris`

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from iris_devtester.containers import IRISContainer
# You'll now see detailed logs
```

### Inspect Container State

```bash
# List all containers (including stopped)
docker ps -a

# View container logs
docker logs <container_id>

# Execute commands in running container
docker exec -it <container_id> bash

# Inside container, check IRIS status
docker exec -it <container_id> iris session IRIS -U%SYS "WRITE \$ZVERSION"
```

### Test Connection Manually

```python
from iris_devtester.containers import IRISContainer

with IRISContainer.community() as iris:
    print(f"Connection URL: {iris.get_connection_url()}")
    print(f"Host: {iris.host}")
    print(f"Port: {iris.port}")

    # Test DBAPI connection
    try:
        import irisnative
        conn = iris.get_connection()
        print("DBAPI: ✅")
    except Exception as e:
        print(f"DBAPI: ❌ {e}")

    # Test JDBC connection (fallback)
    try:
        import jaydebeapi
        # ... JDBC connection code
        print("JDBC: ✅")
    except Exception as e:
        print(f"JDBC: ❌ {e}")
```

### Common Configuration Issues

**Environment Variables:**
```bash
# Check if environment variables are set
env | grep IRIS

# Commonly used variables:
# IRIS_HOST, IRIS_PORT, IRIS_NAMESPACE, IRIS_USERNAME, IRIS_PASSWORD
```

**Docker Resource Limits:**
```bash
# Check Docker resources (macOS/Windows: Docker Desktop → Preferences → Resources)
docker info | grep -E "CPUs|Total Memory"

# Recommended minimums:
# - CPUs: 2
# - Memory: 4GB
```

---

**Remember**: IRIS DevTools is designed to handle most issues automatically. If you encounter consistent errors, please [report them](https://github.com/intersystems-community/iris-devtester/issues/new?template=bug_report.yml) so we can improve auto-remediation.
