"""Shared error contract for ``idt image`` commands.

Every failure is raised as an :class:`ImageCommandError` at the place it is
detected and rendered once, by ``common.run_image_command``.
"""

from typing import Iterable, Optional

EXIT_FAILURE = 1
EXIT_BAD_INPUT = 2
EXIT_TIMEOUT = 5

_VALID_EXIT_CODES = (EXIT_FAILURE, EXIT_BAD_INPUT, EXIT_TIMEOUT)
_MASK = "********"


class ImageCommandError(Exception):
    """A user-facing failure with a what / why / fix explanation."""

    def __init__(
        self,
        what: str,
        why: str,
        fix: str,
        exit_code: int = EXIT_FAILURE,
        title: str = "Image command failed",
    ) -> None:
        if exit_code not in _VALID_EXIT_CODES:
            raise ValueError(f"exit_code must be one of {_VALID_EXIT_CODES}, got {exit_code}")
        if not fix or not fix.strip():
            raise ValueError("ImageCommandError requires a concrete fix")
        super().__init__(what)
        self.what = what
        self.why = why
        self.fix = fix
        self.exit_code = exit_code
        self.title = title


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" if line else "" for line in text.splitlines())


def render_error(err: ImageCommandError, secrets: Iterable[Optional[str]] = ()) -> str:
    """Render ``err`` in the three-part format, masking any ``secrets``."""
    text = (
        f"{err.title}\n\n"
        f"What went wrong:\n{_indent(err.what)}\n\n"
        f"Why it matters:\n{_indent(err.why)}\n\n"
        f"How to fix it:\n{_indent(err.fix)}"
    )
    for secret in secrets:
        if secret:
            text = text.replace(secret, _MASK)
    return text


def build_timeout_error(limit: float, elapsed: float, last_line: str) -> ImageCommandError:
    """Exit-5 error for an expired ``--build-timeout``."""
    tail = f"\nLast build output: {last_line}" if last_line else ""
    return ImageCommandError(
        what=f"The build phase timed out: limit {limit:g}s, elapsed {elapsed:.0f}s.{tail}",
        why="The build was stopped (process group killed), so no image was produced.",
        fix=(
            f"Retry with a larger limit, e.g. --build-timeout {int(limit) * 2}. "
            "Use --keep-build-dir to keep the build context for inspection."
        ),
        exit_code=EXIT_TIMEOUT,
        title="Build timed out",
    )


def load_timeout_error(limit: float, elapsed: float) -> ImageCommandError:
    """Exit-5 error for an expired ``--load-timeout``."""
    return ImageCommandError(
        what=f"The load phase timed out: limit {limit:g}s, elapsed {elapsed:.0f}s.",
        why="The Docker daemon may still finish importing the image after the client stopped.",
        fix=(
            "Run 'docker images' to see whether the image arrived before retrying. "
            f"To allow more time use --load-timeout {int(limit) * 2}."
        ),
        exit_code=EXIT_TIMEOUT,
        title="Image load timed out",
    )


def health_timeout_error(name: str, limit: float, elapsed: float, detail: str) -> ImageCommandError:
    """Exit-5 error for an expired IRIS health wait; the container is left running."""
    return ImageCommandError(
        what=(
            f"IRIS in container '{name}' was not healthy within {limit:g}s "
            f"(elapsed {elapsed:.0f}s): {detail}"
        ),
        why="The container is still running so you can inspect it; it was not removed.",
        fix=(
            f"Inspect it with: docker logs {name}\n"
            f"Remove it with:  docker rm -f {name}\n"
            f"Or wait longer with --timeout {int(limit) * 2}."
        ),
        exit_code=EXIT_TIMEOUT,
        title="IRIS health wait timed out",
    )
