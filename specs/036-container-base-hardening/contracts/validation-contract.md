# Validation Contract

Raised as `ValueError` from the constructor, before `start()`:

```text
Invalid namespace 'MY NS; rm' for IRISDockerContainer

What went wrong:
  A namespace must start with a letter and contain only letters, digits and
  underscores (max 64 characters). The value is used as a SQL identifier in
  CREATE DATABASE, so spaces, quotes and punctuation are not allowed.

How to fix it:
  1. Use a plain name, for example MY_NS.
  2. If it came from the IRIS_NAMESPACE environment variable, correct it there.
```

- Username error has the same shape and names `IRIS_USERNAME`.
- Password error says only: "password must be non-empty and must not contain a NUL character"; the value is never included.
- Exec failure: `Could not create database '<ns>'` or `Could not create user '<name>'`, each with the exit code and a fix; the password is never included.
- Logging never includes the password or the environment mapping passed to the exec.
