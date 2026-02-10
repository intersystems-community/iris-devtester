"""
Integration tests for the IRIS Dev Instance.
"""

import pytest
import subprocess
import time
from pathlib import Path

from iris_devtester.containers.dev_instance import (
    DevInstanceManager,
    DEV_INSTANCE_NAME,
    DEV_VOLUME_NAME,
    get_project_namespace
)
from iris_devtester.connections import get_connection


@pytest.mark.integration
def test_dev_instance_lifecycle():
    """Verify up/down/status lifecycle of the dev engine."""
    manager = DevInstanceManager()
    
    # Cleanup any stale state
    manager.remove(remove_volumes=True)
    
    try:
        # Start engine
        print("\nStarting dev engine...")
        instance = manager.ensure_ready()
        assert instance.status in ["running", "created"]
        assert manager.is_running() or instance.status == "created"
        
        # Verify container name
        assert instance.name == DEV_INSTANCE_NAME
        
        # Verify volume exists
        import docker
        client = docker.from_env()
        volume = client.volumes.get(DEV_VOLUME_NAME)
        assert volume is not None
        
        # Stop engine
        print("Stopping dev engine...")
        manager.stop()
        instance.reload()
        assert instance.status == "exited"
        
        # Remove engine (keep volume)
        print("Removing dev engine container...")
        manager.remove(remove_volumes=False)
        assert manager.get_instance() is None
        
        # Volume should still exist
        assert client.volumes.get(DEV_VOLUME_NAME) is not None
        
    finally:
        manager.remove(remove_volumes=True)


@pytest.mark.integration
def test_dev_instance_connection_isolation():
    """Verify that different projects get isolated namespaces."""
    manager = DevInstanceManager()
    # Ensure fresh state for test
    manager.remove(remove_volumes=True)
    
    try:
        # Project 1
        path1 = "/tmp/project1"
        ns1 = get_project_namespace(path1)
        
        # Project 2
        path2 = "/tmp/project2"
        ns2 = get_project_namespace(path2)
        
        assert ns1 != ns2
        
        # Start engine
        instance = manager.ensure_ready()
        
        # Get actual mapped port
        instance.reload()
        ports = instance.attrs["NetworkSettings"]["Ports"]
        mapped_port = int(ports["1972/tcp"][0]["HostPort"])
        
        # Wait for IRIS to be fully ready (cold start)
        from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy
        strategy = IRISReadyWaitStrategy(timeout=120)
        strategy.wait_until_ready("localhost", port=mapped_port, container_name=DEV_INSTANCE_NAME)
        
        # Connect to Project 1
        from iris_devtester.config import IRISConfig
        iris_config1 = IRISConfig(port=mapped_port, namespace=ns1, container_name=DEV_INSTANCE_NAME)
        
        conn1 = get_connection(iris_config1)
        cursor1 = conn1.cursor()
        cursor1.execute("CREATE TABLE TestData (ID INT PRIMARY KEY)")
        cursor1.execute("INSERT INTO TestData VALUES (1)")
        conn1.commit()
        
        # Connect to Project 2 (should be empty)
        iris_config2 = IRISConfig(port=mapped_port, namespace=ns2, container_name=DEV_INSTANCE_NAME)
        conn2 = get_connection(iris_config2)
        cursor2 = conn2.cursor()
        
        # In Project 2, the table should NOT exist
        try:
            cursor2.execute("SELECT * FROM TestData")
            pytest.fail("Table should not exist in Project 2 namespace")
        except Exception as e:
            assert "not found" in str(e).lower() or "SQLCODE -30" in str(e)
            
        print(f"✓ Isolation verified between {ns1} and {ns2}")
        
    finally:
        manager.remove(remove_volumes=True)


@pytest.mark.integration
def test_dev_instance_warm_start_performance():
    """Verify that warm-start connection is under 500ms."""
    manager = DevInstanceManager()
    instance = manager.ensure_ready()
    
    # Get actual mapped port
    instance.reload()
    ports = instance.attrs["NetworkSettings"]["Ports"]
    mapped_port = int(ports["1972/tcp"][0]["HostPort"])
    
    # Wait for ready if not already
    from iris_devtester.containers.wait_strategies import IRISReadyWaitStrategy
    strategy = IRISReadyWaitStrategy(timeout=120)
    strategy.wait_until_ready("localhost", port=mapped_port, container_name=DEV_INSTANCE_NAME)
    
    # Warm up the namespace (ensure it exists)
    from iris_devtester.config import IRISConfig
    warmup_config = IRISConfig(port=mapped_port, namespace="USER", container_name=DEV_INSTANCE_NAME)
    get_connection(warmup_config).close()
    
    # Measure connection time
    import time
    start = time.perf_counter()
    
    # Explicitly use dev instance port to verify WARM start of the connection handle
    # Connect to the ALREADY EXISTING namespace
    conn = get_connection(warmup_config)
    
    elapsed = (time.perf_counter() - start) * 1000
    print(f"Warm start connection took {elapsed:.2f}ms")
    
    assert elapsed < 500
    conn.close()
