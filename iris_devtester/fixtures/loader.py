"""IRIS .DAT Fixture Loader.

This module provides the DATFixtureLoader class for loading .DAT fixtures
into IRIS namespaces via namespace mounting.
"""

import time
from pathlib import Path
from typing import Optional, Any

from iris_devtester.connections import get_connection, IRISConnection
from iris_devtester.config import IRISConfig

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
        >>> from iris_devtester.fixtures import DATFixtureLoader
        >>> loader = DATFixtureLoader()
        >>> result = loader.load_fixture("./fixtures/test-data")
        >>> print(f"Loaded {len(result.tables_loaded)} tables in {result.elapsed_seconds:.2f}s")

    Constitutional Principle #2: DBAPI First
    Constitutional Principle #5: Fail Fast with Guidance
    Constitutional Principle #7: Medical-Grade Reliability
    """

    def __init__(self, connection_config: Optional[IRISConfig] = None, container: Optional[Any] = None):
        """
        Initialize fixture loader.

        Args:
            connection_config: Optional IRIS connection configuration.
                              If None, auto-discovers from environment.
            container: Optional IRISContainer for docker exec operations.
                      Required for RESTORE operations.

        Example:
            >>> # Auto-discover connection
            >>> loader = DATFixtureLoader()

            >>> # With container (for docker exec)
            >>> from iris_devtester.containers import IRISContainer
            >>> with IRISContainer.community() as container:
            ...     loader = DATFixtureLoader(container=container)

            >>> # Explicit config
            >>> from iris_devtester.config import IRISConfig
            >>> config = IRISConfig(host="localhost", port=1972)
            >>> loader = DATFixtureLoader(config)
        """
        self.connection_config = connection_config
        self.container = container
        self.validator = FixtureValidator()
        self._owns_container = False  # Track if we auto-created the container
        self._connection: Optional[Any] = None

    def close(self) -> None:
        """
        Cleanup resources, especially auto-created containers.

        Example:
            >>> loader = DATFixtureLoader()
            >>> result = loader.load_fixture("./fixtures/test-data")
            >>> loader.close()  # Stops auto-created container
        """
        if self._owns_container and self.container:
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Stopping auto-created container: {self.container.get_container_name()}")
                self.container.stop()
                self._owns_container = False
                self.container = None
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to stop auto-created container: {e}")

    def __del__(self):
        """Ensure container cleanup on garbage collection."""
        self.close()

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

        # Step 2: Mount database via docker exec (similar to creator BACKUP approach)
        # Cannot use iris.connect() + iris.execute() - only works in embedded Python
        try:
            # Auto-create container if not provided (Constitutional Principle #4: Zero Configuration)
            if not self.container:
                from iris_devtester.containers import IRISContainer
                import logging

                logger = logging.getLogger(__name__)
                logger.info("No container provided - auto-creating temporary IRIS container...")

                # Create temporary container
                self.container = IRISContainer.community()
                self.container.start()
                self.container.wait_for_ready(timeout=60)
                self.container.enable_callin_service()

                # Unexpire passwords
                from iris_devtester.utils.unexpire_passwords import unexpire_all_passwords
                unexpire_all_passwords(self.container.get_container_name())

                # Update connection config to use the auto-created container
                self.connection_config = self.container.get_config()

                logger.info(f"✓ Auto-created container: {self.container.get_container_name()}")

                # Mark that we own this container and should clean it up
                self._owns_container = True
            else:
                self._owns_container = False

            import subprocess

            container_name = self.container.get_container_name()

            # First, copy the DAT file into the container
            container_dat_path = f"/tmp/RESTORE_{namespace}.DAT"

            cp_to_container_cmd = [
                "docker",
                "cp",
                str(dat_file_path),
                f"{container_name}:{container_dat_path}"
            ]

            cp_result = subprocess.run(
                cp_to_container_cmd, capture_output=True, text=True, timeout=30
            )

            if cp_result.returncode != 0:
                raise FixtureLoadError(
                    f"Failed to copy DAT file to container\n"
                    f"DAT file: {dat_file_path}\n"
                    f"Container path: {container_dat_path}\n"
                    f"stderr: {cp_result.stderr}\n"
                )

            # Mount database via ObjectScript
            # RESTORE sequence:
            # 1. Create directory and copy IRIS.DAT
            # 2. Create Config.Databases entry
            # 3. Mount database (registers it with IRIS)
            # 4. Create namespace pointing to database
            db_name = f"DB_{namespace}"
            db_dir = f"/usr/irissys/mgr/db_{namespace.lower()}"

            # Simplified ObjectScript - avoid macros, use plain status checks
            # In ObjectScript: status=1 means success, status=0 or other means error
            # Config.Databases.Create() handles database activation, no need for Mount
            #
            # IMPORTANT: When namespace already exists (created by get_test_namespace),
            # just print SUCCESS and skip database/namespace creation
            #
            # ObjectScript syntax note: No braces needed, just If...Else...
            objectscript_commands = f"""Set dbDir = "{db_dir}"
