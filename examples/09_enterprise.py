"""
Example 9: Enterprise Edition Features.

This example demonstrates:
- Enterprise edition setup with license key
- Production-ready patterns
- Advanced features (mirrors, sharding, etc.)
- Enterprise-specific configuration

Constitutional Principle #6: Enterprise Ready, Community Friendly

⚠️ Note: This example requires an IRIS Enterprise license key.
   It will skip gracefully if no license is available.
"""

import os
from pathlib import Path
from iris_devtester.containers import IRISContainer


def find_license_key():
    """Find IRIS license key in common locations."""
    # Common license key locations
    locations = [
        Path.home() / ".iris" / "iris.key",
        Path("/tmp/iris.key"),
        Path(os.getenv("IRIS_LICENSE_KEY", "")),
    ]

    for location in locations:
        if location.exists() and location.is_file():
            return str(location)

    return None


def example_enterprise_setup():
    """Demonstrate Enterprise edition setup."""
    print("=== Enterprise Edition Setup ===\n")
    # Expected output: === Enterprise Edition Setup ===

    license_key = find_license_key()

    if not license_key:
        print("⚠️ No IRIS Enterprise license key found")
        print("   Locations checked:")
        print("   - ~/.iris/iris.key")
        print("   - /tmp/iris.key")
        print("   - $IRIS_LICENSE_KEY environment variable")
        print("\n   Skipping enterprise examples (graceful degradation)")
        # Expected output:
        # ⚠️ No IRIS Enterprise license key found
        #    Locations checked:
        #    - ~/.iris/iris.key
        #    - /tmp/iris.key
        #    - $IRIS_LICENSE_KEY environment variable
        #
        #    Skipping enterprise examples (graceful degradation)
        # ✅ Success: Graceful fallback to community edition
        return False

    print(f"✓ Found license key: {license_key}")
    # Expected output: ✓ Found license key: /Users/user/.iris/iris.key

    # Note: This is example code - actual Enterprise container
    # requires access to InterSystems container registry
    print("\n✓ Enterprise edition available")
    print("  Image: containers.intersystems.com/intersystems/iris:latest")
    # Expected output:
    # ✓ Enterprise edition available
    #   Image: containers.intersystems.com/intersystems/iris:latest

    return True


def example_enterprise_features():
    """Demonstrate enterprise-specific features."""
    print("\n=== Enterprise Features Demo ===\n")
    # Expected output: === Enterprise Features Demo ===

    license_key = find_license_key()
    if not license_key:
        print("⚠️ Enterprise license required - skipping")
        # Expected output: ⚠️ Enterprise license required - skipping
        return

    print("Enterprise features available:")
    print("1. Mirroring:")
    print("   - Automatic failover")
    print("   - Real-time data synchronization")
    print("   - Zero data loss (synchronous mirror)")
    # Expected output:
    # Enterprise features available:
    # 1. Mirroring:
    #    - Automatic failover
    #    - Real-time data synchronization
    #    - Zero data loss (synchronous mirror)

    print("\n2. Sharding:")
    print("   - Horizontal scaling")
    print("   - Automatic data distribution")
    print("   - Query routing")
    # Expected output:
    # 2. Sharding:
    #    - Horizontal scaling
    #    - Automatic data distribution
    #    - Query routing

    print("\n3. Advanced Security:")
    print("   - Audit database")
    print("   - Field-level encryption")
    print("   - Role-based access control (RBAC)")
    # Expected output:
    # 3. Advanced Security:
    #    - Audit database
    #    - Field-level encryption
    #    - Role-based access control (RBAC)

    print("\n4. Interoperability:")
    print("   - HL7 message processing")
    print("   - Web services integration")
    print("   - Business process orchestration")
    # Expected output:
    # 4. Interoperability:
    #    - HL7 message processing
    #    - Web services integration
    #    - Business process orchestration

    print("\n✓ Enterprise features overview complete")
    # Expected output: ✓ Enterprise features overview complete


