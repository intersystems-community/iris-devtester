# Research: Fix Critical Container Creation Bugs

**Feature**: 010-fix-critical-bugs
**Date**: 2025-01-13
**Status**: Complete

## Executive Summary

Research completed for three critical bug fixes in iris-devtester container creation. Key findings:

1. **Docker Hub Image Names**: Community images use `intersystemsdc/iris-community`, Enterprise use `intersystems/iris`
2. **Volume Mounting API**: testcontainers-iris supports `with_volume_mapping(host_path, container_path)`
3. **Docker Error Types**: Specific exceptions available for ImageNotFound, APIError (port conflicts), DockerException
4. **Error Message Format**: Constitutional 4-part format (What/Why/How/Docs) already established
5. **Backwards Compatibility**: Image name fix is transparent, volume mounting is additive (no breaking changes)

## Research Topic 1: Docker Hub Image Names

### Decision
- **Community Edition**: `intersystemsdc/iris-community:{tag}`
- **Enterprise Edition**: `intersystems/iris:{tag}`

### Rationale
Docker Hub naming conventions for InterSystems IRIS:
- Community images published under `intersystemsdc/` organization (Docker Community)
- Enterprise images published under `intersystems/` organization (official InterSystems)
- The 'dc' suffix in `intersystemsdc` stands for "Docker Community"
- This is not documented in IRIS docs but is the actual Docker Hub reality

### Evidence
Current code (container_config.py:266) incorrectly uses:
```python
if self.edition == "community":
    return f"intersystems/iris-community:{self.image_tag}"  # WRONG!
```

Correct implementation:
```python
if self.edition == "community":
    return f"intersystemsdc/iris-community:{self.image_tag}"  # RIGHT
else:
    return f"intersystems/iris:{self.image_tag}"
```

### Alternatives Considered
- **Alternative 1**: Keep using `intersystems/iris-community`
  - **Rejected**: This image doesn't exist on Docker Hub, causes immediate failure
- **Alternative 2**: Use environment variable for image name
  - **Rejected**: Adds complexity for a straightforward naming convention fix

### Impact
- **Positive**: Community edition containers will work out of the box
- **Negative**: None - image name change is transparent to users (they specify edition, not image name)
- **Risk**: Low - existing configs don't specify image names directly

### References
- Docker Hub: https://hub.docker.com/r/intersystemsdc/iris-community
- Docker Hub: https://hub.docker.com/r/intersystems/iris

---

## Research Topic 2: testcontainers-iris Volume Mounting API

### Decision
Use `IRISContainer.with_volume_mapping(host_path, container_path, mode='rw')` method

### Rationale
testcontainers-python provides volume mapping through:
```python
container.with_volume_mapping(
    host="./local/path",
    container="/container/path",
    mode="rw"  # or "ro" for read-only
)
```

This aligns with our existing `ContainerConfig.volumes` field which uses Docker volume syntax:
```yaml
volumes:
  - "./data:/external"
  - "./config:/opt/config:ro"
```

### Implementation Approach
Parse volume strings in `IRISContainerManager.create_from_config()`:
```python
for volume in config.volumes:
    parts = volume.split(":")
    host_path = parts[0]
    container_path = parts[1]
    mode = parts[2] if len(parts) > 2 else "rw"

    container.with_volume_mapping(host_path, container_path, mode)
```

### Alternatives Considered
- **Alternative 1**: Use Docker SDK's `volumes` parameter directly
  - **Rejected**: testcontainers-iris wraps Docker SDK, should use its API
- **Alternative 2**: Mount volumes after container starts
  - **Rejected**: Volumes must be specified before container creation

### Validation
Volume mounts can be verified via:
```python
container.attrs['Mounts']  # Returns list of mount dictionaries
# Example: {'Source': '/host/path', 'Destination': '/container/path', 'Mode': 'rw'}
```

