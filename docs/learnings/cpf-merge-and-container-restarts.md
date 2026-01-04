# Critical: CPF Merge and Container Restart Issues

## The Problem: Days of Fighting This

**Container restarts lose configuration** including CallIn service, password settings, and other critical services.

### What Happens

```bash
# Day 1: Fresh start - everything works
docker-compose up -d
# CallIn enabled, passwords set, services configured ✓

# Day 2: Container restarts
docker-compose restart
# CallIn DISABLED, passwords EXPIRED, configuration LOST ❌
```

### Why This Happens

**IRIS Docker containers have TWO configuration states**:

1. **Ephemeral State** (lost on restart):
   - Service configurations (CallIn, etc.)
   - Password states
   - Runtime settings
   - Stored in memory/temp files

2. **Persistent State** (survives restart):
   - Database files (if volumes mounted)
   - CPF merge files (if properly configured)
   - Durable storage

**The Issue**: Configuration changes made via `iris session` are **EPHEMERAL** unless you use CPF merge!

## The Full Picture

### Scenario 1: Fresh Container (No CPF Merge)

```bash
docker run -d intersystemsdc/iris-community:latest
# Container starts
# CallIn: DISABLED (default)
# We run: iris session ... enable CallIn
# CallIn: ENABLED ✓
# Works great!

# Later: docker restart
# Container restarts
# CallIn: DISABLED ❌ (config lost!)
# ERROR: "CallIn not enabled"
```

**Why**: CallIn was enabled in memory, not persisted to CPF.

### Scenario 2: Container with Volume (130MB Database)

```bash
docker run -d -v /data:/dur intersystemsdc/iris-community:latest
# Container starts with EXISTING database
# CallIn: ENABLED (was enabled before, persisted in database) ✓
# Works!

# Later: docker restart
# Container restarts
# CallIn: STILL ENABLED ✓ (persisted in database)
# Works!
```

**Why**: Large database has persistent configuration.

### Scenario 3: Fresh Container (No CPF, No EnableCallIn)

This is the **DISASTER SCENARIO** we kept hitting:

```bash
# Startup script without CPF merge
docker-entrypoint.sh:
  - Start IRIS
  - Run initialization
  - DON'T enable CallIn (assumed it would persist)
  - DON'T merge CPF

# Day 1: Fresh start
# CallIn: DISABLED ❌
# We debug, manually enable it
# CallIn: ENABLED ✓

# Day 2: Container restart
# CallIn: DISABLED ❌ (lost again!)
# Repeat debugging...
```

**The Realization**: "The 130M database HAS CallIn enabled (it was working before). The problem is that when we removed the CPF merge from the startup, we never enabled it in the FIRST place for fresh starts."

## The Solutions

### Solution 1: CPF Merge (Traditional Approach)

Use IRIS CPF merge to persist configuration:

```dockerfile
# In Dockerfile or docker-entrypoint.sh
COPY iris.cpf /tmp/iris.cpf

# Merge CPF on startup
iris merge IRIS /tmp/iris.cpf
```

**iris.cpf**:
```
[config]
Globals=0,0,1536,0,0,0
Routines=256,32000,1024
GZIP=0
BUFFERSIZE=256
Language=en-us

[Startup]
...

[Service]
%Service_CallIn=1  # Enable CallIn permanently
```

**Pros**:
- Configuration persists across restarts
- Standard IRIS approach
- Well-documented

**Cons**:
- Requires CPF file management
- Merge order matters
- Can conflict with IRIS defaults

### Solution 2: Enable on Every Start (Idempotent - RECOMMENDED for Containers)

Make startup script **idempotent** - safe to run every time:

```bash
# docker-entrypoint.sh
#!/bin/bash

# Start IRIS
iris start IRIS

# ALWAYS enable CallIn (idempotent)
iris session IRIS -U %SYS << 'EOF'
  Do ##class(Security.Services).Get("%Service_CallIn", .svc)
  Set svc.Enabled = 1
  Do ##class(Security.Services).Modify(svc)
  Write "CallIn enabled", !
  Halt
EOF

# ALWAYS unexpire passwords (idempotent)
iris session IRIS -U %SYS << 'EOF'
  Do ##class(Security.Users).UnExpireUserPasswords("*")
  Write "Passwords unexpired", !
  Halt
EOF

echo "IRIS ready for connections"
```

**Pros**:
- Works on fresh start AND restart
- Idempotent (safe to run multiple times)
- No CPF file needed
- Simple to understand

**Cons**:
- Runs on every start (small overhead ~2 seconds)
- Not "persistent" in IRIS terms

### Solution 3: Durable %SYS (Enterprise Approach)

Use IRIS durable %SYS for true persistence:

```bash
docker run -d \
  --volume /data/dur:/dur \
  --env ISC_DATA_DIRECTORY=/dur/iconfig \
  intersystemsdc/iris-community:latest
```

