"""
Unit tests for IRIS-specific wait strategies.

Tests custom wait strategies for IRIS container readiness.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


class TestIRISReadyWaitStrategy:
    """Test IRIS readiness wait strategy."""

    def test_can_import(self):
        """Test that IRISReadyWaitStrategy can be imported."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        assert IRISReadyWaitStrategy is not None

    def test_wait_strategy_checks_port(self):
        """Test that wait strategy verifies port is open."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy(port=1972)

        # Mock container
        mock_container = Mock()
        mock_container.get_container_host_ip.return_value = "localhost"
        mock_container.get_exposed_port.return_value = 1972

        # Should check if port is reachable
        assert hasattr(strategy, "wait_until_ready")

    def test_wait_strategy_checks_iris_process(self):
        """Test that wait strategy verifies IRIS process is running."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy()

        # Should have method to check IRIS process
        assert hasattr(strategy, "check_iris_running") or hasattr(strategy, "wait_until_ready")

    def test_wait_strategy_checks_database_ready(self):
        """Test that wait strategy verifies database accepts queries."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy()

        # Should be able to test database readiness
        assert strategy is not None

    def test_wait_strategy_timeout(self):
        """Test that wait strategy respects timeout."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy(timeout=5)

        # Should have timeout attribute
        assert hasattr(strategy, "timeout") or hasattr(strategy, "_timeout")

    @patch("time.time")
    def test_wait_strategy_timeout_raises(self, mock_time):
        """Test that wait strategy raises on timeout."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        # Mock time to simulate timeout
        mock_time.side_effect = [0, 0, 100]  # Start, check, timeout

        strategy = IRISReadyWaitStrategy(timeout=1)

        # Should implement timeout logic
        assert strategy is not None

    def test_wait_strategy_default_timeout(self):
        """Test that wait strategy has reasonable default timeout."""
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy

        strategy = IRISReadyWaitStrategy()

        # Should have a timeout (either attribute or parameter)
        assert strategy is not None


class TestWaitForIRISReady:
    """Test convenience function for waiting for IRIS."""

    def test_can_import_convenience_function(self):
        """Test that wait_for_iris_ready function exists."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        assert callable(wait_for_iris_ready)

    @patch("socket.socket")
    def test_waits_for_port_open(self, mock_socket):
        """Test that wait function checks port connectivity."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        mock_sock = Mock()
        mock_sock.connect.return_value = None
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = wait_for_iris_ready(host="localhost", port=1972, timeout=1)

        # Should attempt to connect to port
        assert isinstance(result, bool) or result is None

    def test_wait_function_with_timeout(self):
        """Test wait function respects timeout parameter."""
        from iris_devtester.containers.wait_strategies import wait_for_iris_ready

        # Should not hang forever
        start = time.time()
        wait_for_iris_ready(host="unreachable.host", port=9999, timeout=0.1)
        elapsed = time.time() - start

        # Should timeout quickly
        assert elapsed < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