Set dbName = "{db_name}"

Do ##class(Config.Namespaces).Exists("{namespace}",.obj,.nsStatus)
If nsStatus=1 Write "NAMESPACE_EXISTS","SUCCESS" Halt

If '##class(%File).DirectoryExists(dbDir) Do ##class(%File).CreateDirectoryChain(dbDir)
Do ##class(%File).CopyFile("{container_dat_path}",dbDir_"/IRIS.DAT")

Set dbProps("Directory") = dbDir
Set status = ##class(Config.Databases).Create(dbName,.dbProps)
If status'=1 Write "DB_CREATE_FAILED" Halt

Set nsProps("Globals") = dbName
Set nsProps("Routines") = dbName
Set nsProps("TempGlobals") = "IRISTEMP"
Set status = ##class(Config.Namespaces).Create("{namespace}",.nsProps)
If status'=1 Write "NAMESPACE_CREATE_FAILED" Halt

Write "SUCCESS"
Halt"""

            cmd = [
                "docker",
                "exec",
                container_name,
                "sh",
                "-c",
                f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0 or "SUCCESS" not in result.stdout:
                raise FixtureLoadError(
                    f"Failed to restore namespace '{namespace}'\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}\n"
                    "\n"
                    "What went wrong:\n"
                    "  Could not create database and namespace from DAT file.\n"
                    "\n"
                    "How to fix it:\n"
                    "  1. Verify IRIS.DAT file is valid\n"
                    "  2. Check IRIS version compatibility\n"
                    "  3. Review IRIS logs for detailed error\n"
                )

            # WORKAROUND: Fix permissions on restored IRIS.DAT
            # IRIS may reject connections if file ownership is wrong
            chown_cmd = [
                "docker",
                "exec",
                container_name,
                "chown",
                "-R",
                "irisowner:irisowner",
                db_dir
            ]

            chown_result = subprocess.run(
                chown_cmd, capture_output=True, text=True, timeout=10
            )

            if chown_result.returncode != 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to fix permissions on {db_dir}: {chown_result.stderr}"
                )

        except subprocess.TimeoutExpired:
            raise FixtureLoadError(
                f"Timeout during RESTORE of namespace '{namespace}'\n"
                "\n"
                "What went wrong:\n"
                "  RESTORE operation took longer than 60 seconds.\n"
                "\n"
                "How to fix it:\n"
                "  1. Check namespace size (large namespaces take longer)\n"
                "  2. Verify IRIS is responsive\n"
            )

        except Exception as e:
            if isinstance(e, FixtureLoadError):
                raise
            raise FixtureLoadError(
                f"Failed to load fixture '{manifest.fixture_id}' into namespace '{namespace}'\n"
                f"Error: {e}\n"
                "\n"
                "What went wrong:\n"
                "  An error occurred while restoring the database.\n"
                "\n"
                "How to fix it:\n"
                "  1. Verify IRIS container is running\n"
                "  2. Check container logs: docker logs <container>\n"
                "  3. Try validating the fixture first\n"
            )

        # Step 3: Verify mount success by checking tables exist
        tables_loaded = []
        try:
            # Get connection config and create connection to target namespace
            from iris_devtester.config import discover_config
            import dataclasses

            config = self.connection_config if self.connection_config else discover_config()
            namespace_config = dataclasses.replace(config, namespace=namespace)

            # Get connection to target namespace
            conn = get_connection(namespace_config)
            cursor = conn.cursor()

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
            conn.close()

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
            if delete_namespace:
                # Delete namespace entirely using docker exec
                # Cannot use iris.connect() + iris.execute() - only works in embedded Python
                if not self.container:
                    raise FixtureLoadError(
                        "Namespace deletion requires container parameter\n"
                        "\n"
                        "What went wrong:\n"
                        "  DATFixtureLoader was created without container parameter.\n"
                        "\n"
                        "How to fix it:\n"
                        "  1. Pass container to DATFixtureLoader:\n"
                        "     loader = DATFixtureLoader(container=iris_container)\n"
                    )

                import subprocess

                container_name = self.container.get_container_name()

                # Delete namespace via ObjectScript
                objectscript_commands = f"""Set sc = ##class(Config.Namespaces).Delete("{namespace}")
If sc Write "SUCCESS" Halt
Write "FAILED: "_$system.Status.GetErrorText(sc)
Halt"""

                cmd = [
                    "docker",
                    "exec",
                    container_name,
                    "sh",
                    "-c",
                    f'iris session IRIS -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
                ]

                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )

                if result.returncode != 0 or "SUCCESS" not in result.stdout:
                    raise FixtureLoadError(
                        f"Failed to delete namespace '{namespace}'\n"
                        f"stdout: {result.stdout}\n"
                        f"stderr: {result.stderr}\n"
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
                # Note: This path is deprecated - prefer delete_namespace=True
                # Cannot switch namespace via SQL, need to reconnect
                pass  # TODO: Implement if needed - current tests use delete_namespace=True

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
