"""
Contract tests for password reset retry logic (Feature 015).

These tests verify that reset_password() implements proper retry behavior
with exponential backoff and early exit for maximum reliability.

Contract: Retry on transient errors, fail fast on permanent errors.

Expected to PASS after implementation (TDD green phase).
"""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.utils.password_reset import reset_password
from iris_devtester.utils.password_verification import (
    ConnectionVerificationResult,
    VerificationConfig,
)


class TestRetryLogicContract:
    """Contract tests for retry logic (FR-007, NFR-004)."""

    def test_retry_on_access_denied(self, iris_container, monkeypatch):
        """
        Contract: MUST retry on "Access Denied" errors (transient/timing issues).

        Validates FR-007: Retry with exponential backoff on transient failures
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        # Mock subprocess to succeed (password reset command succeeds)
        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            # Fail first 2 attempts, succeed on 3rd
            if attempt_count["value"] < 3:
                raise Exception("Access Denied")
            # Third attempt succeeds
            from unittest.mock import MagicMock
            conn = MagicMock()
            cursor = MagicMock()
            cursor.fetchone.return_value = [1]
            conn.cursor.return_value = cursor
            return conn

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password (should retry and succeed)
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="RETRYTEST",
            hostname=config.host,
            port=config.port,
            namespace=config.namespace
        )

        # Contract assertion: Must have retried
        assert attempt_count["value"] == 3, (
            f"Expected 3 verification attempts (2 retries), got {attempt_count['value']}"
        )

        # Contract assertion: Must succeed after retries
        assert result.success, f"Should succeed after retries: {result.message}"
        assert result.verification_attempts == 3

    def test_fail_fast_on_non_retryable_errors(self, iris_container, monkeypatch):
        """
        Contract: MUST fail fast on non-retryable errors (e.g., connection refused).

        Validates: Don't waste time retrying permanent failures
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            # Simulate connection refused (non-retryable)
            raise Exception("Connection refused")

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password (should fail fast without retries)
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="FAILFAST",
            hostname=config.host,
            port=config.port,
            namespace=config.namespace
        )

        # Contract assertion: Must NOT retry on non-retryable errors
        assert attempt_count["value"] == 1, (
            f"Should fail fast (1 attempt) on connection refused, got {attempt_count['value']}"
        )

        # Contract assertion: Must return failure
        assert not result.success
        assert result.verification_attempts == 1

    def test_early_exit_on_verification_success(self, iris_container, monkeypatch):
        """
        Contract: MUST exit immediately when verification succeeds (FR-007).

        Validates: Don't waste time with additional retries after success
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            # Succeed on first attempt
            from unittest.mock import MagicMock
            conn = MagicMock()
            cursor = MagicMock()
            cursor.fetchone.return_value = [1]
            conn.cursor.return_value = cursor
            return conn

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password (should succeed immediately)
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="EARLYEXIT",
            hostname=config.host,
            port=config.port,
            namespace=config.namespace
        )

        # Contract assertion: Must exit early (no unnecessary retries)
        assert attempt_count["value"] == 1, (
            f"Should exit immediately on success (1 attempt), got {attempt_count['value']}"
        )

        # Contract assertion: Must succeed
        assert result.success
        assert result.verification_attempts == 1

    def test_respect_max_retries_limit(self, iris_container, monkeypatch):
        """
        Contract: MUST respect max_retries=3 limit (NFR-004).

        Validates: Don't retry indefinitely, give up after max_retries
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            # Always fail (simulate password never ready)
            raise Exception("Access Denied")

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password (should fail after max_retries)
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="MAXRETRIES",
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
            verification_config=VerificationConfig(max_retries=3)
        )

        # Contract assertion: Must stop after max_retries
        assert attempt_count["value"] == 3, (
            f"Should stop after max_retries=3, got {attempt_count['value']} attempts"
        )

        # Contract assertion: Must return failure
        assert not result.success
        assert result.verification_attempts == 3

    def test_exponential_backoff_timing(self, iris_container, monkeypatch):
        """
        Contract: MUST use exponential backoff (100ms → 200ms → 400ms).

        Validates FR-007: Exponential backoff between retries
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        attempt_times = []
        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            attempt_times.append(time.time())
            # Fail first 2 attempts, succeed on 3rd
            if attempt_count["value"] < 3:
                raise Exception("Access Denied")
            # Third attempt succeeds
            from unittest.mock import MagicMock
            conn = MagicMock()
            cursor = MagicMock()
            cursor.fetchone.return_value = [1]
            conn.cursor.return_value = cursor
            return conn

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password with explicit backoff config
        result = reset_password(
            container_name=container_name,
            username="SuperUser",
            new_password="BACKOFF",
            hostname=config.host,
            port=config.port,
            namespace=config.namespace,
            verification_config=VerificationConfig(
                max_retries=3,
                initial_backoff_ms=100,
                exponential_backoff=True
            )
        )

        # Contract assertion: Must have 3 attempts
        assert len(attempt_times) == 3

        # Calculate delays between attempts
        delay_1_to_2 = (attempt_times[1] - attempt_times[0]) * 1000  # ms
        delay_2_to_3 = (attempt_times[2] - attempt_times[1]) * 1000  # ms

        # Contract assertion: First backoff ~100ms (allow ±50ms tolerance)
        assert 50 <= delay_1_to_2 <= 200, (
            f"First backoff should be ~100ms, got {delay_1_to_2:.1f}ms"
        )

        # Contract assertion: Second backoff ~200ms (2x first)
        assert 150 <= delay_2_to_3 <= 350, (
            f"Second backoff should be ~200ms (2x first), got {delay_2_to_3:.1f}ms"
        )

        # Verify exponential growth (2x)
        ratio = delay_2_to_3 / delay_1_to_2
        assert 1.5 <= ratio <= 2.5, (
            f"Backoff should double (ratio ~2), got {ratio:.2f}x"
        )

    def test_log_retry_attempts(self, iris_container, monkeypatch, caplog):
        """
        Contract: MUST log all retry attempts with timing (Constitutional Principle #7).

        Validates: Diagnostic logging for troubleshooting
        """
        container_name = iris_container.get_container_name()
        config = iris_container.get_config()

        attempt_count = {"value": 0}

        def mock_dbapi_connect(*args, **kwargs):
            attempt_count["value"] += 1
            # Fail first attempt, succeed on second
            if attempt_count["value"] < 2:
                raise Exception("Access Denied")
            from unittest.mock import MagicMock
            conn = MagicMock()
            cursor = MagicMock()
            cursor.fetchone.return_value = [1]
            conn.cursor.return_value = cursor
            return conn

        try:
            import iris.dbapi as dbapi
            monkeypatch.setattr("iris.dbapi.connect", mock_dbapi_connect)
        except ImportError:
            pytest.skip("DBAPI not available for testing")

        # Reset password with debug logging
        with caplog.at_level(logging.DEBUG):
            result = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password="LOGGING",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace
            )

        # Contract assertion: Must log verification attempts
        log_records = [r.message for r in caplog.records]

        # Should log multiple verification attempts
        verification_logs = [
            log for log in log_records
            if "verification" in log.lower() or "attempt" in log.lower()
        ]

        assert len(verification_logs) >= 2, (
            f"Should log verification attempts, found {len(verification_logs)} logs"
        )

        # Should log success
        success_logs = [
            log for log in log_records
            if "verified" in log.lower() or "success" in log.lower()
        ]

        assert len(success_logs) > 0, "Should log verification success"

    def test_high_success_rate_on_macos(self, iris_container):
        """
        Contract: MUST achieve >= 99% success rate on macOS (NFR-001).

        Validates: Reliability target for production use

        Note: This test runs 10 password resets to measure success rate.
        May take ~60 seconds to complete.
        """
        config = iris_container.get_config()
        container_name = iris_container.get_container_name()

        successes = 0
        total_attempts = 10

        for i in range(total_attempts):
            result = reset_password(
                container_name=container_name,
                username="SuperUser",
                new_password=f"RELIABLE{i}",
                hostname=config.host,
                port=config.port,
                namespace=config.namespace
            )

            if result.success:
                successes += 1

        success_rate = (successes / total_attempts) * 100

        # Contract assertion: Must achieve >= 99% success rate
        assert success_rate >= 99.0, (
            f"Success rate {success_rate:.1f}% below 99% target (NFR-001). "
            f"{successes}/{total_attempts} succeeded"
        )
