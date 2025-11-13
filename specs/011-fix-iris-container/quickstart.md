# Quickstart: Fix IRIS Container Infrastructure Issues

**Feature**: 011-fix-iris-container
**Date**: 2025-01-13
**Purpose**: Manual testing guide to verify container persistence, volume mounting, and benchmark infrastructure support

## Prerequisites

- Docker Desktop running
- iris-devtester installed (will be version 1.2.2 after this feature)
- Python 3.9+ environment
- Terminal access

## Test Scenario 1: Container Persistence (5 minutes)

**Objective**: Verify containers created via CLI persist until explicit removal

### Steps

1. **Create container with unique name**
   ```bash
   # Create config file
   cat > iris-test-config.yml << EOF
   edition: community
   container_name: test-persistence-001
   superserver_port: 31972
   webserver_port: 58773
   namespace: USER
   password: SYS
   EOF

   # Create container
   iris-devtester container up --config iris-test-config.yml
   ```

   **Expected**: "✓ Container 'test-persistence-001' created and started" message

2. **Wait and verify container still exists**
   ```bash
   # Wait 2 minutes
   sleep 120

   # Check container status
   docker ps | grep test-persistence-001
   ```

   **Expected**: Container appears in list with status "Up X minutes"

3. **Verify container survives CLI exit**
   ```bash
   # Container was created in step 1 (CLI exited)
   # Check it still exists after 5 minutes
   sleep 180

   docker inspect test-persistence-001 --format '{{.State.Status}}'
   ```

   **Expected**: Output is "running"

4. **Check for testcontainers labels (should be absent)**
   ```bash
   docker inspect test-persistence-001 --format '{{.Config.Labels}}'
   ```

   **Expected**: No "org.testcontainers.session-id" label present

5. **Cleanup**
   ```bash
   iris-devtester container remove test-persistence-001
   ```

   **Expected**: Container removed successfully

### Success Criteria

✅ Container persists for 5+ minutes after CLI exits
✅ No testcontainers labels on container
✅ Container status remains "running" throughout test
✅ No "Failed to create container: 0" errors

## Test Scenario 2: Volume Mounting (5 minutes)

**Objective**: Verify workspace volumes are mounted and accessible

### Steps

1. **Create workspace directory with test files**
   ```bash
   # Create workspace
   mkdir -p ./test-workspace
   echo "Test file content" > ./test-workspace/test.txt
   echo "Class User.SimpleTestRunner { }" > ./test-workspace/SimpleTestRunner.cls
   ```

2. **Create container with volume mount**
   ```bash
   cat > iris-volume-config.yml << EOF
   edition: community
   container_name: test-volumes-001
   superserver_port: 32972
   webserver_port: 58774
   namespace: USER
   password: SYS
   volumes:
     - ./test-workspace:/external/workspace
   EOF

   iris-devtester container up --config iris-volume-config.yml
   ```

   **Expected**: Container created successfully

3. **Verify volume mount in Docker**
   ```bash
   docker inspect test-volumes-001 --format '{{json .Mounts}}' | jq
   ```

   **Expected**: JSON output shows mount with:
   - `"Destination": "/external/workspace"`
   - `"Source"` contains path to `test-workspace`
   - `"RW": true` (read-write mode)

4. **Verify files accessible from container**
   ```bash
   # Read test file
   docker exec test-volumes-001 cat /external/workspace/test.txt
   ```

   **Expected**: Output is "Test file content"

   ```bash
   # List workspace contents
   docker exec test-volumes-001 ls -la /external/workspace/
   ```

   **Expected**: Shows `test.txt` and `SimpleTestRunner.cls`

5. **Test read-only mount** (optional)
   ```bash
   # Create container with read-only mount
   cat > iris-readonly-config.yml << EOF
   edition: community
   container_name: test-readonly-001
   superserver_port: 33972
   webserver_port: 58775
   namespace: USER
   password: SYS
   volumes:
     - ./test-workspace:/readonly:ro
   EOF

   iris-devtester container up --config iris-readonly-config.yml

   # Try to write (should fail)
   docker exec test-readonly-001 touch /readonly/newfile.txt
   ```

   **Expected**: Error message about read-only filesystem

6. **Cleanup**
   ```bash
   iris-devtester container remove test-volumes-001
   iris-devtester container remove test-readonly-001
   rm -rf ./test-workspace
   rm iris-volume-config.yml iris-readonly-config.yml
   ```

### Success Criteria

✅ Volume mount appears in `docker inspect` output
✅ Files from host are readable in container
✅ Read-only mounts enforce permissions
✅ No silent volume mounting failures

## Test Scenario 3: Benchmark Infrastructure Pattern (10 minutes)

**Objective**: Simulate benchmark test execution pattern (24 operations over time)

### Steps

1. **Setup workspace with SimpleTestRunner**
   ```bash
   mkdir -p ./benchmark-workspace
   cat > ./benchmark-workspace/SimpleTestRunner.cls << 'EOF'
   Class User.SimpleTestRunner Extends %RegisteredObject
   {
       ClassMethod RunTest() As %String
       {
           Return "Test passed"
       }
   }
   EOF
   ```

