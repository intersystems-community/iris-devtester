"""IRIS $SYSTEM.OBJ Export/Import Utilities.

This module provides utilities for exporting and importing IRIS objects using
the official $SYSTEM.OBJ.Export and $SYSTEM.OBJ.Import APIs. These patterns
are documented in docs/learnings/iris-backup-patterns.md.

These utilities complement the IRIS.DAT-based fixtures by providing:
- Granular class/routine export (vs. whole database)
- %GOF format for efficient global data transfer
- XML format for cross-version compatibility
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result from an export operation.

    Attributes:
        success: True if export succeeded
        output_file: Path to exported file
        items_exported: Number of items exported
        message: Human-readable status message
        raw_output: Raw ObjectScript output for debugging
    """

    success: bool
    output_file: str
    items_exported: int
    message: str
    raw_output: str = ""


@dataclass
class ImportResult:
    """Result from an import operation.

    Attributes:
        success: True if import succeeded
        items_imported: Number of items imported
        message: Human-readable status message
        raw_output: Raw ObjectScript output for debugging
    """

    success: bool
    items_imported: int
    message: str
    raw_output: str = ""


def export_classes(
    container: Any,
    namespace: str,
    pattern: str,
    output_file: str,
    compile: bool = False,
) -> ExportResult:
    """Export classes using $SYSTEM.OBJ.Export.

    Source: docs/learnings/iris-backup-patterns.md

    Args:
        container: IRISContainer instance
        namespace: Source namespace
        pattern: Class pattern (e.g., "MyApp.*.cls", "*.cls")
        output_file: Path inside container for output (e.g., "/tmp/classes.xml")
        compile: Whether to compile after export (default: False)

    Returns:
        ExportResult with success status and details

    Example:
        >>> with IRISContainer.community() as iris:
        ...     result = export_classes(
        ...         iris, "USER", "MyApp.*.cls", "/tmp/classes.xml"
        ...     )
        ...     if result.success:
        ...         print(f"Exported {result.items_exported} classes")
    """
    qualifiers = "/displaylog" + ("/compile" if compile else "")

    objectscript = f'''
ZN "{namespace}"
Set sc = $SYSTEM.OBJ.Export("{pattern}", "{output_file}", "{qualifiers}")
Write $Select(sc=1:1,1:0)
Halt
'''

    try:
        container_name = container.get_container_name()

        cmd = [
            "docker", "exec", container_name, "sh", "-c",
            f'iris session IRIS -U %SYS << "EOF"\n{objectscript}\nEOF'
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        raw_output = result.stdout + result.stderr
        success = result.returncode == 0 and "1" in result.stdout

        if success:
            logger.info(f"Exported classes matching '{pattern}' to {output_file}")
            return ExportResult(
                success=True,
                output_file=output_file,
                items_exported=_count_exported_items(raw_output),
                message=f"Exported classes to {output_file}",
                raw_output=raw_output,
            )
        else:
            return ExportResult(
                success=False,
                output_file=output_file,
                items_exported=0,
                message=f"Export failed: {raw_output[:200]}",
                raw_output=raw_output,
            )

    except subprocess.TimeoutExpired:
        return ExportResult(
            success=False,
            output_file=output_file,
            items_exported=0,
            message="Export timed out after 120 seconds",
            raw_output="",
        )
    except Exception as e:
        return ExportResult(
            success=False,
            output_file=output_file,
            items_exported=0,
            message=f"Export error: {e}",
            raw_output="",
        )


def import_classes(
    container: Any,
    namespace: str,
    input_file: str,
    compile: bool = True,
) -> ImportResult:
    """Import classes using $SYSTEM.OBJ.Import.

    Source: docs/learnings/iris-backup-patterns.md

    Args:
        container: IRISContainer instance
        namespace: Target namespace
        input_file: Path inside container to import file
        compile: Whether to compile after import (default: True)

    Returns:
        ImportResult with success status and details

    Example:
        >>> with IRISContainer.community() as iris:
        ...     result = import_classes(
        ...         iris, "USER", "/tmp/classes.xml", compile=True
        ...     )
        ...     if result.success:
        ...         print(f"Imported {result.items_imported} classes")
    """
    qualifiers = "/displaylog" + ("/compile" if compile else "")

    objectscript = f'''
ZN "{namespace}"
Set sc = $SYSTEM.OBJ.Import("{input_file}", "{qualifiers}")
Write $Select(sc=1:1,1:0)
Halt
'''

    try:
        container_name = container.get_container_name()

        cmd = [
            "docker", "exec", container_name, "sh", "-c",
            f'iris session IRIS -U %SYS << "EOF"\n{objectscript}\nEOF'
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        raw_output = result.stdout + result.stderr
        success = result.returncode == 0 and "1" in result.stdout

        if success:
            logger.info(f"Imported classes from {input_file} into {namespace}")
            return ImportResult(
                success=True,
                items_imported=_count_exported_items(raw_output),
                message=f"Imported classes from {input_file}",
                raw_output=raw_output,
            )
        else:
            return ImportResult(
                success=False,
                items_imported=0,
                message=f"Import failed: {raw_output[:200]}",
                raw_output=raw_output,
            )

    except subprocess.TimeoutExpired:
        return ImportResult(
            success=False,
            items_imported=0,
            message="Import timed out after 120 seconds",
            raw_output="",
        )
    except Exception as e:
        return ImportResult(
            success=False,
            items_imported=0,
            message=f"Import error: {e}",
            raw_output="",
        )


def export_global(
    container: Any,
    namespace: str,
    global_name: str,
    output_file: str,
) -> ExportResult:
    """Export a global using ##class(%Library.Global).Export (%GOF format).

    Source: docs/learnings/iris-backup-patterns.md

    The %GOF (Global Output Format) is optimized for global data transfer
    and is faster than XML for large datasets.

    Args:
        container: IRISContainer instance
        namespace: Source namespace
        global_name: Global name (e.g., "^MyData", "^MyApp.UserD")
        output_file: Path inside container for output (e.g., "/tmp/data.gof")

    Returns:
        ExportResult with success status and details

    Example:
        >>> with IRISContainer.community() as iris:
        ...     result = export_global(
        ...         iris, "USER", "^MyApp.UserD", "/tmp/users.gof"
        ...     )
        ...     if result.success:
        ...         print(f"Exported global to {result.output_file}")
    """
    # Normalize global name (remove leading ^ if present for comparison)
    clean_global = global_name.lstrip("^")

    objectscript = f'''
Set sc = ##class(%Library.Global).Export("{namespace}", "^{clean_global}", "{output_file}")
Write $Select(sc=1:1,1:0)
Halt
'''

    try:
        container_name = container.get_container_name()

        cmd = [
            "docker", "exec", container_name, "sh", "-c",
            f'iris session IRIS -U %SYS << "EOF"\n{objectscript}\nEOF'
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        raw_output = result.stdout + result.stderr
        success = result.returncode == 0 and "1" in result.stdout

        if success:
            logger.info(f"Exported global ^{clean_global} to {output_file}")
            return ExportResult(
                success=True,
                output_file=output_file,
                items_exported=1,
                message=f"Exported ^{clean_global} to {output_file}",
                raw_output=raw_output,
            )
        else:
            return ExportResult(
                success=False,
                output_file=output_file,
                items_exported=0,
                message=f"Export failed: {raw_output[:200]}",
                raw_output=raw_output,
            )

    except subprocess.TimeoutExpired:
        return ExportResult(
            success=False,
            output_file=output_file,
            items_exported=0,
            message="Export timed out after 120 seconds",
            raw_output="",
        )
    except Exception as e:
        return ExportResult(
            success=False,
            output_file=output_file,
            items_exported=0,
            message=f"Export error: {e}",
            raw_output="",
        )


def import_global(
    container: Any,
    namespace: str,
    input_file: str,
) -> ImportResult:
    """Import a global using ##class(%Library.Global).Import.

    Source: docs/learnings/iris-backup-patterns.md

    Args:
        container: IRISContainer instance
        namespace: Target namespace
        input_file: Path inside container to %GOF file

    Returns:
        ImportResult with success status and details

    Example:
        >>> with IRISContainer.community() as iris:
        ...     result = import_global(
        ...         iris, "USER", "/tmp/users.gof"
        ...     )
        ...     if result.success:
        ...         print("Imported global data")
    """
    objectscript = f'''
Set sc = ##class(%Library.Global).Import("{namespace}", "{input_file}")
Write $Select(sc=1:1,1:0)
Halt
'''

    try:
        container_name = container.get_container_name()

        cmd = [
            "docker", "exec", container_name, "sh", "-c",
            f'iris session IRIS -U %SYS << "EOF"\n{objectscript}\nEOF'
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        raw_output = result.stdout + result.stderr
        success = result.returncode == 0 and "1" in result.stdout

        if success:
            logger.info(f"Imported global from {input_file} into {namespace}")
            return ImportResult(
                success=True,
                items_imported=1,
                message=f"Imported global from {input_file}",
                raw_output=raw_output,
            )
        else:
            return ImportResult(
                success=False,
                items_imported=0,
                message=f"Import failed: {raw_output[:200]}",
                raw_output=raw_output,
            )

    except subprocess.TimeoutExpired:
        return ImportResult(
            success=False,
            items_imported=0,
            message="Import timed out after 120 seconds",
            raw_output="",
        )
    except Exception as e:
        return ImportResult(
            success=False,
            items_imported=0,
            message=f"Import error: {e}",
            raw_output="",
        )


def export_package(
    container: Any,
    namespace: str,
    package_name: str,
    output_file: str,
) -> ExportResult:
    """Export an entire package using $SYSTEM.OBJ.ExportPackage.

    Source: docs/learnings/iris-backup-patterns.md

    Args:
        container: IRISContainer instance
        namespace: Source namespace
        package_name: Package to export (e.g., "MyApp")
        output_file: Path inside container for output

    Returns:
        ExportResult with success status and details

    Example:
        >>> with IRISContainer.community() as iris:
        ...     result = export_package(
        ...         iris, "USER", "MyApp", "/tmp/myapp.xml"
        ...     )
        ...     if result.success:
        ...         print(f"Exported package to {result.output_file}")
    """
    objectscript = f'''
ZN "{namespace}"
Set sc = $SYSTEM.OBJ.ExportPackage("{package_name}", "{output_file}")
Write $Select(sc=1:1,1:0)
Halt
'''

    try:
        container_name = container.get_container_name()

        cmd = [
            "docker", "exec", container_name, "sh", "-c",
            f'iris session IRIS -U %SYS << "EOF"\n{objectscript}\nEOF'
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        raw_output = result.stdout + result.stderr
        success = result.returncode == 0 and "1" in result.stdout

        if success:
            logger.info(f"Exported package {package_name} to {output_file}")
            return ExportResult(
                success=True,
                output_file=output_file,
                items_exported=_count_exported_items(raw_output),
                message=f"Exported package {package_name} to {output_file}",
                raw_output=raw_output,
            )
        else:
            return ExportResult(
                success=False,
                output_file=output_file,
                items_exported=0,
                message=f"Export failed: {raw_output[:200]}",
                raw_output=raw_output,
            )

    except subprocess.TimeoutExpired:
        return ExportResult(
            success=False,
            output_file=output_file,
            items_exported=0,
            message="Export timed out after 120 seconds",
            raw_output="",
        )
    except Exception as e:
        return ExportResult(
            success=False,
            output_file=output_file,
            items_exported=0,
            message=f"Export error: {e}",
            raw_output="",
        )


def _count_exported_items(output: str) -> int:
    """Count exported items from log output.

    Args:
        output: Raw ObjectScript output

    Returns:
        Number of items exported (estimated)
    """
    # Look for lines like "Exporting: MyApp.User.cls" or similar
    count = output.lower().count("exporting") + output.lower().count("loading")
    return max(count, 1) if count > 0 else 0
