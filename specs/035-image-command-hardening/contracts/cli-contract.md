# CLI Contract: `idt image`

## `idt image load TARBALL`

| Option                                                                        | Default   | Meaning                                           |
| ----------------------------------------------------------------------------- | --------- | ------------------------------------------------- |
| `--load-timeout`                                                              | 300       | import phase only                                 |
| `--timeout`                                                                   | 120       | IRIS health wait only                             |
| `--replace`                                                                   | off       | replace an idt-created container of the same name |
| `--show-password`                                                             | off       | print the real password in the summary            |
| `--password`, `--name`, `--port`, `--web-port`, `--no-start`, `--no-unexpire` | unchanged | unchanged                                         |

## `idt image build TARBALL`

| Option                         | Default | Meaning                                        |
| ------------------------------ | ------- | ---------------------------------------------- |
| `--build-timeout`              | 900     | build phase only                               |
| `--timeout`                    | 120     | IRIS health wait only (was total, default 900) |
| `--license PATH`               | none    | license key, must exist                        |
| `--iris-main PATH`             | none    | iris-main file                                 |
| `--iris-main-container NAME`   | none    | copy from container                            |
| `--iris-main-image REF`        | none    | extract from image                             |
| `--replace`, `--show-password` | off     | as for `load`                                  |
| `--platform`                   | host    | checked against the iris-main ELF              |
| `--keep-build-dir`             | off     | keep build directory                           |

## Environment

`IRIS_LICENSE_KEY` (path), `IDT_IRIS_MAIN` (path).

## Exit codes

| Code | Meaning                                                                                                                                |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | success (also default-password reset warning)                                                                                          |
| 1    | Docker or runtime failure, non-default password reset failure, catch-all                                                               |
| 2    | bad input or precondition: installer kit given to `load`, bad explicit path, name collision, no valid iris-main, architecture mismatch |
| 5    | any timeout                                                                                                                            |

## Labels on created containers

`io.iris-devtester.created-by=idt`, `io.iris-devtester.image=<ref>`.
