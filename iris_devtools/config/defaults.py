"""
Default configuration values.

These defaults enable zero-configuration usage while remaining
overridable via environment variables or explicit configuration.

All defaults are based on:
- IRIS Community Edition standard installation
- Docker container defaults (intersystemsdc/iris-community)
- Common development scenarios
"""

# Connection defaults
DEFAULT_HOST = "localhost"
"""Default IRIS host (localhost for local development)"""

DEFAULT_PORT = 1972
"""Default IRIS superserver port (1972 is standard IRIS port)"""

DEFAULT_NAMESPACE = "USER"
"""Default IRIS namespace (USER is the default workspace)"""

DEFAULT_USERNAME = "SuperUser"
"""Default IRIS username (SuperUser has full access)"""

DEFAULT_PASSWORD = "SYS"
"""Default IRIS password (SYS is the default for containers)"""

DEFAULT_DRIVER = "auto"
"""
Default driver selection (auto tries DBAPI first, falls back to JDBC).

Options:
- "auto": Try DBAPI first, fall back to JDBC (recommended)
- "dbapi": Use DBAPI only (fastest, 3x faster than JDBC)
- "jdbc": Use JDBC only (most compatible, works everywhere)
"""

DEFAULT_TIMEOUT = 30
"""
Default connection timeout in seconds.

Recommended values:
- 30s: Default, works for most cases
- 60s: Slow networks or remote connections
- 5s: Fast fail for availability checks
"""

# Why these defaults?
#
# These defaults follow the "Zero Configuration Viable" principle
# (CONSTITUTION.md Principle #4). They are chosen to work with:
#
# 1. IRIS Community Edition containers (most common dev setup)
# 2. Standard IRIS installations (port 1972, USER namespace)
# 3. Docker Compose setups (localhost, default credentials)
#
# Users can override any default via:
# - Environment variables (IRIS_HOST, IRIS_PORT, etc.)
# - .env file
# - Explicit IRISConfig parameters
#
# See docs/learnings/ for why these specific values were chosen.
