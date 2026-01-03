"""Container lifecycle management CLI commands."""

import json
from pathlib import Path

import click

from iris_devtester.config.container_config import ContainerConfig
from iris_devtester.config.container_state import ContainerState
from iris_devtester.utils import health_checks, progress
from iris_devtester.utils.iris_container_adapter import (
    IRISContainerManager,
    translate_docker_error,
    verify_container_persistence,
)


@click.group(name="container")
@click.pass_context
def container_group(ctx):
    """
    Container lifecycle management commands.

    Manage IRIS containers from the command line with zero-config support.
    Supports both Community and Enterprise editions.
    """
    pass


@container_group.command(name="up")
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to iris-config.yml configuration file"
)
@click.option(
    "--detach/--no-detach",
    default=True,
    help="Run container in background mode (default: detached)"
)
@click.option(
    "--timeout",
    type=int,
    default=60,
    help="Health check timeout in seconds (default: 60)"
)
@click.pass_context
def up(ctx, config, detach, timeout):
    """
    Create and start IRIS container from configuration.

    Similar to docker-compose up. Creates a new container or starts existing one.
    Supports zero-config mode - works without any configuration file.

    Container Lifecycle (Feature 011):
      - Containers persist until explicitly removed with 'container remove'
      - Volume mounts are verified during creation
      - No automatic cleanup when CLI exits

    \b
    Examples:
        # Zero-config (uses Community edition defaults)
        iris-devtester container up

        # With custom configuration including volumes
        iris-devtester container up --config iris-config.yml

        # Example iris-config.yml with volumes:
        # edition: community
        # volumes:
        #   - ./workspace:/external/workspace
        #   - ./config:/opt/config:ro

        # Foreground mode (see logs)
        iris-devtester container up --no-detach
    """
    try:
        # Load configuration
        if config:
            container_config = ContainerConfig.from_yaml(config)
            click.echo(f"⚡ Creating container from config: {config}")
        else:
            # Try default location
            default_config = Path.cwd() / "iris-config.yml"
            if default_config.exists():
                container_config = ContainerConfig.from_yaml(default_config)
                click.echo(f"⚡ Creating container from: {default_config}")
            else:
                container_config = ContainerConfig.default()
                click.echo("⚡ Creating container from zero-config defaults")

        # Check if container already exists
        existing_container = IRISContainerManager.get_existing(container_config.container_name)

        if existing_container:
            # Container exists - check if running
            existing_container.reload()
            if existing_container.status == "running":
                click.echo(f"✓ Container '{container_config.container_name}' is already running")

                # Get port mappings from container
                port_bindings = existing_container.attrs.get("NetworkSettings", {}).get("Ports", {})
                superserver_port = container_config.superserver_port
                webserver_port = container_config.webserver_port

                # Extract mapped ports if available
                if "1972/tcp" in port_bindings and port_bindings["1972/tcp"]:
                    superserver_port = int(port_bindings["1972/tcp"][0]["HostPort"])
                if "52773/tcp" in port_bindings and port_bindings["52773/tcp"]:
                    webserver_port = int(port_bindings["52773/tcp"][0]["HostPort"])

                progress.print_connection_info(
                    container_name=container_config.container_name,
                    superserver_port=superserver_port,
                    webserver_port=webserver_port,
                    namespace=container_config.namespace,
                    password=container_config.password
                )
                return

            # Container exists but not running - start it
            click.echo(f"⚡ Starting existing container '{container_config.container_name}'...")
            existing_container.start()
            click.echo(f"✓ Container '{container_config.container_name}' started")
        else:
            # Create new container using Docker SDK (Feature 011 - T015: CLI mode persistence)
            click.echo(f"  → Edition: {container_config.edition}")
            click.echo(f"  → Image: {container_config.get_image_name()}")
            click.echo(f"  → Ports: {container_config.superserver_port}, {container_config.webserver_port}")
            if container_config.volumes:
                click.echo(f"  → Volumes: {len(container_config.volumes)} mount(s)")

            # Validate volume paths before creation
            volume_errors = container_config.validate_volume_paths()
            if volume_errors:
                error_msg = "Volume path validation failed:\n\n"
                for error in volume_errors:
                    error_msg += f"  {error}\n"
                raise ValueError(error_msg)

            # Create container using Docker SDK (no testcontainers labels, prevents ryuk cleanup)
            click.echo("⏳ Creating container with Docker SDK...")
            try:
                existing_container = IRISContainerManager.create_from_config(
                    container_config,
                    use_testcontainers=False  # CLI mode: manual lifecycle, no ryuk cleanup
                )
                click.echo(f"✓ Container '{container_config.container_name}' created and started")

                # Verify container persistence (Feature 011 - T015)
                click.echo("⏳ Verifying container persistence...")
                check = verify_container_persistence(
                    container_config.container_name,
                    container_config,
                    wait_seconds=2.0
                )

                if not check.success:
                    raise ValueError(check.get_error_message(container_config))

                click.echo(f"✓ Container persistence verified")

            except Exception as e:
                # Translate Docker errors to constitutional format
                translated_error = translate_docker_error(e, container_config)
                raise translated_error from e

        # Wait for healthy with progress callback
        click.echo("⏳ Waiting for container to be healthy...")

        def progress_callback(msg: str):
            click.echo(f"  {msg}")

        state = health_checks.wait_for_healthy(
            existing_container,
            timeout=timeout,
            progress_callback=progress_callback
        )

        # Enable CallIn service (required for DBAPI)
        click.echo("⏳ Enabling CallIn service...")
        try:
            health_checks.enable_callin_service(existing_container)
            click.echo("✓ CallIn service enabled")
        except Exception as e:
            progress.print_warning(f"Could not enable CallIn service: {e}")
            click.echo("  → You may need to enable it manually in Management Portal")

        # Success
        click.echo(f"\n✓ Container '{container_config.container_name}' is running and healthy")

        # Get port mappings from container
        existing_container.reload()
        port_bindings = existing_container.attrs.get("NetworkSettings", {}).get("Ports", {})
        superserver_port = container_config.superserver_port
        webserver_port = container_config.webserver_port

        # Extract mapped ports if available
        if "1972/tcp" in port_bindings and port_bindings["1972/tcp"]:
            superserver_port = int(port_bindings["1972/tcp"][0]["HostPort"])
        if "52773/tcp" in port_bindings and port_bindings["52773/tcp"]:
            webserver_port = int(port_bindings["52773/tcp"][0]["HostPort"])

        # Show connection information
        progress.print_connection_info(
            container_name=container_config.container_name,
            superserver_port=superserver_port,
            webserver_port=webserver_port,
            namespace=container_config.namespace,
            password=container_config.password
        )

        # Exit code 0 (success)
        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except ValueError as e:


        # Configuration error (exit code 2)
        progress.print_error(str(e))
        ctx.exit(2)
    except TimeoutError as e:
        # Health check timeout (exit code 5)
        progress.print_error(str(e))
        ctx.exit(5)
    except Exception as e:
        # Docker error or other failure (exit code 1)
        progress.print_error(f"Failed to create container: {e}")
        ctx.exit(1)


