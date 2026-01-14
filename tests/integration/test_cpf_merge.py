import pytest
from iris_devtester import IRISContainer, get_connection
from iris_devtester.config import CPFPreset

@pytest.mark.integration
@pytest.mark.parametrize("edition", ["community", "enterprise"])
def test_cpf_merge_enables_callin_on_startup(edition):
    """Verify that CPF merge snippet enables CallIn service without remediation."""
    cpf_content = CPFPreset.SECURE_DEFAULTS
    
    if edition == "community":

        import platform
        if platform.machine() == "arm64":
            image = "containers.intersystems.com/intersystems/iris-community:2025.1"
        else:
            image = "intersystemsdc/iris-community:latest"
        iris_container = IRISContainer.community(image=image, username="test", password="test")
    else:
        import os
        license_key = os.environ.get("IRIS_LICENSE_KEY")
        if not license_key:
            import pathlib
            key_file = pathlib.Path(__file__).parent.parent.parent / "iris.key"
            if key_file.exists():
                license_key = key_file.read_text().strip()
        if not license_key:
            pytest.skip("IRIS_LICENSE_KEY not set")
        iris_container = IRISContainer.enterprise(license_key=license_key, username="SuperUser", password="SYS")

    with iris_container.with_cpf_merge(cpf_content) as iris:
        conn = iris.get_connection(enable_callin=False)
        
        try:

            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
        finally:
            conn.close()


@pytest.mark.integration
def test_cpf_merge_from_file(tmp_path):
    cpf_file = tmp_path / "test.cpf"
    cpf_file.write_text(CPFPreset.ENABLE_CALLIN)
    
    with IRISContainer.community().with_cpf_merge(str(cpf_file.absolute())) as iris:
        conn = iris.get_connection()
        assert conn is not None
        conn.close()
