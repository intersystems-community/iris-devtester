"""
Namespace management utilities for InterSystems IRIS.

Implements implicit namespace creation ("SQLite-level ergonomics").
"""

import hashlib
import logging
import os
import subprocess
from typing import Optional

from iris_devtester.config import IRISConfig

logger = logging.getLogger(__name__)


def get_project_id(path: Optional[str] = None) -> str:
    """Generate a stable Project ID from a directory path."""
    target_path = os.path.abspath(path or os.getcwd())
    h = hashlib.sha256(target_path.encode()).hexdigest()
    return h[:11].upper()


def get_project_namespace(path: Optional[str] = None) -> str:
    """Generate a valid IRIS namespace name for a project."""
    return f"P{get_project_id(path)}"


def check_namespace_exists(container_name: str, namespace: str) -> bool:
    """
    Check if a namespace exists in an IRIS container.

    Args:
        container_name: Name of the Docker container.
        namespace: Namespace name to check.

    Returns:
        True if namespace exists, False otherwise.
    """
    script = f'Write ##class(Config.Namespaces).Exists("{namespace}")'
    try:
        cmd = [
            "docker",
            "exec",
            "-u",
            "irisowner",
            "-i",
            container_name,
            "iris",
            "session",
            "IRIS",
            "-U",
            "%SYS",
        ]
        result = subprocess.run(
            cmd, input=f"{script}\nHalt\n".encode("utf-8"), capture_output=True, timeout=10
        )
        # Returns "1" if exists, "0" if not.
        return "1" in result.stdout.decode()
    except Exception as e:
        logger.debug(f"Failed to check namespace existence: {e}")
        return False


def create_namespace(container_name: str, namespace: str) -> bool:
    """
    Create a new namespace and associated database in an IRIS container.

    Args:
        container_name: Name of the Docker container.
        namespace: Namespace name to create.

    Returns:
        True if creation succeeded, False otherwise.
    """
    # Use Durable %SYS path if possible, otherwise default to mgr/
    # (Feature 026: The Dev Instance uses /iris/data)
    db_dir = f"/usr/irissys/mgr/{namespace.lower()}"
    
    # Try to detect if we should use a different base directory
    detect_dir_script = 'Write $Get(%ISC["DataDir"], "/usr/irissys/mgr/")'
    try:
        detect_cmd = [
            "docker", "exec", "-u", "irisowner", "-i", container_name,
            "iris", "session", "IRIS", "-U", "%SYS"
        ]
        res = subprocess.run(
            detect_cmd, input=f"{detect_dir_script}\nHalt\n".encode(), 
            capture_output=True, timeout=10
        )
        base_dir = res.stdout.decode().strip().split("\n")[-1]
        if base_dir and base_dir.endswith("/"):
            db_dir = f"{base_dir}{namespace.lower()}"
        elif base_dir:
            db_dir = f"{base_dir}/{namespace.lower()}"
    except Exception:
        pass

    script = f"""
 Set ns="{namespace}"
 Set dbDir="{db_dir}"
 If '##class(%File).DirectoryExists(dbDir) Do ##class(%File).CreateDirectoryChain(dbDir)
 Set db=##class(SYS.Database).%New() Set db.Directory=dbDir Do db.%Save()
 Do ##class(Config.Databases).Create(ns,dbDir)
 Set p("Globals")=ns,p("Routines")=ns Do ##class(Config.Namespaces).Create(ns,.p)
 Write "SUCCESS"
"""
    try:
        cmd = [
            "docker",
            "exec",
            "-u",
            "irisowner",
            "-i",
            container_name,
            "iris",
            "session",
            "IRIS",
            "-U",
            "%SYS",
        ]
        result = subprocess.run(
            cmd, input=f"{script}\nHalt\n".encode("utf-8"), capture_output=True, timeout=30
        )
        success = "SUCCESS" in result.stdout.decode()
        if success:
            logger.info(f"✓ Created namespace '{namespace}' in container '{container_name}'")
            # Ensure CallIn is enabled for the new namespace (actually it's system-wide but good practice)
            from iris_devtester.utils.enable_callin import enable_callin_service

            enable_callin_service(container_name)
        else:
            logger.error(f"Failed to create namespace '{namespace}': {result.stderr.decode()}")
        return success
    except Exception as e:
        logger.error(f"Error creating namespace '{namespace}': {e}")
        return False


def ensure_namespace_exists(config: IRISConfig) -> bool:
    """
    Ensure the requested namespace exists, creating it if necessary and allowed.

    Args:
        config: IRIS configuration object.

    Returns:
        True if namespace exists (or was created), False if it doesn't exist and couldn't be created.
    """
    # Hybrid Smart Default
    auto_create = config.auto_create
    if auto_create is None:
        if config.host in ["localhost", "127.0.0.1"]:
            auto_create = True
        else:
            auto_create = False

    if not auto_create:
        return True  # Proceed anyway, connection will fail later if NS missing

    container_name = config.container_name or "iris_db"

    # Only attempt auto-creation if we're on localhost or have a container_name
    # (Actually the spec says auto-create on localhost/containers)
    if config.host not in ["localhost", "127.0.0.1"] and not config.container_name:
        return True

    if not check_namespace_exists(container_name, config.namespace):
        logger.info(f"Namespace '{config.namespace}' not found. Attempting auto-creation...")
        return create_namespace(container_name, config.namespace)

    return True
