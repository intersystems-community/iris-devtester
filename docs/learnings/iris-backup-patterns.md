# IRIS Backup Patterns: Export/Import for DAT Fixtures

**Source**: Analysis of IRIS source code at `/databases/sys/cls/SYSTEM/OBJ.xml`
**Feature**: 017-iris-source-insights
**Date**: 2025-12-18

---

## Overview

This document captures official IRIS backup and export/import patterns for use with DAT fixture management. These patterns enable fast, reliable test data loading (10-100x faster than programmatic data creation).

**Key APIs**:
- `$SYSTEM.OBJ.Export()` - Export classes, routines, globals to files
- `$SYSTEM.OBJ.Import()` - Import from files (XML, UDL, %RO, %GOF, etc.)
- `$SYSTEM.OBJ.ExportPackage()` - Export entire package

---

## $SYSTEM.OBJ.Export

### Method Signature

```objectscript
ClassMethod Export(
    items As %String,
    filename As %String,
    qspec As %String = "",
    errorlog As %String = "",
    Charset As %String = ""
) As %Status
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `items` | String | Comma-separated list of items to export (supports wildcards) |
| `filename` | String | Output file path |
| `qspec` | String | Qualifiers (optional) |
| `errorlog` | String | Error log file (optional) |
| `Charset` | String | Character set (optional, default UTF-8) |

### Supported Item Types

| Extension | Type | Description |
|-----------|------|-------------|
| `.cls` | Class | Class definitions |
| `.mac` | Macro | Macro routines |
| `.int` | Routine | Non-macro routines |
| `.inc` | Include | Include files |
| `.gbl` | Global | Global data |
| `.prj` | Project | Studio projects |
| `.obj` | Object | Compiled object code |
| `.pkg` | Package | Package definitions |

### Examples

```objectscript
// Export single class
Set sc = $SYSTEM.OBJ.Export("MyApp.User.cls", "/tmp/user.xml")

// Export multiple classes
Set sc = $SYSTEM.OBJ.Export("MyApp.User.cls,MyApp.Order.cls", "/tmp/classes.xml")

// Export with wildcards
Set sc = $SYSTEM.OBJ.Export("MyApp.*.cls", "/tmp/myapp-classes.xml")

// Export entire package
Set sc = $SYSTEM.OBJ.ExportPackage("MyApp", "/tmp/myapp-all.xml")

// Export global data
Set sc = $SYSTEM.OBJ.Export("MyApp.UserD.gbl", "/tmp/user-data.xml")

// Export with qualifiers
Set sc = $SYSTEM.OBJ.Export("MyApp.*.cls", "/tmp/classes.xml", "/displaylog")
```

---

## $SYSTEM.OBJ.Import

### Method Signature

```objectscript
ClassMethod Import(
    path As %String,
    qualifiers As %String = "",
    selectedItems As %String = "",
    errors As %String = "",
    imported As %String = ""
) As %Status
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | String | File or directory path to import from |
| `qualifiers` | String | Options like /compile, /displaylog |
| `selectedItems` | String | Specific items to import (optional) |
| `errors` | String | Output - error log |
| `imported` | String | Output - list of imported items |

### Common Qualifiers

| Qualifier | Description |
|-----------|-------------|
| `/compile` | Compile after import |
| `/displaylog` | Show import progress |
| `/load=0` | List items without importing |
| `/nodisplay` | Suppress output |
| `/checkuptodate` | Skip unchanged items |

### Examples

```objectscript
// Import and compile
Set sc = $SYSTEM.OBJ.Import("/tmp/classes.xml", "/compile")

// Import with logging
Set sc = $SYSTEM.OBJ.Import("/tmp/classes.xml", "/compile/displaylog")

// Import from directory
Set sc = $SYSTEM.OBJ.Import("/tmp/exports/", "/compile")

// List without importing
Set sc = $SYSTEM.OBJ.Import("/tmp/classes.xml", "/load=0")

// Import specific items from file
Set sc = $SYSTEM.OBJ.Import("/tmp/classes.xml", "/compile", "MyApp.User.cls")
```

---

## Supported Formats

