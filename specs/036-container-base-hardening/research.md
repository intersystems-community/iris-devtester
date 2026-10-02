# Research: Container Base Hardening

No NEEDS CLARIFICATION remain. One assumption is gated by a probe (see below).

## Value transfer (T9)

- **Decision**: constant command, values in `exec_run(environment=...)`, read inside IRIS with the environment-variable lookup; identifiers (namespace, username) also validated by pattern.
- **Rationale**: docker-py applies `shlex.split` to string commands, so a quote breaks tokenising (opaque `ValueError` after the container is running); the ObjectScript string layer is the real injection surface. Passing values by environment removes both layers; the namespace still lands in a SQL identifier, which cannot be bound, so it needs the pattern.
- **Alternatives**: escape both layers (hand-rolled, easy to get wrong); validate everything including passwords (regresses special-character passwords); stdin pipe (socket handling, same escaping weakness).
- **Fallback if the probe fails**: pipe a script on stdin with values delivered as separate lines read with `Read`, still with no interpolation.
- **Unverified**: the lookup's availability on all target images. T0 probe decides.

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
