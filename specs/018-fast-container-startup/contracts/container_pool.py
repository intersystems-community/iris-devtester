"""
Contract tests for ContainerPool.

These tests define the expected behavior of ContainerPool.
Tests MUST FAIL until implementation is complete.
"""

from unittest.mock import Mock, patch

import pytest


class TestContainerPoolSingleton:
    """Test ContainerPool singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """ContainerPool.instance() returns same object on repeated calls."""
        from iris_devtester.containers.pool import ContainerPool

        pool1 = ContainerPool.instance()
        pool2 = ContainerPool.instance()

        assert pool1 is pool2

    def test_singleton_can_be_reset_for_testing(self):
        """ContainerPool._reset() clears singleton for test isolation."""
        from iris_devtester.containers.pool import ContainerPool

        pool1 = ContainerPool.instance()
        ContainerPool._reset()
        pool2 = ContainerPool.instance()

        assert pool1 is not pool2


class TestContainerPoolGetOrCreate:
    """Test ContainerPool.get_or_create() method."""

    def test_returns_existing_container_if_running(self):
        """get_or_create() returns existing container without creating new."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()

        with patch("docker.from_env") as mock_docker:
            mock_container = Mock()
            mock_container.status = "running"
            mock_docker.return_value.containers.get.return_value = mock_container

            ref = pool.get_or_create("iris-dev")

            assert ref is not None
            assert ref.name == "iris-dev"
            mock_docker.return_value.containers.run.assert_not_called()

    def test_creates_container_if_not_found(self):
        """get_or_create() creates new container if none exists."""
        import docker.errors

        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()

        with patch("docker.from_env") as mock_docker:
            mock_docker.return_value.containers.get.side_effect = docker.errors.NotFound("not found")
            mock_new_container = Mock()
            mock_new_container.id = "abc123"
            mock_new_container.status = "running"
            mock_docker.return_value.containers.run.return_value = mock_new_container

            ref = pool.get_or_create("iris-dev")

            assert ref is not None
            mock_docker.return_value.containers.run.assert_called_once()

    def test_starts_stopped_container(self):
        """get_or_create() starts container if stopped."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()

        with patch("docker.from_env") as mock_docker:
            mock_container = Mock()
            mock_container.status = "exited"
            mock_docker.return_value.containers.get.return_value = mock_container

            ref = pool.get_or_create("iris-dev")

            mock_container.start.assert_called_once()


class TestContainerPoolHealthCheck:
    """Test ContainerPool health check with caching."""

    def test_health_check_uses_cache_when_valid(self):
        """health_check() returns cached result without Docker call."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()
        pool.health_cache.set("iris-dev", True)

        with patch("docker.from_env") as mock_docker:
            result = pool.health_check("iris-dev", use_cache=True)

            assert result is True
            mock_docker.assert_not_called()

    def test_health_check_bypasses_cache_when_requested(self):
        """health_check() checks Docker when use_cache=False."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()
        pool.health_cache.set("iris-dev", True)

        with patch("docker.from_env") as mock_docker:
            mock_container = Mock()
            mock_container.status = "running"
            mock_docker.return_value.containers.get.return_value = mock_container

            result = pool.health_check("iris-dev", use_cache=False)

            assert result is True
            mock_docker.return_value.containers.get.assert_called_once()

    def test_health_check_updates_cache_after_check(self):
        """health_check() updates cache after Docker check."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()

        with patch("docker.from_env") as mock_docker:
            mock_container = Mock()
            mock_container.status = "running"
            mock_docker.return_value.containers.get.return_value = mock_container

            pool.health_check("iris-dev", use_cache=False)

            assert pool.health_cache.get("iris-dev") is True


class TestContainerPoolAcquireRelease:
    """Test ContainerPool acquire/release semantics."""

    def test_acquire_marks_container_in_use(self):
        """acquire() marks container as in_use."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()

        with patch("docker.from_env") as mock_docker:
            mock_container = Mock()
            mock_container.status = "running"
            mock_docker.return_value.containers.get.return_value = mock_container

            ref = pool.acquire("iris-dev")

            assert ref.in_use is True

    def test_release_marks_container_available(self):
        """release() marks container as not in_use."""
        from iris_devtester.containers.pool import ContainerPool

        pool = ContainerPool()

        with patch("docker.from_env") as mock_docker:
            mock_container = Mock()
            mock_container.status = "running"
            mock_docker.return_value.containers.get.return_value = mock_container

            ref = pool.acquire("iris-dev")
            pool.release("iris-dev")

            assert pool.containers["iris-dev"].in_use is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
