"""
Contract tests for FixtureValidator API.

These tests validate the public API interface defined in:
specs/004-dat-fixtures/contracts/fixture-validator.yaml

Tests verify:
- Class and method signatures match contract
- Return types are correct
- Exceptions are raised as specified
- API is usable as documented
"""


import pytest

pytestmark = pytest.mark.contract
from pathlib import Path
from typing import Optional


class TestFixtureValidatorClass:
    """Contract tests for FixtureValidator class."""

    def test_class_exists(self):
        """Test that FixtureValidator class can be imported."""
        from iris_devtester.fixtures import FixtureValidator

        assert FixtureValidator is not None

    def test_constructor_signature(self):
        """Test that FixtureValidator() constructor works with no args."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert validator is not None

    def test_class_is_instantiable(self):
        """Test that FixtureValidator can be instantiated."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert isinstance(validator, FixtureValidator)


class TestCalculateSHA256Method:
    """Contract tests for calculate_sha256() method."""

    def test_method_exists(self):
        """Test that calculate_sha256 method exists."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert hasattr(validator, 'calculate_sha256')
        assert callable(validator.calculate_sha256)

    def test_signature_required_params(self):
        """Test calculate_sha256 signature with required parameters."""
        from iris_devtester.fixtures import FixtureValidator
        import tempfile

        validator = FixtureValidator()

        # Create temp file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_path = f.name

        try:
            # Should accept file_path as required param
            result = validator.calculate_sha256(temp_path)
            assert isinstance(result, str)
            assert result.startswith("sha256:")
        finally:
            Path(temp_path).unlink()

    def test_signature_optional_chunk_size(self):
        """Test calculate_sha256 accepts optional chunk_size parameter."""
        from iris_devtester.fixtures import FixtureValidator
        import tempfile

        validator = FixtureValidator()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_path = f.name

        try:
            result = validator.calculate_sha256(temp_path, chunk_size=8192)
            assert isinstance(result, str)
            assert result.startswith("sha256:")
        finally:
            Path(temp_path).unlink()

    def test_raises_filenotfound_for_missing_file(self):
        """Test that calculate_sha256 raises FileNotFoundError for missing file."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()

        with pytest.raises(FileNotFoundError):
            validator.calculate_sha256("/nonexistent/file.dat")


class TestValidateChecksumMethod:
    """Contract tests for validate_checksum() method."""

    def test_method_exists(self):
        """Test that validate_checksum method exists."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert hasattr(validator, 'validate_checksum')
        assert callable(validator.validate_checksum)

    def test_signature_required_params(self):
        """Test validate_checksum signature with required parameters."""
        from iris_devtester.fixtures import FixtureValidator
        import tempfile

        validator = FixtureValidator()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_path = f.name

        try:
            # Get actual checksum
            checksum = validator.calculate_sha256(temp_path)

            # Validate with correct checksum
            result = validator.validate_checksum(temp_path, checksum)
            assert result is True
        finally:
            Path(temp_path).unlink()

    def test_raises_checksum_mismatch_error(self):
        """Test that validate_checksum raises ChecksumMismatchError on mismatch."""
        from iris_devtester.fixtures import FixtureValidator, ChecksumMismatchError
        import tempfile

        validator = FixtureValidator()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test data")
            temp_path = f.name

        try:
            # Use wrong checksum
            wrong_checksum = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

            with pytest.raises(ChecksumMismatchError) as exc_info:
                validator.validate_checksum(temp_path, wrong_checksum)

            # Verify error message contains guidance
            error_msg = str(exc_info.value)
            assert "What went wrong" in error_msg
            assert "How to fix it" in error_msg
        finally:
            Path(temp_path).unlink()


class TestValidateManifestMethod:
    """Contract tests for validate_manifest() method."""

    def test_method_exists(self):
        """Test that validate_manifest method exists."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert hasattr(validator, 'validate_manifest')
        assert callable(validator.validate_manifest)

    def test_signature_accepts_manifest(self):
        """Test validate_manifest accepts FixtureManifest object."""
        from iris_devtester.fixtures import FixtureValidator, FixtureManifest, TableInfo, ValidationResult

        validator = FixtureValidator()

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

        result = validator.validate_manifest(manifest)
        assert isinstance(result, ValidationResult)
        assert result.valid is True


class TestValidateFixtureMethod:
    """Contract tests for validate_fixture() method."""

    def test_method_exists(self):
        """Test that validate_fixture method exists."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert hasattr(validator, 'validate_fixture')
        assert callable(validator.validate_fixture)

    def test_signature_required_params(self):
        """Test validate_fixture signature with required parameters."""
        from iris_devtester.fixtures import FixtureValidator, ValidationResult

        validator = FixtureValidator()

        # Should accept fixture_path (will fail for nonexistent path)
        with pytest.raises(FileNotFoundError):
            validator.validate_fixture("/nonexistent/fixture")

    def test_signature_optional_validate_checksum(self):
        """Test validate_fixture accepts optional validate_checksum parameter."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()

        # Should accept validate_checksum parameter
        with pytest.raises(FileNotFoundError):
            validator.validate_fixture("/nonexistent/fixture", validate_checksum=False)


class TestRecalculateChecksumsMethod:
    """Contract tests for recalculate_checksums() method."""

    def test_method_exists(self):
        """Test that recalculate_checksums method exists."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert hasattr(validator, 'recalculate_checksums')
        assert callable(validator.recalculate_checksums)

    def test_signature_required_params(self):
        """Test recalculate_checksums signature with required parameters."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()

        # Should accept fixture_path (will fail for nonexistent path)
        with pytest.raises(FileNotFoundError):
            validator.recalculate_checksums("/nonexistent/fixture")


class TestGetFixtureSizeMethod:
    """Contract tests for get_fixture_size() method."""

    def test_method_exists(self):
        """Test that get_fixture_size method exists."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()
        assert hasattr(validator, 'get_fixture_size')
        assert callable(validator.get_fixture_size)

    def test_signature_required_params(self):
        """Test get_fixture_size signature with required parameters."""
        from iris_devtester.fixtures import FixtureValidator

        validator = FixtureValidator()

        # Should accept fixture_path (will fail for nonexistent path)
        with pytest.raises(FileNotFoundError):
            validator.get_fixture_size("/nonexistent/fixture")


class TestConstitutionalCompliance:
    """Contract tests for Constitutional Principle compliance."""

    def test_principle_5_error_messages(self):
        """Test that errors follow Principle #5 (Fail Fast with Guidance)."""
        from iris_devtester.fixtures import FixtureValidator, ChecksumMismatchError
        import tempfile

        validator = FixtureValidator()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            wrong_checksum = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

            with pytest.raises(ChecksumMismatchError) as exc_info:
                validator.validate_checksum(temp_path, wrong_checksum)

            error_msg = str(exc_info.value)

            # Verify Constitutional Principle #5 format
            assert "What went wrong:" in error_msg
            assert "How to fix it:" in error_msg
            # Should provide at least 2 remediation steps
            assert "1." in error_msg
            assert "2." in error_msg
        finally:
            Path(temp_path).unlink()

    def test_stateless_validator(self):
        """Test that FixtureValidator is stateless (no IRIS connection required)."""
        from iris_devtester.fixtures import FixtureValidator

        # Should be able to create multiple validators
        validator1 = FixtureValidator()
        validator2 = FixtureValidator()

        # Should not have any connection-related attributes
        assert not hasattr(validator1, 'connection')
        assert not hasattr(validator1, '_connection')
