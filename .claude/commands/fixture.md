# description: Create, load, and validate test fixtures

# Fixture Skill

## Prerequisites
- IRIS container is running
- `iris-devtester` package is installed

## CLI Commands

### Load Fixture
Loads a .DAT fixture into the container.
```bash
iris-devtester fixture load --name my-test-data
```

### Create Fixture (Export)
Exports the current state of the namespace to a .DAT fixture.
```bash
iris-devtester fixture create --name new-baseline
```

### Validate Fixture
Checks the fixture manifest and DAT file integrity.
```bash
iris-devtester fixture validate --name my-test-data
```

### List Fixtures
```bash
iris-devtester fixture list
```

## Python API

### Using Pytest Fixture
The library provides a pytest fixture `dat_fixture` (if configured in `conftest.py`).

```python
import pytest

@pytest.mark.dat_fixture(name="users_data")
def test_users_exist(iris_connection):
    cursor = iris_connection.cursor()
    cursor.execute("SELECT Count(*) FROM App.Users")
    assert cursor.fetchone()[0] > 0
```

### Manual Loading
```python
from iris_devtester.fixtures import FixtureLoader

loader = FixtureLoader(container)
loader.load_fixture("users_data")
```

## Troubleshooting

### Durable Data Conflict
**Symptom**: "Global already exists" or duplicate key errors during load.
**Cause**: The fixture is being loaded into a namespace that already has data.
**Fix**: Ensure you are loading into a clean state or use `--reset` (if implemented/supported) or restart container.
