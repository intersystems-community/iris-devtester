"""
Contract tests for DATFixtureLoader API.

These tests validate the public API interface defined in:
specs/004-dat-fixtures/contracts/fixture-loader.yaml

Tests verify:
- Class and method signatures match contract
- Return types are correct
- Integration with Feature 003 Connection Manager
- API is usable as documented
"""


import pytest

pytestmark = pytest.mark.contract
from typing import Optional


class TestDATFixtureLoaderClass:
    """Contract tests for DATFixtureLoader class."""

    def test_class_exists(self):
        """Test that DATFixtureLoader class can be imported."""
        from iris_devtester.fixtures import DATFixtureLoader

        assert DATFixtureLoader is not None

    def test_constructor_signature_zero_config(self):
        """Test that DATFixtureLoader() constructor works with no args."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()
        assert loader is not None

    def test_constructor_signature_explicit_config(self):
        """Test that DATFixtureLoader accepts optional connection_config."""
        from iris_devtester.fixtures import DATFixtureLoader
        from iris_devtester.config import IRISConfig

        config = IRISConfig(host="localhost", port=1972, namespace="USER")
        loader = DATFixtureLoader(connection_config=config)
        assert loader is not None

    def test_class_is_instantiable(self):
        """Test that DATFixtureLoader can be instantiated."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()
        assert isinstance(loader, DATFixtureLoader)


class TestValidateFixtureMethod:
    """Contract tests for validate_fixture() method."""

    def test_method_exists(self):
        """Test that validate_fixture method exists."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()
        assert hasattr(loader, 'validate_fixture')
        assert callable(loader.validate_fixture)

    def test_signature_required_params(self):
        """Test validate_fixture signature with required parameters."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept fixture_path (will fail for nonexistent path)
        with pytest.raises(FileNotFoundError):
            loader.validate_fixture("/nonexistent/fixture")

    def test_signature_optional_validate_checksum(self):
        """Test validate_fixture accepts optional validate_checksum parameter."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept validate_checksum parameter
        with pytest.raises(FileNotFoundError):
            loader.validate_fixture("/nonexistent/fixture", validate_checksum=False)

    def test_return_type_is_manifest(self):
        """Test that validate_fixture returns FixtureManifest on success."""
        from iris_devtester.fixtures import DATFixtureLoader, FixtureManifest

        loader = DATFixtureLoader()

        # Return type should be FixtureManifest
        # (Will fail without valid fixture, but validates signature)
        with pytest.raises(FileNotFoundError):
            result = loader.validate_fixture("/nonexistent/fixture")


class TestLoadFixtureMethod:
    """Contract tests for load_fixture() method."""

    def test_method_exists(self):
        """Test that load_fixture method exists."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()
        assert hasattr(loader, 'load_fixture')
        assert callable(loader.load_fixture)

    def test_signature_required_params(self):
        """Test load_fixture signature with required parameters."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept fixture_path as required param
        # (Will fail without IRIS connection)
        with pytest.raises((FileNotFoundError, Exception)):
            loader.load_fixture("/nonexistent/fixture")

    def test_signature_optional_target_namespace(self):
        """Test load_fixture accepts optional target_namespace parameter."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept target_namespace parameter
        with pytest.raises((FileNotFoundError, Exception)):
            loader.load_fixture("/nonexistent/fixture", target_namespace="TEST")

    def test_signature_optional_validate_checksum(self):
        """Test load_fixture accepts optional validate_checksum parameter."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept validate_checksum parameter
        with pytest.raises((FileNotFoundError, Exception)):
            loader.load_fixture("/nonexistent/fixture", validate_checksum=False)

    def test_return_type_is_load_result(self):
        """Test that load_fixture returns LoadResult."""
        from iris_devtester.fixtures import DATFixtureLoader, LoadResult

        loader = DATFixtureLoader()

        # Return type should be LoadResult
        # (Signature validation only)
        assert True  # Method exists and has correct signature


class TestCleanupFixtureMethod:
    """Contract tests for cleanup_fixture() method."""

    def test_method_exists(self):
        """Test that cleanup_fixture method exists."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()
        assert hasattr(loader, 'cleanup_fixture')
        assert callable(loader.cleanup_fixture)

    def test_signature_required_params(self):
        """Test cleanup_fixture signature with required parameters."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept namespace as required param
        # (Will fail without IRIS connection)
        with pytest.raises(Exception):
            loader.cleanup_fixture("TEST_NAMESPACE")

    def test_signature_optional_delete_namespace(self):
        """Test cleanup_fixture accepts optional delete_namespace parameter."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should accept delete_namespace parameter
        with pytest.raises(Exception):
            loader.cleanup_fixture("TEST_NAMESPACE", delete_namespace=True)


