# Critical: CallIn Service Must Be Enabled

## The Problem

**IRIS containers often start with CallIn service DISABLED by default**, which breaks DBAPI connections.

### Symptoms

```python
# This will fail silently or with cryptic errors:
import iris
conn = iris.connect(hostname="localhost", port=1972, namespace="USER",
                    username="_SYSTEM", password="SYS")
# Error: CallIn not enabled
```

Common error messages:
- "CallIn not enabled"
- "Connection refused" (even though IRIS is running)
- "Feature not enabled"
- Silent connection failures

## The Solution

### Method 1: Enable on Container Start (RECOMMENDED)

Add to your IRIS container startup script:

```bash
# In docker-entrypoint.sh or initialization script
iris session IRIS -U %SYS << 'EOF'
  Do ##class(Security.Services).Get("%Service_CallIn", .svc)
  Set svc.Enabled = 1
  Do ##class(Security.Services).Modify(svc)
  Halt
EOF
```

### Method 2: Enable via Docker Exec

If container already running:

```bash
docker exec -it iris_container_name \
  iris session IRIS -U %SYS \
  'Do ##class(Security.Services).Get("%Service_CallIn",.s) Set s.Enabled=1 Do ##class(Security.Services).Modify(s)'
```

### Method 3: Enable in iris-devtester (AUTOMATIC)

We handle this automatically in `IRISContainer`:

```python
class IRISContainer(BaseIRISContainer):
    def _connect(self):
        # Wait for IRIS to start
        wait_for_logs(self, predicate="Enabling logons")

        # CRITICAL: Enable CallIn service for DBAPI
        self._enable_callin_service()

    def _enable_callin_service(self):
        """Enable CallIn service for DBAPI connections."""
        cmd = (
            "iris session IRIS -U %SYS "
            "'Do ##class(Security.Services).Get(\"%Service_CallIn\",.s) "
            "Set s.Enabled=1 "
            "Do ##class(Security.Services).Modify(s)'"
        )
        result = self.exec(cmd)
        logger.info("CallIn service enabled for DBAPI")
```

## Why This Matters

### CallIn Service Overview

CallIn is the IRIS service that allows **external programs** to call into IRIS ObjectScript:
- Python DBAPI connections use CallIn
- External applications calling IRIS methods use CallIn
- Required for: embedded Python, external APIs, DBAPI connections

**Default State**: Often DISABLED in Docker containers for security

### Impact on Connection Methods

| Connection Method | Requires CallIn? |
|-------------------|------------------|
| **DBAPI** (intersystems-irispython) | ✅ YES - WILL FAIL without it |
| **JDBC** (jaydebeapi) | ❌ No - Uses different service |
| **HTTP/REST** | ❌ No - Uses web services |
| **Native IRIS SQL** | ❌ No - Internal connections |

This is why our **DBAPI-first, JDBC fallback** strategy is critical:
1. Try DBAPI (faster, but requires CallIn)
2. If fails → automatically try JDBC (slower, but works)
3. User never knows which is being used

## Best Practices

### For iris-devtester

✅ **DO**:
- Automatically enable CallIn on container start
- Log when CallIn is enabled
- Verify CallIn status before DBAPI connection
- Fall back to JDBC if CallIn unavailable

❌ **DON'T**:
- Assume CallIn is enabled
- Fail without clear error message
- Require manual intervention

### For Production IRIS Instances

✅ **DO**:
- Enable CallIn if using DBAPI
- Document which services are enabled
- Test connections after enabling
- Consider security implications (CallIn allows code execution)

❌ **DON'T**:
- Enable CallIn blindly in production (security risk)
- Leave CallIn enabled if not needed
- Forget to document service state

## Security Considerations

**CallIn allows external code execution** - this is powerful but risky.

### Security Best Practices

1. **Development/Testing**: Enable CallIn freely
2. **Production**:
   - Only enable if DBAPI connections required
   - Use firewall rules to restrict access
   - Monitor CallIn usage
   - Consider JDBC if CallIn too risky

3. **Containers**:
   - Enable CallIn in Dockerfile/entrypoint
   - Document why it's enabled
   - Network isolation for security

## Testing CallIn Status

```python
# Check if CallIn is enabled
def check_callin_enabled(container):
    cmd = (
        "iris session IRIS -U %SYS "
        "'Write ##class(Security.Services).Get(\"%Service_CallIn\",.s) "
        "Write s.Enabled'"
    )
    result = container.exec(cmd)
    return "1" in result.output.decode()
```

## Historical Context

### Why This Wasn't Obvious

1. **Works in VM installations**: CallIn often enabled by default
2. **Docker containers differ**: Security-first approach disables services
3. **JDBC doesn't need it**: Masking the issue if using JDBC
4. **Cryptic errors**: "Connection refused" doesn't say "enable CallIn"

### How We Discovered This

- Hours debugging "connection refused" errors
- IRIS running, ports open, credentials correct
- Worked with JDBC but not DBAPI
- Finally found CallIn service was disabled
- Now: **AUTOMATIC in iris-devtester**

## Implementation Checklist

For iris-devtester IRISContainer:

- [ ] Enable CallIn on container start
- [ ] Log CallIn enablement
- [ ] Verify CallIn before DBAPI connection
- [ ] Fall back to JDBC if CallIn fails
- [ ] Document CallIn requirement
- [ ] Test with CallIn disabled (verify fallback)
- [ ] Test with CallIn enabled (verify DBAPI works)

## References

- [IRIS CallIn Documentation](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BGNT_callin)
- [Security Services API](https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?LIBRARY=%25SYS&CLASSNAME=Security.Services)
- Constitutional Principle #1: Automatic Remediation (this is a perfect example)

---

**Lesson Learned**: Always enable CallIn for DBAPI connections in containers. This is now automatic in iris-devtester so developers never encounter this issue.
