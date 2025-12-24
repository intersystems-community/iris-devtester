# Quickstart: Defensive Container Validation

**Feature**: 014-address-this-enhancement
**Date**: 2025-01-17

## Overview

This quickstart demonstrates how to use defensive container validation to detect and handle Docker container issues gracefully.

---

## Scenario: Detecting Recreated Containers

**Problem**: You recreated a container with `docker-compose down && docker-compose up`, but your application still references the old container ID.

### Before (Cryptic Error)

```python
from iris_devtester.containers import IRISContainer

# Container was recreated outside Python
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # Error: container abc123... is not running
    # ^ Confusing! The container IS running, just with new ID
```

**Result**: Cryptic error, no guidance, manual debugging required.

---

### After (Clear Guidance)

```python
from iris_devtester.containers import IRISContainer, HealthCheckLevel

with IRISContainer.community() as iris:
    # Validate before using
    result = iris.validate(level=HealthCheckLevel.STANDARD)

    if not result.success:
        print(result.format_message())
        raise RuntimeError("Container validation failed")

    # Safe to use
    conn = iris.get_connection()
```

**Output** (if container recreated):
```
Container validation failed for 'iris_db'

What went wrong:
  Container was recreated with new ID.
  Cached ID: abc123... (stale)
  Current ID: def456... (active)

How to fix it:
  1. Clear cached references and restart:
     # Exit Python session and restart
     # Or recreate IRISContainer context manager

  2. Verify container is running:
     docker ps | grep iris_db
```

**Result**: Clear diagnosis, actionable remediation, problem solved quickly.

---

## Scenario: Proactive Health Checks

**Problem**: You want to verify a container is healthy before running tests.

### Implementation

```python
from iris_devtester.containers import validate_container, HealthCheckLevel

def setup_test_database():
    """Set up test database with health check."""

    # Validate container health
    result = validate_container(
        container_name="iris_test",
        level=HealthCheckLevel.FULL  # Full validation
    )

    if not result.success:
        print(f"Container not healthy: {result.message}")
        print("\nRemediation steps:")
        for step in result.remediation_steps:
            print(f"  {step}")
        raise RuntimeError("Test database not available")

    print(f"✓ Container healthy (validated in {result.validation_time:.2f}s)")
    return result.container_id


# Use in tests
def test_user_creation():
    container_id = setup_test_database()
    # Run tests...
```

**Output** (container healthy):
```
✓ Container healthy (validated in 0.35s)
```

**Output** (container not running):
```
Container not healthy: Container exists but is not running (status: exited)

Remediation steps:
  docker start iris_test
```

---

## Scenario: Listing Available Containers

**Problem**: You forgot the container name and want to see what's available.

### Implementation

```python
from iris_devtester.containers import validate_container

# Validate non-existent container
result = validate_container("wrong_name")

if result.status == "not_found":
    print(result.format_message())
```

**Output**:
```
Container validation failed for 'wrong_name'

What went wrong:
  Container 'wrong_name' does not exist.

How to fix it:
  1. List all containers:
     docker ps -a

  2. Start container if it exists:
     docker start wrong_name

  3. Or create new container:
     docker run -d --name wrong_name intersystemsdc/iris-community:latest

Available containers:
  - iris_db (running)
  - iris_test (running)
  - iris_prod (stopped)
```

---

## Scenario: Fast Validation for CI/CD

**Problem**: You want quick validation in CI/CD pipeline without full health checks.

### Implementation

```python
from iris_devtester.containers import validate_container, HealthCheckLevel

# Fast validation (just check if running)
result = validate_container(
    container_name="iris_ci",
    level=HealthCheckLevel.MINIMAL,  # Fast check
    timeout=5  # Short timeout for CI
)

if not result.success:
    print(f"CI container check failed: {result.message}")
    exit(1)

print(f"✓ Container ready (checked in {result.validation_time:.2f}s)")
```

