# Data Model: Container Lifecycle CLI Commands

**Feature**: 008-add-container-lifecycle
**Date**: 2025-01-10
**Phase**: 1 (Design)

## Overview

This feature introduces two primary entities for managing IRIS container lifecycle from the CLI:

1. **ContainerConfig**: User-specified configuration for creating/managing containers
2. **ContainerState**: Runtime state of a managed container

## Entity Definitions

### ContainerConfig

**Purpose**: Represents user-defined configuration for IRIS container lifecycle operations. Loaded from YAML file or constructed from CLI arguments + defaults.

**Source**: iris-config.yml file or zero-config defaults

**Attributes**:

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `edition` | Enum[community, enterprise] | No | community | Must be 'community' or 'enterprise' | IRIS edition to use |
| `container_name` | str | No | iris_db | Valid Docker name | Container name identifier |
| `superserver_port` | int | No | 1972 | 1024-65535 | SuperServer port mapping |
| `webserver_port` | int | No | 52773 | 1024-65535 | Management Portal port |
| `namespace` | str | No | USER | Valid IRIS namespace name | Default namespace |
| `password` | str | No | SYS | Non-empty | _SYSTEM user password |
| `license_key` | str | Conditional | None | Valid key format (enterprise only) | License key for Enterprise edition |
| `volumes` | List[VolumeMount] | No | [] | Valid Docker volume syntax | Volume mappings |
| `image_tag` | str | No | latest | Valid Docker tag | IRIS Docker image tag |

**Relationships**:
- Zero or one ContainerState per ContainerConfig (after container created)
- ContainerConfig is immutable after container creation (changes require new container)

**Validation Rules**:
```python
@dataclass
class ContainerConfig:
    """Container configuration model."""
    edition: Literal["community", "enterprise"]
    container_name: str
    superserver_port: int
    webserver_port: int
    namespace: str
    password: str
    license_key: Optional[str]
    volumes: List[str]
    image_tag: str

    def __post_init__(self):
        """Validate configuration."""
        # Validate ports
        if not (1024 <= self.superserver_port <= 65535):
            raise ValueError(f"Invalid superserver_port: {self.superserver_port}")
        if not (1024 <= self.webserver_port <= 65535):
            raise ValueError(f"Invalid webserver_port: {self.webserver_port}")

        # Validate edition + license
        if self.edition == "enterprise" and not self.license_key:
            raise ValueError("license_key required for enterprise edition")

        # Validate container name
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", self.container_name):
            raise ValueError(f"Invalid container_name: {self.container_name}")

        # Validate namespace
        if not re.match(r"^[A-Z][A-Z0-9%]*$", self.namespace):
            raise ValueError(f"Invalid namespace: {self.namespace}")
```

**YAML Representation**:
```yaml
# iris-config.yml
edition: community
container_name: iris_db
ports:
  superserver: 1972
  webserver: 52773
namespace: USER
password: SYS
license_key: ""
volumes:
  - ./data:/external
image_tag: latest
```

**Python Construction**:
```python
from iris_devtester.config import ContainerConfig

# From YAML file
config = ContainerConfig.from_yaml("iris-config.yml")

# From defaults
config = ContainerConfig.default()

# Explicit
config = ContainerConfig(
    edition="community",
    container_name="my_iris",
    superserver_port=1972,
    webserver_port=52773,
    namespace="USER",
    password="SYS",
    license_key=None,
    volumes=[],
    image_tag="latest"
)
```

---

### ContainerState

**Purpose**: Represents the runtime state and health of a managed IRIS container. Updated dynamically as container lifecycle changes.

**Source**: Queried from Docker engine via Docker SDK

**Attributes**:

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `container_id` | str | 64 hex chars | Docker container ID (full hash) |
| `container_name` | str | Matches ContainerConfig | Container name |
| `status` | Enum[creating, starting, running, healthy, stopped, removing] | Valid state | Current lifecycle state |
| `health_status` | Enum[starting, healthy, unhealthy, none] | Optional | Docker health check status |
| `created_at` | datetime | ISO 8601 | Container creation timestamp |
| `started_at` | Optional[datetime] | ISO 8601 | Last start timestamp |
| `finished_at` | Optional[datetime] | ISO 8601 | Last stop timestamp |
| `ports` | Dict[int, int] | Port mapping | Exposed port mappings (container→host) |
| `image` | str | Docker image ref | Full image reference used |
| `config_source` | Optional[Path] | File path | Source config file (if any) |

