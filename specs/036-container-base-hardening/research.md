# Research: Container Base Hardening

No NEEDS CLARIFICATION remain. One assumption is gated by a probe (see below).

## Value transfer (T9)

- **Decision**: constant command, values in `exec_run(environment=...)`, read inside IRIS with the environment-variable lookup; identifiers (namespace, username) also validated by pattern.
- **Rationale**: docker-py applies `shlex.split` to string commands, so a quote breaks tokenising (opaque `ValueError` after the container is running); the ObjectScript string layer is the real injection surface. Passing values by environment removes both layers; the namespace still lands in a SQL identifier, which cannot be bound, so it needs the pattern.
- **Alternatives**: escape both layers (hand-rolled, easy to get wrong); validate everything including passwords (regresses special-character passwords); stdin pipe (socket handling, same escaping weakness).
- **Fallback if the probe fails**: pipe a script on stdin with values delivered as separate lines read with `Read`, still with no interpolation.
- **Unverified (resolved by probe, 2026-10-02)**: the lookup's availability on the target images. `$system.Util.GetEnviron("IDT_PW")` returned `a"b'c$(x)` byte for byte on `intersystemsdc/iris-community:latest-em` and `intersystemsdc/irishealth-community:latest` (arm64), through `exec_run(["sh", "-c", script], environment=...)`. Fallback not needed.
- **Probe finding that shapes the command**: `iris session iris -U NS '<expr>'` treats its argument as a routine reference (`<NOROUTINE>` for anything but `##class(...).Method(...)`), always exits 0 even on `<CLASS DOES NOT EXIST>`, and swallows a returned `%Status`. The exit status alone therefore cannot detect failure. The fixed command is `["sh", "-c", <constant heredoc script>]` that pipes a constant ObjectScript script to `iris session iris -U %SYS` on stdin; the script reads values with `GetEnviron`, writes an `IDT_OK` / `IDT_ERR:<text>` marker, and the shell exits non-zero unless the `IDT_OK` marker was printed. Still a constant command with values only in the environment.

## Coverage baseline (T003)

`pytest tests/unit -m "not integration and not e2e" --cov=iris_devtester`: **91.75%** total (1459 passed). One pre-existing timing-flaky test (`test_wait_strategies.py::TestWaitForIRISReady::test_wait_function_with_timeout`) failed in the full run and passes alone.

## Validation rules (T9)

- Namespace: `[A-Za-z][A-Za-z0-9_]{0,63}` (fullmatch), checked when not `USER`.
- Username: `[A-Za-z0-9_][A-Za-z0-9_.@-]{0,127}` (fullmatch), checked only when a password is also supplied.
- Password: non-empty, no NUL.
- Conservative on purpose; widen on demand.

## Exit-status checks (T9)

Both commands' results were only logged; now a non-zero exit raises a structured error naming the step.

## Licence check (T10)

- **Decision**: catch `docker.errors.DockerException` and `testcontainers` container-start exceptions only; log a warning; return False; the timeout path message notes unreadable logs.
- **Rationale**: `AttributeError`/`TypeError` from a bug must not be hidden; the swallow produced a silent wrong answer.
- **Alternatives**: keep (hides failure); narrow with debug log (invisible); tri-state return (changes helper contract).

## Dead code (T10, R2)

- Safe step: `self.image`, `driver`, stub base, `_ActualBase` plus try/except, `IRISBase`; two test patches re-point to `IRISDockerContainer.start`.
- Second step: `HAS_TESTCONTAINERS` (22 patch sites, one assertion, one constructor warning, one `attach()` branch).
- No sibling repository uses any of these names (411 importing files checked in R2).

## Contract test (T10)

`tests/contract/test_preconfig_contract.py` patches a nonexistent attribute. Compare with `test_password_preconfig.py`; rewrite unique contract content, delete the rest.

## Labels (T4)

Same keys as feature 035. The adapter's Docker SDK path passes `labels=`; the testcontainers path, if used by `container up`, uses `with_kwargs(labels=...)`. The image label is omitted when the ref is unknown.

## Contract test comparison (T022)

`tests/contract/test_preconfig_contract.py` patched `HAS_TESTCONTAINERS_IRIS` (never existed) and called `_should_preconfigure()` / `_apply_password_preconfig()` (no longer in the source), so all 11 tests failed before this feature. Line-by-line comparison with `tests/unit/test_password_preconfig.py`:

- Duplicated by the unit file (deleted): `with_preconfigured_password` returns self and stores the value, `with_credentials` returns self and stores both values, empty password and empty username rejected.
- Unique and still meaningful (rewritten as real contract tests, no patching of nonexistent names): the API password wins over a process-level `IRIS_PASSWORD` when `start()` configures the container; `start()` sets no credentials and does not reset the password when the API is unused.
- Dropped as untestable: `_should_preconfigure()` and `_apply_password_preconfig()` no longer exist.

## IRISContainer own arguments (FR-008)

`IRISContainer` does not forward `namespace`, `username` or `password` to the base, because the base would then create a database and a `%ALL` user for them (its defaults `_SYSTEM`/`SYS` would even fail as a duplicate user). It calls the base validators on its own arguments instead, before `super().__init__`: namespace unless `USER`, username when a password is also given, and a NUL check on the password. An empty password is still accepted here (previous behaviour). Environment variables are validated by the base as before.