2. **Create persistent container**
   ```bash
   cat > benchmark-config.yml << EOF
   edition: community
   container_name: benchmark-iris-001
   superserver_port: 34972
   webserver_port: 58776
   namespace: USER
   password: SYS
   volumes:
     - ./benchmark-workspace:/external/workspace
   EOF

   iris-devtester container up --config benchmark-config.yml
   ```

   **Expected**: Container created and started

3. **Run 24 test operations** (simplified simulation)
   ```bash
   # Simulate 24 test runs (each reads SimpleTestRunner.cls)
   for i in {1..24}; do
       echo "Test $i: $(date)"
       docker exec benchmark-iris-001 cat /external/workspace/SimpleTestRunner.cls | head -1
       sleep 15  # Wait 15 seconds between operations
   done
   ```

   **Expected**:
   - All 24 operations succeed
   - Each operation shows "Class User.SimpleTestRunner..."
   - No "container not found" errors
   - Total duration: ~6 minutes (24 * 15 seconds)

4. **Verify container still running after all operations**
   ```bash
   docker ps | grep benchmark-iris-001
   docker inspect benchmark-iris-001 --format '{{.State.Status}}'
   ```

   **Expected**: Container still running

5. **Check container uptime**
   ```bash
   docker inspect benchmark-iris-001 --format '{{.State.StartedAt}}'
   ```

   **Expected**: Started >6 minutes ago

6. **Cleanup**
   ```bash
   iris-devtester container remove benchmark-iris-001
   rm -rf ./benchmark-workspace
   rm benchmark-config.yml
   ```

### Success Criteria

✅ Container persists for all 24 operations
✅ SimpleTestRunner class accessible every time
✅ No connection failures during test execution
✅ Container uptime matches expected duration

## Test Scenario 4: Error Messaging (5 minutes)

**Objective**: Verify constitutional error messages (What/Why/How/Docs format)

### Steps

1. **Test invalid volume path**
   ```bash
   cat > invalid-config.yml << EOF
   edition: community
   container_name: test-errors-001
   superserver_port: 35972
   webserver_port: 58777
   namespace: USER
   password: SYS
   volumes:
     - /nonexistent/path:/data
   EOF

   iris-devtester container up --config invalid-config.yml
   ```

   **Expected**: Error message with sections:
   - "What went wrong:"
   - "How to fix it:"
   - Mentions path `/nonexistent/path` doesn't exist

2. **Test without Docker running** (optional, if safe)
   ```bash
   # Stop Docker Desktop briefly
   # Try to create container
   iris-devtester container up
   ```

   **Expected**: Clear error about Docker not running, with remediation steps

3. **Cleanup**
   ```bash
   rm invalid-config.yml
   ```

### Success Criteria

✅ Error messages follow What/Why/How/Docs format
✅ Specific paths and values mentioned in errors
✅ Remediation steps are actionable
✅ No cryptic "Failed to create container: 0" errors

## Performance Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Container creation (no pull) | <60s | _____ |
| Container creation (with pull) | <180s | _____ |
| Volume mount verification | <5s | _____ |
| Persistence check | <5s | _____ |
| 24-operation benchmark | ~6min | _____ |

## Troubleshooting

### Container disappears after creation

**Symptom**: "✓ Container created" but `docker ps` shows nothing

**Diagnosis**:
```bash
# Check ryuk logs
docker logs $(docker ps -a | grep ryuk | awk '{print $1}')

# Check container labels
docker inspect <container_name> --format '{{.Config.Labels}}'
```

**Fix**: Verify iris-devtester is using Docker SDK mode (not testcontainers mode)

### Volume not mounted

**Symptom**: `docker exec cat /container/path/file` returns "No such file"

**Diagnosis**:
```bash
# Check mounts
docker inspect <container_name> --format '{{json .Mounts}}' | jq

# Check host path exists
ls -la /host/path/
```

**Fix**: Verify host path exists before creating container

### "Failed to create container: 0" error

**Symptom**: Error message with exit code 0

**Cause**: Old version of iris-devtester (pre-1.2.2)

**Fix**: Upgrade to iris-devtester 1.2.2+

## Expected Outcomes

After completing all test scenarios:

✅ **Container Persistence**: Containers survive 5+ minutes, no ryuk cleanup
✅ **Volume Mounting**: Files accessible, read-only mode enforced
✅ **Benchmark Pattern**: 24 operations succeed, container persists throughout
✅ **Error Messages**: Constitutional format (What/Why/How/Docs)

**Overall Success**: Benchmark infrastructure can now achieve >90% pass rate (>22/24 tests)

## Documentation References

- Feature 010: Volume mounting fix (baseline)
- Feature 011: Container persistence fix (this feature)
- `docs/learnings/testcontainers-ryuk-lifecycle.md`: Ryuk cleanup details
- `docs/learnings/docker-hub-image-naming.md`: Image naming conventions
- Constitutional Principle #3: Isolation by Default
- Constitutional Principle #5: Fail Fast with Guidance

## Next Steps

After verifying all scenarios pass:

1. Run automated test suite: `pytest tests/integration/test_bug_fixes_011.py`
2. Run benchmark infrastructure: Verify >22/24 tests pass
3. Check regression: `pytest tests/contract/cli/` (35 tests should pass)
4. Update documentation with any findings
