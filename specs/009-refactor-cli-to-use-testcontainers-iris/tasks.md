# Feature 009: Refactor CLI to use testcontainers-iris - Tasks

**Feature**: Refactor container lifecycle CLI to use testcontainers-iris as implementation layer
**Goal**: Reduce code duplication from 462 lines → ~100 lines while preserving all CLI functionality
**Target**: v1.2.0
**Success Criteria**: All 35 contract tests pass, 75% code reduction, zero breaking changes

---

## Task Overview

**Total Tasks**: 16
- Phase 1 (Adapter Layer): 5 tasks
- Phase 2 (Integration): 7 tasks
- Phase 3 (Cleanup & Validation): 4 tasks

**Parallelizable Tasks**: Marked with [P]
**Estimated Time**: 2-3 hours total

---

## Phase 1: Adapter Layer (5 tasks)

### T001: Create IRISContainerAdapter Module [P]
**Status**: pending
**Files**:
- CREATE: `iris_devtester/utils/iris_container_adapter.py`

**Description**:
Create new adapter module with imports and module docstring.

**Implementation**:
```python
"""Adapter layer between CLI and testcontainers-iris.

This module provides a thin wrapper around testcontainers-iris for CLI use,
adapting the test-focused API for command-line container lifecycle management.
"""

from typing import Optional
import docker
from docker.models.containers import Container
from testcontainers.iris import IRISContainer

from iris_devtester.config.container_config import ContainerConfig
```

**Dependencies**: None
**Test**: Import succeeds

---

### T002: Implement IRISContainerManager.create_from_config() [P]
**Status**: pending
**Files**:
- EDIT: `iris_devtester/utils/iris_container_adapter.py`

**Description**:
Implement static method to create IRISContainer from ContainerConfig.

**Implementation**:
- Map ContainerConfig fields to IRISContainer constructor
- Use builder pattern for ports, volumes, environment
- Handle Community vs Enterprise edition (license key)
- Return configured IRISContainer (not started)

**Key Code**:
```python
@staticmethod
def create_from_config(config: ContainerConfig) -> IRISContainer:
    """Create IRISContainer from ContainerConfig.

    Args:
        config: Container configuration

    Returns:
        Configured IRISContainer (not started)
    """
    # Create base container
    container = IRISContainer(
        image=config.image,
        port=config.superserver_port,
        username=config.username,
        password=config.password,
        namespace=config.namespace,
        license_key=config.license_key if config.edition == "enterprise" else None
    )

    # Configure container
    container.with_name(config.container_name)
    container.with_bind_ports(config.superserver_port, config.superserver_port)
    container.with_bind_ports(config.webserver_port, config.webserver_port)

    # Add volume mappings for Enterprise license
    if config.edition == "enterprise" and config.license_key_path:
        container.with_volume_mapping(
            str(config.license_key_path),
            "/usr/irissys/mgr/iris.key",
            mode="ro"
        )

    return container
```

**Dependencies**: T001
**Test**: Creates IRISContainer with correct config

---

### T003: Implement IRISContainerManager.get_existing() [P]
**Status**: pending
**Files**:
- EDIT: `iris_devtester/utils/iris_container_adapter.py`

**Description**:
Implement static method to get existing container by name using Docker SDK.

**Implementation**:
- Use docker.from_env() to get Docker client
- Try to get container by name
- Return Container object or None if not found
- Handle Docker errors with constitutional format

**Key Code**:
```python
@staticmethod
def get_existing(container_name: str) -> Optional[Container]:
    """Get existing container by name.

    Args:
        container_name: Name of container to find

    Returns:
        Docker Container object or None if not found
    """
    try:
        client = docker.from_env()
        return client.containers.get(container_name)
    except docker.errors.NotFound:
        return None
    except docker.errors.DockerException as e:
        # Re-raise with constitutional error format
        raise ConnectionError(
            f"Failed to connect to Docker daemon\n"
            "\n"
            "What went wrong:\n"
            "  Docker is not running or not accessible.\n"
            # ... rest of constitutional error
        ) from e
```

**Dependencies**: T001
**Test**: Finds existing containers, returns None for non-existent

---

### T004: Implement Exception Translation Helper [P]
**Status**: pending
**Files**:
- EDIT: `iris_devtester/utils/iris_container_adapter.py`

**Description**:
Create helper function to translate Docker/testcontainers exceptions to constitutional format.

**Implementation**:
- Detect common error patterns (port in use, image not found, etc.)
- Convert to ValueError/ConnectionError with 4-part message (What/Why/How/Docs)
- Preserve original exception as cause

