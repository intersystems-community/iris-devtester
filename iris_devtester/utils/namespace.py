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

# Optional iris module — may not be installed in all environments
try:
    import iris as _iris_module
except ImportError:
    _iris_module = None


def get_project_id(path: Optional[str] = None) -> str:
    """Generate a stable Project ID from a directory path."""
    target_path = os.path.abspath(path or os.getcwd())
    h = hashlib.sha256(target_path.encode()).hexdigest()
    return h[:11].upper()


def get_project_namespace(path: Optional[str] = None) -> str:
    """Generate a valid IRIS namespace name for a project."""
    return f"P{get_project_id(path)}"


def check_namespace_via_iris_connect(config: IRISConfig, namespace: str) -> bool:
    """
    Check if a namespace exists using iris.connect() to %SYS.

    Connects to the %SYS namespace using the credentials from the provided
    config, then calls Config.Namespaces.Exists() to verify namespace existence.
    This avoids requiring Docker exec access.

    Args:
        config: IRIS configuration providing host, port, username, password.
        namespace: Namespace name to check.

    Returns:
        True if namespace exists, False otherwise (including on any error).
    """
    if _iris_module is None:
        logger.warning(
            f"Cannot verify namespace '{namespace}': iris module not available"
        )
        return False

    try:
        conn = _iris_module.connect(
            hostname=config.host,
            port=config.port,
            namespace="%SYS",
            username=config.username,
            password=config.password,
        )
        try:
            iris_obj = _iris_module.createIRIS(conn)
            exists = iris_obj.classMethodValue("Config.Namespaces", "Exists", namespace)
            if exists:
                logger.debug(f"Namespace '{namespace}' verified via iris.connect()")
            else:
                logger.debug(f"Namespace '{namespace}' not found via iris.connect()")
            return bool(exists)
        finally:
            conn.close()
    except Exception as e:
        err_str = str(e).lower()
        if "access denied" in err_str or "privilege" in err_str or "protect" in err_str:
            logger.warning(
                f"Cannot verify namespace '{namespace}': %%SYS access denied "
                f"for user '{config.username}'"
            )
        else:
            logger.warning(f"Cannot verify namespace '{namespace}': connection failed ({e})")
        return False


def create_namespace_via_iris_connect(config: IRISConfig, namespace: str) -> bool:
    """
    Create a namespace using iris.connect() to %SYS.

    Connects to the %SYS namespace and uses Config.Namespaces.Create() to
    create the namespace. Uses the simplified creation pattern established
    in the codebase (namespace name only; IRIS provides sensible defaults).

    For full database + namespace setup (custom directory, database creation),
    use the Docker exec path via create_namespace() instead.

    Args:
        config: IRIS configuration providing host, port, username, password.
        namespace: Namespace name to create.

    Returns:
        True if namespace was created successfully, False otherwise.
    """
    if _iris_module is None:
        logger.warning(
            f"Cannot create namespace '{namespace}': iris module not available"
        )
        return False

    try:
        conn = _iris_module.connect(
            hostname=config.host,
            port=config.port,
            namespace="%SYS",
            username=config.username,
            password=config.password,
        )
        try:
            iris_obj = _iris_module.createIRIS(conn)
            status = iris_obj.classMethodValue(
                "Config.Namespaces", "Create", namespace
            )
            if status:
                logger.info(
                    f"Created namespace '{namespace}' via iris.connect() "
                    f"on {config.host}:{config.port}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to create namespace '{namespace}' via iris.connect(): "
                    f"Config.Namespaces.Create returned failure status"
                )
                return False
        finally:
            conn.close()
    except Exception as e:
        err_str = str(e).lower()
        if "access denied" in err_str or "privilege" in err_str or "protect" in err_str:
            logger.warning(
                f"Cannot create namespace '{namespace}': %%SYS access denied "
                f"for user '{config.username}'"
            )
        else:
            logger.warning(f"Cannot create namespace '{namespace}': operation failed ({e})")
        return False


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

    Strategy selection:
    - auto_create resolves to False → skip (return True immediately)
    - container_name is set (non-None, non-empty) → Docker exec strategy
    - container_name is not set → iris.connect() strategy via %SYS
    - NEVER falls back to a hardcoded container name

    Args:
        config: IRIS configuration object.

    Returns:
        True if namespace exists (or was created), or if the check failed
        but the connection should proceed anyway (graceful degradation).
    """
    # Hybrid Smart Default: resolve auto_create
    auto_create = config.auto_create
    if auto_create is None:
        if config.host in ["localhost", "127.0.0.1"]:
            auto_create = True
        else:
            auto_create = False

    if not auto_create:
        return True  # Proceed anyway; connection will fail later if NS missing

    # Strategy selection based on container_name availability
    container_name = config.container_name or None  # Normalize empty string to None

    if container_name:
        # Docker exec strategy — container name is known
        logger.debug(
            f"Checking namespace '{config.namespace}' via Docker exec "
            f"on container '{container_name}'"
        )
        if not check_namespace_exists(container_name, config.namespace):
            logger.info(
                f"Namespace '{config.namespace}' not found. "
                f"Attempting auto-creation via Docker exec..."
            )
            return create_namespace(container_name, config.namespace)
        return True
    else:
        # iris.connect() strategy — no container name available
        logger.debug(
            f"Checking namespace '{config.namespace}' via iris.connect() "
            f"to {config.host}:{config.port}"
        )
        if not check_namespace_via_iris_connect(config, config.namespace):
            logger.info(
                f"Namespace '{config.namespace}' not found or could not be verified. "
                f"Attempting auto-creation via iris.connect()..."
            )
            if not create_namespace_via_iris_connect(config, config.namespace):
                logger.debug(
                    f"Could not create namespace '{config.namespace}' via iris.connect(). "
                    f"Proceeding with connection attempt anyway."
                )
            return True  # Always proceed — namespace may already exist
        return True
