import pytest
from iris_devtester import IRISContainer, get_connection
from iris_devtester.containers.performance import get_resource_metrics

@pytest.mark.e2e
@pytest.mark.integration
def test_skill_guided_workflow():
    with IRISContainer.community(username="skill_user", password="SYS") as iris:
        container = iris.get_wrapped_container()
        assert container is not None
        assert container.status == "running"
        
        conn = iris.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT $ZVERSION")
        result = cursor.fetchone()
        assert result is not None
        assert "IRIS" in result[0]
        
        metrics = get_resource_metrics(iris)
        assert metrics.memory_percent >= 0
        assert metrics.cpu_percent >= 0
        
        cursor.execute("CREATE TABLE App.Test (ID INT, Val VARCHAR(10))")
        cursor.execute("INSERT INTO App.Test VALUES (1, 'OK')")
        conn.commit()
        
        cursor.execute("SELECT Val FROM App.Test WHERE ID=1")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "OK"
