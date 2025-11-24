# Reproducing iris-devtester macOS Password Reset Bug

This document provides step-by-step instructions to reproduce the password reset bug observed on macOS with iris-devtester v1.4.2-v1.4.5.

## Bug Summary

**Symptoms:**
- Container starts successfully
- `wait_for_ready()` completes without error
- Password reset command executes (exit_code=0)
- **Connection fails with "Access Denied" error**

**Expected behavior:** After successful password reset, `get_connection()` should establish connection.

**Actual behavior:** Password reset executes but IRIS doesn't process it, causing connection failure.

## System Information

**Affected System:**
- OS: macOS Darwin 24.5.0
- Docker: Docker Desktop (latest)
- Python: 3.12
- iris-devtester: v1.4.2, v1.4.3, v1.4.4, v1.4.5 (all four versions fail identically)
- IRIS Image: intersystemsdc/iris-community:latest

## Prerequisites

1. **macOS with Docker Desktop installed**
   ```bash
   # Verify Docker is running
   docker ps
   ```

2. **Python 3.12+ installed**
   ```bash
   python3 --version
   ```

3. **iris-devtester installed**
   ```bash
   pip install iris-devtester==1.4.5
   # Or use the version you want to test
   ```

## Reproduction Steps

### Option 1: Using the Automated Test Script (Recommended)

1. **Navigate to iris-devtester directory:**
   ```bash
   cd /Users/tdyar/ws/iris-devtester
   ```

2. **Run the reproduction script:**
   ```bash
   chmod +x reproduce_macos_password_bug.py
   python3 reproduce_macos_password_bug.py
   ```

3. **Expected output if bug reproduces:**
   ```
   ================================================================================
   iris-devtester macOS Password Reset Bug Reproduction
   ================================================================================

   Step 1: Checking iris-devtester version...
   ✅ iris-devtester version: 1.4.5

   Step 2: Importing iris-devtester modules...
   ✅ Modules imported successfully

   Step 3: Creating IRIS container with PortRegistry...
   ✅ Container created

   Step 4: Starting container...
   ✅ Container started
   ✅ Assigned port: 1973

   Step 5: Waiting for IRIS to be ready (timeout: 90s)...
   ✅ Container ready after 6.4s

   Step 6: Testing connection (CRITICAL - this is where bug manifests)...
   ❌ CONNECTION FAILED!
      Error: <COMMUNICATION LINK ERROR> Failed to connect to server;
             Details: <COMMUNICATION ERROR> Invalid Message received;
             Details: Access Denied

   ================================================================================
   🐛 BUG REPRODUCED: Password reset failure on macOS
   ================================================================================

   Symptoms:
   - Container starts successfully
   - wait_for_ready() completes without error
   - Password reset command likely executed (exit_code=0)
   - Connection fails with 'Access Denied' or similar error

   This indicates the password reset executed but IRIS didn't process it.

   System Information:
     OS: Darwin 24.5.0
     Python: 3.12.x
     iris-devtester: 1.4.5
     Assigned port: 1973

   Step 7: Cleaning up container...
   ✅ Container stopped and cleaned up
   ```

4. **Expected output if bug does NOT reproduce:**
   ```
   ✅ CONNECTION SUCCESSFUL!
      Password reset worked correctly!
   ✅ Query executed successfully

   ================================================================================
   🎉 SUCCESS: Password reset bug NOT reproduced!
   ================================================================================

   iris-devtester is working correctly on this system.
   ```

### Option 2: Manual Testing (Step-by-Step)

1. **Create test script:**
   ```python
   from iris_devtester.containers import IRISContainer
   from iris_devtester.ports import PortRegistry

   # Create container with PortRegistry
   registry = PortRegistry()
   iris = IRISContainer.community(
       username='SuperUser',
       password='SYS',
       namespace='HIPPORAG',
       port_registry=registry
   )

   # Start container
   iris.start()
   print(f"Container started on port {iris.get_assigned_port()}")

   # Wait for ready (password reset happens here)
   iris.wait_for_ready(timeout=90)
   print("Container is ready")

   # CRITICAL TEST: Attempt connection
   try:
       conn = iris.get_connection()
       print("✅ CONNECTION SUCCESSFUL!")

       # Verify with query
       cursor = conn.cursor()
       cursor.execute("SELECT 1")
       result = cursor.fetchone()
       print(f"✅ Query result: {result[0]}")

       cursor.close()
       conn.close()

   except Exception as e:
       print(f"❌ CONNECTION FAILED: {e}")
       print("BUG REPRODUCED!")

   finally:
       iris.stop()
   ```

2. **Run the test:**
   ```bash
   python3 test_password_reset.py
   ```

3. **Observe output:**
   - If bug reproduces: Connection fails with "Access Denied"
   - If bug doesn't reproduce: Connection succeeds and query executes

### Option 3: Testing Multiple Versions

To test if bug affects multiple versions:

```bash
# Test v1.4.2
pip install iris-devtester==1.4.2 --force-reinstall
python3 reproduce_macos_password_bug.py

# Test v1.4.3
pip install iris-devtester==1.4.3 --force-reinstall
python3 reproduce_macos_password_bug.py

# Test v1.4.4
pip install iris-devtester==1.4.4 --force-reinstall
python3 reproduce_macos_password_bug.py

# Test v1.4.5
pip install iris-devtester==1.4.5 --force-reinstall
python3 reproduce_macos_password_bug.py
```

On the affected system, all four versions fail identically.

## Additional Diagnostic Tests

### Test 1: Manual Password Reset

After container starts, try manual password reset:

```bash
# Get container name (e.g., "compassionate_turing")
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Attempt manual password reset
docker exec <container_name> iris session IRIS -U %SYS '##class(Security.Users).UnExpireUserPasswords("*")'

# Try connection again
python3 -c "
from iris_devtester.containers import IRISContainer
from iris_devtester.ports import PortRegistry

registry = PortRegistry()
iris = IRISContainer.community(port_registry=registry)
iris.start()
iris.wait_for_ready(timeout=90)

try:
    conn = iris.get_connection()
    print('✅ Connection successful')
except Exception as e:
    print(f'❌ Connection failed: {e}')
finally:
    iris.stop()
"
```

On affected system, manual password reset also fails.

### Test 2: Check Docker Logs

View container logs to see password reset attempts:

```bash
# Start container
python3 -c "
from iris_devtester.containers import IRISContainer
from iris_devtester.ports import PortRegistry

registry = PortRegistry()
iris = IRISContainer.community(port_registry=registry)
iris.start()
print(f'Container: {iris.container.name}')
print(f'Port: {iris.get_assigned_port()}')
print('Press Ctrl+C when done')
import time
time.sleep(300)
"

# In another terminal, check logs
docker logs -f <container_name> 2>&1 | grep -i "password\|user\|auth"
```

### Test 3: Verify Docker Configuration

```bash
# Check Docker version
docker version

# Check Docker Desktop settings
# Go to Docker Desktop > Settings > Resources
# Verify sufficient resources allocated

# Check for other IRIS containers
docker ps -a | grep iris

# Stop all IRIS containers
docker stop $(docker ps -a -q --filter ancestor=intersystemsdc/iris-community)
docker rm $(docker ps -a -q --filter ancestor=intersystemsdc/iris-community)

# Retry test with clean Docker state
python3 reproduce_macos_password_bug.py
```

## What to Report

If you can reproduce the bug, please report:

1. **System information:**
   ```bash
   uname -a
   python3 --version
   docker version
   pip show iris-devtester
   ```

2. **Test output:**
   - Complete output from `reproduce_macos_password_bug.py`
   - Any error messages or stack traces

3. **Docker logs:**
   - Container logs showing password reset attempts
   - Any authentication-related errors

4. **Environment:**
   - Any custom Docker Desktop settings
   - VPN or network proxies in use
   - Security software (e.g., firewalls, antivirus)

## Known Workarounds

If you encounter this bug in your development:

### Workaround 1: Use Existing Container

Instead of creating new containers, use an existing container with working password:

```python
import os

# Set environment variables to use existing container
os.environ['SKIP_IRIS_CONTAINER'] = '1'
os.environ['IRIS_HOST'] = 'localhost'
os.environ['IRIS_PORT'] = '41972'  # Your existing container port
os.environ['IRIS_USERNAME'] = 'SuperUser'
os.environ['IRIS_PASSWORD'] = 'SYS'
os.environ['IRIS_NAMESPACE'] = 'HIPPORAG'

# Now use your code normally - it will connect to existing container
```

### Workaround 2: Pre-Create Container Manually

```bash
# Create container with working password state
docker run -d \
  --name iris-dev \
  -p 1972:1972 \
  -p 52773:52773 \
  intersystemsdc/iris-community:latest

# Configure password manually (if needed)

# Use this container in your code
```

## Additional Context

**Background:**
- This bug was discovered during HippoRAG2 pipeline development
- Affects iris-devtester v1.4.2 through v1.4.5
- Only observed on one specific macOS system (Darwin 24.5.0)
- Same iris-devtester versions work correctly on other systems

**Prior Testing:**
- iris-devtester has 12/12 contract tests passing
- Reported 100% success rate on macOS in testing
- Bug appears to be environment-specific or edge case

**Related Files:**
- Bug report: `../hipporag2-pipeline/IRIS_DEVTESTER_BUG_REPORT.md`
- Constitution: `../hipporag2-pipeline/CONSTITUTION.md` (lines 110-177)

## Contact

If you can reproduce this bug or have additional diagnostic information, please:

1. Open an issue in the iris-devtester repository
2. Include output from `reproduce_macos_password_bug.py`
3. Attach system information and logs

---

**Last Updated:** 2025-11-21
**Reporter:** Automated bug detection during HippoRAG2 development
**Status:** Under investigation