**Key Code**:
```python
def translate_docker_error(error: Exception, config: ContainerConfig) -> Exception:
    """Translate Docker errors to constitutional format.

    Args:
        error: Original Docker exception
        config: Container configuration (for context in error message)

    Returns:
        Translated exception with constitutional error message
    """
    error_str = str(error).lower()

    if "port is already allocated" in error_str:
        return ValueError(
            f"Port {config.superserver_port} is already in use\n"
            "\n"
            "What went wrong:\n"
            "  Another container or service is using the SuperServer port.\n"
            "\n"
            "Why it matters:\n"
            "  IRIS requires exclusive access to the SuperServer port.\n"
            "\n"
            "How to fix it:\n"
            "  1. Stop the conflicting container: docker ps\n"
            "  2. Change the port in iris-config.yml\n"
            "  3. Use environment variable: export IRIS_SUPERSERVER_PORT=2000\n"
            "\n"
            "Documentation: https://iris-devtester.readthedocs.io/troubleshooting/\n"
        )

    # Add more error patterns...

    # Default passthrough
    return error
```

**Dependencies**: T001
**Test**: Translates common errors correctly

---

### T005: Add Adapter Unit Tests [P]
**Status**: pending
**Files**:
- CREATE: `tests/unit/utils/test_iris_container_adapter.py`

**Description**:
Create unit tests for adapter module.

**Test Coverage**:
- `test_create_from_config_community()` - Community edition
- `test_create_from_config_enterprise()` - Enterprise with license
- `test_create_from_config_port_mapping()` - Port configuration
- `test_get_existing_found()` - Find existing container
- `test_get_existing_not_found()` - Returns None
- `test_translate_docker_error_port_conflict()` - Error translation
- `test_translate_docker_error_docker_not_running()` - Connection error

**Dependencies**: T002, T003, T004
**Test**: All adapter tests pass

---

## Phase 2: Integration - Update CLI Commands (7 tasks)

### T006: Refactor 'container up' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~30-150)

**Description**:
Replace docker_utils calls with iris_container_adapter in the 'up' command.

**Changes**:
1. Import `IRISContainerManager` instead of `docker_utils`
2. Use `IRISContainerManager.get_existing()` to check for existing container
3. Use `IRISContainerManager.create_from_config()` to create container
4. Call `iris.start()` instead of separate pull/create/start
5. Wrap operations with progress indicators
6. Use `iris.get_wrapped_container()` for health checks

**Implementation Pattern**:
```python
from iris_devtester.utils.iris_container_adapter import IRISContainerManager

@container_group.command(name="up")
def up(ctx, config, detach, timeout):
    progress = ProgressIndicator("Creating IRIS container")

    # Check for existing
    existing = IRISContainerManager.get_existing(container_config.container_name)
    if existing and existing.status == "running":
        # Already running
        return

    if existing:
        existing.start()
    else:
        progress.update("⏳ Configuring container...")
        iris = IRISContainerManager.create_from_config(container_config)

        progress.update("⏳ Pulling image and starting...")
        try:
            iris.start()
        except Exception as e:
            error = translate_docker_error(e, container_config)
            raise error

        container = iris.get_wrapped_container()

    # Health checks (unchanged)
    health_checks.wait_for_healthy(container, timeout, progress.update)
```

**Dependencies**: T001-T005
**Test**: Run contract tests for 'up' command (7 tests)

---

### T007: Refactor 'container start' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~151-200)

**Description**:
Replace docker_utils.start_container() with direct Docker SDK call via get_existing().

**Changes**:
- Use `IRISContainerManager.get_existing()` to get container
- Call `container.start()` directly
- Keep progress indicators

**Dependencies**: T006
**Test**: Contract test for 'start' command

---

### T008: Refactor 'container stop' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~201-250)

**Description**:
Replace docker_utils.stop_container() with direct Docker SDK call.

**Changes**:
- Use `IRISContainerManager.get_existing()`
- Call `container.stop(timeout=timeout)`
- Keep progress indicators

**Dependencies**: T006
**Test**: Contract test for 'stop' command

---

### T009: Refactor 'container restart' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~251-300)

**Description**:
Replace docker_utils.restart_container() with direct Docker SDK call.

**Changes**:
- Use `IRISContainerManager.get_existing()`
- Call `container.restart(timeout=timeout)`
- Preserve health checks after restart

**Dependencies**: T006
**Test**: Contract test for 'restart' command

---

### T010: Refactor 'container status' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~301-350)

**Description**:
Replace docker_utils calls with get_existing() for status command.

**Changes**:
- Use `IRISContainerManager.get_existing()`
- Access container.status, container.attrs directly
- Keep JSON/text formatting logic

**Dependencies**: T006
**Test**: Contract test for 'status' command

---

### T011: Refactor 'container logs' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~351-400)

**Description**:
Replace docker_utils.get_container_logs() with direct container.logs() call.

**Changes**:
- Use `IRISContainerManager.get_existing()`
- Call `container.logs(stream=follow, tail=tail, follow=follow)`
- Keep streaming/tail logic

**Dependencies**: T006
**Test**: Contract test for 'logs' command

---

### T012: Refactor 'container remove' Command
**Status**: pending
**Files**:
- EDIT: `iris_devtester/cli/container.py` (lines ~401-450)

**Description**:
Replace docker_utils.remove_container() with direct container.remove() call.

**Changes**:
- Use `IRISContainerManager.get_existing()`
- Call `container.remove(v=remove_volumes, force=True)`
- Keep progress indicators

**Dependencies**: T006
**Test**: Contract test for 'remove' command

