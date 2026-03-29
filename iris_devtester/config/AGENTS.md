# config/ — Configuration Discovery

> Parent: [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Configuration management with multi-source discovery: env vars, YAML files, container probing, and sensible defaults. Pydantic-based models. 9 files, 1480 lines.

## KEY FILES

| File | Role |
|------|------|
| `models.py` | `IRISConfig` — central config dataclass (host, port, namespace, username, password) |
| `discovery.py` | Config discovery logic; priority: env vars > YAML > container probe |
| `auto_discovery.py` | Docker-based auto-detection of running IRIS containers |
| `container_config.py` | Container-specific configuration |
| `container_state.py` | Tracks container runtime state |
| `defaults.py` | Default values (port 1972, namespace USER, etc.) |
| `presets.py` | Named configuration presets (community, enterprise, light) |
| `yaml_loader.py` | YAML config file parser |

## DISCOVERY PRIORITY

1. Environment variables (`IRIS_HOST`, `IRIS_PORT`, etc.)
2. YAML config file (if present)
3. Docker container probe (finds running IRIS containers)
4. Defaults (127.0.0.1:1972, USER, _SYSTEM/SYS)

## PATTERNS

- **Zero-config viable**: `IRISConfig()` with no args uses discovery chain
- **Pydantic validation**: Config values validated at construction time
- **Immutable after creation**: Config objects are not modified after initialization
