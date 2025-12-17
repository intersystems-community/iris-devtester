# DAT Fixture Management

Fast, reproducible test fixtures by exporting IRIS tables to .DAT files with checksum validation.

## Overview

DAT Fixture Management provides **10-100x faster** test data loading compared to programmatic data creation:
- Load 10K rows in <10 seconds (vs ~50 minutes programmatically)
- SHA256 checksum validation for data integrity
- Atomic loading with transaction rollback
- Version-controlled fixtures for team sharing

## Quick Start

### Python API

```python
from iris_devtester.fixtures import FixtureCreator, DATFixtureLoader

# Create fixture from existing data
creator = FixtureCreator()
manifest = creator.create_fixture(
    fixture_id="test-users-100",
    namespace="USER",
    output_dir="./fixtures/test-users-100"
)

# Load fixture in tests (10K rows in <10 seconds)
loader = DATFixtureLoader()
result = loader.load_fixture("./fixtures/test-users-100")
print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")
```

### CLI Commands

```bash
# Create fixture from namespace
iris-devtester fixture create --name test-100 --namespace USER --output ./fixtures/test-100

# Validate fixture integrity (SHA256 checksums)
iris-devtester fixture validate --fixture ./fixtures/test-100

# Load fixture into IRIS
iris-devtester fixture load --fixture ./fixtures/test-100

# List available fixtures
iris-devtester fixture list ./fixtures/

# Show fixture info
iris-devtester fixture info --fixture ./fixtures/test-100
```

## pytest Integration

```python
import pytest
from iris_devtester.fixtures import DATFixtureLoader

@pytest.fixture
def loaded_fixture(iris_container):
    """Load DAT fixture for tests."""
    loader = DATFixtureLoader(container=iris_container)
    target_ns = iris_container.get_test_namespace(prefix="TEST")

    result = loader.load_fixture(
        fixture_path="./fixtures/test-100",
        target_namespace=target_ns
    )

    yield result

    # Cleanup
    loader.cleanup_fixture(target_ns, delete_namespace=True)

def test_entity_count(loaded_fixture):
    """Test using loaded DAT fixture."""
    assert loaded_fixture.success
    assert len(loaded_fixture.tables_loaded) > 0
```

## Best Practices

1. **Version control fixtures**: Store .DAT files in git for reproducibility
2. **Use checksums**: Always validate before loading to catch corruption
3. **Namespace isolation**: Load into test-specific namespaces
4. **Atomic operations**: Use transaction rollback on failures
5. **Clean up**: Delete test namespaces after test completion

## Fixture Structure

```
fixtures/test-100/
├── manifest.json        # Metadata and checksums
├── tables/
│   ├── MyApp.Users.dat  # Exported table data
│   └── MyApp.Orders.dat
└── globals/             # Optional global exports
```

## Troubleshooting

### Fixture load fails with checksum mismatch
- Re-export the fixture: `iris-devtester fixture create ...`
- Verify no corruption during transfer

### Load timeout
- Increase timeout: `--timeout 300`
- Check IRIS container health
- Verify namespace exists

### Permission denied
- Ensure IRIS user has CREATE TABLE permissions
- Check namespace security settings

## See Also

- [Testcontainers Integration](testcontainers.md) - Container setup for fixtures
- [examples/](../../examples/) - Runnable examples
