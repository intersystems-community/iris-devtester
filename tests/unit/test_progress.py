"""Unit tests for iris_devtester/utils/progress.py."""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from iris_devtester.utils.progress import (
    ProgressIndicator,
    Spinner,
    format_bytes,
    format_duration,
    print_connection_info,
    print_error,
    print_info,
    print_step,
    print_success,
    print_warning,
)


class TestProgressIndicator:
    def test_init_default(self):
        p = ProgressIndicator()
        assert p.current_message == ""
        assert p.is_complete is False

    def test_init_with_message(self):
        p = ProgressIndicator("Starting")
        assert p.current_message == "Starting"

    def test_update_sets_message(self):
        p = ProgressIndicator()
        with patch("sys.stderr", new_callable=StringIO):
            p.update("new message")
        assert p.current_message == "new message"

    def test_complete_sets_is_complete(self):
        p = ProgressIndicator()
        with patch("sys.stderr", new_callable=StringIO):
            p.complete()
        assert p.is_complete is True

    def test_complete_with_message(self):
        p = ProgressIndicator()
        buf = StringIO()
        with patch("sys.stderr", buf):
            p.complete("Done!")
        assert p.is_complete is True
        assert "Done!" in buf.getvalue()

    def test_fail_sets_is_complete(self):
        p = ProgressIndicator()
        with patch("sys.stderr", new_callable=StringIO):
            p.fail("Failed!")
        assert p.is_complete is True

    def test_context_manager_enter_returns_self(self):
        p = ProgressIndicator()
        with patch("sys.stderr", new_callable=StringIO):
            result = p.__enter__()
        assert result is p

    def test_context_manager_calls_update_on_enter(self):
        p = ProgressIndicator("Hello")
        buf = StringIO()
        with patch("sys.stderr", buf):
            p.__enter__()
        assert "Hello" in buf.getvalue()

    def test_context_manager_no_update_if_empty_message(self):
        p = ProgressIndicator()
        buf = StringIO()
        with patch("sys.stderr", buf):
            p.__enter__()
        assert buf.getvalue() == ""

    def test_context_manager_complete_on_exit(self):
        buf = StringIO()
        with patch("sys.stderr", buf):
            with ProgressIndicator("test") as p:
                pass
        assert p.is_complete is True

    def test_context_manager_no_complete_on_exception(self):
        p = ProgressIndicator()
        buf = StringIO()
        try:
            with patch("sys.stderr", buf):
                with p:
                    raise ValueError("error")
        except ValueError:
            pass
        # complete should not have been called since exception occurred
        assert p.is_complete is False

    def test_context_manager_no_double_complete(self):
        buf = StringIO()
        with patch("sys.stderr", buf):
            with ProgressIndicator() as p:
                p.complete("manual complete")
        assert p.is_complete is True


class TestPrintFunctions:
    def test_print_success(self, capsys):
        print_success("all good")
        out, _ = capsys.readouterr()
        assert "all good" in out
        assert "✓" in out

    def test_print_error(self, capsys):
        print_error("something failed")
        _, err = capsys.readouterr()
        assert "something failed" in err
        assert "✗" in err

    def test_print_warning(self, capsys):
        print_warning("watch out")
        _, err = capsys.readouterr()
        assert "watch out" in err
        assert "⚠" in err

    def test_print_info(self, capsys):
        print_info("just info")
        out, _ = capsys.readouterr()
        assert "just info" in out
        assert "ℹ" in out

    def test_print_step(self, capsys):
        print_step(2, 5, "Downloading image")
        out, _ = capsys.readouterr()
        assert "[2/5]" in out
        assert "Downloading image" in out


class TestFormatDuration:
    def test_zero_seconds(self):
        assert format_duration(0) == "0s"

    def test_seconds_only(self):
        assert format_duration(30) == "30s"

    def test_minutes_and_seconds(self):
        assert format_duration(65) == "1m 5s"

    def test_exactly_one_minute(self):
        assert format_duration(60) == "1m 0s"

    def test_hours_minutes_seconds(self):
        assert format_duration(3665) == "1h 1m 5s"

    def test_exactly_one_hour(self):
        assert format_duration(3600) == "1h 0m 0s"

    def test_large_value(self):
        result = format_duration(7384)
        assert "h" in result


class TestFormatBytes:
    def test_zero_bytes(self):
        assert format_bytes(0) == "0.0 B"

    def test_bytes(self):
        result = format_bytes(500)
        assert "B" in result

    def test_kilobytes(self):
        result = format_bytes(1024)
        assert "KB" in result
        assert "1.0" in result

    def test_megabytes(self):
        result = format_bytes(1024 * 1024)
        assert "MB" in result
        assert "1.0" in result

    def test_gigabytes(self):
        result = format_bytes(1024 * 1024 * 1024)
        assert "GB" in result

    def test_terabytes(self):
        result = format_bytes(1024 ** 4)
        assert "TB" in result


class TestSpinner:
    def test_init(self):
        s = Spinner("Loading")
        assert s.message == "Loading"
        assert s.is_spinning is False

    def test_start_sets_spinning(self):
        s = Spinner("test")
        with patch("sys.stderr", new_callable=StringIO):
            s.start()
        assert s.is_spinning is True

    def test_stop_clears_spinning(self):
        s = Spinner("test")
        buf = StringIO()
        with patch("sys.stderr", buf):
            s.start()
            s.stop()
        assert s.is_spinning is False

    def test_stop_with_message(self):
        s = Spinner("test")
        buf = StringIO()
        with patch("sys.stderr", buf):
            s.start()
            s.stop("All done")
        assert "All done" in buf.getvalue()

    def test_update_changes_message(self):
        s = Spinner("old")
        with patch("sys.stderr", new_callable=StringIO):
            s.start()
            s.update("new")
        assert s.message == "new"

    def test_show_frame_no_op_when_not_spinning(self):
        s = Spinner("test")
        buf = StringIO()
        with patch("sys.stderr", buf):
            s._show_frame()
        assert buf.getvalue() == ""


class TestPrintConnectionInfo:
    def test_prints_superserver_port(self, capsys):
        print_connection_info("iris_db", 1972, 52773, "USER")
        out, _ = capsys.readouterr()
        assert "1972" in out

    def test_prints_webserver_port(self, capsys):
        print_connection_info("iris_db", 1972, 52773, "USER")
        out, _ = capsys.readouterr()
        assert "52773" in out

    def test_prints_namespace(self, capsys):
        print_connection_info("iris_db", 1972, 52773, "MYNS")
        out, _ = capsys.readouterr()
        assert "MYNS" in out

    def test_prints_username(self, capsys):
        print_connection_info("iris_db", 1972, 52773, "USER", username="admin")
        out, _ = capsys.readouterr()
        assert "admin" in out

    def test_prints_password(self, capsys):
        print_connection_info("iris_db", 1972, 52773, "USER", password="secret")
        out, _ = capsys.readouterr()
        assert "secret" in out
