# Quickstart: Verify Bug Fixes

**Feature**: 010-fix-critical-bugs
**Date**: 2025-01-13
**Purpose**: Step-by-step verification that all three bugs are fixed

## Prerequisites

- Python 3.11+
- Docker Desktop running
- iris-devtester installed: `pip install -e .`
- Fresh terminal session (no stale containers)

## Verification Steps

### Bug Fix 1: Correct Image Name

**Expected**: Community edition uses `intersystemsdc/iris-community` (not `intersystems/iris-community`)

**Steps**:

1. **Clean Docker state**:
   ```bash
   # Remove any existing IRIS containers
   docker rm -f iris_db 2>/dev/null || true

   # Remove old images to force fresh pull
   docker rmi intersystems/iris-community:latest 2>/dev/null || true
   docker rmi intersystemsdc/iris-community:latest 2>/dev/null || true
   ```

2. **Create Community edition container**:
   ```bash
   iris-devtester container up
   ```

   **Expected output**:
   ```
   ⚡ Creating container from zero-config defaults
     → Edition: community
     → Image: intersystemsdc/iris-community:latest  ← MUST BE intersystemsdc/
     → Ports: 1972, 52773
   ⏳ Configuring container...
   ⏳ Pulling image (if needed) and starting container...
   ✓ Container 'iris_db' created and started
   ```

3. **Verify image name via Docker**:
   ```bash
   docker inspect iris_db --format='{{.Config.Image}}'
   ```

   **Expected**: `intersystemsdc/iris-community:latest`
   **NOT**: `intersystems/iris-community:latest`

4. **Verify on Docker Hub**:
   ```bash
   # This should succeed (image exists)
   docker pull intersystemsdc/iris-community:latest

   # This should fail (image doesn't exist)
   docker pull intersystems/iris-community:latest 2>&1 | grep "not found"
   ```

**✅ Success Criteria**:
- Container starts successfully
- Image name contains `intersystemsdc/`
- Docker Hub pull succeeds for correct name

---

### Bug Fix 2: Clear Error Messages

**Expected**: Errors show constitutional format (What/Why/How), not "Failed to create container: 0"

**Test 1: Port Conflict Error**

1. **Create first container**:
   ```bash
   iris-devtester container up
   ```

2. **Try to create second container on same port**:
   ```bash
   # This should fail with clear error message
   iris-devtester container up 2>&1 | tee error_output.txt
   ```

   **Expected output includes**:
   ```
   Port 1972 is already in use

   What went wrong:
     Another container or process is using port 1972.

   How to fix it:
     1. Stop conflicting container: docker ps | grep 1972
     2. Use different port in config: superserver_port: 1973
     3. Kill process using port: lsof -ti:1972 | xargs kill
   ```

   **NOT expected**:
   ```
   ✗ Failed to create container: 0  ← OLD BAD MESSAGE
   ```

3. **Verify error message quality**:
   ```bash
   # Check for constitutional format
   grep -q "What went wrong:" error_output.txt && echo "✅ Has 'What' section"
   grep -q "How to fix it:" error_output.txt && echo "✅ Has 'How' section"

   # Check we don't have old error
   ! grep -q "Failed to create container: 0" error_output.txt && echo "✅ No silent failure message"
   ```

4. **Clean up**:
   ```bash
   docker rm -f iris_db
   rm error_output.txt
   ```

**Test 2: Image Not Found Error**

1. **Try to use non-existent image tag**:
   ```bash
   # Create config with bad image tag
   cat > test-config.yml << EOF
   edition: community
   image_tag: nonexistent-tag-12345
   EOF

   # Try to create container
   iris-devtester container up --config test-config.yml 2>&1 | tee image_error.txt
   ```

   **Expected output includes**:
   ```
   Docker image 'intersystemsdc/iris-community:nonexistent-tag-12345' not found

   What went wrong:
     The Docker image doesn't exist on Docker Hub or locally.

   How to fix it:
     1. Check image name spelling
     2. Pull image manually: docker pull ...
     3. Verify Docker Hub access
   ```

2. **Verify**:
   ```bash
   grep -q "not found" image_error.txt && echo "✅ Clear error message"
   grep -q "How to fix it:" image_error.txt && echo "✅ Has remediation"
   ```

3. **Clean up**:
   ```bash
   rm test-config.yml image_error.txt
   ```

**✅ Success Criteria**:
- No "Failed to create container: 0" messages
- All errors include "What went wrong:" section
- All errors include "How to fix it:" section
- Error messages are specific (mention port number, image name, etc.)

---

### Bug Fix 3: Volume Mounting

**Expected**: Volumes from config are actually mounted in container

**Steps**:

1. **Create test directory and file**:
   ```bash
   mkdir -p /tmp/iris-test-volumes/data
   echo "Test data from host" > /tmp/iris-test-volumes/data/test.txt
   ls -la /tmp/iris-test-volumes/data/
   ```

2. **Create config with volume mount**:
   ```bash
   cat > volume-config.yml << EOF
   edition: community
   container_name: iris_volume_test
   superserver_port: 1972
   webserver_port: 52773
   namespace: USER
   password: SYS
   volumes:
     - /tmp/iris-test-volumes/data:/external
   EOF
   ```

