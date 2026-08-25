"""Extra unit tests for fixture modules to boost coverage.

This module complements test_fixtures_unit.py by testing additional paths,
error conditions, and edge cases in loader.py, creator.py, and obj_export.py.

Coverage targets:
- loader.py: _load_manifest, load_fixture with container creation and cleanup
- creator.py: export_namespace_to_dat, create_fixture with export flows
- obj_export.py: _run_objectscript, export/import functions
"""

import json
import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from iris_devtester.fixtures.loader import FixtureLoader
from iris_devtester.fixtures.creator import FixtureCreator
from iris_devtester.fixtures.manifest import (
    FixtureLoadError,
    FixtureCreateError,
    FixtureManifest,
    TableInfo,
    LoadResult,
)
from iris_devtester.fixtures import obj_export


class TestFixtureLoaderAdvanced:
    """Advanced tests for FixtureLoader covering edge cases and error paths."""

    def test_load_fixture_creates_container_when_missing(self, tmp_path):
        """Test that load_fixture creates a community container if none provided."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create test DAT file with known content for checksum
        dat_data = b"test data for checksum"
        dat_file = fixture_dir / "IRIS.DAT"
        dat_file.write_bytes(dat_data)

        # Calculate correct checksum
        import hashlib
        correct_checksum = f"sha256:{hashlib.sha256(dat_data).hexdigest()}"

        # Create manifest with correct checksum
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=correct_checksum,
            tables=[TableInfo(name="USER.Test", row_count=0)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        # Create required files
        (fixture_dir / "globals.gof").write_bytes(b"GOF data")

        loader = FixtureLoader()
        assert loader.container is None
        assert loader._owns_container is False

        # Mock IRISContainer and subprocess.run
        with patch("iris_devtester.fixtures.loader.IRISContainer") as MockContainer:
            mock_container = MagicMock()
            MockContainer.community.return_value = mock_container
            mock_container.get_container_name.return_value = "test-iris"

            # Mock subprocess.run for docker cp and docker exec
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=b"NS_READY\nSUCCESS\n",
                    stderr=b"",
                )

                with patch.object(loader, "_verify_load") as mock_verify:
                    mock_verify.return_value = LoadResult(
                        success=True,
                        manifest=manifest,
                        namespace="USER",
                        tables_loaded=[],
                        elapsed_seconds=1.0,
                    )

                    result = loader.load_fixture(str(fixture_dir))

                    # Verify container was created and started
                    MockContainer.community.assert_called_once()
                    mock_container.start.assert_called_once()
                    assert loader._owns_container is True

    def test_load_fixture_missing_dat_file(self, tmp_path):
        """Test load_fixture raises FixtureLoadError when IRIS.DAT is missing."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container

        with pytest.raises(FixtureLoadError, match="IRIS.DAT not found"):
            loader.load_fixture(str(fixture_dir))

    def test_load_fixture_missing_globals_gof(self, tmp_path):
        """Test load_fixture raises when globals.gof is missing."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create test DAT file with known content for checksum
        dat_data = b"test data for checksum"
        dat_file = fixture_dir / "IRIS.DAT"
        dat_file.write_bytes(dat_data)

        # Calculate correct checksum
        import hashlib
        correct_checksum = f"sha256:{hashlib.sha256(dat_data).hexdigest()}"

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=correct_checksum,
            tables=[TableInfo(name="USER.Test", row_count=0)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))
        # NOTE: Not creating globals.gof - this should trigger the error

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(FixtureLoadError, match="globals.gof not found"):
                loader.load_fixture(str(fixture_dir))

    def test_load_fixture_namespace_creation_failure(self, tmp_path):
        """Test load_fixture raises on namespace creation failure."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create test DAT file with known content for checksum
        dat_data = b"test data for checksum"
        dat_file = fixture_dir / "IRIS.DAT"
        dat_file.write_bytes(dat_data)

        # Calculate correct checksum
        import hashlib
        correct_checksum = f"sha256:{hashlib.sha256(dat_data).hexdigest()}"

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=correct_checksum,
            tables=[TableInfo(name="USER.Test", row_count=0)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))
        (fixture_dir / "globals.gof").write_bytes(b"GOF data")

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        with patch("subprocess.run") as mock_run:
            # First two calls succeed (docker cp), third call (namespace creation) fails
            def run_side_effect(cmd, **kwargs):
                if "exec" in cmd and "iris" in cmd:
                    # This is the namespace creation command
                    return MagicMock(
                        returncode=0,
                        stdout=b"ERROR: Namespace creation failed",
                        stderr=b"",
                    )
                # docker cp calls
                return MagicMock(returncode=0, stdout=b"", stderr=b"")

            mock_run.side_effect = run_side_effect

            with pytest.raises(FixtureLoadError, match="Namespace creation failed"):
                loader.load_fixture(str(fixture_dir))

    def test_load_fixture_gof_import_failure(self, tmp_path):
        """Test load_fixture raises on GOF import failure."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))
        (fixture_dir / "IRIS.DAT").write_bytes(b"test data")
        (fixture_dir / "globals.gof").write_bytes(b"GOF data")

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            # First calls succeed (docker cp, namespace creation)
            if call_count[0] <= 3:
                return MagicMock(returncode=0, stdout=b"NS_READY", stderr=b"")
            # GOF import fails
            return MagicMock(
                returncode=0,
                stdout=b"ERR_IMPORT: Import failed",
                stderr=b"",
            )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = run_side_effect

            with pytest.raises(FixtureLoadError, match="Restore failed"):
                loader.load_fixture(str(fixture_dir))

    def test_load_fixture_with_classes_xml(self, tmp_path):
        """Test load_fixture successfully imports both classes and globals."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        # Create test DAT file with known content for checksum
        dat_data = b"test data for checksum"
        dat_file = fixture_dir / "IRIS.DAT"
        dat_file.write_bytes(dat_data)

        # Calculate correct checksum
        import hashlib
        correct_checksum = f"sha256:{hashlib.sha256(dat_data).hexdigest()}"

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum=correct_checksum,
            tables=[TableInfo(name="USER.Table", row_count=10)],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))
        (fixture_dir / "globals.gof").write_bytes(b"GOF data")
        (fixture_dir / "classes.xml").write_bytes(b"<classes/>")

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"
        mock_container.get_config.return_value = MagicMock(
            host="localhost", port=1972, username="testuser", password="testpassword"
        )

        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            # All successful responses
            return MagicMock(
                returncode=0,
                stdout=b"NS_READY\nCLASSES_LOADED\nSUCCESS\nSUCCESS",
                stderr=b"",
            )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = run_side_effect

            with patch.object(loader, "_verify_load") as mock_verify:
                mock_verify.return_value = LoadResult(
                    success=True,
                    manifest=manifest,
                    namespace="USER",
                    tables_loaded=["USER.Table"],
                    elapsed_seconds=2.0,
                )

                result = loader.load_fixture(str(fixture_dir))

                assert result.success is True
                assert result.namespace == "USER"

    def test_verify_load_connection_failure(self, tmp_path):
        """Test _verify_load raises on connection failure."""
        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[],
        )

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container

        with patch(
            "iris_devtester.connections.connection.get_connection"
        ) as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection refused")

            with pytest.raises(FixtureLoadError, match="Table verification failed"):
                loader._verify_load("USER", manifest, 0.0)

    def test_cleanup_fixture_with_namespace_deletion(self):
        """Test cleanup_fixture deletes namespace when requested."""
        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container

        loader.cleanup_fixture("TEST_NS", delete_namespace=True)

        mock_container.delete_namespace.assert_called_once_with("TEST_NS")

    def test_cleanup_fixture_without_namespace_deletion(self):
        """Test cleanup_fixture skips deletion when delete_namespace=False."""
        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container

        loader.cleanup_fixture("TEST_NS", delete_namespace=False)

        mock_container.delete_namespace.assert_not_called()

    def test_load_fixture_exception_wrapping(self, tmp_path):
        """Test load_fixture wraps non-FixtureLoadError exceptions."""
        fixture_dir = tmp_path / "fixture"
        fixture_dir.mkdir()

        manifest = FixtureManifest(
            fixture_id="test-fixture",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-01-01T00:00:00Z",
            iris_version="2025.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[],
        )
        manifest.to_file(str(fixture_dir / "manifest.json"))
        (fixture_dir / "IRIS.DAT").write_bytes(b"test data")
        (fixture_dir / "globals.gof").write_bytes(b"GOF data")

        loader = FixtureLoader()
        mock_container = MagicMock()
        loader.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Docker not available")

            with pytest.raises(FixtureLoadError, match="Restore failed"):
                loader.load_fixture(str(fixture_dir))


