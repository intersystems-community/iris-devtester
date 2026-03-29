# cli/ — Click Command Interface

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Click-based CLI exposing all library functionality. Entry points: `iris-devtester` and `idt` (alias). 7 files, 2257 lines.

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `__init__.py` | 60 | `main()` Click group; registers all subcommands |
| `container.py` | 1174 | `container` subgroup: up, stop, status, list, logs, reset-password, enable-callin |
| `container_commands.py` | — | Container command implementations |
| `fixture_commands.py` | — | `fixture` subgroup: load, create, validate, list |
| `connection_commands.py` | — | `test-connection` command |
| `dev_commands.py` | — | `dev` subgroup: up, down (persistent dev instance) |

## COMMAND TREE

```
idt (iris-devtester)
  container
    up [--edition community|light|enterprise] [--license PATH]
    stop [--remove]
    status
    list [--format json]
    logs
    reset-password [--user _SYSTEM] [--password SYS]
    enable-callin
  fixture
    load --name NAME
    create --name NAME
    validate --name NAME
    list
  dev
    up
    down
  test-connection
```

## PATTERNS

- **Structured exit codes**: 0=success, 1=error, 2=not found, 5=timeout
- **JSON output**: `--format json` for machine-readable output
- **All commands support `--help`** with detailed option descriptions
- **Library-first**: CLI delegates to library code; never contains business logic directly
