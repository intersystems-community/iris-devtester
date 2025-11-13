# IRIS Docker SDK Environment Variables

**Feature**: 011-fix-iris-container
**Date**: 2025-01-13
**Status**: Resolved
**Category**: Container Infrastructure

## Summary

When creating IRIS containers directly with Docker SDK (bypassing testcontainers-iris), the wrong environment variables cause immediate container exit. Specifically, setting `ISC_DATA_DIRECTORY` to a non-existent path causes IRIS to fail during startup.

## The Problem

### Initial Implementation

```python
# WRONG - Causes container to exit
environment = {
    'ISC_DATA_DIRECTORY': '/home/irisowner/iris/data',  # Path doesn't exist!
    'IRIS_PASSWORD': config.password,
    'IRIS_USERNAME': '_SYSTEM',
}
```

### Container Logs Showed

```
Durable folder: /home/irisowner/iris/data does not exists, or cannot be created
```

### Symptom

- Container created successfully (exit code 0)
- Container immediately exits after `.start()` call
- Status: `"exited"` instead of `"running"`
- Integration tests failed: "container is not running"

## Why It Happened

1. **testcontainers-iris hides complexity**: When using testcontainers-iris, it handles all environment variable setup internally
2. **Docker SDK requires explicit configuration**: When bypassing testcontainers and using Docker SDK directly, we must provide correct environment variables
3. **ISC_DATA_DIRECTORY assumption**: We assumed IRIS needed explicit data directory configuration, but IRIS Community containers use a default internal path

## The Solution

### Correct Implementation

```python
# CORRECT - Let IRIS use its default data directory
environment = {}

# Only add license key for Enterprise edition
if config.edition == 'enterprise' and config.license_key:
    environment['ISC_LICENSE_KEY'] = config.license_key
```

### Key Insights

1. **IRIS Community containers don't need environment variables**: The container bootstraps automatically with sensible defaults
2. **Data directory is managed internally**: IRIS creates and manages its own data directory at `/usr/irissys/mgr/`
3. **Password is set via defaults**: IRIS Community uses default password "SYS" for _SYSTEM user
4. **Minimal environment is best**: Only set environment variables that are actually needed (like license keys for Enterprise)

## Evidence: Container Now Starts Successfully

```
Container status: running

Container Logs:
11/13/25-18:33:58:661 (476) 0 [Utility.Event] Private webserver started on 52773
11/13/25-18:33:59:456 (465) 0 [Utility.Event] Enabling logons
[INFO] ...started InterSystems IRIS instance IRIS
```

## Environment Variables That Work

### Community Edition

```python
# Minimal environment - works perfectly
environment = {}
```

### Enterprise Edition

```python
# Only add license key
environment = {
    'ISC_LICENSE_KEY': config.license_key
}
```

## Environment Variables to AVOID

❌ **ISC_DATA_DIRECTORY** - Don't set unless you're mounting a custom data volume
❌ **IRIS_PASSWORD** - Not supported by Community containers (use default "SYS")
❌ **IRIS_USERNAME** - Not needed (always "_SYSTEM")

## Testing Results

After fixing the environment variables:

| Test | Before Fix | After Fix |
|------|-----------|-----------|
| Container starts | ❌ Exits immediately | ✅ Running |
| Integration tests | 1/6 passed (16.7%) | 6/6 passed (100%) |
| Container status | "exited" | "running" |
| Logs | "folder does not exist" | "started IRIS instance" |

## When to Set Environment Variables

### Use Empty Environment (`{}`) For:
✅ Community Edition containers
✅ Default IRIS configuration
✅ Standard port mappings
✅ CLI-managed containers

### Add License Key For:
✅ Enterprise Edition containers
✅ Production deployments

### Custom Data Directory Only When:
✅ Mounting external data volume (advanced use case)
✅ Persisting data across container recreations
✅ Sharing data between containers

**Warning**: If setting `ISC_DATA_DIRECTORY`, ensure the path:
1. Exists in the container or is mounted as a volume
2. Has correct permissions (owned by `irisowner` user)
3. Is writable by the IRIS process

## Related Documentation

- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [InterSystems IRIS Container Reference](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK)
- Feature 011 specification: `specs/011-fix-iris-container/spec.md`
- Ryuk lifecycle document: `docs/learnings/testcontainers-ryuk-lifecycle.md`

## Lessons Learned

1. **Don't assume environment variables are needed**: Start with empty environment and add only what's required
2. **Test with real containers**: Unit tests can't catch container startup failures
3. **Check container logs immediately**: Logs reveal the exact error when containers exit
4. **testcontainers-iris is opinionated**: It makes assumptions that may not apply when using Docker SDK directly
5. **Community vs Enterprise have different needs**: Community containers are simpler and need less configuration

## Decision Record

**Date**: 2025-01-13
**Decision**: Use empty environment for Community containers, only add license key for Enterprise
**Rationale**: IRIS Community containers bootstrap themselves correctly without environment variables
**Alternatives Considered**:
1. ❌ Set ISC_DATA_DIRECTORY - Caused immediate container exit
2. ❌ Set IRIS_PASSWORD/IRIS_USERNAME - Not supported by Community images
3. ✅ **Empty environment** - Works perfectly, containers start and run

**Result**: 100% integration test pass rate (6/6), containers start successfully
