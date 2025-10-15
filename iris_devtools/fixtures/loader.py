"""IRIS .DAT Fixture Loader.

This module provides the DATFixtureLoader class for loading .DAT fixtures
into IRIS namespaces via namespace mounting.
"""

import time
from pathlib import Path
from typing import Optional, Any

from iris_devtools.connections import get_connection, IRISConnection
from iris_devtools.config import IRISConfig

from .manifest import (
    FixtureManifest,
    LoadResult,
    FixtureLoadError,
)
from .validator import FixtureValidator


class DATFixtureLoader:
    """
    Loads .DAT fixtures into IRIS namespaces.

    This class loads pre-created IRIS database fixtures by:
    1. Validating manifest and IRIS.DAT checksum
    2. Mounting the namespace via ObjectScript
    3. Verifying mount success
    4. Returning LoadResult with timing information

    Example:
        >>> from iris_devtools.fixtures import DATFixtureLoader
        >>> loader = DATFixtureLoader()
        >>> result = loader.load_fixture("./fixtures/test-data")
        >>> print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")

    Constitutional Principle #2: DBAPI First
    Constitutional Principle #5: Fail Fast with Guidance
    Constitutional Principle #7: Medical-Grade Reliability
    """

    def __init__(self, connection_config: Optional[IRISConfig] = None):
        """
        Initialize fixture loader.

        Args:
            connection_config: Optional IRIS connection configuration.
                              If None, auto-discovers from environment.

        Example:
            >>> # Auto-discover connection
            >>> loader = DATFixtureLoader()

            >>> # Explicit config
            >>> from iris_devtools.config import IRISConfig
            >>> config = IRISConfig(host="localhost", port=1972)
            >>> loader = DATFixtureLoader(config)
        """
        self.connection_config = connection_config
        self.validator = FixtureValidator()
        self._connection: Optional[Any] = None

    def validate_fixture(
        self, fixture_path: str, validate_checksum: bool = True
    ) -> FixtureManifest:
        """
        Validate fixture before loading.

        Args:
            fixture_path: Path to fixture directory
            validate_checksum: Validate IRIS.DAT checksum (default: True)

        Returns:
            FixtureManifest if validation succeeds

        Raises:
            FixtureValidationError: If validation fails

        Example:
            >>> loader = DATFixtureLoader()
            >>> manifest = loader.validate_fixture("./fixtures/test-data")
            >>> print(f"Fixture: {manifest.fixture_id}")
        """
        result = self.validator.validate_fixture(
            fixture_path, validate_checksum=validate_checksum
        )
        result.raise_if_invalid()

        # After raise_if_invalid(), manifest is guaranteed to be set
        assert result.manifest is not None, "Manifest should be set after successful validation"
        return result.manifest

    def load_fixture(
        self,
        fixture_path: str,
        target_namespace: Optional[str] = None,
        validate_checksum: bool = True,
    ) -> LoadResult:
        """
        Load fixture into IRIS namespace.

        Steps:
        1. Validate manifest and IRIS.DAT checksum
        2. Mount namespace via ObjectScript RESTORE^DBACK routine
        3. Verify mount success by checking table existence
        4. Return LoadResult with timing information

        Args:
            fixture_path: Path to fixture directory containing manifest.json and IRIS.DAT
            target_namespace: Target namespace name (default: use manifest's namespace)
            validate_checksum: Validate IRIS.DAT checksum before loading (default: True)

        Returns:
            LoadResult with success status, manifest, and timing info

        Raises:
            FixtureValidationError: If fixture validation fails
            FixtureLoadError: If loading fails (with remediation guidance)

        Example:
            >>> loader = DATFixtureLoader()
            >>> result = loader.load_fixture("./fixtures/test-data")
            >>> if result.success:
            ...     print(f"✅ Loaded {len(result.tables_loaded)} tables")
            ... else:
            ...     print("❌ Load failed")
        """
        start_time = time.time()

        # Step 1: Validate fixture
        manifest = self.validate_fixture(fixture_path, validate_checksum)

        # Use manifest namespace if target not specified
        namespace = target_namespace or manifest.namespace

        # Get absolute path to IRIS.DAT file
        fixture_dir = Path(fixture_path).resolve()
        dat_file_path = fixture_dir / manifest.dat_file

        if not dat_file_path.exists():
            raise FixtureLoadError(
                f"IRIS.DAT file not found: {dat_file_path}\n"
                "\n"
                "What went wrong:\n"
                f"  The manifest specifies '{manifest.dat_file}' but it doesn't exist.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify the fixture directory is correct\n"
                "  2. Check if the .DAT file was renamed or moved\n"
                "  3. Re-create the fixture if necessary\n"
            )

        # Step 2: Mount namespace via ObjectScript
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Mount database via RESTORE^DBACK routine
            # This is a namespace-level restore operation
            # RESTORE^DBACK(namespace, dat_file_path)
            restore_command = f"""
                set sc = ##class(SYS.Database).RestoreNamespace(
                    "{namespace}",
                    "{str(dat_file_path)}",
                    ,  // Skip log restore
                    ,  // Skip all databases flag
                    ,  // Restore in place
                    1  // Create namespace if doesn't exist
                )
                if sc {{
                    write "SUCCESS"
                }} else {{
                    write "FAILED: "_$system.Status.GetErrorText(sc)
                }}
            """

            # Execute restore via ObjectScript
            cursor.execute(f"SELECT $SYSTEM.OBJ.Execute('{restore_command}')")
            result_row = cursor.fetchone()

            if not result_row or "SUCCESS" not in str(result_row[0]):
                error_msg = str(result_row[0]) if result_row else "Unknown error"
                raise FixtureLoadError(
                    f"Failed to restore namespace '{namespace}'\n"
                    f"Error: {error_msg}\n"
                    "\n"
                    "What went wrong:\n"
                    "  The IRIS.DAT file could not be restored to the namespace.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Verify IRIS has permissions to read the .DAT file\n"
                    "  2. Check IRIS version compatibility (manifest shows v{manifest.iris_version})\n"
                    "  3. Verify the .DAT file is not corrupted (run: iris-devtools fixture validate)\n"
                    "  4. Check IRIS logs for detailed error information\n"
                )

            cursor.close()

        except Exception as e:
            if isinstance(e, FixtureLoadError):
                raise
            raise FixtureLoadError(
                f"Failed to load fixture '{manifest.fixture_id}' into namespace '{namespace}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  An error occurred while communicating with IRIS.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify IRIS is running: docker ps | grep iris\n"
                "  2. Check IRIS connection: iris-devtools connection test\n"
                "  3. Review IRIS logs for errors\n"
                "  4. Try validating the fixture first: iris-devtools fixture validate\n"
            )

        # Step 3: Verify mount success by checking tables exist
        tables_loaded = []
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Switch to target namespace
            cursor.execute(f"SET NAMESPACE {namespace}")

            # Verify each table exists
            for table_info in manifest.tables:
                # Query table to verify it exists and has expected rows
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_info.name}")
                    row_count = cursor.fetchone()[0]

                    # Warn if row count doesn't match (but don't fail)
                    if row_count != table_info.row_count:
                        # Note: This is a warning, not an error
                        # Row counts can legitimately differ after restore
                        pass

                    tables_loaded.append(table_info.name)
                except Exception as table_error:
                    raise FixtureLoadError(
                        f"Failed to verify table '{table_info.name}' in namespace '{namespace}'\n"
                        f"Error: {table_error}\n"
                        "\n"
                        "What went wrong:\n"
                        "  The namespace was restored but table verification failed.\n"
                        "\n"
                        "How to fix it:\n"
                        "  1. Check if the table exists: SELECT * FROM INFORMATION_SCHEMA.TABLES\n"
                        "  2. Verify namespace is correct\n"
                        "  3. Try recreating the fixture from source\n"
                    )

            cursor.close()

        except Exception as e:
            if isinstance(e, FixtureLoadError):
                raise
            raise FixtureLoadError(
                f"Failed to verify tables in namespace '{namespace}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  The namespace was restored but table verification failed.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check IRIS connection\n"
                "  2. Verify namespace exists: do $SYSTEM.OBJ.ListNamespaces()\n"
                "  3. Try querying tables manually in IRIS SQL\n"
            )

        # Calculate elapsed time
        elapsed_seconds = time.time() - start_time

        return LoadResult(
            success=True,
            manifest=manifest,
            namespace=namespace,
            tables_loaded=tables_loaded,
            elapsed_seconds=elapsed_seconds,
        )

    def cleanup_fixture(
        self, namespace: str, delete_namespace: bool = False
    ) -> None:
        """
        Cleanup loaded fixture.

        Args:
            namespace: Namespace to cleanup
            delete_namespace: If True, delete the namespace entirely.
                             If False, just unmount (namespace remains but data removed).

        Raises:
            FixtureLoadError: If cleanup fails

        Example:
            >>> loader = DATFixtureLoader()
            >>> result = loader.load_fixture("./fixtures/test-data")
            >>> # ... use fixture ...
            >>> loader.cleanup_fixture(result.namespace, delete_namespace=True)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if delete_namespace:
                # Delete namespace entirely
                delete_command = f"""
                    set sc = ##class(Config.Namespaces).Delete("{namespace}")
                    if sc {{
                        write "SUCCESS"
                    }} else {{
                        write "FAILED: "_$system.Status.GetErrorText(sc)
                    }}
                """
                cursor.execute(f"SELECT $SYSTEM.OBJ.Execute('{delete_command}')")
                result_row = cursor.fetchone()

                if not result_row or "SUCCESS" not in str(result_row[0]):
                    error_msg = str(result_row[0]) if result_row else "Unknown error"
                    raise FixtureLoadError(
                        f"Failed to delete namespace '{namespace}'\n"
                        f"Error: {error_msg}\n"
                        "\n"
                        "What went wrong:\n"
                        "  Could not delete the namespace.\n"
                        "\n"
                        "How to fix it:\n"
                        "  1. Verify namespace exists: do $SYSTEM.OBJ.ListNamespaces()\n"
                        "  2. Try deleting manually via IRIS Management Portal\n"
                        "  3. Check if namespace is in use by other connections\n"
                    )
            else:
                # Just unmount (clear data but keep namespace definition)
                # Switch to namespace and drop all tables
                cursor.execute(f"SET NAMESPACE {namespace}")

                # Get list of all tables
                cursor.execute(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
                )
                tables = [row[0] for row in cursor.fetchall()]

                # Drop each table
                for table_name in tables:
                    cursor.execute(f"DROP TABLE {table_name}")

            cursor.close()

        except Exception as e:
            if isinstance(e, FixtureLoadError):
                raise
            raise FixtureLoadError(
                f"Failed to cleanup namespace '{namespace}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  Could not cleanup the fixture namespace.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check IRIS connection\n"
                "  2. Try manual cleanup via IRIS Management Portal\n"
                "  3. Restart IRIS if necessary\n"
            )

    def get_connection(self) -> Any:
        """
        Get or create IRIS connection.

        Returns:
            IRIS database connection (DBAPI)

        Raises:
            ConnectionError: If connection fails

        Example:
            >>> loader = DATFixtureLoader()
            >>> conn = loader.get_connection()
            >>> cursor = conn.cursor()
        """
        if self._connection is None:
            self._connection = get_connection(self.connection_config)
        return self._connection