@container_group.command(name="start")
@click.argument("container_name", required=False, default="iris_db")
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to configuration file (used if creating new container)"
)
@click.option(
    "--timeout",
    type=int,
    default=60,
    help="Health check timeout in seconds (default: 60)"
)
@click.pass_context
def start(ctx, container_name, config, timeout):
    """
    Start existing IRIS container or create new one.

    If container exists, starts it. If not found, creates from config.
    Containers persist until explicitly removed with 'container remove'.

    Volume Support (Feature 011):
      - Volume mounts specified in config are applied during creation
      - Host paths are validated before container creation
      - Supports read-only (`:ro`) and read-write (`:rw`) modes

    \b
    Examples:
        # Start default container
        iris-devtester container start

        # Start specific container
        iris-devtester container start my_iris

        # Create with volumes (if not exists)
        iris-devtester container start --config iris-config.yml
    """
    try:
        # Check if container exists
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            # Container doesn't exist - create from config
            click.echo(f"⚡ Container '{container_name}' not found, creating new one...")

            # Load config
            if config:
                container_config = ContainerConfig.from_yaml(config)
            else:
                default_config = Path.cwd() / "iris-config.yml"
                if default_config.exists():
                    container_config = ContainerConfig.from_yaml(default_config)
                else:
                    container_config = ContainerConfig.default()

            # Create and start container using Docker SDK (Feature 011 - T015)
            click.echo("⏳ Configuring and starting container with Docker SDK...")

            # Validate volume paths before creation
            volume_errors = container_config.validate_volume_paths()
            if volume_errors:
                error_msg = "Volume path validation failed:\n\n"
                for error in volume_errors:
                    error_msg += f"  {error}\n"
                raise ValueError(error_msg)

            try:
                container = IRISContainerManager.create_from_config(
                    container_config,
                    use_testcontainers=False  # CLI mode: manual lifecycle, no ryuk cleanup
                )
                click.echo(f"✓ Container '{container_name}' created and started")

                # Verify container persistence (Feature 011 - T015)
                check = verify_container_persistence(
                    container_name,
                    container_config,
                    wait_seconds=2.0
                )

                if not check.success:
                    raise ValueError(check.get_error_message(container_config))

            except Exception as e:
                translated_error = translate_docker_error(e, container_config)
                raise translated_error from e

        # Check current status
        container.reload()
        if container.status == "running":
            click.echo(f"✓ Container '{container_name}' is already running")
            ctx.exit(0)

        # Start container
        click.echo(f"⚡ Starting container '{container_name}'...")
        container.start()
        click.echo(f"✓ Container '{container_name}' started")

        # Wait for healthy
        click.echo("⏳ Waiting for container to be healthy...")
        state = health_checks.wait_for_healthy(container, timeout=timeout)

        click.echo(f"✓ Container '{container_name}' started successfully")
        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        progress.print_error(f"Failed to start container: {e}")
        ctx.exit(1)


