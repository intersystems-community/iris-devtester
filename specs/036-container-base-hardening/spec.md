# Feature Specification: Container Base Hardening

**Feature Branch**: `036-container-base-hardening`
**Created**: 2026-10-02
**Status**: Draft
**Input**: User description: "Harden the IRIS Docker container base class (`containers/_base.py` and `IRISContainer`): safe user and namespace creation, dead-code removal, licence-check exception policy, idt labels on `container up` containers, and the remaining documentation gaps. Decisions are recorded in `.scratch/wayfinder/` tickets T4 (labelling part), T9 and T10, and R2."

Companion feature: `035-image-command-hardening` (the `idt image` commands). Labels, the error style and the installer-kit learnings note are defined there; this feature does not repeat them.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Any password or namespace is handled safely (Priority: P1)

A developer or CI job supplies a username, password and namespace, through arguments or the `IRIS_USERNAME`, `IRIS_PASSWORD` and `IRIS_NAMESPACE` environment variables. A password that contains quotes or shell-looking text works. A namespace or username that is unsafe is rejected before any container starts, with a message that says how to fix it. Values are never spliced into commands or ObjectScript/SQL text.

**Why this priority**: Today a quote in a password breaks start-up with an opaque error after the container is already running, and a crafted value can run arbitrary ObjectScript in `%SYS`. CI secrets are often not written by the person running the tests.

**Independent Test**: Start a container object with the password `a"b'c$(x)` and confirm the values reach the container unchanged; construct one with namespace `MY NS; rm` and confirm a structured error before `start()`.

**Acceptance Scenarios**:

1. **Given** a username and a password containing quotes, dollar signs or parentheses, **When** the container starts, **Then** the user is created and can connect with that exact password.
2. **Given** a namespace that is not a plain name (spaces, quotes, punctuation, leading percent sign or hyphen), **When** the container object is created, **Then** it fails with a structured error naming the value's source (argument or environment variable) and an example of a valid name, and Docker is not touched.
3. **Given** a username that is not valid and a password that is set, **When** the container object is created, **Then** it fails with a structured error before start.
4. **Given** a username but no password, **When** the container is created, **Then** no user is created and the username is not validated.
5. **Given** a password that is empty or contains a NUL character, **When** the container object is created with a username, **Then** it fails with a message that never includes the password.
6. **Given** creating the database or the user fails inside IRIS, **When** start-up runs, **Then** a structured error names the failed step instead of failing later as an authentication error.
7. **Given** the namespace is `USER`, **When** the container starts, **Then** no database is created.

---

### User Story 2 - A licence problem is never silently hidden (Priority: P2)

A developer starts a community container whose licence is rejected. If reading the container logs fails during that check, the failure is visible, and real programming errors are not swallowed.

**Why this priority**: The licence check currently swallows every exception, so an unreadable log is reported as "licence fine" and nobody is told why.

**Independent Test**: Make the log read raise a Docker error, then a generic error; the first is logged as a warning and treated as not rejected, the second propagates.

**Acceptance Scenarios**:

1. **Given** the log read raises a Docker error or a not-started error, **When** the check runs, **Then** a warning with the error is logged and the licence is treated as not rejected.
2. **Given** the log read raises any other error, **When** the check runs, **Then** the error propagates.
3. **Given** a log read failure on the timeout path, **When** the start-up timeout is reported, **Then** the message says the licence check could not read the logs.
4. **Given** rejected and accepted licences, **When** the check runs, **Then** it returns true and false respectively.

---

### User Story 3 - No dead code pretending to be an API (Priority: P2)

A maintainer reads the container classes and finds only live code: no unused `driver` option, no fallback stub base class, no always-true feature flag, and no test that patches a name that does not exist.

**Why this priority**: The dead code misleads readers and about 34 test references pin behaviour no one can reach. Research found no users in sibling repositories.

**Independent Test**: Inspect the class hierarchy and constructor; run the suite and confirm coverage holds.

**Acceptance Scenarios**:

