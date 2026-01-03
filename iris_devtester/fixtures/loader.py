import logging
import time
import subprocess
from pathlib import Path
from typing import List, Optional
from subprocess import TimeoutExpired

from iris_devtester.containers.iris_container import IRISContainer
from .manifest import FixtureManifest, LoadResult, FixtureLoadError, FixtureValidationError

logger = logging.getLogger(__name__)

class DATFixtureLoader:

    def __init__(self, container: Optional[IRISContainer] = None):
        self.container = container
        self._owns_container = False

    def _load_manifest(self, fixture_path: str) -> FixtureManifest:
        manifest_path = Path(fixture_path) / "manifest.json"
        if not manifest_path.exists():
            raise FixtureLoadError(f"Manifest not found at {manifest_path}")
        return FixtureManifest.from_json(manifest_path.read_text())

    def load_fixture(
        self,
        fixture_path: str,
        target_namespace: Optional[str] = None,
        validate_checksum: bool = True,
        force_refresh: bool = False,
    ) -> LoadResult:
        start_time = time.time()

        if not self.container:
            self.container = IRISContainer.community()
            self.container.start()
            self._owns_container = True

        try:
            manifest = self._load_manifest(fixture_path)
            namespace = target_namespace or manifest.namespace

            dat_file_path = Path(fixture_path) / "IRIS.DAT"
            if not dat_file_path.exists():
                raise FixtureLoadError(f"IRIS.DAT not found in {fixture_path}")

            if validate_checksum:
                from .validator import FixtureValidator
                validator = FixtureValidator()
                validation = validator.validate_fixture(fixture_path)
                if not validation.valid:
                    raise FixtureValidationError(
                        f"Checksum validation failed: {validation.errors}"
                    )

            container_name = self.container.get_container_name()
            container_dat_path = f"/tmp/RESTORE_{namespace}.DAT"

            subprocess.run([
                "docker", "cp", str(dat_file_path),
                f"{container_name}:{container_dat_path}"
            ], check=True, capture_output=True, text=True)

            db_name = f"DB_{namespace}"
            db_dir = f"/usr/irissys/mgr/db_{namespace.lower()}"

            objectscript = f"""
 Set dbDir = "{db_dir}"
 Set dbName = "{db_name}"
 Set nsName = "{namespace}"
 
 If ##class(Config.Namespaces).Exists(nsName,.obj) Do ##class(Config.Namespaces).Delete(nsName)
 If ##class(Config.Databases).Exists(dbName,.obj) {{
 Set dir = obj.Directory
 Do ##class(SYS.Database).DismountDatabase(dir)
 Do ##class(Config.Databases).Delete(dbName)
 }}
 
 If '##class(%File).DirectoryExists(dbDir) Do ##class(%File).CreateDirectoryChain(dbDir)
 Do ##class(%File).CopyFile("{container_dat_path}",dbDir_"/IRIS.DAT")
 
 Set dbProps("Directory") = dbDir
 Set status = ##class(Config.Databases).Create(dbName,.dbProps)
 If status'=1 Write "DB_CREATE_FAILED" Halt
 
 Set status = ##class(SYS.Database).MountDatabase(dbDir)
 
 Set nsProps("Globals") = dbName
 Set nsProps("Routines") = dbName
 Set status = ##class(Config.Namespaces).Create(nsName,.nsProps)
 If status=1 Write "SUCCESS"
 Halt
"""

            result = subprocess.run([
                "docker", "exec", "-i", container_name,
                "iris", "session", "IRIS", "-U", "%SYS"
            ], input=objectscript.encode('utf-8'), capture_output=True, timeout=60)

            stdout = result.stdout.decode('utf-8', errors='replace')
            if "SUCCESS" not in stdout:
                raise FixtureLoadError(f"Restore failed: {stdout}")

            subprocess.run([
                "docker", "exec", "-u", "root", container_name,
                "chown", "-R", "irisowner:irisowner", db_dir
            ], check=False)
            
            time.sleep(2)

        except TimeoutExpired:
            raise FixtureLoadError("Restore timed out")
        except Exception as e:
            if isinstance(e, FixtureLoadError): raise
            raise FixtureLoadError(f"Restore failed: {e}")

        try:
            from iris_devtester.connections import get_connection
            from iris_devtester.config import IRISConfig

            config = self.container.get_config()
            conn = get_connection(IRISConfig(
                host=config.host, port=config.port,
                namespace=namespace, username=config.username, password=config.password
            ))
            cursor = conn.cursor()
            verified_tables = []
            for table_info in manifest.tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_info.name}")
                cursor.fetchone()
                verified_tables.append(table_info.name)
            cursor.close()
            conn.close()

            return LoadResult(
                success=True, manifest=manifest,
                namespace=namespace, tables_loaded=verified_tables,
                elapsed_seconds=time.time() - start_time
            )
        except Exception as e:
            raise FixtureLoadError(f"Table verification failed: {e}")
