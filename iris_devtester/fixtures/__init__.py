"""IRIS .DAT Fixture Management.

This module provides tools for creating, loading, and validating IRIS database
fixtures stored as .DAT files. Fixtures enable fast, reproducible test data
setup by exporting database namespaces to version-controlled files.

Key Features:
- Create fixtures from IRIS namespaces (entire database backup)
- Load fixtures via namespace mounting (<1 second)
- Validate fixture integrity with SHA256 checksums
- CLI commands for fixture management

Example:
    >>> from iris_devtester.fixtures import DATFixtureLoader, FixtureCreator
    >>>
    >>> # Create fixture from existing namespace
    >>> creator = FixtureCreator(container=iris_container)
    >>> manifest = creator.create_fixture(
    ...     fixture_id="test-data",
    ...     namespace="TEST",
    ...     output_dir="./fixtures/test-data"
    ... )
    >>>
    >>> # Load fixture into new namespace
    >>> loader = DATFixtureLoader(container=iris_container)
    >>> target_ns = iris_container.get_test_namespace(prefix="LOADED")
    >>> result = loader.load_fixture(
    ...     fixture_path="./fixtures/test-data",
    ...     target_namespace=target_ns
    ... )
    >>> print(f"Loaded {len(result.tables_loaded)} tables")

pytest Integration:
    Use fixtures directly in pytest tests:

        @pytest.fixture
        def loaded_fixture(iris_container):
            loader = DATFixtureLoader(container=iris_container)
            target_ns = iris_container.get_test_namespace(prefix="TEST")
            result = loader.load_fixture(
                fixture_path="./fixtures/test-data",
                target_namespace=target_ns
            )
            yield result
            # Cleanup
            loader.cleanup_fixture(target_ns, delete_namespace=True)

        def test_with_fixture(loaded_fixture):
            assert loaded_fixture.success
            assert len(loaded_fixture.tables_loaded) > 0
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

# Import $SYSTEM.OBJ export/import utilities
# Source: docs/learnings/iris-backup-patterns.md
from .obj_export import (
    ExportResult,
    ImportResult,
    export_classes,
    import_classes,
    export_global,
    import_global,
    export_package,
)

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
    # $SYSTEM.OBJ utilities (Feature 017)
    "ExportResult",
    "ImportResult",
    "export_classes",
    "import_classes",
    "export_global",
    "import_global",
    "export_package",
]