### References
- testcontainers-python docs: https://testcontainers-python.readthedocs.io/en/latest/
- testcontainers-iris source: https://github.com/caretdev/testcontainers-python-intersystems-iris

---

## Research Topic 3: Docker Error Types and Detection

### Decision
Enhance `translate_docker_error()` to handle specific Docker exception types

### Exception Types Identified

1. **docker.errors.ImageNotFound**
   - Raised when: Image doesn't exist on Docker Hub or locally
   - Example: `intersystems/iris-community:latest` (wrong name)
   - Detection: `isinstance(error, docker.errors.ImageNotFound)`

2. **docker.errors.APIError with port conflict**
   - Raised when: Port is already allocated to another container
   - Message contains: `"port is already allocated"` or `"address already in use"`
   - Detection: `isinstance(error, docker.errors.APIError) and "port" in str(error).lower()`

3. **docker.errors.APIError with permission denied**
   - Raised when: Docker daemon requires elevated permissions
   - Message contains: `"permission denied"`
   - Detection: `isinstance(error, docker.errors.APIError) and "permission" in str(error).lower()`

4. **docker.errors.DockerException (generic)**
   - Raised when: Docker daemon not running or not accessible
   - Detection: `isinstance(error, docker.errors.DockerException)`

### Implementation Strategy

```python
def translate_docker_error(error: Exception, config: Optional[ContainerConfig]) -> Exception:
    """Translate Docker errors to constitutional format."""
    from docker.errors import ImageNotFound, APIError, DockerException

    # Image not found
    if isinstance(error, ImageNotFound):
        image_name = config.get_image_name() if config else "unknown"
        return ValueError(
            f"Docker image '{image_name}' not found\n"
            "\n"
            "What went wrong:\n"
            f"  The Docker image '{image_name}' doesn't exist on Docker Hub or locally.\n"
            "\n"
            "How to fix it:\n"
            "  1. Check image name spelling\n"
            "  2. Pull image manually: docker pull {image_name}\n"
            "  3. Verify Docker Hub access\n"
            "\n"
            "Documentation: https://hub.docker.com/r/intersystemsdc/iris-community\n"
        )

    # Port conflict
    if isinstance(error, APIError) and ("port" in str(error).lower() or "address already in use" in str(error).lower()):
        port = config.superserver_port if config else "unknown"
        return ValueError(
            f"Port {port} is already in use\n"
            "\n"
            "What went wrong:\n"
            f"  Another container or process is using port {port}.\n"
            "\n"
            "How to fix it:\n"
            "  1. Stop conflicting container: docker ps | grep {port}\n"
            "  2. Use different port in config: superserver_port: 1973\n"
            "  3. Kill process using port: lsof -ti:{port} | xargs kill\n"
        )

    # Permission denied
    if isinstance(error, APIError) and "permission" in str(error).lower():
        return ConnectionError(
            "Docker daemon permission denied\n"
            "\n"
            "What went wrong:\n"
            "  Current user doesn't have permission to access Docker daemon.\n"
            "\n"
            "How to fix it:\n"
            "  1. Add user to docker group: sudo usermod -aG docker $USER\n"
            "  2. Log out and back in\n"
            "  3. Or run with sudo (not recommended)\n"
        )

    # Docker daemon not running
    if isinstance(error, DockerException):
        return ConnectionError(
            "Failed to connect to Docker daemon\n"
            "\n"
            "What went wrong:\n"
            "  Docker is not running or not accessible.\n"
            "\n"
            "How to fix it:\n"
            "  1. Start Docker Desktop (Mac/Windows)\n"
            "  2. Or start Docker daemon: sudo systemctl start docker (Linux)\n"
            "  3. Verify: docker ps\n"
        )

    # Unknown error - return original
    return error
```

### Alternatives Considered
- **Alternative 1**: Parse error messages with regex
  - **Rejected**: Less reliable than exception type checking
