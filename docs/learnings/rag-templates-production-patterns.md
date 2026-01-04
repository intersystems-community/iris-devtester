# Production IRIS Patterns from rag-templates

**Source**: `~/ws/rag-templates/`
**Purpose**: Extract battle-tested patterns for iris-devtester
**Date**: 2025-10-18

---

## Overview

This document captures production-proven patterns from the rag-templates project that should be integrated into iris-devtester to make it "facile with database container ops."

**Key Files Analyzed**:
- `common/iris_connection_manager.py` - Connection management
- `common/iris_connection_pool.py` - Connection pooling
- `common/iris_dbapi_connector.py` - DBAPI connections with auto-detection
- `tests/utils/iris_password_reset.py` - Password remediation
- `tests/integration/conftest.py` - Integration test fixtures
- `docker-compose.yml` - Container configuration

---

## Pattern 1: Multi-Port Discovery with Fallback

**Location**: `tests/integration/conftest.py:35-65`

**The Pattern**:
```python
@pytest.fixture(scope="session")
def iris_connection_config():
    """IRIS database connection configuration for integration tests."""
    # Try multiple common IRIS ports in priority order
    test_ports = [31972, 1972, 11972, 21972]

    for port in test_ports:
        try:
            # Test with subprocess to avoid import issues
            result = subprocess.run([
                sys.executable, "-c",
                f"""
import sqlalchemy_iris
from sqlalchemy import create_engine, text
try:
    engine = create_engine(f'iris://_SYSTEM:SYS@localhost:{port}/USER')
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('SUCCESS')
except Exception:
    print('FAILED')
"""
            ], capture_output=True, text=True, timeout=5)

            if "SUCCESS" in result.stdout:
                return {
                    "host": "localhost",
                    "port": port,
                    "username": "_SYSTEM",
                    "password": "SYS",
                    "namespace": "USER",
                }
        except:
            continue

    pytest.skip("No IRIS database available for integration tests")
```

**Why It Works**:
- **Real-world deployments** use different ports (1972 standard, 11972 rag-templates, 21972 licensed, 31972 testcontainers)
- **Subprocess isolation** prevents import errors from breaking port detection
- **Graceful degradation** - tries each port until one succeeds
- **pytest.skip()** instead of failing when no IRIS available

**Integration into iris-devtester**:
- Add to `iris_devtester/config/auto_discovery.py`
- Use in IRISContainer.from_existing()
- Document port conventions in CONSTITUTION.md

---

## Pattern 2: Docker Container Port Auto-Detection

**Location**: `common/iris_dbapi_connector.py:13-48`

**The Pattern**:
```python
def auto_detect_iris_port():
    """
    Auto-detect running IRIS instance and its SuperServer port.

    Checks in priority order:
    1. Docker containers with IRIS (port 1972 mapped)
    2. Native IRIS instances via 'iris list' command

    Returns:
        int: SuperServer port of first accessible instance, or None if none found.
    """
    # Priority 1: Check for Docker IRIS containers
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Look for IRIS containers with port mappings
            for line in result.stdout.split('\n'):
                if 'iris' in line.lower() and '1972' in line:
                    # Parse port mapping like "0.0.0.0:1972->1972/tcp"
                    match = re.search(r'0\.0\.0\.0:(\d+)->1972/tcp', line)
                    if match:
                        port = int(match.group(1))
                        logger.info(f"✅ Auto-detected Docker IRIS on port {port}")
                        return port

    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("Docker not available, trying native IRIS")

    # Priority 2: Check native IRIS instances
    # [Native IRIS detection via 'iris list' command]
    ...
```

**Why It Works**:
- **Real container names** - searches for 'iris' in container name (catches iris_db, iris_db_rag_templates, etc.)
- **Regex port parsing** - extracts actual port mapping from Docker output
- **Native fallback** - checks `iris list` if Docker not available
- **Timeout protection** - won't hang on slow Docker

**Integration into iris-devtester**:
- Add to IRISContainer.get_config()
- Use in zero-config connections
- Document in "Zero Configuration Viable" principle

---

## Pattern 3: Connection Pooling for High-Throughput

**Location**: `common/iris_connection_pool.py:26-313`

**The Pattern**:
```python
class IRISConnectionPool:
    """
    Thread-safe connection pool for InterSystems IRIS.

    Features:
    - Thread-safe connection pool with min/max sizing
    - Automatic connection validation and refresh
    - Graceful degradation on pool exhaustion
    - Connection health checks
    - Pool statistics for monitoring
    """

    def __init__(
        self,
        min_size: int = 5,
        max_size: int = 20,
        connection_timeout: float = 30.0,
        validation_interval: int = 60,
        host: str = None,
        port: int = None,
        namespace: str = None,
        username: str = None,
        password: str = None
    ):
        self._pool = Queue(maxsize=max_size)
        self._active_connections = 0
        self._lock = threading.Lock()

        # Statistics
        self._stats = {
            "created": 0,
            "destroyed": 0,
            "hits": 0,
            "misses": 0,
            "timeouts": 0,
            "validation_failures": 0
        }

    @contextmanager
    def get_connection(self, timeout: float = None):
        """Get connection from pool with validation."""
        conn = None
        try:
            conn = self._pool.get(block=True, timeout=timeout)

            # Validate connection before use
            if not self._validate_connection(conn):
                self._destroy_connection(conn)
                conn = self._create_connection()

            yield conn
        finally:
            # Return to pool if valid
            if conn and self._validate_connection(conn):
                self._pool.put(conn, block=False)
            else:
                self._destroy_connection(conn)
```