**Performance**:
- `MINIMAL`: ~0.1s (just checks running status)
- `STANDARD`: ~0.3s (running + accessibility)
- `FULL`: ~0.8s (full IRIS health check)

---

## Scenario: Cached Validation for Repeated Checks

**Problem**: You validate the same container many times and want to avoid repeated Docker API calls.

### Implementation

```python
from iris_devtester.containers import ContainerValidator, HealthCheckLevel

# Create validator with caching
validator = ContainerValidator(
    container_name="iris_db",
    cache_ttl=10  # Cache for 10 seconds
)

# First validation (hits Docker API)
result1 = validator.validate(level=HealthCheckLevel.STANDARD)
print(f"First check: {result1.validation_time:.3f}s")

# Second validation (cached)
result2 = validator.validate()
print(f"Second check: {result2.validation_time:.3f}s")  # Much faster!

# Force refresh
result3 = validator.validate(force_refresh=True)
print(f"Force refresh: {result3.validation_time:.3f}s")

# Get detailed health info
health = validator.get_health()
print(f"Container ID: {health.container_id}")
print(f"Started at: {health.started_at}")
print(f"Image: {health.image}")
```

**Output**:
```
First check: 0.312s
Second check: 0.001s
Force refresh: 0.298s
Container ID: def456789012
Started at: 2025-01-17T10:30:00Z
Image: intersystemsdc/iris-community:latest
```

---

## Scenario: Assertion-Style Validation

**Problem**: You want validation to raise an exception if container is unhealthy.

### Implementation

```python
from iris_devtester.containers import IRISContainer, HealthCheckLevel

def test_database_operations():
    """Test database operations with assertion-style validation."""

    with IRISContainer.community() as iris:
        # Assert healthy (raises exception if not)
        iris.assert_healthy(level=HealthCheckLevel.FULL)

        # Safe to proceed
        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION")
        print(cursor.fetchone())
```

**Behavior**:
- If healthy: Continues silently
- If unhealthy: Raises `ContainerValidationError` with full error message

---

## Scenario: Handling Docker Daemon Down

**Problem**: Docker daemon is not running or accessible.

### Implementation

```python
from iris_devtester.containers import validate_container, ContainerHealthStatus

result = validate_container("iris_db")

if result.status == ContainerHealthStatus.DOCKER_ERROR:
    print(result.format_message())
    # Graceful degradation or retry logic
```

**Output**:
```
Container validation failed for 'iris_db'

What went wrong:
  Cannot connect to Docker daemon.
  Error: Error while fetching server API version

How to fix it:
  1. Check if Docker is running:
     docker --version

  2. Start Docker Desktop (macOS/Windows)
     # Or start Docker daemon (Linux):
     sudo systemctl start docker

  3. Verify Docker is accessible:
     docker ps
```

---

## Integration with pytest

### Fixture for Container Validation

```python
import pytest
from iris_devtester.containers import IRISContainer, HealthCheckLevel

@pytest.fixture(scope="module")
def iris_container():
    """Provide validated IRIS container for tests."""
    with IRISContainer.community() as iris:
        # Validate before yielding to tests
        result = iris.validate(level=HealthCheckLevel.FULL)

        if not result.success:
            pytest.skip(f"Container not healthy: {result.message}")

        yield iris


def test_database_query(iris_container):
    """Test database query with validated container."""
    conn = iris_container.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

---

## Complete Example: Production-Ready Validation

```python
"""
Production-ready container validation example.

Demonstrates:
- Comprehensive validation
- Graceful error handling
- Retry logic with backoff
- Detailed logging
"""

import logging
import time
from typing import Optional

from iris_devtester.containers import (
    validate_container,
    HealthCheckLevel,
    ValidationResult,
    ContainerHealthStatus
)

logger = logging.getLogger(__name__)


