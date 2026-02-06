"""IRIS Fixture Management.

This module provides tools for creating, loading, and validating IRIS database
fixtures. Fixtures enable fast, reproducible test data setup by exporting
database namespaces to version-controlled files.

Key Features:
- Create fixtures from IRIS namespaces (globals + class definitions)
- Load fixtures via global import (<1 second for most fixtures)
- Validate fixture integrity with SHA256 checksums
- CLI commands for fixture management

Fixture Format:
    Fixtures are stored as directories containing:
    - manifest.json: Metadata, checksums, and table information
    - globals.gof: Global data in IRIS %GOF format
    - classes.xml: Class definitions (optional, for SQL tables)

Example:
    >>> from iris_devtester.fixtures import FixtureLoader, FixtureCreator
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
    >>> loader = FixtureLoader(container=iris_container)
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
            loader = FixtureLoader(container=iris_container)
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

from .creator import FixtureCreator
from .loader import FixtureLoader

# Import data models and exceptions
from .manifest import (
    ChecksumMismatchError,
    FixtureCreateError,
    FixtureError,
    FixtureLoadError,
    FixtureManifest,
    FixtureValidationError,
    LoadResult,
    TableInfo,
    ValidationResult,
)

# Import $SYSTEM.OBJ export/import utilities
# Source: docs/learnings/iris-backup-patterns.md
from .obj_export import (
    ExportResult,
    ImportResult,
    export_classes,
    export_global,
    export_package,
    import_classes,
    import_global,
)

# Import validator, loader, and creator
from .validator import FixtureValidator

# Backward compatibility alias
DATFixtureLoader = FixtureLoader

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
    "FixtureLoader",
    "FixtureCreator",
    # Backward compatibility
    "DATFixtureLoader",
    # $SYSTEM.OBJ utilities (Feature 017)
    "ExportResult",
    "ImportResult",
    "export_classes",
    "import_classes",
    "export_global",
    "import_global",
    "export_package",
]
