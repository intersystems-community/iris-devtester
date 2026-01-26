"""Additional unit tests for password pre-configuration feature."""

import os
from unittest.mock import MagicMock, patch

import pytest

from iris_devtester.containers.iris_container import IRISContainer


@pytest.fixture
def clean_env():
    """Clean environment variables for testing."""
    env_to_clear = ["IRIS_PASSWORD", "IRIS_USERNAME", "IRIS_TEST_MODE"]
    old_values = {k: os.environ.get(k) for k in env_to_clear}

    for k in env_to_clear:
        if k in os.environ:
            del os.environ[k]

    yield

    for k, v in old_values.items():
        if v is None:
            if k in os.environ:
                del os.environ[k]
        else:
            os.environ[k] = v


def test_with_credentials_callable():
    """Test that with_credentials is callable and sets attributes."""
    container = IRISContainer()
    result = container.with_credentials("admin", "secret")
    assert container._preconfigure_username == "admin"
    assert container._preconfigure_password == "secret"
    assert result is container


def test_with_preconfigured_password_sets_password(clean_env):
    """Test that with_preconfigured_password sets password."""
    container = IRISContainer()
    result = container.with_preconfigured_password("test_pass")
    assert container._preconfigure_password == "test_pass"
    assert container._password == "test_pass"
    assert result is container


def test_with_credentials_validation():
    """Test validation for empty credentials."""
    container = IRISContainer()
    with pytest.raises(ValueError, match="Password cannot be empty"):
        container.with_credentials("user", "")
    with pytest.raises(ValueError, match="Username cannot be empty"):
        container.with_credentials("", "pass")


def test_with_preconfigured_password_validation():
    """Test validation for empty password."""
    container = IRISContainer()
    with pytest.raises(ValueError, match="Password cannot be empty"):
        container.with_preconfigured_password("")


def test_start_sets_env_vars_when_password_configured():
    """Test that start() sets IRIS_PASSWORD env var when configured."""
    container = IRISContainer()
    container.with_preconfigured_password("secret_pass")

    # Track with_env calls
    original_with_env = container.with_env
    env_calls = []

    def track_with_env(key, value):
        env_calls.append((key, value))
        return original_with_env(key, value)

    container.with_env = track_with_env

    # Mock the parent start and get_config
    with patch.object(IRISContainer.__bases__[0], "start", return_value=container):
        container.get_config = MagicMock()
        container.start()

    assert ("IRIS_PASSWORD", "secret_pass") in env_calls
    assert container._password_preconfigured is True


def test_start_sets_both_env_vars_when_credentials_configured():
    """Test that start() sets both env vars when credentials configured."""
    container = IRISContainer()
    container.with_credentials("custom_user", "secret_pass")

    # Track with_env calls
    original_with_env = container.with_env
    env_calls = []

    def track_with_env(key, value):
        env_calls.append((key, value))
        return original_with_env(key, value)

    container.with_env = track_with_env

    # Mock the parent start and get_config
    with patch.object(IRISContainer.__bases__[0], "start", return_value=container):
        container.get_config = MagicMock()
        container.start()

    assert ("IRIS_PASSWORD", "secret_pass") in env_calls
    assert ("IRIS_USERNAME", "custom_user") in env_calls
