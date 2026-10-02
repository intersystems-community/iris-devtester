# Feature Specification: Image Command Hardening

**Feature Branch**: `035-image-command-hardening`
**Created**: 2026-10-02
**Status**: Draft
**Input**: User description: "Harden `idt image load` and `idt image build` from the 2026-10-02 code-review findings of v1.19.4...HEAD. Decisions are recorded in `.scratch/wayfinder/map.md` and tickets T1-T7."

Vocabulary (see `CONTEXT.md`): an **image archive** is a tarball produced by `docker save`, loaded with `idt image load`. An **installer kit** is an IRIS installer tarball (contains `irisinstall_silent`), turned into an image with `idt image build`.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Commands that stop when they should (Priority: P1)

A developer runs `idt image load` or `idt image build` on a large archive or kit. If a phase hangs or exceeds its limit, the command stops, says which phase timed out, and tells them what to check, instead of running forever or reporting "Unexpected error".

**Why this priority**: Today the build timeout is never enforced, so a stuck build blocks a terminal or a CI job indefinitely. This is the most damaging defect.

**Independent Test**: Run `build` against a fake slow build command with a 1 second limit and confirm it exits with code 5 in roughly that time, with a message naming the phase, the limit and the elapsed time.

**Acceptance Scenarios**:

1. **Given** a build that runs past `--build-timeout`, **When** the limit is reached, **Then** the build and all its child processes are terminated, the command exits 5, and the message gives phase, limit, elapsed time, the last output line, and a retry hint.
2. **Given** an image load that runs past `--load-timeout`, **When** the limit is reached, **Then** the command exits 5 and advises checking `docker images` before retrying, because the daemon may still finish the import.
3. **Given** a container that does not become healthy within `--timeout`, **When** the limit is reached, **Then** the command exits 5, leaves the container running, and names it with `docker logs <name>` and `docker rm -f <name>`.
4. **Given** `--build-timeout 60`, **When** the command runs, **Then** exactly 60 seconds applies (no hidden minimum).

---

### User Story 2 - Clear, consistent failures and no leaked passwords (Priority: P1)

A developer hits any failure in `image load` or `image build` and gets the same three-part message (what went wrong, why it matters, how to fix it) and a predictable exit code. The container password is not printed by default.

**Why this priority**: Constitution #5 requires actionable errors. Printing the password in progress output leaks it into logs and screen shares.

**Independent Test**: Trigger each failure path and assert the exit code and the presence of the three message parts with at least one concrete command or flag; run a successful load and assert the password is absent from output.

**Acceptance Scenarios**:

1. **Given** an installer kit passed to `load`, **When** the command runs, **Then** it exits 2 with a message explaining to use `build`.
2. **Given** any Docker or runtime failure, **When** it occurs, **Then** the command exits 1 with the three-part message; no raw subprocess output is shown without a fix.
3. **Given** a timeout of any kind, **When** it occurs, **Then** the exit code is 5 and the message never says "Unexpected error".
4. **Given** a successful start with default settings, **When** the connection summary prints, **Then** the password shows as `********` and the output notes it was set with `--password`.
5. **Given** `--show-password`, **When** the summary prints, **Then** the real password is shown.
6. **Given** a non-default `--password` and a failed password reset, **When** the step fails, **Then** the command exits 1, leaves the container running, and names `docker rm -f <name>` and the re-run.
7. **Given** the default password and a failed reset, **When** the step fails, **Then** a warning is shown and the command exits 0.
8. **Given** `idt container up`, **When** it prints its connection summary, **Then** its output is unchanged from today.

---

### User Story 3 - License keys stay out of images (Priority: P1)

A developer builds an image from an installer kit with a license key. The key is never copied into the build context or any image layer; it is supplied to the container when it starts.

**Why this priority**: A key baked into a layer travels with the image to every registry and colleague. This is a credential-handling defect.

**Independent Test**: Build with a dummy key and confirm it is absent from the generated build context, the image history, and the saved image; confirm the run command mounts it read-only.

**Acceptance Scenarios**:

1. **Given** a key supplied by `--license`, `IRIS_LICENSE_KEY`, or `./iris.key` (checked in that order), **When** the container starts, **Then** the key is mounted read-only at `/usr/irissys/mgr/iris.key` and the "start manually" hint shows the same mount.
2. **Given** no key is found, **When** the build runs, **Then** a structured notice explains the consequence for enterprise images and how to supply a key, and the build continues.
3. **Given** an explicit path (option or environment variable) that does not exist, **When** the command runs, **Then** it exits 2 with a structured error.
4. **Given** a key in the package parent directory or `~/ws/iris-devtester/iris.key`, **When** none of the three sources is set, **Then** those locations are not consulted.
5. **Given** a key is resolved, **When** the command reports progress, **Then** it states which path was used.

---

### User Story 4 - Safe handling of existing containers (Priority: P2)

A developer re-runs `idt image load` or `build` with a container name that already exists. The tool cleans up only containers it created and never deletes anything else.

**Why this priority**: Constitution #1 asks for automatic remediation, but removing someone else's container, or one holding data, is destructive.

**Independent Test**: Create containers in each state, labelled and unlabelled, and assert which are removed, refused, or replaced.

**Acceptance Scenarios**:

1. **Given** an idt-created container in state `created` or `dead` with the same name, **When** the command runs, **Then** it is removed after one announcement line and the command continues.
2. **Given** an idt-created container that is running, exited, paused, or restarting, **When** the command runs without `--replace`, **Then** it exits 2 and explains why (running, or holds data) and offers `--replace`.
3. **Given** the same container and `--replace`, **When** the command runs, **Then** it states name, status and image, removes the container only (never volumes), and continues.
4. **Given** a container not created by idt (including from older idt versions), **When** the command runs, with or without `--replace`, **Then** it is never removed; the command exits 2 with guidance and no `--replace` hint.
5. **Given** any container created by `image load` or `image build`, **When** it is inspected, **Then** it carries the labels `io.iris-devtester.created-by=idt` and `io.iris-devtester.image=<ref>`.

---

### User Story 5 - A trustworthy iris-main for the target platform (Priority: P2)

A developer builds an installer kit for a given platform. The tool finds a matching `iris-main` binary deterministically, rejects one built for the wrong architecture before building, and tells them exactly how to get a correct one.

**Why this priority**: A wrong-architecture binary builds successfully and only fails at container start. Picking the first running container is non-deterministic and can read from an unrelated project's container.

**Independent Test**: Supply stub binaries with arm64 and amd64 ELF headers against each `--platform`, and confirm acceptance, rejection, source order, and cleanup.

**Acceptance Scenarios**:

1. **Given** several sources are available, **When** the build resolves iris-main, **Then** the order is `--iris-main`, `IDT_IRIS_MAIN`, `--iris-main-container`, `--iris-main-image`, then a running container that holds `/iris-main` and matches the target architecture.
2. **Given** a resolved binary whose architecture differs from `--platform`, **When** the build starts, **Then** it exits 2 before the build directory is populated, naming both architectures.
3. **Given** `--iris-main-image <ref>`, **When** the binary is extracted, **Then** the temporary container is removed on success and on failure.
4. **Given** no valid binary is found, **When** the build starts, **Then** it exits 2 with a message that includes the exact extraction commands for the detected platform, using the public `containers.intersystems.com/intersystems/iris-community:latest-preview` image.
5. **Given** a binary whose IRIS build differs from the installer kit's build, **When** both are determinable, **Then** a warning is shown and the build continues.
6. **Given** any resolution, **When** it succeeds, **Then** the source used is reported.

---

### User Story 6 - Maintainable, tested image commands (Priority: P3)

A maintainer changes the image commands with confidence: logic is split by concern, failure handling exists once, and the behaviour is covered by tests that fail if the old defects return.

**Why this priority**: The current module is one large file with no tests; the fixes above add enough logic that it would be unmaintainable without restructuring.

**Independent Test**: Run the unit suite and check coverage on the image package; confirm the CLI entry point still exposes `idt image`.

**Acceptance Scenarios**:

1. **Given** the restructure, **When** `idt image --help` runs, **Then** output and option names match the specified behaviour and the existing import path still works.
2. **Given** the package, **When** coverage is measured, **Then** it is at least 95%.
3. **Given** the pre-existing defects (unenforced timeout, echoed password, hard-coded 120 s health wait), **When** the characterisation tests run before the fixes, **Then** they are recorded as expected failures and become normal passing tests in the task that fixes each.

### Edge Cases

