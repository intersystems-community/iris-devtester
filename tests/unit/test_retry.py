"""
Unit tests for retry logic module.

Tests verify exponential backoff and retry behavior.
"""

import time
from unittest.mock import MagicMock, patch
import pytest

from iris_devtester.connections.retry import (
    retry_with_backoff,
    create_connection_with_retry,
)


class TestRetryWithBackoff:
    """Test retry_with_backoff function."""

    def test_successful_on_first_attempt(self):
        """
        Test function succeeds on first attempt.

        Expected: Returns result immediately, no retries.
        """
        mock_func = MagicMock(return_value="success")

        result = retry_with_backoff(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_successful_on_second_attempt(self):
        """
        Test function succeeds on second attempt.

        Expected: Retries once, returns result.
        """
        mock_func = MagicMock(side_effect=[
            Exception("First attempt failed"),
            "success"
        ])

        result = retry_with_backoff(mock_func, max_retries=3, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_exhausts_all_retries(self):
        """
        Test behavior when all retries exhausted.

        Expected: Raises last exception after max_retries attempts.
        """
        mock_func = MagicMock(side_effect=Exception("Always fails"))

        with pytest.raises(Exception, match="Always fails"):
            retry_with_backoff(mock_func, max_retries=3, initial_delay=0.01)

        assert mock_func.call_count == 3

    def test_exponential_backoff_delays(self):
        """
        Test that delays follow exponential backoff pattern.

        Expected: Delays increase exponentially (0.1s → 0.2s → 0.4s).
        """
        mock_func = MagicMock(side_effect=[
            Exception("Attempt 1"),
            Exception("Attempt 2"),
            Exception("Attempt 3"),
        ])

        start_time = time.time()

        with pytest.raises(Exception):
            retry_with_backoff(
                mock_func,
                max_retries=3,
                initial_delay=0.1,
                backoff_factor=2.0,
            )

        total_time = time.time() - start_time

        # Total delay should be approximately 0.1 + 0.2 = 0.3s
        # (third attempt fails immediately, no delay after)
        assert 0.25 < total_time < 0.5  # Allow some timing variance

    def test_max_delay_caps_backoff(self):
        """
        Test that max_delay prevents delays from growing too large.

        Expected: Delays capped at max_delay.
        """
        mock_func = MagicMock(side_effect=[
            Exception("Attempt 1"),
            Exception("Attempt 2"),
            Exception("Attempt 3"),
            Exception("Attempt 4"),
        ])

        start_time = time.time()

        with pytest.raises(Exception):
            retry_with_backoff(
                mock_func,
                max_retries=4,
                initial_delay=0.5,
                backoff_factor=10.0,  # Would grow to 5s, 50s, but capped
                max_delay=0.6,  # Cap at 0.6s
            )

        total_time = time.time() - start_time

        # Delays should be: 0.5s, 0.6s, 0.6s (all capped)
        # Total ≈ 1.7s
        assert 1.5 < total_time < 2.2

    def test_custom_retry_count(self):
        """
        Test with custom retry count.

        Expected: Respects max_retries parameter.
        """
        mock_func = MagicMock(side_effect=Exception("Always fails"))

        with pytest.raises(Exception):
            retry_with_backoff(mock_func, max_retries=5, initial_delay=0.01)

        assert mock_func.call_count == 5

    def test_zero_retries(self):
        """
        Test with zero retries.

        Expected: Tries once, no retries on failure.
        """
        mock_func = MagicMock(side_effect=Exception("Immediate failure"))

        with pytest.raises(RuntimeError, match="Retry failed with no exception"):
            retry_with_backoff(mock_func, max_retries=0, initial_delay=0.01)

        # With max_retries=0, the loop doesn't execute, so call_count is 0
        assert mock_func.call_count == 0


class TestCreateConnectionWithRetry:
    """Test create_connection_with_retry function."""

    def test_successful_connection_first_try(self):
        """
        Test successful connection on first attempt.

        Expected: Returns connection immediately.
        """
        mock_connection = MagicMock()
        mock_func = MagicMock(return_value=mock_connection)

        result = create_connection_with_retry(mock_func, max_retries=3)

        assert result == mock_connection
        assert mock_func.call_count == 1

    def test_successful_connection_after_retries(self):
        """
        Test successful connection after initial failures.

        Expected: Retries and succeeds.
        """
        mock_connection = MagicMock()
        mock_func = MagicMock(side_effect=[
            Exception("Connection refused"),
            Exception("Timeout"),
            mock_connection
        ])

        result = create_connection_with_retry(mock_func, max_retries=3)

        assert result == mock_connection
        assert mock_func.call_count == 3

    def test_connection_fails_all_retries(self):
        """
        Test behavior when connection fails all retries.

        Expected: Raises last exception.
        """
        mock_func = MagicMock(side_effect=Exception("Cannot connect"))

        with pytest.raises(Exception, match="Cannot connect"):
            create_connection_with_retry(mock_func, max_retries=3)

        assert mock_func.call_count == 3

    def test_uses_correct_retry_defaults(self):
        """
        Test that default retry parameters match rag-templates pattern.

        Expected: Uses 0.5s, 1s, 2s delay pattern.
        """
        mock_func = MagicMock(side_effect=[
            Exception("Attempt 1"),
            Exception("Attempt 2"),
            Exception("Attempt 3"),
        ])

        start_time = time.time()

        with pytest.raises(Exception):
            create_connection_with_retry(mock_func, max_retries=3)

        total_time = time.time() - start_time

        # Delays should be 0.5s + 1.0s = 1.5s total
        # (third attempt fails immediately, no delay after)
        assert 1.3 < total_time < 2.0


class TestRetryEdgeCases:
    """Test edge cases and error conditions."""

    def test_function_returns_none(self):
        """
        Test retry when function returns None.

        Expected: Accepts None as valid return value.
        """
        mock_func = MagicMock(return_value=None)

        result = retry_with_backoff(mock_func, max_retries=3)

        assert result is None
        assert mock_func.call_count == 1

    def test_function_raises_different_exceptions(self):
        """
        Test retry with different exception types.

        Expected: Retries regardless of exception type.
        """
        mock_func = MagicMock(side_effect=[
            ValueError("Type error"),
            ConnectionError("Network error"),
            "success"
        ])

        result = retry_with_backoff(mock_func, max_retries=3, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_negative_retry_count_treated_as_zero(self):
        """
        Test behavior with negative retry count.

        Expected: Treats as zero (no attempts).
        """
        mock_func = MagicMock(side_effect=Exception("Should not be called"))

        # With max_retries < 0, the loop should make 0 attempts
        # (range(max_retries) with negative number is empty)
        with pytest.raises(RuntimeError, match="Retry failed with no exception"):
            retry_with_backoff(mock_func, max_retries=-1, initial_delay=0.01)

        # Should not be called at all
        assert mock_func.call_count == 0