**State Transitions**:
```
[Not Exists]
    ↓ (create)
[creating] → [starting] → [running] → [healthy]
    ↓            ↓            ↓            ↓
 (error)      (error)      (stop)      (remove)
    ↓            ↓            ↓            ↓
[stopped] ←──────┴────────────┘            X
    ↓ (restart)
[starting] → ...
    ↓ (remove)
    X (removed)
```

**Validation Rules**:
- `status` must be valid lifecycle state
- `container_id` must be 64 character hex string
- `started_at` must be after `created_at` (if present)
- `finished_at` must be after `started_at` (if present)
- `ports` keys must be container ports, values must be host ports

**Query Pattern**:
```python
from iris_devtester.cli.container import get_container_state

# Get current state
state = get_container_state("iris_db")

print(f"Status: {state.status}")
print(f"Health: {state.health_status}")
print(f"Uptime: {datetime.now() - state.started_at}")
print(f"Ports: {state.ports}")
```

**Docker SDK Mapping**:
```python
import docker

def get_container_state(container_name: str) -> ContainerState:
    """Query Docker engine for container state."""
    client = docker.from_env()
    container = client.containers.get(container_name)

    # Map Docker attrs to ContainerState
    return ContainerState(
        container_id=container.id,
        container_name=container.name,
        status=_map_docker_status(container.status),
        health_status=_extract_health(container.attrs),
        created_at=_parse_timestamp(container.attrs["Created"]),
        started_at=_parse_timestamp(container.attrs["State"]["StartedAt"]),
        finished_at=_parse_timestamp(container.attrs["State"]["FinishedAt"]),
        ports=_extract_ports(container.attrs["NetworkSettings"]["Ports"]),
        image=container.image.tags[0],
        config_source=None  # Retrieved from labels if set
    )
```

---

## Relationships

```
┌─────────────────────┐
│  ContainerConfig    │
│  (Configuration)    │
│                     │
│  - edition          │
│  - container_name   │
│  - ports            │
│  - namespace        │
│  - password         │
│  - license_key      │
│  - volumes          │
│  - image_tag        │
└──────────┬──────────┘
           │
           │ creates
           │
           ↓
┌─────────────────────┐
│  ContainerState     │
│  (Runtime)          │
│                     │
│  - container_id     │
│  - status           │
│  - health_status    │
│  - created_at       │
│  - ports            │
│  - config_source    │
└─────────────────────┘
```

**Lifecycle**:
1. User creates/loads `ContainerConfig` (from YAML or defaults)
2. CLI validates `ContainerConfig` (ports, license, namespace)
3. `container up` uses config to create container → `ContainerState` created
4. `container status` queries Docker → returns current `ContainerState`
5. `container stop` updates Docker → `ContainerState.status` changes to "stopped"
6. `container remove` deletes container → `ContainerState` no longer exists

---

## CLI Command Mappings

| CLI Command | Primary Entity | Operation |
|-------------|----------------|-----------|
| `container up` | ContainerConfig → ContainerState | Create container from config, return final state |
| `container start` | ContainerConfig → ContainerState | Start existing or create new, return state |
| `container stop` | ContainerState | Update state to stopped |
| `container restart` | ContainerState | Stop then start, update state |
| `container status` | ContainerState | Query and display current state |
| `container logs` | ContainerState | Stream logs from running container |
| `container remove` | ContainerState | Delete container, state no longer exists |

---

## Configuration Loading Strategy

```python
def load_config(config_path: Optional[Path]) -> ContainerConfig:
    """Load configuration with fallback hierarchy."""

    # 1. Explicit config file
    if config_path and config_path.exists():
        return ContainerConfig.from_yaml(config_path)

    # 2. Default location (./iris-config.yml)
    default_path = Path.cwd() / "iris-config.yml"
    if default_path.exists():
        return ContainerConfig.from_yaml(default_path)

    # 3. Environment variables
    if "IRIS_EDITION" in os.environ or "IRIS_LICENSE_KEY" in os.environ:
        return ContainerConfig.from_env()

    # 4. Zero-config defaults
    return ContainerConfig.default()
```