3. **Create container with volume mount**:
   ```bash
   iris-devtester container up --config volume-config.yml
   ```

4. **Verify mount exists via Docker inspect**:
   ```bash
   docker inspect iris_volume_test --format='{{json .Mounts}}' | python3 -m json.tool
   ```

   **Expected output includes**:
   ```json
   [
     {
       "Type": "bind",
       "Source": "/tmp/iris-test-volumes/data",
       "Destination": "/external",
       "Mode": "rw",
       ...
     }
   ]
   ```

5. **Verify file is accessible from inside container**:
   ```bash
   docker exec iris_volume_test cat /external/test.txt
   ```

   **Expected output**: `Test data from host`

6. **Verify write capability**:
   ```bash
   # Write from container
   docker exec iris_volume_test sh -c 'echo "Written from container" > /external/from_container.txt'

   # Read from host
   cat /tmp/iris-test-volumes/data/from_container.txt
   ```

   **Expected output**: `Written from container`

7. **Test read-only mount**:
   ```bash
   cat > readonly-config.yml << EOF
   edition: community
   container_name: iris_readonly_test
   superserver_port: 1973
   webserver_port: 52774
   volumes:
     - /tmp/iris-test-volumes/data:/external:ro
   EOF

   # Stop previous container
   docker rm -f iris_volume_test

   # Start with read-only mount
   iris-devtester container up --config readonly-config.yml

   # Try to write (should fail)
   docker exec iris_readonly_test sh -c 'echo "test" > /external/readonly_test.txt' 2>&1 | grep -q "Read-only file system" && echo "✅ Read-only mount working"
   ```

8. **Test multiple mounts**:
   ```bash
   mkdir -p /tmp/iris-test-volumes/config
   echo "Config file" > /tmp/iris-test-volumes/config/app.conf

   cat > multi-volume-config.yml << EOF
   edition: community
   container_name: iris_multi_test
   superserver_port: 1974
   webserver_port: 52775
   volumes:
     - /tmp/iris-test-volumes/data:/data
     - /tmp/iris-test-volumes/config:/config:ro
   EOF

   docker rm -f iris_readonly_test
   iris-devtester container up --config multi-volume-config.yml

   # Verify both mounts exist
   docker inspect iris_multi_test --format='{{len .Mounts}}'
   # Expected: 2 or more (may include IRIS internals)

   # Verify both are accessible
   docker exec iris_multi_test cat /data/test.txt
   docker exec iris_multi_test cat /config/app.conf
   ```

9. **Clean up**:
   ```bash
   docker rm -f iris_multi_test
   rm -rf /tmp/iris-test-volumes
   rm volume-config.yml readonly-config.yml multi-volume-config.yml
   ```

**✅ Success Criteria**:
- Volume mounts appear in `docker inspect`
- Files are readable from inside container
- Write operations work for rw mounts
- Write operations fail for ro mounts
- Multiple mounts all work simultaneously

---

## Automated Verification

Run all tests to verify fixes:

```bash
# Run all unit tests
pytest tests/unit/ -v -k "image_name or volume or error"

# Run integration tests for bug fixes
pytest tests/integration/test_bug_fixes.py -v

# Run all contract tests (verify no regression)
pytest tests/contract/ -v

# Summary
pytest tests/ -v --tb=short
```

**Expected results**:
- All new tests pass (image name, volume mounting, error handling)
- All 35 existing contract tests still pass (no regression)
- 0 failures, 0 errors

---

## Success Checklist

- [ ] Bug Fix 1: Image name verified via `docker inspect`
- [ ] Bug Fix 1: Container pulls correct image from Docker Hub
- [ ] Bug Fix 2: Port conflict shows constitutional error message
- [ ] Bug Fix 2: Image not found shows constitutional error message
- [ ] Bug Fix 2: No "Failed to create container: 0" messages
- [ ] Bug Fix 3: Single volume mount works (read-write)
- [ ] Bug Fix 3: Read-only volume mount works
- [ ] Bug Fix 3: Multiple volume mounts work
- [ ] Bug Fix 3: Volume files accessible from container
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All 35 contract tests pass (no regression)

---

## Troubleshooting

### "Image pull failed" even with correct name
- **Cause**: Network connectivity or Docker Hub rate limiting
- **Fix**: Wait a few minutes and retry, or use cached image

### "Port already in use" during tests
- **Cause**: Containers from previous tests not cleaned up
- **Fix**: `docker rm -f $(docker ps -aq -f name=iris_)`

### Volume mount not working
- **Cause**: Path doesn't exist or permissions issue
- **Fix**: Ensure directory exists and is readable: `ls -la /path/to/mount`

### Tests pass but quickstart fails
- **Cause**: Cached test results or stale Docker state
- **Fix**: Clear pytest cache and Docker state:
  ```bash
  pytest --cache-clear
  docker system prune -f
  ```

---

**Quickstart Complete**: All three bugs should now be verified as fixed
**Next Step**: Run `/implement` to execute task implementation