**Why It Works**:
- **Production tested** - Eliminated 60s connection overhead in batch processing
- **Health checks** - Validates connections before use (SELECT 1)
- **Statistics** - Monitors pool performance (hits/misses/timeouts)
- **Thread-safe** - Uses threading.Lock() for concurrent access
- **Context manager** - Automatic cleanup via `with` statement

**Business Impact** (from rag-templates):
> "Implements connection pooling to eliminate the connection overhead observed in production (60s per 100-ticket batch from connection churn)."

**Integration into iris-devtester**:
- Add to `iris_devtester/connections/` as optional feature
- Document in performance guide
- Make available via `IRISContainer.get_pool()`

---

## Pattern 4: Automatic Password Reset with Retry

**Location**: `tests/utils/iris_password_reset.py:17-212`

**The Pattern**:
```python
class IRISPasswordResetHandler:
    """Handles automatic detection and remediation of IRIS password change requirements."""

    def detect_password_change_required(self, error_message: str) -> bool:
        """Detect if error is due to password change requirement."""
        password_change_indicators = [
            "Password change required",
            "password change required",
            "PASSWORD_CHANGE_REQUIRED",
            "User must change password",
        ]
        return any(indicator in error_message for indicator in password_change_indicators)

    def reset_iris_password(self, username: str = None, new_password: str = None):
        """Reset IRIS password using Docker exec."""
        # Check container is running
        check_cmd = ["docker", "ps", "--filter", f"name={self.container_name}"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)

        if self.container_name not in result.stdout:
            return False, f"Container {self.container_name} not running"

        # Reset via iris session
        reset_cmd = [
            "docker", "exec", "-i", self.container_name,
            "iris", "session", "IRIS", "-U", "%SYS",
            f"##class(Security.Users).ChangePassword('{username}','{new_password}')"
        ]

        result = subprocess.run(reset_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Update environment variables
            os.environ["IRIS_USERNAME"] = username
            os.environ["IRIS_PASSWORD"] = new_password
            time.sleep(2)  # Wait for password change to take effect
            return True, f"Password reset successful"

        # Fallback to SQL method
        alt_cmd = [
            "docker", "exec", "-i", self.container_name,
            "sh", "-c",
            f"echo \"ALTER USER {username} IDENTIFY BY '{new_password}'\" | iris sql IRIS -U %SYS"
        ]
        ...
```

**Why It Works**:
- **Multiple detection patterns** - Catches all password error variants
- **Primary + fallback** - ObjectScript method, then SQL fallback
- **Environment sync** - Updates os.environ after reset
- **Wait period** - Gives IRIS 2s to apply password change
- **Helpful error messages** - Includes manual steps if automation fails

**Integration into iris-devtester**:
- Already implemented in `iris_devtester/containers/iris_container.py:321-412`
- Matches Constitutional Principle #1 (Automatic Remediation)
- Keep existing implementation ✅

---

## Pattern 5: "Out of the Way" Port Mapping

**Location**: `docker-compose.yml:1-64`

**The Pattern**:
```yaml
# Docker Compose for RAG Templates IRIS Database
# Uses "out of the way" ports to avoid conflicts with existing IRIS installations
# IRIS standard ports: 1972 (SuperServer), 52773 (Management Portal)
# Mapped to: 11972 (SuperServer), 15273 (Management Portal)

services:
  iris_db:
    image: intersystemsdc/iris-community:latest
    container_name: iris_db_rag_templates
    ports:
      - "11972:1972"   # IRIS SuperServer port
      - "15273:52773"  # IRIS Management Portal
    environment:
      - IRISNAMESPACE=USER
      - ISC_DEFAULT_PASSWORD=SYS
    healthcheck:
      test: ["CMD", "/usr/irissys/bin/iris", "session", "iris", "-U%SYS",
             "##class(%SYSTEM.Process).CurrentDirectory()"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 60s
    # Disable password expiration for all accounts
    command: --check-caps false -a "iris session iris -U%SYS '##class(Security.Users).UnExpireUserPasswords(\"*\")'"

# PORT MAPPING STRATEGY:
# - Default IRIS:    11972 (SuperServer), 15273 (Portal)
# - Licensed IRIS:   21972 (SuperServer), 25273 (Portal)
# - Standard IRIS:    1972 (SuperServer), 52773 (Portal) - reserved for existing installations
```

**Why It Works**:
- **No conflicts** - 11972 instead of 1972 avoids conflict with native IRIS
- **Predictable** - Always same ports for same project
- **Documented** - Comments explain strategy
- **Password auto-fix** - UnExpireUserPasswords() prevents expiration issues
- **Healthcheck** - Ensures IRIS fully started before marking healthy