**Priority Order**:
1. `--config` flag (explicit)
2. `./iris-config.yml` in current directory
3. Environment variables (`IRIS_EDITION`, `IRIS_LICENSE_KEY`, etc.)
4. Zero-config defaults (community, localhost:1972, etc.)

---

## State Persistence

**Container Labels**: Store config source for future reference

```python
def create_container_with_labels(config: ContainerConfig):
    """Create container with config metadata in labels."""
    labels = {
        "iris-devtester.config.source": str(config.source_file) if config.source_file else "default",
        "iris-devtester.config.edition": config.edition,
        "iris-devtester.version": "1.0.3",
    }

    container = client.containers.run(
        image=get_image_name(config),
        name=config.container_name,
        labels=labels,
        ...
    )
```

**Why Labels**:
- Survives container restarts
- Queryable via Docker API
- No external database required
- Standard Docker pattern

---

## Example Workflows

### Workflow 1: Zero-Config Container
```python
# User runs: iris-devtester container up

# 1. Load config
config = ContainerConfig.default()  # Uses community defaults

# 2. Create container
state = create_container(config)  # ContainerState created

# 3. Wait for healthy
wait_for_healthy(state)

# 4. Display connection info
print(f"IRIS running at localhost:{state.ports[1972]}")
```

### Workflow 2: Enterprise Container from YAML
```yaml
# iris-config.yml
edition: enterprise
license_key: "AB12-CD34-EF56-GH78"
namespace: PROD
password: SecurePassword123
```

```python
# User runs: iris-devtester container up --config iris-config.yml

# 1. Load config from file
config = ContainerConfig.from_yaml("iris-config.yml")

# 2. Validate enterprise license
if config.edition == "enterprise":
    validate_license_key(config.license_key)

# 3. Create container with enterprise image
state = create_container(config)

# 4. Wait and display
wait_for_healthy(state)
print(f"IRIS Enterprise running: {state.container_id[:12]}")
```

### Workflow 3: Check Status
```python
# User runs: iris-devtester container status

# 1. Query current state from Docker
state = get_container_state("iris_db")  # Default container name

# 2. Display state information
print(f"Status: {state.status}")
print(f"Health: {state.health_status}")
print(f"Uptime: {format_uptime(state.started_at)}")
print(f"Ports: {format_ports(state.ports)}")
print(f"Image: {state.image}")
```

---

## Testing Strategy

### Unit Tests
- ContainerConfig validation (invalid ports, missing license, etc.)
- ContainerState transitions (valid/invalid state changes)
- Configuration loading hierarchy (file → env → defaults)
- YAML parsing (valid/invalid schemas)

### Integration Tests
- Full lifecycle: up → status → stop → start → remove
- Config file variations (community, enterprise, custom ports)
- Idempotency (multiple `up` calls)
- Error scenarios (Docker not running, port conflicts)

### Contract Tests
- ContainerConfig JSON schema validation
- ContainerState JSON schema validation
- YAML file schema validation
- CLI output format (status, connection info)

---

## Schema Validation

Using Pydantic for runtime validation:

```python
from pydantic import BaseModel, Field, validator

class ContainerConfigModel(BaseModel):
    """Pydantic model for ContainerConfig validation."""
    edition: Literal["community", "enterprise"]
    container_name: str = Field(..., regex=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
    superserver_port: int = Field(1972, ge=1024, le=65535)
    webserver_port: int = Field(52773, ge=1024, le=65535)
    namespace: str = Field("USER", regex=r"^[A-Z][A-Z0-9%]*$")
    password: str = Field(..., min_length=1)
    license_key: Optional[str] = None
    volumes: List[str] = []
    image_tag: str = "latest"

    @validator("license_key", always=True)
    def validate_enterprise_license(cls, v, values):
        """Require license_key for enterprise edition."""
        if values.get("edition") == "enterprise" and not v:
            raise ValueError("license_key required for enterprise edition")
        return v

    class Config:
        schema_extra = {
            "example": {
                "edition": "community",
                "container_name": "iris_db",
                "superserver_port": 1972,
                "webserver_port": 52773,
                "namespace": "USER",
                "password": "SYS",
                "volumes": ["./data:/external"],
                "image_tag": "latest"
            }
        }
```

---

## Next Phase

Data model complete. Proceed to contract generation for CLI commands.
