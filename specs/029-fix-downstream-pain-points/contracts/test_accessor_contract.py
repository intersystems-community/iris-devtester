"""Contract tests for Feature 029: public password/username accessors.

These tests define the API contract BEFORE implementation.
They should FAIL until get_password()/get_username() are implemented.
"""

class TestPublicPasswordAccessor:
    """FR-001: IRISContainer MUST expose get_password() returning configured password."""

    def test_get_password_returns_default(self):
        """Default password is 'SYS'."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        assert iris.get_password() == "SYS"

    def test_get_password_after_with_credentials(self):
        """with_credentials() updates the returned password."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        iris.with_credentials("_SYSTEM", "MyPass")
        assert iris.get_password() == "MyPass"

    def test_get_password_after_with_preconfigured_password(self):
        """with_preconfigured_password() updates the returned password."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        iris.with_preconfigured_password("PreConf")
        assert iris.get_password() == "PreConf"

    def test_get_password_before_start(self):
        """get_password() works before the container is started."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        # Must not raise — no start required
        password = iris.get_password()
        assert isinstance(password, str)
        assert len(password) > 0


class TestPublicUsernameAccessor:
    """FR-002: IRISContainer MUST expose get_username() returning configured username."""

    def test_get_username_returns_default(self):
        """Default username is '_SYSTEM'."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        assert iris.get_username() == "_SYSTEM"

    def test_get_username_after_with_credentials(self):
        """with_credentials() updates the returned username."""
        from iris_devtester.containers.iris_container import IRISContainer

        iris = IRISContainer.community()
        iris.with_credentials("admin", "pass")
        assert iris.get_username() == "admin"


class TestRyukDocumentation:
    """FR-005/FR-006/FR-007: Docstrings MUST document Ryuk lifecycle."""

    def test_class_docstring_mentions_ryuk(self):
        """IRISContainer class docstring mentions Ryuk/cleanup behavior."""
        from iris_devtester.containers.iris_container import IRISContainer

        docstring = IRISContainer.__doc__ or ""
        assert "ryuk" in docstring.lower() or "cleanup" in docstring.lower(), (
            "IRISContainer class docstring must mention Ryuk or cleanup behavior"
        )

    def test_attach_docstring_mentions_persistent(self):
        """attach() docstring mentions persistent containers / CLI usage."""
        from iris_devtester.containers.iris_container import IRISContainer

        docstring = IRISContainer.attach.__doc__ or ""
        assert "persist" in docstring.lower() or "cli" in docstring.lower(), (
            "attach() docstring must mention persistent containers or CLI usage"
        )

    def test_community_docstring_mentions_cleanup(self):
        """community() docstring mentions process-exit cleanup."""
        from iris_devtester.containers.iris_container import IRISContainer

        docstring = IRISContainer.community.__doc__ or ""
        assert "exit" in docstring.lower() or "cleanup" in docstring.lower() or "ryuk" in docstring.lower(), (
            "community() docstring must mention cleanup on process exit"
        )
