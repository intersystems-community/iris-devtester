import pytest
import uuid
import subprocess
from iris_devtester.fixtures import DATFixtureLoader, FixtureCreator
from iris_devtester.config import IRISConfig
from iris_devtester.connections import get_connection

@pytest.mark.integration
def test_fixture_refresh_works(iris_container):
    source_ns = f"SRC_{uuid.uuid4().hex[:8]}".upper()
    target_ns = f"TGT_{uuid.uuid4().hex[:8]}".upper()
    
    config = iris_container.get_config()
    
    import subprocess
    container_name = iris_container.get_wrapped_container().name
    cmd = ["docker", "exec", "-i", container_name, "sh", "-c", "iris session IRIS -U %SYS"]
    subprocess.run(cmd, input=f'Do ##class(Config.Namespaces).Create("{source_ns}", ##class(Config.Namespaces).Get("USER"))\nHalt\n', text=True, capture_output=True, timeout=30)
    
    source_config = IRISConfig(host="127.0.0.1", port=config.port, namespace=source_ns, username="_SYSTEM", password="SYS")
    src_conn = get_connection(source_config, auto_retry=False)
    src_cursor = src_conn.cursor()
    src_cursor.execute("CREATE TABLE Test.Data (ID INT, Name VARCHAR(50))")
    src_cursor.execute("INSERT INTO Test.Data (ID, Name) VALUES (1, 'Initial')")
    src_conn.commit()
    src_conn.close()
    
    creator = FixtureCreator(container=iris_container)
    fixture_path = f"/tmp/fixture_{source_ns}"
    creator.create_fixture(fixture_id="test-refresh", namespace=source_ns, output_dir=fixture_path)
    
    loader = DATFixtureLoader(container=iris_container)
    result1 = loader.load_fixture(fixture_path, target_namespace=target_ns)
    assert result1.success is True
    
    tgt_config = IRISConfig(host="127.0.0.1", port=config.port, namespace=target_ns, username="_SYSTEM", password="SYS")
    tgt_conn = get_connection(tgt_config)
    tgt_cursor = tgt_conn.cursor()
    tgt_cursor.execute("UPDATE Test.Data SET Name = 'Modified'")
    tgt_conn.commit()
    tgt_conn.close()
    
    result2 = loader.load_fixture(fixture_path, target_namespace=target_ns, force_refresh=True)
    assert result2.success is True
    
    tgt_conn2 = get_connection(tgt_config)
    tgt_cursor2 = tgt_conn2.cursor()
    tgt_cursor2.execute("SELECT Name FROM Test.Data")
    assert tgt_cursor2.fetchone()[0] == "Initial"

