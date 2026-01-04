"""
CLI commands for .DAT fixture management.

Provides 5 commands:
- fixture create: Export namespace to .DAT fixture
- fixture load: Load .DAT fixture into IRIS
- fixture validate: Validate fixture integrity
- fixture list: List available fixtures
- fixture info: Show detailed fixture information
"""

import click
import sys
from pathlib import Path
from typing import Optional

from iris_devtester.fixtures import (
    FixtureCreator,
    DATFixtureLoader,
    FixtureValidator,
    FixtureManifest,
    FixtureCreateError,
    FixtureLoadError,
    FixtureValidationError,
)


@click.group()
def fixture():
    """Manage IRIS .DAT fixtures for reproducible testing."""
    pass


@fixture.command()
@click.option('--name', required=True, help='Fixture identifier (e.g., "test-entities-100")')
@click.option('--namespace', required=True, help='Source namespace to export (e.g., "USER_TEST_100")')
@click.option('--output', required=True, help='Output directory for fixture')
@click.option('--description', default="", help='Human-readable description')
@click.option('--version', default="1.0.0", help='Semantic version')
@click.option('--verbose', is_flag=True, help='Show detailed progress')
def create(name: str, namespace: str, output: str, description: str, version: str, verbose: bool):
    """Create .DAT fixture by exporting IRIS namespace."""
    try:
        if verbose:
            click.echo("Connecting to IRIS...")

        creator = FixtureCreator()

        if verbose:
            click.echo(f"Exporting namespace '{namespace}' to {output}...")

        manifest = creator.create_fixture(
            fixture_id=name,
            namespace=namespace,
            output_dir=output,
            description=description,
            version=version
        )

        if verbose:
            click.echo("Calculating checksums...")

        # Get fixture size
        validator = FixtureValidator()
        sizes = validator.get_fixture_size(output)

        # Calculate totals
        table_count = len(manifest.tables)
        total_rows = sum(t.row_count for t in manifest.tables)

        click.secho(f"\n✅ Fixture created: {manifest.fixture_id}", fg='green', bold=True)
        click.echo(f"\nLocation: {output}")
        click.echo(f"Tables: {table_count}")
        click.echo(f"Total rows: {total_rows:,}")
        click.echo(f"Size: {sizes['total_mb']:.2f} MB")

        click.echo("\nNext steps:")
        click.echo(f"  1. Validate: iris-devtester fixture validate --fixture {output}")
        click.echo(f"  2. Load: iris-devtester fixture load --fixture {output}")
        click.echo(f"  3. Commit to git: git add {output}")

        sys.exit(0)

    except FileExistsError as e:
        click.secho(f"\n❌ Failed to create fixture", fg='red', bold=True)
        click.echo(f"\n{str(e)}")
        sys.exit(1)

    except FixtureCreateError as e:
        click.secho(f"\n❌ Failed to create fixture", fg='red', bold=True)
        click.echo(f"\n{str(e)}")
        sys.exit(3)

    except ConnectionError as e:
        click.secho(f"\n❌ Failed to create fixture", fg='red', bold=True)
        click.echo(f"\nConnection error: {str(e)}")
        sys.exit(4)

    except Exception as e:
        click.secho(f"\n❌ Failed to create fixture", fg='red', bold=True)
        click.echo(f"\nUnexpected error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@fixture.command()
@click.option('--fixture', required=True, help='Path to fixture directory')
@click.option('--namespace', default=None, help='Target namespace (default: use manifest namespace)')
@click.option('--no-validate', is_flag=True, help='Skip checksum validation (faster, less safe)')
@click.option('--force', is_flag=True, help='Force reload by deleting existing namespace')
@click.option('--verbose', is_flag=True, help='Show detailed progress')
def load(fixture: str, namespace: Optional[str], no_validate: bool, force: bool, verbose: bool):
    """Load .DAT fixture into IRIS database."""
    try:
        if verbose:
            click.echo("Validating fixture...")

        loader = DATFixtureLoader()

        # Validate fixture first
        validate_checksum = not no_validate
        if verbose and validate_checksum:
            click.echo("Validating checksums...")

        if verbose:
            click.echo(f"Loading fixture into namespace...")

        result = loader.load_fixture(
            fixture_path=fixture,
            target_namespace=namespace,
            validate_checksum=validate_checksum,
            force_refresh=force
        )

        # Calculate totals
        table_count = len(result.tables_loaded)
        total_rows = sum(t.row_count for t in result.manifest.tables if t.name in result.tables_loaded)

        click.secho(f"\n✅ Fixture loaded: {result.manifest.fixture_id}", fg='green', bold=True)
        click.echo(f"\nNamespace: {result.namespace}")
        click.echo(f"Tables loaded: {table_count}")
        click.echo(f"Total rows: {total_rows:,}")
        click.echo(f"Time: {result.elapsed_seconds:.2f}s")

        if verbose and result.tables_loaded:
            click.echo("\nTables:")
            for table_name in result.tables_loaded:
                table_info = next((t for t in result.manifest.tables if t.name == table_name), None)
                if table_info:
                    click.echo(f"  - {table_info}")

        click.echo("\nNext steps:")
        click.echo("  Run your tests or query the data")

        sys.exit(0)

    except FileNotFoundError as e:
        click.secho(f"\n❌ Failed to load fixture", fg='red', bold=True)
        click.echo(f"\nFixture not found: {str(e)}")
        sys.exit(1)

    except FixtureValidationError as e:
        click.secho(f"\n❌ Failed to load fixture", fg='red', bold=True)
        click.echo(f"\n{str(e)}")
        sys.exit(2)

    except FixtureLoadError as e:
        click.secho(f"\n❌ Failed to load fixture", fg='red', bold=True)
        click.echo(f"\n{str(e)}")
        click.echo("\nNote: Namespace mount is atomic (all-or-nothing operation)")
        sys.exit(4)

    except ConnectionError as e:
        click.secho(f"\n❌ Failed to load fixture", fg='red', bold=True)
        click.echo(f"\nConnection error: {str(e)}")
        sys.exit(5)

    except Exception as e:
        click.secho(f"\n❌ Failed to load fixture", fg='red', bold=True)
        click.echo(f"\nUnexpected error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@fixture.command()
@click.option('--fixture', required=True, help='Path to fixture directory')
@click.option('--no-checksums', is_flag=True, help='Skip checksum validation (faster)')
@click.option('--recalc', is_flag=True, help='Recalculate checksums and update manifest')
@click.option('--verbose', is_flag=True, help='Show detailed validation results')
def validate(fixture: str, no_checksums: bool, recalc: bool, verbose: bool):
    """Validate fixture integrity (manifest, files, checksums)."""
    try:
        validator = FixtureValidator()

        if recalc:
            if verbose:
                click.echo("Recalculating checksums...")

            manifest = validator.recalculate_checksums(fixture)
            click.secho(f"\n✅ Checksums recalculated", fg='green', bold=True)
            click.echo(f"\nNew checksum: {manifest.checksum}")
            sys.exit(0)

        if verbose:
            click.echo("Loading manifest...")
            click.echo("Checking files...")
            if not no_checksums:
                click.echo("Validating checksums...")

        validate_checksum = not no_checksums
        result = validator.validate_fixture(fixture, validate_checksum=validate_checksum)

        if result.valid:
            manifest = result.manifest
            sizes = validator.get_fixture_size(fixture)

            table_count = len(manifest.tables)
            total_rows = sum(t.row_count for t in manifest.tables)

            click.secho(f"\n✅ Fixture is valid: {manifest.fixture_id}", fg='green', bold=True)
            click.echo(f"\nFixture: {manifest.fixture_id}")
            click.echo(f"Version: {manifest.version}")
            click.echo(f"Schema: {manifest.schema_version}")
            click.echo(f"Tables: {table_count}")
            click.echo(f"Total rows: {total_rows:,}")
            click.echo(f"Size: {sizes['total_mb']:.2f} MB")

            if verbose and manifest.tables:
                click.echo("\nTables:")
                for table in manifest.tables:
                    click.echo(f"  - {table}")

            if result.warnings:
                click.secho(f"\nWarnings ({len(result.warnings)}):", fg='yellow')
                for warning in result.warnings:
                    click.echo(f"  - {warning}")

            sys.exit(0)

        else:
            click.secho(f"\n❌ Fixture validation failed", fg='red', bold=True)
            click.echo(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                click.echo(f"  - {error}")

            if result.warnings:
                click.secho(f"\nWarnings ({len(result.warnings)}):", fg='yellow')
                for warning in result.warnings:
                    click.echo(f"  - {warning}")

            sys.exit(1)

    except FileNotFoundError as e:
        click.secho(f"\n❌ Fixture not found", fg='red', bold=True)
        click.echo(f"\n{str(e)}")
        sys.exit(2)

    except Exception as e:
        click.secho(f"\n❌ Validation failed", fg='red', bold=True)
        click.echo(f"\nUnexpected error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@fixture.command()
@click.argument('path', default="./fixtures")
@click.option('--verbose', is_flag=True, help='Show detailed fixture info')
def list(path: str, verbose: bool):
    """List available fixtures in directory."""
    try:
        fixtures_dir = Path(path)

        if not fixtures_dir.exists():
            click.secho(f"\n❌ Directory not found: {path}", fg='red')
            sys.exit(1)

        # Find all manifest.json files
        manifests = list(fixtures_dir.rglob("manifest.json"))

        if not manifests:
            click.secho(f"\nNo fixtures found in {path}", fg='yellow')
            click.echo(f"\nTo create a fixture:")
            click.echo(f"  iris-devtester fixture create --name my-fixture --namespace USER --output {path}/my-fixture")
            sys.exit(0)

        # Load and display fixtures
        validator = FixtureValidator()
        fixtures = []
        total_size = 0

        for manifest_file in manifests:
            try:
                manifest = FixtureManifest.from_file(str(manifest_file))
                fixture_dir = manifest_file.parent
                sizes = validator.get_fixture_size(str(fixture_dir))
                total_size += sizes['total_bytes']

                fixtures.append({
                    'manifest': manifest,
                    'path': fixture_dir,
                    'size_mb': sizes['total_mb']
                })
            except Exception:
                # Skip invalid fixtures
                continue

        click.echo(f"\nAvailable fixtures in {path}:\n")

        for f in fixtures:
            manifest = f['manifest']
            table_count = len(manifest.tables)
            total_rows = sum(t.row_count for t in manifest.tables)

            click.secho(f"  {manifest.fixture_id}", fg='cyan', bold=True)
            click.echo(f"    Version: {manifest.version}")
            click.echo(f"    Tables: {table_count}, Rows: {total_rows:,}, Size: {f['size_mb']:.2f} MB")
            if manifest.description:
                click.echo(f"    Description: {manifest.description}")
            click.echo(f"    Path: {f['path']}")

            if verbose and manifest.tables:
                click.echo(f"    Tables:")
                for table in manifest.tables[:5]:  # Show first 5
                    click.echo(f"      - {table}")
                if len(manifest.tables) > 5:
                    click.echo(f"      ... and {len(manifest.tables) - 5} more")

            click.echo()

        click.echo(f"Total: {len(fixtures)} fixtures, {total_size / (1024 * 1024):.2f} MB")

        sys.exit(0)

    except Exception as e:
        click.secho(f"\n❌ Failed to list fixtures", fg='red', bold=True)
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)


@fixture.command()
@click.option('--fixture', required=True, help='Path to fixture directory')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def info(fixture: str, output_json: bool):
    """Show detailed information about fixture."""
    try:
        validator = FixtureValidator()
        manifest_file = Path(fixture) / "manifest.json"

        if not manifest_file.exists():
            click.secho(f"\n❌ Fixture not found: {fixture}", fg='red')
            sys.exit(1)

        manifest = FixtureManifest.from_file(str(manifest_file))
        sizes = validator.get_fixture_size(fixture)

        if output_json:
            import json
            data = {
                "fixture_id": manifest.fixture_id,
                "version": manifest.version,
                "description": manifest.description,
                "created_at": manifest.created_at,
                "iris_version": manifest.iris_version,
                "schema_version": manifest.schema_version,
                "namespace": manifest.namespace,
                "tables": [{"name": t.name, "row_count": t.row_count} for t in manifest.tables],
                "size": {
                    "total_mb": sizes['total_mb'],
                    "manifest_kb": sizes['manifest_kb'],
                    "dat_mb": sizes['dat_mb']
                },
                "features": manifest.features,
                "known_queries": manifest.known_queries,
                "location": str(Path(fixture).resolve())
            }
            click.echo(json.dumps(data, indent=2))
        else:
            table_count = len(manifest.tables)
            total_rows = sum(t.row_count for t in manifest.tables)

            click.echo(f"\nFixture: {manifest.fixture_id}")
            click.echo(f"Version: {manifest.version}")
            click.echo(f"Description: {manifest.description}")
            click.echo(f"Created: {manifest.created_at}")
            click.echo(f"IRIS Version: {manifest.iris_version}")
            click.echo(f"Schema Version: {manifest.schema_version}")
            click.echo(f"Namespace: {manifest.namespace}")

            click.echo(f"\nTables ({table_count}, {total_rows:,} total rows):")
            for table in manifest.tables:
                click.echo(f"  - {table}")

            click.echo(f"\nSize:")
            click.echo(f"  Total: {sizes['total_mb']:.2f} MB")
            click.echo(f"  Manifest: {sizes['manifest_kb']:.2f} KB")
            click.echo(f"  DAT file: {sizes['dat_mb']:.2f} MB")

            if manifest.features:
                click.echo(f"\nFeatures:")
                for key, value in manifest.features.items():
                    click.echo(f"  {key}: {value}")

            if manifest.known_queries:
                click.echo(f"\nKnown Queries ({len(manifest.known_queries)}):")
                for query in manifest.known_queries[:3]:
                    click.echo(f"  - {query.get('name', 'Unnamed')}")
                if len(manifest.known_queries) > 3:
                    click.echo(f"  ... and {len(manifest.known_queries) - 3} more")

            click.echo(f"\nLocation: {Path(fixture).resolve()}")

        sys.exit(0)

    except FileNotFoundError as e:
        click.secho(f"\n❌ Fixture not found", fg='red')
        click.echo(f"\n{str(e)}")
        sys.exit(1)

    except Exception as e:
        click.secho(f"\n❌ Failed to show fixture info", fg='red', bold=True)
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    fixture()
