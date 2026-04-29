import pytest
from unittest.mock import patch

from iris_devtester import IRISContainer, get_connection
from iris_devtester.containers.performance import get_resource_metrics


@pytest.mark.e2e
@pytest.mark.integration
def test_skill_guided_workflow():
    with IRISContainer.community() as iris:
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


@pytest.mark.e2e
@pytest.mark.integration
def test_cpf_first_no_docker_exec_on_happy_path():
    from iris_devtester.utils.password import unexpire_all_passwords

    with patch("iris_devtester.utils.password.unexpire_all_passwords") as mock_unexpire:
        with IRISContainer.community() as iris:
            conn = iris.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    mock_unexpire.assert_not_called()