---

## Phase 3: Cleanup & Validation (4 tasks)

### T013: Run Full Contract Test Suite
**Status**: pending
**Files**:
- NO CODE CHANGES

**Description**:
Run all 35 container CLI contract tests to verify no regressions.

**Command**:
```bash
pytest tests/contract/cli/ -v
```

**Success Criteria**:
- All 35 contract tests pass (100%)
- No new failures introduced
- Same exit codes, error messages, behavior

**Dependencies**: T006-T012
**Test**: 35/35 contract tests passing

---

### T014: Remove docker_utils.py
**Status**: pending
**Files**:
- DELETE: `iris_devtester/utils/docker_utils.py` (462 lines)

**Description**:
Remove the old docker_utils.py module now that it's replaced by the adapter.

**Verification**:
- Check no imports of docker_utils remain
- Grep codebase: `grep -r "from.*docker_utils" .`
- Grep codebase: `grep -r "import.*docker_utils" .`

**Dependencies**: T013 (verify tests pass first)
**Test**: Package still imports, tests still pass

---

### T015: Update CHANGELOG for v1.2.0
**Status**: pending
**Files**:
- EDIT: `CHANGELOG.md`

**Description**:
Add v1.2.0 release notes documenting the refactoring.

**Content**:
```markdown
## [1.2.0] - 2025-01-XX

### Changed

#### Refactored CLI to use testcontainers-iris
- **BREAKING**: None - all CLI commands maintain same interface
- Replaced custom Docker SDK wrapper (462 lines) with thin adapter (~100 lines)
- Now leverages testcontainers-iris for container operations
- 75% code reduction in container management layer
- Benefits: Shared bug fixes, reduced maintenance, battle-tested implementation

#### Technical Details
- New: `iris_container_adapter.py` (~100 lines) - Adapter between CLI and testcontainers-iris
- Removed: `docker_utils.py` (462 lines) - Replaced by testcontainers-iris
- Preserved: All 7 CLI commands, progress indicators, constitutional errors
- Preserved: Configuration management (YAML, env, validation)
- Preserved: Multi-layer health checks
- Tests: All 35 contract tests still passing (100%)

### Dependencies
- Leverages existing testcontainers-iris>=1.2.2 dependency
```

**Dependencies**: T013, T014
**Test**: CHANGELOG is accurate

---

### T016: Update Documentation
**Status**: pending
**Files**:
- EDIT: `README.md` (mention refactoring in Architecture section)
- EDIT: `V1_RELEASE_SUMMARY.md` (update v1.2.0 status)

**Description**:
Update documentation to reflect the architectural change.

**Changes to README.md**:
- Add note in Architecture section about testcontainers-iris integration
- Emphasize zero breaking changes

**Changes to V1_RELEASE_SUMMARY.md**:
- Update v1.2.0 status from "PLANNED" to "COMPLETE"
- Add completion date
- Document actual code reduction achieved

**Dependencies**: T015
**Test**: Documentation is clear and accurate

---

## Parallel Execution Strategy

### Batch 1: Adapter Layer (Parallel)
Run T001-T005 in parallel - they're independent:
```bash
# All adapter tasks can run simultaneously
Task 1: Create module
Task 2: create_from_config() implementation
Task 3: get_existing() implementation
Task 4: Exception translation
Task 5: Unit tests
```

### Batch 2: CLI Commands (Sequential)
Run T006-T012 sequentially - they all modify container.py:
```bash
# Must run in order since they edit the same file
Task 6: up command
Task 7: start command
Task 8: stop command
Task 9: restart command
Task 10: status command
Task 11: logs command
Task 12: remove command
```

### Batch 3: Cleanup (Sequential)
Run T013-T016 in order - each depends on previous:
```bash
Task 13: Verify tests pass
Task 14: Remove old module
Task 15: Update CHANGELOG
Task 16: Update docs
```

---

## Success Metrics

**Code Reduction**:
- Before: 462 lines (docker_utils.py)
- After: ~100 lines (iris_container_adapter.py)
- Reduction: ~75%

**Test Coverage**:
- Contract tests: 35/35 passing (100%)
- Unit tests: New adapter tests + existing tests
- Integration: Leverage testcontainers-iris tests

**Zero Breaking Changes**:
- All CLI commands same interface
- Same flags, same exit codes
- Same error messages (constitutional format)
- Same configuration files work

---

## Rollback Plan

If refactoring fails:
1. Revert commits (git revert)
2. Keep v1.1.0 shipped version
3. Investigate issues in separate branch
4. Try again in v1.2.1

Risk: LOW (testcontainers-iris is battle-tested, we control all changes)

---

## Completion Checklist

- [ ] T001-T005: Adapter layer complete
- [ ] T006-T012: All CLI commands refactored
- [ ] T013: All 35 contract tests pass
- [ ] T014: Old code removed
- [ ] T015-T016: Documentation updated
- [ ] Code reduction: >50% achieved
- [ ] Performance: No regression
- [ ] Error messages: Constitutional format preserved

**Ready to ship when all tasks complete!**
