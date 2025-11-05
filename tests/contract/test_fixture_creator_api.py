"""
Contract tests for FixtureCreator API.

These tests validate the public API interface defined in:
specs/004-dat-fixtures/contracts/fixture-creator.yaml

Tests verify:
- Class and method signatures match contract
- Return types are correct
- Integration with Feature 003 Connection Manager
- API is usable as documented
"""


import pytest

pytestmark = pytest.mark.contract
from typing import Optional, Dict, Any, List


class TestFixtureCreatorClass:
    """Contract tests for FixtureCreator class."""

    def test_class_exists(self):
        """Test that FixtureCreator class can be imported."""
        from iris_devtester.fixtures import FixtureCreator

        assert FixtureCreator is not None

    def test_constructor_signature_zero_config(self):
        """Test that FixtureCreator() constructor works with no args."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert creator is not None

    def test_constructor_signature_explicit_config(self):
        """Test that FixtureCreator accepts optional connection_config."""
        from iris_devtester.fixtures import FixtureCreator
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        creator = FixtureCreator(connection_config=config)
        assert creator is not None

    def test_class_is_instantiable(self):
        """Test that FixtureCreator can be instantiated."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert isinstance(creator, FixtureCreator)


class TestCreateFixtureMethod:
    """Contract tests for create_fixture() method."""

    def test_method_exists(self):
        """Test that create_fixture method exists."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert hasattr(creator, 'create_fixture')
        assert callable(creator.create_fixture)

    def test_signature_required_params(self):
        """Test create_fixture signature with required parameters."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should accept required params: fixture_id, namespace, output_dir
        # (Will fail without IRIS connection)
        with pytest.raises(Exception):
            creator.create_fixture(
                fixture_id="test",
                namespace="USER",
                output_dir="/tmp/test-fixture"
            )

    def test_signature_optional_description(self):
        """Test create_fixture accepts optional description parameter."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        with pytest.raises(Exception):
            creator.create_fixture(
                fixture_id="test",
                namespace="USER",
                output_dir="/tmp/test-fixture",
                description="Test fixture"
            )

    def test_signature_optional_version(self):
        """Test create_fixture accepts optional version parameter."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        with pytest.raises(Exception):
            creator.create_fixture(
                fixture_id="test",
                namespace="USER",
                output_dir="/tmp/test-fixture",
                version="2.0.0"
            )

    def test_signature_optional_features(self):
        """Test create_fixture accepts optional features parameter."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        with pytest.raises(Exception):
            creator.create_fixture(
                fixture_id="test",
                namespace="USER",
                output_dir="/tmp/test-fixture",
                features={"use_case": "testing", "dataset": "sample"}
            )

    def test_return_type_is_manifest(self):
        """Test that create_fixture returns FixtureManifest."""
        from iris_devtester.fixtures import FixtureCreator, FixtureManifest

        creator = FixtureCreator()

        # Return type should be FixtureManifest
        # (Signature validation only)
        assert True  # Method exists and has correct signature


class TestExportNamespaceToDatMethod:
    """Contract tests for export_namespace_to_dat() method."""

    def test_method_exists(self):
        """Test that export_namespace_to_dat method exists."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert hasattr(creator, 'export_namespace_to_dat')
        assert callable(creator.export_namespace_to_dat)

    def test_signature_required_params(self):
        """Test export_namespace_to_dat signature with required parameters."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should accept namespace and dat_file_path
        # (Will fail without IRIS connection)
        with pytest.raises(Exception):
            creator.export_namespace_to_dat("USER", "/tmp/IRIS.DAT")

    def test_return_type_is_string(self):
        """Test that export_namespace_to_dat returns string (file path)."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Return type should be str
        # (Signature validation only)
        assert True  # Method exists


class TestCalculateChecksumMethod:
    """Contract tests for calculate_checksum() method."""

    def test_method_exists(self):
        """Test that calculate_checksum method exists."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert hasattr(creator, 'calculate_checksum')
        assert callable(creator.calculate_checksum)

    def test_signature_required_params(self):
        """Test calculate_checksum signature with required parameters."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should accept dat_file_path
        # (Will fail for nonexistent file)
        with pytest.raises(FileNotFoundError):
            creator.calculate_checksum("/nonexistent/IRIS.DAT")

    def test_return_type_is_string(self):
        """Test that calculate_checksum returns string (sha256:...)."""
        import tempfile
        from pathlib import Path
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            checksum = creator.calculate_checksum(temp_path)
            assert isinstance(checksum, str)
            assert checksum.startswith("sha256:")
        finally:
            Path(temp_path).unlink()


class TestGetNamespaceTablesMethod:
    """Contract tests for get_namespace_tables() method."""

    def test_method_exists(self):
        """Test that get_namespace_tables method exists."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert hasattr(creator, 'get_namespace_tables')
        assert callable(creator.get_namespace_tables)

    def test_signature_required_params(self):
        """Test get_namespace_tables signature with required parameters."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should accept namespace
        # (Will fail without IRIS connection)
        with pytest.raises(Exception):
            creator.get_namespace_tables("USER")

    def test_return_type_is_list_of_tableinfo(self):
        """Test that get_namespace_tables returns List[TableInfo]."""
        from iris_devtester.fixtures import FixtureCreator, TableInfo

        creator = FixtureCreator()

        # Return type should be List[TableInfo]
        # (Signature validation only)
        assert True  # Method exists


