"""Progress indicator utilities for CLI output."""

import sys
from typing import Optional


class ProgressIndicator:
    """
    Simple progress indicator for CLI operations.

    Provides spinner, status messages, and completion indicators.

    Example:
        >>> with ProgressIndicator("Starting container") as progress:
        ...     # Do work
        ...     progress.update("Waiting for health check...")
        ...     # More work
        ...     progress.complete("Container started successfully")
    """

    def __init__(self, initial_message: str = ""):
        """
        Initialize progress indicator.

        Args:
            initial_message: Initial status message
        """
        self.current_message = initial_message
        self.is_complete = False

    def __enter__(self):
        """Context manager entry."""
        if self.current_message:
            self.update(self.current_message)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not self.is_complete and exc_type is None:
            self.complete()
        return False

    def update(self, message: str) -> None:
        """
        Update progress message.

        Args:
            message: New status message

        Example:
            >>> progress = ProgressIndicator()
            >>> progress.update("Downloading image...")
        """
        self.current_message = message
        # Write to stderr to not interfere with stdout
        sys.stderr.write(f"\r\033[K{message}")
        sys.stderr.flush()

    def complete(self, message: Optional[str] = None) -> None:
        """
        Mark progress as complete.

        Args:
            message: Optional completion message

        Example:
            >>> progress = ProgressIndicator("Starting")
            >>> progress.complete("✓ Started successfully")
        """
        self.is_complete = True
        if message:
            sys.stderr.write(f"\r\033[K{message}\n")
        else:
            sys.stderr.write("\n")
        sys.stderr.flush()

    def fail(self, message: str) -> None:
        """
        Mark progress as failed.

        Args:
            message: Failure message

        Example:
            >>> progress = ProgressIndicator("Starting")
            >>> progress.fail("✗ Failed to start")
        """
        self.is_complete = True
        sys.stderr.write(f"\r\033[K{message}\n")
        sys.stderr.flush()


def print_success(message: str) -> None:
    """
    Print success message with checkmark.

    Args:
        message: Success message

    Example:
        >>> print_success("Container started")
        ✓ Container started
    """
    print(f"✓ {message}")


def print_error(message: str) -> None:
    """
    Print error message with X mark.

    Args:
        message: Error message

    Example:
        >>> print_error("Failed to start container")
        ✗ Failed to start container
    """
    print(f"✗ {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """
    Print warning message with warning symbol.

    Args:
        message: Warning message

    Example:
        >>> print_warning("No health check defined")
        ⚠ No health check defined
    """
    print(f"⚠ {message}", file=sys.stderr)


def print_info(message: str) -> None:
    """
    Print informational message.

    Args:
        message: Info message

    Example:
        >>> print_info("Using default configuration")
        ℹ Using default configuration
    """
    print(f"ℹ {message}")


def print_step(step_num: int, total_steps: int, message: str) -> None:
    """
    Print step progress.

    Args:
        step_num: Current step number
        total_steps: Total number of steps
        message: Step description

    Example:
        >>> print_step(1, 3, "Pulling image")
        [1/3] Pulling image
    """
    print(f"[{step_num}/{total_steps}] {message}")


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(125)
        '2m 5s'
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_bytes(bytes_count: int) -> str:
    """
    Format byte count to human-readable string.

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted byte string

    Example:
        >>> format_bytes(1024)
        '1.0 KB'
        >>> format_bytes(1048576)
        '1.0 MB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


class Spinner:
    """
    Animated spinner for long-running operations.

    Example:
        >>> import time
        >>> spinner = Spinner("Loading")
        >>> spinner.start()
        >>> time.sleep(2)
        >>> spinner.stop("Done")
    """

    def __init__(self, message: str = ""):
        """
        Initialize spinner.

        Args:
            message: Status message to display
        """
        self.message = message
        self.is_spinning = False
        self._frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame_index = 0

    def start(self) -> None:
        """Start the spinner animation."""
        self.is_spinning = True
        self._show_frame()

    def stop(self, final_message: Optional[str] = None) -> None:
        """
        Stop the spinner.

        Args:
            final_message: Optional final message to display
        """
        self.is_spinning = False
        if final_message:
            sys.stderr.write(f"\r\033[K{final_message}\n")
        else:
            sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    def _show_frame(self) -> None:
        """Show current spinner frame."""
        if not self.is_spinning:
            return

        frame = self._frames[self._frame_index]
        sys.stderr.write(f"\r\033[K{frame} {self.message}")
        sys.stderr.flush()

        self._frame_index = (self._frame_index + 1) % len(self._frames)

    def update(self, message: str) -> None:
        """
        Update spinner message.

        Args:
            message: New message to display
        """
        self.message = message
        self._show_frame()


def print_connection_info(
    container_name: str,
    superserver_port: int,
    webserver_port: int,
    namespace: str,
    username: str = "_SYSTEM",
    password: str = "SYS"
) -> None:
    """
    Print connection information for IRIS container.

    Args:
        container_name: Container name
        superserver_port: SuperServer port
        webserver_port: Web portal port
        namespace: Default namespace
        username: Username
        password: Password

    Example:
        >>> print_connection_info("iris_db", 1972, 52773, "USER")
        Connection Information:
          SuperServer: localhost:1972
          Web Portal:  http://localhost:52773
          Namespace:   USER
          Username:    _SYSTEM
          Password:    SYS
    """
    print("\nConnection Information:")
    print(f"  SuperServer: localhost:{superserver_port}")
    print(f"  Web Portal:  http://localhost:{webserver_port}")
    print(f"  Namespace:   {namespace}")
    print(f"  Username:    {username}")
    print(f"  Password:    {password}")
