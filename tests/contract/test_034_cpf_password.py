from unittest.mock import MagicMock, patch, call
import pytest


class TestStartCPFInjection:
    def test_start_injects_cpf_merge_when_none_configured(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        with patch.object(iris, "with_cpf_merge", return_value=iris) as mock_cpf, \
             patch.object(iris, "with_env", return_value=iris), \
             patch.object(iris, "get_config"), \
             patch.object(type(iris).__mro__[1], "start", lambda self: None):
            iris.start()
        mock_cpf.assert_called_once()
        cpf_arg = mock_cpf.call_args[0][0]
        assert "ChangePassword=0" in cpf_arg
        assert "_SYSTEM" in cpf_arg

    def test_start_skips_cpf_if_already_configured(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        iris._cpf_temp_files = ["/tmp/existing.cpf"]
        with patch.object(iris, "with_cpf_merge", return_value=iris) as mock_cpf, \
             patch.object(iris, "with_env", return_value=iris), \
             patch.object(iris, "get_config"), \
             patch.object(type(iris).__mro__[1], "start", lambda self: None):
            iris.start()
        mock_cpf.assert_not_called()

    def test_start_sets_password_handled_true(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        assert iris._password_handled is False
        with patch.object(iris, "with_cpf_merge", return_value=iris), \
             patch.object(iris, "with_env", return_value=iris), \
             patch.object(iris, "get_config"), \
             patch.object(type(iris).__mro__[1], "start", lambda self: None):
            iris.start()
        assert iris._password_handled is True

    def test_start_merges_password_hash_when_preconfigured(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        iris._preconfigure_password = "myhash"
        with patch.object(iris, "with_cpf_merge", return_value=iris) as mock_cpf, \
             patch.object(iris, "with_env", return_value=iris), \
             patch.object(iris, "get_config"), \
             patch.object(type(iris).__mro__[1], "start", lambda self: None):
            iris.start()
        cpf_arg = mock_cpf.call_args[0][0]
        assert "myhash" in cpf_arg
        assert "ChangePassword=0" in cpf_arg


class TestGetConnectionOptimisticFallback:
    def _make_iris(self, password_handled=False):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        iris._password_handled = password_handled
        iris._callin_enabled = True
        iris._connection = None
        return iris

    def test_no_unexpire_call_on_clean_connection(self):
        iris = self._make_iris(password_handled=True)
        mock_conn = MagicMock()
        with patch.object(iris, "get_config"), \
             patch("iris_devtester.containers.iris_container.get_connection", return_value=mock_conn), \
             patch("iris_devtester.utils.password.unexpire_all_passwords") as mock_unexpire:
            result = iris.get_connection(enable_callin=False)
        mock_unexpire.assert_not_called()
        assert result is mock_conn

    def test_fallback_on_password_change_error(self):
        iris = self._make_iris(password_handled=False)
        mock_conn = MagicMock()
        pw_error = ConnectionError("Password change required")
        with patch.object(iris, "get_config"), \
             patch.object(iris, "get_container_name", return_value="iris_db"), \
             patch("iris_devtester.containers.iris_container.get_connection",
                   side_effect=[pw_error, mock_conn]), \
             patch("iris_devtester.utils.password.detect_password_change_required",
                   return_value=True), \
             patch("iris_devtester.utils.password.unexpire_all_passwords") as mock_unexpire:
            result = iris.get_connection(enable_callin=False)
        mock_unexpire.assert_called_once_with("iris_db")
        assert result is mock_conn
        assert iris._password_handled is True

    def test_no_double_fallback_when_already_handled(self):
        iris = self._make_iris(password_handled=True)
        pw_error = ConnectionError("Password change required")
        with patch.object(iris, "get_config"), \
             patch("iris_devtester.containers.iris_container.get_connection",
                   side_effect=pw_error), \
             patch("iris_devtester.utils.password.detect_password_change_required",
                   return_value=True), \
             patch("iris_devtester.utils.password.unexpire_all_passwords") as mock_unexpire:
            with pytest.raises(ConnectionError):
                iris.get_connection(enable_callin=False)
        mock_unexpire.assert_not_called()

    def test_non_password_errors_propagate_unchanged(self):
        iris = self._make_iris(password_handled=False)
        with patch.object(iris, "get_config"), \
             patch("iris_devtester.containers.iris_container.get_connection",
                   side_effect=RuntimeError("container not started")):
            with pytest.raises(RuntimeError, match="container not started"):
                iris.get_connection(enable_callin=False)


class TestPasswordHandledInitDefault:
    def test_password_handled_false_on_new_instance(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        assert iris._password_handled is False

    def test_attach_does_not_set_password_handled(self):
        from iris_devtester.containers.iris_container import IRISContainer
        iris = IRISContainer.community()
        iris._is_attached = True
        assert iris._password_handled is False
