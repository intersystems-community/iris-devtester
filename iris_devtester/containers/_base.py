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
import re
from typing import Optional, Tuple
from urllib.parse import quote

from docker.errors import DockerException
from testcontainers.core.container import DockerContainer
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.core.waiting_utils import wait_for_logs

logger = logging.getLogger(__name__)

_LICENSE_REJECTED = "Invalid Community Edition license"

# Identifiers end up in SQL (CREATE DATABASE) or in a user record, so they are
# restricted on purpose. Passwords are not restricted: they travel through the
# exec environment and are never interpolated into any command or script.
NAMESPACE_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.@-]{0,127}")

_PASSWORD_RULE = "password must be non-empty and must not contain a NUL character"

_OK_MARKER = "IDT_OK"
_ERR_MARKER = "IDT_ERR:"


def _script_command(body: str) -> list:
    """Build the fixed argv that pipes a constant ObjectScript script to IRIS.

    ``iris session iris -U ns '<expr>'`` always exits 0 and cannot report a
    failed ``%Status``, so the script goes on stdin instead. It prints an
    ``IDT_OK`` marker on success and the shell exits non-zero without it.
    Values are read inside IRIS from the process environment; nothing is
    interpolated into this text.
    """
    shell = (
        "out=$(iris session iris -U %SYS <<'IDT_EOF'\n"
        + body
        + "Halt\n"
        + "IDT_EOF\n"
        + ")\n"
        + "printf '%s\\n' \"$out\"\n"
        + 'case "$out" in *IDT_OK*) exit 0;; esac\n'
        + "exit 1\n"
    )
    return ["sh", "-c", shell]


_CREATE_DATABASE_COMMAND = _script_command(
    'Set tNs=$system.Util.GetEnviron("IDT_NAMESPACE")\n'
    'Set tRS=##class(%SQL.Statement).%ExecDirect(,"CREATE DATABASE "_tNs)\n'
    'Write $Select(tRS.%SQLCODE<0:"IDT_ERR:"_tRS.%Message,1:"IDT_OK"),!\n'
)

_CREATE_USER_COMMAND = _script_command(
    'Set tSC=##class(Security.Users).Create($system.Util.GetEnviron("IDT_USERNAME"),'
    '"%ALL",$system.Util.GetEnviron("IDT_PASSWORD"))\n'
    'Write $Select($system.Status.IsOK(tSC):"IDT_OK",1:"IDT_ERR:"_$system.Status.GetErrorText(tSC)),!\n'
)


def _invalid_identifier(
    kind: str, value: str, env_var: str, source: str, rule: str, example: str
) -> ValueError:
    return ValueError(
        f"Invalid {kind} {value!r} for IRISDockerContainer{source}\n"
        "\n"
        "What went wrong:\n"
        f"  {rule}\n"
        "\n"
        "How to fix it:\n"
        f"  1. Use a plain name, for example {example}.\n"
        f"  2. If it came from the {env_var} environment variable, correct it there.\n"
    )


def validate_namespace(value: str, source: str = "") -> None:
    """Raise ValueError unless ``value`` is a safe namespace name."""
    if NAMESPACE_PATTERN.fullmatch(value):
        return
    raise _invalid_identifier(
        "namespace",
        value,
        "IRIS_NAMESPACE",
        source,
        "A namespace must start with a letter and contain only letters, digits and\n"
        "  underscores (max 64 characters). The value is used as a SQL identifier in\n"
        "  CREATE DATABASE, so spaces, quotes and punctuation are not allowed.",
        "MY_NS",
    )


def validate_username(value: str, source: str = "") -> None:
    """Raise ValueError unless ``value`` is a safe username."""
    if USERNAME_PATTERN.fullmatch(value):
        return
    raise _invalid_identifier(
        "username",
        value,
        "IRIS_USERNAME",
        source,
        "A username must be 1 to 128 characters, start with a letter, digit or\n"
        "  underscore, and continue with letters, digits, underscore, dot, at sign\n"
        "  or hyphen. Spaces and quotes are not allowed.",
        "svc_user",
    )


def validate_password(value: str, source: str = "") -> None:
    """Raise ValueError if ``value`` is empty or holds a NUL. Never echoes it."""
    if value and "\x00" not in value:
        return
    raise ValueError(
        f"Invalid password for IRISDockerContainer{source}\n"
        "\n"
        "What went wrong:\n"
        f"  {_PASSWORD_RULE}.\n"
        "\n"
        "How to fix it:\n"
        "  1. Supply a non-empty password without NUL characters; every other\n"
        "     character is allowed.\n"
        "  2. If it came from the IRIS_PASSWORD environment variable, correct it there.\n"
    )


