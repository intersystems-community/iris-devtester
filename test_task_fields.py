#!/usr/bin/env python
"""Test which Task Manager fields cause validation errors."""
from iris_devtools.connections import get_connection

conn = get_connection()
cursor = conn.cursor()

# Test fields one at a time
tests = [
    ("Suspended", "INSERT INTO %SYS.Task (Name, TaskClass, Suspended) VALUES ('test', '%SYS.Task.SystemPerformance', 0)"),
    ("DailyFrequency", "INSERT INTO %SYS.Task (Name, TaskClass, DailyFrequency) VALUES ('test', '%SYS.Task.SystemPerformance', 1)"),
    ("DailyIncrement-str", "INSERT INTO %SYS.Task (Name, TaskClass, DailyIncrement) VALUES ('test', '%SYS.Task.SystemPerformance', '30')"),
    ("TimePeriod", "INSERT INTO %SYS.Task (Name, TaskClass, TimePeriod) VALUES ('test', '%SYS.Task.SystemPerformance', 30)"),
    ("All-together", """INSERT INTO %SYS.Task (Name, TaskClass, Description, RunAsUser, Suspended, DailyFrequency, DailyIncrement, TimePeriod, StartDate)
        VALUES ('test', '%SYS.Task.SystemPerformance', 'Test', '_SYSTEM', 0, 1, '30', 30, CURRENT_DATE)"""),
]

for name, sql in tests:
    print(f"\nTesting {name}...")
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"  ✓ {name} works")

        # Clean up
        cursor.execute("DELETE FROM %SYS.Task WHERE Name = 'test'")
        conn.commit()
    except Exception as e:
        print(f"  ❌ {name} failed: {e}")
        conn.rollback()

conn.close()
print("\n✓ Done")