def example_production_patterns():
    """Demonstrate production-ready patterns."""
    print("\n=== Production-Ready Patterns ===\n")
    # Expected output: === Production-Ready Patterns ===

    # Pattern 1: Health checks
    print("1. Health Check Pattern:")
    print("   - Monitor container health")
    print("   - Verify database connectivity")
    print("   - Check license expiration")
    # Expected output:
    # 1. Health Check Pattern:
    #    - Monitor container health
    #    - Verify database connectivity
    #    - Check license expiration

    with IRISContainer.community() as iris:
        # Example health check
        try:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()[0]
            cursor.close()

            if result == 1:
                print("   ✓ Health check passed")
                # Expected output:    ✓ Health check passed
        except Exception as e:
            print(f"   ✗ Health check failed: {e}")
            # Expected output:    ✗ Health check failed: <error>

    # Pattern 2: Connection pooling
    print("\n2. Connection Pool Pattern:")
    print("   - Reuse connections for performance")
    print("   - Set min/max pool size")
    print("   - Monitor connection usage")
    # Expected output:
    # 2. Connection Pool Pattern:
    #    - Reuse connections for performance
    #    - Set min/max pool size
    #    - Monitor connection usage

    # Pattern 3: Error handling
    print("\n3. Error Handling Pattern:")
    print("   - Automatic retry on transient errors")
    print("   - Structured error logging")
    print("   - Graceful degradation")
    # Expected output:
    # 3. Error Handling Pattern:
    #    - Automatic retry on transient errors
    #    - Structured error logging
    #    - Graceful degradation

    # Pattern 4: Monitoring
    print("\n4. Monitoring Pattern:")
    print("   - Track query performance")
    print("   - Monitor container resources")
    print("   - Alert on anomalies")
    # Expected output:
    # 4. Monitoring Pattern:
    #    - Track query performance
    #    - Monitor container resources
    #    - Alert on anomalies

    print("\n✓ Production patterns demonstrated")
    # Expected output: ✓ Production patterns demonstrated
    # ✅ Success: Battle-tested patterns for production use


def example_license_management():
    """Demonstrate license key management."""
    print("\n=== License Key Management ===\n")
    # Expected output: === License Key Management ===

    license_key = find_license_key()

    if license_key:
        print(f"✓ License key location: {license_key}")
        # Expected output: ✓ License key location: /Users/user/.iris/iris.key

        # Check if file is readable
        key_path = Path(license_key)
        if key_path.exists():
            size_kb = key_path.stat().st_size / 1024
            print(f"  File size: {size_kb:.1f} KB")
            # Expected output:   File size: 2.3 KB

            print("  ✓ License key accessible")
            # Expected output:   ✓ License key accessible
    else:
        print("⚠️ No license key found")
        print("\nTo use Enterprise features:")
        print("1. Obtain license key from InterSystems")
        print("2. Save to ~/.iris/iris.key")
        print("3. Set permissions: chmod 600 ~/.iris/iris.key")
        print("4. Set environment: export IRIS_LICENSE_KEY=~/.iris/iris.key")
        # Expected output:
        # ⚠️ No license key found
        #
        # To use Enterprise features:
        # 1. Obtain license key from InterSystems
        # 2. Save to ~/.iris/iris.key
        # 3. Set permissions: chmod 600 ~/.iris/iris.key
        # 4. Set environment: export IRIS_LICENSE_KEY=~/.iris/iris.key

    print("\n✓ License management example complete")
    # Expected output: ✓ License management example complete


def example_graceful_fallback():
    """Demonstrate graceful fallback to Community edition."""
    print("\n=== Graceful Fallback Pattern ===\n")
    # Expected output: === Graceful Fallback Pattern ===

    license_key = find_license_key()

    # Try Enterprise first, fallback to Community
    if license_key:
        print("✓ Attempting Enterprise edition...")
        # Expected output: ✓ Attempting Enterprise edition...
        # Note: Actual Enterprise container launch would go here
        print("  (Enterprise container would start here)")
        # Expected output:   (Enterprise container would start here)
    else:
        print("⚠️ Enterprise not available, using Community edition")
        # Expected output: ⚠️ Enterprise not available, using Community edition

        with IRISContainer.community() as iris:
            print("✓ Community edition container started")
            # Expected output: ✓ Community edition container started

            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT $ZVERSION")
            version = cursor.fetchone()[0]
            print(f"  Version: {version[:50]}...")
            # Expected output:   Version: IRIS for UNIX (Ubuntu Server LTS for ARM64 C...
            cursor.close()

    print("\n✓ Graceful fallback demonstrated")
    # Expected output: ✓ Graceful fallback demonstrated
    # ✅ Success: Same code works with both editions


def main():
    """Run all enterprise examples."""
    has_license = example_enterprise_setup()

    if has_license:
        example_enterprise_features()
        example_license_management()
    else:
        print("\n" + "=" * 50)
        print("Running in Community mode")
        print("=" * 50)
        # Expected output:
        # ==================================================
        # Running in Community mode
        # ==================================================

    example_production_patterns()
    example_graceful_fallback()

    print("\n" + "=" * 50)
    print("✓ All enterprise/production examples complete")
    print("=" * 50)
    # Expected output:
    # ==================================================
    # ✓ All enterprise/production examples complete
    # ==================================================
    # ✅ Success: Enterprise-ready with Community fallback
    # ⚠️ Note: Total runtime ~10-15 seconds (Community only)


if __name__ == "__main__":
    main()
