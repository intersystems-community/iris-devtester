"""
Example 10: Docker-Compose Integration - Work with existing IRIS containers.

This example demonstrates working with IRIS containers managed by docker-compose
or external tools. It shows three approaches:
1. Standalone utilities (for scripts and shell operations)
2. IRISContainer.attach() (for programmatic access)
3. CLI commands (for manual operations)

Use Case: Licensed IRIS running via docker-compose that you want to use for testing.

Constitutional Principle #6: Enterprise Ready, Community Friendly
"""

from iris_devtester.utils.enable_callin import enable_callin_service
from iris_devtester.utils.test_connection import test_connection
from iris_devtester.utils.container_status import get_container_status
from iris_devtester.containers import IRISContainer


def example_standalone_utilities():
    """
    Use standalone utilities for quick operations.

    Best for: Shell scripts, automation, quick checks.
    """
    print("=== Standalone Utilities Example ===\n")
    # Expected output: === Standalone Utilities Example ===

    container_name = "iris_db"  # Your docker-compose service name

    # 1. Enable CallIn service (required for DBAPI connections)
    print("1. Enabling CallIn service...")
    success, message = enable_callin_service(container_name)
    if success:
        print(f"   ✓ {message}")
        # Expected output:
        #   ✓ CallIn service enabled on iris_db
    else:
        print(f"   ✗ {message}")
        # If container not running, provides remediation steps

    # 2. Test connection
    print("\n2. Testing connection...")
    success, message = test_connection(container_name, namespace="USER")
    if success:
        print(f"   ✓ {message}")
        # Expected output:
        #   ✓ Connection successful to USER namespace on iris_db
    else:
        print(f"   ✗ {message}")

    # 3. Get comprehensive status
    print("\n3. Getting container status...")
    success, status_report = get_container_status(container_name)
    print(status_report)
    # Expected output:
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Container Status: iris_db
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Running: ✓ Container is running
    # Health: ✓ Health check passed
    # Connection: ✓ Connection to USER namespace successful
    # Overall: ✓ Container is healthy and ready


def example_attach_workflow():
    """
    Attach to existing container for programmatic access.

    Best for: pytest fixtures, integration tests, Python applications.
    """
    print("\n=== IRISContainer.attach() Example ===\n")
    # Expected output: === IRISContainer.attach() Example ===

    container_name = "iris_db"  # Your docker-compose service name

    try:
        # Attach to existing container
        print(f"1. Attaching to existing container: {container_name}")
        iris = IRISContainer.attach(container_name)
        print(f"   ✓ Attached to {container_name}")
        # Expected output:
        #   ✓ Attached to iris_db

        # Use all IRISContainer utility methods
        print("\n2. Getting connection...")
        conn = iris.get_connection()
        print("   ✓ Connection established")
        # Expected output:
        #   ✓ Connection established

        # Run a query
        print("\n3. Running test query...")
        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]
        print(f"   ✓ IRIS Version: {version[:50]}...")
        # Expected output:
        #   ✓ IRIS Version: IRIS for UNIX (Ubuntu Server LTS for ARM64 Contai...

        cursor.execute("SELECT $HOROLOG")
        horolog = cursor.fetchone()[0]
        print(f"   ✓ $HOROLOG: {horolog}")
        # Expected output:
        #   ✓ $HOROLOG: 66583,51234

        cursor.close()

        # Note: Do NOT call start(), stop(), or use context manager
        # These lifecycle methods are only for testcontainers-managed instances
        print("\n✓ Successfully used existing container without lifecycle management")
        # Expected output:
        # ✓ Successfully used existing container without lifecycle management

    except ValueError as e:
        print(f"✗ Could not attach: {e}")
        print("   Make sure the container is running:")
        print("   $ docker-compose up -d")
        # Expected output (if container not found):
        # ✗ Could not attach: Container 'iris_db' not found or not running
        #
        # What went wrong:
        #   The specified container is not running or doesn't exist.
        #
        # How to fix it:
        #   1. Check running containers:
        #      docker ps
        #
        #   2. Check all containers (including stopped):
        #      docker ps -a
        #
        #   3. Start the container if stopped:
        #      docker start iris_db
        #
        #   4. Or start with docker-compose:
        #      docker-compose up -d


def example_cli_commands():
    """
    Show CLI commands for manual operations.

    Best for: DevOps, troubleshooting, quick checks in terminal.
    """
    print("\n=== CLI Commands Example ===\n")
    # Expected output: === CLI Commands Example ===

    print("The iris-devtester CLI provides commands for docker-compose workflows:")
    print()
    print("# Check container status")
    print("$ iris-devtester container status iris_db")
    print()
    print("# Enable CallIn service (required for DBAPI)")
    print("$ iris-devtester container enable-callin iris_db")
    print()
    print("# Test database connection")
    print("$ iris-devtester container test-connection iris_db --namespace USER")
    print()
    print("# Reset password (if needed)")
    print("$ iris-devtester container reset-password iris_db --user _SYSTEM --password SYS")
    print()
    print("# Show all available container commands")
    print("$ iris-devtester container --help")
    print()
    print("✓ These commands work with ANY running IRIS container")
    # Expected output: ✓ These commands work with ANY running IRIS container


