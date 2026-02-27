import pytest
from unittest.mock import patch
from iris_devtester.connections import get_connection
from iris_devtester.config import IRISConfig

@pytest.mark.integration
@pytest.mark.slow
def test_implicit_namespace_creation_on_localhost(iris_container):
    """
    Test that get_connection() auto-creates a namespace on localhost.
    """
    config = iris_container.get_config()
    new_namespace = "IMPLICIT_NS_TEST"
    
    # Ensure it doesn't exist first (though it's a fresh container)
    # We use the config from the container but change the namespace
    test_config = IRISConfig(
        host=config.host,
        port=config.port,
        namespace=new_namespace,
        username=config.username,
        password=config.password,
        container_name=iris_container.get_container_name()
    )
    
    # This should trigger auto-creation
    conn = get_connection(test_config)
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT $NAMESPACE")
        result = cursor.fetchone()
        assert result[0] == new_namespace
        
        # Verify it exists in Config.Namespaces
        script = f'Write ##class(Config.Namespaces).Exists("{new_namespace}")'
        output = iris_container.execute_objectscript(script, namespace="%SYS")
        assert "1" in output
        
    finally:
        conn.close()

@pytest.mark.integration
def test_no_auto_create_for_remote_by_default():
    """
    Test that auto-creation is NOT attempted for remote hosts by default.
    """
    # Use a dummy remote host that doesn't exist
    test_config = IRISConfig(
        host="192.168.1.100", # Non-localhost
        namespace="REMOTE_NS",
        auto_create=None # Use smart default
    )
    
    # We don't want to actually connect, we just want to verify 
    # that ensure_namespace_exists returns True without trying docker exec
    from iris_devtester.utils.namespace import ensure_namespace_exists
    
    # It should return True (skipping creation) because it's not localhost
    # and no container_name is provided.
    assert ensure_namespace_exists(test_config) is True

@pytest.mark.integration
def test_explicit_opt_in_for_remote(iris_container):
    """
    Test that explicit auto_create=True works even if host is not localhost.
    """
    config = iris_container.get_config()
    new_namespace = "REMOTE_OPT_IN"
    
    # Simulate a "remote" connection by using the host IP instead of 'localhost'
    # if it's different, or just explicitly setting auto_create=True
    test_config = IRISConfig(
        host=config.host,
        port=config.port,
        namespace=new_namespace,
        username=config.username,
        password=config.password,
        container_name=iris_container.get_container_name(),
        auto_create=True
    )
    
    conn = get_connection(test_config)
    try:
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute("SELECT $NAMESPACE")
        result = cursor.fetchone()
        assert result[0] == new_namespace
    finally:
        conn.close()


@pytest.mark.integration
@pytest.mark.slow
def test_iris_connect_namespace_check_no_docker(iris_container):
    """
    T012+T013: Test that explicit config without container_name checks namespace
    via iris.connect() to %SYS, not via Docker exec.
    
    Verifies FR-001 and FR-002 end-to-end.
    """
    config = iris_container.get_config()
    
    # Create explicit config WITHOUT container_name
    # This should force the iris.connect() strategy
    test_config = IRISConfig(
        host=config.host,
        port=config.port,
        namespace="USER",  # Known to exist
        username=config.username,
        password=config.password,
        container_name=None,  # Explicitly no container
        auto_create=True,
    )
    
    from iris_devtester.utils.namespace import ensure_namespace_exists
    
    # Patch subprocess to verify it's NOT called
    with patch("subprocess.run") as mock_subprocess:
        result = ensure_namespace_exists(test_config)
        
        assert result is True
        # The key assertion: subprocess (Docker exec) was NOT used
        mock_subprocess.assert_not_called()


@pytest.mark.integration
@pytest.mark.slow
def test_auto_discovered_config_uses_docker_exec(iris_container):
    """
    T017: Test that auto-discovered config with container_name uses Docker exec.
    
    Verifies FR-003 backward compatibility.
    """
    config = iris_container.get_config()
    container_name = iris_container.get_container_name()
    
    # Config WITH container_name — should use Docker exec
    test_config = IRISConfig(
        host=config.host,
        port=config.port,
        namespace="USER",
        username=config.username,
        password=config.password,
        container_name=container_name,
        auto_create=True,
    )
    
    from iris_devtester.utils.namespace import ensure_namespace_exists
    
    with patch("subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = type('MockResult', (), {
            'stdout': b'1\n',
            'returncode': 0,
        })()
        
        result = ensure_namespace_exists(test_config)
        
        assert result is True
        # Docker exec SHOULD be used when container_name is set
        mock_subprocess.assert_called()
        # Verify correct container name was used (not "iris_db")
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]
        assert container_name in cmd
        assert "iris_db" not in cmd
