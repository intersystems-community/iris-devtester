# Docker Hub Image Naming for InterSystems IRIS

**Date Discovered**: 2025-01-13
**Feature**: 010-fix-critical-bugs
**Impact**: Critical - Container creation failures

## The Problem

Community edition containers were failing to start with "image not found" errors, despite using what appeared to be the correct image name: `intersystems/iris-community`.

## Why Not Use `intersystems/iris-community`?

**What we tried**: Using `intersystems/iris-community` as the Docker image name for Community edition.

**Why it didn't work**:
- The image doesn't exist on Docker Hub under that name
- Community edition images use the `intersystemsdc/` organization prefix (Docker Community)
- Only Enterprise edition images use the `intersystems/` organization prefix
- This is a Docker Hub organizational structure decision by InterSystems

**What we use instead**: `intersystemsdc/iris-community`

**Evidence**:
- Container creation failures dropped to 0 after the fix
- Docker Hub repositories confirm the naming:
  - Community: https://hub.docker.com/r/intersystemsdc/iris-community
  - Enterprise: https://hub.docker.com/r/intersystems/iris

## Docker Hub Naming Conventions

InterSystems IRIS uses two separate Docker Hub organizations:

### Community Edition
- **Organization**: `intersystemsdc` (Docker Community)
- **Repository**: `iris-community`
- **Full image name**: `intersystemsdc/iris-community:{tag}`
- **Example tags**: `latest`, `2024.1`, `2024.1.0`

### Enterprise Edition
- **Organization**: `intersystems`
- **Repository**: `iris`
- **Full image name**: `intersystems/iris:{tag}`
- **Example tags**: `latest`, `2024.1`, `2024.1.0`

## Key Differences

| Aspect | Community Edition | Enterprise Edition |
|--------|------------------|-------------------|
| Organization | `intersystemsdc` | `intersystems` |
| Repository | `iris-community` | `iris` |
| Full Image | `intersystemsdc/iris-community:latest` | `intersystems/iris:latest` |
| License Required | No | Yes |

## Implementation Fix

**Location**: `iris_devtester/config/container_config.py:266`

**Before** (incorrect):
```python
def get_image_name(self) -> str:
    if self.edition == "community":
        return f"intersystems/iris-community:{self.image_tag}"  # WRONG
    else:
        return f"intersystems/iris:{self.image_tag}"
```

**After** (correct):
```python
def get_image_name(self) -> str:
    if self.edition == "community":
        # Bug Fix #1: Community images use 'intersystemsdc/' prefix on Docker Hub
        return f"intersystemsdc/iris-community:{self.image_tag}"  # CORRECT
    else:
        return f"intersystems/iris:{self.image_tag}"
```

## Testing

The fix was validated with unit tests in `tests/unit/config/test_container_config.py`:

```python
def test_get_image_name_community_latest(self):
    """Test image name for community edition with latest tag."""
    config = ContainerConfig(edition="community", image_tag="latest")
    assert config.get_image_name() == "intersystemsdc/iris-community:latest"

def test_get_image_name_community_specific_tag(self):
    """Test image name for community edition with specific tag."""
    config = ContainerConfig(edition="community", image_tag="2024.1")
    assert config.get_image_name() == "intersystemsdc/iris-community:2024.1"
```

## Lessons Learned

1. **Always verify Docker Hub naming**: Don't assume image names follow a consistent pattern across organizations
2. **Test with real container pulls**: The bug was only caught when containers failed to start
3. **Document organizational conventions**: InterSystems uses different Docker Hub orgs for different editions
4. **Check Docker Hub directly**: When in doubt, search Docker Hub to confirm image availability

## Related Resources

- Docker Hub Community Repository: https://hub.docker.com/r/intersystemsdc/iris-community
- Docker Hub Enterprise Repository: https://hub.docker.com/r/intersystems/iris
- Feature 010 Specification: `/specs/010-fix-critical-bugs/spec.md`
- Constitutional Principle #8: "Document the Blind Alleys" (CONSTITUTION.md:342-356)

## Decision Record

**Decision**: Use `intersystemsdc/iris-community` for Community edition images
**Rationale**: This is the actual Docker Hub organization and repository name used by InterSystems
**Alternatives Considered**: None - this is the only valid option
**Date**: 2025-01-13
**Status**: Implemented in Feature 010
