"""End-to-end coverage for the port registry auto-port fallback."""

import os
import re
import socket
import uuid
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
        # Pre-initialize the registry with the expanded range
        PortRegistry(registry_path=registry_path, port_range=(1972, 2001))
        
        # Set environment variable so the CLI uses our temporary registry
        os.environ["IRIS_PORT_REGISTRY_PATH"] = str(registry_path)
        os.environ["IRIS_PORT_REGISTRY_RANGE"] = "1972-2000"
        
        container_name = f"e2e-port-test-{uuid.uuid4().hex[:8]}"
        project_path = str(Path.cwd().absolute())
        runner = CliRunner()

        # Find a port to block that is in our range (1972-2000)
        # but currently free
        block_port = 1972
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        found_port = False
        # Use wider range for E2E to avoid exhaustion
        for port in range(1972, 2001):
            try:
                sock.bind(("0.0.0.0", port))
                block_port = port
                found_port = True
                break
            except OSError:
                continue
                
        if not found_port:
            pytest.skip("No free ports in range 1972-2000 to block for test")

        # Note: We do NOT call sock.listen(1) here
        # This is the "bound but not listening" case

        assigned_port = None

        try:
            result = runner.invoke(
                main,
                [
                    "container", 
                    "up", 
                    "--auto-port", 
                    "--port-range", "1972-2000",
                    "--name", container_name
                ],
                catch_exceptions=False,
            )

            assert result.exit_code == 0, f"CLI failed:\n{result.output}"

            # Check for conflict warning
            assert "unavailable" in result.output.lower(), "Conflict warning missing"
            # It might warn about 1972 (default) OR our block_port
            assert "Assigned" in result.output, "Assignment message missing"

            assigned_match = re.search(r"Assigned (\d+) instead", result.output)
            assert assigned_match, "Assigned port not reported"

            assigned_port = int(assigned_match.group(1))
            assert assigned_port != block_port
            assert assigned_port != 1972

            superserver_match = re.search(
                r"SuperServer: localhost:(\d+)", result.output
            )
            assert superserver_match, "Connection info missing superserver port"
            assert assigned_port == int(superserver_match.group(1))

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

            container = IRISContainerManager.get_existing(container_name)
            if container:
                try:
                    container.stop(timeout=5)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass

            try:
                PortRegistry(
                    registry_path=registry_path,
                    port_range=(1972, 2001)
                ).release_port(project_path)
            except KeyError:
                pass
            except Exception:
                pass
            
            # Clean up env vars
            if "IRIS_PORT_REGISTRY_PATH" in os.environ:
                del os.environ["IRIS_PORT_REGISTRY_PATH"]
            if "IRIS_PORT_REGISTRY_RANGE" in os.environ:
                del os.environ["IRIS_PORT_REGISTRY_RANGE"]
