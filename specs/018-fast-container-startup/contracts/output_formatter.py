"""
Contract tests for OutputFormatter.

These tests define the expected behavior of OutputFormatter.
Tests MUST FAIL until implementation is complete.
"""

import pytest


class TestOutputFormatterTruncation:
    """Test OutputFormatter truncation behavior."""

    def test_passing_output_limited_to_50_lines(self):
        """Passing test output is limited to 50 lines (NFR-004)."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        raw_output = "\n".join([f"line {i}" for i in range(200)])

        result = formatter.format_test_output(raw_output, is_failing=False)

        lines = result.strip().split("\n")
        assert len(lines) <= 50

    def test_failing_output_limited_to_100_lines(self):
        """Failing test output is limited to 100 lines (NFR-005)."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        raw_output = "\n".join([f"line {i}" for i in range(200)])

        result = formatter.format_test_output(raw_output, is_failing=True)

        lines = result.strip().split("\n")
        assert len(lines) <= 100

    def test_truncation_preserves_head_and_tail(self):
        """Truncation keeps first and last lines, marks middle as omitted."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(max_lines=10)
        raw_output = "\n".join([f"line {i}" for i in range(100)])

        result = formatter.format_test_output(raw_output, is_failing=False)

        assert "line 0" in result  # Head preserved
        assert "line 99" in result  # Tail preserved
        assert "omitted" in result.lower()  # Middle marked

    def test_short_output_not_truncated(self):
        """Output under limit is not truncated."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(max_lines=50)
        raw_output = "\n".join([f"line {i}" for i in range(30)])

        result = formatter.format_test_output(raw_output, is_failing=False)

        lines = result.strip().split("\n")
        assert len(lines) == 30
        assert "omitted" not in result.lower()


class TestOutputFormatterDeduplication:
    """Test OutputFormatter deduplication behavior."""

    def test_consecutive_duplicates_collapsed(self):
        """Consecutive duplicate lines are collapsed with count."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(dedupe_enabled=True)
        raw_output = "line A\nline B\nline B\nline B\nline C"

        result = formatter.format_test_output(raw_output, is_failing=False)

        assert result.count("line B") < 3
        assert "repeated" in result.lower() or "3x" in result

    def test_non_consecutive_duplicates_not_collapsed(self):
        """Non-consecutive duplicates are preserved."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(dedupe_enabled=True)
        raw_output = "line A\nline B\nline A\nline B"

        result = formatter.format_test_output(raw_output, is_failing=False)

        # All lines should be present (not collapsed)
        assert result.count("line A") >= 2 or "repeated" not in result

    def test_deduplication_can_be_disabled(self):
        """Deduplication can be disabled via dedupe_enabled=False."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(dedupe_enabled=False, max_lines=100)
        raw_output = "line A\nline A\nline A"

        result = formatter.format_test_output(raw_output, is_failing=False)

        assert result.count("line A") == 3


class TestOutputFormatterContainerLogs:
    """Test OutputFormatter container log summarization."""

    def test_container_logs_limited_to_20_lines(self):
        """Container logs are summarized to 20 lines max."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        logs = "\n".join([f"[timestamp] log line {i}" for i in range(100)])

        result = formatter.summarize_container_logs(logs)

        lines = result.strip().split("\n")
        assert len(lines) <= 20

    def test_container_logs_prioritize_errors(self):
        """Log summary prioritizes error/warning lines."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        logs = "\n".join([
            "INFO: normal line 1",
            "INFO: normal line 2",
            "ERROR: critical error here",
            "INFO: normal line 3",
            "WARNING: warning message",
        ])

        result = formatter.summarize_container_logs(logs, max_lines=3)

        assert "ERROR" in result
        assert "WARNING" in result


class TestOutputFormatterErrors:
    """Test OutputFormatter error formatting."""

    def test_error_fits_one_screen(self):
        """Formatted error fits in 25 lines (FR-014)."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        error = Exception("Long error message\n" * 50)

        result = formatter.format_error(error)

        lines = result.strip().split("\n")
        assert len(lines) <= 25

    def test_error_includes_type_and_message(self):
        """Formatted error includes exception type and message."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        error = ValueError("specific message here")

        result = formatter.format_error(error)

        assert "ValueError" in result
        assert "specific message here" in result

    def test_error_includes_actionable_traceback(self):
        """Formatted error includes relevant traceback frames."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()

        try:
            raise RuntimeError("test error")
        except RuntimeError as e:
            result = formatter.format_error(e)

        # Should include file/line info
        assert ".py" in result or "line" in result.lower()


class TestOutputFormatterConfiguration:
    """Test OutputFormatter configuration."""

    def test_max_lines_configurable(self):
        """max_lines can be configured via constructor."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(max_lines=25)

        assert formatter.max_lines == 25

    def test_max_lines_failing_configurable(self):
        """max_lines_failing can be configured via constructor."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter(max_lines_failing=75)

        assert formatter.max_lines_failing == 75

    def test_default_settings(self):
        """Default settings match NFR requirements."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()

        assert formatter.max_lines == 50  # NFR-004
        assert formatter.max_lines_failing == 100  # NFR-005
        assert formatter.dedupe_enabled is True


class TestOutputFormatterIntegration:
    """Integration-style contract tests for OutputFormatter."""

    def test_typical_passing_pytest_output(self):
        """Typical passing pytest output formatted correctly."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        # Simulate typical pytest output
        raw = """============================= test session starts ==============================
platform darwin -- Python 3.11.0
collected 50 items

tests/unit/test_example.py::test_one PASSED                              [  2%]
tests/unit/test_example.py::test_two PASSED                              [  4%]
""" + "tests/unit/test_example.py::test_many PASSED\n" * 100 + """
============================== 50 passed in 2.34s ==============================
"""

        result = formatter.format_test_output(raw, is_failing=False)

        lines = result.strip().split("\n")
        assert len(lines) <= 50
        assert "passed" in result.lower()

    def test_typical_failing_pytest_output(self):
        """Typical failing pytest output formatted correctly."""
        from iris_devtester.output.formatter import OutputFormatter

        formatter = OutputFormatter()
        raw = """============================= test session starts ==============================
FAILED tests/unit/test_example.py::test_fail - AssertionError: assert 1 == 2

================================== FAILURES ===================================
____________________________ test_fail ____________________________________

    def test_fail():
>       assert 1 == 2
E       AssertionError: assert 1 == 2

tests/unit/test_example.py:10: AssertionError
""" + "E   Additional context line\n" * 50 + """
=========================== short test summary info ============================
FAILED tests/unit/test_example.py::test_fail - AssertionError
=============================== 1 failed in 0.12s ==============================
"""

        result = formatter.format_test_output(raw, is_failing=True)

        lines = result.strip().split("\n")
        assert len(lines) <= 100
        assert "AssertionError" in result
        assert "failed" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