- Build timeout fires while the build is writing its last line: the timeout still wins and exit is 5.
- `docker load` times out but the daemon completes the import: the message tells the user to check `docker images` before re-running.
- Labelled container exists but `docker rm` fails: structured error, exit 1, name the manual command.
- `IDT_IRIS_MAIN` points to a file that does not exist: structured error, exit 2.
- `--iris-main-image` with an unreachable registry: temporary container cleanup still runs, exit 1 with fix.
- Windows: the build timeout falls back to terminating the Docker CLI process only; child processes may linger. This is documented, not solved.
- A truncated or non-ELF `iris-main` file is rejected as a bad file, not reported as an architecture mismatch.
- The user supplies both a key and no key environment: the explicit option wins.

## Requirements _(mandatory)_

### Functional Requirements

Timeouts (T2)

- **FR-001**: `build` MUST accept `--build-timeout` (default 900 seconds) covering only the image build phase.
- **FR-002**: `load` MUST accept `--load-timeout` (default 300 seconds) covering only the archive import phase.
- **FR-003**: `--timeout` on both commands MUST mean only the IRIS health wait (default 120 seconds) and MUST reach the health check instead of a fixed value.
- **FR-004**: The build MUST be terminated, including child processes, when its limit is reached (graceful stop, then forced stop after about 3 seconds) on macOS and Linux.
- **FR-005**: An import timeout MUST be reported as a timeout, with advice to check `docker images`.
- **FR-006**: Every timeout MUST exit 5. The build directory MUST be removed unless `--keep-build-dir` is given.
- **FR-007**: On health-wait expiry the container MUST be left running and named in the error.
- **FR-008**: The fixed 60-second `docker run` limit MUST become a named constant. No minimum value is enforced on user-supplied timeouts. Each timeout option's `--help` MUST name its phase.
- **FR-009**: The `--timeout` meaning change on `build` MUST be recorded in the CHANGELOG.

Errors and output (T3)

- **FR-010**: Every failure MUST be reported once, by one shared renderer, as a title plus "What went wrong", "Why it matters" and "How to fix it", with at least one concrete command or flag.
- **FR-011**: Exit codes MUST be 0 success; 1 Docker or runtime failure (including the catch-all, whose fix mentions `--keep-build-dir` and filing an issue); 2 bad input or precondition; 5 any timeout.
- **FR-012**: The `Setting _SYSTEM password to '<pw>'` output MUST be removed. The connection summary MUST show `********` unless `--show-password` is given.
- **FR-013**: The shared connection-summary function MUST keep showing the password by default so `container up` and its tests are unchanged.
- **FR-014**: A failed password reset or unexpire MUST be a warning with exit 0 for the default password, and an error with exit 1 for a non-default `--password`, leaving the container running.
- **FR-015**: The unreachable statement after the clean exit MUST be removed.

License key (T1)

- **FR-016**: The key MUST NOT appear in the build context or any image layer.
- **FR-017**: Key discovery MUST be `--license`, then `IRIS_LICENSE_KEY`, then `./iris.key` in the current directory, and nothing else.
- **FR-018**: A resolved key MUST be mounted read-only at `/usr/irissys/mgr/iris.key` when the container starts, and in the printed manual-start command.
- **FR-019**: With no key, the command MUST print a structured notice (what happened, consequence for enterprise images, how to supply one) and continue.
- **FR-020**: An explicit path that does not exist MUST fail with a structured error, exit 2.

Name collisions and labels (T4)

- **FR-021**: Containers created by `load` and `build` MUST carry the labels `io.iris-devtester.created-by=idt` and `io.iris-devtester.image=<ref>`.
- **FR-022**: Collision handling MUST follow the rules in User Story 4, including one-line announcements and exit 2 refusals with a reason (running, holds data, not created by idt).
- **FR-023**: `--replace` MUST remove only the container, after stating its name, status and image, and MUST NOT be honoured for unlabelled containers.

iris-main (T5)

- **FR-024**: Resolution order MUST follow User Story 5, with the environment variable `IDT_IRIS_MAIN` and the option `--iris-main-image`.
- **FR-025**: The first 20 bytes of the resolved file MUST be checked: little-endian 64-bit ELF with a machine type matching `--platform` (arm64 or amd64) before the build directory is populated.
- **FR-026**: Image extraction MUST target `--platform` and MUST remove its temporary container on success and failure.
- **FR-027**: A version mismatch MUST warn and never fail; the gap MUST be documented.
- **FR-028**: The failure message MUST include exact extraction commands for the detected platform.
- **FR-029**: The helper that finds a source container MUST be named for what it returns.

