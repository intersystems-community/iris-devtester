# Data Model: CPF Merge Support

**Feature Branch**: `022-add-cpf-merge-support` | **Date**: 2026-01-05

## Entities

### `IRISContainer` (Core)
Existing entity, enhanced with configuration management.

| Method | Arguments | Description |
|-------|-----------|-------------|
| `with_cpf_merge` | `path_or_content: str` | Sets the CPF merge file for the container. |

### `CPFMergeRequest` (Internal)
Encapsulates the state of a pending CPF merge.

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Original input (path or raw content). |
| `is_path` | `bool` | True if source is an existing file path. |
| `temp_path` | `str \| None` | Host path to the generated temp file if applicable. |

### `CPFPreset` (Registry)
Static collection of optimized snippets.

| Constant | Value | Description |
|----------|-------|-------------|
| `ENABLE_CALLIN` | `[Security.Services]...` | Enables %Service_CallIn for DBAPI. |
| `CI_OPTIMIZED` | `[config]...` | Sets 512MB memory profile. |

## Relationships

- `IRISContainer` **OWN-A** `TempCPFManager`
- `TempCPFManager` **TRACKS** `CPFMergeRequest`
- `IRISContainer` **USES** `CPFPreset`