1. **Given** the `IRISContainer` class, **When** its bases are listed, **Then** `IRISDockerContainer` is a direct base and there is no stub base or availability flag.
2. **Given** the base class constructor, **When** it is called, **Then** it has no `driver` parameter or attribute.
3. **Given** the test suite, **When** it runs, **Then** no test patches a nonexistent attribute, and the previously broken contract test file is either rewritten as a real contract or deleted after comparison with the unit tests.
4. **Given** the deletions, **When** coverage is measured, **Then** the project-wide gate of 90% still holds.

---

### User Story 4 - `container up` containers are recognisable as idt's (Priority: P3)

A developer lists containers and can tell which ones idt created, so that feature 035's collision rule can safely treat them as replaceable.

**Why this priority**: Without labels on `container up` and the container adapter, 035 would treat them as unlabelled and refuse to touch them.

**Independent Test**: Create a container with `idt container up` and inspect its labels.

**Acceptance Scenarios**:

1. **Given** a container created by `idt container up`, **When** inspected, **Then** it carries `io.iris-devtester.created-by=idt` and `io.iris-devtester.image=<ref>`.
2. **Given** a container created through the container adapter's direct Docker path, **When** inspected, **Then** it carries the same labels.
3. **Given** the labelling, **When** `container up`, `remove` and the other commands run, **Then** their behaviour and output are otherwise unchanged.

---

### User Story 5 - Decisions are written down (Priority: P3)

A future contributor finds a record of why the base class is not built on the deprecated database container, why the fallback base was dropped, why values travel by environment, and what was left for later.

**Why this priority**: Constitution #10 requires blind alleys to be documented.

**Independent Test**: Read the CHANGELOG and `docs/learnings/` entries.

**Acceptance Scenarios**:

1. **Given** the CHANGELOG, **When** read, **Then** it states that the base deliberately does not derive from `DbContainer`, that `driver` was removed, and the new validation rules.
2. **Given** `docs/learnings/`, **When** read, **Then** one note explains why the fallback base and availability flag were dropped and why values are passed by environment rather than escaped.
3. **Given** the note, **When** read, **Then** it lists the follow-up: the same interpolation pattern in `utils/password.py` and `utils/namespace.py`.

### Edge Cases

- Namespace given through the environment but overridden by an argument: validation applies to the effective value.
- Username valid, password set only through the environment: user is created.
- Log read fails because the container exited before the check: treated as a not-started error, warning logged.
- A caller still passes `driver=`: receives an ordinary unexpected-argument error; no deprecation cycle (research found no users).
- The labelled image reference is empty or unknown: the image label is omitted rather than set empty.
- IRIS versions without the environment-variable lookup used for value transfer: caught by the integration test; see Assumptions.

## Requirements _(mandatory)_

### Functional Requirements

Safe values (T9)

- **FR-001**: The base MUST NOT place the username, password or namespace into any command string or ObjectScript/SQL text sent to the container. Values MUST reach the container through the process environment of a fixed command.
- **FR-002**: The namespace, when not `USER`, MUST fully match a letter followed by up to 63 letters, digits or underscores. The username, when a password is also supplied, MUST fully match 1 to 128 characters beginning with a letter, digit or underscore followed by letters, digits, underscore, dot, at sign or hyphen.
- **FR-003**: A password MUST be accepted if non-empty and free of NUL characters; nothing else is restricted.
- **FR-004**: Validation MUST happen when the container object is created, so errors precede `docker run`, and MUST cover values read from `IRIS_USERNAME`, `IRIS_PASSWORD` and `IRIS_NAMESPACE`.
- **FR-005**: Invalid values MUST raise a `ValueError` with a structured message (what went wrong, how to fix it) that names the source and gives a valid example. The password value MUST NOT appear in any error, log or exception text.
- **FR-006**: The opt-in rule MUST hold: no password means no user is created and the username is not validated; an invalid namespace always errors.
- **FR-007**: Both the create-database and create-user steps MUST have their exit status checked and raise a structured error naming the failed step on failure.
- **FR-008**: `IRISContainer` MUST inherit this behaviour without separate code.

