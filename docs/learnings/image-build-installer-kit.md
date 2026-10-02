# Learnings: `idt image build` and installer kits

Feature 035 hardened `idt image load` and `idt image build`. This records the blind alleys and the reasons behind the current behaviour.

## Why the license key is mounted, never baked

- The old build copied `iris.key` into the build context and a `COPY` line put it into an image layer. Anyone who could pull the image could read the key.
- A BuildKit secret (`RUN --mount=type=secret`) keeps the key out of the layers, but it adds cache-key and single-`RUN` constraints, and no build step needs a licensed instance. It is held in reserve.
- Decision: the image is always license-free. `docker run` gets `-v <key>:/usr/irissys/mgr/iris.key:ro`. The key is found from `--license`, then `IRIS_LICENSE_KEY`, then `./iris.key`. The old lookups beside the package and under `~/ws/iris-devtester` are gone, because they silently used keys from unrelated checkouts.
- The `--no-start` hint prints the same mount so a manual start is licensed too.

## Why `docker load` fails on installer kits

`singlefile_kits/` tarballs contain `irisinstall_silent`, not image layers (`manifest.json`). `docker load` cannot read them. `idt image load` detects this and exits 2 with a pointer to `idt image build`.

## `CAP_IPC_LOCK` and `setcap`

The Dockerfile copies `irisdb` to `iriscp` and runs `setcap cap_ipc_lock+ep` on it, and the container is started with `--cap-add CAP_IPC_LOCK`. Without both, IRIS cannot lock shared memory and fails to start inside a container.

## Timeouts

- The three phases have separate limits: `--build-timeout` (900 s), `--load-timeout` (300 s) and `--timeout` (120 s, the IRIS health wait only). The old build timeout was never enforced and `--timeout` was floored and overridden.
- The build runs in its own process group (`start_new_session=True`). On expiry idt sends SIGTERM to the group, then SIGKILL after 3 s. Killing only the `docker` CLI leaves buildx children running.
- Enforcement is macOS and Linux only. On Windows only the Docker CLI process is killed and build children may linger.
- Every timeout exits 5. On a health timeout the container is left running so you can read `docker logs`.

## `iris-main` architecture

`iris-main` must match the build platform. idt reads the ELF header (`e_machine` 0xB7 for arm64, 0x3E for amd64) before it populates the build directory. A wrong-architecture binary used to be found only after an eight-minute build. The OS ABI byte is not checked because it varies between toolchains.

Sources, in order: `--iris-main`, `IDT_IRIS_MAIN`, `--iris-main-container`, `--iris-main-image`, then auto-detect from running containers of the right architecture.

## Unverified

Whether an `iris-main` from a different IRIS version than the kit causes problems is not known. idt only warns when it can read both versions (a running source container's `/iris-main --version`, or a version in the image tag, against the kit file name) and continues.

## Container names

Containers idt creates carry `io.iris-devtester.created-by=idt` and `io.iris-devtester.image=<ref>`. A same-name container is replaced only when it has that label, and (unless it never started) only with `--replace`. Unlabelled containers are never removed. `--replace` removes the container but not volumes. An exited container is not auto-removed because its writable layer may hold data.
