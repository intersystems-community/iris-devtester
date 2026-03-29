# cli/ — Click Command Interface

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Click-based CLI exposing all library functionality. Entry points: `iris-devtester` and `idt` (alias). 7 files, ~2500 lines.

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `__init__.py` | 60 | `main()` Click group; registers all subcommands |
| `container.py` | ~1350 | `container` subgroup: up, stop, status, list, logs, reset-password, enable-callin, exec |
| `container_commands.py` | — | Container command implementations |
| `fixture_commands.py` | — | `fixture` subgroup: load, create, validate, list |
| `connection_commands.py` | ~340 | `test-connection` command (password detection, --auto-fix, credential display) |
| `dev_commands.py` | — | `dev` subgroup: up, down (persistent dev instance) |

## COMMAND TREE

```
idt (iris-devtester)
  container
    up [--edition community|light|enterprise] [--license PATH] [--port PORT] [--auto-port]
    stop [--remove]
    status
    list [--format json]
    logs
    reset-password [--user _SYSTEM] [--password SYS] [--timeout 30]
    enable-callin [--timeout 30]
    exec [--objectscript CODE] [--namespace USER] [--timeout 30] [-- COMMAND...]
    test-connection  ⚠ DEPRECATED → use top-level test-connection
  fixture
    load --name NAME
    create --name NAME
    validate --name NAME
    list
  dev
    up
    down
  test-connection [--container NAME] [--auto-fix] [-v]
```

## NEW IN 030

- **`test-connection --auto-fix`**: Detects password-change-required errors (the cryptic "Unexpected error: 1") and auto-remediates by calling `reset_password()` then retrying.
- **`test-connection` shows credentials**: Displays masked password by default (`S***`), full in verbose mode.
- **`container reset-password --timeout`**: Exposed existing `timeout` parameter to CLI (default 30s).
- **`container up --port`**: Exact host-port mapping. Mutually exclusive with `--auto-port`.
- **`container exec`**: Run ObjectScript or shell commands inside container. Uses `docker exec` under the hood.
- **`container test-connection` DEPRECATED**: Prints warning directing to `idt test-connection --container`.

## PATTERNS

- **Structured exit codes**: 0=success, 1=error, 2=not found, 5=timeout
- **JSON output**: `--format json` for machine-readable output
- **All commands support `--help`** with detailed option descriptions
- **Library-first**: CLI delegates to library code; never contains business logic directly
- **`--port` vs `--auto-port`**: Mutually exclusive. `--port` sets exact mapping; `--auto-port` assigns from registry range.
