"""
Unit tests for the IRIS Dev Instance management logic.
"""

import os
import hashlib
import pytest
from unittest.mock import MagicMock, patch

from iris_devtester.containers.dev_instance import (
    DevInstanceManager,
    DEV_INSTANCE_NAME,
    DEV_VOLUME_NAME,
    get_project_id,
    get_project_namespace
)


def test_get_project_id():
    """Verify stable hashing of directory paths."""
    path1 = "/absolute/path/to/project1"
    path2 = "/absolute/path/to/project2"
    
    id1 = get_project_id(path1)
    id2 = get_project_id(path2)
    
    assert len(id1) == 11
    assert id1.isupper()
    assert id1 == get_project_id(path1)  # Stable
    assert id1 != id2  # Unique


def test_get_project_namespace():
    """Verify IRIS-compatible namespace name generation."""
    path = "/some/path"
    ns = get_project_namespace(path)
    
    assert ns.startswith("P")
    assert len(ns) == 12
    assert ns.isupper()


@patch("docker.from_env")
def test_dev_instance_manager_status(mock_docker):
    """Verify DevInstanceManager status checks."""
    mock_client = MagicMock()
    mock_docker.return_value = mock_client
    
    # Instance doesn't exist
    from docker.errors import NotFound
    mock_client.containers.get.side_effect = NotFound("Not found")
    manager = DevInstanceManager()
    assert manager.get_instance() is None
    assert not manager.is_running()
    
    # Instance exists but stopped
    mock_instance = MagicMock()
    mock_instance.status = "exited"
    mock_client.containers.get.side_effect = None
    mock_client.containers.get.return_value = mock_instance
    
    assert manager.get_instance() == mock_instance
    assert not manager.is_running()
    
    # Instance running
    mock_instance.status = "running"
    assert manager.is_running()


@patch("docker.from_env")
@patch("iris_devtester.utils.iris_container_adapter.IRISContainerManager.create_from_config")
def test_dev_instance_ensure_ready(mock_create, mock_docker):
    """Verify logic for ensuring dev instance is ready."""
    mock_client = MagicMock()
    mock_docker.return_value = mock_client
    
    # Mock container not existing
    from docker.errors import NotFound
    mock_client.containers.get.side_effect = NotFound("No container")
    
    # Mock container being created
    mock_instance = MagicMock()
    mock_instance.status = "running"
    mock_create.return_value = mock_instance
    
    manager = DevInstanceManager()
    instance = manager.ensure_ready()
    
    assert instance == mock_instance
    # Verify volume was checked/created
    mock_client.volumes.get.assert_called()
    # Verify adapter was called with correct config
    mock_create.assert_called_once()
    args, kwargs = mock_create.call_args
    config = args[0]
    assert config.container_name == DEV_INSTANCE_NAME
    assert config.durable_sys is True
    assert f"{DEV_VOLUME_NAME}:/iris/data" in config.volumes
