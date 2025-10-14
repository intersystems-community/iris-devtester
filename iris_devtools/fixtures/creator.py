"""IRIS .DAT Fixture Creator.

This module provides the FixtureCreator class for creating IRIS database
fixtures by exporting namespaces using BACKUP^DBACK routine.
"""

import datetime
from pathlib import Path
from typing import Optional, Any, List, Dict

from iris_devtools.connections import get_connection
from iris_devtools.config import IRISConfig

from .manifest import (
    FixtureManifest,
    TableInfo,
    FixtureCreateError,
)
from .validator import FixtureValidator


class FixtureCreator:
    """
    Creates .DAT fixtures by exporting IRIS namespaces.

    This class creates database fixtures by:
    1. Exporting entire namespace to IRIS.DAT via BACKUP^DBACK
    2. Querying table list with row counts
    3. Calculating SHA256 checksum
    4. Generating manifest.json

    Example:
        >>> from iris_devtools.fixtures import FixtureCreator
        >>> creator = FixtureCreator()
        >>> manifest = creator.create_fixture(
        ...     fixture_id="test-data",
        ...     namespace="USER",
        ...     output_dir="./fixtures/test-data",
        ...     description="Test fixture with sample data"
        ... )
        >>> print(f"Created fixture with {len(manifest.tables)} tables")

    Constitutional Principle #2: DBAPI First
    Constitutional Principle #5: Fail Fast with Guidance
    Constitutional Principle #7: Medical-Grade Reliability
    """

    def __init__(self, connection_config: Optional[IRISConfig] = None):
        """
        Initialize fixture creator.

        Args:
            connection_config: Optional IRIS connection configuration.
                              If None, auto-discovers from environment.

        Example:
            >>> # Auto-discover connection
            >>> creator = FixtureCreator()

            >>> # Explicit config
            >>> from iris_devtools.config import IRISConfig
            >>> config = IRISConfig(host="localhost", port=1972)
            >>> creator = FixtureCreator(config)
        """
        self.connection_config = connection_config
        self.validator = FixtureValidator()
        self._connection: Optional[Any] = None

    def create_fixture(
        self,
        fixture_id: str,
        namespace: str,
        output_dir: str,
        description: str = "",
        version: str = "1.0.0",
        features: Optional[Dict[str, Any]] = None,
    ) -> FixtureManifest:
        """
        Create fixture by exporting IRIS namespace.

        Steps:
        1. Verify namespace exists
        2. Create output directory
        3. Export namespace to IRIS.DAT via BACKUP^DBACK
        4. Query table list with row counts
        5. Calculate SHA256 checksum
        6. Generate and save manifest.json

        Args:
            fixture_id: Unique identifier (e.g., "test-entities-100")
            namespace: Source namespace to export (e.g., "USER", "USER_TEST_100")
            output_dir: Output directory path (will be created if doesn't exist)
            description: Human-readable description
            version: Semantic version (default: "1.0.0")
            features: Optional custom metadata

        Returns:
            FixtureManifest with complete fixture metadata

        Raises:
            FileExistsError: If output directory already exists
            FixtureCreateError: If creation fails (with remediation guidance)

        Example:
            >>> creator = FixtureCreator()
            >>> manifest = creator.create_fixture(
            ...     fixture_id="test-entities-100",
            ...     namespace="USER_TEST_100",
            ...     output_dir="./fixtures/test-entities-100",
            ...     description="Test data with 100 RAG entities"
            ... )
        """
        output_path = Path(output_dir)

        # Check if output directory already exists
        if output_path.exists():
            raise FileExistsError(
                f"Fixture directory already exists: {output_dir}\n"
                "\n"
                "What went wrong:\n"
                "  Cannot overwrite existing fixture for safety.\n"
                "\n"
                "How to fix it:\n"
                f"  1. Delete existing fixture: rm -rf {output_dir}\n"
                "  2. Choose different output path\n"
                "  3. Use refresh_fixture() to update existing fixture\n"
            )

        # Create output directory
        try:
            output_path.mkdir(parents=True, exist_ok=False)
        except Exception as e:
            raise FixtureCreateError(
                f"Failed to create output directory: {output_dir}\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  Could not create fixture directory.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check directory permissions\n"
                "  2. Verify parent directory exists\n"
                "  3. Check disk space: df -h\n"
            )

        # Export namespace to IRIS.DAT
        dat_file_path = output_path / "IRIS.DAT"
        try:
            self.export_namespace_to_dat(namespace, str(dat_file_path))
        except Exception as e:
            # Cleanup on failure
            try:
                output_path.rmdir()
            except:
                pass
            raise

        # Get IRIS version
        iris_version = self._get_iris_version()

        # Get table list with row counts
        tables = self.get_namespace_tables(namespace)

        # Calculate checksum
        checksum = self.calculate_checksum(str(dat_file_path))

        # Create manifest
        manifest = FixtureManifest(
            fixture_id=fixture_id,
            version=version,
            schema_version="1.0",
            description=description,
            created_at=datetime.datetime.utcnow().isoformat() + "Z",
            iris_version=iris_version,
            namespace=namespace,
            dat_file="IRIS.DAT",
            checksum=checksum,
            tables=tables,
            features=features,
        )

        # Save manifest
        manifest_path = output_path / "manifest.json"
        manifest.to_file(str(manifest_path))

        return manifest

    def export_namespace_to_dat(self, namespace: str, dat_file_path: str) -> str:
        """
        Export IRIS namespace to IRIS.DAT file.

        Uses IRIS BACKUP^DBACK routine to create database backup.

        Args:
            namespace: Source namespace to backup (e.g., "USER_TEST_100")
            dat_file_path: Output path for IRIS.DAT file

        Returns:
            Path to created IRIS.DAT file

        Raises:
            FixtureCreateError: If backup fails

        Example:
            >>> creator = FixtureCreator()
            >>> dat_file = creator.export_namespace_to_dat(
            ...     "USER_TEST_100",
            ...     "./fixtures/test-100/IRIS.DAT"
            ... )
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Verify namespace exists
            cursor.execute(
                f"SELECT COUNT(*) FROM SYS.Namespace WHERE Name = '{namespace}'"
            )
            ns_count = cursor.fetchone()[0]

            if ns_count == 0:
                raise FixtureCreateError(
                    f"Namespace '{namespace}' does not exist\n"
                    "\n"
                    "What went wrong:\n"
                    "  Cannot export non-existent namespace.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. List available namespaces: do $SYSTEM.OBJ.ListNamespaces()\n"
                    "  2. Create namespace if needed\n"
                    "  3. Verify namespace name spelling\n"
                )

            # Execute BACKUP via ObjectScript
            # Use ##class(SYS.Database).BackupNamespace()
            backup_command = f"""
                set sc = ##class(SYS.Database).BackupNamespace(
                    "{namespace}",
                    "{dat_file_path}",
                    ,  // Skip journal files
                    ,  // Include all databases
                    1  // Overwrite existing file
                )
                if sc {{
                    write "SUCCESS"
                }} else {{
                    write "FAILED: "_$system.Status.GetErrorText(sc)
                }}
            """

            cursor.execute(f"SELECT $SYSTEM.OBJ.Execute('{backup_command}')")
            result_row = cursor.fetchone()

            if not result_row or "SUCCESS" not in str(result_row[0]):
                error_msg = str(result_row[0]) if result_row else "Unknown error"
                raise FixtureCreateError(
                    f"Failed to backup namespace '{namespace}'\n"
                    f"Error: {error_msg}\n"
                    "\n"
                    "What went wrong:\n"
                    "  The database backup operation failed.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Check user has BACKUP permission\n"
                    "  2. Verify disk space: df -h\n"
                    "  3. Check IRIS logs for detailed error\n"
                    "  4. Try manual backup via Management Portal\n"
                )

            cursor.close()

            # Verify file was created
            if not Path(dat_file_path).exists():
                raise FixtureCreateError(
                    f"Backup completed but IRIS.DAT not found: {dat_file_path}\n"
                    "\n"
                    "What went wrong:\n"
                    "  IRIS reported success but file not created.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Check IRIS version compatibility\n"
                    "  2. Verify file path is writable\n"
                    "  3. Review IRIS logs\n"
                )

            return dat_file_path

        except Exception as e:
            if isinstance(e, FixtureCreateError):
                raise
            raise FixtureCreateError(
                f"Failed to export namespace '{namespace}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  An error occurred during namespace backup.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify IRIS is running\n"
                "  2. Check connection: iris-devtools connection test\n"
                "  3. Review IRIS logs for errors\n"
                "  4. Try listing namespaces: do $SYSTEM.OBJ.ListNamespaces()\n"
            )

    def calculate_checksum(self, dat_file_path: str) -> str:
        """
        Calculate SHA256 checksum for .DAT file.

        Args:
            dat_file_path: Path to .DAT file

        Returns:
            SHA256 checksum (format: "sha256:abc123...")

        Raises:
            FileNotFoundError: If .DAT file doesn't exist

        Example:
            >>> creator = FixtureCreator()
            >>> checksum = creator.calculate_checksum("./fixtures/test/IRIS.DAT")
            >>> print(f"Checksum: {checksum}")
        """
        return self.validator.calculate_sha256(dat_file_path)

    def get_namespace_tables(self, namespace: str) -> List[TableInfo]:
        """
        Get list of tables in namespace with row counts.

        Args:
            namespace: Namespace to inspect

        Returns:
            List of TableInfo objects with names and row counts

        Raises:
            FixtureCreateError: If namespace doesn't exist or query fails

        Example:
            >>> creator = FixtureCreator()
            >>> tables = creator.get_namespace_tables("USER_TEST_100")
            >>> for table in tables:
            ...     print(f"{table.name}: {table.row_count} rows")
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Switch to namespace
            cursor.execute(f"SET NAMESPACE {namespace}")

            # Query for all tables
            cursor.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )

            tables = []
            for row in cursor.fetchall():
                schema_name = row[0]
                table_name = row[1]
                qualified_name = f"{schema_name}.{table_name}"

                # Get row count
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {qualified_name}")
                    row_count = cursor.fetchone()[0]

                    tables.append(TableInfo(name=qualified_name, row_count=row_count))
                except Exception as table_error:
                    # Skip tables we can't count (permissions, corrupted, etc.)
                    # Log warning but continue
                    continue

            cursor.close()
            return tables

        except Exception as e:
            raise FixtureCreateError(
                f"Failed to query tables in namespace '{namespace}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  Could not retrieve table list from namespace.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify namespace exists: do $SYSTEM.OBJ.ListNamespaces()\n"
                "  2. Check user has SELECT permission\n"
                "  3. Try querying tables manually: SELECT * FROM INFORMATION_SCHEMA.TABLES\n"
            )

    def refresh_fixture(self, fixture_dir: str, namespace: str) -> FixtureManifest:
        """
        Refresh existing fixture by re-exporting namespace.

        This updates the IRIS.DAT file, recalculates checksum, and updates manifest.

        Args:
            fixture_dir: Path to existing fixture directory
            namespace: Source namespace to re-export

        Returns:
            Updated FixtureManifest

        Raises:
            FileNotFoundError: If fixture directory doesn't exist
            FixtureCreateError: If refresh fails

        Example:
            >>> creator = FixtureCreator()
            >>> manifest = creator.refresh_fixture(
            ...     "./fixtures/test-100",
            ...     namespace="USER_TEST_100"
            ... )
            >>> print(f"Refreshed, new checksum: {manifest.checksum}")
        """
        fixture_path = Path(fixture_dir)

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Fixture directory not found: {fixture_dir}\n"
                "\n"
                "What went wrong:\n"
                "  Cannot refresh non-existent fixture.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify fixture path is correct\n"
                "  2. Use create_fixture() for new fixtures\n"
            )

        manifest_file = fixture_path / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"Manifest not found: {manifest_file}\n"
                "\n"
                "What went wrong:\n"
                "  Fixture directory exists but manifest.json is missing.\n"
                "\n"
                "How to fix it:\n"
                "  1. Re-create fixture: use create_fixture()\n"
                "  2. Restore manifest.json from backup\n"
            )

        # Load existing manifest
        manifest = FixtureManifest.from_file(str(manifest_file))

        # Create backup of old manifest
        backup_file = fixture_path / "manifest.json.backup"
        manifest.to_file(str(backup_file))

        # Re-export namespace to IRIS.DAT
        dat_file_path = fixture_path / manifest.dat_file
        try:
            # Remove old .DAT file
            if dat_file_path.exists():
                dat_file_path.unlink()

            # Export new .DAT file
            self.export_namespace_to_dat(namespace, str(dat_file_path))

            # Get updated table list
            tables = self.get_namespace_tables(namespace)

            # Recalculate checksum
            checksum = self.calculate_checksum(str(dat_file_path))

            # Update manifest
            manifest.tables = tables
            manifest.checksum = checksum
            manifest.created_at = datetime.datetime.utcnow().isoformat() + "Z"
            manifest.iris_version = self._get_iris_version()

            # Save updated manifest
            manifest.to_file(str(manifest_file))

            return manifest

        except Exception as e:
            # Restore backup on failure
            if backup_file.exists():
                manifest_backup = FixtureManifest.from_file(str(backup_file))
                manifest_backup.to_file(str(manifest_file))

            if isinstance(e, FixtureCreateError):
                raise
            raise FixtureCreateError(
                f"Failed to refresh fixture '{manifest.fixture_id}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  Could not re-export namespace to update fixture.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify namespace still exists\n"
                "  2. Check IRIS connection\n"
                "  3. Review previous manifest backup: manifest.json.backup\n"
            )

    def get_connection(self) -> Any:
        """
        Get or create IRIS connection.

        Returns:
            IRIS database connection (DBAPI)

        Raises:
            ConnectionError: If connection fails

        Example:
            >>> creator = FixtureCreator()
            >>> conn = creator.get_connection()
            >>> cursor = conn.cursor()
        """
        if self._connection is None:
            self._connection = get_connection(self.connection_config)
        return self._connection

    def _get_iris_version(self) -> str:
        """
        Get IRIS version from system.

        Returns:
            IRIS version string (e.g., "2024.1")
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT $SYSTEM.Version.GetVersion()")
            row = cursor.fetchone()
            cursor.close()
            if row and row[0]:
                return str(row[0])
            return "unknown"
        except Exception:
            return "unknown"