**Port Convention Pattern**:
```
Default Community:   11972, 15273
Licensed/Enterprise: 21972, 25273
Standard IRIS:        1972, 52773 (reserved, don't use)
Testcontainers:      31972, 35273 (random high ports)
```

**Integration into iris-devtester**:
- Document port conventions in README
- Use 31972+ for testcontainers (high ephemeral range)
- Add to auto-discovery pattern

---

## Pattern 6: Schema Reset Utilities

**Location**: `tests/integration/test_schema_reset_integration.py:23-52`

**The Pattern**:
```python
class TestSchemaResetIntegration:
    """Integration tests for schema reset operations."""

    def test_fresh_database_schema_creation(self):
        """
        Verify schema reset creates all required tables on fresh database.

        Given: IRIS database running, no RAG tables exist
        When: Schema reset executed
        Then: All 4 tables created
        """
        from tests.fixtures.schema_reset import SchemaResetter
        from common.iris_connection_manager import get_iris_connection

        resetter = SchemaResetter()
        resetter.reset_schema()

        # Verify all tables exist
        conn = get_iris_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'RAG'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['DocumentChunks', 'Entities', 'EntityRelationships', 'SourceDocuments']

        missing = set(expected_tables) - set(tables)

        assert not missing, (
            f"Missing tables after schema reset: {missing}.\n"
            f"Schema reset should create all required tables."
        )
```

**Why It Works**:
- **Idempotent** - Can be run multiple times safely
- **Verification** - Uses INFORMATION_SCHEMA to confirm creation
- **Clear errors** - Detailed assertion messages
- **Set operations** - Uses set difference to find missing tables

**Integration into iris-devtester**:
- Add to Phase 2.2 testing utilities
- Create `iris_devtester/testing/schema_reset.py`
- Implement pattern from PHASE_2_PLAN.md:326-351

---

## Pattern 7: Retry Logic with Exponential Backoff

**Location**: `common/iris_dbapi_connector.py:193-258`

**The Pattern**:
```python
def get_iris_dbapi_connection():
    """Establishes connection with retry logic."""
    max_retries = 3
    retry_delay = 0.5  # Start with 500ms delay

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                import time
                logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

            logger.info(f"Attempting IRIS connection to {host}:{port}/{namespace}")
            conn = iris.connect(host, port, namespace, user, password)

            # Validate connection
            if conn is None:
                logger.error("Connection is None")
                if attempt < max_retries - 1:
                    continue
                return None

            # Test with simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()

            if result is None:
                logger.error("Test query returned None")
                conn.close()
                if attempt < max_retries - 1:
                    continue
                return None

            logger.info("✅ Successfully connected to IRIS")
            return conn

        except Exception as e:
            logger.error(f"Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                continue
            return None

    return None
```

**Why It Works**:
- **Exponential backoff** - 0.5s, 1s, 2s delays prevent hammering
- **Validation** - Tests connection with SELECT 1 before returning
- **Logging** - Clear feedback on each retry attempt
- **Graceful failure** - Returns None instead of raising

**Integration into iris-devtester**:
- Already partially in IRISContainer.wait_for_ready()
- Add to get_connection() methods
- Document in reliability guide

---

## Summary: Patterns to Integrate

### High Priority (Phase 2)

1. ✅ **Automatic Password Reset** - Already implemented in IRISContainer
2. **Multi-Port Discovery** - Add to `iris_devtester/config/auto_discovery.py`
3. **Docker Port Auto-Detection** - Add to IRISContainer.from_existing()
4. **Schema Reset Utilities** - Add to Phase 2.2 testing utilities

### Medium Priority (Phase 3)

5. **Connection Pooling** - Add as optional advanced feature
6. **Retry with Backoff** - Enhance existing wait_for_ready()
7. **Port Convention Documentation** - Add to README/CONSTITUTION

### Low Priority (Post-v1.0.0)

8. **Global Connection Pool Singleton** - Advanced optimization
9. **Pool Statistics/Monitoring** - For production deployments

---

## Code Extraction Priority

**Immediate (Phase 2.1-2.2)**:
1. Extract schema reset pattern → `iris_devtester/testing/schema_reset.py`
2. Extract port discovery → `iris_devtester/config/auto_discovery.py`
3. Update integration test fixtures with port discovery

**Next (Phase 3)**:
4. Extract connection pool → `iris_devtester/connections/pool.py` (optional import)
5. Document port conventions → README.md
6. Add retry enhancements → IRISContainer methods

---

## References

- **Source**: `~/ws/rag-templates/`
- **Target**: `~/ws/iris-devtester/`
- **Constitutional Principles**: All 8 principles, especially #1 (Automatic Remediation) and #4 (Zero Config)
- **Related Docs**:
  - `docs/SQL_VS_OBJECTSCRIPT.md`
  - `docs/PHASE_2_PLAN.md`
  - `CONSTITUTION.md`