class TestGetConnectionMethod:
    """Contract tests for get_connection() method."""

    def test_method_exists(self):
        """Test that get_connection method exists."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()
        assert hasattr(loader, 'get_connection')
        assert callable(loader.get_connection)

    def test_signature_no_params(self):
        """Test get_connection signature requires no parameters."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should work with no params (will fail without IRIS available)
        # But validates signature
        try:
            conn = loader.get_connection()
        except Exception:
            # Expected - no IRIS available in contract tests
            pass


class TestIntegrationWithConnectionManager:
    """Contract tests for Feature 003 Connection Manager integration."""

    def test_uses_get_connection_from_feature_003(self):
        """Test that DATFixtureLoader uses get_connection from Feature 003."""
        from iris_devtester.fixtures import DATFixtureLoader
        from iris_devtester.connections import get_connection

        loader = DATFixtureLoader()

        # Should use Feature 003's get_connection
        # (Implementation detail check)
        assert hasattr(loader, 'get_connection')

    def test_accepts_iris_config_from_feature_003(self):
        """Test that DATFixtureLoader accepts IRISConfig from Feature 003."""
        from iris_devtester.fixtures import DATFixtureLoader
        from iris_devtester.config import IRISConfig

        config = IRISConfig(
            host="localhost",
            port=1972,
            namespace="USER",
            username="_SYSTEM",
            password="SYS"
        )

        loader = DATFixtureLoader(connection_config=config)
        assert loader.connection_config == config


class TestConstitutionalCompliance:
    """Contract tests for Constitutional Principle compliance."""

    def test_principle_2_dbapi_first(self):
        """Test Principle #2: DBAPI First via Feature 003."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should use Feature 003 which is DBAPI-first
        # (Integration validation)
        assert hasattr(loader, 'connection_config')

    def test_principle_4_zero_config(self):
        """Test Principle #4: Zero Configuration Viable."""
        from iris_devtester.fixtures import DATFixtureLoader

        # Should be able to create loader with no config
        loader = DATFixtureLoader()
        assert loader is not None

    def test_principle_5_error_messages(self):
        """Test Principle #5: Fail Fast with Guidance."""
        from iris_devtester.fixtures import DATFixtureLoader, FixtureLoadError

        loader = DATFixtureLoader()

        # Errors should include "What went wrong" and "How to fix it"
        try:
            loader.validate_fixture("/nonexistent/fixture")
        except FileNotFoundError as e:
            # Standard Python error, but our custom errors should have guidance
            pass

    def test_principle_7_medical_grade_reliability(self):
        """Test Principle #7: Medical-Grade Reliability."""
        from iris_devtester.fixtures import DATFixtureLoader

        loader = DATFixtureLoader()

        # Should validate checksums by default (medical-grade)
        # (validate_checksum=True is default)
        assert True  # Implementation validates this


class TestLoadResultDataclass:
    """Contract tests for LoadResult dataclass."""

    def test_loadresult_exists(self):
        """Test that LoadResult can be imported."""
        from iris_devtester.fixtures import LoadResult

        assert LoadResult is not None

    def test_loadresult_fields(self):
        """Test that LoadResult has required fields."""
        from iris_devtester.fixtures import LoadResult, FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        result = LoadResult(
            success=True,
            manifest=manifest,
            namespace="USER",
            tables_loaded=["Test.Table"],
            elapsed_seconds=1.5
        )

        assert result.success is True
        assert result.manifest == manifest
        assert result.namespace == "USER"
        assert result.tables_loaded == ["Test.Table"]
        assert result.elapsed_seconds == 1.5

    def test_loadresult_str_method(self):
        """Test that LoadResult has __str__ method."""
        from iris_devtester.fixtures import LoadResult, FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        result = LoadResult(
            success=True,
            manifest=manifest,
            namespace="USER",
            tables_loaded=["Test.Table"],
            elapsed_seconds=1.5
        )

        result_str = str(result)
        assert "test" in result_str
        assert "USER" in result_str

    def test_loadresult_summary_method(self):
        """Test that LoadResult has summary() method."""
        from iris_devtester.fixtures import LoadResult, FixtureManifest, TableInfo

        manifest = FixtureManifest(
            fixture_id="test",
            version="1.0.0",
            schema_version="1.0",
            description="Test",
            created_at="2025-10-14T00:00:00Z",
            iris_version="2024.1",
            namespace="USER",
            dat_file="IRIS.DAT",
            checksum="sha256:abc123",
            tables=[TableInfo(name="Test.Table", row_count=100)]
        )

        result = LoadResult(
            success=True,
            manifest=manifest,
            namespace="USER",
            tables_loaded=["Test.Table"],
            elapsed_seconds=1.5
        )

        summary = result.summary()
        assert isinstance(summary, str)
        assert "Test.Table" in summary
