import pytest
from iris_devtester.containers import IRISContainer

@pytest.mark.integration
def test_superuser_remediation_works():
    with IRISContainer.community(
        username="SuperUser",
        password="SYS",
        namespace="USER"
    ) as iris:
        conn = iris.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT $USERNAME")
        username = cursor.fetchone()[0]
        
        assert username.upper() == "SUPERUSER"