### Format Overview

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| XML | `.xml` | Standard interchange format | Cross-version compatibility |
| UDL | `.cls`, `.mac` | Universal Document Language | Human-readable, git-friendly |
| %RO | `.ro` | Routine output format | Legacy routine exchange |
| %GOF | `.gof` | Global output format | Global data transfer |
| CDL | `.cdl` | Class Definition Language | Legacy class exchange |

### XML Format (Recommended)

The XML format is the most versatile and recommended for DAT fixtures:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Export generator="IRIS" version="26">
<Class name="MyApp.User">
<Description>User class for application</Description>
<Super>%Persistent</Super>
<Property name="Name">
<Type>%String</Type>
</Property>
</Class>
</Export>
```

### Global Output Format (%GOF)

For exporting raw global data (not class storage):

```objectscript
// Export global as %GOF
Do $SYSTEM.OBJ.Export("^MyData.gbl", "/tmp/mydata.gof", "", "", "GOF")

// Import %GOF file
Do ##class(%Library.Global).Import("/tmp/mydata.gof", "", "")
```

---

## Wildcard Patterns

### Pattern Syntax

| Pattern | Matches |
|---------|---------|
| `*.cls` | All classes |
| `MyApp.*.cls` | All classes in MyApp package |
| `MyApp.User*.cls` | Classes starting with User |
| `'MyApp.Test*.cls` | Exclude test classes (apostrophe prefix) |
| `MyApp.*.cls,'MyApp.Test*.cls` | All except test classes |

### Examples

```objectscript
// All classes in package
Set sc = $SYSTEM.OBJ.Export("MyApp.*.cls", "/tmp/myapp.xml")

// All classes and routines
Set sc = $SYSTEM.OBJ.Export("MyApp.*.cls,MyApp.*.mac", "/tmp/myapp-code.xml")

// Exclude test classes
Set items = "MyApp.*.cls,'MyApp.*Test*.cls"
Set sc = $SYSTEM.OBJ.Export(items, "/tmp/myapp-prod.xml")

// Multiple packages
Set sc = $SYSTEM.OBJ.Export("MyApp.*.cls,Utils.*.cls", "/tmp/combined.xml")
```

---

## Global Export

### For Data-Level Backup

Global export is essential for DAT fixtures that contain actual data:

```objectscript
// Export specific global
Set sc = $SYSTEM.OBJ.Export("^MyApp.UserD.gbl", "/tmp/user-data.xml")

// Export class storage globals (D = data, I = index)
Set sc = $SYSTEM.OBJ.Export("MyApp.UserD.gbl,MyApp.UserI.gbl", "/tmp/user-storage.xml")

// Export with %Library.Global for %GOF format
Set sc = ##class(%Library.Global).Export(
    "USER",              // Namespace
    "^MyApp.UserD",      // Global name
    "/tmp/user.gof"      // Output file
)
```

### Import Global Data

```objectscript
// Import from XML
Set sc = $SYSTEM.OBJ.Import("/tmp/user-data.xml")

// Import from %GOF
Set sc = ##class(%Library.Global).Import(
    "USER",              // Target namespace
    "/tmp/user.gof"      // Source file
)
```

### Finding Class Storage Globals

```objectscript
// Get storage global for a persistent class
Set classname = "MyApp.User"
Set storagedef = ##class(%Dictionary.ClassDefinition).%OpenId(classname)
If storagedef {
    Set storage = storagedef.Storages.GetAt(1)
    Write "Data global: ", storage.DataLocation, !
    Write "Index global: ", storage.IndexLocation, !
}
```

---

## Integration with DAT Fixtures

### Fixture Creation Pattern

