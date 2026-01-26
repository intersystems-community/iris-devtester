"""
Contract tests for HealthCache.

These tests define the expected behavior of HealthCache.
Tests MUST FAIL until implementation is complete.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


class TestHealthCacheGet:
    """Test HealthCache.get() method."""

    def test_get_returns_none_for_missing_entry(self):
        """get() returns None when no cache entry exists."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_get_returns_cached_value_when_valid(self):
        """get() returns cached boolean when within TTL."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache(ttl_seconds=30)
        cache.set("iris-dev", True)

        result = cache.get("iris-dev")

        assert result is True

    def test_get_returns_none_when_expired(self):
        """get() returns None when cache entry has expired."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache(ttl_seconds=1)
        cache.set("iris-dev", True)

        # Simulate time passing
        with patch("iris_devtester.containers.health_cache.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now() + timedelta(seconds=5)

            result = cache.get("iris-dev")

            assert result is None


class TestHealthCacheSet:
    """Test HealthCache.set() method."""

    def test_set_stores_healthy_status(self):
        """set() stores True for healthy container."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        cache.set("iris-dev", True)

        assert cache.get("iris-dev") is True

    def test_set_stores_unhealthy_status(self):
        """set() stores False for unhealthy container."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        cache.set("iris-dev", False)

        assert cache.get("iris-dev") is False

    def test_set_overwrites_previous_entry(self):
        """set() replaces existing cache entry."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()
        cache.set("iris-dev", True)
        cache.set("iris-dev", False)

        assert cache.get("iris-dev") is False

    def test_set_records_timestamp(self):
        """set() records the time of the check."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        before = datetime.now()
        cache.set("iris-dev", True)
        after = datetime.now()

        entry = cache.results.get("iris-dev")
        assert entry is not None
        assert before <= entry.checked_at <= after


class TestHealthCacheInvalidate:
    """Test HealthCache.invalidate() method."""

    def test_invalidate_removes_specific_entry(self):
        """invalidate(name) removes only that entry."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()
        cache.set("iris-dev", True)
        cache.set("iris-other", True)

        cache.invalidate("iris-dev")

        assert cache.get("iris-dev") is None
        assert cache.get("iris-other") is True

    def test_invalidate_all_clears_cache(self):
        """invalidate() with no args clears all entries."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()
        cache.set("iris-dev", True)
        cache.set("iris-other", True)

        cache.invalidate()

        assert cache.get("iris-dev") is None
        assert cache.get("iris-other") is None

    def test_invalidate_nonexistent_is_noop(self):
        """invalidate() for missing entry doesn't raise."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        # Should not raise
        cache.invalidate("nonexistent")


class TestHealthCacheIsValid:
    """Test HealthCache.is_valid() method."""

    def test_is_valid_returns_true_for_fresh_entry(self):
        """is_valid() returns True when entry is within TTL."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache(ttl_seconds=30)
        cache.set("iris-dev", True)

        assert cache.is_valid("iris-dev") is True

    def test_is_valid_returns_false_for_expired_entry(self):
        """is_valid() returns False when entry has expired."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache(ttl_seconds=1)
        cache.set("iris-dev", True)

        with patch("iris_devtester.containers.health_cache.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now() + timedelta(seconds=5)

            assert cache.is_valid("iris-dev") is False

    def test_is_valid_returns_false_for_missing_entry(self):
        """is_valid() returns False when no entry exists."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        assert cache.is_valid("nonexistent") is False


class TestHealthCacheTTLConfiguration:
    """Test HealthCache TTL configuration."""

    def test_default_ttl_is_30_seconds(self):
        """Default TTL is 30 seconds for local dev."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()

        assert cache.ttl_seconds == 30.0

    def test_ttl_configurable_via_constructor(self):
        """TTL can be set via constructor."""
        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache(ttl_seconds=5.0)

        assert cache.ttl_seconds == 5.0

    def test_ttl_from_environment_variable(self):
        """TTL can be configured via IRIS_HEALTH_CACHE_TTL env var."""
        import os

        from iris_devtester.containers.health_cache import HealthCache

        with patch.dict(os.environ, {"IRIS_HEALTH_CACHE_TTL": "10"}):
            cache = HealthCache.from_env()

            assert cache.ttl_seconds == 10.0


class TestHealthCachePerformance:
    """Test HealthCache performance requirements."""

    def test_get_completes_under_100ms(self):
        """get() returns within 100ms (NFR-003)."""
        import time

        from iris_devtester.containers.health_cache import HealthCache

        cache = HealthCache()
        cache.set("iris-dev", True)

        start = time.perf_counter()
        for _ in range(1000):
            cache.get("iris-dev")
        elapsed = time.perf_counter() - start

        # 1000 calls should complete in <100ms total
        assert elapsed < 0.1, f"1000 gets took {elapsed:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