**Pros**:
- True persistence (survives container deletion)
- Enterprise-grade
- Configuration changes persist automatically

**Cons**:
- More complex setup
- Requires volume management
- Not needed for ephemeral test containers

## What iris-devtester Must Do

### For IRISContainer (Testcontainers)

✅ **ALWAYS enable CallIn on container start**:

```python
class IRISContainer(BaseIRISContainer):
    def _connect(self):
        wait_for_logs(self, predicate="Enabling logons")

        # CRITICAL: Enable CallIn EVERY TIME
        # (container might be restarted)
        self._enable_callin_service()
        self._unexpire_passwords()

    def _enable_callin_service(self):
        """Enable CallIn - idempotent, safe to run every time."""
        cmd = (
            "iris session IRIS -U %SYS "
            "'Do ##class(Security.Services).Get(\"%Service_CallIn\",.s) "
            "Set s.Enabled=1 "
            "Do ##class(Security.Services).Modify(s)'"
        )
        result = self.exec(cmd)
        logger.info("✓ CallIn service enabled")

    def _unexpire_passwords(self):
        """Unexpire all passwords - idempotent."""
        cmd = (
            "iris session IRIS -U %SYS "
            "'Do ##class(Security.Users).UnExpireUserPasswords(\"*\")'"
        )
        result = self.exec(cmd)
        logger.info("✓ Passwords unexpired")
```

### For Documentation

Document this clearly:

1. **Why**: Container restarts lose ephemeral config
2. **What we do**: Enable CallIn + unexpire passwords on EVERY start
3. **Alternative**: CPF merge (when needed)
4. **Testing**: Verify config survives restart

## Testing Strategy

### Test 1: Fresh Start

```python
def test_fresh_container_has_callin():
    with IRISContainer.community() as iris:
        # Should work immediately
        conn = iris.get_connection()  # Uses DBAPI
        assert conn is not None
```

### Test 2: Restart Resilience

```python
def test_callin_survives_restart():
    container = IRISContainer.community()
    container.start()

    # Works before restart
    conn1 = container.get_connection()
    assert conn1 is not None

    # Restart container
    container.restart()

    # Should still work after restart
    conn2 = container.get_connection()
    assert conn2 is not None
```

### Test 3: CPF Merge (When Needed)

```python
def test_cpf_merge_for_production():
    container = IRISContainer.enterprise(
        license_key="/path/to/iris.key",
        cpf_file="/path/to/custom.cpf"  # Optional
    )
    # Custom CPF merged on start
```

## Historical Context: Why This Was So Painful

### The Debugging Journey

1. **Day 1**: Fresh container, manually enable CallIn → works ✓
2. **Day 2**: Container restart → "CallIn not enabled" ❌
3. **Debug**: Check logs, verify IRIS running, ports open
4. **Manually fix**: Enable CallIn again → works ✓
5. **Day 3**: Another restart → broken again ❌
6. **Realization**: "Oh, we need CPF merge"
7. **Remove CPF**: "We'll just enable on startup"
8. **Forget**: Don't actually add it to startup script
9. **Day 4-7**: Fresh containers fail, existing containers work
10. **Final realization**: "130M database has it enabled. Fresh starts don't."

### The Blind Alley

**What we tried that DIDN'T work**:
- ❌ Assuming CallIn persists (it doesn't)
- ❌ Enabling once and forgetting (lost on restart)
- ❌ Relying on CPF merge without testing
- ❌ Different behavior for fresh vs existing databases

**What WORKS**:
- ✅ Enable CallIn EVERY start (idempotent)
- ✅ Unexpire passwords EVERY start (idempotent)
- ✅ Test both fresh AND restart scenarios
- ✅ Make startup script bulletproof

## Checklist for iris-devtester

Container initialization must:

- [ ] Enable CallIn service (EVERY start)
- [ ] Unexpire passwords (EVERY start)
- [ ] Wait for IRIS ready (not just log message)
- [ ] Verify services enabled (health check)
- [ ] Log what was configured
- [ ] Be idempotent (safe to run multiple times)
- [ ] Work on fresh start AND restart
- [ ] Not require CPF merge (optional enhancement)

## References

- [IRIS CPF Reference](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RACS_cpf)
- [Security Services API](https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?LIBRARY=%25SYS&CLASSNAME=Security.Services)
- [Durable %SYS](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK_iris_durable)
- Constitutional Principle #1: Automatic Remediation

---

**Lesson Learned**: Container configuration is ephemeral by default. ALWAYS enable CallIn and unexpire passwords on EVERY container start. Make it idempotent. Test both fresh starts AND restarts. This is now automatic in iris-devtester so developers never fight this again.

**Time Saved**: Days of debugging → 2 seconds of automatic setup.
