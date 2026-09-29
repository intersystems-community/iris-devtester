"""In-house IRIS testcontainer base.

Absorbed from the CaretDev ``testcontainers-iris`` package (~93 lines) so that
iris-devtester no longer depends on it. That package hard-requires
``sqlalchemy-iris``, whose bundled ``iris/__init__.py`` collides with
intersystems-irispython under some resolvers (uv) and replaces ``iris.connect``
with a stub. See docs/learnings/testcontainers-iris-removal.md.

Subclasses ``DockerContainer`` rather than ``DbContainer``: upstream marks
``DbContainer`` deprecated-for-removal and its ``_connect`` imports sqlalchemy.
"""

import logging
import os
from typing import Optional
from urllib.parse import quote

from testcontainers.core.container import DockerContainer
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.core.waiting_utils import wait_for_logs

logger = logging.getLogger(__name__)

_LICENSE_REJECTED = "Invalid Community Edition license"


class IRISDockerContainer(DockerContainer):
    """Minimal InterSystems IRIS container (drop-in for testcontainers.iris.IRISContainer).

    Unlike upstream, no ``test``/``test`` %ALL account is created by default. A
    user is created only when both username and password are supplied, either as
    arguments or via ``IRIS_USERNAME`` / ``IRIS_PASSWORD``. Otherwise the image's
    built-in ``_SYSTEM`` account is used.
    """

    DEFAULT_USERNAME = "_SYSTEM"
    DEFAULT_PASSWORD = "SYS"

    def __init__(
        self,
        image: str = "intersystemsdc/iris-community:latest",
        port: int = 1972,
        username: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
        driver: str = "iris",
        license_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(image=image, **kwargs)
        self.image = image
        self.username = username or os.environ.get("IRIS_USERNAME")
        self.password = password or os.environ.get("IRIS_PASSWORD")
        self.namespace = namespace or os.environ.get("IRIS_NAMESPACE", "USER")
        self.port = port
        self.driver = driver
        self.license_key = license_key

        self.with_exposed_ports(self.port)

    def start(self) -> "IRISDockerContainer":
        self._configure()
        super().start()
        self._connect()
        return self

    def _configure(self) -> None:
        if self.license_key:
            self.with_volume_mapping(self.license_key, "/usr/irissys/mgr/iris.key", "ro")

    def _connect(self) -> None:
        try:
            wait_for_logs(
                self,
                predicate=lambda logs: "Enabling logons" in logs or _LICENSE_REJECTED in logs,
            )
        except TimeoutError as e:
            if self._community_license_rejected():
                raise self._license_error() from e
            raise
        if self._community_license_rejected():
            raise self._license_error()
        if self.namespace.upper() != "USER":
            cmd = (
                "iris session iris -U %%SYS "
                "'##class(%%SQL.Statement).%%ExecDirect(,\"CREATE DATABASE %s\")'"
                % (self.namespace,)
            )
            res = self.exec(cmd)
            logger.debug("create database: %s -> %s", cmd, res)
        if not (self.username and self.password):
            return
        cmd = "iris session iris -U %%SYS '##class(Security.Users).Create(\"%s\",\"%s\",\"%s\")'" % (
            self.username,
            "%ALL",
            self.password,
        )
        res = self.exec(cmd)
        logger.debug("create user %s -> %s", self.username, res)

    def _license_error(self) -> RuntimeError:
        return RuntimeError(
            f"IRIS refused to start: community license rejected in {self.image}\n"
            "\n"
            "What went wrong:\n"
            "  IRIS logged 'Invalid Community Edition license, may have exceeded core\n"
            "  limit'. Despite the wording, this is almost always an expired license\n"
            "  baked into an older community image, not a CPU count problem.\n"
            "\n"
            "How to fix it:\n"
            "  1. Use a current image: IRISContainer.community() (defaults to latest-em)\n"
            "     or containers.intersystems.com/intersystems/iris-community:latest-em\n"
            "  2. Re-pull if the tag is cached locally: docker pull <image>\n"
        )

    def _community_license_rejected(self) -> bool:
        try:
            stdout, stderr = self.get_logs()
        except Exception:
            return False
        logs = (stdout or b"") + (stderr or b"")
        return _LICENSE_REJECTED.encode() in logs

    def get_connection_url(self, host: Optional[str] = None) -> str:
        """SQLAlchemy-style URL: iris://user:pass@host:port/NAMESPACE."""
        if self._container is None:
            raise ContainerStartException("container has not been started")
        host = host or self.get_container_host_ip()
        port = self.get_exposed_port(self.port)
        username, password = self._url_credentials()
        return f"iris://{username}:{quote(password, safe=' +')}@{host}:{port}/{self.namespace}"

    def _url_credentials(self) -> "tuple[str, str]":
        return (
            self.username or self.DEFAULT_USERNAME,
            self.password or self.DEFAULT_PASSWORD,
        )
