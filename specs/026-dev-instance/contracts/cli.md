# CLI Contract: idt dev

## Command Structure

### 1. `idt dev up`
Starts the background dev engine.

**Arguments**:
- `--image`: (Optional) IRIS Docker image to use.
- `--force`: (Optional) Restart even if already running.

**Exit Codes**:
- 0: Started successfully (or already running).
- 1: Docker not available or port conflict could not be resolved.

---

### 2. `idt dev down`
Stops and removes the dev engine container.

**Arguments**:
- `--volumes`: (Optional) Also remove the `idt-dev-data` volume.

---

### 3. `idt dev status`
Shows the status of the engine and the current project's isolation layer.

**Output (JSON/Text)**:
- Engine Status: Running/Stopped
- Port: 1972
- Project Namespace: P8F3A2B1C9D
- Volume Status: Connected/Missing

---

### 4. `idt dev logs`
Tails the logs of the `idt-dev-instance`.
