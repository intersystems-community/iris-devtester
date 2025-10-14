"""IRIS .DAT Fixture Management.

This module provides tools for creating, loading, and validating IRIS database
fixtures stored as .DAT files. Fixtures enable fast, reproducible test data
setup by exporting database namespaces to version-controlled files.

Key Features:
- Create fixtures from IRIS namespaces (entire database backup)
- Load fixtures via namespace mounting (<1 second)
- Validate fixture integrity with SHA256 checksums
- pytest integration with @pytest.mark.dat_fixture decorator
- CLI commands for fixture management

Example:
    >>> from iris_devtools.fixtures import DATFixtureLoader
    >>> loader = DATFixtureLoader()
    >>> result = loader.load_fixture("./fixtures/test-data")
    >>> print(f"Loaded {len(result.tables_loaded)} tables")

pytest Integration:
    Configure in conftest.py:
        pytest_plugins = ["iris_devtools.fixtures.pytest_plugin"]

    Use in tests:
        @pytest.mark.dat_fixture("./fixtures/test-data")
        def test_with_fixture(dat_fixture_connection):
            cursor = dat_fixture_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
            assert cursor.fetchone()[0] > 0
"""

__version__ = "0.1.0"

# Import data models and exceptions
from .manifest import (
    FixtureManifest,
    TableInfo,
    ValidationResult,
    LoadResult,
    FixtureError,
    FixtureValidationError,
    FixtureLoadError,
    FixtureCreateError,
    ChecksumMismatchError,
)

# Import validator, loader, and creator
from .validator import FixtureValidator
from .loader import DATFixtureLoader
from .creator import FixtureCreator

# pytest plugin is auto-registered when imported
# Users configure it in conftest.py or pytest.ini:
#   pytest_plugins = ["iris_devtools.fixtures.pytest_plugin"]

# Public API
__all__ = [
    # Data models
    "FixtureManifest",
    "TableInfo",
    "ValidationResult",
    "LoadResult",
    # Exceptions
    "FixtureError",
    "FixtureValidationError",
    "FixtureLoadError",
    "FixtureCreateError",
    "ChecksumMismatchError",
    # Classes
    "FixtureValidator",
    "DATFixtureLoader",
    "FixtureCreator",
]
