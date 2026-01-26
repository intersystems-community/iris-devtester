# Quickstart: Pre-configure Passwords at Container Startup

**Feature**: 001-preconfigure-passwords  
**Date**: 2026-01-24

## Overview

Pre-configure IRIS credentials at container startup to eliminate the 5-10 second "Hardening user accounts..." delay.

## Quick Usage

### Option 1: Environment Variable (Recommended for CI/CD)

```bash
# Set environment variable before running tests
export IRIS_PASSWORD=MySecretPass

# Run your tests - password pre-configuration happens automatically
pytest
```

### Option 2: Programmatic API

```python
from iris_devtester.containers import IRISContainer

# Simple: just pre-configure password
with IRISContainer.community().with_preconfigured_password("MySecretPass") as iris:
    conn = iris.get_connection()
    # Connection is ready immediately - no password reset delay!

# Advanced: custom username and password
with IRISContainer.community().with_credentials(
    username="dev",
    password="MySecretPass"
) as iris:
    conn = iris.get_connection()
```

### Option 3: Existing Behavior (Unchanged)

```python
# No changes needed - existing code continues to work
with IRISContainer.community() as iris:
    conn = iris.get_connection()
    # Still works, just uses password reset (5-10s slower)
```

## What Changes

| Before | After |
|--------|-------|
| Container starts | Container starts |
| Wait for IRIS ready (~10s) | Wait for IRIS ready (~10s) |
| **Password reset (~5-10s)** | **Skipped!** |
| Connection ready | Connection ready |

**Time saved**: 5-10 seconds per container startup

## How It Works

1. When `IRIS_PASSWORD` env var is set OR `with_preconfigured_password()` is called
2. The password is passed to the Docker container via environment variable
3. IRIS configures the password at startup (no post-startup reset needed)
4. Connection is verified immediately after container ready
5. If verification fails, system falls back to password reset (reliability preserved)

## Troubleshooting

### Pre-configuration Not Working?

Check the logs:
```
INFO: Password pre-configuration enabled via IRIS_PASSWORD environment variable
INFO: Password pre-configuration succeeded - skipping hardening step
```

If you see:
```
WARN: Password pre-configuration failed - falling back to password reset
```

This means:
- The IRIS image may not support password pre-configuration (older images)
- The system automatically fell back to the existing mechanism
- Your tests still work, just without the speedup

### Verify Pre-configuration Status

```python
with IRISContainer.community().with_preconfigured_password("MyPass") as iris:
    if iris._password_preconfigured:
        print("Pre-configuration succeeded!")
    else:
        print("Fell back to password reset")
```

## Best Practices

1. **CI/CD**: Use `IRIS_PASSWORD` environment variable for consistent behavior
2. **Local Development**: Use `with_preconfigured_password()` for explicit control
3. **Shared Fixtures**: Pre-configured containers are great for module-scoped fixtures
4. **Mixed Environments**: The automatic fallback ensures tests work everywhere

## Example: pytest Fixture

```python
import pytest
from iris_devtester.containers import IRISContainer

@pytest.fixture(scope="module")
def fast_iris():
    """Fast IRIS container with pre-configured password."""
    with IRISContainer.community().with_preconfigured_password("SYS") as iris:
        yield iris

def test_example(fast_iris):
    conn = fast_iris.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

## CI/CD Configuration Examples

### GitHub Actions

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      IRIS_PASSWORD: SYS
      IRIS_USERNAME: _SYSTEM
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest tests/
```

### GitLab CI

```yaml
test:
  variables:
    IRIS_PASSWORD: SYS
    IRIS_USERNAME: _SYSTEM
  script:
    - pytest tests/
```

### Azure DevOps

```yaml
steps:
  - script: pytest tests/
    env:
      IRIS_PASSWORD: SYS
      IRIS_USERNAME: _SYSTEM
```

The password pre-configuration activates automatically when these environment variables are set, saving 5-10 seconds per container startup in your CI pipeline.
