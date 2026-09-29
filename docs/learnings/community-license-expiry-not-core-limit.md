# "May have exceeded core limit" usually means an expired community image

## Symptom

A community container exits during startup and IRIS logs this:

```text
Error: Invalid Community Edition license, may have exceeded core limit.
- Shutting down the system : $zu(56,2)= 0
```

testcontainers then waits for `Enabling logons` until its 120 s timeout.

## Blind alley: pinning CPU cores

The message points at CPU count, so the obvious fix is `cpuset_cpus="0-3"`.
Measured on 2026-09-29 (OrbStack, 8 vCPUs, arm64):

| Image                                         | 4 cores | 8 cores | unpinned |
| --------------------------------------------- | ------- | ------- | -------- |
| `containers.intersystems.com/...:2025.1`      | FAIL    | FAIL    | FAIL     |
| `containers.intersystems.com/...:2026.1`      | OK      | OK      | not run  |
| `containers.intersystems.com/...:latest-em`   | —       | —       | OK       |
| `intersystemsdc/iris-community:latest` (26.1) | OK      | OK      | OK       |

Core count made no difference. The 2025.1 image fails even on 4 cores. Its
bundled Community license has expired. A pinned-core run only appeared to fix
it because that run happened to use a newer image.

## Root cause in idt

On arm64, `IRISContainer.community()` defaulted to the pinned tag `2025.1`. It
worked when written and broke once that image's license expired.

## Fix

- On arm64, `community()` now defaults to the rolling `latest-em` tag, as
  `light()` already did. It no longer defaults to a fixed release.
- `IRISDockerContainer._connect` also treats the license error as a
  wait-for-logs stop condition. Startup then fails in seconds with a
  `RuntimeError` that explains the expiry and names a current tag, instead of
  a 120 s `TimeoutError`.

If you need a specific release, pass `version="2026.1"`. Expect to bump it
when that image's license expires.