Licence check (T10)

- **FR-009**: The community licence check MUST catch only Docker errors and container-not-started errors, log the error at warning level, and treat the licence as not rejected.
- **FR-010**: Other errors MUST propagate.
- **FR-011**: On the start-up timeout path the message MUST say when the licence check could not read logs; the helper keeps its boolean result.

Dead code (T10, R2)

- **FR-012**: The `driver` parameter and attribute, the redundant `self.image` assignment, the stub base class, the fallback import and the intermediate base alias MUST be removed, and `IRISContainer` MUST derive directly from the base.
- **FR-013**: The `HAS_TESTCONTAINERS` flag MUST be removed in a second step after FR-012 is green: its constructor warning and the manual host/port branch in `attach()` are deleted and the dependent tests are rewritten or deleted.
- **FR-014**: The contract test that patches a nonexistent attribute MUST be compared line by line with the password-preconfig unit tests, then rewritten as a real contract test for anything unique and deleted otherwise. No test may patch a nonexistent attribute.
- **FR-015**: Coverage MUST stay at or above the 90% gate (target 95%) after each removal step.

Labels (T4, 036 part)

- **FR-016**: Containers created by `idt container up` and by the container adapter's direct Docker path MUST carry `io.iris-devtester.created-by=idt` and `io.iris-devtester.image=<ref>`. Other behaviour is unchanged.

Tests and documentation

- **FR-017**: Tests MUST be written first in every task group; one integration test MUST create a user whose password contains a quote and connect as it, which also confirms the environment-variable value transfer on the target IRIS images.
- **FR-018**: The CHANGELOG MUST record the deliberate choice not to derive from `DbContainer`, the `driver` removal, and the new validation rules.
- **FR-019**: A `docs/learnings/` note MUST record why the fallback base and flag were dropped, why values travel by environment, and the follow-up for `utils/password.py` and `utils/namespace.py`.

### Key Entities

- **Container credentials**: username, password, namespace, and where each came from (argument or environment variable).
- **Validation rule**: a named pattern with an error message and an example.
- **Licence check result**: rejected, not rejected, or unreadable (logged, treated as not rejected).
- **Idt label set**: the two labels proving idt created a container.

## Assumptions

- The environment-variable lookup used for value transfer exists on all target IRIS images; FR-017's integration test verifies it, and if it fails the plan must choose another non-interpolating transfer before implementation continues.
- The namespace rule is deliberately conservative and is widened on demand (hyphen and leading percent sign are rejected).
- The installer-kit learnings note belongs to feature 035 (FR-037 there).
- Removing `driver` without a deprecation cycle is acceptable because no sibling repository uses it; external users of the published package are unknown and the CHANGELOG records it.
- The same interpolation in `utils/password.py` and `utils/namespace.py` is not fixed here.

## Out of Scope

- Fixing interpolation in `utils/password.py` and `utils/namespace.py` (follow-up).
- Changes to the `idt image` commands (feature 035).
- Any change to `container up` output or options other than labels.
- Rewriting the container classes beyond the removals above.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A password containing quotes, dollar signs and parentheses creates a usable account in 100% of tested cases.
- **SC-002**: 100% of invalid namespaces and usernames are rejected before any container is started, each with a message that names the fix.
- **SC-003**: The password value appears in 0 error, log or exception outputs across all tested failure paths.
- **SC-004**: A failure to create the database or user is reported at start-up with the failing step named in 100% of tested cases, instead of surfacing later as an authentication error.
- **SC-005**: A log-read failure during the licence check is visible to the user in 100% of tested cases, and no programming error is swallowed.
- **SC-006**: The removed names (`driver`, stub base, availability flag) have 0 references left in source and tests, and no test patches a nonexistent attribute.
- **SC-007**: Every container created by `idt container up` carries both labels.
- **SC-008**: The unit suite passes and project coverage stays at or above 90%.
