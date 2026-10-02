"""IRISContainer inherits the base validation without separate code (FR-008)."""

import pytest

from iris_devtester.containers.iris_container import IRISContainer


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("IRIS_USERNAME", "IRIS_PASSWORD", "IRIS_NAMESPACE"):
        monkeypatch.delenv(var, raising=False)


def test_bad_namespace_from_environment_raises_same_error(monkeypatch):
    monkeypatch.setenv("IRIS_NAMESPACE", "MY NS; rm")
    with pytest.raises(ValueError) as exc:
        IRISContainer()
    assert "Invalid namespace" in str(exc.value)
    assert "IRIS_NAMESPACE" in str(exc.value)


def test_bad_username_from_environment_raises(monkeypatch):
    monkeypatch.setenv("IRIS_USERNAME", "bad name")
    monkeypatch.setenv("IRIS_PASSWORD", "pw")
    with pytest.raises(ValueError, match="Invalid username"):
        IRISContainer()


def test_valid_environment_accepted(monkeypatch):
    monkeypatch.setenv("IRIS_NAMESPACE", "APP_1")
    assert IRISContainer().namespace == "APP_1"


class TestOwnArguments:
    """FR-008: IRISContainer's own namespace/username/password arguments are validated."""

    def test_bad_namespace_argument_raises_before_start(self):
        with pytest.raises(ValueError) as exc:
            IRISContainer(namespace="MY NS; rm")
        assert "Invalid namespace" in str(exc.value)
        assert "What went wrong" in str(exc.value)

    def test_bad_username_argument_raises(self):
        with pytest.raises(ValueError, match="Invalid username"):
            IRISContainer(username="bad name", password="pw")

    def test_nul_password_argument_raises_without_echo(self):
        with pytest.raises(ValueError) as exc:
            IRISContainer(username="u", password="a\x00b")
        assert "a\x00b" not in str(exc.value)

    def test_valid_arguments_pass_and_defaults_unchanged(self):
        c = IRISContainer(namespace="APP_1", username="svc", password="a\"b'c$(x)")
        assert c._namespace == "APP_1"
        d = IRISContainer()
        assert (d._username, d._password, d._namespace) == ("_SYSTEM", "SYS", "USER")

    def test_user_namespace_any_case_accepted(self):
        assert IRISContainer(namespace="user")._namespace == "user"

    def test_base_still_creates_no_extra_user_or_database(self):
        c = IRISContainer(namespace="APP_1")
        assert c.username is None and c.namespace == "USER"
