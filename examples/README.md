# IRIS DevTools Examples

This directory contains practical examples demonstrating common use cases for iris-devtester.

## Learning Path

**New to iris-devtester?** Follow this recommended order:

1. **Start Here**: `01_quickstart.py` - Basic container usage (~2 min)
2. **Connections**: `02_connection_management.py` - DBAPI vs JDBC (~5 min)
3. **Testing Basics**: `04_pytest_fixtures.py` - Simple pytest integration (~5 min)
4. **Isolation**: `05_test_isolation.py` - Schema reset patterns (~5 min)
5. **Auto-Discovery**: `08_auto_discovery.py` - Connect to existing IRIS (~5 min)
6. **Production**: `09_production_patterns.py` - Real-world patterns (~10 min)
7. **Advanced**: `06_dat_fixtures.py` - Fast fixture loading (~10 min)

**Total time**: ~45 minutes to understand all capabilities

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
# Install iris-devtester with all features
pip install iris-devtester[all]

# Run an example
python examples/01_quickstart.py
```

### Prerequisites

Before running examples, ensure you have:

- ✅ **Python 3.9+** installed (`python --version`)
- ✅ **Docker running** (`docker ps` should work)
- ✅ **iris-devtester installed** (`pip install iris-devtester[all]`)

### Expected Outputs

Each example includes comments showing expected output. Look for:
- `# Expected output: ...` - What you should see
- `# ✅ Success:` - Successful operation
- `# ⚠️ Note:` - Important information

If your output differs significantly, check the [Troubleshooting Guide](https://github.com/intersystems-community/iris-devtester/blob/main/docs/TROUBLESHOOTING.md).

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
1. Check [Troubleshooting Guide](https://github.com/intersystems-community/iris-devtester/blob/main/docs/TROUBLESHOOTING.md)
2. Review [Codified Learnings](https://github.com/intersystems-community/iris-devtester/blob/main/docs/learnings/)
3. Open an [issue](https://github.com/intersystems-community/iris-devtester/issues)
