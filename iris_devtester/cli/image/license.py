"""License key discovery for ``idt image build``.

The key is mounted read-only when the container is started; it is never copied
into the build context, so it cannot end up in an image layer.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from iris_devtester.cli.image.errors import EXIT_BAD_INPUT, ImageCommandError

ENV_VAR = "IRIS_LICENSE_KEY"

_SOURCE_LABELS = {
    "option": "--license",
    "env": ENV_VAR,
    "cwd": "./iris.key",
}


@dataclass(frozen=True)
class LicenseNotice:
    """Non-fatal notice: no key was found, the build continues without one."""

    message: str


@dataclass(frozen=True)
class LicenseResolution:
    path: Optional[Path]
    source: Optional[str]  # "option" | "env" | "cwd" | None
    notice: Optional[LicenseNotice] = None

    def describe(self) -> str:
        """One line naming the key that will be mounted and where it came from."""
        if self.path is None or self.source is None:
            return "no license key"
        return f"{self.path} (from {_SOURCE_LABELS[self.source]})"


def _explicit(raw: str, origin: str, fix_hint: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_file():
        raise ImageCommandError(
            what=f"The license key given by {origin} does not exist or is not a file: {raw}",
            why="An explicitly requested key that is missing would silently give an unlicensed "
            "container, so idt refuses to continue.",
            fix=fix_hint,
            exit_code=EXIT_BAD_INPUT,
            title="License key not found",
        )
    return path.resolve()


def discover_license_key(
    option: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
) -> LicenseResolution:
    """Resolve the key: ``--license`` > ``IRIS_LICENSE_KEY`` > ``./iris.key``.

    No other location is consulted.
    """
    environ = os.environ if env is None else env
    if option:
        return LicenseResolution(
            _explicit(option, "--license", "Pass the path of an existing iris.key to --license."),
            "option",
        )
    env_value = environ.get(ENV_VAR)
    if env_value:
        return LicenseResolution(
            _explicit(
                env_value,
                f"the {ENV_VAR} environment variable",
                f"Point {ENV_VAR} at an existing iris.key, or unset it.",
            ),
            "env",
        )
    candidate = (cwd if cwd is not None else Path.cwd()) / "iris.key"
    if candidate.is_file():
        return LicenseResolution(candidate.resolve(), "cwd")
    return LicenseResolution(
        None,
        None,
        LicenseNotice(
            "No license key found -- continuing without one.\n"
            "    Enterprise/HealthShare images may fail at startup.\n"
            f"    Supply one with --license /path/to/iris.key, {ENV_VAR}=/path, or ./iris.key"
        ),
    )