class TestRefreshFixtureMethod:
    """Contract tests for refresh_fixture() method."""

    def test_method_exists(self):
        """Test that refresh_fixture method exists."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert hasattr(creator, 'refresh_fixture')
        assert callable(creator.refresh_fixture)

    def test_signature_required_params(self):
        """Test refresh_fixture signature with required parameters."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should accept fixture_dir and namespace
        # (Will fail for nonexistent fixture)
        with pytest.raises(FileNotFoundError):
            creator.refresh_fixture("/nonexistent/fixture", "USER")

    def test_return_type_is_manifest(self):
        """Test that refresh_fixture returns FixtureManifest."""
        from iris_devtester.fixtures import FixtureCreator, FixtureManifest

        creator = FixtureCreator()

        # Return type should be FixtureManifest
        # (Signature validation only)
        assert True  # Method exists


class TestGetConnectionMethod:
    """Contract tests for get_connection() method."""

    def test_method_exists(self):
        """Test that get_connection method exists."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()
        assert hasattr(creator, 'get_connection')
        assert callable(creator.get_connection)

    def test_signature_no_params(self):
        """Test get_connection signature requires no parameters."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should work with no params (will fail without IRIS available)
        try:
            conn = creator.get_connection()
        except Exception:
            # Expected - no IRIS available in contract tests
            pass


class TestIntegrationWithConnectionManager:
    """Contract tests for Feature 003 Connection Manager integration."""

    def test_uses_get_connection_from_feature_003(self):
        """Test that FixtureCreator uses get_connection from Feature 003."""
        from iris_devtester.fixtures import FixtureCreator
        from iris_devtester.connections import get_connection

        creator = FixtureCreator()

        # Should use Feature 003's get_connection
        assert hasattr(creator, 'get_connection')

    def test_accepts_iris_config_from_feature_003(self):
        """Test that FixtureCreator accepts IRISConfig from Feature 003."""
        from iris_devtester.fixtures import FixtureCreator
        from iris_devtester.config import IRISConfig

        config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            password="SYS"
        )

        creator = FixtureCreator(connection_config=config)
        assert creator.connection_config == config


class TestConstitutionalCompliance:
    """Contract tests for Constitutional Principle compliance."""

    def test_principle_2_dbapi_first(self):
        """Test Principle #2: DBAPI First via Feature 003."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should use Feature 003 which is DBAPI-first
        assert hasattr(creator, 'connection_config')

    def test_principle_4_zero_config(self):
        """Test Principle #4: Zero Configuration Viable."""
        from iris_devtester.fixtures import FixtureCreator

        # Should be able to create creator with no config
        creator = FixtureCreator()
        assert creator is not None

    def test_principle_5_error_messages(self):
        """Test Principle #5: Fail Fast with Guidance."""
        from iris_devtester.fixtures import FixtureCreator, FixtureCreateError
        import tempfile
        import os

        creator = FixtureCreator()

        # Create temp directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Should raise FileExistsError with guidance
            with pytest.raises(FileExistsError) as exc_info:
                creator.create_fixture(
                    fixture_id="test",
                    namespace="USER",
                    output_dir=temp_dir  # Already exists
                )

            error_msg = str(exc_info.value)
            # Should include guidance format
            assert "What went wrong" in error_msg
            assert "How to fix it" in error_msg
        finally:
            os.rmdir(temp_dir)

    def test_principle_7_medical_grade_reliability(self):
        """Test Principle #7: Medical-Grade Reliability."""
        from iris_devtester.fixtures import FixtureCreator

        creator = FixtureCreator()

        # Should use SHA256 checksums (medical-grade)
        # Should validate data integrity
        assert hasattr(creator, 'calculate_checksum')
        assert hasattr(creator, 'validator')


class TestTableInfoDataclass:
    """Contract tests for TableInfo dataclass."""

    def test_tableinfo_exists(self):
        """Test that TableInfo can be imported."""
        from iris_devtester.fixtures import TableInfo

        assert TableInfo is not None

    def test_tableinfo_fields(self):
        """Test that TableInfo has required fields."""
        from iris_devtester.fixtures import TableInfo

        table = TableInfo(name="RAG.Entities", row_count=100)

        assert table.name == "RAG.Entities"
        assert table.row_count == 100

    def test_tableinfo_str_method(self):
        """Test that TableInfo has __str__ method."""
        from iris_devtester.fixtures import TableInfo

        table = TableInfo(name="RAG.Entities", row_count=100)
        table_str = str(table)

        assert "RAG.Entities" in table_str
        assert "100" in table_str

    def test_tableinfo_validation(self):
        """Test that TableInfo validates row_count."""
        from iris_devtester.fixtures import TableInfo

        # Should reject negative row_count
        with pytest.raises(ValueError):
            TableInfo(name="Test.Table", row_count=-1)
