"""
Example 5: CI/CD Integration - GitHub Actions and automated testing.

This example demonstrates:
- GitHub Actions workflow setup
- CI/CD testing patterns
- Container caching strategies
- Parallel test execution

Constitutional Principle #4: Zero Configuration Viable
Constitutional Principle #7: Medical-Grade Reliability
"""

import os
from iris_devtester.containers import IRISContainer


def example_basic_ci_test():
    """Demonstrate basic CI test pattern."""
    print("=== Basic CI Test Pattern ===\n")
    # Expected output: === Basic CI Test Pattern ===

    # Detect CI environment
    is_ci = os.getenv("CI", "false").lower() == "true"
    print(f"Running in CI: {is_ci}")
    # Expected output:
    # Running in CI: False (locally)
    # Running in CI: True (in GitHub Actions)

    with IRISContainer.community() as iris:
        print("✓ IRIS container started")
        # Expected output: ✓ IRIS container started
        # ⚠️ Note: First run in CI downloads image (~30-60s)

        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]
        print(f"✓ IRIS Version: {version[:50]}...")
        # Expected output: ✓ IRIS Version: IRIS for UNIX (Ubuntu Server LTS for ARM64 C...
        cursor.close()

    print("✓ Container cleaned up")
    # Expected output: ✓ Container cleaned up
    # ✅ Success: Same code works locally and in CI


def example_github_actions_workflow():
    """Display example GitHub Actions workflow."""
    print("\n=== GitHub Actions Workflow Example ===\n")
    # Expected output: === GitHub Actions Workflow Example ===

    workflow = """
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install iris-devtester[all]
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest tests/ -v --cov=iris_devtester

      # IRIS container starts automatically!
      # No manual Docker setup needed
    """

    print(workflow)
    # Expected output: [Full workflow YAML displayed]
    print("✓ Zero-config CI setup - just install and run!")
    # Expected output: ✓ Zero-config CI setup - just install and run!
    # ✅ Success: No Docker-in-Docker or service containers needed


def example_ci_optimizations():
    """Demonstrate CI optimization techniques."""
    print("\n=== CI Optimization Patterns ===\n")
    # Expected output: === CI Optimization Patterns ===

    print("1. Image Caching:")
    print("   - GitHub Actions caches Docker images automatically")
    print("   - First run: ~60s (pull image)")
    print("   - Subsequent runs: ~5s (cached)")
    # Expected output:
    # 1. Image Caching:
    #    - GitHub Actions caches Docker images automatically
    #    - First run: ~60s (pull image)
    #    - Subsequent runs: ~5s (cached)

    print("\n2. Parallel Testing:")
    print("   - Use pytest-xdist for parallel execution")
    print("   - Each test class gets isolated container")
    print("   - Command: pytest -n auto")
    # Expected output:
    # 2. Parallel Testing:
    #    - Use pytest-xdist for parallel execution
    #    - Each test class gets isolated container
    #    - Command: pytest -n auto

    print("\n3. Resource Limits:")
    print("   - GitHub Actions: 2 CPU cores, 7 GB RAM")
    print("   - IRIS container needs: ~2 GB RAM minimum")
    print("   - Recommendation: Run 1-2 containers concurrently")
    # Expected output:
    # 3. Resource Limits:
    #    - GitHub Actions: 2 CPU cores, 7 GB RAM
    #    - IRIS container needs: ~2 GB RAM minimum
    #    - Recommendation: Run 1-2 containers concurrently

    print("\n✓ CI optimization tips displayed")
    # Expected output: ✓ CI optimization tips displayed


def example_ci_debugging():
    """Demonstrate CI debugging techniques."""
    print("\n=== CI Debugging Patterns ===\n")
    # Expected output: === CI Debugging Patterns ===

    with IRISContainer.community() as iris:
        # Enable verbose logging
        config = iris.get_config()
        print("Container info:")
        print(f"  Host: {config.host}")
        print(f"  Port: {config.port}")
        print(f"  Image: intersystemsdc/iris-community:latest")
        # Expected output:
        # Container info:
        #   Host: localhost
        #   Port: 49153 (random port)
        #   Image: intersystemsdc/iris-community:latest

        # Check container logs (useful for CI debugging)
        container_id = iris.get_container_name()
        print(f"  Container ID: {container_id[:12]}...")
        # Expected output:   Container ID: a1b2c3d4e5f6...
        # ⚠️ Note: Use `docker logs <id>` in CI for debugging

        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT $ZVERSION, $NAMESPACE, $USERNAME")
        result = cursor.fetchone()
        print(f"\n✓ Connected successfully:")
        print(f"  Version: {result[0][:40]}...")
        print(f"  Namespace: {result[1]}")
        print(f"  Username: {result[2]}")
        # Expected output:
        # ✓ Connected successfully:
        #   Version: IRIS for UNIX (Ubuntu Server LTS...
        #   Namespace: USER
        #   Username: _SYSTEM
        cursor.close()


def example_multi_environment_test():
    """Demonstrate testing across multiple environments."""
    print("\n=== Multi-Environment Testing ===\n")
    # Expected output: === Multi-Environment Testing ===

    # Example: Test with different IRIS editions
    environments = [
        {"name": "Community", "image": "intersystemsdc/iris-community:latest"},
        # Enterprise requires license key:
        # {"name": "Enterprise", "image": "containers.intersystems.com/intersystems/iris:latest"}
    ]

    for env in environments:
        print(f"\nTesting with {env['name']} Edition:")
        # Expected output: Testing with Community Edition:

        try:
            with IRISContainer(image=env['image']) as iris:
                conn = iris.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()[0]
                print(f"✓ {env['name']}: Test passed (result={result})")
                # Expected output: ✓ Community: Test passed (result=1)
                cursor.close()
        except Exception as e:
            print(f"⚠️ {env['name']}: Skipped ({str(e)[:30]}...)")
            # Expected output: ⚠️ Enterprise: Skipped (license required...)

    print("\n✓ Multi-environment testing complete")
    # Expected output: ✓ Multi-environment testing complete
    # ✅ Success: Same test code works across editions


def main():
    """Run all CI/CD examples."""
    example_basic_ci_test()
    example_github_actions_workflow()
    example_ci_optimizations()
    example_ci_debugging()
    example_multi_environment_test()

    print("\n" + "=" * 50)
    print("✓ All CI/CD examples complete")
    print("=" * 50)
    # Expected output:
    # ==================================================
    # ✓ All CI/CD examples complete
    # ==================================================
    # ✅ Success: Ready for production CI/CD pipelines
    # ⚠️ Note: Total runtime ~30-45 seconds


if __name__ == "__main__":
    main()
