"""
Example 8: Auto-Discovery - Connect to existing IRIS instances.

This example demonstrates automatic discovery of IRIS instances:
- Docker container detection
- Native IRIS installation detection
- Multi-port scanning

Constitutional Principle #4: Zero Configuration Viable
"""

from iris_devtools.config.auto_discovery import (
    auto_discover_iris,
    discover_docker_iris,
    discover_native_iris,
    discover_iris_port,
)
from iris_devtools.containers import IRISContainer


def example_auto_discover():
    """Try all discovery methods automatically."""
    print("=== Auto-Discovery Example ===\n")

    config = auto_discover_iris()

    if config:
        print(f"✓ Found IRIS instance:")
        print(f"  Host: {config['host']}")
        print(f"  Port: {config['port']}")
        print(f"  Namespace: {config['namespace']}")
        if "container_name" in config:
            print(f"  Container: {config['container_name']}")
    else:
        print("✗ No IRIS instance found")
        print("  Start one with: docker run -d -p 1972:1972 intersystemsdc/iris-community")


def example_docker_discovery():
    """Discover IRIS running in Docker."""
    print("\n=== Docker Discovery Example ===\n")

    config = discover_docker_iris()

    if config:
        print(f"✓ Found IRIS in Docker:")
        print(f"  Container: {config['container_name']}")
        print(f"  Port: {config['port']}")
    else:
        print("✗ No Docker IRIS containers found")


def example_port_scan():
    """Scan common IRIS ports."""
    print("\n=== Port Scan Example ===\n")

    # Common IRIS ports (in priority order)
    ports = [31972, 1972, 11972, 21972]

    port = discover_iris_port(test_ports=ports)

    if port:
        print(f"✓ Found IRIS on port: {port}")
    else:
        print(f"✗ No IRIS found on ports: {ports}")


def example_connect_to_existing():
    """Connect to existing IRIS instance."""
    print("\n=== Connect to Existing IRIS ===\n")

    # Try to find existing IRIS
    config = IRISContainer.from_existing()

    if config:
        print(f"✓ Can connect to existing IRIS at {config.host}:{config.port}")
        print(f"  Namespace: {config.namespace}")

        # You could now use this config to connect
        # conn = get_connection(config)
    else:
        print("✗ No existing IRIS found")
        print("  Falling back to starting new container...")

        # Fallback: start new container
        with IRISContainer.community() as iris:
            print("✓ Started new IRIS container")
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT $ZVERSION")
            print(f"  Version: {cursor.fetchone()[0]}")
            cursor.close()


def main():
    """Run all discovery examples."""
    example_auto_discover()
    example_docker_discovery()
    example_port_scan()
    example_connect_to_existing()

    print("\n✓ All discovery examples complete")


if __name__ == "__main__":
    main()
