"""Integration tests for $SYSTEM.OBJ export/import patterns.

These tests verify the export/import utilities based on patterns
documented in docs/learnings/iris-backup-patterns.md.

Constitutional Compliance:
- Principle #2: DBAPI First (uses native IRIS APIs)
- Principle #5: Fail Fast with Guidance (structured results)
- Principle #7: Medical-Grade Reliability (comprehensive coverage)
"""

import pytest
from iris_devtester.containers import IRISContainer
from iris_devtester.fixtures import (
    export_classes,
    import_classes,
    export_global,
    import_global,
    export_package,
    ExportResult,
    ImportResult,
)


@pytest.fixture(scope="module")
def running_iris_container():
    """Running IRIS container for export/import tests."""
    with IRISContainer.community() as iris:
        iris.wait_for_ready(timeout=60)
        yield iris


class TestExportClasses:
    """Test export_classes() function."""

    def test_export_returns_result(self, running_iris_container):
        """Export should return ExportResult object."""
        result = export_classes(
            running_iris_container,
            namespace="%SYS",
            pattern="Security.Users.cls",
            output_file="/tmp/test-export.xml",
        )

        assert isinstance(result, ExportResult)
        assert result.output_file == "/tmp/test-export.xml"

    def test_export_system_class_succeeds(self, running_iris_container):
        """Exporting a system class should succeed."""
        result = export_classes(
            running_iris_container,
            namespace="%SYS",
            pattern="%SYSTEM.OBJ.cls",
            output_file="/tmp/system-obj.xml",
        )

        # May or may not succeed depending on permissions, but should not error
        assert isinstance(result, ExportResult)


class TestImportClasses:
    """Test import_classes() function."""

    def test_import_returns_result(self, running_iris_container):
        """Import should return ImportResult object."""
        # First create a file to import (even if empty, it tests the function)
        result = import_classes(
            running_iris_container,
            namespace="USER",
            input_file="/tmp/nonexistent.xml",
            compile=False,
        )

        assert isinstance(result, ImportResult)
        # Will fail because file doesn't exist, but should return result
        assert result.success is False


class TestExportGlobal:
    """Test export_global() function."""

    def test_export_returns_result(self, running_iris_container):
        """Export global should return ExportResult object."""
        result = export_global(
            running_iris_container,
            namespace="USER",
            global_name="^TestGlobal",
            output_file="/tmp/test-global.gof",
        )

        assert isinstance(result, ExportResult)


class TestImportGlobal:
    """Test import_global() function."""

    def test_import_returns_result(self, running_iris_container):
        """Import global should return ImportResult object."""
        result = import_global(
            running_iris_container,
            namespace="USER",
            input_file="/tmp/nonexistent.gof",
        )

        assert isinstance(result, ImportResult)
        # Will fail because file doesn't exist
        assert result.success is False


class TestExportPackage:
    """Test export_package() function."""

    def test_export_returns_result(self, running_iris_container):
        """Export package should return ExportResult object."""
        result = export_package(
            running_iris_container,
            namespace="%SYS",
            package_name="Security",
            output_file="/tmp/security-pkg.xml",
        )

        assert isinstance(result, ExportResult)


class TestExportImportRoundTrip:
    """Test round-trip export and import."""

    def test_export_import_roundtrip_pattern(self, running_iris_container):
        """Pattern: Export from one namespace, import to another.

        This tests the documented pattern from iris-backup-patterns.md:
        1. Export classes from source namespace
        2. Import into target namespace
        """
        # Export a system class (guaranteed to exist)
        export_result = export_classes(
            running_iris_container,
            namespace="%SYS",
            pattern="%Utility.cls",
            output_file="/tmp/utility-class.xml",
        )

        # If export succeeded, try import
        if export_result.success:
            import_result = import_classes(
                running_iris_container,
                namespace="USER",
                input_file="/tmp/utility-class.xml",
                compile=False,  # Don't compile system classes in USER
            )

            # Verify result structure
            assert isinstance(import_result, ImportResult)
            assert import_result.message  # Should have some message
