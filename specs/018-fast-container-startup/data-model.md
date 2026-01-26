# Data Model: Fast Container Startup

**Feature**: 018-fast-container-startup
**Date**: 2025-12-24

---

## Entities

### 1. ContainerPool

Singleton managing reusable IRIS containers.

```python
@dataclass
class ContainerPool:
    """Manages reusable IRIS containers for test sessions."""

    # Fields
    containers: Dict[str, ContainerRef] = field(default_factory=dict)
    default_name: str = "iris-dev"
    health_cache: HealthCache = field(default_factory=HealthCache)

    # Singleton
    _instance: ClassVar[Optional["ContainerPool"]] = None

    @classmethod
    def instance(cls) -> "ContainerPool":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # Methods
    def get_or_create(self, name: str = None) -> ContainerRef:
        """Get existing container or create new one."""
        ...

    def acquire(self, name: str = None) -> ContainerRef:
        """Acquire container for use (marks as in-use)."""
        ...

    def release(self, name: str) -> None:
        """Release container back to pool."""
        ...

    def health_check(self, name: str, use_cache: bool = True) -> bool:
        """Check container health with optional caching."""
        ...
```

**Relationships**:
- Contains multiple `ContainerRef` instances
- Uses `HealthCache` for caching health checks

---

### 2. ContainerRef

Reference to a Docker container with connection info.

```python
@dataclass
class ContainerRef:
    """Reference to a reusable IRIS container."""

    # Fields
    name: str
    container_id: str
    host: str = "localhost"
    port: int = 1972
    webserver_port: int = 52773
    status: ContainerStatus = ContainerStatus.UNKNOWN
    in_use: bool = False
    last_health_check: Optional[datetime] = None
    allocated_namespaces: List[str] = field(default_factory=list)

    # Methods
    def get_connection(self) -> Connection:
        """Get DBAPI connection to this container."""
        ...

    def get_iris_connection(self) -> iris.Connection:
        """Get iris.connect() connection for ObjectScript ops."""
        ...

    def is_healthy(self) -> bool:
        """Check if container is healthy and running."""
        ...
```

**Validation Rules**:
- `name` must be non-empty string
- `port` must be 1-65535
- `container_id` must be valid Docker container ID

---

### 3. TestNamespace

Isolated namespace for a test session.

```python
@dataclass
class TestNamespace:
    """Isolated IRIS namespace for test session."""

    # Fields
    name: str
    container_ref: ContainerRef
    created_at: datetime = field(default_factory=datetime.now)
    cleanup_registered: bool = False
    tables_created: List[str] = field(default_factory=list)

    # Methods
    def create(self) -> None:
        """Create namespace in IRIS via Config.Namespaces."""
        ...

    def drop(self) -> None:
        """Delete namespace and all contents."""
        ...

    def execute_sql(self, sql: str) -> Any:
        """Execute SQL in this namespace via DBAPI."""
        ...

    def execute_objectscript(self, code: str) -> str:
        """Execute ObjectScript in this namespace via iris.connect()."""
        ...

    def register_cleanup(self, atexit: bool = True) -> None:
        """Register cleanup handler for test teardown."""
        ...
```

**State Transitions**:
```
PENDING -> CREATED -> IN_USE -> DROPPED
                  \-> ERROR
```

**Naming Convention**:
- Pattern: `TEST_{timestamp}_{random_hex}`
- Example: `TEST_1735084800_a1b2c3d4`

---

### 4. HealthCache

Cached health check results with TTL.

```python
@dataclass
class HealthCache:
    """Cache for container health check results."""

    # Fields
    results: Dict[str, HealthCacheEntry] = field(default_factory=dict)
    ttl_seconds: float = 30.0  # Default 30s for dev, 5s for CI

    # Methods
    def get(self, container_name: str) -> Optional[bool]:
        """Get cached health status if not expired."""
        ...

    def set(self, container_name: str, is_healthy: bool) -> None:
        """Cache health check result."""
        ...

    def invalidate(self, container_name: str = None) -> None:
        """Invalidate cache entry or all entries."""
        ...

    def is_valid(self, container_name: str) -> bool:
        """Check if cache entry exists and is not expired."""
        ...


@dataclass
class HealthCacheEntry:
    """Single cache entry."""
    is_healthy: bool
    checked_at: datetime
    ttl_seconds: float
```

**TTL Configuration**:
- Local development: 30 seconds (fast iteration)
- CI/CD: 5 seconds (more frequent validation)
- Configurable via environment variable `IRIS_HEALTH_CACHE_TTL`

---

### 5. OutputFormatter

Transforms verbose output for AI consumption.

```python
@dataclass
class OutputFormatter:
    """Format test output for AI-friendly consumption."""

    # Fields
    max_lines: int = 50
    max_lines_failing: int = 100
    dedupe_enabled: bool = True
    show_timestamps: bool = False

    # Methods
    def format_test_output(self, raw: str, is_failing: bool = False) -> str:
        """Format test output with truncation and deduplication."""
        ...

    def summarize_container_logs(self, logs: str, max_lines: int = 20) -> str:
        """Summarize container logs to key events."""
        ...

    def format_error(self, error: Exception) -> str:
        """Format exception for AI consumption (one screen max)."""
        ...

    def _deduplicate_lines(self, lines: List[str]) -> List[str]:
        """Remove consecutive duplicate lines."""
        ...

    def _truncate_middle(self, lines: List[str], max_lines: int) -> List[str]:
        """Keep head and tail, truncate middle."""
        ...
```

**Output Limits**:
- Passing tests: 50 lines max
- Failing tests: 100 lines max
- Error messages: 25 lines max
- Container logs: 20 lines max

---

## Enums

### ContainerStatus

```python
class ContainerStatus(Enum):
    """Status of a container in the pool."""
    UNKNOWN = "unknown"
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    ERROR = "error"
```

---

## Relationships Diagram

```
ContainerPool (singleton)
    │
    ├── contains many → ContainerRef
    │                       │
    │                       └── allocates many → TestNamespace
    │
    └── uses → HealthCache
                   │
                   └── contains many → HealthCacheEntry
```

---

## Validation Rules Summary

| Entity | Field | Rule |
|--------|-------|------|
| ContainerRef | name | Non-empty string, valid Docker name |
| ContainerRef | port | 1-65535 |
| TestNamespace | name | Match pattern `TEST_\d+_[a-f0-9]+` |
| HealthCache | ttl_seconds | > 0 |
| OutputFormatter | max_lines | >= 10 |

---
*Data model complete - ready for contract generation*
