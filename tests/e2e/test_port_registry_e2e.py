"""End-to-end coverage for the port registry auto-port fallback."""

import os
import re
import socket
import uuid
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from click.testing import CliRunner

from iris_devtester.cli import main
from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection
from iris_devtester.ports.registry import PortRegistry
from iris_devtester.utils.iris_container_adapter import IRISContainerManager


@pytest.mark.e2e
@pytest.mark.integration
def test_port_registry_auto_port_fallback():
    """Ensure CLI falls back to a different port when preferred port is occupied."""
    with TemporaryDirectory() as tmp_dir:
        registry_path = Path(tmp_dir) / "port-registry.json"
        
        # Use a UNIQUE project path for this test
        project_path = f"/tmp/idt-e2e-project-{uuid.uuid4().hex[:8]}"
        
        # Set environment variable so the CLI uses our temporary registry
        os.environ["IRIS_PORT_REGISTRY_PATH"] = str(registry_path)
        
        container_name = f"e2e-port-test-{uuid.uuid4().hex[:8]}"
        runner = CliRunner()

        # 1. Find a truly free port to block (using bind check)
        block_port = 1972
        found = False
        for p in range(1972, 1985): # Stay low to leave room in range
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("0.0.0.0", p))
                block_port = p
                found = True
                break
            except OSError:
                continue
        
        if not found:
            pytest.skip("No free ports in range 1972-1985 to block for test")

        time.sleep(0.1) # Cooldown

        # 2. Block that port with a real socket (BOUND but NOT LISTENING)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", block_port))
        
        assigned_port = None

        try:
            # 3. Run idt container up --auto-port
            result = runner.invoke(
                main,
                [
                    "container", 
                    "up", 
                    "--auto-port", 
                    "--name", container_name
                ],
                catch_exceptions=False,
            )

            assert result.exit_code == 0, f"CLI failed:\n{result.output}"

            # 4. Verify conflict was detected
            assert "unavailable" in result.output.lower(), "Conflict warning missing"
            assert "Assigned" in result.output, "Assignment message missing"

            assigned_match = re.search(r"Assigned (\d+) instead", result.output)
            assert assigned_match, "Assigned port not reported"

            assigned_port = int(assigned_match.group(1))
            assert assigned_port != block_port
            
            # 5. Verify connectivity
            config = IRISConfig(
                host="localhost",
                port=assigned_port,
                namespace="USER",
                username="_SYSTEM",
                password="SYS",
                container_name=container_name,
            )

            conn = get_connection(config=config)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT $NAMESPACE AS namespace")
                assert cursor.fetchone() is not None
            finally:
                cursor.close()
                conn.close()

        finally:
            sock.close()
            if "IRIS_PORT_REGISTRY_PATH" in os.environ:
                del os.environ["IRIS_PORT_REGISTRY_PATH"]
                
            container = IRISContainerManager.get_existing(container_name)
            if container:
                try:
                    container.stop(timeout=5)
                    container.remove(force=True)
                except Exception:
                    pass

            try:
                # Clean up the specific assignment we made
                PortRegistry(registry_path=registry_path).release_port(project_path)
            except Exception:
                pass
