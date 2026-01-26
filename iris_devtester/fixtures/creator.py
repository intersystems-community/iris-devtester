import datetime
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection

from .manifest import (
    FixtureCreateError,
    FixtureManifest,
    TableInfo,
)
from .validator import FixtureValidator


class FixtureCreator:
    """
    Creates .DAT fixtures by exporting IRIS namespaces.
    """

    def __init__(
        self, connection_config: Optional[IRISConfig] = None, container: Optional[Any] = None
    ):
        self.connection_config = connection_config
        self.container = container
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
        output_path = Path(output_dir)

        if output_path.exists():
            raise FileExistsError(f"Fixture directory already exists: {output_dir}")

        output_path.mkdir(parents=True, exist_ok=False)

        # Export namespace to IRIS.DAT
        dat_file_path = output_path / "IRIS.DAT"
        try:
            self.export_namespace_to_dat(namespace, str(dat_file_path))
        except Exception as e:
            try:
                output_path.rmdir()
            except:
                pass
            raise

        # Get IRIS version
        iris_version = self._get_iris_version()

        # Get table list with row counts
        import dataclasses

        from iris_devtester.config import discover_config
        from iris_devtester.connections import get_connection as get_conn_factory

        base_config = self.connection_config or discover_config()
        ns_config = dataclasses.replace(base_config, namespace=namespace)

        ns_connection = get_conn_factory(ns_config)

        try:
            tables = self.get_namespace_tables(ns_connection, namespace)
        finally:
            ns_connection.close()

        # Calculate checksum
        checksum = self.calculate_checksum(str(dat_file_path))

        # Create manifest
        manifest = FixtureManifest(
            fixture_id=fixture_id,
            version=version,
            schema_version="1.0",
            description=description,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
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
        Export namespace to a fixture package (classes + globals).

        We export:
        1. Class definitions (XML) - for SQL schema
        2. Globals (GOF) - for data
        """
        if self.container is None:
            raise FixtureCreateError("Export operations require container parameter")

        container_name = self.container.get_container_name()
        container_gof_path = f"/tmp/GLOBALS_{namespace}.gof"
        container_cls_path = f"/tmp/CLASSES_{namespace}.xml"

        # Step 1: Export class definitions (for SQL schema)
        export_classes_script = f"""
 Set clsFile = "{container_cls_path}"
 Set sc = $SYSTEM.OBJ.ExportAllClasses(clsFile)
 If 'sc Write "WARN_CLS:",$System.Status.GetErrorText(sc),!
 Write "CLASSES_DONE"
 Halt
 """
        result = subprocess.run(
            ["docker", "exec", "-i", container_name, "iris", "session", "IRIS", "-U", namespace],
            input=export_classes_script.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        if "CLASSES_DONE" not in stdout:
            # Non-fatal - some namespaces may have no user classes
            pass

        # Step 2: Export globals (for data)
        export_globals_script = f"""
 Set file = "{container_gof_path}"
 Set glist = ""
 Set g = "" For  Set g = $Order(^$Global(g)) Quit:g=""  If $Extract(g,1)'="%" Set glist = glist_$Select(glist="":"",1:",")_g
 If glist = "" Write "WARN:No user globals found",! Write "SUCCESS" Halt
 Write "Exporting globals: ",glist,!
 Set sc = ##class(%Library.Global).Export($Namespace, glist, file, 7)
 If 'sc Write "ERR:",$System.Status.GetErrorText(sc) Halt
 If '##class(%File).Exists(file) Write "ERR_FILE_NOT_FOUND" Halt
 Write "SUCCESS"
 Halt
 """
        result = subprocess.run(
            ["docker", "exec", "-i", container_name, "iris", "session", "IRIS", "-U", namespace],
            input=export_globals_script.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )

        stdout = result.stdout.decode("utf-8", errors="replace")
        if "SUCCESS" not in stdout:
            raise FixtureCreateError(f"GOF export failed: {stdout}")

        # Copy both files from container to host
        # The dat_file_path is expected to be IRIS.DAT, we'll use it as base
        base_path = Path(dat_file_path).parent
        subprocess.run(
            [
                "docker",
                "cp",
                f"{container_name}:{container_gof_path}",
                str(base_path / "globals.gof"),
            ],
            check=True,
        )

        # Try to copy classes file (may not exist if no user classes)
        try:
            subprocess.run(
                [
                    "docker",
                    "cp",
                    f"{container_name}:{container_cls_path}",
                    str(base_path / "classes.xml"),
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            pass  # No classes to export

        # Create a marker file at the expected dat_file_path location
        Path(dat_file_path).write_text("GOF_FIXTURE")
        return dat_file_path

    def calculate_checksum(self, dat_file_path: str) -> str:
        return self.validator.calculate_sha256(dat_file_path)

    def get_namespace_tables(self, connection: Any = None, namespace: str = "") -> List[TableInfo]:
        if connection is None:
            connection = self.get_connection()

        tables = []
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', '%SYS', '%Library')
        """
        )

        for row in cursor.fetchall():
            qualified_name = f"{row[0]}.{row[1]}"
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {qualified_name}")
                row_count = cursor.fetchone()[0]
                tables.append(TableInfo(name=qualified_name, row_count=row_count))
            except:
                continue
        cursor.close()
        return tables

    def get_connection(self) -> Any:
        if self._connection is None:
            # Use the modern connection manager which has automatic password reset remediation
            from iris_devtester.connections.connection import (
                get_connection as get_modern_connection,
            )

            self._connection = get_modern_connection(self.connection_config)
        return self._connection

    def _get_iris_version(self) -> str:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT $SYSTEM.Version.GetVersion()")
            row = cursor.fetchone()
            cursor.close()
            return str(row[0]) if row else "unknown"
        except:
            return "unknown"