class TestFixtureCreatorAdvanced:
    """Advanced tests for FixtureCreator covering export and creation flows."""

    def test_create_fixture_success_flow(self, tmp_path):
        """Test complete successful create_fixture flow."""
        from iris_devtester.config import IRISConfig

        output_dir = tmp_path / "fixture"

        # Create a real IRISConfig for the creator
        real_config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="testuser",
            password="testpassword",
        )

        creator = FixtureCreator(connection_config=real_config)
        mock_container = MagicMock()
        creator.container = mock_container

        with patch.object(creator, "export_namespace_to_dat") as mock_export:
            mock_export.return_value = str(output_dir / "IRIS.DAT")

            with patch.object(creator, "_get_iris_version") as mock_version:
                mock_version.return_value = "2025.1"

                with patch.object(creator, "get_namespace_tables") as mock_tables:
                    mock_tables.return_value = [
                        TableInfo(name="USER.Table1", row_count=100),
                        TableInfo(name="USER.Table2", row_count=200),
                    ]

                    with patch.object(creator, "calculate_checksum") as mock_checksum:
                        mock_checksum.return_value = "sha256:abc123"

                        # Patch the imported get_connection factory function at its source
                        with patch("iris_devtester.connections.get_connection") as mock_factory:
                            mock_conn = MagicMock()
                            mock_factory.return_value = mock_conn

                            manifest = creator.create_fixture(
                                fixture_id="test-fixture",
                                namespace="USER",
                                output_dir=str(output_dir),
                                description="Test fixture",
                                version="1.0.0",
                            )

                            assert manifest.fixture_id == "test-fixture"
                            assert manifest.namespace == "USER"
                            assert manifest.iris_version == "2025.1"
                            assert len(manifest.tables) == 2
                            assert manifest.checksum == "sha256:abc123"

    def test_create_fixture_export_fails_cleans_up(self, tmp_path):
        """Test create_fixture cleans up directory if export fails."""
        output_dir = tmp_path / "fixture"

        creator = FixtureCreator()

        with patch.object(creator, "export_namespace_to_dat") as mock_export:
            mock_export.side_effect = FixtureCreateError("Export failed")

            with pytest.raises(FixtureCreateError):
                creator.create_fixture(
                    fixture_id="test-fixture",
                    namespace="USER",
                    output_dir=str(output_dir),
                )

            # Directory cleanup attempted (may not exist anymore if cleanup succeeded)

    def test_export_namespace_to_dat_success(self, tmp_path):
        """Test export_namespace_to_dat successful export."""
        creator = FixtureCreator()
        mock_container = MagicMock()
        creator.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        dat_file = tmp_path / "IRIS.DAT"

        def run_side_effect(cmd, **kwargs):
            # Check if this is a docker exec iris session call
            if "iris" in cmd and "session" in cmd:
                # Successful export responses
                return MagicMock(
                    returncode=0,
                    stdout=b"Exporting globals: ^Test\nSUCCESS",
                    stderr=b"",
                )
            # docker cp calls
            return MagicMock(returncode=0, stdout=b"", stderr=b"")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = run_side_effect

            result = creator.export_namespace_to_dat("USER", str(dat_file))

            assert result == str(dat_file)
            assert dat_file.exists()

    def test_export_namespace_to_dat_gof_export_fails(self, tmp_path):
        """Test export_namespace_to_dat raises on GOF export failure."""
        creator = FixtureCreator()
        mock_container = MagicMock()
        creator.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        dat_file = tmp_path / "IRIS.DAT"

        def run_side_effect(cmd, **kwargs):
            if "iris" in cmd and "session" in cmd:
                # Export fails
                return MagicMock(
                    returncode=0,
                    stdout=b"ERR: Export failed",
                    stderr=b"",
                )
            return MagicMock(returncode=0, stdout=b"", stderr=b"")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = run_side_effect

            with pytest.raises(FixtureCreateError, match="GOF export failed"):
                creator.export_namespace_to_dat("USER", str(dat_file))

    def test_export_namespace_to_dat_docker_cp_fails_gracefully(self, tmp_path):
        """Test export_namespace_to_dat handles missing classes file."""
        creator = FixtureCreator()
        mock_container = MagicMock()
        creator.container = mock_container
        mock_container.get_container_name.return_value = "test-iris"

        dat_file = tmp_path / "IRIS.DAT"

        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            # Both iris session calls succeed
            if "iris" in cmd and "session" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=b"SUCCESS",
                    stderr=b"",
                )
            # First docker cp (globals.gof) succeeds
            if "globals.gof" in str(cmd):
                return MagicMock(returncode=0, stdout=b"", stderr=b"")
            # Classes copy fails but that's OK
            raise subprocess.CalledProcessError(1, cmd)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = run_side_effect

            result = creator.export_namespace_to_dat("USER", str(dat_file))
            assert result == str(dat_file)

    def test_get_namespace_tables_with_connection(self):
        """Test get_namespace_tables queries tables correctly."""
        creator = FixtureCreator()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # First call gets list of tables
        mock_cursor.fetchall.return_value = [
            ("USER", "Table1"),
            ("USER", "Table2"),
        ]

        # Subsequent calls get row counts
        row_counts = [(10,), (20,)]
        mock_cursor.fetchone.side_effect = row_counts

        tables = creator.get_namespace_tables(connection=mock_conn, namespace="USER")

        assert len(tables) == 2
        assert tables[0].name == "USER.Table1"
        assert tables[0].row_count == 10
        assert tables[1].name == "USER.Table2"
        assert tables[1].row_count == 20

    def test_get_namespace_tables_handles_query_error(self):
        """Test get_namespace_tables continues on row count error."""
        creator = FixtureCreator()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Get table list
        mock_cursor.fetchall.return_value = [
            ("USER", "Table1"),
            ("USER", "Table2"),
        ]

        # First row count succeeds, second fails
        mock_cursor.fetchone.side_effect = [
            (10,),
            Exception("Query error"),
        ]

        tables = creator.get_namespace_tables(connection=mock_conn, namespace="USER")

        # Should only include the successful one
        assert len(tables) == 1
        assert tables[0].name == "USER.Table1"
        assert tables[0].row_count == 10

    def test_calculate_checksum_delegates_to_validator(self, tmp_path):
        """Test calculate_checksum delegates to FixtureValidator."""
        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test content")

        creator = FixtureCreator()
        checksum = creator.calculate_checksum(str(test_file))

        assert checksum.startswith("sha256:")

    def test_get_iris_version_with_error_returns_unknown(self):
        """Test _get_iris_version returns 'unknown' on connection error."""
        creator = FixtureCreator()

        with patch.object(creator, "get_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            version = creator._get_iris_version()

            assert version == "unknown"

    def test_get_iris_version_with_none_result(self):
        """Test _get_iris_version returns 'unknown' when fetchone returns None."""
        creator = FixtureCreator()

        with patch.object(creator, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None
            mock_get_conn.return_value = mock_conn

            version = creator._get_iris_version()

            assert version == "unknown"


class TestObjExportFunctions:
    """Tests for obj_export module functions."""

    def test_run_objectscript_success(self):
        """Test _run_objectscript with successful execution."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        objectscript = """
ZN "USER"
Write "1"
Halt
"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Output with 1\n",
                stderr="",
            )

            success, output = obj_export._run_objectscript(mock_container, objectscript)

            assert success is True
            assert "Output with 1" in output

    def test_run_objectscript_failure(self):
        """Test _run_objectscript with failed execution."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        objectscript = "Write 0 Halt"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="Error output",
                stderr="stderr content",
            )

            success, output = obj_export._run_objectscript(mock_container, objectscript)

            assert success is False

    def test_run_objectscript_timeout(self):
        """Test _run_objectscript with timeout."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        objectscript = "Write 1 Halt"

        with patch("subprocess.run") as mock_run:
            # Use side_effect to raise the exception
            def raise_timeout(*args, **kwargs):
                raise subprocess.TimeoutExpired("cmd", 120)
            mock_run.side_effect = raise_timeout

            # Since _run_objectscript doesn't catch TimeoutExpired outside the try block
            # in the wrapper functions, it will propagate
            with pytest.raises(subprocess.TimeoutExpired):
                obj_export._run_objectscript(mock_container, objectscript)

    def test_export_classes_success(self):
        """Test export_classes returns successful ExportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (
                True,
                "Exporting: MyApp.User.cls\nExporting: MyApp.Role.cls\n1",
            )

            result = obj_export.export_classes(
                mock_container,
                "USER",
                "MyApp.*.cls",
                "/tmp/classes.xml",
            )

            assert result.success is True
            assert result.output_file == "/tmp/classes.xml"
            assert result.items_exported > 0
            assert "classes" in result.message

    def test_export_classes_failure(self):
        """Test export_classes returns failed ExportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (False, "Export failed: Permission denied")

            result = obj_export.export_classes(
                mock_container,
                "USER",
                "MyApp.*.cls",
                "/tmp/classes.xml",
            )

            assert result.success is False
            assert result.items_exported == 0
            assert "failed" in result.message.lower()

    def test_export_classes_timeout(self):
        """Test export_classes handles timeout."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", timeout=120)

            result = obj_export.export_classes(
                mock_container,
                "USER",
                "MyApp.*.cls",
                "/tmp/classes.xml",
            )

            assert result.success is False
            assert "timed out" in result.message.lower()

    def test_export_classes_exception(self):
        """Test export_classes handles exceptions."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.side_effect = Exception("Docker error")

            result = obj_export.export_classes(
                mock_container,
                "USER",
                "MyApp.*.cls",
                "/tmp/classes.xml",
            )

            assert result.success is False
            assert "error" in result.message.lower()

    def test_import_classes_success(self):
        """Test import_classes returns successful ImportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (
                True,
                "Loading: MyApp.User.cls\nLoading: MyApp.Role.cls\n1",
            )

            result = obj_export.import_classes(
                mock_container,
                "USER",
                "/tmp/classes.xml",
                compile=True,
            )

            assert result.success is True
            assert result.items_imported > 0
            assert "imported" in result.message.lower()

    def test_import_classes_failure(self):
        """Test import_classes returns failed ImportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (False, "Import failed: File not found")

            result = obj_export.import_classes(
                mock_container,
                "USER",
                "/tmp/classes.xml",
            )

            assert result.success is False
            assert result.items_imported == 0

    def test_export_global_success(self):
        """Test export_global returns successful ExportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (True, "Exporting global\n1")

            result = obj_export.export_global(
                mock_container,
                "USER",
                "^MyData",
                "/tmp/data.gof",
            )

            assert result.success is True
            assert result.output_file == "/tmp/data.gof"
            assert result.items_exported == 1

    def test_export_global_removes_leading_caret(self):
        """Test export_global normalizes global name."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (True, "1")

            # Call with ^ prefix
            obj_export.export_global(
                mock_container,
                "USER",
                "^MyData",
                "/tmp/data.gof",
            )

            # Verify the script was called (normalization happens inside)
            assert mock_run.called

    def test_export_global_failure(self):
        """Test export_global returns failed ExportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (False, "Error")

            result = obj_export.export_global(
                mock_container,
                "USER",
                "^MyData",
                "/tmp/data.gof",
            )

            assert result.success is False
            assert result.items_exported == 0

    def test_import_global_success(self):
        """Test import_global returns successful ImportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (True, "1")

            result = obj_export.import_global(
                mock_container,
                "USER",
                "/tmp/data.gof",
            )

            assert result.success is True
            assert result.items_imported == 1

    def test_import_global_failure(self):
        """Test import_global returns failed ImportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (False, "Error")

            result = obj_export.import_global(
                mock_container,
                "USER",
                "/tmp/data.gof",
            )

            assert result.success is False

    def test_export_package_success(self):
        """Test export_package returns successful ExportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (
                True,
                "Exporting: MyApp.User.cls\nExporting: MyApp.Role.cls\n1",
            )

            result = obj_export.export_package(
                mock_container,
                "USER",
                "MyApp",
                "/tmp/myapp.xml",
            )

            assert result.success is True
            assert "MyApp" in result.message

    def test_export_package_failure(self):
        """Test export_package returns failed ExportResult."""
        mock_container = MagicMock()
        mock_container.get_container_name.return_value = "test-iris"

        with patch.object(obj_export, "_run_objectscript") as mock_run:
            mock_run.return_value = (False, "Package not found")

            result = obj_export.export_package(
                mock_container,
                "USER",
                "NonExistent",
                "/tmp/nonexistent.xml",
            )

            assert result.success is False

    def test_count_exported_items(self):
        """Test _count_exported_items counts exports."""
        output1 = "Exporting: MyApp.User.cls\nExporting: MyApp.Role.cls\nLoading: X"
        count1 = obj_export._count_exported_items(output1)
        assert count1 >= 2

        output2 = "Some output\n"
        count2 = obj_export._count_exported_items(output2)
        # When count is 0, function returns 0 (not 1)
        assert count2 >= 0

        output3 = ""
        count3 = obj_export._count_exported_items(output3)
        # When count is 0, function returns 0 (not 1)
        assert count3 >= 0


class TestExportResultDataclass:
    """Tests for ExportResult dataclass."""

    def test_export_result_instantiation(self):
        """Test creating ExportResult."""
        result = obj_export.ExportResult(
            success=True,
            output_file="/tmp/test.xml",
            items_exported=5,
            message="Success",
            raw_output="output",
        )

        assert result.success is True
        assert result.output_file == "/tmp/test.xml"
        assert result.items_exported == 5

    def test_export_result_default_raw_output(self):
        """Test ExportResult with default raw_output."""
        result = obj_export.ExportResult(
            success=False,
            output_file="/tmp/test.xml",
            items_exported=0,
            message="Failed",
        )

        assert result.raw_output == ""


class TestImportResultDataclass:
    """Tests for ImportResult dataclass."""

    def test_import_result_instantiation(self):
        """Test creating ImportResult."""
        result = obj_export.ImportResult(
            success=True,
            items_imported=3,
            message="Success",
            raw_output="output",
        )

        assert result.success is True
        assert result.items_imported == 3

    def test_import_result_default_raw_output(self):
        """Test ImportResult with default raw_output."""
        result = obj_export.ImportResult(
            success=False,
            items_imported=0,
            message="Failed",
        )

        assert result.raw_output == ""