Structure and tests (T6, T7)

- **FR-030**: The image commands MUST live in a package split by concern (errors, iris-main, collision, license, load, build, options), with the existing module kept as a thin shim so the current import path and `idt image` entry point keep working.
- **FR-031**: Start-up parameters MUST be carried in one immutable options object shared by both commands; failure handling and the no-start output MUST exist once.
- **FR-032**: The start helper MUST be renamed for what it does; unused parameters and dead code MUST be removed.
- **FR-033**: Code formatting of the existing module MUST be applied as the first change, before behavioural changes.
- **FR-034**: Tests MUST be written before the code they cover. Characterisation tests for existing defects MUST be written first as strict expected failures.
- **FR-035**: Tests MUST mock only the subprocess runner and the Docker client, use generated installer-kit and image-archive fixtures with stub ELF headers, and include one integration test for `load` that is skipped when Docker is unavailable.
- **FR-036**: Coverage of the image package MUST be at least 95%; the project-wide gate stays 90%.

Documentation (Constitution #10)

- **FR-037**: A `docs/learnings/` note MUST record: why the key is mounted rather than baked (including the build-secret findings), why `docker load` fails on installer kits, the `CAP_IPC_LOCK`/`setcap` requirement, the macOS/Linux-only timeout enforcement, and the unverified version-mismatch question.

### Key Entities

- **Image archive**: a `docker save` tarball accepted by `load`.
- **Installer kit**: an IRIS installer tarball accepted by `build`.
- **Image command error**: a failure carrying what, why, fix and an exit code.
- **Start options**: name, ports, password and visibility, unexpire choice, health timeout, run timeout, labels, license mount.
- **Idt label**: the marker proving idt created a container; the sole basis for removal.
- **Resolved iris-main**: a binary file plus the source that supplied it and its detected architecture.

## Assumptions

- Traceability: the code-review findings map to requirements as follows. Build timeout unenforced: FR-001, FR-004, FR-006. Hard-coded health timeout: FR-003. Unexpected-error on timeout: FR-005, FR-011. Password echo: FR-012 to FR-014. Unstructured errors: FR-010. Key handling and hard-coded user path: FR-016 to FR-020. Destructive guidance on collision: FR-021 to FR-023. Unvalidated iris-main: FR-024 to FR-029. Long functions, duplicated handlers, dead code, formatting: FR-030 to FR-033. Missing tests: FR-034 to FR-036. Missing blind-alley docs: FR-037.
- Timeout flags and exit code 5 already appear in the existing CLI help; this feature makes them true.
- A BuildKit secret is held in reserve and not used, since no known build step needs a licensed instance.
- Password-handling changes in `utils/password.py` and `utils/namespace.py` belong to feature 036, not this one.
- Labelling of `idt container up` and the container adapter belongs to feature 036.

## Out of Scope

- Rebuilding `idt image` on top of the existing container, CPF and wait-strategy modules.
- Applying the `latest-em` default to x86.
- Merging the two version strings into one source.
- The scope-creep items already shipped (Colima wording, "Historical roadmap" rename, `packaging` dependency).
- Windows-native process-tree termination.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A build or load that exceeds its limit stops within 5 seconds of the limit and exits 5, in 100% of tested cases.
- **SC-002**: 100% of failure paths in `load` and `build` show all three message parts with a concrete fix and use exit codes from the documented set.
- **SC-003**: The password appears in default output in 0 tested paths, and appears only when `--show-password` is given.
- **SC-004**: A license key is found in 0 of: the build context, image history, saved image.
- **SC-005**: No container not created by idt is removed in any tested state, with or without `--replace`.
- **SC-006**: A wrong-architecture `iris-main` is rejected before any build work begins in 100% of tested platform combinations.
- **SC-007**: A developer with no running IRIS container can obtain a valid `iris-main` by copy-pasting commands from the error message alone.
- **SC-008**: Coverage of the image package is at least 95%, and the full unit suite passes with the project-wide gate at 90%.
