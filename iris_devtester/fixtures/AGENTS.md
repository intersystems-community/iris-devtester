# fixtures/ — GOF Fixture Management

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Create, load, and validate IRIS test data fixtures using %GOF (Global Object Format). Also supports `$SYSTEM.OBJ` export/import for class definitions. 6 files, 1884 lines.

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `loader.py` | — | `FixtureLoader` — imports GOF data into IRIS namespace (<1s typical) |
| `creator.py` | — | `FixtureCreator` — exports namespace to GOF fixture |
| `obj_export.py` | 504 | `$SYSTEM.OBJ` wrappers: `export_classes()`, `import_classes()`, `export_global()` |
| `validator.py` | — | `FixtureValidator` — SHA256 checksum verification |
| `manifest.py` | — | `FixtureManifest` model, `TableInfo`, error classes |

## FIXTURE FORMAT

```
fixture-dir/
  manifest.json    # Metadata, checksums, table info
  globals.gof      # Global data in IRIS %GOF format
  classes.xml      # Class definitions (optional)
```

## PATTERNS

- **GOF over DAT**: GOF format is portable and version-controllable; DAT files are binary
- **Manifest-driven**: Every fixture has `manifest.json` with SHA256 checksums
- **Backward compat**: `DATFixtureLoader` alias exists for legacy code
- **$SYSTEM.OBJ**: Used for class definition export/import (XML format)

## KEY CLASSES

- `FixtureLoader` — `load_fixture(fixture_path, target_namespace)` → `LoadResult`
- `FixtureCreator` — `create_fixture(fixture_id, namespace, output_dir)` → `FixtureManifest`
- `FixtureValidator` — checksum verification before load
