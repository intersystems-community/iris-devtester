# Data Model: Fix Critical Container Creation Bugs

**Feature**: 010-fix-critical-bugs
**Date**: 2025-01-13

## Overview

This bug fix feature involves minimal data model changes. The primary entity `ContainerConfig` already has all necessary fields - we're fixing the logic in methods and adding missing functionality.

## Modified Entities

### ContainerConfig

**Location**: `iris_devtester/config/container_config.py`

**Purpose**: Represents user's desired IRIS container configuration

**Existing Fields** (no changes):
```python
edition: Literal["community", "enterprise"]  # Edition type
container_name: str                           # Container identifier
superserver_port: int                         # SuperServer port (1972 default)
webserver_port: int                           # Management Portal port (52773 default)
namespace: str                                # Default IRIS namespace
password: str                                 # _SYSTEM user password
license_key: Optional[str]                    # Enterprise license (optional)
volumes: List[str]                            # Volume mount strings (CURRENTLY IGNORED - BUG!)
image_tag: str                                # Docker image tag (latest default)
```

**Modified Method**: `get_image_name() -> str`

Current (BUGGY) Implementation:
```python
def get_image_name(self) -> str:
    if self.edition == "community":
        return f"intersystems/iris-community:{self.image_tag}"  # WRONG IMAGE NAME!
    else:
        return f"intersystems/iris:{self.image_tag}"
```

Fixed Implementation:
```python
def get_image_name(self) -> str:
    if self.edition == "community":
        return f"intersystemsdc/iris-community:{self.image_tag}"  # CORRECT!
    else:
        return f"intersystems/iris:{self.image_tag}"
```

**Change Summary**:
- Line 266: Change `intersystems/iris-community` → `intersystemsdc/iris-community`
- No schema changes
- No field additions
- No validation rule changes

### Volume Mount Representation

**Format**: String in Docker volume syntax
```
{host_path}:{container_path}[:{mode}]
```

**Examples**:
```python
volumes = [
    "./data:/external",              # Read-write mount
    "./config:/opt/config:ro",       # Read-only mount
    "/abs/path:/container/path:rw"   # Explicit read-write
]
```

**Parsing Logic** (to be added in `IRISContainerManager`):
```python
def parse_volume_string(volume: str) -> tuple[str, str, str]:
    """
    Parse Docker volume syntax into components.

    Args:
        volume: Volume string in format "host:container" or "host:container:mode"

    Returns:
        Tuple of (host_path, container_path, mode)

    Examples:
        >>> parse_volume_string("./data:/external")
        ('./data', '/external', 'rw')

        >>> parse_volume_string("./config:/opt/config:ro")
        ('./config', '/opt/config', 'ro')
    """
    parts = volume.split(":")
    host_path = parts[0]
    container_path = parts[1]
    mode = parts[2] if len(parts) > 2 else "rw"
    return (host_path, container_path, mode)
```

## New Entities

None - all bug fixes work with existing data structures

## State Transitions

No state machine changes - container lifecycle unchanged

## Validation Rules

**Existing Validation** (unchanged):
- `container_name`: Must match `^[a-zA-Z0-9][a-zA-Z0-9_.-]*$`
- `superserver_port`: Must be 1024-65535
- `webserver_port`: Must be 1024-65535
- `namespace`: Must match `^[A-Z][A-Z0-9%]*$`
- `password`: Min length 1
- `image_tag`: No validation (any string accepted)

**New Validation** (Bug Fix 3):
- Volume paths will be validated at container creation time
- Invalid paths will raise ValueError with constitutional error message
- Validation includes:
  - Host path must exist or be creatable
  - Container path must be absolute
  - Mode must be 'rw' or 'ro'

## Database Schema Changes

N/A - No database involved (container configuration only)

## Serialization Format

**YAML Format** (unchanged):
```yaml
edition: community
container_name: iris_db
superserver_port: 1972
webserver_port: 52773
namespace: USER
password: SYS
image_tag: latest
volumes:
  - ./data:/external
  - ./config:/opt/config:ro
```

**JSON Format** (unchanged):
```json
{
  "edition": "community",
  "container_name": "iris_db",
  "superserver_port": 1972,
  "webserver_port": 52773,
  "namespace": "USER",
  "password": "SYS",
  "image_tag": "latest",
  "volumes": [
    "./data:/external",
    "./config:/opt/config:ro"
  ]
}
```

## Relationships

```
ContainerConfig
  ├─ edition ────────────► Docker Image Name (via get_image_name())
  │                        ├─ community → intersystemsdc/iris-community:{tag}
  │                        └─ enterprise → intersystems/iris:{tag}
  │
  ├─ volumes ────────────► Volume Mounts (parsed at container creation)
  │                        └─ Each string → (host_path, container_path, mode)
  │
  └─ ports ──────────────► Docker Port Bindings
                          ├─ superserver_port → 1972/tcp
                          └─ webserver_port → 52773/tcp
```

## Migration Notes

No migration required:
- Image name change is transparent (users specify edition, not image name)
- Volume mounting is additive (existing configs without volumes continue to work)
- No schema version bump needed

## Examples

### Before (Broken):
```python
config = ContainerConfig(edition="community", image_tag="2024.1")
image = config.get_image_name()
# Returns: "intersystems/iris-community:2024.1"  ← DOESN'T EXIST ON DOCKER HUB!
```

### After (Fixed):
```python
config = ContainerConfig(edition="community", image_tag="2024.1")
image = config.get_image_name()
# Returns: "intersystemsdc/iris-community:2024.1"  ← CORRECT!
```

### Volume Mounting (New Functionality):
```python
config = ContainerConfig(
    volumes=["./data:/external", "./config:/opt/config:ro"]
)
iris = IRISContainerManager.create_from_config(config)
# Volumes now actually get mounted (was previously ignored)
```

---

**Data Model Status**: ✅ Complete - Minimal changes, no breaking modifications