@container_group.command(name="stop")
@click.argument("container_name", required=False, default="iris_db")
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Grace period before force kill (default: 30 seconds)"
)
@click.pass_context
def stop(ctx, container_name, timeout):
    """
    Gracefully stop running IRIS container.

    Sends SIGTERM, waits for graceful shutdown, then SIGKILL if timeout.

    \b
    Examples:
        # Stop default container
        iris-devtester container stop

        # Stop with custom timeout
        iris-devtester container stop --timeout 60
    """
    try:
        # Get container
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            progress.print_error(f"Container '{container_name}' not found")
            ctx.exit(2)

        # Check if already stopped
        container.reload()
        if container.status in ["exited", "stopped"]:
            click.echo(f"✓ Container '{container_name}' is already stopped")
            ctx.exit(0)

        # Stop container
        click.echo(f"⚡ Stopping container '{container_name}'...")
        container.stop(timeout=timeout)

        click.echo(f"✓ Container '{container_name}' stopped successfully")
        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        progress.print_error(f"Failed to stop container: {e}")
        ctx.exit(1)


@container_group.command(name="restart")
@click.argument("container_name", required=False, default="iris_db")
@click.option(
    "--timeout",
    type=int,
    default=60,
    help="Health check timeout in seconds (default: 60)"
)
@click.pass_context
def restart(ctx, container_name, timeout):
    """
    Restart IRIS container (stop + start).

    \b
    Examples:
        # Restart default container
        iris-devtester container restart

        # Restart specific container
        iris-devtester container restart my_iris
    """
    try:
        # Get container
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            progress.print_error(f"Container '{container_name}' not found")
            ctx.exit(2)

        # Restart container
        click.echo(f"⚡ Restarting container '{container_name}'...")
        container.restart(timeout=timeout)

        # Wait for healthy
        click.echo("⏳ Waiting for container to be healthy...")
        state = health_checks.wait_for_healthy(container, timeout=timeout)

        click.echo(f"✓ Container '{container_name}' restarted successfully")
        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except TimeoutError as e:
        progress.print_error(str(e))
        ctx.exit(5)
    except Exception as e:
        progress.print_error(f"Failed to restart container: {e}")
        ctx.exit(1)


@container_group.command(name="status")
@click.argument("container_name", required=False, default="iris_db")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text)"
)
@click.pass_context
def status(ctx, container_name, format):
    """
    Display current container state and health.

    \b
    Examples:
        # Text format (human-readable)
        iris-devtester container status

        # JSON format (for automation)
        iris-devtester container status --format json
    """
    try:
        # Get container
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            if format == "json":
                print(json.dumps({"error": f"Container '{container_name}' not found"}))
            else:
                progress.print_error(f"Container '{container_name}' not found")
            ctx.exit(2)

        # Get state
        state = ContainerState.from_container(container)

        # Output
        if format == "json":
            print(json.dumps(state.to_json_output(), indent=2))
        else:
            print(state.to_text_output())

        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        # Let Click handle these - don't catch them
        raise
    except Exception as e:
        if format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            progress.print_error(f"Failed to get container status: {e}")
        ctx.exit(1)


