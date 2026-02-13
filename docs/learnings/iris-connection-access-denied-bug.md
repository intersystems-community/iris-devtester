# Learning: IRIS Connection "Access Denied" / "Invalid Message received"

## Symptoms
When connecting to an InterSystems IRIS container using `iris.connect` (Python Native SDK / DB-API), the connection fails with:
```
<COMMUNICATION LINK ERROR> Failed to connect to server;
Details: <COMMUNICATION ERROR> Invalid Message received;
Details: Access Denied
```
This happens even if the port, username, and password appear correct, and direct connections to `localhost` work.

## Root Cause
The "Invalid Message received" error is a specific response from the IRIS Superserver when it receives data that does not match the expected wire protocol (e.g., hitting the Superserver port with an HTTP request, or hitting the Web port with a Superserver client).

In `iris-devtester`, `IRISContainer.get_config()` was using `get_container_host_ip()` to determine the host. On some platforms or Docker configurations, this can return `0.0.0.0`. While `0.0.0.0` is valid for *listening*, it is often problematic for *connecting* on certain OSs or when IRIS security policies restrict connections to specific interfaces. More importantly, if the discovery logic returned the **Web Port** (52773) instead of the **Superserver Port** (1972) due to misconfiguration or "attached" container inspection errors, the Superserver would reject the "invalid" protocol message.

## Solution
Sanitize the discovered host and ensure the Superserver port is correctly prioritized over other mapped ports.

In `iris_devtester/containers/iris_container.py`:
```python
def get_config(self) -> IRISConfig:
    ...
    discovered_host = self.get_container_host_ip()
    # Sanitize 0.0.0.0 to localhost for client connections
    if discovered_host in ("0.0.0.0", "::"):
        discovered_host = "localhost"
    
    self.host = discovered_host
    self._mapped_port = int(self.get_exposed_port(1972))
    ...
```

## Prevention
1. **Explicit Port Discovery**: Always use the internal port (1972) as the key for `get_exposed_port()` discovery, rather than assuming the first available port.
2. **Host Sanitization**: Always translate `0.0.0.0` or `::` to `localhost` for client-side connection strings.
3. **Validation**: Validate that `container_name` is never `None` during `attach()` calls to ensure Docker SDK inspection succeeds.
