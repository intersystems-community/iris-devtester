from unittest.mock import MagicMock, patch
import pytest


class TestStopGracefully:
    def test_stop_gracefully_calls_iris_stop(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"")
        with patch.object(iris, "get_wrapped_container", return_value=mock_container):
            result = iris.stop_gracefully()
        mock_container.exec_run.assert_called_once_with(
            "iris stop IRIS quietly", user="irisowner"
        )
        assert result is True

    def test_stop_gracefully_returns_false_when_container_none(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        with patch.object(iris, "get_wrapped_container", return_value=None):
            result = iris.stop_gracefully()
        assert result is False

    def test_stop_gracefully_returns_false_on_exception(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        with patch.object(iris, "get_wrapped_container", side_effect=RuntimeError("not started")):
            result = iris.stop_gracefully()
        assert result is False

    def test_exit_calls_stop_gracefully_then_super(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        calls = []
        with patch.object(iris, "stop_gracefully", side_effect=lambda **kw: calls.append("graceful") or True), \
             patch.object(type(iris).__mro__[1], "__exit__", lambda *a: calls.append("super")):
            iris.__exit__(None, None, None)
        assert calls == ["graceful", "super"]