@container_group.command(name="logs")
@click.argument("container_name", required=False, default="iris_db")
@click.option(
    "--follow", "-f",
    is_flag=True,
    help="Stream logs continuously (CTRL+C to exit)"
)
@click.option(
    "--tail",
    type=int,
    default=100,
    help="Number of lines to show (default: 100)"
)
@click.option(
    "--since",
    type=str,
    help="Show logs since timestamp (ISO 8601 format)"
)
@click.pass_context
def logs(ctx, container_name, follow, tail, since):
    """
    Display container logs.

    \b
    Examples:
        # Last 100 lines
        iris-devtester container logs

        # Last 20 lines
        iris-devtester container logs --tail 20

        # Stream continuously
        iris-devtester container logs --follow

        # Since specific time
        iris-devtester container logs --since "2025-01-10T14:30:00"
    """
    try:
        # Get container
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            progress.print_error(f"Container '{container_name}' not found")
            ctx.exit(2)

        # Build log options
        log_kwargs = {
            "tail": tail if not follow else "all",
            "stream": follow,
            "timestamps": True,
        }

        if since:
            log_kwargs["since"] = since

        # Get logs
        if follow:
            # Stream logs
            try:
                for log_line in container.logs(**log_kwargs):
                    print(log_line.decode("utf-8", errors="ignore"), end="")
            except KeyboardInterrupt:
                click.echo("\n⚠ Log streaming stopped")
                ctx.exit(0)
        else:
            # Get logs once
            logs_output = container.logs(**log_kwargs)
            print(logs_output.decode("utf-8", errors="ignore"))

        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        progress.print_error(f"Failed to get container logs: {e}")
        ctx.exit(1)


@container_group.command(name="remove")
@click.argument("container_name", required=False, default="iris_db")
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force remove running container"
)
@click.option(
    "--volumes", "-v",
    is_flag=True,
    help="Remove associated volumes (data loss!)"
)
@click.pass_context
def remove(ctx, container_name, force, volumes):
    """
    Remove stopped container and optionally volumes.

    WARNING: Using --volumes will delete all container data permanently!

    \b
    Examples:
        # Remove stopped container (keeps volumes)
        iris-devtester container remove

        # Force remove running container
        iris-devtester container remove --force

        # Remove container and all data
        iris-devtester container remove --force --volumes
    """
    try:
        # Get container
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            progress.print_error(f"Container '{container_name}' not found")
            ctx.exit(2)

        # Warn about data loss
        if volumes:
            click.echo("⚠ WARNING: This will permanently delete all container data!")
            if not force:
                click.confirm("Are you sure you want to continue?", abort=True)

        # Check if running without --force
        container.reload()
        if container.status == "running" and not force:
            raise ValueError(
                "Container is running. Stop it first or use --force to force removal."
            )

        # Remove container
        click.echo(f"⚡ Removing container '{container_name}'...")
        container.remove(v=volumes, force=force)

        if volumes:
            click.echo(f"✓ Container '{container_name}' and volumes removed")
        else:
            click.echo(f"✓ Container '{container_name}' removed")

        ctx.exit(0)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except ValueError as e:
        # Running without --force (exit code 3)
        progress.print_error(str(e))
        ctx.exit(3)
    except Exception as e:
        progress.print_error(f"Failed to remove container: {e}")
        ctx.exit(1)


@container_group.command(name="reset-password")
@click.argument("container_name")
@click.option(
    "--user",
    default="_SYSTEM",
    help="Username to reset password for (default: _SYSTEM)"
)
@click.option(
    "--password",
    default="SYS",
    help="New password (default: SYS)"
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="IRIS SuperServer port (auto-detected if not specified)"
)
@click.pass_context
def reset_password_cmd(ctx, container_name, user, password, port):
    """
    Reset password for IRIS user in container.

    Uses iris session to reset the password via ObjectScript.
    Port is auto-detected for testcontainers with random port mapping.

    \b
    Examples:
        # Reset _SYSTEM password to SYS
        iris-devtester container reset-password my_iris

        # Reset specific user password
        iris-devtester container reset-password my_iris --user admin --password newpass

        # Specify port explicitly
        iris-devtester container reset-password my_iris --port 51972
    """
    try:
        from iris_devtester.utils.password_reset import reset_password
        from iris_devtester.utils.container_port import get_container_port

        # Auto-detect port if not specified (for random port containers like testcontainers)
        if port is None:
            detected_port = get_container_port(container_name)
            if detected_port:
                port = detected_port
                click.echo(f"🔍 Auto-detected port: {port}")
            else:
                port = 1972  # Default fallback

        click.echo(f"⚡ Resetting password for user '{user}' in container '{container_name}' on port {port}...")

        # Call password reset utility
        success, message = reset_password(
            container_name=container_name,
            username=user,
            new_password=password,
            port=port
        )

        if success:
            click.echo(f"✓ Password reset successful for user '{user}'")
            ctx.exit(0)
        else:
            progress.print_error(f"Failed to reset password: {message}")
            ctx.exit(1)

    except (ImportError, ModuleNotFoundError) as e:
        progress.print_error(f"password_reset utility not available: {e}")
        ctx.exit(1)
    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        # Let Click handle these - don't catch them
        raise
    except Exception as e:
        progress.print_error(f"Failed to reset password: {e}")
        ctx.exit(1)


