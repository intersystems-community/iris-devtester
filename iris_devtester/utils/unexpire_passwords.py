"""
Password unexpiration utility for InterSystems IRIS.

Handles the common "password expired" issue in containers and benchmarks.
Implements Constitutional Principle #1: "Automatic Remediation Over Manual Intervention"
"""

import logging
import subprocess
from typing import Tuple

logger = logging.getLogger(__name__)


def unexpire_all_passwords(container_name: str = "iris_db", timeout: int = 30) -> Tuple[bool, str]:
    """
    Unexpire all passwords in IRIS container.

    This is commonly needed for:
    - Benchmark containers that need to run without interaction
    - Test containers that get reused
    - CI/CD pipelines
    - Multi-container setups (pgwire, embedded, etc.)

    Args:
        container_name: Name of IRIS Docker container
        timeout: Timeout in seconds for docker commands (default: 30)

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        >>> # For pgwire benchmarks:
        >>> unexpire_all_passwords("iris-4way")
        >>> unexpire_all_passwords("iris-4way-embedded")
        >>>
        >>> # Or use the convenience function:
        >>> from iris_devtester.utils import unexpire_passwords_for_containers
        >>> unexpire_passwords_for_containers(["iris-4way", "iris-4way-embedded"])

    Note:
        This is automatically called by IRISContainer.get_connection() if needed,
        but can be called manually for non-testcontainer setups.
    """
    try:
        # ObjectScript commands to unexpire all user passwords
        # Using heredoc for reliable multi-line execution
        objectscript_commands = """Do ##class(Security.Users).UnExpireUserPasswords("*")
Write "UNEXPIRED"
Halt"""

        # Execute via iris session with heredoc
        cmd = [
            "docker",
            "exec",
            container_name,
            "sh",
            "-c",
            f'iris session iris -U %SYS << "EOF"\n{objectscript_commands}\nEOF',
        ]

        logger.info(f"Unexpiring passwords in container: {container_name}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        if result.returncode == 0 and "UNEXPIRED" in result.stdout:
            logger.info(f"✓ Passwords unexpired in {container_name}")
            return True, f"Passwords unexpired successfully in {container_name}"
        else:
            return (
                False,
                f"Failed to unexpire passwords in {container_name}\n"
                f"stderr: {result.stderr}\n"
                f"stdout: {result.stdout}",
            )

    except subprocess.TimeoutExpired:
        return (
            False,
            f"Timeout unexpiring passwords in {container_name} after {timeout}s\n"
            "\n"
            "How to fix it:\n"
            f"  1. Check container is running:\n"
            f"     docker ps | grep {container_name}\n"
            "\n"
            f"  2. Check container logs:\n"
            f"     docker logs {container_name}\n"
            "\n"
            f"  3. Try with longer timeout:\n"
            f"     unexpire_all_passwords('{container_name}', timeout=60)\n",
        )

    except FileNotFoundError:
        return (
            False,
            "Docker command not found\n"
            "\n"
            "How to fix it:\n"
            "  1. Install Docker:\n"
            "     https://docs.docker.com/get-docker/\n"
            "\n"
            "  2. Verify installation:\n"
            "     docker --version\n",
        )

    except Exception as e:
        return (
            False,
            f"Failed to unexpire passwords in {container_name}: {str(e)}\n"
            "\n"
            "Manual fix:\n"
            f"  docker exec {container_name} bash -c 'echo \"do ##class(Security.Users).UnExpireUserPasswords(\\\"*\\\")\" | iris session iris -U %SYS'\n",
        )


def unexpire_passwords_for_containers(
    container_names: list[str], timeout: int = 30, fail_fast: bool = False
) -> dict[str, Tuple[bool, str]]:
    """
    Unexpire passwords for multiple IRIS containers.

    Perfect for multi-container benchmark setups like pgwire 4-way benchmarks.

    Args:
        container_names: List of container names to process
        timeout: Timeout per container in seconds (default: 30)
        fail_fast: Stop on first failure (default: False, process all)

    Returns:
        Dictionary mapping container_name -> (success, message)

    Example:
        >>> # For pgwire 4-way benchmark:
        >>> results = unexpire_passwords_for_containers([
        ...     "iris-4way",
        ...     "iris-4way-embedded",
        ... ])
        >>>
        >>> for container, (success, msg) in results.items():
        ...     if success:
        ...         print(f"✓ {container}: {msg}")
        ...     else:
        ...         print(f"✗ {container}: {msg}")
    """
    results = {}

    for container_name in container_names:
        success, message = unexpire_all_passwords(container_name, timeout)
        results[container_name] = (success, message)

        if not success and fail_fast:
            logger.error(f"Stopping due to failure on {container_name}")
            break

    # Summary logging
    successes = sum(1 for s, _ in results.values() if s)
    failures = len(results) - successes

    if failures == 0:
        logger.info(f"✓ All {successes} containers: passwords unexpired")
    else:
        logger.warning(
            f"Password unexpiration: {successes} succeeded, {failures} failed"
        )

    return results
