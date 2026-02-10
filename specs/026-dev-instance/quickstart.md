# Quickstart: The Dev Instance

Achieve instant, isolated IRIS connectivity for your Python projects.

## 1. Start the Dev Engine
Run this once to boot your warm-start environment:

```bash
idt dev up
```

## 2. Connect from Python
Just call `get_connection()`. The toolkit automatically detects the dev engine, generates a project-specific namespace, and connects you instantly.

```python
from iris_devtester.connections import get_connection

# First call: Starts engine if missing, creates Namespace, connects.
# Subsequent calls: < 100ms connection time.
conn = get_connection()

cursor = conn.cursor()
cursor.execute("CREATE TABLE MyData (ID INT PRIMARY KEY)")
```

## 3. Persistent Data
Data is stored in a managed Docker volume. You can stop and restart the engine without losing your work:

```bash
idt dev down  # Stops container
idt dev up    # Resumes with data intact
```

## 4. Isolation
Run the same code in a different folder, and `idt` will automatically use a DIFFERENT namespace, keeping your projects clean and isolated.