@container_group.command(name="test-connection")
@click.argument("container_name")
@click.option(
    "--namespace",
    default="USER",
    help="IRIS namespace to test connection to (default: USER)"
)
@click.option(
    "--username",
    default="_SYSTEM",
    help="Username for connection (default: _SYSTEM)"
)
@click.option(
    "--password",
    default="SYS",
    help="Password for connection (default: SYS)"
)
@click.pass_context
def test_connection_cmd(ctx, container_name, namespace, username, password):
    """
    Test database connection to IRIS container.

    Verifies that DBAPI connection works to the specified container and namespace.

    \b
    Examples:
        # Test connection to default namespace (USER)
        iris-devtester container test-connection my_iris

        # Test connection to specific namespace
        iris-devtester container test-connection my_iris --namespace MYAPP

        # Test with custom credentials
        iris-devtester container test-connection my_iris --user admin --password secret
    """
    try:
        from iris_devtester.config import IRISConfig
        from iris_devtester.connections import get_connection

        click.echo(f"⚡ Testing connection to container '{container_name}' namespace '{namespace}'...")

        # Get container to extract connection details
        container = IRISContainerManager.get_existing(container_name)

        if not container:
            progress.print_error(f"Container '{container_name}' not found")
            ctx.exit(2)

        # Get port mappings
        container.reload()
        port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})

        # Extract superserver port
        superserver_port = 1972  # Default
        if "1972/tcp" in port_bindings and port_bindings["1972/tcp"]:
            superserver_port = int(port_bindings["1972/tcp"][0]["HostPort"])

        # Create configuration
        config = IRISConfig(
            host="localhost",
            port=superserver_port,
            namespace=namespace,
            username=username,
            password=password,
            driver="auto"
        )

        # Try to connect
        try:
            conn = get_connection(config)

            # Test the connection with a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT $NAMESPACE as namespace")
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            click.echo(f"✓ Connection successful to namespace '{namespace}'")
            click.echo(f"  Host: {config.host}:{config.port}")
            click.echo(f"  Namespace: {namespace}")
            click.echo(f"  User: {username}")
            ctx.exit(0)

        except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            progress.print_error(f"Connection failed: {e}")
            ctx.exit(1)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        progress.print_error(f"Failed to test connection: {e}")
        ctx.exit(1)


@container_group.command(name="enable-callin")
@click.argument("container_name")
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Timeout in seconds for docker commands (default: 30)"
)
@click.pass_context
def enable_callin(ctx, container_name, timeout):
    """
    Enable CallIn service in IRIS container.

    Required for DBAPI connections to work properly.

    \b
    Examples:
        # Enable CallIn service
        iris-devtester container enable-callin my_iris

        # With longer timeout
        iris-devtester container enable-callin my_iris --timeout 60
    """
    try:
        from iris_devtester.utils.enable_callin import enable_callin_service

        click.echo(f"⚡ Enabling CallIn service in container '{container_name}'...")

        # Call enable callin utility
        success, message = enable_callin_service(
            container_name=container_name,
            timeout=timeout
        )

        if success:
            click.echo(f"✓ CallIn service enabled in container '{container_name}'")
            click.echo(f"  {message}")
            ctx.exit(0)
        else:
            progress.print_error(f"Failed to enable CallIn service:\n{message}")
            ctx.exit(1)

    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        raise
    except (ImportError, ModuleNotFoundError) as e:
        progress.print_error(f"enable_callin utility not available: {e}")
        ctx.exit(1)
    except (click.exceptions.Exit, SystemExit, KeyboardInterrupt):
        # Let Click handle these - don't catch them
        raise
    except Exception as e:
        progress.print_error(f"Failed to enable CallIn: {e}")
        ctx.exit(1)
