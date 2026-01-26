# Quickstart: CPF Merge Support

**Feature Branch**: `022-add-cpf-merge-support` | **Date**: 2026-01-05

## Basic Usage

Enable the CallIn service automatically on container startup using a raw string snippet.

```python
from iris_devtester.containers import IRISContainer

with IRISContainer.community().with_cpf_merge("""
[Security.Services]
%Service_CallIn=1,1,1,1,1,1,1,1,1,1,1,1,1,1
""") as iris:
    conn = iris.get_connection()
    # DBAPI works immediately without remediation
```

## Using Presets

Use built-in presets for common InterSystems IRIS optimizations.

```python
from iris_devtester.containers import IRISContainer
from iris_devtester.config import CPFPreset

# Combine multiple presets or raw content
config = CPFPreset.CI_OPTIMIZED + "\n" + CPFPreset.ENABLE_CALLIN

with IRISContainer.community().with_cpf_merge(config) as iris:
    conn = iris.get_connection()
    # Optimized for CI memory limits and DBAPI
```

## Advanced: Path-based Config

Pass an absolute path to an existing `.cpf` file.

```python
with IRISContainer.community().with_cpf_merge("/path/to/my/custom.cpf") as iris:
    # Uses your pre-defined config file
    pass
```
