import logging
import subprocess
import time
from pathlib import Path
from subprocess import TimeoutExpired
from typing import List, Optional

from iris_devtester.containers.iris_container import IRISContainer

from .manifest import FixtureLoadError, FixtureManifest, FixtureValidationError, LoadResult

logger = logging.getLogger(__name__)


class DATFixtureLoader:

    def __init__(self, container: Optional[IRISContainer] = None, **kwargs):
        self.container = container
        self.connection_config = kwargs.get("connection_config")
        self._owns_container = False

    def validate_fixture(
        self, fixture_path: str, validate_checksum: bool = True
    ) -> FixtureManifest:
        from .validator import FixtureValidator

        validator = FixtureValidator()
        result = validator.validate_fixture(fixture_path, validate_checksum=validate_checksum)
        if not result.valid or result.manifest is None:
            raise FixtureValidationError(f"Invalid fixture: {result.errors}")
        return result.manifest

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
                    raise FixtureValidationError(f"Checksum validation failed: {validation.errors}")

            container_name = self.container.get_container_name()
            container_gof_path = f"/tmp/RESTORE_{namespace}.gof"
            container_cls_path = f"/tmp/RESTORE_{namespace}.xml"

            # Step 1: Copy fixture files to container
            # The fixture package has globals.gof and optionally classes.xml
            fixture_base = Path(fixture_path)
            gof_file = fixture_base / "globals.gof"
            cls_file = fixture_base / "classes.xml"

            if gof_file.exists():
                subprocess.run(
                    ["docker", "cp", str(gof_file), f"{container_name}:{container_gof_path}"],
                    check=True,
                )
            else:
                raise FixtureLoadError(f"globals.gof not found in {fixture_path}")

            has_classes = cls_file.exists()
            if has_classes:
                subprocess.run(
                    ["docker", "cp", str(cls_file), f"{container_name}:{container_cls_path}"],
                    check=True,
                )

            # Fix permissions on the copied files
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-u",
                    "root",
                    container_name,
                    "chmod",
                    "644",
                    container_gof_path,
                ],
                capture_output=True,
                timeout=30,
            )
            if has_classes:
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        "-u",
                        "root",
                        container_name,
                        "chmod",
                        "644",
                        container_cls_path,
                    ],
                    capture_output=True,
                    timeout=30,
                )

            # Step 2: Create namespace if it doesn't exist, then import globals
            # First, ensure the namespace exists (create with default database structure)
            db_dir = f"/usr/irissys/mgr/db_{namespace.lower()}"
            create_ns_script = f"""
 Set ns = "{namespace}"
 Set dbDir = "{db_dir}"
 If ##class(Config.Namespaces).Exists(ns) Write "NS_READY" Halt
 If '##class(%File).DirectoryExists(dbDir) Do ##class(%File).CreateDirectoryChain(dbDir)
 Set db = ##class(SYS.Database).%New()
 Set db.Directory = dbDir
 Set sc = db.%Save()
 If 'sc Write "ERR_DB:",$System.Status.GetErrorText(sc) Halt
 Set sc = ##class(Config.Databases).Create(ns, dbDir)
 If 'sc Write "ERR_DBCFG:",$System.Status.GetErrorText(sc) Halt
 Kill p Set p("Globals") = ns, p("Routines") = ns
 Set sc = ##class(Config.Namespaces).Create(ns, .p)
 If 'sc Write "ERR_NS:",$System.Status.GetErrorText(sc) Halt
 Write "NS_READY"
 Halt
 """
            result = subprocess.run(
                ["docker", "exec", "-i", container_name, "iris", "session", "IRIS", "-U", "%SYS"],
                input=create_ns_script.encode("utf-8"),
                capture_output=True,
                timeout=60,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            if "NS_READY" not in stdout:
                raise FixtureLoadError(f"Namespace creation failed: {stdout}")

            # Step 3a: Import classes FIRST (if available) - this creates SQL table metadata
            if has_classes:
                import_cls_script = f"""
 Set clsFile = "{container_cls_path}"
 Set sc = $SYSTEM.OBJ.Load(clsFile, "ck")
 If 'sc Write "ERR_CLS:",$System.Status.GetErrorText(sc) Halt
 Write "CLASSES_LOADED"
 Halt
 """
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "-i",
                        container_name,
                        "iris",
                        "session",
                        "IRIS",
                        "-U",
                        namespace,
                    ],
                    input=import_cls_script.encode("utf-8"),
                    capture_output=True,
                    timeout=120,
                )
                stdout = result.stdout.decode("utf-8", errors="replace")
                logger.info(f"Class import output: {stdout}")
                if "CLASSES_LOADED" not in stdout and "ERR_CLS" in stdout:
                    raise FixtureLoadError(f"Class import failed: {stdout}")

            # Step 3b: Import globals (data)
            # Signature: Import(Nsp, GlobalList, FileName, InputFormat)
            # InputFormat=7 for GOF (block format)
            import_gof_script = f"""
 Set file = "{container_gof_path}"
 Set sc = ##class(%Library.Global).Import($Namespace, "*", file, 7)
 If 'sc Write "ERR_IMPORT:",$System.Status.GetErrorText(sc) Halt
 Write "SUCCESS"
 Halt
 """
            # Run import in the TARGET namespace so globals go to the right place
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    container_name,
                    "iris",
                    "session",
                    "IRIS",
                    "-U",
                    namespace,
                ],
                input=import_gof_script.encode("utf-8"),
                capture_output=True,
                timeout=120,
            )

            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.info(f"GOF import output: {stdout}")
            if stderr:
                logger.warning(f"GOF import stderr: {stderr}")
            if "SUCCESS" not in stdout:
                raise FixtureLoadError(f"Restore failed: {stdout}")

            # Step 3: CRITICAL - Ensure test credentials still work after restore
            # Restoration can sometimes overwrite security settings or trigger flags.
            ensure_user_script = """
 Set user="testuser",pass="testpassword"
 Kill p
 Set p("PasswordExternal")=pass,p("Roles")="%ALL",p("ChangePassword")=0,p("PasswordNeverExpires")=1
 If ##class(Security.Users).Exists(user) Do ##class(Security.Users).Delete(user)
 Set sc=##class(Security.Users).Create(user,.p)
 Do ##class(Security.Services).Get("%Service_CallIn",.svcP)
 Set svcP("Enabled")=1
 Do ##class(Security.Services).Modify("%Service_CallIn",.svcP)
 If $$$ISERR(sc) Write "ERR:",$System.Status.GetErrorText(sc) Halt
 Write "SUCCESS" Halt
 """
            subprocess.run(
                ["docker", "exec", "-i", container_name, "iris", "session", "IRIS", "-U", "%SYS"],
                input=ensure_user_script.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            # Also unexpire everything else just in case
            from iris_devtester.utils.password import unexpire_all_passwords

            unexpire_all_passwords(container_name)

            time.sleep(5)  # Give IRIS a moment to stabilize security changes

        except Exception as e:
            if isinstance(e, FixtureLoadError):
                raise
            raise FixtureLoadError(f"Restore failed: {e}")

        return self._verify_load(namespace, manifest, start_time)

    def _verify_load(
        self, namespace: str, manifest: FixtureManifest, start_time: float
    ) -> LoadResult:
        if not self.container:
            raise RuntimeError("IRIS container required for verification")

        try:
            # Use the modern connection manager which has automatic password reset remediation
            from iris_devtester.config import IRISConfig
            from iris_devtester.connections.connection import (
                get_connection as get_modern_connection,
            )

            # CRITICAL: Use the provided connection_config if available (has verified testuser credentials)
            # Otherwise fall back to container's config
            if self.connection_config:
                config = self.connection_config
            else:
                config = self.container.get_config()

            # Use the actual container name for remediation if needed
            container_name = self.container.get_container_name()

            conn = get_modern_connection(
                IRISConfig(
                    host=config.host,
                    port=config.port,
                    namespace=namespace,
                    username=config.username,
                    password=config.password,
                    container_name=container_name,
                )
            )
            cursor = conn.cursor()
            verified_tables = []
            for table_info in manifest.tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_info.name}")
                cursor.fetchone()
                verified_tables.append(table_info.name)
            cursor.close()
            conn.close()

            return LoadResult(
                success=True,
                manifest=manifest,
                namespace=namespace,
                tables_loaded=verified_tables,
                elapsed_seconds=time.time() - start_time,
            )
        except Exception as e:
            raise FixtureLoadError(f"Table verification failed: {e}")

    def cleanup_fixture(self, namespace: str, delete_namespace: bool = True):
        if not namespace:
            raise ValueError("Namespace is required")
        if not self.container:
            raise RuntimeError("IRIS container required for cleanup")
        if delete_namespace:
            self.container.delete_namespace(namespace)

    def get_connection(self):
        """Contract‑compatible connection getter."""
        # Use the modern connection manager which has automatic password reset remediation
        from iris_devtester.connections.connection import get_connection as get_modern_connection

        return get_modern_connection(config=self.connection_config)