```python
def create_fixture(container, namespace: str, output_dir: str) -> dict:
    """Create a DAT fixture from namespace contents.

    Returns:
        Manifest dict with exported items
    """
    manifest = {
        "namespace": namespace,
        "created": datetime.now().isoformat(),
        "items": []
    }

    # Export all classes
    classes_script = f'''
        Set ns = "{namespace}"
        ZN ns
        Set sc = $SYSTEM.OBJ.Export("*.cls", "/external/classes.xml")
        Write $Select($$$ISOK(sc):1,1:0)
        Halt
    '''

    result = container.exec_run(
        ['iris', 'session', 'IRIS', '-U', namespace],
        stdin=True,
        input=classes_script.encode()
    )

    if b'1' in result.output:
        manifest["items"].append({"type": "classes", "file": "classes.xml"})

    # Export global data
    globals_script = f'''
        Set ns = "{namespace}"
        ZN ns
        // Export all user globals (not system globals)
        Set global = "^"
        For {{
            Set global = $Order(^$GLOBAL(global))
            Quit:global=""
            Continue:$E(global,1,1)="%"  // Skip system globals
            Set file = "/external/"_$TR(global,"^","")_".gof"
            Do ##class(%Library.Global).Export(ns, global, file)
        }}
        Write 1
        Halt
    '''

    result = container.exec_run(
        ['iris', 'session', 'IRIS', '-U', namespace],
        stdin=True,
        input=globals_script.encode()
    )

    return manifest
```

### Fixture Loading Pattern

```python
def load_fixture(container, fixture_path: str, target_namespace: str) -> bool:
    """Load a DAT fixture into target namespace.

    Args:
        container: Docker container
        fixture_path: Path to fixture directory (mounted in container)
        target_namespace: Namespace to load into

    Returns:
        True if successful
    """
    load_script = f'''
        Set ns = "{target_namespace}"
        ZN ns

        // Import classes and compile
        Set sc = $SYSTEM.OBJ.Import("{fixture_path}/classes.xml", "/compile")
        If $$$ISERR(sc) {{
            Write 0
            Halt
        }}

        // Import global data files
        Set file = ""
        For {{
            Set file = $ZSEARCH("{fixture_path}/*.gof")
            Quit:file=""
            Set sc = ##class(%Library.Global).Import(ns, file)
        }}

        Write 1
        Halt
    '''

    result = container.exec_run(
        ['iris', 'session', 'IRIS', '-U', '%SYS'],
        stdin=True,
        input=load_script.encode()
    )

    return b'1' in result.output
```

### Checksum Validation

```python
import hashlib

def validate_fixture(fixture_path: str, manifest: dict) -> bool:
    """Validate fixture integrity using SHA256 checksums.

    Returns:
        True if all files match expected checksums
    """
    for item in manifest.get("items", []):
        file_path = os.path.join(fixture_path, item["file"])

        if not os.path.exists(file_path):
            return False

        with open(file_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        if actual_hash != item.get("checksum"):
            return False

    return True
```

---

## Performance Considerations

### Export Performance

| Approach | Speed | Notes |
|----------|-------|-------|
| XML export | Fast | Single file, good for <1000 items |
| %GOF export | Faster | Binary format, best for large globals |
| Per-class export | Slow | Multiple files, use for incremental |

### Import Performance

| Approach | Speed | Notes |
|----------|-------|-------|
| Bulk import | 10-100x faster | vs programmatic creation |
| With /compile | Slower | But necessary for classes |
| Without /compile | Faster | Use for data-only imports |

### Best Practices

1. **Use %GOF for large data** - Binary format is faster than XML
2. **Separate code from data** - Export classes and globals separately
3. **Skip compilation when possible** - Use /compile only for classes
4. **Validate checksums** - Ensure data integrity
5. **Use wildcards wisely** - More specific = faster

---

## Cross-References

### Related Learning Documents

- [dat-fixtures-docker-exec-pattern.md](dat-fixtures-docker-exec-pattern.md) - Docker exec patterns
- [dat-restore-database-isolation-problem.md](dat-restore-database-isolation-problem.md) - Isolation issues

### Source Files Analyzed

- `/databases/sys/cls/SYSTEM/OBJ.xml` - Export/Import methods
- `/databases/sys/cls/%Library/Global.xml` - Global operations

---

## Summary

| Operation | Pattern |
|-----------|---------|
| Export classes | `$SYSTEM.OBJ.Export("Package.*.cls", "/path/file.xml")` |
| Export globals | `##class(%Library.Global).Export(ns, "^GlobalName", "/path/file.gof")` |
| Import with compile | `$SYSTEM.OBJ.Import("/path/file.xml", "/compile")` |
| Import globals | `##class(%Library.Global).Import(ns, "/path/file.gof")` |
| Export package | `$SYSTEM.OBJ.ExportPackage("Package", "/path/file.xml")` |

**Remember**: Use %GOF format for large global data, XML for classes and code.
