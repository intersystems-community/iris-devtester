"""End-to-end coverage for the port registry auto-port fallback."""

import re
import socket
import uuid
from pathlib import Path

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
    """Ensure CLI falls back to a different port when 1972 is occupied."""

    container_name = f"e2e-port-test-{uuid.uuid4().hex[:8]}"
    project_path = str(Path.cwd().absolute())
    runner = CliRunner()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 1972))
    sock.listen(1)

    assigned_port = None

    try:
        result = runner.invoke(
            main,
            ["container", "up", "--auto-port", "--name", container_name],
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"CLI failed:\n{result.output}"

        # Check for conflict warning
        assert "unavailable" in result.output.lower(), "Conflict warning missing"
        assert "Assigned" in result.output, "Assignment message missing"

        assigned_match = re.search(r"Assigned (\d+) instead", result.output)
        assert assigned_match, "Assigned port not reported"

        assigned_port = int(assigned_match.group(1))
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
            PortRegistry().release_port(project_path)
        except KeyError:
            pass
        except Exception:
            pass