def example_docker_compose_yaml():
    """
    Show example docker-compose.yml configuration.

    Best for: Setting up licensed IRIS with docker-compose.
    """
    print("\n=== Docker-Compose YAML Example ===\n")
    # Expected output: === Docker-Compose YAML Example ===

    yaml_content = """version: '3.8'

services:
  iris_db:
    image: intersystemsdc/iris:latest  # Licensed IRIS
    container_name: iris_db
    ports:
      - "1972:1972"   # SuperServer port
      - "52773:52773" # Management Portal
    environment:
      - ISC_CPF_MERGE_FILE=/iris-init/merge.cpf
    volumes:
      - iris-data:/usr/irissys/mgr
      - ./iris-init:/iris-init

volumes:
  iris-data:"""

    print(yaml_content)
    print()
    print("Usage:")
    print("  1. Save above YAML as docker-compose.yml")
    print("  2. Start IRIS: docker-compose up -d")
    print("  3. Enable CallIn: iris-devtester container enable-callin iris_db")
    print("  4. Use in Python:")
    print("       from iris_devtester.containers import IRISContainer")
    print("       iris = IRISContainer.attach('iris_db')")
    print("       conn = iris.get_connection()")
    print()
    print("✓ Works with both Community and Enterprise editions")
    # Expected output: ✓ Works with both Community and Enterprise editions


def example_pytest_fixture():
    """
    Show pytest fixture for docker-compose integration.

    Best for: Integration tests with existing IRIS instance.
    """
    print("\n=== pytest Fixture Example ===\n")
    # Expected output: === pytest Fixture Example ===

    fixture_code = '''"""
Integration tests using existing docker-compose IRIS.

Put this in your tests/conftest.py file.
"""
import pytest
from iris_devtester.containers import IRISContainer

@pytest.fixture(scope="session")
def iris_db():
    """
    Attach to existing IRIS container managed by docker-compose.

    Assumes you've run: docker-compose up -d
    """
    # Attach to docker-compose service
    iris = IRISContainer.attach("iris_db")

    # Return connection for tests
    yield iris.get_connection()

    # No cleanup needed - container lifecycle managed by docker-compose

# Usage in test file
def test_my_feature(iris_db):
    """Test using existing IRIS instance."""
    cursor = iris_db.cursor()
    cursor.execute("SELECT $HOROLOG")
    assert cursor.fetchone()[0] is not None
'''

    print(fixture_code)
    print()
    print("Benefits:")
    print("  ✓ No container startup delay (use existing instance)")
    print("  ✓ Works with licensed IRIS")
    print("  ✓ Lifecycle managed by docker-compose, not testcontainers")
    print("  ✓ Same connection API as testcontainers workflow")
    # Expected output:
    # Benefits:
    #   ✓ No container startup delay (use existing instance)
    #   ✓ Works with licensed IRIS
    #   ✓ Lifecycle managed by docker-compose, not testcontainers
    #   ✓ Same connection API as testcontainers workflow


def main():
    """
    Run all docker-compose integration examples.

    NOTE: Most examples require a running IRIS container.
    Start one with:
        docker run -d --name iris_db -p 1972:1972 intersystemsdc/iris-community

    Or with docker-compose (see example_docker_compose_yaml() output).
    """
    print("Docker-Compose Integration Examples")
    print("=" * 80)
    print()
    print("⚠️  These examples require a running IRIS container named 'iris_db'")
    print()
    print("Quick start:")
    print("  $ docker run -d --name iris_db -p 1972:1972 intersystemsdc/iris-community")
    print()
    print("=" * 80)
    print()

    # Show all approaches
    example_docker_compose_yaml()
    example_standalone_utilities()
    example_attach_workflow()
    example_cli_commands()
    example_pytest_fixture()

    print("\n" + "=" * 80)
    print("✓ All docker-compose integration examples complete")
    print("=" * 80)
    # Expected output:
    # ============================================================
    # ✓ All docker-compose integration examples complete
    # ============================================================
    #
    # ✅ Success: Demonstrates all three approaches to docker-compose integration
    # 🎯 Use Case: Working with licensed IRIS or existing containers
    # 📚 See: specs/006-address-docker-compose/spec.md for detailed requirements


if __name__ == "__main__":
    main()