def _unpack_exec_result(result) -> Tuple[int, str]:
    exit_code = getattr(result, "exit_code", None)
    output = getattr(result, "output", None)
    if exit_code is None:
        exit_code, output = result
    if isinstance(output, bytes):
        output = output.decode("utf-8", "replace")
    return (1 if exit_code is None else exit_code), (output or "")


def _scrub(text: str, secret: Optional[str]) -> str:
    """Keep the useful tail of command output and drop any trace of the secret."""
    if secret:
        text = text.replace(secret, "***")
    marker = text.rfind(_ERR_MARKER)
    if marker != -1:
        text = text[marker + len(_ERR_MARKER) :]
    return text.strip()[:500]


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
        license_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        if "driver" in kwargs:
            raise TypeError(
                "IRISDockerContainer no longer accepts 'driver'; it had no effect and was removed"
            )
        super().__init__(image=image, **kwargs)
        env_username = os.environ.get("IRIS_USERNAME") or None
        env_password = os.environ.get("IRIS_PASSWORD") or None
        self.username = username or env_username
        # An explicit empty password is an error when a user is requested; only
        # an empty environment variable counts as "unset".
        self.password = password if password is not None else env_password
        self.namespace = namespace or os.environ.get("IRIS_NAMESPACE") or "USER"
        self.port = port
        self.license_key = license_key
        self._license_check_error: Optional[str] = None

        self._validate_credentials(
            namespace_from_env=not namespace and bool(os.environ.get("IRIS_NAMESPACE")),
            username_from_env=not username and bool(env_username),
            password_from_env=password is None and bool(env_password),
        )

        self.with_exposed_ports(self.port)

    def _validate_credentials(
        self, namespace_from_env: bool, username_from_env: bool, password_from_env: bool
    ) -> None:
        """Validate values before any docker call. See contracts/validation-contract.md."""
        if self.namespace.upper() != "USER":
            validate_namespace(
                self.namespace, " (from IRIS_NAMESPACE)" if namespace_from_env else ""
            )
        if self.username and self.password is not None:
            validate_username(self.username, " (from IRIS_USERNAME)" if username_from_env else "")
            validate_password(self.password, " (from IRIS_PASSWORD)" if password_from_env else "")

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
            if self._license_check_error:
                raise TimeoutError(
                    f"{e}\n\n"
                    "Note: the licence check could not read the container logs "
                    f"({self._license_check_error}), so an expired community licence "
                    "cannot be ruled out. Check: docker logs <container>"
                ) from e
            raise
        if self._community_license_rejected():
            raise self._license_error()
        if self.namespace.upper() != "USER":
            self._run_step(
                "create database",
                f"Could not create database '{self.namespace}'",
                _CREATE_DATABASE_COMMAND,
                {"IDT_NAMESPACE": self.namespace},
                "A database or namespace with this name may already exist. Pick another\n"
                "     name, or remove the existing one.",
            )
        if not (self.username and self.password):
            return
        self._run_step(
            "create user",
            f"Could not create user '{self.username}'",
            _CREATE_USER_COMMAND,
            {"IDT_USERNAME": self.username, "IDT_PASSWORD": self.password},
            "The user may already exist. Pick another username, or use the image's\n"
            "     built-in _SYSTEM account by leaving username and password unset.",
        )

    def _run_step(self, step: str, title: str, command: list, environment: dict, fix: str) -> None:
        """Run a fixed command with values in its environment and check the result.

        Neither the environment mapping nor the password is ever logged or
        included in an error message.
        """
        result = self._container.exec_run(command, environment=environment)
        exit_code, output = _unpack_exec_result(result)
        logger.debug("%s: exit code %s", step, exit_code)
        if exit_code == 0:
            return
        detail = _scrub(output, environment.get("IDT_PASSWORD"))
        raise RuntimeError(
            f"{title} (exit code {exit_code})\n"
            "\n"
            "What went wrong:\n"
            f"  IRIS did not confirm the {step} step. Output:\n"
            f"  {detail or '(none)'}\n"
            "\n"
            "How to fix it:\n"
            f"  1. {fix}\n"
            "  2. Check the container logs: docker logs <container>\n"
        )

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
        self._license_check_error = None
        try:
            stdout, stderr = self.get_logs()
        except (DockerException, ContainerStartException) as exc:
            self._license_check_error = str(exc)
            logger.warning("Could not read container logs for the licence check: %s", exc)
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
