#!/usr/bin/env python
"""Test Task Manager INSERT to find minimal working fields."""
from iris_devtools.connections import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()

    # Test 1: Minimal insert
    print("\n=== Test 1: Minimal INSERT ===")
    try:
        cursor.execute("""
            INSERT INTO %SYS.Task (Name, TaskClass)
            VALUES ('test-minimal', '%SYS.Task.SystemPerformance')
        """)
        conn.commit()
        print("✓ Minimal insert succeeded")

        # Clean up
        cursor.execute("DELETE FROM %SYS.Task WHERE Name = 'test-minimal'")
        conn.commit()
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 2: With Description
    print("\n=== Test 2: With Description ===")
    try:
        cursor.execute("""
            INSERT INTO %SYS.Task (Name, TaskClass, Description)
            VALUES ('test-desc', '%SYS.Task.SystemPerformance', 'Test task')
        """)
        conn.commit()
        print("✓ With description succeeded")

        # Clean up
        cursor.execute("DELETE FROM %SYS.Task WHERE Name = 'test-desc'")
        conn.commit()
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 3: With RunAsUser
    print("\n=== Test 3: With RunAsUser ===")
    try:
        cursor.execute("""
            INSERT INTO %SYS.Task (Name, TaskClass, Description, RunAsUser)
            VALUES ('test-user', '%SYS.Task.SystemPerformance', 'Test task', '_SYSTEM')
        """)
        conn.commit()
        print("✓ With RunAsUser succeeded")

        # Clean up
        cursor.execute("DELETE FROM %SYS.Task WHERE Name = 'test-user'")
        conn.commit()
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 4: With dates/times
    print("\n=== Test 4: With StartDate ===")
    try:
        cursor.execute("""
            INSERT INTO %SYS.Task (Name, TaskClass, Description, RunAsUser, StartDate)
            VALUES ('test-date', '%SYS.Task.SystemPerformance', 'Test task', '_SYSTEM', CURRENT_DATE)
        """)
        conn.commit()
        print("✓ With StartDate succeeded")

        # Check what was created
        cursor.execute("SELECT ID, Name, StartDate FROM %SYS.Task WHERE Name = 'test-date'")
        result = cursor.fetchone()
        print(f"  Created: ID={result[0]}, Name={result[1]}, StartDate={result[2]}")

        # Clean up
        cursor.execute("DELETE FROM %SYS.Task WHERE Name = 'test-date'")
        conn.commit()
    except Exception as e:
        print(f"❌ Failed: {e}")

    conn.close()
    print("\n✓ Tests complete")

except Exception as e:
    print(f"\n❌ Connection error: {e}")
    import traceback
    traceback.print_exc()
