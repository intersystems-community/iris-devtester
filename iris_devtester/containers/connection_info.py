"""IRISConnectionInfo — the iris-devtester -> iris-agentic-dev handoff contract.

A single authoritative description of how to reach a running IRIS container, so
that iris-agentic-dev (iad) does not have to reconstruct connection details each
session. iris-devtester emits an ``IRISConnectionInfo``; ``to_toml_snippet()``
renders the fragment a session writes into ``.iris-agentic-dev.toml``, which iad
hot-reloads.

Scope: the two-container IRIS + WebGateway case. Capability fingerprinting
(NoPWS, atelier_rest, compile_path) is iad's responsibility, not ours.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# docker-py image reference substring identifying a WebGateway container.
_WEBGATEWAY_MARKER = "webgateway"

# Apache listens on port 80 inside the WebGateway container; the host-mapped
# value is what a session (and iad) actually connects to.
_WEBGATEWAY_INTERNAL_PORT = "80/tcp"


@dataclass
class IRISConnectionInfo:
    """Authoritative description of a connection to a running IRIS container.

    This is the shared contract with iris-agentic-dev. Field names and semantics
    must stay in lockstep with iad's ``.iris-agentic-dev.toml`` reader.

    Attributes:
        host: Hostname reachable from the session (usually "localhost").
        superserver_port: Host-mapped IRIS SuperServer port (container 1972).
        container: Docker container name of the IRIS instance.
        iris_image: IRIS image reference (docker inspect .Config.Image).
        namespace: Default IRIS namespace.
        username: Connection username.
        password: Connection password.
        webgateway_url: "http://host:port" of a detected WebGateway, or None.
        webgateway_container: Docker name of the WebGateway container, or None.
        docker_only: True when no WebGateway is reachable (defaults to
            ``webgateway_url is None`` unless explicitly set).

    Example:
        >>> info = IRISConnectionInfo(
        ...     host="localhost",
        ...     superserver_port=1972,
        ...     container="opsreview-iris",
        ...     iris_image="intersystemsdc/iris-community:latest",
        ... )
        >>> info.docker_only
        True
        >>> print(info.to_toml_snippet())
        container = "opsreview-iris"
        docker_only = true
        namespace = "USER"
    """

    host: str
    superserver_port: int
    container: str
    iris_image: str
    namespace: str = "USER"
    username: str = "_SYSTEM"
    password: str = "SYS"
    webgateway_url: Optional[str] = None
    webgateway_container: Optional[str] = None
    docker_only: Optional[bool] = None

    def __post_init__(self) -> None:
        # docker_only defaults to "no WebGateway reachable" but an explicit
        # value (True/False) passed by the caller is always respected.
        if self.docker_only is None:
            self.docker_only = self.webgateway_url is None

    def to_toml_snippet(self) -> str:
        """Render a ``.iris-agentic-dev.toml`` fragment for iad to hot-reload.

        Emits ``container``, either ``docker_only = true`` or ``web_port = <n>``,
        and ``namespace``. A session writes the returned string to
        ``.iris-agentic-dev.toml`` and iad picks it up on its next reload.

        Returns:
            A TOML fragment (no trailing newline).
        """
        lines = [f'container = "{self.container}"']
        port = None if self.webgateway_url is None else _port_from_url(self.webgateway_url)
        # Only advertise web access when the flag allows it AND we have a usable
        # port; otherwise fall back to docker_only so iad never sees
        # "docker_only = false" without a web_port to connect to.
        if not self.docker_only and port is not None:
            lines.append(f"web_port = {port}")
            lines.append("docker_only = false")
        else:
            lines.append("docker_only = true")
        lines.append(f'namespace = "{self.namespace}"')
        return "\n".join(lines)


def _port_from_url(url: str) -> Optional[int]:
    """Extract the port from a "http://host:port" URL, or None."""
    try:
        return int(url.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return None


def _image_refs(container: Any) -> Tuple[str, ...]:
    """Best-effort collection of image reference strings for a container.

    docker-py exposes ``container.image.tags`` (list) most of the time; when a
    container runs an untagged/pulled-by-digest image, fall back to the image's
    ``RepoTags`` attr. Any access may raise if the image was removed out from
    under a running container, so guard broadly.
    """
    refs = []
    try:
        tags = container.image.tags or []
        refs.extend(tags)
    except Exception:
        pass
    if not refs:
        try:
            repo_tags = container.image.attrs.get("RepoTags") or []
            refs.extend(repo_tags)
        except Exception:
            pass
    return tuple(refs)


def _is_webgateway(container: Any) -> bool:
    """True if any of the container's image references names a WebGateway."""
    return any(_WEBGATEWAY_MARKER in ref.lower() for ref in _image_refs(container))


def _container_networks(container: Any) -> Set[str]:
    """Set of Docker network names the container is attached to."""
    try:
        networks = container.attrs["NetworkSettings"]["Networks"]
        return set(networks.keys())
    except Exception:
        return set()


def _host_mapped_port(container: Any, internal_port: str) -> Optional[str]:
    """Host-side port bound to ``internal_port`` (e.g. "80/tcp"), or None."""
    try:
        bindings = container.attrs["NetworkSettings"]["Ports"].get(internal_port)
        if not bindings:
            return None
        return bindings[0].get("HostPort")
    except Exception:
        return None


def detect_webgateway(
    client: Any,
    iris_networks: Set[str],
    host: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Find a WebGateway container sharing a network with the IRIS container.

    Detection rules (in order):
      1. Consider every container whose image name matches ``*webgateway*``.
      2. Keep only those sharing at least one Docker network with IRIS.
      3. Return the first match's host-mapped port 80 as ``http://host:port``.

    Any Docker API failure is swallowed and treated as "no WebGateway" — the
    caller falls back to docker_only mode rather than raising.

    Args:
        client: A docker-py client (``docker.from_env()``).
        iris_networks: Network names the IRIS container is attached to.
        host: Hostname to embed in the returned URL.

    Returns:
        ``(webgateway_url, webgateway_container_name)``, or ``(None, None)``.
    """
    try:
        candidates = client.containers.list()
    except Exception as e:
        logger.debug("WebGateway detection skipped (Docker error): %s", e)
        return (None, None)

    for container in candidates:
        if not _is_webgateway(container):
            continue
        if not (_container_networks(container) & iris_networks):
            continue
        port = _host_mapped_port(container, _WEBGATEWAY_INTERNAL_PORT)
        if port is None:
            continue
        return (f"http://{host}:{port}", container.name)

    return (None, None)
