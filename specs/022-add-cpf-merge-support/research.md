# Research: CPF Merge Support

**Feature Branch**: `022-add-cpf-merge-support` | **Date**: 2026-01-05

## 1. Internal Path for CPF Merge

- **Decision**: Mount CPF merge files to `/usr/irissys/merge.cpf` inside the container.
- **Rationale**: This path is standard in InterSystems community templates and ensures the file is accessible to the `iris-main` startup process.
- **Alternatives considered**: `/tmp/iris.cpf`.
  - *Rejected because*: Some environments may have strict `/tmp` cleanup policies or no-exec flags.

## 2. Temporary File Lifecycle

- **Decision**: Use `tempfile.NamedTemporaryFile` with a custom `TempCPFManager` that tracks files.
- **Rationale**: Python's `tempfile` is robust but needs careful handling to ensure the file exists long enough for Docker to mount it, but is deleted after the container stops.
- **Implementation**:
  ```python
  class TempCPFManager:
      def create(self, content: str) -> str:
          # Creates file, returns absolute host path
          pass
      def cleanup(self):
          # Deletes all tracked files
          pass
  ```

## 3. CPF Syntax for Common Actions

### Enabling CallIn
```ini
[Actions]
ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48
```
*AutheEnabled=48 enables both Password and Unauthenticated access.*

### CI Memory Optimization
```ini
[config]
globals=0,0,256,0,0,0
gmheap=64000
```
*Optimized for a ~512MB budget: 256MB Global cache, 64MB Shared memory.*

## 4. Testcontainers Integration

- **Decision**: Use `self.with_volume_mapping(host_path, "/usr/irissys/merge.cpf", "ro")`.
- **Rationale**: Read-only mapping is sufficient and safer for configuration.
- **Decision**: Set `ISC_CPF_MERGE_FILE` environment variable via `self.with_env()`.
