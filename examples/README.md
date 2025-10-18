# IRIS DevTools Examples

This directory contains practical examples demonstrating common use cases for iris-devtools.

## Examples Overview

### Basic Usage
- [`01_quickstart.py`](01_quickstart.py) - Zero-config container startup
- [`02_connection_management.py`](02_connection_management.py) - Connection patterns
- [`03_namespace_operations.py`](03_namespace_operations.py) - Namespace management

### Testing
- [`04_pytest_fixtures.py`](04_pytest_fixtures.py) - pytest integration
- [`05_test_isolation.py`](05_test_isolation.py) - Schema reset and isolation
- [`06_dat_fixtures.py`](06_dat_fixtures.py) - .DAT fixture management

### Advanced
- [`07_monitoring_setup.py`](07_monitoring_setup.py) - Performance monitoring
- [`08_auto_discovery.py`](08_auto_discovery.py) - Existing IRIS detection
- [`09_production_patterns.py`](09_production_patterns.py) - Battle-tested patterns

## Running Examples

Each example is standalone and can be run directly:

```bash
# Install iris-devtools with all features
pip install iris-devtools[all]

# Run an example
python examples/01_quickstart.py
```

## Requirements

- Python 3.9+
- Docker (for testcontainers)
- iris-devtools installed

## Constitutional Principles in Action

All examples follow the [8 core principles](../CONSTITUTION.md):

1. **Automatic Remediation** - No manual intervention needed
2. **DBAPI First** - Fast connections by default
3. **Isolation by Default** - Each test gets own namespace
4. **Zero Configuration** - Works out of the box
5. **Fail Fast with Guidance** - Clear error messages
6. **Enterprise Ready** - Both editions supported
7. **Medical-Grade Reliability** - Error handling throughout
8. **Document Blind Alleys** - Learn from our mistakes

## Help

If you run into issues:
1. Check [docs/troubleshooting.md](../docs/troubleshooting.md)
2. Review [docs/SQL_VS_OBJECTSCRIPT.md](../docs/SQL_VS_OBJECTSCRIPT.md)
3. Open an [issue](https://github.com/intersystems-community/iris-devtools/issues)
