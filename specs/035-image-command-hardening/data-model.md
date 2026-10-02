# Data Model: Image Command Hardening

## ImageCommandError

| Field     | Type | Rule                                  |
| --------- | ---- | ------------------------------------- |
| what      | str  | one line, states what failed          |
| why       | str  | why it matters                        |
| fix       | str  | at least one concrete command or flag |
| exit_code | int  | one of 1, 2, 5                        |

Rendered once by the command wrapper. `TimeoutExpired` and `TimeoutError` are converted to exit 5 and never to the catch-all.

## StartOptions (frozen dataclass)

| Field                      | Notes                                         |
| -------------------------- | --------------------------------------------- |
| name                       | container name                                |
| superserver_port, web_port | published ports                               |
| password, show_password    | summary shows `********` unless show_password |
| no_unexpire                | skip unexpire step                            |
| health_timeout             | from `--timeout`, default 120                 |
| run_timeout                | named constant, 60                            |
| labels                     | the two idt labels                            |
| license_mount              | resolved key path or None                     |
| replace                    | `--replace` flag                              |
| cap_ipc_lock               | existing behaviour                            |

## LicenseResolution

`path: Path | None`, `source: "option" | "env" | "cwd" | None`. Explicit source with missing file raises `ImageCommandError` (exit 2).

## IrisMainResolution

`path: Path`, `source: str` (option, env, container name, image ref, auto-detected container), `arch: "arm64" | "amd64"`, `cleanup: callable | None`.

## CollisionDecision

Function of `(labels, status, replace)`:

| Labelled    | Status                              | replace | Outcome                                               |
| ----------- | ----------------------------------- | ------- | ----------------------------------------------------- |
| yes         | created, dead                       | any     | announce and remove                                   |
| yes         | running, exited, paused, restarting | no      | refuse, exit 2                                        |
| yes         | running, exited, paused, restarting | yes     | announce (name, status, image), remove container only |
| no          | any                                 | any     | refuse, exit 2, no `--replace` hint                   |
| none exists | n/a                                 | any     | proceed                                               |

## Constants

`BUILD_TIMEOUT=900`, `LOAD_TIMEOUT=300`, `HEALTH_TIMEOUT=120`, `RUN_TIMEOUT=60`, `KILL_GRACE=3`, label keys, exit codes 0/1/2/5.
