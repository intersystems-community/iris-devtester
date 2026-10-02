# Error Format Contract

```text
<Title>

What went wrong:
  <what>

Why it matters:
  <why>

How to fix it:
  <fix: at least one concrete command or flag>
```

Rules:

- Rendered once per command by the wrapper, to stderr.
- Never prints raw subprocess output without a fix.
- Never contains the password.
- Timeout messages add phase, limit and elapsed time; build timeouts add the last output line.
- Health timeout names `docker logs <name>` and `docker rm -f <name>`.
- Load timeout advises `docker images` before retrying.
- Collision refusals state one reason: "it is running", "it holds data", or "it was not created by idt"; the `--replace` hint appears only for idt-labelled containers.
- No-iris-main and architecture-mismatch messages include `docker create --platform <p>`, `docker cp`, `docker rm` for the public `containers.intersystems.com/intersystems/iris-community:latest-preview`.
