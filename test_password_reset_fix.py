#!/usr/bin/env python3
"""
Test the password reset fix for DBAPI authentication.

This script tests that the updated password reset utility correctly:
1. Changes the password
2. Disables the "ChangePassword on next login" flag
3. Works with both iris.connect() and DBAPI

Usage:
    python test_password_reset_fix.py --container iris_benchmark_clickbench
"""

import argparse
import sys
from pathlib import Path

# Add iris-devtools to path
sys.path.insert(0, str(Path(__file__).parent))

from iris_devtools.utils.password_reset import reset_password


def test_password_reset(container_name: str):
    """Test the password reset fix."""
    print("=" * 60)
    print("Testing Password Reset Fix")
    print("=" * 60)
    print()

    # Test 1: Reset password
    print("[Test 1] Resetting password with ChangePassword flag disabled...")
    success, message = reset_password(
        container_name=container_name,
        username="_SYSTEM",
        new_password="SYS"
    )

    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        return False

    print()

    # Test 2: Try DBAPI connection
    print("[Test 2] Testing DBAPI connection...")
    try:
        import intersystems_iris.dbapi._DBAPI as dbapi

        conn = dbapi.connect("localhost:31972/USER", "_SYSTEM", "SYS")
        print("✓ DBAPI connection successful!")
        conn.close()

    except ImportError:
        print("⚠️  DBAPI module not available, skipping DBAPI test")

    except Exception as e:
        print(f"✗ DBAPI connection failed: {e}")
        print()
        print("This means the ChangePassword flag is still set.")
        print("The fix did not work as expected.")
        return False

    print()

    # Test 3: Try iris.connect()
    print("[Test 3] Testing iris.connect()...")
    try:
        import iris

        conn = iris.connect(
            hostname="localhost",
            port=31972,
            namespace="USER",
            username="_SYSTEM",
            password="SYS"
        )
        print("✓ iris.connect() successful!")
        conn.close()

    except ImportError:
        print("⚠️  iris module not available, skipping iris.connect() test")

    except Exception as e:
        print(f"✗ iris.connect() failed: {e}")
        return False

    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test password reset fix for DBAPI authentication"
    )
    parser.add_argument(
        "--container",
        default="iris_db",
        help="IRIS container name (default: iris_db)"
    )

    args = parser.parse_args()

    success = test_password_reset(args.container)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