- **Alternative 2**: Catch all exceptions generically
  - **Rejected**: Loses specificity, can't provide targeted remediation

### References
- docker-py error types: https://docker-py.readthedocs.io/en/stable/api.html#module-docker.errors

---

## Research Topic 4: Error Message Best Practices

### Decision
Continue using established constitutional 4-part error message format

### Format Structure
```
{Brief error description}

What went wrong:
  {Technical explanation of the failure}

Why it matters:
  {Optional - impact/context if not obvious}

How to fix it:
  1. {Step-by-step remediation}
  2. {Alternative approaches}
  3. {Verification steps}

Alternative: {Optional - alternative approach}

Documentation: {Link to relevant docs}
```

### Rationale
- Already established in Constitution Principle #5 (Fail Fast with Guidance)
- Already implemented in existing `translate_docker_error()` function
- Users familiar with this format
- Provides actionable guidance, not just error descriptions

### Examples in Existing Code
See `iris_container_adapter.py:101-122` for port conflict example
See `iris_container_adapter.py:124-145` for Docker daemon not running example

### Implementation Notes
- "Why it matters" section optional when impact is obvious (port conflict, missing image)
- "Alternative" section useful for suggesting testcontainers vs manual Docker
- Documentation links should point to relevant troubleshooting guides

### References
- CONSTITUTION.md lines 206-251 (Principle #5: Fail Fast with Guidance)

---

## Research Topic 5: Backwards Compatibility Concerns

### Decision
All fixes maintain backwards compatibility

### Analysis

**Bug Fix 1: Image Name Correction**
- **Risk Level**: ✅ LOW
- **Impact**: Users don't specify image names directly, they specify `edition: community`
- **Config Format**: No changes to YAML schema
- **Existing Configs**: Continue to work unchanged
- **Validation**: All 35 contract tests should pass (they test CLI behavior, not image names)

**Bug Fix 2: Error Message Enhancement**
- **Risk Level**: ✅ NONE
- **Impact**: Error messages are informational only, not part of API contract
- **Changes**: Better error messages, same exception types
- **Existing Code**: Code catching exceptions continues to work
- **Validation**: Tests check exception types, not message content

**Bug Fix 3: Volume Mounting**
- **Risk Level**: ✅ NONE (additive change)
- **Impact**: `volumes` field already exists in ContainerConfig, was just ignored
- **New Behavior**: Volumes now actually get mounted (fixing the bug)
- **Existing Configs**: Configs without volumes continue to work
- **Validation**: Only new tests check volume mounting

### Migration Path
No migration needed - all fixes are:
1. **Transparent**: Image name change invisible to users
2. **Additive**: Volume mounting adds missing functionality
3. **Compatible**: Error messages don't affect API contracts

### Risk Mitigation
Run all 35 existing contract tests to verify no regression:
```bash
pytest tests/contract/ -v
```

### References
- NFR-001: "Fixes MUST maintain backwards compatibility with existing config files"
- NFR-002: "Fixes MUST not break existing integration tests"

---

## Summary of Decisions

| Research Area | Decision | Confidence | Risk |
|---------------|----------|------------|------|
| Docker Hub image names | Use `intersystemsdc/iris-community` | HIGH | LOW |
| Volume mounting API | Use `with_volume_mapping()` | HIGH | LOW |
| Docker error types | Enhance with specific exception handling | HIGH | NONE |
| Error message format | Continue constitutional 4-part format | HIGH | NONE |
| Backwards compatibility | All fixes are compatible | HIGH | LOW |

## Open Questions

None - all research topics resolved

## Next Steps

Proceed to Phase 1: Design & Contracts
- Generate data-model.md (minimal - only ContainerConfig changes)
- Generate contract JSON files for test scenarios
- Generate quickstart.md for verification steps
- Update CLAUDE.md with bug fix context

---

**Research Complete**: 2025-01-13
**Approver**: Ready for Phase 1
