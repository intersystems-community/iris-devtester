"""IRIS .DAT Fixture Validator.

This module provides the FixtureValidator class for validating fixture
integrity including manifest structure, file existence, and SHA256 checksums.
"""

import hashlib
from pathlib import Path
from typing import Optional

from .manifest import (
    FixtureManifest,
    ValidationResult,
    FixtureValidationError,
    ChecksumMismatchError,
)


class FixtureValidator:
    """
    Validates .DAT fixture integrity.

    This is a stateless validator that checks:
    - Manifest structure and required fields
    - File existence (manifest.json, IRIS.DAT)
    - SHA256 checksum matching
    - Fixture size statistics

    Example:
        >>> validator = FixtureValidator()
        >>> result = validator.validate_fixture("./fixtures/test-data")
        >>> if result.valid:
        ...     print("Fixture is valid!")
        >>> else:
        ...     print(f"Errors: {result.errors}")
    """

    def __init__(self):
        """Initialize fixture validator (stateless, no configuration needed)."""
        pass

    def calculate_sha256(self, file_path: str, chunk_size: int = 65536) -> str:
        """
        Calculate SHA256 checksum for a file using streaming.

        Args:
            file_path: Path to file
            chunk_size: Read chunk size in bytes (default: 64KB)

        Returns:
            SHA256 checksum in format "sha256:abc123..."

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read

        Example:
            >>> validator = FixtureValidator()
            >>> checksum = validator.calculate_sha256("./fixtures/test/IRIS.DAT")
            >>> print(checksum)
            sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
        except IOError as e:
            raise IOError(f"Failed to read file {file_path}: {e}")

        return f"sha256:{sha256_hash.hexdigest()}"

    def validate_checksum(
        self, file_path: str, expected_checksum: str, chunk_size: int = 65536
    ) -> bool:
        """
        Validate file checksum against expected value.

        Args:
            file_path: Path to file
            expected_checksum: Expected checksum in format "sha256:..."
            chunk_size: Read chunk size in bytes (default: 64KB)

        Returns:
            True if checksum matches, False otherwise

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If expected_checksum format is invalid
            ChecksumMismatchError: If checksum doesn't match

        Example:
            >>> validator = FixtureValidator()
            >>> is_valid = validator.validate_checksum(
            ...     "./fixtures/test/IRIS.DAT",
            ...     "sha256:abc123..."
            ... )
        """
        if not expected_checksum.startswith("sha256:"):
            raise ValueError(
                f"Invalid checksum format: {expected_checksum}. "
                "Must start with 'sha256:'"
            )

        actual_checksum = self.calculate_sha256(file_path, chunk_size)

        if actual_checksum != expected_checksum:
            raise ChecksumMismatchError(
                f"Checksum mismatch for {file_path}\n"
                f"Expected: {expected_checksum}\n"
                f"Actual:   {actual_checksum}\n\n"
                f"What went wrong:\n"
                f"  The IRIS.DAT file has been modified or corrupted.\n\n"
                f"How to fix it:\n"
                f"  1. Re-download the fixture from version control\n"
                f"  2. Or recalculate checksums: iris-devtester fixture validate --recalc\n"
                f"  3. Or re-create the fixture from the source namespace"
            )

        return True

    def validate_manifest(self, manifest: FixtureManifest) -> ValidationResult:
        """
        Validate manifest structure and contents (no file I/O).

        Args:
            manifest: FixtureManifest to validate

        Returns:
            ValidationResult with errors/warnings

        Example:
            >>> manifest = FixtureManifest.from_file("./fixtures/test/manifest.json")
            >>> validator = FixtureValidator()
            >>> result = validator.validate_manifest(manifest)
            >>> result.raise_if_invalid()
        """
        # Use the manifest's built-in validation
        return manifest.validate()

    def validate_fixture(
        self,
        fixture_path: str,
        validate_checksum: bool = True,
        chunk_size: int = 65536,
    ) -> ValidationResult:
        """
        Validate complete fixture (manifest + files + checksums).

        Args:
            fixture_path: Path to fixture directory
            validate_checksum: Validate IRIS.DAT checksum (default: True, slower but safer)
            chunk_size: Checksum chunk size in bytes (default: 64KB)

        Returns:
            ValidationResult with errors/warnings

        Raises:
            FileNotFoundError: If fixture directory doesn't exist

        Example:
            >>> validator = FixtureValidator()
            >>> result = validator.validate_fixture("./fixtures/test-data")
            >>> if result.valid:
            ...     print("✅ Fixture is valid")
            >>> else:
            ...     for error in result.errors:
            ...         print(f"❌ {error}")
        """
        fixture_dir = Path(fixture_path)
        errors: list[str] = []
        warnings: list[str] = []
        manifest = None

        # Check fixture directory exists
        if not fixture_dir.exists():
            raise FileNotFoundError(f"Fixture directory not found: {fixture_path}")

        if not fixture_dir.is_dir():
            errors.append(f"{fixture_path} is not a directory")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Check manifest.json exists
        manifest_file = fixture_dir / "manifest.json"
        if not manifest_file.exists():
            errors.append("manifest.json not found")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Load and validate manifest structure
        try:
            manifest = FixtureManifest.from_file(str(manifest_file))
            manifest_validation = self.validate_manifest(manifest)
            errors.extend(manifest_validation.errors)
            warnings.extend(manifest_validation.warnings)
        except Exception as e:
            errors.append(f"Failed to load manifest: {e}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Check IRIS.DAT file exists
        dat_file = fixture_dir / manifest.dat_file
        if not dat_file.exists():
            errors.append(f"{manifest.dat_file} not found")
        elif not dat_file.is_file():
            errors.append(f"{manifest.dat_file} is not a file")
        else:
            # Validate checksum if requested
            if validate_checksum:
                try:
                    self.validate_checksum(
                        str(dat_file), manifest.checksum, chunk_size
                    )
                except ChecksumMismatchError:
                    # Re-raise ChecksumMismatchError - it's a critical failure
                    # that requires immediate attention (Constitutional Principle #5)
                    raise
                except Exception as e:
                    errors.append(f"Checksum validation failed: {e}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            manifest=manifest,
        )

    def recalculate_checksums(
        self, fixture_path: str, create_backup: bool = True, chunk_size: int = 65536
    ) -> FixtureManifest:
        """
        Recalculate and update IRIS.DAT checksum in manifest.

        Args:
            fixture_path: Path to fixture directory
            create_backup: Create manifest.json.backup before updating (default: True)
            chunk_size: Checksum chunk size in bytes (default: 64KB)

        Returns:
            Updated FixtureManifest

        Raises:
            FileNotFoundError: If fixture or files not found
            IOError: If cannot write manifest

        Example:
            >>> validator = FixtureValidator()
            >>> manifest = validator.recalculate_checksums("./fixtures/test-data")
            >>> print(f"New checksum: {manifest.checksum}")
        """
        fixture_dir = Path(fixture_path)
        manifest_file = fixture_dir / "manifest.json"

        if not fixture_dir.exists():
            raise FileNotFoundError(f"Fixture directory not found: {fixture_path}")

        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        # Load existing manifest
        manifest = FixtureManifest.from_file(str(manifest_file))

        # Create backup if requested
        if create_backup:
            backup_file = fixture_dir / "manifest.json.backup"
            manifest.to_file(str(backup_file))

        # Recalculate IRIS.DAT checksum
        dat_file = fixture_dir / manifest.dat_file
        if not dat_file.exists():
            raise FileNotFoundError(f"{manifest.dat_file} not found")

        new_checksum = self.calculate_sha256(str(dat_file), chunk_size)
        manifest.checksum = new_checksum

        # Save updated manifest
        manifest.to_file(str(manifest_file))

        return manifest

    def get_fixture_size(self, fixture_path: str) -> dict:
        """
        Get disk usage statistics for fixture.

        Args:
            fixture_path: Path to fixture directory

        Returns:
            Dictionary with size information:
            {
                "total_bytes": int,
                "manifest_bytes": int,
                "dat_bytes": int,
                "total_mb": float,
                "manifest_kb": float,
                "dat_mb": float
            }

        Raises:
            FileNotFoundError: If fixture not found

        Example:
            >>> validator = FixtureValidator()
            >>> sizes = validator.get_fixture_size("./fixtures/test-data")
            >>> print(f"Total: {sizes['total_mb']:.2f} MB")
        """
        fixture_dir = Path(fixture_path)

        if not fixture_dir.exists():
            raise FileNotFoundError(f"Fixture directory not found: {fixture_path}")

        manifest_file = fixture_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        # Load manifest to get DAT file name
        manifest = FixtureManifest.from_file(str(manifest_file))
        dat_file = fixture_dir / manifest.dat_file

        # Get file sizes
        manifest_bytes = manifest_file.stat().st_size if manifest_file.exists() else 0
        dat_bytes = dat_file.stat().st_size if dat_file.exists() else 0
        total_bytes = manifest_bytes + dat_bytes

        return {
            "total_bytes": total_bytes,
            "manifest_bytes": manifest_bytes,
            "dat_bytes": dat_bytes,
            "total_mb": total_bytes / (1024 * 1024),
            "manifest_kb": manifest_bytes / 1024,
            "dat_mb": dat_bytes / (1024 * 1024),
        }
