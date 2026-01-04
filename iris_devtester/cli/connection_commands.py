"""Connection testing and diagnostics CLI commands."""

import sys
from pathlib import Path
from typing import Optional

import click

from iris_devtester.config.container_config import ContainerConfig
from iris_devtester.utils import progress
from iris_devtester.utils.iris_container_adapter import IRISContainerManager


@click.command(name="test-connection")
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to iris-config.yml configuration file"
)
@click.option(
    "--container",
    type=str,
    help="Container name to test connection against (default: iris_db)"
)
@click.option(
    "--host",
    type=str,
    help="IRIS host (overrides config/container)"
)
@click.option(
    "--port",
    type=int,
    help="IRIS SuperServer port (overrides config/container)"
)
@click.option(
    "--namespace",
    type=str,
    help="IRIS namespace (default: USER)"
)
@click.option(
    "--username",
    type=str,
    help="Username (default: _SYSTEM)"
)
@click.option(
    "--password",
    type=str,
    help="Password (default: SYS)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed connection diagnostics"
)
@click.pass_context
def test_connection(ctx, config, container, host, port, namespace, username, password, verbose):
    """
    Test connection to IRIS database.

    Tests both DBAPI and JDBC connectivity and provides diagnostic information.
    Constitutional Principle #2: Tries DBAPI first (3x faster), then JDBC fallback.

    \b
    Examples:
        # Test connection to default container
        iris-devtester test-connection

        # Test connection to specific container
        iris-devtester test-connection --container my_iris

        # Test connection with explicit parameters
        iris-devtester test-connection --host localhost --port 1972

        # Test with config file
        iris-devtester test-connection --config iris-config.yml

        # Verbose diagnostics
        iris-devtester test-connection -v
    """
    try:
        # Determine connection parameters
        if verbose:
            click.echo("🔍 Determining connection parameters...")

        # Priority: CLI flags > config file > container > defaults
        conn_host: Optional[str] = host
        conn_port: Optional[int] = port
        conn_namespace: str = namespace or "USER"
        conn_username: str = username or "_SYSTEM"
        conn_password: str = password or "SYS"

        # Try to load from config file
        if config:
            if verbose:
                click.echo(f"  → Loading config from: {config}")
            container_config = ContainerConfig.from_yaml(config)
            conn_host = conn_host or "localhost"
            conn_port = conn_port or container_config.superserver_port
            conn_namespace = namespace or container_config.namespace
            conn_password = password or container_config.password
        # Try to detect from container
        elif container or (not host and not port):
            container_name = container or "iris_db"
            if verbose:
                click.echo(f"  → Looking for container: {container_name}")

            docker_container = IRISContainerManager.get_existing(container_name)
            if docker_container:
                docker_container.reload()
                if verbose:
                    click.echo(f"  → Found container: {container_name} (status: {docker_container.status})")

                # Get port mapping
                port_bindings = docker_container.attrs.get("NetworkSettings", {}).get("Ports", {})
                if "1972/tcp" in port_bindings and port_bindings["1972/tcp"]:
                    conn_port = int(port_bindings["1972/tcp"][0]["HostPort"])
                    conn_host = "localhost"
                    if verbose:
                        click.echo(f"  → Detected SuperServer port: {conn_port}")
                else:
                    raise ValueError(
                        f"Container '{container_name}' found but SuperServer port not exposed\n"
                        "\n"
                        "What went wrong:\n"
                        f"  Container '{container_name}' is running but port 1972 is not mapped.\n"
                        "\n"
                        "How to fix it:\n"
                        "  1. Remove and recreate container with port mapping:\n"
                        f"     iris-devtester container remove {container_name}\n"
                        "     iris-devtester container up\n"
                        "  2. Or specify connection parameters explicitly:\n"
                        "     iris-devtester test-connection --host localhost --port 1972\n"
                    )
            else:
                if container:
                    # User specified container but not found
                    raise ValueError(
                        f"Container '{container_name}' not found\n"
                        "\n"
                        "What went wrong:\n"
                        f"  No Docker container named '{container_name}' exists.\n"
                        "\n"
                        "How to fix it:\n"
                        "  1. Create container:\n"
                        "     iris-devtester container up\n"
                        "  2. Or specify connection parameters:\n"
                        "     iris-devtester test-connection --host localhost --port 1972\n"
                    )
                else:
                    # No container specified and default not found - use defaults
                    if verbose:
                        click.echo("  → No container found, using defaults")
                    conn_host = "localhost"
                    conn_port = 1972

        # Default values if still None
        conn_host = conn_host or "localhost"
        conn_port = conn_port or 1972

        # Display connection parameters
        click.echo(f"\n🔌 Testing connection to IRIS:")
        click.echo(f"   Host: {conn_host}")
        click.echo(f"   Port: {conn_port}")
        click.echo(f"   Namespace: {conn_namespace}")
        click.echo(f"   Username: {conn_username}")
        click.echo()

        # Test DBAPI connection
        click.echo("📊 Test 1/2: DBAPI Connection (fast native protocol)")
        dbapi_success = False
        try:
            import intersystems_iris.dbapi._DBAPI as dbapi

            if verbose:
                click.echo(f"  → Connecting to SuperServer {conn_host}:{conn_port}...")

            connection_string = f"{conn_host}:{conn_port}/{conn_namespace}"
            conn = dbapi.connect(
                connection_string,
                conn_username,
                conn_password,
                timeout=5
            )

            if verbose:
                click.echo("  → Executing test query...")

            cursor = conn.cursor()
            cursor.execute("SELECT $ZVERSION")
            version = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            click.echo(f"  ✓ DBAPI connection successful")
            click.echo(f"  ✓ IRIS version: {version}")
            dbapi_success = True

        except ImportError:
            click.echo("  ⚠ DBAPI not available (intersystems-irispython not installed)")
            if verbose:
                click.echo("    Install with: pip install intersystems-irispython")
        except Exception as e:
            click.echo(f"  ✗ DBAPI connection failed: {e}")
            if verbose:
                import traceback
                click.echo(f"\n{traceback.format_exc()}")

        # Test JDBC connection
        click.echo("\n🔌 Test 2/2: JDBC Connection (Java-based fallback)")
        jdbc_success = False
        try:
            import jaydebeapi
            import jpype

            if not jpype.isJVMStarted():
                if verbose:
                    click.echo("  → Starting JVM...")
                jpype.startJVM(jpype.getDefaultJVMPath(), "-Djava.class.path=./intersystems-jdbc-3.8.1.jar")

            if verbose:
                click.echo(f"  → Connecting via JDBC to {conn_host}:{conn_port}...")

            jdbc_url = f"jdbc:IRIS://{conn_host}:{conn_port}/{conn_namespace}"
            conn = jaydebeapi.connect(
                "com.intersystems.jdbc.IRISDriver",
                jdbc_url,
                [conn_username, conn_password],
                "./intersystems-jdbc-3.8.1.jar"
            )

            if verbose:
                click.echo("  → Executing test query...")

            cursor = conn.cursor()
            cursor.execute("SELECT $ZVERSION")
            version = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            click.echo(f"  ✓ JDBC connection successful")
            click.echo(f"  ✓ IRIS version: {version}")
            jdbc_success = True

        except ImportError as e:
            missing_module = "jaydebeapi" if "jaydebeapi" in str(e) else "jpype"
            click.echo(f"  ⚠ JDBC not available ({missing_module} not installed)")
            if verbose:
                click.echo(f"    Install with: pip install iris-devtester[jdbc]")
        except Exception as e:
            click.echo(f"  ✗ JDBC connection failed: {e}")
            if verbose:
                import traceback
                click.echo(f"\n{traceback.format_exc()}")

        # Summary
        click.echo("\n" + "="*60)
        if dbapi_success or jdbc_success:
            click.echo("✓ Connection test PASSED")
            if dbapi_success and jdbc_success:
                click.echo("  → Both DBAPI and JDBC working")
            elif dbapi_success:
                click.echo("  → DBAPI working (recommended)")
                click.echo("  → JDBC not available (install with: pip install iris-devtester[jdbc])")
            else:
                click.echo("  → JDBC working (slower fallback)")
                click.echo("  → DBAPI not available (install with: pip install intersystems-irispython)")
            click.echo("="*60)
            return  # Success - exit with code 0
        else:
            click.echo("✗ Connection test FAILED")
            click.echo("\nWhat went wrong:")
            click.echo("  Could not connect to IRIS using either DBAPI or JDBC.")
            click.echo("\nHow to fix it:")
            click.echo("  1. Verify IRIS is running:")
            click.echo(f"     iris-devtester container status")
            click.echo("  2. Check connection parameters:")
            click.echo(f"     Host: {conn_host}")
            click.echo(f"     Port: {conn_port}")
            click.echo("  3. Install connection libraries:")
            click.echo("     pip install iris-devtester[all]")
            click.echo("  4. Check firewall/network access to port")
            click.echo("\nDocumentation:")
            click.echo("  https://github.com/intersystems-community/iris-devtester#connection-issues")
            click.echo("="*60)
            ctx.exit(1)

    except ValueError as e:
        # Configuration error
        progress.print_error(str(e))
        ctx.exit(2)
    except Exception as e:
        # Unexpected error
        progress.print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback
            click.echo(f"\n{traceback.format_exc()}")
        ctx.exit(1)


__all__ = ["test_connection"]