def wait_for_healthy_container(
    container_name: str,
    max_retries: int = 3,
    retry_delay: int = 5
) -> ValidationResult:
    """
    Wait for container to become healthy with retry logic.

    Args:
        container_name: Container to validate
        max_retries: Maximum retry attempts
        retry_delay: Seconds between retries

    Returns:
        ValidationResult when container healthy

    Raises:
        RuntimeError: If container not healthy after max_retries
    """
    for attempt in range(1, max_retries + 1):
        logger.info(f"Validating container (attempt {attempt}/{max_retries})...")

        result = validate_container(
            container_name=container_name,
            level=HealthCheckLevel.FULL,
            timeout=10
        )

        if result.success:
            logger.info(f"✓ Container healthy (validated in {result.validation_time:.2f}s)")
            return result

        # Log failure details
        logger.warning(f"Container validation failed: {result.status}")
        logger.warning(f"Message: {result.message}")

        # Special handling for different failure modes
        if result.status == ContainerHealthStatus.NOT_FOUND:
            # Don't retry if container doesn't exist
            logger.error("Container does not exist - aborting retries")
            print(result.format_message())
            raise RuntimeError(f"Container '{container_name}' not found")

        elif result.status == ContainerHealthStatus.DOCKER_ERROR:
            # Don't retry if Docker is down
            logger.error("Docker daemon not accessible - aborting retries")
            print(result.format_message())
            raise RuntimeError("Docker daemon not available")

        elif result.status in (ContainerHealthStatus.NOT_RUNNING, ContainerHealthStatus.RUNNING_NOT_ACCESSIBLE):
            # Retry for transient failures
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                # Final attempt failed
                logger.error("Container failed final validation attempt")
                print("\n" + result.format_message())
                raise RuntimeError(f"Container '{container_name}' not healthy after {max_retries} attempts")

    raise RuntimeError("Unexpected validation loop exit")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Wait for container with retry
    try:
        result = wait_for_healthy_container(
            container_name="iris_db",
            max_retries=3,
            retry_delay=5
        )
        print(f"\n✓ Container validated successfully!")
        print(f"  Container ID: {result.container_id}")
        print(f"  Validation time: {result.validation_time:.2f}s")

    except RuntimeError as e:
        print(f"\n✗ Container validation failed: {e}")
        exit(1)
```

**Output** (success):
```
2025-01-17 10:30:00 - INFO - Validating container (attempt 1/3)...
2025-01-17 10:30:00 - INFO - ✓ Container healthy (validated in 0.35s)

✓ Container validated successfully!
  Container ID: def456789012
  Validation time: 0.35s
```

**Output** (transient failure with retry):
```
2025-01-17 10:30:00 - INFO - Validating container (attempt 1/3)...
2025-01-17 10:30:00 - WARNING - Container validation failed: running_not_accessible
2025-01-17 10:30:00 - WARNING - Message: Container is running but not accessible
2025-01-17 10:30:00 - INFO - Retrying in 5 seconds...
2025-01-17 10:30:05 - INFO - Validating container (attempt 2/3)...
2025-01-17 10:30:05 - INFO - ✓ Container healthy (validated in 0.42s)

✓ Container validated successfully!
  Container ID: def456789012
  Validation time: 0.42s
```

---

## Summary

Defensive container validation provides:

✅ **Clear error messages** - No more cryptic "container not running" errors
✅ **Actionable remediation** - Copy-paste commands to fix issues
✅ **Proactive detection** - Catch problems before they cause failures
✅ **Progressive validation** - Fast checks for CI, deep checks for diagnostics
✅ **Caching support** - Avoid redundant Docker API calls
✅ **Constitutional compliance** - Automatic remediation, fail-fast guidance

**Next Steps**:
1. Run contract tests: `pytest tests/contract/test_container_validation_api.py`
2. Run integration tests: `pytest tests/integration/test_container_validation.py`
3. Review data model: See `data-model.md`
4. Review API contract: See `contracts/container-validation-api.md`
