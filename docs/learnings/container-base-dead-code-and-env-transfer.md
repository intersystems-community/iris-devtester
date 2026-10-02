# Container base: dead code removed, values travel by environment

Feature 036. Why `IRISDockerContainer` changed and what was left for later.

## Why the fallback base and `HAS_TESTCONTAINERS` were dropped

`containers/iris_container.py` carried a stub base class (`_IRISMockContainer`),
a try/except import, two aliases (`IRISBase`, `_ActualBase`) and a
`HAS_TESTCONTAINERS` flag that selected a manual host/port branch in `attach()`.
`testcontainers` is a hard dependency, so the fallback could never be reached in
a working install. It only cost tests: about 34 test references patched the flag
to `False` to exercise a path that no user can take. The removal happened in two
steps so each could be reviewed and coverage-checked on its own: first the names
with no test impact, then the flag.

A contract test (`tests/contract/test_preconfig_contract.py`) patched
`HAS_TESTCONTAINERS_IRIS`, a name that never existed, and called two methods
that no longer exist, so all 11 of its tests failed. Its unique assertions were
rewritten as real tests; the rest duplicated the unit tests and were deleted.

## Why values travel by environment and are not escaped

The old start-up steps built one string with `%`-formatting and sent it to
`iris session`. Two layers interpreted that string:

1. docker-py splits a string command with `shlex.split`, so a quote in the
   password failed to tokenise. The error was an opaque `ValueError` after the
   container was already running.
2. The ObjectScript string literal. A `"` in a password ended the literal early.

Escaping for both layers by hand is easy to get wrong. Passing the values in
`exec_run(environment=...)` and reading them inside IRIS with
`$system.Util.GetEnviron(...)` removes both layers: the command never contains a
value. A password is accepted if it is non-empty and has no NUL.

A namespace still ends up as a SQL identifier in `CREATE DATABASE`, and an
identifier cannot be bound as a parameter. So namespaces and usernames are also
checked against a pattern, in the constructor, before `docker run`. The rule is
conservative on purpose (letter first, letters, digits and underscore for a
namespace); widen it when someone needs more.

### Probe result (T002)

Checked on `intersystemsdc/iris-community:latest-em` and
`intersystemsdc/irishealth-community:latest` (arm64, OrbStack): a password of
`a"b'c$(x)` came back byte for byte. See
`tests/integration/test_base_quoted_password.py`. A user created with such a
password also logs in over DBAPI.

### Blind alley: `iris session iris -U NS '<expression>'`

The old form passes the expression as an argument. IRIS treats that argument as
a routine reference: anything except `##class(...).Method(...)` fails with
`<NOROUTINE>`, nested calls fail with `<INVALID ARGUMENT>`, a returned `%Status`
is discarded, and the process **always exits 0**, even for
`<CLASS DOES NOT EXIST>`. The exit status cannot report failure in that form, so
"check the exit status" alone would not have worked.

The fixed command is now `sh -c` with a constant heredoc piped to
`iris session iris -U %SYS`. The script reads the environment, prints `IDT_OK`
or `IDT_ERR:<text>`, and the shell exits non-zero unless `IDT_OK` was printed.
Still no value in the command text.

## Follow-up

`utils/password.py` and `utils/namespace.py` build ObjectScript and SQL text
from values the same way the old base did (string interpolation into
`iris session` commands). They were out of scope here. They should move to the
same pattern: fixed script, values in the exec environment, result marker
instead of the exit code.
